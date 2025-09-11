"""
Confidence Scorer

Advanced confidence scoring system for pattern predictions that combines:
- Pattern strength (historical win rate and sample size)  
- Statistical significance (p-values and confidence intervals)
- Regime stability (consistency across different market conditions)
- Recent performance (weighted emphasis on recent occurrences)
- Context factors (Fed environment, market stress, etc.)
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
from pathlib import Path

from ..utils.date_utils import now_iso, parse_date_string
from .statistical_validator import StatisticalValidator

logger = logging.getLogger(__name__)


class ConfidenceScorer:
    """
    Advanced confidence scoring system for pattern predictions.
    
    Combines multiple factors to produce calibrated confidence scores:
    - Historical performance metrics
    - Statistical significance
    - Temporal stability  
    - Recent performance weighting
    - Market context adjustments
    """
    
    def __init__(self, 
                 base_lookback_days: int = 252,
                 recent_weight_days: int = 63,
                 min_sample_size: int = 20):
        """
        Initialize confidence scorer.
        
        Args:
            base_lookback_days: Days for base historical analysis (default 252 = 1 year)
            recent_weight_days: Days for recent performance weighting (default 63 = 3 months)
            min_sample_size: Minimum sample size for reliable scoring
        """
        self.base_lookback_days = base_lookback_days
        self.recent_weight_days = recent_weight_days
        self.min_sample_size = min_sample_size
        
        self.validator = StatisticalValidator()
        
        # Scoring weights for different components
        self.component_weights = {
            'historical_performance': 0.30,
            'statistical_significance': 0.25,
            'regime_stability': 0.20,
            'recent_performance': 0.15,
            'context_factors': 0.10
        }
        
        logger.info(f"ConfidenceScorer initialized with lookback={base_lookback_days} days")
    
    def calculate_pattern_confidence(self, 
                                   pattern_data: Dict,
                                   statistical_results: Dict = None,
                                   market_context: Dict = None,
                                   recent_data: Dict = None) -> Dict:
        """
        Calculate comprehensive confidence score for a pattern.
        
        Args:
            pattern_data: Historical pattern performance data
            statistical_results: Results from StatisticalValidator
            market_context: Current market context (Fed, stress, etc.)
            recent_data: Recent pattern performance data
            
        Returns:
            Dictionary with detailed confidence scoring breakdown
        """
        logger.info(f"Calculating confidence for pattern: {pattern_data.get('pattern', 'Unknown')}")
        
        confidence_components = {}
        
        # 1. Historical Performance Score (30%)
        hist_score = self._score_historical_performance(pattern_data)
        confidence_components['historical_performance'] = hist_score
        
        # 2. Statistical Significance Score (25%)
        if statistical_results:
            stat_score = self._score_statistical_significance(statistical_results)
        else:
            stat_score = self._estimate_statistical_score(pattern_data)
        confidence_components['statistical_significance'] = stat_score
        
        # 3. Regime Stability Score (20%)
        stability_score = self._score_regime_stability(pattern_data)
        confidence_components['regime_stability'] = stability_score
        
        # 4. Recent Performance Score (15%)
        if recent_data:
            recent_score = self._score_recent_performance(recent_data, pattern_data)
        else:
            recent_score = hist_score  # Fall back to historical if no recent data
        confidence_components['recent_performance'] = recent_score
        
        # 5. Context Factors Score (10%)
        context_score = self._score_context_factors(market_context, pattern_data)
        confidence_components['context_factors'] = context_score
        
        # Calculate weighted overall confidence
        overall_confidence = sum(
            score * self.component_weights[component]
            for component, score in confidence_components.items()
        )
        
        # Apply adjustments
        adjusted_confidence = self._apply_confidence_adjustments(
            overall_confidence, pattern_data, market_context
        )
        
        # Confidence calibration
        calibrated_confidence = self._calibrate_confidence(adjusted_confidence, pattern_data)
        
        return {
            'pattern': pattern_data.get('pattern', 'Unknown'),
            'overall_confidence': round(calibrated_confidence, 1),
            'raw_confidence': round(overall_confidence, 1),
            'adjusted_confidence': round(adjusted_confidence, 1),
            'component_scores': {k: round(v, 1) for k, v in confidence_components.items()},
            'component_weights': self.component_weights,
            'sample_size': pattern_data.get('total_occurrences', 0),
            'confidence_level': self._interpret_confidence_level(calibrated_confidence),
            'reliability': self._assess_reliability(pattern_data),
            'analysis_date': now_iso()
        }
    
    def batch_score_patterns(self, 
                           patterns_data: Dict,
                           statistical_results: Dict = None,
                           market_context: Dict = None) -> Dict:
        """
        Score confidence for multiple patterns in batch.
        
        Args:
            patterns_data: Dictionary mapping pattern names to data
            statistical_results: Statistical validation results
            market_context: Current market context
            
        Returns:
            Dictionary with confidence scores for all patterns
        """
        logger.info(f"Batch scoring {len(patterns_data)} patterns")
        
        batch_results = {
            'analysis_date': now_iso(),
            'patterns_scored': len(patterns_data),
            'market_context': market_context,
            'pattern_scores': {}
        }
        
        for pattern_name, pattern_data in patterns_data.items():
            # Get statistical results for this pattern if available
            pattern_stats = None
            if statistical_results and 'results' in statistical_results:
                pattern_stats = statistical_results['results'].get(pattern_name)
            
            # Calculate confidence score
            confidence_result = self.calculate_pattern_confidence(
                pattern_data=pattern_data,
                statistical_results=pattern_stats,
                market_context=market_context
            )
            
            batch_results['pattern_scores'][pattern_name] = confidence_result
        
        # Add batch-level insights
        batch_results['summary'] = self._generate_batch_summary(batch_results['pattern_scores'])
        
        return batch_results
    
    def _score_historical_performance(self, pattern_data: Dict) -> float:
        """Score based on historical win rate and return magnitude."""
        win_rate = pattern_data.get('win_rate', 50.0) / 100.0  # Convert to decimal
        avg_return = pattern_data.get('mean_return', 0.0)
        sample_size = pattern_data.get('total_occurrences', 0)
        
        # Base score from win rate (0-100)
        win_rate_score = min(100, max(0, (win_rate - 0.5) * 200))  # Scale 50-100% to 0-100
        
        # Return magnitude bonus/penalty
        return_magnitude = abs(avg_return)
        if avg_return > 0:
            return_bonus = min(20, return_magnitude * 10)  # Up to 20 point bonus
        else:
            return_bonus = -min(20, return_magnitude * 10)  # Up to 20 point penalty
        
        # Sample size adjustment
        if sample_size < self.min_sample_size:
            size_penalty = (self.min_sample_size - sample_size) / self.min_sample_size * 30
        else:
            size_penalty = 0
        
        score = win_rate_score + return_bonus - size_penalty
        return max(0, min(100, score))
    
    def _score_statistical_significance(self, statistical_results: Dict) -> float:
        """Score based on statistical significance tests."""
        if not statistical_results or 'overall_significant' not in statistical_results:
            return 50.0  # Neutral score if no stats available
        
        # Base score from overall significance
        base_score = 75 if statistical_results['overall_significant'] else 25
        
        # Adjust based on number of significant tests
        sig_count = statistical_results.get('significant_test_count', 0)
        total_tests = statistical_results.get('total_tests', 4)
        
        if total_tests > 0:
            sig_ratio = sig_count / total_tests
            ratio_adjustment = (sig_ratio - 0.5) * 50  # Scale 50-100% to 0-25
            base_score += ratio_adjustment
        
        # P-value adjustments
        if 't_test' in statistical_results:
            t_p_value = statistical_results['t_test'].get('p_value', 1.0)
            if not np.isnan(t_p_value):
                # Stronger significance gets higher score
                if t_p_value < 0.001:
                    base_score += 10
                elif t_p_value < 0.01:
                    base_score += 5
                elif t_p_value < 0.05:
                    base_score += 2
        
        # Bootstrap CI check
        if 'bootstrap_ci' in statistical_results:
            if statistical_results['bootstrap_ci'].get('excludes_zero', False):
                base_score += 5
        
        return max(0, min(100, base_score))
    
    def _estimate_statistical_score(self, pattern_data: Dict) -> float:
        """Estimate statistical score when full validation not available."""
        win_rate = pattern_data.get('win_rate', 50.0)
        sample_size = pattern_data.get('total_occurrences', 0)
        
        # Rough estimation based on win rate and sample size
        if sample_size < 10:
            return 20  # Low confidence without validation
        elif sample_size < 30:
            return 40  # Medium-low confidence
        
        # Estimate significance based on win rate deviation from 50%
        deviation = abs(win_rate - 50)
        if deviation > 20:
            return 80  # Likely significant
        elif deviation > 10:
            return 60  # Possibly significant
        else:
            return 40  # Unlikely significant
    
    def _score_regime_stability(self, pattern_data: Dict) -> float:
        """Score based on pattern stability across market regimes."""
        # Check if regime breakdown data is available
        if 'regime_breakdown' in pattern_data:
            regime_data = pattern_data['regime_breakdown']
            if isinstance(regime_data, dict) and len(regime_data) > 1:
                return self._calculate_regime_stability_score(regime_data)
        
        # If no regime data, check for time period stability
        if 'time_period_breakdown' in pattern_data:
            period_data = pattern_data['time_period_breakdown']
            if isinstance(period_data, dict) and len(period_data) > 1:
                return self._calculate_time_stability_score(period_data)
        
        # Default to historical performance if no stability data
        return self._score_historical_performance(pattern_data) * 0.8  # Slight penalty for unknown stability
    
    def _calculate_regime_stability_score(self, regime_data: Dict) -> float:
        """Calculate stability score from regime breakdown data."""
        win_rates = []
        sample_sizes = []
        
        for regime, data in regime_data.items():
            if isinstance(data, dict) and 'win_rate' in data:
                win_rates.append(data['win_rate'])
                sample_sizes.append(data.get('sample_size', 1))
        
        if len(win_rates) < 2:
            return 50.0
        
        # Calculate coefficient of variation
        mean_win_rate = np.mean(win_rates)
        std_win_rate = np.std(win_rates)
        
        if mean_win_rate == 0:
            return 50.0
        
        cv = std_win_rate / mean_win_rate
        
        # Lower CV = higher stability
        stability_score = max(0, 100 - cv * 100)
        
        # Weight by sample sizes
        total_samples = sum(sample_sizes)
        if total_samples < 30:
            stability_score *= 0.7  # Penalty for small samples
        
        return min(100, stability_score)
    
    def _calculate_time_stability_score(self, period_data: Dict) -> float:
        """Calculate stability score from time period breakdown."""
        return self._calculate_regime_stability_score(period_data)  # Same logic
    
    def _score_recent_performance(self, recent_data: Dict, historical_data: Dict) -> float:
        """Score based on recent vs historical performance."""
        recent_win_rate = recent_data.get('win_rate', 50.0)
        historical_win_rate = historical_data.get('win_rate', 50.0)
        
        recent_sample_size = recent_data.get('sample_size', 0)
        
        # Base score from recent performance
        base_score = self._score_historical_performance(recent_data)
        
        # Consistency bonus/penalty
        consistency = 1.0 - abs(recent_win_rate - historical_win_rate) / 100.0
        consistency_adjustment = (consistency - 0.8) * 50  # Reward consistency > 80%
        
        # Sample size adjustment for recent data
        if recent_sample_size < 5:
            base_score *= 0.5  # Heavy penalty for very small recent sample
        elif recent_sample_size < 10:
            base_score *= 0.7  # Moderate penalty
        
        final_score = base_score + consistency_adjustment
        return max(0, min(100, final_score))
    
    def _score_context_factors(self, market_context: Dict, pattern_data: Dict) -> float:
        """Score based on current market context factors."""
        if not market_context:
            return 50.0  # Neutral if no context
        
        base_score = 50.0
        
        # Fed context factors
        if 'fed_environment' in market_context:
            fed_env = market_context['fed_environment']
            # Pattern-specific adjustments could go here
            # For now, neutral scoring
        
        # Market stress factors
        stress_level = market_context.get('market_stress_level', 'normal')
        if stress_level == 'low':
            base_score += 5  # Slight boost in low stress
        elif stress_level == 'elevated':
            base_score -= 5  # Slight penalty in elevated stress
        elif stress_level == 'extreme':
            base_score -= 15  # Larger penalty in extreme stress
        
        # Volatility regime
        if 'vix_regime' in market_context:
            vix_regime = market_context['vix_regime']
            if vix_regime == 'low' and pattern_data.get('pattern') == 'pin_risk':
                base_score += 10  # Pin risk more reliable in low vol
            elif vix_regime == 'high' and pattern_data.get('pattern') == 'gamma_trap':
                base_score += 10  # Gamma traps more reliable in high vol
        
        return max(0, min(100, base_score))
    
    def _apply_confidence_adjustments(self, 
                                    base_confidence: float,
                                    pattern_data: Dict,
                                    market_context: Dict) -> float:
        """Apply final adjustments to confidence score."""
        adjusted = base_confidence
        
        # Pattern-specific adjustments
        pattern_name = pattern_data.get('pattern', '')
        
        # Sample size penalties
        sample_size = pattern_data.get('total_occurrences', 0)
        if sample_size < self.min_sample_size:
            penalty_factor = 1.0 - (self.min_sample_size - sample_size) / self.min_sample_size * 0.3
            adjusted *= penalty_factor
        
        # Extreme confidence dampening (reduce overconfidence)
        if adjusted > 90:
            adjusted = 90 + (adjusted - 90) * 0.5  # Dampen extreme high confidence
        elif adjusted < 10:
            adjusted = 10 + (adjusted - 10) * 0.5  # Dampen extreme low confidence
        
        return max(0, min(100, adjusted))
    
    def _calibrate_confidence(self, confidence: float, pattern_data: Dict) -> float:
        """Calibrate confidence to improve reliability."""
        # Simple calibration based on historical accuracy
        # In production, this would use historical confidence vs actual performance
        
        # Conservative calibration - reduce overconfidence
        if confidence > 80:
            calibrated = 80 + (confidence - 80) * 0.7
        elif confidence > 60:
            calibrated = 60 + (confidence - 60) * 0.8
        else:
            calibrated = confidence * 0.9
        
        return max(0, min(95, calibrated))  # Cap at 95% to avoid overconfidence
    
    def _interpret_confidence_level(self, confidence: float) -> str:
        """Provide human-readable confidence level interpretation."""
        if confidence >= 80:
            return "High Confidence"
        elif confidence >= 65:
            return "Medium-High Confidence"
        elif confidence >= 50:
            return "Medium Confidence"
        elif confidence >= 35:
            return "Low-Medium Confidence"
        else:
            return "Low Confidence"
    
    def _assess_reliability(self, pattern_data: Dict) -> str:
        """Assess overall reliability of the pattern."""
        sample_size = pattern_data.get('total_occurrences', 0)
        win_rate = pattern_data.get('win_rate', 50.0)
        
        if sample_size < 10:
            return "Unreliable - Insufficient Data"
        elif sample_size < 30:
            return "Limited Reliability"
        elif sample_size < 50:
            return "Moderate Reliability"
        else:
            if win_rate > 70 or win_rate < 30:
                return "High Reliability"
            else:
                return "Moderate Reliability"
    
    def _generate_batch_summary(self, pattern_scores: Dict) -> Dict:
        """Generate summary statistics for batch scoring."""
        if not pattern_scores:
            return {}
        
        confidences = [score['overall_confidence'] for score in pattern_scores.values()]
        sample_sizes = [score['sample_size'] for score in pattern_scores.values()]
        
        # Find highest confidence patterns
        sorted_patterns = sorted(
            pattern_scores.items(),
            key=lambda x: x[1]['overall_confidence'],
            reverse=True
        )
        
        return {
            'total_patterns': len(pattern_scores),
            'avg_confidence': round(np.mean(confidences), 1),
            'median_confidence': round(np.median(confidences), 1),
            'std_confidence': round(np.std(confidences), 1),
            'high_confidence_patterns': len([c for c in confidences if c >= 70]),
            'medium_confidence_patterns': len([c for c in confidences if 50 <= c < 70]),
            'low_confidence_patterns': len([c for c in confidences if c < 50]),
            'top_3_patterns': [
                {
                    'pattern': name,
                    'confidence': data['overall_confidence'],
                    'level': data['confidence_level']
                }
                for name, data in sorted_patterns[:3]
            ],
            'avg_sample_size': round(np.mean(sample_sizes), 0),
            'total_samples': sum(sample_sizes)
        }