"""
Pattern Probability Mapper

Analyzes historical patterns to calculate:
- Next-day return distributions after each pattern
- Success rates by confidence level
- Fed context impact on pattern outcomes
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import logging
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import json

from ..data_sources.fed_data_integration import FedDataIntegration
from ..gex.calculator import GEXCalculator
from ..utils.date_utils import now_iso, parse_date_string, calculate_duration_minutes

logger = logging.getLogger(__name__)


class PatternProbabilityMapper:
    """
    Analyzes historical patterns to calculate:
    - Next-day return distributions after each pattern
    - Success rates by confidence level  
    - Fed context impact on pattern outcomes
    """
    
    def __init__(self, database_path: str = None):
        """
        Initialize Pattern Probability Mapper.
        
        Args:
            database_path: Path to historical database (optional)
        """
        self.db_path = database_path
        self.cache_dir = Path('.cache/pattern_analysis')
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.fed_integration = FedDataIntegration()
        self.gex_calculator = GEXCalculator()
        
        # Pattern tracking
        self.pattern_history = defaultdict(list)
        self.outcome_cache = {}
        
        logger.info("PatternProbabilityMapper initialized")
    
    def analyze_pattern_outcomes(self, pattern_name: str, 
                                historical_data: pd.DataFrame,
                                lookforward_days: int = 1) -> Dict:
        """
        For each pattern occurrence, what happened next?
        
        Args:
            pattern_name: Name of pattern to analyze
            historical_data: DataFrame with historical pattern and price data
            lookforward_days: Days to look forward for outcomes
            
        Returns:
            Dictionary with statistical analysis of pattern outcomes
        """
        logger.info(f"Analyzing pattern outcomes for: {pattern_name}")
        
        if pattern_name not in historical_data.columns:
            logger.warning(f"Pattern {pattern_name} not found in historical data")
            return {'error': f'Pattern {pattern_name} not found'}
        
        # Filter for pattern occurrences
        pattern_occurrences = historical_data[historical_data[pattern_name] == True].copy()
        
        if len(pattern_occurrences) < 10:
            logger.warning(f"Insufficient data for {pattern_name}: {len(pattern_occurrences)} occurrences")
            return {
                'pattern': pattern_name,
                'total_occurrences': len(pattern_occurrences),
                'error': 'Insufficient data (minimum 10 occurrences required)'
            }
        
        # Calculate forward returns
        returns = []
        for idx, row in pattern_occurrences.iterrows():
            try:
                # Find the next trading day's data
                next_idx = historical_data.index.get_indexer([idx], method='nearest')[0] + lookforward_days
                if next_idx < len(historical_data):
                    current_price = row['close']
                    future_price = historical_data.iloc[next_idx]['close']
                    return_pct = (future_price - current_price) / current_price * 100
                    returns.append(return_pct)
            except (KeyError, IndexError) as e:
                logger.debug(f"Skipping invalid data point: {e}")
                continue
        
        if not returns:
            return {
                'pattern': pattern_name,
                'total_occurrences': len(pattern_occurrences),
                'error': 'No valid forward returns calculated'
            }
        
        returns = np.array(returns)
        
        # Statistical analysis
        win_rate = np.sum(returns > 0) / len(returns) * 100
        avg_return = np.mean(returns)
        median_return = np.median(returns)
        std_return = np.std(returns)
        
        # Distribution analysis
        percentiles = [5, 10, 25, 50, 75, 90, 95]
        return_percentiles = {f'p{p}': np.percentile(returns, p) for p in percentiles}
        
        # Risk metrics
        downside_returns = returns[returns < 0]
        upside_returns = returns[returns > 0]
        
        max_loss = np.min(returns) if len(returns) > 0 else 0
        max_gain = np.max(returns) if len(returns) > 0 else 0
        
        # Tail risks
        var_95 = np.percentile(returns, 5)  # 95% VaR
        cvar_95 = np.mean(returns[returns <= var_95]) if np.any(returns <= var_95) else var_95
        
        return {
            'pattern': pattern_name,
            'lookforward_days': lookforward_days,
            'analysis_date': now_iso(),
            
            # Sample statistics
            'total_occurrences': len(pattern_occurrences),
            'valid_returns': len(returns),
            
            # Central tendency
            'mean_return': round(avg_return, 3),
            'median_return': round(median_return, 3),
            'std_return': round(std_return, 3),
            
            # Success metrics
            'win_rate': round(win_rate, 1),
            'positive_returns': int(np.sum(returns > 0)),
            'negative_returns': int(np.sum(returns < 0)),
            'flat_returns': int(np.sum(returns == 0)),
            
            # Distribution
            'return_percentiles': {k: round(v, 3) for k, v in return_percentiles.items()},
            
            # Risk metrics
            'max_gain': round(max_gain, 3),
            'max_loss': round(max_loss, 3),
            'sharpe_ratio': round(avg_return / std_return, 3) if std_return > 0 else None,
            'value_at_risk_95': round(var_95, 3),
            'conditional_var_95': round(cvar_95, 3),
            
            # Return breakdown
            'avg_winning_return': round(np.mean(upside_returns), 3) if len(upside_returns) > 0 else 0,
            'avg_losing_return': round(np.mean(downside_returns), 3) if len(downside_returns) > 0 else 0,
            'win_loss_ratio': round(np.mean(upside_returns) / abs(np.mean(downside_returns)), 3) if len(downside_returns) > 0 and np.mean(downside_returns) != 0 else None
        }
    
    def calculate_conditional_probabilities(self, 
                                          historical_data: pd.DataFrame,
                                          pattern_names: List[str] = None) -> Dict:
        """
        P(profitable | pattern, confidence, fed_context)
        
        Args:
            historical_data: DataFrame with patterns, returns, and Fed context
            pattern_names: List of patterns to analyze (None = all patterns)
            
        Returns:
            Dictionary with conditional probability analysis
        """
        logger.info("Calculating conditional probabilities")
        
        if pattern_names is None:
            # Auto-detect pattern columns
            pattern_columns = [col for col in historical_data.columns 
                             if col.startswith('pattern_') or col in [
                                 'gamma_trap', 'gamma_flip', 'pin_risk', 
                                 'vol_squeeze', 'dealer_reload', 'liquidity_cascade'
                             ]]
            pattern_names = pattern_columns
        
        conditional_probs = {}
        
        for pattern in pattern_names:
            if pattern not in historical_data.columns:
                logger.warning(f"Pattern {pattern} not found in data")
                continue
            
            pattern_data = historical_data[historical_data[pattern] == True].copy()
            
            if len(pattern_data) < 5:
                logger.warning(f"Insufficient data for {pattern}: {len(pattern_data)} occurrences")
                continue
            
            # Calculate base probability
            base_prob = self._calculate_base_probability(pattern_data)
            
            # Calculate Fed context conditional probabilities
            fed_conditional = self._calculate_fed_conditional_probability(pattern_data)
            
            # Calculate confidence level conditional probabilities
            confidence_conditional = self._calculate_confidence_conditional_probability(pattern_data)
            
            # Calculate regime conditional probabilities
            regime_conditional = self._calculate_regime_conditional_probability(pattern_data)
            
            conditional_probs[pattern] = {
                'base_probability': base_prob,
                'fed_conditional': fed_conditional,
                'confidence_conditional': confidence_conditional,
                'regime_conditional': regime_conditional,
                'sample_size': len(pattern_data)
            }
        
        return {
            'analysis_date': now_iso(),
            'patterns_analyzed': len(conditional_probs),
            'conditional_probabilities': conditional_probs
        }
    
    def identify_high_conviction_setups(self, 
                                      conditional_probs: Dict,
                                      min_win_rate: float = 0.65,
                                      min_sample_size: int = 20) -> List[Dict]:
        """
        Find pattern + context combinations with >65% win rate.
        
        Args:
            conditional_probs: Output from calculate_conditional_probabilities
            min_win_rate: Minimum win rate threshold
            min_sample_size: Minimum sample size for reliability
            
        Returns:
            List of high conviction setups
        """
        logger.info(f"Identifying high conviction setups (win rate > {min_win_rate*100}%)")
        
        high_conviction = []
        
        for pattern, data in conditional_probs.get('conditional_probabilities', {}).items():
            
            # Check base probability first
            base_win_rate = data['base_probability'].get('win_rate', 0) / 100
            if base_win_rate >= min_win_rate and data['sample_size'] >= min_sample_size:
                high_conviction.append({
                    'pattern': pattern,
                    'setup_type': 'base',
                    'win_rate': base_win_rate,
                    'sample_size': data['sample_size'],
                    'avg_return': data['base_probability'].get('avg_return', 0),
                    'context': 'No additional context required'
                })
            
            # Check Fed context combinations
            for fed_context, fed_data in data.get('fed_conditional', {}).items():
                if isinstance(fed_data, dict):
                    fed_win_rate = fed_data.get('win_rate', 0) / 100
                    fed_sample_size = fed_data.get('sample_size', 0)
                    
                    if fed_win_rate >= min_win_rate and fed_sample_size >= min_sample_size // 2:
                        high_conviction.append({
                            'pattern': pattern,
                            'setup_type': 'fed_conditional',
                            'win_rate': fed_win_rate,
                            'sample_size': fed_sample_size,
                            'avg_return': fed_data.get('avg_return', 0),
                            'context': f'Fed context: {fed_context}'
                        })
            
            # Check confidence level combinations
            for conf_level, conf_data in data.get('confidence_conditional', {}).items():
                if isinstance(conf_data, dict):
                    conf_win_rate = conf_data.get('win_rate', 0) / 100
                    conf_sample_size = conf_data.get('sample_size', 0)
                    
                    if conf_win_rate >= min_win_rate and conf_sample_size >= min_sample_size // 2:
                        high_conviction.append({
                            'pattern': pattern,
                            'setup_type': 'confidence_conditional',
                            'win_rate': conf_win_rate,
                            'sample_size': conf_sample_size,
                            'avg_return': conf_data.get('avg_return', 0),
                            'context': f'Confidence level: {conf_level}'
                        })
        
        # Sort by win rate descending
        high_conviction.sort(key=lambda x: x['win_rate'], reverse=True)
        
        logger.info(f"Found {len(high_conviction)} high conviction setups")
        
        return high_conviction
    
    def _calculate_base_probability(self, pattern_data: pd.DataFrame) -> Dict:
        """Calculate base probability metrics for a pattern."""
        if 'forward_return' not in pattern_data.columns:
            logger.warning("forward_return column not found, attempting to calculate")
            return {'error': 'No forward return data available'}
        
        returns = pattern_data['forward_return'].dropna()
        
        if len(returns) == 0:
            return {'error': 'No valid return data'}
        
        win_rate = (returns > 0).sum() / len(returns) * 100
        avg_return = returns.mean()
        
        return {
            'win_rate': round(win_rate, 1),
            'avg_return': round(avg_return, 3),
            'sample_size': len(returns),
            'std_return': round(returns.std(), 3)
        }
    
    def _calculate_fed_conditional_probability(self, pattern_data: pd.DataFrame) -> Dict:
        """Calculate Fed context conditional probabilities."""
        fed_conditional = {}
        
        # Define Fed context categories
        fed_contexts = {
            'fomc_week': pattern_data.get('is_fomc_week', pd.Series(dtype=bool)),
            'blackout_period': pattern_data.get('in_blackout_period', pd.Series(dtype=bool)),
            'high_stress': pattern_data.get('stress_regime', pd.Series(dtype=str)) == 'elevated'
        }
        
        for context_name, context_filter in fed_contexts.items():
            if context_filter.empty or context_filter.isna().all():
                continue
                
            context_data = pattern_data[context_filter == True]
            if len(context_data) >= 5:  # Minimum sample size
                fed_conditional[context_name] = self._calculate_base_probability(context_data)
        
        return fed_conditional
    
    def _calculate_confidence_conditional_probability(self, pattern_data: pd.DataFrame) -> Dict:
        """Calculate confidence level conditional probabilities."""
        confidence_conditional = {}
        
        if 'pattern_confidence' not in pattern_data.columns:
            return confidence_conditional
        
        # Define confidence buckets
        confidence_buckets = {
            'high_confidence': pattern_data['pattern_confidence'] >= 80,
            'medium_confidence': (pattern_data['pattern_confidence'] >= 60) & (pattern_data['pattern_confidence'] < 80),
            'low_confidence': pattern_data['pattern_confidence'] < 60
        }
        
        for bucket_name, bucket_filter in confidence_buckets.items():
            bucket_data = pattern_data[bucket_filter]
            if len(bucket_data) >= 5:
                confidence_conditional[bucket_name] = self._calculate_base_probability(bucket_data)
        
        return confidence_conditional
    
    def _calculate_regime_conditional_probability(self, pattern_data: pd.DataFrame) -> Dict:
        """Calculate market regime conditional probabilities."""
        regime_conditional = {}
        
        if 'market_regime' not in pattern_data.columns:
            return regime_conditional
        
        # Group by market regime
        for regime in pattern_data['market_regime'].unique():
            if pd.isna(regime):
                continue
                
            regime_data = pattern_data[pattern_data['market_regime'] == regime]
            if len(regime_data) >= 5:
                regime_conditional[str(regime)] = self._calculate_base_probability(regime_data)
        
        return regime_conditional
    
    def generate_probability_report(self, 
                                   pattern_outcomes: Dict,
                                   conditional_probs: Dict,
                                   high_conviction: List[Dict],
                                   output_path: str = None) -> str:
        """
        Generate comprehensive probability analysis report.
        
        Args:
            pattern_outcomes: Output from analyze_pattern_outcomes
            conditional_probs: Output from calculate_conditional_probabilities  
            high_conviction: Output from identify_high_conviction_setups
            output_path: Custom output path (optional)
            
        Returns:
            Path to generated report
        """
        if output_path is None:
            timestamp = now_iso().replace(':', '-')
            output_path = self.cache_dir / f"pattern_probability_report_{timestamp}.txt"
        
        report_lines = [
            "=" * 80,
            "PATTERN PROBABILITY ANALYSIS REPORT",
            "=" * 80,
            f"Generated: {now_iso()}",
            f"Analysis Type: Pattern-Outcome Probability Mapping",
            "",
            "EXECUTIVE SUMMARY",
            "-" * 40
        ]
        
        # High conviction summary
        if high_conviction:
            report_lines.extend([
                f"High Conviction Setups Found: {len(high_conviction)}",
                f"Top Setup: {high_conviction[0]['pattern']} ({high_conviction[0]['win_rate']*100:.1f}% win rate)",
                ""
            ])
        else:
            report_lines.append("No high conviction setups identified")
            report_lines.append("")
        
        # Pattern outcomes summary
        if isinstance(pattern_outcomes, dict) and 'error' not in pattern_outcomes:
            report_lines.extend([
                "PATTERN OUTCOME ANALYSIS",
                "-" * 40,
                f"Pattern: {pattern_outcomes.get('pattern', 'Unknown')}",
                f"Total Occurrences: {pattern_outcomes.get('total_occurrences', 0)}",
                f"Valid Returns: {pattern_outcomes.get('valid_returns', 0)}",
                f"Win Rate: {pattern_outcomes.get('win_rate', 0)}%",
                f"Average Return: {pattern_outcomes.get('mean_return', 0)}%",
                f"Sharpe Ratio: {pattern_outcomes.get('sharpe_ratio', 'N/A')}",
                f"Max Gain: {pattern_outcomes.get('max_gain', 0)}%",
                f"Max Loss: {pattern_outcomes.get('max_loss', 0)}%",
                ""
            ])
        
        # High conviction details
        if high_conviction:
            report_lines.extend([
                "HIGH CONVICTION SETUPS",
                "-" * 40
            ])
            
            for i, setup in enumerate(high_conviction[:10], 1):  # Top 10
                report_lines.extend([
                    f"{i}. {setup['pattern'].upper()}",
                    f"   Win Rate: {setup['win_rate']*100:.1f}%",
                    f"   Average Return: {setup['avg_return']:.2f}%", 
                    f"   Sample Size: {setup['sample_size']}",
                    f"   Context: {setup['context']}",
                    ""
                ])
        
        # Conditional probability summary
        patterns_analyzed = conditional_probs.get('patterns_analyzed', 0)
        if patterns_analyzed > 0:
            report_lines.extend([
                "CONDITIONAL PROBABILITY ANALYSIS",
                "-" * 40,
                f"Patterns Analyzed: {patterns_analyzed}",
                ""
            ])
        
        report_lines.extend([
            "=" * 80,
            "End of Report"
        ])
        
        # Write report
        with open(output_path, 'w') as f:
            f.write('\n'.join(report_lines))
        
        logger.info(f"Pattern probability report saved to: {output_path}")
        return str(output_path)
    
    def export_results_json(self, 
                           pattern_outcomes: Dict,
                           conditional_probs: Dict,
                           high_conviction: List[Dict],
                           output_path: str = None) -> str:
        """Export analysis results as JSON for programmatic access."""
        if output_path is None:
            timestamp = now_iso().replace(':', '-')
            output_path = self.cache_dir / f"pattern_probability_data_{timestamp}.json"
        
        export_data = {
            'analysis_metadata': {
                'generated': now_iso(),
                'analysis_type': 'pattern_probability_mapping',
                'version': '1.0'
            },
            'pattern_outcomes': pattern_outcomes,
            'conditional_probabilities': conditional_probs,
            'high_conviction_setups': high_conviction
        }
        
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        logger.info(f"Pattern probability data exported to: {output_path}")
        return str(output_path)