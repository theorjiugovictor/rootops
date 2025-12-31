"""
Performance Predictor Service

Uses XGBoost Regression to forecast system performance metrics (Latency, CPU) 
based on deployment characteristics.
"""
import logging
import joblib
import os
import numpy as np
from typing import List, Dict, Tuple
from xgboost import XGBRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

logger = logging.getLogger(__name__)

class PerformancePredictor:
    """
    Predicts performance impact of changes.
    """
    
    def __init__(self, model_path: str = "model_artifacts/performance_model.joblib"):
        self.model_path = model_path
        self.model = None
        self.is_trained = False
        self._ensure_artifacts_dir()
        self._load_model()
        
    def _ensure_artifacts_dir(self):
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        
    def _load_model(self):
        if os.path.exists(self.model_path):
            try:
                self.model = joblib.load(self.model_path)
                self.is_trained = True
                logger.info("Loaded existing Performance Prediction model")
            except Exception as e:
                logger.error(f"Failed to load performance model: {e}")
                self.model = self._create_pipeline()
        else:
            self.model = self._create_pipeline()
            
    def _create_pipeline(self) -> Pipeline:
        """Create XGBoost Regression pipeline."""
        return Pipeline([
            ('scaler', StandardScaler()),
            ('regressor', XGBRegressor(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                objective='reg:squarederror',
                n_jobs=-1,
                random_state=42
            ))
        ])
    
    def prepare_features(self, commit_data: Dict, system_state: Dict) -> List[float]:
        """
        Features for performance prediction:
        1. lines_added (code churn)
        2. complexity_score (structural complexity)
        3. files_changed (breadth of change)
        4. current_cpu_usage (system load)
        5. current_p95_latency (baseline performance)
        6. database_migration (bool, impactful)
        """
        patterns = commit_data.get("risky_patterns", [])
        return [
            float(commit_data.get("additions", 0)),
            float(commit_data.get("complexity_score", 0)),
            float(commit_data.get("files_changed", 0)),
            float(system_state.get("cpu_usage", 0.0)),
            float(system_state.get("p95_latency", 0.0)),
            1.0 if "db_migration" in patterns else 0.0
        ]

    def train(self, historical_data: List[Dict]) -> Dict:
        """
        Train regression model.
        Data should contain 'features' and 'target_latency'.
        """
        if len(historical_data) < 10:
             return {"success": False, "message": "Insufficient data"}
             
        X = []
        y = []
        for data in historical_data:
            X.append(data["features"])
            # Target is the P95 latency OBSERVED after this deployment
            y.append(float(data["target_latency"]))
            
        try:
            self.model.fit(np.array(X), np.array(y))
            self.is_trained = True
            joblib.dump(self.model, self.model_path)
            
            score = self.model.score(np.array(X), np.array(y)) # R^2 score
            logger.info(f"Trained Performance Predictor (R2: {score:.2f})")
            return {"success": True, "r2_score": score, "samples": len(X)}
        except Exception as e:
            logger.error(f"Performance training failed: {e}")
            return {"success": False, "error": str(e)}

    def predict_latency(self, features: List[float]) -> float:
        """
        Predict expected P95 latency (ms).
        """
        if not self.is_trained:
            # Fallback: simple heuristic based on complexity
            # Baseline is current latency (feature index 4)
            current_latency = features[4] if len(features) > 4 else 100.0
            complexity = features[1] if len(features) > 1 else 0
            churn = features[0] if len(features) > 0 else 0
            
            # Simple impactful math
            impact = (complexity * 0.1) + (churn * 0.05)
            return current_latency + impact
            
        try:
            prediction = self.model.predict([features])[0]
            return float(prediction)
        except Exception as e:
            logger.error(f"Performance prediction failed: {e}")
            return -1.0
