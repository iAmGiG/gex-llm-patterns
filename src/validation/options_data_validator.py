"""Options Data Validator Validates and cleans Alpha Vantage options data for GEX calculations."""

import logging

import pandas as pd

from src.utils.config_manager import get_config

logger = logging.getLogger(__name__)


class OptionsDataValidator:
    """Validate and clean options data for GEX calculations."""

    # Expected columns from Alpha Vantage
    REQUIRED_COLUMNS = [
        "contractID",
        "symbol",
        "expiration",
        "strike",
        "type",
        "date",
        "implied_volatility",
        "delta",
        "gamma",
        "open_interest",
    ]

    OPTIONAL_COLUMNS = ["last", "mark", "bid", "ask", "volume", "bid_size", "ask_size", "theta", "vega", "rho"]

    GREEK_BOUNDS = {
        "delta": {"call": (0, 1), "put": (-1, 0)},
        "gamma": {"both": (0, float("inf"))},
        "theta": {"both": (float("-inf"), 0)},
        "vega": {"both": (0, float("inf"))},
        "implied_volatility": {"both": (0, 10)},  # 0 to 1000%
    }

    def __init__(self, strict_mode=False):
        """Initialize validator.

        Argsict_mode: If True, raises errors on validation failures.
                        If False, logs warnings and attempts to fix.
        """
        config = get_config()

        self.strict_mode = strict_mode
        self.validation_report = {}

        # Load validation thresholds from config
        self.put_call_parity_tolerance = config.get("validation.options_data_validator.put_call_parity_tolerance", 0.2)

    def validate(self, df):
        """Validate and clean options data.

        Args:
            df: Options data DataFrame

        Returns:
            Tuple of (cleaned_df, validation_report)
        """
        logger.info(f"Validating {len(df)} option contracts")

        self.validation_report = {
            "input_rows": len(df),
            "issues": [],
            "warnings": [],
            "dropped_rows": 0,
            "fixed_values": 0,
        }

        # Create a copy to avoid modifying original
        clean_df = df.copy()

        # Step 1: Check required columns
        clean_df = self._validate_columns(clean_df)

        # Step 2: Validate data types
        clean_df = self._validate_dtypes(clean_df)

        # Step 3: Validate Greeks bounds
        clean_df = self._validate_greeks(clean_df)

        # Step 4: Validate logical consistency
        clean_df = self._validate_consistency(clean_df)

        # Step 5: Remove invalid rows
        clean_df = self._remove_invalid_rows(clean_df)

        # Step 6: Fill missing optional values
        clean_df = self._fill_missing_values(clean_df)

        self.validation_report["output_rows"] = len(clean_df)
        self.validation_report["dropped_rows"] = (
            self.validation_report["input_rows"] - self.validation_report["output_rows"]
        )

        logger.info(f"Validation complete: {len(clean_df)} valid contracts")

        return clean_df, self.validation_report

    def _validate_columns(self, df):
        """Check for required columns."""
        missing_cols = set(self.REQUIRED_COLUMNS) - set(df.columns)

        if missing_cols:
            msg = f"Missing required columns: {missing_cols}"
            if self.strict_mode:
                raise ValueError(msg)
            else:
                self.validation_report["issues"].append(msg)
                logger.error(msg)

        return df

    def _validate_dtypes(self, df):
        """Ensure correct data types."""
        # Numeric columns
        numeric_cols = [
            "strike",
            "implied_volatility",
            "delta",
            "gamma",
            "theta",
            "vega",
            "rho",
            "open_interest",
            "volume",
            "last",
            "mark",
            "bid",
            "ask",
            "bid_size",
            "ask_size",
        ]

        for col in numeric_cols:
            if col in df.columns:
                try:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                except Exception as e:
                    msg = f"Failed to convert {col} to numeric: {e}"
                    self.validation_report["warnings"].append(msg)
                    logger.warning(msg)

        # Date columns
        date_cols = ["date", "expiration"]
        for col in date_cols:
            if col in df.columns:
                try:
                    df[col] = pd.to_datetime(df[col])
                except Exception as e:
                    msg = f"Failed to convert {col} to datetime: {e}"
                    self.validation_report["warnings"].append(msg)
                    logger.warning(msg)

        # Categorical columns
        if "type" in df.columns:
            df["type"] = df["type"].str.lower()
            invalid_types = df[~df["type"].isin(["call", "put"])]["type"].unique()
            if len(invalid_types) > 0:
                msg = f"Invalid option types found: {invalid_types}"
                self.validation_report["warnings"].append(msg)
                logger.warning(msg)

        return df

    def _validate_greeks(self, df):
        """Validate Greek values are within expected bounds."""
        fixes_made = 0

        for greek, bounds_dict in self.GREEK_BOUNDS.items():
            if greek not in df.columns:
                continue

            for opt_type in ["call", "put"]:
                if opt_type in bounds_dict:
                    bounds = bounds_dict[opt_type]
                else:
                    bounds = bounds_dict["both"]

                mask = df["type"] == opt_type
                if mask.sum() == 0:
                    continue

                # Check bounds
                out_of_bounds = (df.loc[mask, greek] < bounds[0]) | (df.loc[mask, greek] > bounds[1])

                if out_of_bounds.any():
                    n_invalid = out_of_bounds.sum()
                    msg = f"{n_invalid} {opt_type} options have {greek} out of bounds {bounds}"

                    if self.strict_mode:
                        self.validation_report["issues"].append(msg)
                    else:
                        # Clip to bounds
                        df.loc[mask & out_of_bounds, greek] = df.loc[mask & out_of_bounds, greek].clip(
                            bounds[0], bounds[1]
                        )
                        fixes_made += n_invalid
                        self.validation_report["warnings"].append(msg + " (fixed)")
                        logger.warning(msg)

        self.validation_report["fixed_values"] += fixes_made
        return df

    def _validate_consistency(self, df):
        """Check logical consistency of options data."""
        issues = []

        # Check expiration is after trade date
        if "date" in df.columns and "expiration" in df.columns:
            expired = df["expiration"] <= df["date"]
            if expired.any():
                n_expired = expired.sum()
                msg = f"{n_expired} contracts have already expired"
                issues.append(msg)
                if not self.strict_mode:
                    df = df[~expired]

        # Check strike prices are positive
        if "strike" in df.columns:
            negative_strikes = df["strike"] <= 0
            if negative_strikes.any():
                n_negative = negative_strikes.sum()
                msg = f"{n_negative} contracts have non-positive strikes"
                issues.append(msg)
                if not self.strict_mode:
                    df = df[~negative_strikes]

        # Check open interest is non-negative
        if "open_interest" in df.columns:
            negative_oi = df["open_interest"] < 0
            if negative_oi.any():
                df.loc[negative_oi, "open_interest"] = 0
                self.validation_report["fixed_values"] += negative_oi.sum()

        # Check put-call parity relationship (loose check)
        if all(col in df.columns for col in ["type", "strike", "expiration", "symbol"]):
            for (symbol, strike, exp), group in df.groupby(["symbol", "strike", "expiration"]):
                if len(group) == 2 and set(group["type"]) == {"call", "put"}:
                    call_data = group[group["type"] == "call"].iloc[0]
                    put_data = group[group["type"] == "put"].iloc[0]

                    # Very loose check: call delta - put delta should be close to 1
                    if "delta" in df.columns:
                        delta_diff = abs((call_data["delta"] - put_data["delta"]) - 1)
                        if delta_diff > self.put_call_parity_tolerance:
                            msg = f"Put-call parity violation for {symbol} {strike} {exp}: delta diff={delta_diff:.3f}"
                            self.validation_report["warnings"].append(msg)

        for issue in issues:
            if self.strict_mode:
                self.validation_report["issues"].append(issue)
            else:
                self.validation_report["warnings"].append(issue)

        return df

    def _remove_invalid_rows(self, df):
        """Remove rows with critical missing or invalid data."""
        initial_len = len(df)

        # Remove rows with NaN in required columns
        for col in self.REQUIRED_COLUMNS:
            if col in df.columns:
                df = df.dropna(subset=[col])

        # Remove rows with invalid option type
        if "type" in df.columns:
            df = df[df["type"].isin(["call", "put"])]

        # Remove rows with zero gamma (unusable for GEX)
        if "gamma" in df.columns:
            df = df[df["gamma"] != 0]

        dropped = initial_len - len(df)
        if dropped > 0:
            msg = f"Dropped {dropped} invalid rows"
            self.validation_report["warnings"].append(msg)
            logger.info(msg)

        return df

    def _fill_missing_values(self, df):
        """Fill missing optional values with sensible defaults."""
        fill_values = {
            "volume": 0,
            "bid_size": 0,
            "ask_size": 0,
            "last": lambda row: (row["bid"] + row["ask"]) / 2 if pd.notna(row["bid"]) else row["mark"],
            "mark": lambda row: (row["bid"] + row["ask"]) / 2 if pd.notna(row["bid"]) else row["last"],
        }

        for col, fill_value in fill_values.items():
            if col in df.columns:
                if callable(fill_value):
                    # Row-wise calculation
                    mask = df[col].isna()
                    if mask.any():
                        df.loc[mask, col] = df.loc[mask].apply(fill_value, axis=1)
                else:
                    # Simple fill
                    df[col] = df[col].fillna(fill_value)

        return df

    def get_quality_metrics(self, df):
        """Calculate quality metrics for the validated data.

        Args:
            df: Validated DataFrame

        Returnsionary of quality metrics
        """
        metrics = {
            "total_contracts": len(df),
            "complete_greeks": df[["delta", "gamma", "theta", "vega"]].notna().all(axis=1).sum(),
            "has_volume": (df["volume"] > 0).sum() if "volume" in df.columns else 0,
            "has_open_interest": (df["open_interest"] > 0).sum() if "open_interest" in df.columns else 0,
            "unique_symbols": df["symbol"].nunique() if "symbol" in df.columns else 0,
            "unique_expirations": df["expiration"].nunique() if "expiration" in df.columns else 0,
            "avg_days_to_expiry": None,
            "iv_distribution": {},
        }

        # Calculate average days to expiry
        if "date" in df.columns and "expiration" in df.columns:
            try:
                from src.utils.date_utils import calculate_days_to_expiration

                days_to_exp = calculate_days_to_expiration(df["expiration"], df["date"])
                metrics["avg_days_to_expiry"] = days_to_exp.mean()
            except Exception as e:
                logger.warning(f"Could not calculate days to expiry: {e}")
                metrics["avg_days_to_expiry"] = None

        # IV distribution
        if "implied_volatility" in df.columns:
            metrics["iv_distribution"] = {
                "mean": df["implied_volatility"].mean(),
                "std": df["implied_volatility"].std(),
                "min": df["implied_volatility"].min(),
                "max": df["implied_volatility"].max(),
                "q25": df["implied_volatility"].quantile(0.25),
                "q50": df["implied_volatility"].quantile(0.50),
                "q75": df["implied_volatility"].quantile(0.75),
            }

        return metrics
