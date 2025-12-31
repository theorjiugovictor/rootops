"""
Anomaly Detector Service

Uses Isolation Forest (Unsupervised Learning) to detect anomalies in system logs and metrics.
"""
import logging
import joblib
import os
import numpy as np
from typing import List, Dict, Tuple
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

logger = logging.getLogger(__name__)

class AnomalyDetector:
    """
    Detects unusual patterns in logs and metrics.
    """
    
    def __init__(self, model_path: str = "model_artifacts/anomaly_model.joblib"):
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
                logger.info("Loaded existing Anomaly Detection model")
            except Exception as e:
                logger.error(f"Failed to load anomaly model: {e}")
                self.model = self._create_pipeline()
        else:
            self.model = self._create_pipeline()
            
    def _create_pipeline(self) -> Pipeline:
        """Create Isolation Forest pipeline."""
        return Pipeline([
            ('scaler', StandardScaler()),
            ('detector', IsolationForest(
                n_estimators=100,
                contamination=0.05, # Expect about 5% anomalies
                random_state=42,
                n_jobs=-1
            ))
        ])
    
    def prepare_features(self, log_analysis: Dict) -> List[float]:
        """
        Convert log analysis dictionary to feature vector.
        Features:
        1. error_rate (float)
        2. log_volume (int)
        3. unique_error_count (int)
        4. warning_count (int)
        5. spike_score (float)
        """
        return [
            float(log_analysis.get("error_rate", 0.0)),
            float(log_analysis.get("log_count", 0)),
            float(len(log_analysis.get("anomalies", []))), # Proxy for unique error patterns
            float(log_analysis.get("warning_count", 0)),
            float(log_analysis.get("spike_score", 0.0))
        ]

    def train(self, historical_data: List[Dict]) -> Dict:
        """
        Train unsupervised model on historical log data.
        We assume historical data contains mostly 'normal' behavior.
        """
        if len(historical_data) < 20:
             return {"success": False, "message": "Insufficient data (need 20+ samples for reliable anomaly detection)"}
             
        X = []
        for data in historical_data:
            X.append(self.prepare_features(data))
            
        try:
            self.model.fit(X)
            self.is_trained = True
            joblib.dump(self.model, self.model_path)
            logger.info("Trained Anomaly Detection model")
            return {"success": True, "samples": len(X)}
        except Exception as e:
            logger.error(f"Anomaly training failed: {e}")
            return {"success": False, "error": str(e)}

    def detect(self, current_data: Dict) -> Dict:
        """
        Detect if current state is anomalous.
        Returns:
            {
                "is_anomaly": bool,
                "score": float (-1.0 to 1.0, lower is more anomalous),
                "severity": str
            }
        """
        if not self.is_trained:
            # Fallback heuristic
            score = current_data.get("spike_score", 0.0)
            return {
                "is_anomaly": score > 0.7,
                "score": -score, # Normalize direction roughly
                "severity": "HIGH" if score > 0.7 else "LOW",
                "method": "heuristic"
            }
            
        features = self.prepare_features(current_data)
        try:
            # Predict: 1 for inlier, -1 for outlier
            prediction = self.model.predict([features])[0]
            # Decision function: average anomaly score
            score = self.model.decision_function([features])[0]
            
            is_anomaly = prediction == -1
            
            severity = "low"
            if is_anomaly:
                # deeper negative score = more anomalous
                if score < -0.2:
                    severity = "CRITICAL"
                else:
                    severity = "HIGH"
            
            return {
                "is_anomaly": is_anomaly,
                "score": float(score),
                "severity": severity,
                "method": "ml"
            }
        except Exception as e:
            logger.error(f"Anomaly detection failed: {e}")
            return {"is_anomaly": False, "error": str(e)}
