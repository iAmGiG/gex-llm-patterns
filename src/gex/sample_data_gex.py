"""
GEX Calculation Interface for Sample Data
Bridges Alpha Vantage sample data with the existing GEX calculation engine.

NOTE: This module uses sample_data/ directory for testing purposes only.
      Production data will be stored in the .cache/ directory structure
      when proper data streaming is implemented.
      The sample data location will need to be updated to use .cache/
      once we have a live data pipeline.
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from data_sources.sample_data_loader import AlphaVantageSampleLoader, SampleDataProvider
from validation.options_data_validator import OptionsDataValidator
from gex.gex_calculator import GEXCalculator

logger = logging.getLogger(__name__)


class SampleDataGEXInterface:
    """
    Interface for calculating GEX from Alpha Vantage sample data.
    Connects sample data loader -> validator -> GEX calculator.
    """
    
    def __init__(self, 
                 sample_file= None,
                 risk_free_rate = 0.05,
                 validate_data = True):
        """
        Initialize the GEX interface.
        
        Args:
            sample_file: Path to sample data file
            risk_free_rate: Risk-free rate for Black-Scholes calculations
            validate_data: Whether to validate data before GEX calculations
        """
        self.loader = AlphaVantageSampleLoader(sample_file)
        self.provider = SampleDataProvider(self.loader)
        self.validator = OptionsDataValidator(strict_mode=False)
        self.gex_calculator = GEXCalculator(risk_free_rate=risk_free_rate)
        self.validate_data = validate_data
        
        # Cache for processed data
        self._processed_cache = {}
        
    def calculate_gex_for_symbol(self, 
                                 symbol,
                                 date= None,
                                 spot_price= None) :
        """
        Calculate complete GEX metrics for a symbol.
        
        Args:
            symbol: Stock symbol
            date: Options date (uses latest if None)
            spot_price: Current spot price (auto-detects if None)
        
        Returnsionary containing:
            - total_gex: Net gamma exposure
            - call_gex: Call gamma exposure
            - put_gex: Put gamma exposure
            - net_gex: Net exposure (calls - puts)
            - gex_by_strike: GEX breakdown by strike
            - flip_point: Zero gamma flip point
            - peak_gamma_strike: Strike with highest gamma
            - summary_stats: Additional metrics
        """
        cache_key = f"{symbol}_{date}_{spot_price}"
        if cache_key in self._processed_cache:
            logger.info(f"Using cached GEX for {cache_key}")
            return self._processed_cache[cache_key]
        
        # Load options data
        logger.info(f"Loading options data for {symbol} on {date}")
        options_df = self.provider.fetch_options_data(symbol, date)
        
        if options_df.empty:
            logger.warning(f"No options data found for {symbol} on {date}")
            return self._empty_gex_result()
        
        # Validate data if requested
        if self.validate_data:
            logger.info("Validating options data")
            options_df, validation_report = self.validator.validate(options_df)
            
            if validation_report['dropped_rows'] > 0:
                logger.warning(
                    f"Dropped {validation_report['dropped_rows']} invalid rows"
                )
        
        # Auto-detect spot price if not provided
        if spot_price is None:
            spot_price = self._estimate_spot_price(options_df)
            logger.info(f"Estimated spot price: ${spot_price:.2f}")
        
        # Calculate GEX components
        results = {
            'symbol': symbol,
            'date': date or options_df['date'].max().strftime('%Y-%m-%d'),
            'spot_price': spot_price,
            'total_contracts': len(options_df)
        }
        
        # Separate calls and puts
        calls_df = options_df[options_df['type'] == 'call']
        puts_df = options_df[options_df['type'] == 'put']
        
        # Calculate GEX for each type
        results['call_gex'] = self._calculate_type_gex(calls_df, 'call', spot_price)
        results['put_gex'] = self._calculate_type_gex(puts_df, 'put', spot_price)
        
        # Net GEX (dealer perspective: calls positive, puts negative)
        results['net_gex'] = results['call_gex'] - abs(results['put_gex'])
        results['total_gex'] = abs(results['call_gex']) + abs(results['put_gex'])
        
        # GEX by strike
        results['gex_by_strike'] = self._calculate_gex_by_strike(
            options_df, spot_price
        )
        
        # Find key levels
        results['flip_point'] = self._find_flip_point(results['gex_by_strike'])
        results['peak_gamma_strike'] = self._find_peak_gamma_strike(options_df)
        
        # Summary statistics
        results['summary_stats'] = self._calculate_summary_stats(
            options_df, results
        )
        
        # Cache results
        self._processed_cache[cache_key] = results
        
        return results
    
    def _calculate_type_gex(self, 
                           df, 
                           option_type,
                           spot_price) -> float:
        """
        Calculate GEX for calls or puts.
        
        Args:
            df: DataFrame with single option type
            option_type: 'call' or 'put'
            spot_price: Current spot price
        
        Returns:
            Total GEX for the option type
        """
        if df.empty:
            return 0.0
        
        total_gex = 0.0
        
        for _, row in df.iterrows():
            # GEX = Gamma * Open Interest * 100 * Spot^2 / 100
            # The 100 factor is for contract multiplier
            gex = row['gamma'] * row['open_interest'] * 100 * (spot_price ** 2) / 100
            
            # Adjust sign for dealer perspective
            if option_type == 'put':
                gex = -gex  # Dealers are short gamma on puts
            
            total_gex += gex
        
        return total_gex
    
    def _calculate_gex_by_strike(self, 
                                 df,
                                 spot_price) :
        """
        Calculate GEX grouped by strike price.
        
        Args:
            df: Options DataFrame
            spot_price: Current spot price
        
        Returns:
            DataFrame with GEX by strike
        """
        gex_by_strike = []
        
        for strike in df['strike'].unique():
            strike_df = df[df['strike'] == strike]
            
            call_gex = self._calculate_type_gex(
                strike_df[strike_df['type'] == 'call'], 'call', spot_price
            )
            put_gex = self._calculate_type_gex(
                strike_df[strike_df['type'] == 'put'], 'put', spot_price
            )
            
            gex_by_strike.append({
                'strike': strike,
                'call_gex': call_gex,
                'put_gex': put_gex,
                'net_gex': call_gex + put_gex,  # put_gex is already negative
                'total_gex': abs(call_gex) + abs(put_gex)
            })
        
        return pd.DataFrame(gex_by_strike).sort_values('strike')
    
    def _estimate_spot_price(self, df) -> float:
        """
        Estimate spot price from options data.
        
        Uses the strike where put-call parity is closest to satisfied,
        or the strike with maximum open interest.
        
        Args:
            df: Options DataFrame
        
        Returns:
            Estimated spot price
        """
        # Method 1: ATM strike (where call delta ≈ 0.5)
        calls = df[df['type'] == 'call']
        if not calls.empty and 'delta' in calls.columns:
            atm_calls = calls[abs(calls['delta'] - 0.5) < 0.1]
            if not atm_calls.empty:
                # Weight by open interest
                if atm_calls['open_interest'].sum() > 0:
                    weights = atm_calls['open_interest'] / atm_calls['open_interest'].sum()
                    return (atm_calls['strike'] * weights).sum()
                else:
                    return atm_calls['strike'].median()
        
        # Method 2: Maximum open interest strike
        if 'open_interest' in df.columns and df['open_interest'].sum() > 0:
            max_oi_strike = df.groupby('strike')['open_interest'].sum().idxmax()
            return float(max_oi_strike)
        
        # Method 3: Median strike
        return df['strike'].median()
    
    def _find_flip_point(self, gex_by_strike) :
        """
        Find the zero gamma flip point.
        
        Args:
            gex_by_strike: DataFrame with GEX by strike
        
        Returns:
            Strike price where net GEX flips sign, or None
        """
        if gex_by_strike.empty or 'net_gex' not in gex_by_strike.columns:
            return None
        
        # Sort by strike
        sorted_df = gex_by_strike.sort_values('strike')
        
        # Find sign changes
        signs = np.sign(sorted_df['net_gex'])
        sign_changes = signs.diff().fillna(0) != 0
        
        if sign_changes.any():
            # Get the strike where sign changes
            flip_idx = sign_changes[sign_changes].index[0]
            
            # Interpolate between strikes for more precision
            if flip_idx > 0:
                strike_before = sorted_df.iloc[flip_idx - 1]['strike']
                strike_after = sorted_df.iloc[flip_idx]['strike']
                gex_before = sorted_df.iloc[flip_idx - 1]['net_gex']
                gex_after = sorted_df.iloc[flip_idx]['net_gex']
                
                # Linear interpolation
                if gex_after != gex_before:
                    flip_point = strike_before - gex_before * (
                        strike_after - strike_before
                    ) / (gex_after - gex_before)
                    return flip_point
        
        return None
    
    def _find_peak_gamma_strike(self, df) :
        """
        Find strike with highest total gamma.
        
        Args:
            df: Options DataFrame
        
        Returns:
            Strike with peak gamma
        """
        if df.empty or 'gamma' not in df.columns:
            return None
        
        # Sum gamma by strike (weighted by OI)
        gamma_by_strike = df.groupby('strike').apply(
            lambda x: (x['gamma'] * x['open_interest']).sum()
        )
        
        if not gamma_by_strike.empty:
            return gamma_by_strike.idxmax()
        
        return None
    
    def _calculate_summary_stats(self, 
                                 df,
                                 results) :
        """
        Calculate summary statistics.
        
        Args:
            df: Options DataFrame
            results: Current results dict
        
        Returnsionary of summary statistics
        """
        stats = {
            'total_open_interest': df['open_interest'].sum(),
            'total_volume': df['volume'].sum() if 'volume' in df.columns else 0,
            'put_call_oi_ratio': 0,
            'avg_iv': df['implied_volatility'].mean() if 'implied_volatility' in df.columns else 0,
            'gamma_concentration': 0,
            'is_positive_gamma': results['net_gex'] > 0,
            'gamma_flip_distance': None
        }
        
        # Put/Call OI ratio
        call_oi = df[df['type'] == 'call']['open_interest'].sum()
        put_oi = df[df['type'] == 'put']['open_interest'].sum()
        if call_oi > 0:
            stats['put_call_oi_ratio'] = put_oi / call_oi
        
        # Gamma concentration (% of gamma in top 3 strikes)
        if 'gamma' in df.columns:
            gamma_by_strike = df.groupby('strike')['gamma'].sum().sort_values(ascending=False)
            if len(gamma_by_strike) > 0:
                top3_gamma = gamma_by_strike.head(3).sum()
                total_gamma = gamma_by_strike.sum()
                if total_gamma > 0:
                    stats['gamma_concentration'] = top3_gamma / total_gamma
        
        # Distance to flip point
        if results.get('flip_point') and results.get('spot_price'):
            stats['gamma_flip_distance'] = (
                results['flip_point'] - results['spot_price']
            ) / results['spot_price']
        
        return stats
    
    def _empty_gex_result(self) :
        """Return empty GEX result structure."""
        return {
            'symbol': None,
            'date': None,
            'spot_price': None,
            'total_contracts': 0,
            'call_gex': 0,
            'put_gex': 0,
            'net_gex': 0,
            'total_gex': 0,
            'gex_by_strike': pd.DataFrame(),
            'flip_point': None,
            'peak_gamma_strike': None,
            'summary_stats': {}
        }
    
    def generate_gex_report(self, 
                           symbol,
                           date= None) -> str:
        """
        Generate a formatted GEX report.
        
        Args:
            symbol: Stock symbol
            date: Options date
        
        Returns:
            Formatted report string
        """
        results = self.calculate_gex_for_symbol(symbol, date)
        
        if results['total_contracts'] == 0:
            return f"No options data available for {symbol} on {date}"
        
        report = []
        report.append("=" * 60)
        report.append(f"GEX ANALYSIS REPORT - {results['symbol']}")
        report.append(f"Date: {results['date']}")
        report.append(f"Spot Price: ${results['spot_price']:.2f}")
        report.append("=" * 60)
        report.append("")
        
        # GEX Summary
        report.append("GAMMA EXPOSURE SUMMARY")
        report.append("-" * 30)
        report.append(f"Call GEX:  ${results['call_gex']:,.0f}")
        report.append(f"Put GEX:   ${results['put_gex']:,.0f}")
        report.append(f"Net GEX:   ${results['net_gex']:,.0f}")
        report.append(f"Total GEX: ${results['total_gex']:,.0f}")
        report.append("")
        
        # Key Levels
        report.append("KEY LEVELS")
        report.append("-" * 30)
        if results['flip_point']:
            report.append(f"Zero Gamma Flip: ${results['flip_point']:.2f}")
            flip_dist = (results['flip_point'] - results['spot_price']) / results['spot_price'] * 100
            report.append(f"  Distance: {flip_dist:+.2f}%")
        
        if results['peak_gamma_strike']:
            report.append(f"Peak Gamma Strike: ${results['peak_gamma_strike']:.2f}")
        report.append("")
        
        # Market Statistics
        stats = results['summary_stats']
        report.append("MARKET STATISTICS")
        report.append("-" * 30)
        report.append(f"Total Open Interest: {stats['total_open_interest']:,.0f}")
        report.append(f"Put/Call OI Ratio: {stats['put_call_oi_ratio']:.2f}")
        report.append(f"Average IV: {stats['avg_iv']:.2%}")
        report.append(f"Gamma Concentration: {stats['gamma_concentration']:.1%}")
        report.append(f"Dealer Positioning: {'Long Gamma' if stats['is_positive_gamma'] else 'Short Gamma'}")
        report.append("")
        
        # Top strikes by GEX
        if not results['gex_by_strike'].empty:
            report.append("TOP 5 STRIKES BY ABSOLUTE GEX")
            report.append("-" * 30)
            top_strikes = results['gex_by_strike'].nlargest(5, 'total_gex')
            for _, row in top_strikes.iterrows():
                report.append(
                    f"${row['strike']:6.0f}: Net GEX=${row['net_gex']:10,.0f} "
                    f"(C:${row['call_gex']:,.0f}, P:${row['put_gex']:,.0f})"
                )
        
        report.append("=" * 60)
        
        return "\n".join(report)