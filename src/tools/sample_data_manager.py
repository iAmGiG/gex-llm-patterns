"""
Sample Data Manager for GEX-LLM Testing

Manages local sample datasets for testing the complete analysis pipeline
without requiring live API access. Creates realistic data shapes for:
- SPY/SPX options chains 
- Underlying stock price data
- Historical options data spanning multiple years
"""

import pandas as pd
import numpy as np
from datetime import timedelta
import json
from pathlib import Path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.date_utils import parse_date_string, today_str, now_iso


class SampleDataManager:
    """
    Generate and manage sample market data for testing GEX analysis pipeline.
    """
    
    def __init__(self, base_dir = ".cache"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
        
        # Create subdirectories for different data types
        (self.base_dir / "options").mkdir(exist_ok=True)
        (self.base_dir / "stocks").mkdir(exist_ok=True)
        (self.base_dir / "news").mkdir(exist_ok=True)  # Future use
        (self.base_dir / "metadata").mkdir(exist_ok=True)
        
        # Market parameters for realistic data
        self.spy_current_price = 450.0
        self.spx_current_price = 4500.0
        self.base_vol = 0.20  # 20% IV baseline
        
    def create_sample_options_chain(self, 
                                  symbol = "SPY", 
                                  trading_date = "2024-01-15",
                                  expirations = None) :
        """
        Create realistic options chain data matching Alpha Vantage format.
        
        Args:
            symbol: SPY or SPX
            trading_date: Trading date for the options chain
            expirations of expiration dates, or None for defaults
            
        Returns:
            DataFrame with complete options chain
        """
        if expirations is None:
            # Default expirations: weekly and monthly
            base_date = parse_date_string(trading_date)
            expirations = [
                (base_date + timedelta(days=3)).strftime("%Y-%m-%d"),   # This week
                (base_date + timedelta(days=10)).strftime("%Y-%m-%d"),  # Next week  
                (base_date + timedelta(days=17)).strftime("%Y-%m-%d"),  # Week after
                (base_date + timedelta(days=31)).strftime("%Y-%m-%d"),  # Monthly
                (base_date + timedelta(days=45)).strftime("%Y-%m-%d"),  # Next month
            ]
        
        # Set underlying price based on symbol
        underlying_price = self.spy_current_price if symbol == "SPY" else self.spx_current_price
        
        all_contracts = []
        
        for exp_date in expirations:
            # Create strike ladder around current price
            strikes = self._generate_strike_ladder(underlying_price, symbol)
            
            # Calculate time to expiration
            exp_dt = parse_date_string(exp_date)
            trade_dt = parse_date_string(trading_date)
            days_to_exp = (exp_dt - trade_dt).days
            time_to_exp = max(days_to_exp / 365.25, 1/365.25)  # At least 1 day
            
            for strike in strikes:
                # Generate both call and put
                for option_type in ["call", "put"]:
                    contract = self._generate_contract(
                        symbol, trading_date, exp_date, strike, option_type,
                        underlying_price, time_to_exp
                    )
                    all_contracts.append(contract)
        
        df = pd.DataFrame(all_contracts)
        
        # Apply Alpha Vantage processing
        from src.data_sources.alpha_vantage_gex import AlphaVantageGEXClient
        client = AlphaVantageGEXClient()
        processed_df = client._apply_standard_processing(df)
        
        return processed_df
    
    def _generate_strike_ladder(self, underlying_price, symbol) :
        """Generate realistic strike ladder around underlying price."""
        if symbol == "SPY":
            # SPY: $1 strikes near ATM, $5 strikes further out
            strikes = []
            # Close strikes ($1 increments)
            for i in range(-20, 21):
                strikes.append(underlying_price + i)
            # Wider strikes ($5 increments)  
            for i in range(-10, 11):
                if i != 0:  # Don't duplicate ATM area
                    strikes.append(underlying_price + i * 5)
        else:  # SPX
            # SPX: $5 strikes near ATM, $25 strikes further out
            strikes = []
            # Close strikes ($5 increments)
            for i in range(-40, 41):
                strikes.append(underlying_price + i * 5)
            # Wider strikes ($25 increments)
            for i in range(-20, 21):
                if i != 0:
                    strikes.append(underlying_price + i * 25)
        
        return sorted(list(set(strikes)))  # Remove duplicates and sort
    
    def _generate_contract(self, symbol, trading_date, expiration,
                         strike, option_type, underlying_price,
                         time_to_exp) :
        """Generate individual option contract with realistic Greeks."""
        
        # Calculate moneyness
        moneyness = strike / underlying_price
        
        # Base implied volatility with skew
        if option_type == "call":
            iv = self.base_vol + (moneyness - 1) * 0.1  # Call skew
        else:
            iv = self.base_vol + (1 - moneyness) * 0.2  # Put skew (higher)
        
        iv = max(0.05, min(2.0, iv))  # Clamp IV to reasonable range
        
        # Black-Scholes calculations (simplified)
        intrinsic_value = self._calculate_intrinsic_value(
            underlying_price, strike, option_type
        )
        
        # Time value decreases with time and distance from ATM
        distance_from_atm = abs(moneyness - 1)
        time_value = max(0.01, iv * underlying_price * np.sqrt(time_to_exp) * 
                        np.exp(-distance_from_atm * 2))
        
        theoretical_price = intrinsic_value + time_value
        
        # Greeks (simplified)
        if option_type == "call":
            delta = max(0.01, min(0.99, 0.5 + (underlying_price - strike) / (underlying_price * 0.2)))
        else:
            delta = max(-0.99, min(-0.01, delta - 1)) if 'delta' in locals() else -0.5
        
        gamma = max(0.001, 0.01 * np.exp(-distance_from_atm * 5))
        theta = -max(0.01, theoretical_price * 0.02 / max(time_to_exp, 1/365))
        vega = max(0.01, underlying_price * gamma * np.sqrt(time_to_exp))
        rho = delta * strike * time_to_exp * 0.01
        
        # Market data with realistic bid/ask spreads
        mid_price = theoretical_price
        spread_pct = 0.02 + distance_from_atm * 0.01  # Wider spreads for OTM
        spread = mid_price * spread_pct
        
        bid = max(0.01, mid_price - spread/2)
        ask = mid_price + spread/2
        
        # Volume and open interest based on moneyness
        volume_factor = max(0.1, np.exp(-distance_from_atm * 3))
        base_volume = np.random.poisson(100 * volume_factor)
        base_oi = np.random.poisson(500 * volume_factor)
        
        # Contract ID
        exp_code = parse_date_string(expiration).strftime("%y%m%d")
        option_code = "C" if option_type == "call" else "P"
        strike_code = f"{int(strike * 1000):08d}"
        contract_id = f"{symbol}{exp_code}{option_code}{strike_code}"
        
        return {
            "contractID": contract_id,
            "symbol": symbol,
            "expiration": expiration,
            "strike": f"{strike:.2f}",
            "type": option_type,
            "last": f"{mid_price:.2f}",
            "mark": f"{mid_price:.2f}",
            "bid": f"{bid:.2f}",
            "ask": f"{ask:.2f}",
            "bid_size": str(np.random.randint(1, 50)),
            "ask_size": str(np.random.randint(1, 50)),
            "volume": str(base_volume),
            "open_interest": str(base_oi),
            "date": trading_date,
            "implied_volatility": f"{iv:.5f}",
            "delta": f"{delta:.5f}",
            "gamma": f"{gamma:.5f}",
            "theta": f"{theta:.5f}",
            "vega": f"{vega:.5f}",
            "rho": f"{rho:.5f}"
        }
    
    def _calculate_intrinsic_value(self, spot, strike, option_type) -> float:
        """Calculate intrinsic value."""
        if option_type == "call":
            return max(0, spot - strike)
        else:
            return max(0, strike - spot)
    
    def create_sample_underlying_data(self, 
                                    symbol = "SPY",
                                    start_date = "2020-01-01", 
                                    end_date = "2024-01-15") :
        """
        Create sample underlying stock data with realistic price movements.
        """
        start_dt = parse_date_string(start_date)
        end_dt = parse_date_string(end_date)
        
        # Generate business days only
        dates = pd.bdate_range(start=start_dt, end=end_dt)
        
        # Starting price
        initial_price = self.spy_current_price * 0.8  # Start lower for growth
        
        # Generate realistic price series with trends and volatility
        returns = np.random.normal(0.0005, 0.012, len(dates))  # ~12% annual vol
        
        # Add some trending periods
        trend_periods = len(dates) // 4
        for i in range(0, len(returns), trend_periods):
            trend_strength = np.random.choice([-0.001, 0.001, 0.0002], p=[0.2, 0.3, 0.5])
            end_idx = min(i + trend_periods, len(returns))
            returns[i:end_idx] += trend_strength
        
        # Calculate prices
        prices = [initial_price]
        for ret in returns[:-1]:
            prices.append(prices[-1] * (1 + ret))
        
        # Generate OHLCV data
        ohlcv_data = []
        for i, (date, close_price) in enumerate(zip(dates, prices)):
            # Daily volatility for OHLC generation
            daily_vol = abs(np.random.normal(0, 0.008))  
            
            high = close_price * (1 + daily_vol)
            low = close_price * (1 - daily_vol)
            
            if i == 0:
                open_price = close_price
            else:
                open_price = prices[i-1] * (1 + np.random.normal(0, 0.003))
            
            volume = np.random.randint(50000000, 200000000)  # Typical SPY volume
            
            ohlcv_data.append({
                "open": open_price,
                "high": max(open_price, high, close_price),
                "low": min(open_price, low, close_price), 
                "close": close_price,
                "volume": volume
            })
        
        df = pd.DataFrame(ohlcv_data, index=dates)
        
        # Add timezone localization like real data
        from src.utils.date_utils import localize_df, get_default_timezone
        df = localize_df(df, get_default_timezone())
        
        return df
    
    def save_sample_data_locally(self, symbol = "SPY", years_back = 2):
        """
        Generate and save sample data locally for testing.
        
        Creates both options and underlying data files.
        """
        print(f"Generating sample data for {symbol}...")
        
        # Create underlying data
        from datetime import datetime
        end_date = today_str()
        start_date = (datetime.now() - timedelta(days=365 * years_back)).strftime("%Y-%m-%d")
        
        underlying_df = self.create_sample_underlying_data(symbol, start_date, end_date)
        underlying_path = self.base_dir / "stocks" / f"{symbol.lower()}_underlying_{start_date}_{end_date}.json"
        underlying_df.reset_index().to_json(underlying_path, orient='records', date_format='iso')
        print(f"✅ Saved underlying data: {underlying_path}")
        
        # Create options data for several trading days
        sample_dates = [
            "2024-01-15", "2024-01-22", "2024-01-29",  # January
            "2024-06-15", "2024-07-15", "2024-08-15",  # Summer (for patterns)
            "2024-12-15"  # December
        ]
        
        for trading_date in sample_dates:
            options_df = self.create_sample_options_chain(symbol, trading_date)
            options_path = self.base_dir / "options" / f"{symbol.lower()}_options_{trading_date}.json"
            options_df.to_json(options_path, orient='records', date_format='iso')
            print(f"✅ Saved options data: {options_path} ({len(options_df)} contracts)")
        
        # Create summary metadata
        metadata = {
            "symbol": symbol,
            "generated_at": now_iso(),
            "underlying_data": {
                "start_date": start_date,
                "end_date": end_date,
                "file": str(underlying_path.name),
                "records": len(underlying_df)
            },
            "options_data": [
                {
                    "trading_date": date,
                    "file": f"{symbol.lower()}_options_{date}.parquet",
                    "contracts": len(self.create_sample_options_chain(symbol, date))
                }
                for date in sample_dates
            ]
        }
        
        metadata_path = self.base_dir / "metadata" / f"{symbol.lower()}_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"✅ Saved metadata: {metadata_path}")
        return metadata
    
    def load_sample_options(self, symbol = "SPY", trading_date = "2024-01-15") :
        """Load sample options data from local files."""
        options_path = self.base_dir / "options" / f"{symbol.lower()}_options_{trading_date}.json"
        
        if not options_path.exists():
            print(f"Sample data not found: {options_path}")
            print("Run save_sample_data_locally() first")
            return pd.DataFrame()
        
        return pd.read_json(options_path, orient='records')
    
    def load_sample_underlying(self, symbol = "SPY") :
        """Load sample underlying data from local files."""
        # Find the most recent underlying data file
        pattern = f"{symbol.lower()}_underlying_*.json"
        files = list((self.base_dir / "stocks").glob(pattern))
        
        if not files:
            print(f"No sample underlying data found for {symbol}")
            print("Run save_sample_data_locally() first")
            return pd.DataFrame()
        
        # Use the most recent file
        latest_file = sorted(files)[-1]
        df = pd.read_json(latest_file, orient='records')
        
        # Set the index back to dates if it exists
        if 'index' in df.columns:
            df.set_index('index', inplace=True)
            df.index = pd.to_datetime(df.index)
        
        return df


def create_all_sample_data():
    """Generate sample data for both SPY and SPX."""
    manager = SampleDataManager()
    
    print("Creating comprehensive sample dataset...")
    
    # Generate SPY data
    spy_metadata = manager.save_sample_data_locally("SPY", years_back=4)
    
    # Generate SPX data  
    spx_metadata = manager.save_sample_data_locally("SPX", years_back=4)
    
    print("\n🎉 Sample data generation complete!")
    print(f"📁 Data location: {manager.base_dir.absolute()}")
    print(f"📊 SPY: {spy_metadata['underlying_data']['records']} price records")
    print(f"📊 SPX: {spx_metadata['underlying_data']['records']} price records")
    print(f"🎯 Options: {len(spy_metadata['options_data'])} SPY + {len(spx_metadata['options_data'])} SPX chains")
    
    return manager


if __name__ == "__main__":
    create_all_sample_data()