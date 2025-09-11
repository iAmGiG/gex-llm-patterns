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
        Calculate comprehensive daily GEX metrics with three-metric approach.
        
        Args:
            options_chain: DataFrame with options data
            spot_price: Current underlying price
            expiration_dates: List of expiration dates to process
            
        Returns:
            Dictionary with complete daily GEX analysis including:
            - Net GEX for regime identification
            - Strike-level GEX for support/resistance
            - GEX flip point for directional bias
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
        
        # METRIC 1: Net GEX - for regime identification
        total_gex = sum(s['total_gex'] for s in all_strikes.values())
        notional_gex = total_gex * spot_price * 0.01  # SpotGamma style
        
        # METRIC 2: Strike-level GEX - for support/resistance
        key_levels = self.identify_key_levels(all_strikes)
        
        # Get top 5 strikes by absolute GEX for granular analysis
        top_5_strikes = sorted(
            all_strikes.items(),
            key=lambda x: abs(x[1]['total_gex']),
            reverse=True
        )[:5]
        
        strike_profile = {
            strike: {
                'gex': data['total_gex'],
                'notional_gex': data['total_gex'] * spot_price * 0.01
            }
            for strike, data in top_5_strikes
        }
        
        # METRIC 3: GEX Flip Point - for directional bias
        flip_point = key_levels['gamma_flip']
        if flip_point is not None:
            flip_bias = 'bearish' if spot_price > flip_point else 'bullish'
        else:
            flip_bias = 'neutral'
        
        regime = self.classify_gex_regime(total_gex, flip_point, spot_price)
        
        return {
            'date': datetime.now().date(),
            'spot_price': spot_price,
            # Three core metrics for backtesting
            'net_gex': total_gex,
            'notional_gex': notional_gex,
            'strike_profile': strike_profile,
            'flip_point': flip_point,
            'flip_bias': flip_bias,
            # Supporting data
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
    
    def detect_patterns(self, gex_data, price_data, context=None):
        """
        Detect six key GEX patterns for trading signals.
        
        Args:
            gex_data: Dictionary from calculate_daily_gex_metrics
            price_data: Dictionary with price information
            context: Optional dictionary with additional context (FOMC dates, OpEx, etc.)
            
        Returns:
            List of detected patterns with confidence scores
        """
        patterns = []
        context = context or {}
        
        net_gex = gex_data['net_gex']
        spot_price = gex_data['spot_price']
        flip_point = gex_data['flip_point']
        high_gamma_strikes = gex_data['high_gamma_strikes']
        
        # 1. GAMMA TRAP: Price approaching negative GEX strike
        if net_gex < 0 and high_gamma_strikes:
            nearest_strike = min(high_gamma_strikes, key=lambda x: abs(x - spot_price))
            distance_pct = abs(spot_price - nearest_strike) / spot_price * 100
            if distance_pct < 1:  # Within 1% of high gamma strike
                confidence = min(90, 100 - distance_pct * 10)
                patterns.append({
                    'pattern': 'gamma_trap',
                    'confidence': confidence,
                    'details': f'Price within {distance_pct:.2f}% of high gamma strike {nearest_strike}'
                })
        
        # 2. GAMMA FLIP: Price crossing zero-gamma level
        if flip_point:
            distance_to_flip = abs(spot_price - flip_point) / spot_price * 100
            if distance_to_flip < 0.5:  # Within 0.5% of flip point
                confidence = min(95, 100 - distance_to_flip * 20)
                patterns.append({
                    'pattern': 'gamma_flip',
                    'confidence': confidence,
                    'details': f'Price {distance_to_flip:.2f}% from flip point at {flip_point}'
                })
        
        # 3. PIN RISK: OpEx with massive OI at current price
        if context.get('is_opex', False):
            if high_gamma_strikes:
                atm_strike = min(high_gamma_strikes, key=lambda x: abs(x - spot_price))
                if abs(atm_strike - spot_price) / spot_price < 0.01:  # Within 1%
                    patterns.append({
                        'pattern': 'pin_risk',
                        'confidence': 85,
                        'details': f'OpEx pin risk at strike {atm_strike}'
                    })
        
        # 4. VOLATILITY SQUEEZE: GEX compression before event
        if context.get('upcoming_fomc', False):
            # Check if GEX is in low percentile (would need historical data)
            if abs(net_gex) < 1e9:  # Low absolute GEX
                patterns.append({
                    'pattern': 'vol_squeeze',
                    'confidence': 75,
                    'details': 'Low GEX before FOMC event'
                })
        
        # Enhanced FOMC context from Fed integration
        if context.get('days_to_fomc') is not None:
            days_to_fomc = context['days_to_fomc']
            if 1 <= days_to_fomc <= 7 and abs(net_gex) < 5e8:
                patterns.append({
                    'pattern': 'vol_squeeze',
                    'confidence': 80,
                    'details': f'Pre-FOMC volatility compression ({days_to_fomc} days to FOMC)'
                })
        
        # 5. DEALER RELOAD: Post-expiry positioning rebuild
        if context.get('days_after_opex', 0) <= 2 and context.get('days_after_opex', 0) > 0:
            if context.get('gex_change_pct', 0) > 20:  # Significant GEX change
                patterns.append({
                    'pattern': 'dealer_reload',
                    'confidence': 80,
                    'details': f"Dealer repositioning {context['days_after_opex']} days post-OpEx"
                })
        
        # 6. LIQUIDITY CASCADE: Negative GEX + technical levels
        if net_gex < 0:
            if context.get('near_technical_level', False):
                patterns.append({
                    'pattern': 'liquidity_cascade',
                    'confidence': 70,
                    'details': 'Negative gamma near technical level'
                })
        
        return patterns
    
    def prepare_backtest_data(self, options_chain, spot_price):
        """
        Prepare GEX data optimized for backtesting strategies.
        
        Args:
            options_chain: Options chain data
            spot_price: Current spot price
            
        Returns:
            Dictionary with key metrics for backtesting
        """
        metrics = self.calculate_daily_gex_metrics(options_chain, spot_price)
        
        return {
            # Core signals
            'net_gex': metrics['net_gex'],
            'notional_gex': metrics['notional_gex'],
            'regime': metrics['regime'],
            
            # Support/Resistance levels
            'call_wall': metrics['call_wall'],
            'put_support': metrics['put_support'],
            'key_levels': metrics['high_gamma_strikes'][:5] if metrics['high_gamma_strikes'] else [],
            
            # Flip point analysis
            'flip_point': metrics['flip_point'],
            'above_flip': spot_price > metrics['flip_point'] if metrics['flip_point'] else None,
            'flip_bias': metrics['flip_bias'],
            
            # Risk metrics
            'is_negative_gamma': metrics['net_gex'] < 0,
            'is_extreme_gamma': abs(metrics['net_gex']) > 5e9,
            'near_flip': abs(spot_price - metrics['flip_point']) / spot_price < 0.02 if metrics['flip_point'] else False,
            
            # Strike profile for entry/exit
            'strike_profile': metrics['strike_profile']
        }