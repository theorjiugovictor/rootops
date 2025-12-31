"""
Machine Learning Predictor Service

Uses XGBoost to train real models on deployment history.
"""
import logging
import joblib
import os
import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from xgboost import XGBClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.exceptions import NotFittedError

from src.models.db_models import DeploymentEvent

logger = logging.getLogger(__name__)

class MLPredictor:
    """
    Real ML model for predicting deployment risk.
    Uses XGBoost Classifier trained on historical deployment data.
    """
    
    def __init__(self, model_path: str = "model_artifacts/risk_model.joblib"):
        self.model_path = model_path
        self.model = None
        self.is_trained = False
        self._ensure_artifacts_dir()
        self._load_model()
        
    def _ensure_artifacts_dir(self):
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        
    def _load_model(self):
        """Load persisted model if exists."""
        if os.path.exists(self.model_path):
            try:
                self.model = joblib.load(self.model_path)
                self.is_trained = True
                logger.info("Loaded existing ML model")
            except Exception as e:
                logger.error(f"Failed to load model: {e}")
                self.model = self._create_pipeline()
        else:
            self.model = self._create_pipeline()
            
    def _create_pipeline(self) -> Pipeline:
        """Create new untrained pipeline using XGBoost."""
        return Pipeline([
            ('scaler', StandardScaler()),
            ('classifier', XGBClassifier(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                eval_metric='logloss',
                use_label_encoder=False,
                random_state=42
            ))
        ])

    def prepare_features(self, commit_data: Dict, system_state: Dict, time: datetime) -> List[float]:
        """
        Convert raw data into feature vector.
        Order must match training!
        
        Features:
        1. lines_added
        2. lines_deleted
        3. files_changed
        4. complexity_score
        5. risk_score (heuristic base)
        6. test_ratio
        7. hour_of_day
        8. day_of_week
        """
        return [
            float(commit_data.get("additions", 0)),
            float(commit_data.get("deletions", 0)),
            float(commit_data.get("files_changed", 0)),
            float(commit_data.get("complexity_score", 0)),
            float(commit_data.get("risk_score", 0)),
            float(commit_data.get("test_ratio", 0)),
            float(time.hour),
            float(time.weekday())
        ]

    def train(self, deployments: List[Dict]) -> Dict:
        """
        Train the model on historical deployments.
        Args:
            deployments: List of dictionaries containing features and 'target' (incident bool)
        """
        if len(deployments) < 10:
            logger.warning("Not enough data to train ML model (need 10+ samples)")
            return {"success": False, "message": "Insufficient data"}

        X = []
        y = []
        
        for d in deployments:
            X.append(d["features"])
            y.append(int(d["target"])) # 1 for incident, 0 for success
            
        try:
            self.model.fit(np.array(X), np.array(y))
            self.is_trained = True
            joblib.dump(self.model, self.model_path)
            
            # reliable cv score would be better, but simple accuracy for now
            score = self.model.score(np.array(X), np.array(y))
            logger.info(f"Trained XGBoost model with accuracy: {score:.2f}")
            
            return {
                "success": True, 
                "accuracy": score, 
                "samples": len(X)
            }
        except Exception as e:
            logger.error(f"Training failed: {e}")
            return {"success": False, "error": str(e)}

    def predict_risk(self, features: List[float]) -> float:
        """
        Predict probability of incident (0.0 to 1.0).
        Returns -1.0 if model is not trained.
        """
        if not self.is_trained:
            return -1.0
            
        try:
            # predict_proba returns [[prob_class_0, prob_class_1]]
            probs = self.model.predict_proba([features])
            return float(probs[0][1]) # Probability of class 1 (Incicent)
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return -1.0
