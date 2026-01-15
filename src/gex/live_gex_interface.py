"""
Live GEX Interface - Uses only cached options data
Replaces SampleDataGEXInterface for production use with live data
"""

import logging

import pandas as pd

from gex_db_infrastructure.gex.gex_calculator import GEXCalculator
from gex_db_infrastructure.validation.data_obfuscation import DataObfuscator
from gex_db_infrastructure.validation.options_data_validator import OptionsDataValidator

logger = logging.getLogger(__name__)


class LiveGEXInterface:
    """Interface for calculating GEX from live cached options data.

    No sample data dependencies - uses only provided DataFrame.
    """

    def __init__(self, risk_free_rate=0.05, validate_data=True, obfuscate_data=False):
        """Initialize the live GEX interface.

        Args:
            risk_free_rate: Risk-free rate for Black-Scholes calculations
            validate_data: Whether to validate data before GEX calculations
            obfuscate_data: Whether to obfuscate dates/symbols to prevent LLM training data leakage
        """
        self.validator = OptionsDataValidator(strict_mode=False)
        self.gex_calculator = GEXCalculator(risk_free_rate=risk_free_rate)
        self.validate_data = validate_data
        self.obfuscate_data = obfuscate_data

        # Initialize obfuscator if needed
        if self.obfuscate_data:
            self.obfuscator = DataObfuscator()

        # Cache for processed data
        self._processed_cache = {}

        logger.info("Initialized LiveGEXInterface for cached options data")

    def _obfuscate_options_data(self, options_data, symbol, trading_date):
        """Obfuscate options data to prevent LLM training data leakage.

        Args:
            options_data: DataFrame with options data
            symbol: Stock symbol to obfuscate
            trading_date: Trading date to use as base date

        Returns:
            Tuple of (obfuscated_dataframe, obfuscation_metadata)
        """
        if not self.obfuscate_data:
            return options_data, {}

        try:
            # Create copy to avoid modifying original
            obfuscated_df = options_data.copy()

            # Collect unique dates from the data
            date_strings = set()
            if "date" in obfuscated_df.columns:
                date_strings.update(obfuscated_df["date"].dt.strftime("%Y-%m-%d").unique())
            if "expiration" in obfuscated_df.columns:
                date_strings.update(obfuscated_df["expiration"].dt.strftime("%Y-%m-%d").unique())

            # Create mappings
            date_mapping = self.obfuscator.obfuscate_dates(list(date_strings), trading_date)
            ticker_mapping = self.obfuscator.obfuscate_tickers([symbol])

            # Apply obfuscation to date columns
            if "date" in obfuscated_df.columns:
                obfuscated_df["date"] = obfuscated_df["date"].dt.strftime("%Y-%m-%d").map(date_mapping)
            if "expiration" in obfuscated_df.columns:
                obfuscated_df["expiration"] = obfuscated_df["expiration"].dt.strftime("%Y-%m-%d").map(date_mapping)

            # Apply obfuscation to symbol column
            if "symbol" in obfuscated_df.columns:
                obfuscated_df["symbol"] = obfuscated_df["symbol"].map(ticker_mapping)

            obfuscation_metadata = {"date_mapping": date_mapping, "ticker_mapping": ticker_mapping, "obfuscated": True}

            logger.info(
                f"Obfuscated options data: {len(date_strings)} dates, symbol {symbol} -> {ticker_mapping.get(symbol)}"
            )
            return obfuscated_df, obfuscation_metadata

        except Exception as e:
            logger.error(f"Error obfuscating options data: {e}")
            # Return original data if obfuscation fails
            return options_data, {"obfuscated": False, "error": str(e)}

    def calculate_gex_for_symbol(self, symbol, trading_date=None, spot_price=None, options_data=None):
        """Calculate complete GEX metrics for a symbol using live data.

        Args:
            symbol: Stock symbol
            trading_date: Options date
            spot_price: Current spot price (auto-detects if None)
            options_data: Pre-loaded options DataFrame (REQUIRED)

        Returns dictionary containing:
            - status: 'success' or 'error'
            - metrics: GEX calculation results
            - message: Error message if failed
        """
        if options_data is None or options_data.empty:
            return {"status": "error", "message": f"No options data provided for {symbol} on {trading_date}"}

        cache_key = f"{symbol}_{trading_date}_{spot_price}"
        if cache_key in self._processed_cache:
            logger.info(f"Using cached GEX for {cache_key}")
            return self._processed_cache[cache_key]

        try:
            logger.info(f"Calculating GEX for {symbol} on {trading_date} with {len(options_data)} contracts")

            # Validate data if requested
            if self.validate_data:
                logger.info("Validating options data")
                cleaned_data, validation_report = self.validator.validate(options_data)

                if validation_report.get("issues"):
                    logger.warning(f"Data validation issues: {validation_report['issues']}")

                # Use cleaned data
                options_data = cleaned_data

            # Obfuscate data if requested (for LLM analysis without training data leakage)
            obfuscation_metadata = {}
            if self.obfuscate_data:
                options_data, obfuscation_metadata = self._obfuscate_options_data(options_data, symbol, trading_date)

            # Auto-detect spot price if not provided
            if spot_price is None:
                spot_price = self._estimate_spot_price(options_data)
                logger.info(f"Auto-detected spot price: ${spot_price:.2f}")

            # Calculate GEX metrics
            call_gex, put_gex = self._calculate_type_gex(options_data, spot_price)
            net_gex = call_gex + put_gex  # Puts are already negative

            # Calculate GEX by strike
            gex_by_strike = self._calculate_gex_by_strike(options_data, spot_price)

            # Find flip point and peak gamma
            flip_point = self._find_flip_point(gex_by_strike)
            peak_gamma_strike = self._find_peak_gamma_strike(options_data)

            # Generate summary statistics
            summary_stats = self._calculate_summary_stats(options_data, spot_price, call_gex, put_gex, net_gex)

            # Package results
            results = {
                "status": "success",
                "metrics": {
                    "symbol": symbol,
                    "trading_date": trading_date,
                    "spot_price": spot_price,
                    "total_gex": net_gex,
                    "call_gex": call_gex,
                    "put_gex": put_gex,
                    "net_gex": net_gex,
                    "gex_by_strike": gex_by_strike.to_dict() if not gex_by_strike.empty else {},
                    "flip_point": flip_point,
                    "peak_gamma_strike": peak_gamma_strike,
                    "summary_stats": summary_stats,
                    "total_contracts": len(options_data),
                    "calculation_metadata": {
                        "risk_free_rate": self.gex_calculator.risk_free_rate,
                        "validation_enabled": self.validate_data,
                        "obfuscation_enabled": self.obfuscate_data,
                        "contracts_processed": len(options_data),
                    },
                    "obfuscation_metadata": obfuscation_metadata,
                },
            }

            # Cache the results
            self._processed_cache[cache_key] = results

            logger.info(f"Successfully calculated GEX: Net={net_gex:.0f}, Calls={call_gex:.0f}, Puts={put_gex:.0f}")
            return results

        except Exception as e:
            logger.error(f"Error calculating GEX for {symbol}: {e}")
            return {"status": "error", "message": str(e)}

    def _calculate_type_gex(self, df, spot_price):
        """Calculate GEX for calls and puts separately."""
        call_df = df[df["type"] == "call"]
        put_df = df[df["type"] == "put"]

        call_gex = 0
        put_gex = 0

        if not call_df.empty:
            call_gex_data = self.gex_calculator.calculate_dealer_gamma_exposure(call_df, spot_price)
            call_gex = self.gex_calculator.calculate_net_gex(call_gex_data)

        if not put_df.empty:
            put_gex_data = self.gex_calculator.calculate_dealer_gamma_exposure(put_df, spot_price)
            put_gex = self.gex_calculator.calculate_net_gex(put_gex_data)

        return call_gex, put_gex

    def _calculate_gex_by_strike(self, df, spot_price):
        """Calculate GEX breakdown by strike price."""
        try:
            strikes = df["strike"].unique()
            gex_data = []

            for strike in sorted(strikes):
                strike_df = df[df["strike"] == strike]

                call_df = strike_df[strike_df["type"] == "call"]
                put_df = strike_df[strike_df["type"] == "put"]

                call_gex = 0
                put_gex = 0

                if not call_df.empty:
                    call_gex_data = self.gex_calculator.calculate_dealer_gamma_exposure(call_df, spot_price)
                    call_gex = self.gex_calculator.calculate_net_gex(call_gex_data)

                if not put_df.empty:
                    put_gex_data = self.gex_calculator.calculate_dealer_gamma_exposure(put_df, spot_price)
                    put_gex = self.gex_calculator.calculate_net_gex(put_gex_data)

                net_gex = call_gex + put_gex

                gex_data.append(
                    {
                        "strike": strike,
                        "call_gex": call_gex,
                        "put_gex": put_gex,
                        "net_gex": net_gex,
                        "distance_from_spot": (strike - spot_price) / spot_price * 100,
                    }
                )

            return pd.DataFrame(gex_data)

        except Exception as e:
            logger.error(f"Error calculating GEX by strike: {e}")
            return pd.DataFrame()

    def _estimate_spot_price(self, df):
        """Estimate spot price from options data."""
        try:
            # Find ATM options (smallest absolute difference from strike)
            strikes = df["strike"].unique()
            mid_prices = []

            for strike in strikes:
                strike_data = df[df["strike"] == strike]
                if not strike_data.empty:
                    # Use bid-ask midpoint
                    avg_bid = strike_data["bid"].mean()
                    avg_ask = strike_data["ask"].mean()
                    mid_prices.append((strike, (avg_bid + avg_ask) / 2))

            # Estimate from ATM strike
            if mid_prices:
                # Middle strike as estimate
                return sorted(strikes)[len(strikes) // 2]
            else:
                return 500.0  # Default fallback for SPY

        except Exception as e:
            logger.warning(f"Could not estimate spot price: {e}")
            return 500.0

    def _find_flip_point(self, gex_by_strike):
        """Find the gamma flip point where GEX changes sign."""
        if gex_by_strike.empty:
            return None

        try:
            # Find zero crossings
            net_gex = gex_by_strike["net_gex"].values
            strikes = gex_by_strike["strike"].values

            for i in range(len(net_gex) - 1):
                if net_gex[i] * net_gex[i + 1] < 0:  # Sign change
                    # Linear interpolation
                    flip_point = strikes[i] + (strikes[i + 1] - strikes[i]) * abs(net_gex[i]) / (
                        abs(net_gex[i]) + abs(net_gex[i + 1])
                    )
                    return flip_point

            return None

        except Exception as e:
            logger.error(f"Error finding flip point: {e}")
            return None

    def _find_peak_gamma_strike(self, df):
        """Find strike with highest gamma exposure."""
        try:
            if "gamma" in df.columns:
                max_gamma_idx = df["gamma"].abs().idxmax()
                return df.loc[max_gamma_idx, "strike"]
            else:
                # Fallback: use highest open interest
                if "open_interest" in df.columns:
                    max_oi_idx = df["open_interest"].idxmax()
                    return df.loc[max_oi_idx, "strike"]

            return None

        except Exception as e:
            logger.error(f"Error finding peak gamma strike: {e}")
            return None

    def _calculate_summary_stats(self, df, spot_price, call_gex, put_gex, net_gex):
        """Calculate summary statistics."""
        try:
            total_volume = df["volume"].sum() if "volume" in df.columns else 0
            total_oi = df["open_interest"].sum() if "open_interest" in df.columns else 0

            # GEX concentration
            abs_gex = abs(call_gex) + abs(put_gex)
            gex_concentration = abs(net_gex) / abs_gex if abs_gex > 0 else 0

            return {
                "total_volume": int(total_volume),
                "total_open_interest": int(total_oi),
                "gex_concentration": gex_concentration,
                "call_put_gex_ratio": abs(call_gex) / abs(put_gex) if put_gex != 0 else float("inf"),
                "contracts_analyzed": len(df),
            }

        except Exception as e:
            logger.error(f"Error calculating summary stats: {e}")
            return {}
