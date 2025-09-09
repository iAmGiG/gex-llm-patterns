"""
GEX Validator Module

Validation framework for Gamma Exposure (GEX) calculations.
Provides sanity checks and reference comparison capabilities.
"""

import logging


class GEXValidator:
    """
    Validate GEX calculations for accuracy and reasonableness.
    
    Provides both reference comparison validation and sanity checking
    to ensure GEX calculations are mathematically sound and realistic.
    """
    
    def __init__(self, reference_source="SpotGamma"):
        """
        Initialize GEX validator.
        
        Args:
            reference_source: Name of reference data source for validation
        """
        self.reference_source = reference_source
        self.logger = logging.getLogger(__name__)
    
    def validate_against_reference(self, our_gex, reference_gex, tolerance=0.1):
        """
        Validate our GEX calculations against known reference data.
        
        Args:
            our_gex: Our calculated GEX metrics
            reference_gex: Reference GEX metrics for comparison
            tolerance: Acceptable difference percentage (0.1 = 10%)
            
        Returns:
            Dictionary with validation results
        """
        gex_diff_pct = abs(our_gex['total_gex'] - reference_gex['total_gex']) / abs(reference_gex['total_gex'])
        
        if our_gex['gamma_flip'] and reference_gex['gamma_flip']:
            flip_diff_pct = abs(our_gex['gamma_flip'] - reference_gex['gamma_flip']) / reference_gex['gamma_flip']
        else:
            flip_diff_pct = 0 if our_gex['gamma_flip'] == reference_gex['gamma_flip'] else 1
        
        validation_result = {
            'total_gex_match': gex_diff_pct < tolerance,
            'gamma_flip_match': flip_diff_pct < tolerance,
            'gex_difference_pct': gex_diff_pct,
            'flip_difference_pct': flip_diff_pct,
            'overall_valid': (gex_diff_pct < tolerance) and (flip_diff_pct < tolerance),
            'reference_source': self.reference_source
        }
        
        return validation_result
    
    def validate_calculation_sanity(self, gex_data):
        """
        Perform sanity checks on GEX calculations.
        
        Args:
            gex_data: Dictionary with GEX calculation results
            
        Returns:
            Dictionary with sanity check results
        """
        checks = []
        
        if gex_data.get('gamma_flip') and gex_data.get('spot_price'):
            flip_distance = abs(gex_data['gamma_flip'] - gex_data['spot_price']) / gex_data['spot_price']
            checks.append({
                'check': 'gamma_flip_reasonable',
                'passed': flip_distance < 0.1,
                'value': flip_distance,
                'description': 'Gamma flip should be within 10% of current price'
            })
        
        if gex_data.get('call_wall') and gex_data.get('spot_price'):
            call_wall_above = gex_data['call_wall'] > gex_data['spot_price']
            checks.append({
                'check': 'call_wall_above_spot',
                'passed': call_wall_above,
                'value': gex_data['call_wall'] - gex_data['spot_price'],
                'description': 'Call wall should typically be above current price'
            })
        
        if gex_data.get('put_support') and gex_data.get('spot_price'):
            put_support_below = gex_data['put_support'] < gex_data['spot_price']
            checks.append({
                'check': 'put_support_below_spot',
                'passed': put_support_below,
                'value': gex_data['spot_price'] - gex_data['put_support'],
                'description': 'Put support should typically be below current price'
            })
        
        if gex_data.get('total_gex') is not None:
            gex_magnitude = abs(gex_data['total_gex'])
            reasonable_magnitude = 1e8 < gex_magnitude < 1e12
            checks.append({
                'check': 'reasonable_gex_magnitude',
                'passed': reasonable_magnitude,
                'value': gex_magnitude,
                'description': 'Total GEX should be between $100M and $1T'
            })
        
        if gex_data.get('strikes_detail'):
            self._validate_strikes_detail(gex_data['strikes_detail'], checks)
        
        return {
            'all_checks_passed': all(check['passed'] for check in checks),
            'individual_checks': checks,
            'validation_score': sum(check['passed'] for check in checks) / len(checks) if checks else 0,
            'total_checks': len(checks)
        }
    
    def _validate_strikes_detail(self, strikes_detail, checks):
        """Validate individual strike-level calculations."""
        if not strikes_detail:
            return
        
        total_strikes = len(strikes_detail)
        gamma_sum = sum(abs(data.get('gamma', 0)) for data in strikes_detail.values())
        
        checks.append({
            'check': 'strikes_have_gamma',
            'passed': gamma_sum > 0,
            'value': gamma_sum,
            'description': 'At least some strikes should have positive gamma'
        })
        
        gex_values = [data.get('total_gex', 0) for data in strikes_detail.values()]
        non_zero_gex = sum(1 for gex in gex_values if abs(gex) > 1000)
        
        checks.append({
            'check': 'meaningful_gex_distribution',
            'passed': non_zero_gex > total_strikes * 0.1,
            'value': non_zero_gex / total_strikes if total_strikes > 0 else 0,
            'description': 'At least 10% of strikes should have meaningful GEX'
        })
    
    def validate_time_series_consistency(self, gex_history):
        """
        Validate consistency across a time series of GEX calculations.
        
        Args:
            gex_history: List of GEX calculation results over time
            
        Returns:
            Dictionary with time series validation results
        """
        if len(gex_history) < 2:
            return {
                'consistent': True,
                'message': 'Insufficient data for time series validation',
                'checks': []
            }
        
        checks = []
        
        total_gex_values = [data.get('total_gex', 0) for data in gex_history]
        
        max_daily_change = 0
        for i in range(1, len(total_gex_values)):
            if total_gex_values[i-1] != 0:
                daily_change = abs((total_gex_values[i] - total_gex_values[i-1]) / total_gex_values[i-1])
                max_daily_change = max(max_daily_change, daily_change)
        
        checks.append({
            'check': 'reasonable_daily_changes',
            'passed': max_daily_change < 2.0,
            'value': max_daily_change,
            'description': 'Daily GEX changes should be less than 200%'
        })
        
        flip_points = [data.get('gamma_flip') for data in gex_history if data.get('gamma_flip')]
        if len(flip_points) > 1:
            flip_volatility = self._calculate_volatility(flip_points)
            checks.append({
                'check': 'stable_gamma_flip',
                'passed': flip_volatility < 0.1,
                'value': flip_volatility,
                'description': 'Gamma flip point should be relatively stable'
            })
        
        return {
            'consistent': all(check['passed'] for check in checks),
            'individual_checks': checks,
            'validation_score': sum(check['passed'] for check in checks) / len(checks) if checks else 1
        }
    
    def _calculate_volatility(self, values):
        """Calculate volatility of a list of values."""
        if len(values) < 2:
            return 0
        
        mean_val = sum(values) / len(values)
        variance = sum((x - mean_val) ** 2 for x in values) / len(values)
        return (variance ** 0.5) / mean_val if mean_val != 0 else 0
    
    def generate_validation_report(self, validation_results):
        """
        Generate a human-readable validation report.
        
        Args:
            validation_results: Results from validation methods
            
        Returns:
            Formatted validation report string
        """
        report = []
        report.append("=== GEX Validation Report ===\n")
        
        if 'all_checks_passed' in validation_results:
            status = "✅ PASSED" if validation_results['all_checks_passed'] else "❌ FAILED"
            score = validation_results.get('validation_score', 0) * 100
            report.append(f"Overall Status: {status} ({score:.1f}% checks passed)")
            report.append(f"Total Checks: {validation_results.get('total_checks', 0)}\n")
            
            for check in validation_results.get('individual_checks', []):
                status_icon = "✅" if check['passed'] else "❌"
                report.append(f"{status_icon} {check['check']}: {check['description']}")
                if 'value' in check:
                    report.append(f"   Value: {check['value']}")
        
        if 'reference_source' in validation_results:
            report.append(f"\nReference Source: {validation_results['reference_source']}")
            
        return "\n".join(report)