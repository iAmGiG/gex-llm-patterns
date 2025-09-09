"""
GEX Calculator Module

Core Gamma Exposure (GEX) calculations for options market making analysis.
Implements Black-Scholes gamma calculations and dealer position analysis.
"""

import numpy as np
from datetime import datetime, date
from scipy.stats import norm


class GEXCalculator:
    """
    Calculate Gamma Exposure (GEX) metrics for options chains.
    
    GEX quantifies the dollar amount of gamma exposure dealers have from 
    options market making, which influences their hedging behavior.
    """
    
    def __init__(self, risk_free_rate=0.05):
        """
        Initialize GEX calculator.
        
        Args:
            risk_free_rate: Risk-free interest rate for Black-Scholes calculations
        """
        self.risk_free_rate = risk_free_rate
    
    def calculate_gamma(self, S, K, T, r, sigma):
        """
        Calculate option gamma using Black-Scholes formula.
        
        Args:
            S: Spot price
            K: Strike price
            T: Time to expiration (years)
            r: Risk-free rate
            sigma: Implied volatility
            
        Returns:
            Option gamma (same for calls and puts)
        """
        if T <= 0 or sigma <= 0:
            return 0.0
            
        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
        
        return gamma
    
    def calculate_strike_gex(self, spot_price, strike, time_to_expiry, 
                           implied_vol, call_oi, put_oi):
        """
        Calculate GEX for a single strike.
        
        Args:
            spot_price: Current underlying price
            strike: Option strike price
            time_to_expiry: Time to expiration in years
            implied_vol: Implied volatility
            call_oi: Call open interest
            put_oi: Put open interest
            
        Returns:
            Dictionary with strike GEX breakdown
        """
        gamma = self.calculate_gamma(
            S=spot_price,
            K=strike,
            T=time_to_expiry,
            r=self.risk_free_rate,
            sigma=implied_vol
        )
        
        call_gex = spot_price * gamma * call_oi * 100 * 0.01
        put_gex = -spot_price * gamma * put_oi * 100 * 0.01
        total_gex = call_gex + put_gex
        
        return {
            'strike': strike,
            'gamma': gamma,
            'call_gex': call_gex,
            'put_gex': put_gex,
            'total_gex': total_gex
        }
    
    def find_gamma_flip_point(self, gex_by_strike):
        """
        Find where total GEX crosses zero (gamma flip point).
        
        Args:
            gex_by_strike: Dictionary of strike -> GEX data
            
        Returns:
            Gamma flip point price, or None if not found
        """
        strikes = sorted(gex_by_strike.keys())
        
        for i in range(len(strikes) - 1):
            current_strike = strikes[i]
            next_strike = strikes[i + 1]
            
            current_gex = gex_by_strike[current_strike]['total_gex']
            next_gex = gex_by_strike[next_strike]['total_gex']
            
            if current_gex * next_gex < 0:
                flip_point = current_strike + (next_strike - current_strike) * (
                    -current_gex / (next_gex - current_gex)
                )
                return flip_point
        
        return None
    
    def identify_key_levels(self, gex_by_strike, top_n=5):
        """
        Identify critical GEX levels (call wall, put support, etc).
        
        Args:
            gex_by_strike: Dictionary of strike -> GEX data
            top_n: Number of top gamma strikes to return
            
        Returns:
            Dictionary with key levels identified
        """
        call_levels = {k: v['call_gex'] for k, v in gex_by_strike.items() 
                      if v['call_gex'] > 0}
        put_levels = {k: abs(v['put_gex']) for k, v in gex_by_strike.items() 
                     if v['put_gex'] < 0}
        
        call_wall = max(call_levels.items(), key=lambda x: x[1])[0] if call_levels else None
        put_support = max(put_levels.items(), key=lambda x: x[1])[0] if put_levels else None
        
        high_gamma_strikes = sorted(
            gex_by_strike.keys(),
            key=lambda k: abs(gex_by_strike[k]['total_gex']),
            reverse=True
        )[:top_n]
        
        return {
            'call_wall': call_wall,
            'put_support': put_support,
            'high_gamma_strikes': high_gamma_strikes,
            'gamma_flip': self.find_gamma_flip_point(gex_by_strike)
        }
    
    def classify_gex_regime(self, total_gex, gamma_flip, current_price):
        """
        Classify current market regime based on GEX.
        
        Args:
            total_gex: Total gamma exposure
            gamma_flip: Gamma flip point price
            current_price: Current underlying price
            
        Returns:
            Dictionary with regime classification and behavior
        """
        if total_gex > 1e9:
            regime = "POSITIVE_GAMMA_HIGH"
            behavior = "Dealers buy dips, sell rallies (stabilizing)"
        elif total_gex > 0:
            regime = "POSITIVE_GAMMA_LOW"
            behavior = "Mild dealer stabilization"
        elif total_gex > -1e9:
            regime = "NEGATIVE_GAMMA_LOW"
            behavior = "Mild dealer amplification"
        else:
            regime = "NEGATIVE_GAMMA_HIGH"
            behavior = "Dealers sell dips, buy rallies (destabilizing)"
        
        distance_to_flip = None
        if gamma_flip and current_price:
            distance_to_flip = (current_price - gamma_flip) / gamma_flip
            if abs(distance_to_flip) < 0.02:
                regime += "_NEAR_FLIP"
                behavior += " - NEAR GAMMA FLIP (unstable)"
        
        return {
            'regime': regime,
            'behavior': behavior,
            'total_gex': total_gex,
            'distance_to_flip': distance_to_flip
        }
    
    def calculate_daily_gex_metrics(self, options_chain, spot_price, expiration_dates=None):
        """
        Calculate comprehensive daily GEX metrics.
        
        Args:
            options_chain: DataFrame with options data
            spot_price: Current underlying price
            expiration_dates: List of expiration dates to process
            
        Returns:
            Dictionary with complete daily GEX analysis
        """
        all_strikes = {}
        
        if expiration_dates is None:
            expiration_dates = options_chain['expiration'].unique() if 'expiration' in options_chain.columns else []
        
        for exp_date in expiration_dates:
            time_to_expiry = self._calculate_time_to_expiry(exp_date)
            
            exp_chain = options_chain[options_chain['expiration'] == exp_date] if 'expiration' in options_chain.columns else options_chain
            
            for _, row in exp_chain.iterrows():
                strike = row['strike']
                
                strike_gex = self.calculate_strike_gex(
                    spot_price=spot_price,
                    strike=strike,
                    time_to_expiry=time_to_expiry,
                    implied_vol=row.get('implied_vol', 0.2),
                    call_oi=row.get('call_oi', 0),
                    put_oi=row.get('put_oi', 0)
                )
                
                if strike not in all_strikes:
                    all_strikes[strike] = {
                        'total_gex': 0,
                        'call_gex': 0,
                        'put_gex': 0,
                        'gamma': 0
                    }
                
                all_strikes[strike]['total_gex'] += strike_gex['total_gex']
                all_strikes[strike]['call_gex'] += strike_gex['call_gex']
                all_strikes[strike]['put_gex'] += strike_gex['put_gex']
                all_strikes[strike]['gamma'] += strike_gex['gamma']
        
        total_gex = sum(s['total_gex'] for s in all_strikes.values())
        key_levels = self.identify_key_levels(all_strikes)
        regime = self.classify_gex_regime(total_gex, key_levels['gamma_flip'], spot_price)
        
        return {
            'date': datetime.now().date(),
            'spot_price': spot_price,
            'total_gex': total_gex,
            'gamma_flip': key_levels['gamma_flip'],
            'call_wall': key_levels['call_wall'],
            'put_support': key_levels['put_support'],
            'high_gamma_strikes': key_levels['high_gamma_strikes'],
            'regime': regime['regime'],
            'regime_behavior': regime['behavior'],
            'strikes_detail': all_strikes
        }
    
    def calculate_gex_vectorized(self, options_df, spot_price):
        """
        Vectorized GEX calculation for performance with large datasets.
        
        Args:
            options_df: DataFrame with options data
            spot_price: Current underlying price
            
        Returns:
            DataFrame with GEX calculations added
        """
        S = spot_price
        K = options_df['strike'].values
        T = options_df.get('time_to_expiry', 0.25).values
        r = self.risk_free_rate
        sigma = options_df.get('implied_vol', 0.2).values
        
        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
        
        call_gex = S * gamma * options_df.get('call_oi', 0).values * 100 * 0.01
        put_gex = -S * gamma * options_df.get('put_oi', 0).values * 100 * 0.01
        total_gex = call_gex + put_gex
        
        results_df = options_df.copy()
        results_df['gamma'] = gamma
        results_df['call_gex'] = call_gex
        results_df['put_gex'] = put_gex
        results_df['total_gex'] = total_gex
        
        return results_df
    
    def _calculate_time_to_expiry(self, expiration_date):
        """Calculate time to expiry in years."""
        if isinstance(expiration_date, str):
            exp_date = datetime.strptime(expiration_date, '%Y-%m-%d').date()
        elif isinstance(expiration_date, datetime):
            exp_date = expiration_date.date()
        else:
            exp_date = expiration_date
        
        today = date.today()
        days_to_expiry = (exp_date - today).days
        return max(days_to_expiry / 365.0, 1/365.0)