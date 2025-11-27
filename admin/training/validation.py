"""
Model Validation Module
Validates trained models against test data and real drummer standards
"""

import logging
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ValidationMetrics:
    """Metrics for model validation"""
    mae: float  # Mean Absolute Error
    mse: float  # Mean Squared Error
    r2_score: float  # R² score
    per_param_mae: Dict[str, float]  # MAE per output parameter
    humanization_score: float  # Overall humanization quality score


class ModelValidator:
    """Validate trained humanization models"""
    
    def __init__(self):
        logger.info("Model Validator initialized")
    
    def validate_model(self, model, X_test: np.ndarray, y_test: np.ndarray) -> ValidationMetrics:
        """
        Validate model on test data
        
        Args:
            model: Trained model
            X_test: Test input features
            y_test: Test target features
        
        Returns:
            ValidationMetrics with performance scores
        """
        # Get predictions
        predictions = model.predict(X_test)
        
        # Calculate errors
        errors = predictions - y_test
        mae = float(np.mean(np.abs(errors)))
        mse = float(np.mean(errors ** 2))
        
        # Calculate R² score
        ss_res = np.sum(errors ** 2)
        ss_tot = np.sum((y_test - np.mean(y_test, axis=0)) ** 2)
        r2 = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0.0
        
        # Per-parameter MAE
        param_names = [
            'timing_variance', 'timing_drift', 'groove_consistency',
            'swing_factor', 'velocity_variance', 'ghost_note_frequency',
            'velocity_humanization', 'hihat_variation', 'kick_snare_relationship'
        ]
        
        per_param_mae = {}
        for i, name in enumerate(param_names):
            if i < predictions.shape[1]:
                per_param_mae[name] = float(np.mean(np.abs(errors[:, i])))
        
        # Calculate humanization quality score (0-100)
        humanization_score = self._calculate_humanization_score(predictions)
        
        metrics = ValidationMetrics(
            mae=mae,
            mse=mse,
            r2_score=float(r2),
            per_param_mae=per_param_mae,
            humanization_score=humanization_score
        )
        
        logger.info(f"Validation complete: MAE={mae:.4f}, R²={r2:.3f}, HScore={humanization_score:.1f}")
        return metrics
    
    def _calculate_humanization_score(self, predictions: np.ndarray) -> float:
        """Calculate how human-like the predicted parameters are"""
        scores = []
        
        for pred in predictions:
            # Timing variance score (0.01-0.05 is good)
            timing_var = pred[0] if len(pred) > 0 else 0
            timing_score = 1.0 if 0.01 <= timing_var <= 0.05 else 0.5
            
            # Velocity variance score (0.10-0.25 is good)
            vel_var = pred[4] if len(pred) > 4 else 0
            vel_score = 1.0 if 0.10 <= vel_var <= 0.25 else 0.5
            
            # Groove consistency score (0.70-0.95 is good)
            groove = pred[2] if len(pred) > 2 else 0
            groove_score = 1.0 if 0.70 <= groove <= 0.95 else 0.5
            
            avg_score = (timing_score + vel_score + groove_score) / 3.0
            scores.append(avg_score)
        
        return float(np.mean(scores) * 100)


class HumanEvaluator:
    """Interface for human evaluation of generated patterns"""
    
    def __init__(self):
        self.evaluations = []
        logger.info("Human Evaluator initialized")
    
    def submit_evaluation(self, pattern_id: str, rating: int, comments: str = ""):
        """Submit human evaluation of a generated pattern"""
        evaluation = {
            'pattern_id': pattern_id,
            'rating': rating,  # 1-5 stars
            'comments': comments
        }
        self.evaluations.append(evaluation)
        logger.info(f"Evaluation submitted: {pattern_id} - {rating} stars")
    
    def get_average_rating(self) -> float:
        """Get average rating from all evaluations"""
        if not self.evaluations:
            return 0.0
        ratings = [e['rating'] for e in self.evaluations]
        return sum(ratings) / len(ratings)
