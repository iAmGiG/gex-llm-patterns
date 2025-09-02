"""
Flip Point Detector - Gamma Flip Point Analysis

Identifies key price levels where dealer gamma exposure flips from positive 
to negative (or vice versa), creating critical support/resistance levels.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime
import logging
from scipy import interpolate
from scipy.optimize import brentq

logger = logging.getLogger(__name__)


class FlipPointDetector:
    """
    Detect gamma flip points where dealer positioning changes from 
    supportive to reactive (or vice versa).
    
    Flip points often act as critical support/resistance levels because
    they represent transitions in dealer hedging behavior.
    """
    
    def __init__(self, 
                 interpolation_method: str = 'cubic',
                 min_gex_threshold: float = 1000000):
        """
        Initialize Flip Point Detector.
        
        Args:
            interpolation_method: Method for GEX interpolation ('linear', 'cubic', 'quadratic')
            min_gex_threshold: Minimum absolute GEX to consider significant
        """
        self.interpolation_method = interpolation_method
        self.min_gex_threshold = min_gex_threshold
        
    def create_gex_interpolation(self, 
                               strike_gex: pd.DataFrame,
                               price_range: Tuple[float, float],
                               num_points: int = 1000) -> Tuple[np.ndarray, np.ndarray]:
        """
        Create interpolated GEX curve across price range.
        
        Args:
            strike_gex: DataFrame with strike and total_gex columns
            price_range: (min_price, max_price) for interpolation
            num_points: Number of interpolation points
            
        Returns:
            Tuple of (price_points, gex_values)
        """
        if strike_gex.empty or len(strike_gex) < 2:
            logger.warning("Insufficient data for GEX interpolation")
            return np.array([]), np.array([])
            
        # Filter strikes within reasonable range
        min_price, max_price = price_range
        valid_strikes = strike_gex[
            (strike_gex['strike'] >= min_price * 0.8) & 
            (strike_gex['strike'] <= max_price * 1.2)
        ].copy()
        
        if len(valid_strikes) < 2:
            logger.warning(f"Insufficient strikes in range {price_range}")
            return np.array([]), np.array([])
            
        # Sort by strike for interpolation
        valid_strikes = valid_strikes.sort_values('strike')
        
        try:
            # Create interpolation function
            if self.interpolation_method == 'linear':
                f_gex = interpolate.interp1d(
                    valid_strikes['strike'], 
                    valid_strikes['total_gex'],
                    kind='linear',
                    fill_value='extrapolate'
                )
            elif self.interpolation_method == 'cubic':
                if len(valid_strikes) >= 4:
                    f_gex = interpolate.interp1d(
                        valid_strikes['strike'], 
                        valid_strikes['total_gex'],
                        kind='cubic',
                        fill_value='extrapolate'
                    )
                else:
                    # Fall back to linear for insufficient points
                    f_gex = interpolate.interp1d(
                        valid_strikes['strike'], 
                        valid_strikes['total_gex'],
                        kind='linear',
                        fill_value='extrapolate'
                    )
            else:  # quadratic
                if len(valid_strikes) >= 3:
                    f_gex = interpolate.interp1d(
                        valid_strikes['strike'], 
                        valid_strikes['total_gex'],
                        kind='quadratic',
                        fill_value='extrapolate'
                    )
                else:
                    f_gex = interpolate.interp1d(
                        valid_strikes['strike'], 
                        valid_strikes['total_gex'],
                        kind='linear',
                        fill_value='extrapolate'
                    )
            
            # Generate interpolated points
            price_points = np.linspace(min_price, max_price, num_points)
            gex_values = f_gex(price_points)
            
            return price_points, gex_values
            
        except Exception as e:
            logger.error(f"Failed to create GEX interpolation: {e}")
            return np.array([]), np.array([])
    
    def find_zero_crossings(self, 
                           price_points: np.ndarray, 
                           gex_values: np.ndarray) -> List[float]:
        """
        Find price points where GEX crosses zero (flip points).
        
        Args:
            price_points: Array of price points
            gex_values: Corresponding GEX values
            
        Returns:
            List of flip point prices
        """
        if len(price_points) == 0 or len(gex_values) == 0:
            return []
            
        flip_points = []
        
        # Look for sign changes in GEX
        for i in range(len(gex_values) - 1):
            current_gex = gex_values[i]
            next_gex = gex_values[i + 1]
            
            # Check for zero crossing
            if (current_gex > 0 and next_gex < 0) or (current_gex < 0 and next_gex > 0):
                # Linear interpolation to find more precise crossing point
                current_price = price_points[i]
                next_price = price_points[i + 1]
                
                # Find exact crossing point using linear interpolation
                if abs(next_gex - current_gex) > 1e-10:  # Avoid division by zero
                    crossing_price = current_price - current_gex * (next_price - current_price) / (next_gex - current_gex)
                    flip_points.append(crossing_price)
        
        return flip_points
    
    def find_flip_points_analytical(self, strike_gex: pd.DataFrame) -> List[Dict]:
        """
        Find flip points using analytical approach between adjacent strikes.
        
        Args:
            strike_gex: DataFrame with strike and total_gex columns
            
        Returns:
            List of flip point information dictionaries
        """
        if strike_gex.empty or len(strike_gex) < 2:
            return []
            
        flip_points = []
        sorted_strikes = strike_gex.sort_values('strike')
        
        for i in range(len(sorted_strikes) - 1):
            current_row = sorted_strikes.iloc[i]
            next_row = sorted_strikes.iloc[i + 1]
            
            current_gex = current_row['total_gex']
            next_gex = next_row['total_gex']
            current_strike = current_row['strike']
            next_strike = next_row['strike']
            
            # Check for sign change
            if (current_gex > 0 and next_gex < 0) or (current_gex < 0 and next_gex > 0):
                # Linear interpolation for flip point
                if abs(next_gex - current_gex) > 1e-10:
                    flip_strike = current_strike - current_gex * (next_strike - current_strike) / (next_gex - current_gex)
                    
                    # Determine flip type
                    flip_type = "positive_to_negative" if current_gex > 0 else "negative_to_positive"
                    
                    flip_points.append({
                        'flip_price': flip_strike,
                        'flip_type': flip_type,
                        'left_strike': current_strike,
                        'right_strike': next_strike,
                        'left_gex': current_gex,
                        'right_gex': next_gex,
                        'gex_magnitude': abs(current_gex) + abs(next_gex)
                    })
        
        return flip_points
    
    def identify_significant_flip_points(self, 
                                       strike_gex: pd.DataFrame,
                                       underlying_price: float,
                                       price_range_pct: float = 0.15) -> List[Dict]:
        """
        Identify significant flip points near current price.
        
        Args:
            strike_gex: DataFrame with GEX by strike
            underlying_price: Current underlying price
            price_range_pct: Percentage range around current price to analyze
            
        Returns:
            List of significant flip points with analysis
        """
        logger.info(f"Identifying flip points around ${underlying_price:.2f}")
        
        if strike_gex.empty:
            return []
            
        # Define analysis range
        price_lower = underlying_price * (1 - price_range_pct)
        price_upper = underlying_price * (1 + price_range_pct)
        
        # Method 1: Analytical approach (more reliable)
        analytical_flips = self.find_flip_points_analytical(strike_gex)
        
        # Filter to price range
        relevant_flips = [
            flip for flip in analytical_flips 
            if price_lower <= flip['flip_price'] <= price_upper
        ]
        
        # Method 2: Interpolation approach (smoother, but less precise)
        price_points, gex_values = self.create_gex_interpolation(
            strike_gex, (price_lower, price_upper), num_points=2000
        )
        
        if len(price_points) > 0:
            interpolated_flips = self.find_zero_crossings(price_points, gex_values)
        else:
            interpolated_flips = []
        
        # Enhance analytical flips with additional metrics
        enhanced_flips = []
        for flip in relevant_flips:
            flip_price = flip['flip_price']
            
            # Calculate distance from current price
            price_distance = abs(flip_price - underlying_price)
            price_distance_pct = price_distance / underlying_price
            
            # Determine significance based on GEX magnitude and proximity
            gex_significance = min(flip['gex_magnitude'] / self.min_gex_threshold, 5.0)
            proximity_score = max(0, 1 - price_distance_pct / price_range_pct)
            significance_score = gex_significance * proximity_score
            
            enhanced_flip = {
                **flip,
                'distance_from_price': price_distance,
                'distance_pct': price_distance_pct,
                'proximity_score': proximity_score,
                'gex_significance': gex_significance,
                'significance_score': significance_score,
                'underlying_price': underlying_price
            }
            
            enhanced_flips.append(enhanced_flip)
        
        # Sort by significance score
        enhanced_flips.sort(key=lambda x: x['significance_score'], reverse=True)
        
        # Add interpolation flip points for reference
        for interp_flip in interpolated_flips:
            if price_lower <= interp_flip <= price_upper:
                # Check if this interpolation flip is close to an analytical flip
                is_duplicate = any(
                    abs(interp_flip - flip['flip_price']) < underlying_price * 0.005 
                    for flip in enhanced_flips
                )
                
                if not is_duplicate:
                    enhanced_flips.append({
                        'flip_price': interp_flip,
                        'flip_type': 'interpolated',
                        'method': 'interpolation',
                        'distance_from_price': abs(interp_flip - underlying_price),
                        'distance_pct': abs(interp_flip - underlying_price) / underlying_price,
                        'significance_score': 0.5  # Lower significance for interpolated
                    })
        
        return enhanced_flips
    
    def analyze_flip_point_environment(self, 
                                     flip_points: List[Dict],
                                     underlying_price: float) -> Dict:
        """
        Analyze the overall flip point environment for trading insights.
        
        Args:
            flip_points: List of flip point dictionaries
            underlying_price: Current underlying price
            
        Returns:
            Dictionary with environmental analysis
        """
        if not flip_points:
            return {
                'environment': 'no_flip_points',
                'nearest_flip': None,
                'support_levels': [],
                'resistance_levels': [],
                'trading_range': None
            }
        
        # Find nearest flip points above and below current price
        below_price = [fp for fp in flip_points if fp['flip_price'] < underlying_price]
        above_price = [fp for fp in flip_points if fp['flip_price'] > underlying_price]
        
        nearest_support = max(below_price, key=lambda x: x['flip_price']) if below_price else None
        nearest_resistance = min(above_price, key=lambda x: x['flip_price']) if above_price else None
        
        # Determine market environment
        if nearest_support and nearest_resistance:
            range_size = nearest_resistance['flip_price'] - nearest_support['flip_price']
            range_pct = range_size / underlying_price
            
            if range_pct < 0.02:  # Very tight range
                environment = 'tight_range'
            elif range_pct < 0.05:  # Normal range
                environment = 'range_bound'
            else:  # Wide range
                environment = 'wide_range'
        elif nearest_support:
            environment = 'above_support'
        elif nearest_resistance:
            environment = 'below_resistance'
        else:
            environment = 'no_nearby_flips'
        
        # Identify significant support/resistance levels
        support_levels = sorted(
            [fp for fp in below_price if fp.get('significance_score', 0) > 0.5],
            key=lambda x: x['flip_price'],
            reverse=True
        )[:3]  # Top 3 support levels
        
        resistance_levels = sorted(
            [fp for fp in above_price if fp.get('significance_score', 0) > 0.5],
            key=lambda x: x['flip_price']
        )[:3]  # Top 3 resistance levels
        
        return {
            'environment': environment,
            'nearest_support': nearest_support,
            'nearest_resistance': nearest_resistance,
            'support_levels': support_levels,
            'resistance_levels': resistance_levels,
            'trading_range': {
                'support': nearest_support['flip_price'] if nearest_support else None,
                'resistance': nearest_resistance['flip_price'] if nearest_resistance else None,
                'range_size': range_size if nearest_support and nearest_resistance else None,
                'range_pct': range_pct if nearest_support and nearest_resistance else None
            },
            'total_flip_points': len(flip_points)
        }