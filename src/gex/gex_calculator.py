"""
GEX Calculator - Core Gamma Exposure Calculation Engine

Calculates dealer gamma exposure from options data to identify key market levels
and hedging constraints that create predictable price movements.
"""

import logging
from math import log, sqrt
from typing import Any, Dict

import numpy as np
import pandas as pd
from scipy.stats import norm

from src.utils.config_manager import get_config
from src.utils.date_utils import calculate_days_to_expiration, get_datetime_now

logger = logging.getLogger(__name__)


class GEXCalculator:
    """Calculate Gamma Exposure (GEX) for dealer positioning analysis.

    GEX represents the amount dealers must buy/sell for every 1% move in the underlying. Positive GEX suggests dealers
    are long gamma (supportive), negative suggests short gamma (reactive hedging).
    """

    def __init__(self, risk_free_rate: float = None):
        """Initialize GEX Calculator.

        Args:
            risk_free_rate: Risk-free rate for Black-Scholes calculations (default from config)
        """
        config = get_config()
        self.risk_free_rate = risk_free_rate or config.get("gex_calculation.gex_calculator.risk_free_rate", 0.05)

        # Load configuration values
        self.days_per_year = config.get("gex_calculation.gex_calculator.days_per_year", 365.0)
        self.percentage_move_multiplier = config.get("gex_calculation.gex_calculator.percentage_move_multiplier", 0.01)
        self.open_interest_multiplier = config.get("gex_calculation.gex_calculator.open_interest_multiplier", 100)
        self.long_gamma_threshold = config.get("gex_calculation.gex_calculator.long_gamma_threshold", 0.0001)
        self.short_gamma_threshold = config.get("gex_calculation.gex_calculator.short_gamma_threshold", -0.0001)
        self.default_price_range_pct = config.get("gex_calculation.gex_calculator.default_price_range_pct", 0.20)
        self.key_levels_count = config.get("gex_calculation.gex_calculator.key_levels_count", 5)

    def black_scholes_gamma(self, S, K, T, r, sigma) -> float:
        """Calculate Black-Scholes gamma for an option.

        Args:
            S: Current stock price
            K: Strike price
            T: Time to expiration (in years)
            r: Risk-free rate
            sigma: Volatility (annual)

        Returns:
            Gamma value
        """
        if T <= 0 or sigma <= 0:
            return 0.0

        d1 = (log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * sqrt(T))

        gamma = norm.pdf(d1) / (S * sigma * sqrt(T))
        return gamma

    def calculate_dealer_gamma_exposure(
        self, options_data: pd.DataFrame, underlying_price: float, open_interest_multiplier: int = 100
    ) -> pd.DataFrame:
        """Calculate dealer GEX for each option contract.

        Dealer GEX = -1 * Customer Position * Gamma * Underlying Price^2 * 0.01

        Assumes dealers are short customer positions (market makers).

        Args:
            options_data: DataFrame with options data (strike, oi, iv, dte, type)
            underlying_price: Current price of underlying
            open_interest_multiplier: Contract size multiplier (default 100 shares/contract)

        Returns:
            DataFrame with GEX calculations per strike
        """
        if options_data.empty:
            logger.warning("Empty options data provided to GEX calculator")
            return pd.DataFrame()

        logger.info(f"Calculating GEX for {len(options_data)} option contracts")

        gex_data = options_data.copy()

        # Calculate days to expiration if not present
        if "days_to_expiration" not in gex_data.columns and "expiration" in gex_data.columns:
            if "date" in gex_data.columns:
                gex_data["days_to_expiration"] = calculate_days_to_expiration(gex_data["expiration"], gex_data["date"])
            else:
                # Use current date if trade date not available
                current_date = pd.Timestamp.now().normalize()
                current_dates = pd.Series([current_date] * len(gex_data), index=gex_data.index)
                gex_data["days_to_expiration"] = calculate_days_to_expiration(gex_data["expiration"], current_dates)

        # Convert DTE to years
        gex_data["time_to_expiry"] = gex_data["days_to_expiration"] / self.days_per_year

        # Calculate Black-Scholes gamma for each contract
        gex_data["bs_gamma"] = gex_data.apply(
            lambda row: self.black_scholes_gamma(
                S=underlying_price,
                K=row["strike"],
                T=row["time_to_expiry"],
                r=self.risk_free_rate,
                sigma=row["implied_volatility"],
            ),
            axis=1,
        )

        # Calculate dealer GEX per contract
        # Dealer GEX = -1 * Customer OI * Gamma * S^2 * percentage_move * multiplier
        gex_data["dealer_gex"] = (
            -1
            * gex_data["open_interest"]
            * gex_data["bs_gamma"]
            * (underlying_price**2)
            * self.percentage_move_multiplier
            * open_interest_multiplier
        )

        # Add contract type weighting (calls are positive customer exposure)
        # Convention: Calls contribute positive GEX, Puts contribute negative GEX.
        # Since dealer_gex is negative, we multiply calls by -1 to make them positive,
        # and puts by 1 to keep them negative.
        gex_data["weighted_gex"] = gex_data["dealer_gex"] * np.where(gex_data["type"] == "call", -1, 1)

        return gex_data

    def aggregate_gex_by_strike(self, gex_data: pd.DataFrame) -> pd.DataFrame:
        """Aggregate GEX by strike price for market level analysis.

        Args:
            gex_data: Output from calculate_dealer_gamma_exposure

        Returns:
            DataFrame with total GEX per strike
        """
        if gex_data.empty:
            return pd.DataFrame()

        strike_gex = (
            gex_data.groupby("strike")
            .agg({"weighted_gex": "sum", "open_interest": "sum", "bs_gamma": "mean"})  # Average gamma at strike
            .reset_index()
        )

        strike_gex.columns = ["strike", "total_gex", "total_oi", "avg_gamma"]

        # Sort by strike for easier analysis
        strike_gex = strike_gex.sort_values("strike").reset_index(drop=True)

        return strike_gex

    def calculate_net_gex(self, gex_data) -> float:
        """Calculate total net GEX across all strikes.

        Args:
            gex_data: Output from calculate_dealer_gamma_exposure

        Returns:
            Net GEX value (positive = long gamma, negative = short gamma)
        """
        if gex_data.empty:
            return 0.0

        return gex_data["weighted_gex"].sum()

    def calculate_gex_velocity(self, current_gex: float, previous_gex: float) -> Dict[str, float]:
        """Calculate GEX velocity metrics (day-over-day changes).

        Issue #80: Velocity metrics are often the primary signal, not absolute levels.

        Args:
            current_gex: Net GEX for current date
            previous_gex: Net GEX for previous date

        Returns:
            Dict with:
                - net_gex_change_1d_usd: Absolute change in USD
                - net_gex_change_1d_pct: Percentage change
                - gex_acceleration: Rate of change (if multiple periods)
        """
        if previous_gex == 0:
            # Avoid division by zero
            change_pct = 0.0 if current_gex == 0 else 100.0
        else:
            change_pct = ((current_gex - previous_gex) / abs(previous_gex)) * 100

        return {"net_gex_change_1d_usd": current_gex - previous_gex, "net_gex_change_1d_pct": round(change_pct, 2)}

    def calculate_gex_profile(
        self, options_data: pd.DataFrame, underlying_price: float, price_range_pct: float = None
    ) -> Dict[str, Any]:
        """Calculate comprehensive GEX profile for market analysis.

        Args:
            options_data: DataFrame with options data
            underlying_price: Current underlying price
            price_range_pct: Percentage range around current price to analyze

        Returns:
            Dictionary with GEX profile metrics
        """
        logger.info(f"Calculating comprehensive GEX profile for underlying at ${underlying_price:.2f}")

        # Use config default if not specified
        if price_range_pct is None:
            price_range_pct = self.default_price_range_pct

        # Calculate base GEX
        gex_data = self.calculate_dealer_gamma_exposure(options_data, underlying_price)

        if gex_data.empty:
            return {
                "net_gex": 0.0,
                "strike_gex": pd.DataFrame(),
                "key_levels": [],
                "gex_range": (0.0, 0.0),
                "calculation_timestamp": get_datetime_now(),
            }

        # Aggregate by strike
        strike_gex = self.aggregate_gex_by_strike(gex_data)

        # Calculate key metrics
        net_gex = self.calculate_net_gex(gex_data)

        # Find strikes within analysis range
        price_lower = underlying_price * (1 - price_range_pct)
        price_upper = underlying_price * (1 + price_range_pct)

        relevant_strikes = strike_gex[
            (strike_gex["strike"] >= price_lower) & (strike_gex["strike"] <= price_upper)
        ].copy()

        # Identify key GEX levels (high absolute GEX values)
        if not relevant_strikes.empty:
            relevant_strikes["abs_gex"] = abs(relevant_strikes["total_gex"])
            key_levels = relevant_strikes.nlargest(self.key_levels_count, "abs_gex")[
                ["strike", "total_gex", "total_oi"]
            ].to_dict("records")
        else:
            key_levels = []

        # GEX range for the analysis window
        if not relevant_strikes.empty:
            gex_range = (relevant_strikes["total_gex"].min(), relevant_strikes["total_gex"].max())
        else:
            gex_range = (0.0, 0.0)

        return {
            "net_gex": net_gex,
            "strike_gex": strike_gex,
            "relevant_strikes": relevant_strikes,
            "key_levels": key_levels,
            "gex_range": gex_range,
            "underlying_price": underlying_price,
            "price_range": (price_lower, price_upper),
            "calculation_timestamp": get_datetime_now(),
            "total_contracts": len(gex_data),
        }

    def calculate_dual_gex(
        self, options_data: pd.DataFrame, underlying_price: float, open_interest_multiplier: int = 100
    ) -> Dict[str, Any]:
        """
        Calculate dual GEX metrics: GEX_OI (structural) and GEX_Volume (activity).

        Issue #138: Dual GEX Framework
        - GEX_OI: Weighted by open_interest (what dealers HAVE)
        - GEX_Volume: Weighted by daily volume (what dealers are DOING)

        Purpose: Explain why detection rate stays constant but profitability varies.
        Example: Q1 2024 (+21bp alpha) vs Q4 2024 (-1bp alpha) despite 100% detection.

        Args:
            options_data: DataFrame with options data (must include 'volume' field)
            underlying_price: Current price of underlying
            open_interest_multiplier: Contract size multiplier (default 100)

        Returns:
            Dict with:
                - gex_oi: Structural positioning (open interest weighted)
                - gex_volume: Economic activity (volume weighted)
                - activity_ratio: |GEX_Volume / GEX_OI| (hedging intensity)
                - net_gex: Backward compatible aggregate (same as gex_oi)
                - gex_data_oi: DataFrame with per-contract GEX_OI
                - gex_data_volume: DataFrame with per-contract GEX_Volume (if volume available)
        """
        if options_data.empty:
            logger.warning("Empty options data provided to dual GEX calculator")
            return {
                "gex_oi": 0.0,
                "gex_volume": 0.0,
                "net_gex": 0.0,
                "activity_ratio": 0.0,
                "gex_data_oi": pd.DataFrame(),
                "gex_data_volume": pd.DataFrame(),
                "has_volume_data": False,
            }

        # Calculate GEX_OI (structural positioning - existing method)
        gex_data_oi = self.calculate_dealer_gamma_exposure(options_data, underlying_price, open_interest_multiplier)

        # Calculate GEX_OI aggregate
        gex_oi = self.calculate_net_gex(gex_data_oi)

        # Check if volume data is available
        has_volume = "volume" in options_data.columns

        if has_volume:
            # Calculate GEX_Volume (economic activity)
            gex_data_volume = gex_data_oi.copy()

            # Replace open_interest with volume in GEX calculation
            # GEX_Volume = -1 * volume * gamma * S^2 * 0.01 * multiplier
            gex_data_volume["dealer_gex"] = (
                -1
                * gex_data_volume["volume"]
                * gex_data_volume["bs_gamma"]
                * (underlying_price**2)
                * self.percentage_move_multiplier
                * open_interest_multiplier
            )

            # Re-apply contract type weighting
            gex_data_volume["weighted_gex"] = gex_data_volume["dealer_gex"] * np.where(
                gex_data_volume["type"] == "call", 1, -1
            )

            # Calculate GEX_Volume aggregate
            gex_volume = gex_data_volume["weighted_gex"].sum()

            # Calculate activity ratio (hedging intensity)
            activity_ratio = abs(gex_volume / gex_oi) if gex_oi != 0 else 0.0

            logger.info(
                f"Dual GEX calculated: GEX_OI=${gex_oi / 1e9:.2f}B, "
                f"GEX_Volume=${gex_volume / 1e9:.2f}B, "
                f"Activity Ratio={activity_ratio:.2f}"
            )
        else:
            logger.warning("Volume data not available - GEX_Volume set to 0.0")
            gex_data_volume = pd.DataFrame()
            gex_volume = 0.0
            activity_ratio = 0.0

        return {
            "gex_oi": gex_oi,
            "gex_volume": gex_volume,
            "net_gex": gex_oi,  # Backward compatible
            "activity_ratio": activity_ratio,
            "gex_data_oi": gex_data_oi,
            "gex_data_volume": gex_data_volume,
            "has_volume_data": has_volume,
            "underlying_price": underlying_price,
            "calculation_timestamp": get_datetime_now(),
        }

    def analyze_gex_regime(self, net_gex: float, underlying_price: float) -> Dict[str, Any]:
        """Determine market regime based on GEX levels.

        Args:
            net_gex: Net gamma exposure
            underlying_price: Current underlying price

        Returns:
            Dictionary with regime analysis
        """
        # Normalize GEX by price for regime classification
        normalized_gex = net_gex / (underlying_price**2) if underlying_price > 0 else 0

        if normalized_gex > self.long_gamma_threshold:
            regime = "Long Gamma"
            description = "Dealers long gamma - suppressive to volatility, mean-reverting environment"
            market_impact = "Supportive on dips, resistant on rallies"
        elif normalized_gex < self.short_gamma_threshold:
            regime = "Short Gamma"
            description = "Dealers short gamma - amplifies volatility, momentum environment"
            market_impact = "Selling on dips, buying on rallies"
        else:
            regime = "Neutral Gamma"
            description = "Balanced gamma positioning"
            market_impact = "Limited dealer hedging impact"

        return {
            "regime": regime,
            "description": description,
            "market_impact": market_impact,
            "normalized_gex": normalized_gex,
            "raw_gex": net_gex,
        }

    def calculate_net_gex_from_raw(
        self,
        contracts: list,
        open_interest_multiplier: int = 100,
    ) -> Dict[str, Any]:
        """Calculate net GEX from raw contract data using a standard practitioner convention.

        This function implements the common GEX convention where:
        - Call options contribute POSITIVE GEX.
        - Put options contribute NEGATIVE GEX.
        - Net GEX is the sum of Call GEX and Put GEX.

        This convention is used to model dealer hedging flows, where a large positive
        Net GEX implies a volatility-dampening environment (dealers sell into strength)
        and a large negative Net GEX implies a volatility-amplifying environment
        (dealers sell into weakness).

        Formula: GEX_per_contract = gamma * OI * 100 * (spot_price^2) * 0.01

        Args:
            contracts: List of dicts with keys:
                - option_type: 'call' or 'put'
                - gamma: Pre-computed gamma value
                - open_interest: Contract open interest
                - underlying_price: Spot price of underlying
            open_interest_multiplier: Contract size (default 100 shares/contract)

        Returns:
            Dict with:
                - net_gex: Total net GEX in USD
                - call_gex: GEX contribution from calls (positive)
                - put_gex: GEX contribution from puts (negative)
                - underlying_price: Price used for calculation
                - contract_count: Number of contracts processed
        """
        if not contracts:
            return {
                "net_gex": 0.0,
                "call_gex": 0.0,
                "put_gex": 0.0,
                "underlying_price": None,
                "contract_count": 0,
            }

        call_gex = 0.0
        put_gex = 0.0
        underlying_price = None
        contract_count = 0

        for contract in contracts:
            option_type = contract.get("option_type", "").lower()
            gamma = contract.get("gamma", 0)
            oi = contract.get("open_interest", 0)
            price = contract.get("underlying_price", 0)

            # Skip invalid contracts
            if gamma is None or oi is None or oi <= 0 or price is None or price <= 0:
                continue

            if underlying_price is None:
                underlying_price = price

            # GEX formula: gamma * OI * S^2 * 0.01 * multiplier
            # Matches calculate_dealer_gamma_exposure() final weighted_gex sign convention:
            #   dealer_gex = -1 * OI * gamma * S^2 * 0.01 * 100  (negative)
            #   weighted_gex = dealer_gex * (-1 if call else +1)
            #   Result: CALLS → POSITIVE, PUTS → NEGATIVE
            contract_gex = (
                gamma
                * oi
                * open_interest_multiplier
                * price
                * price
                * self.percentage_move_multiplier
            )

            # Apply dealer positioning sign convention (matches calculate_dealer_gamma_exposure):
            # Calls contribute POSITIVE to net GEX (dampening effect)
            # Puts contribute NEGATIVE to net GEX (amplifying effect)
            if option_type == "call":
                call_gex += contract_gex  # calls: positive contribution
            else:
                put_gex -= contract_gex   # puts: negative contribution

            contract_count += 1

        net_gex = call_gex + put_gex

        logger.debug(
            f"Raw GEX calculation: {contract_count} contracts, "
            f"call_gex=${call_gex / 1e9:.2f}B, put_gex=${put_gex / 1e9:.2f}B, "
            f"net_gex=${net_gex / 1e9:.2f}B"
        )

        return {
            "net_gex": net_gex,
            "call_gex": call_gex,
            "put_gex": put_gex,
            "underlying_price": underlying_price,
            "contract_count": contract_count,
        }
