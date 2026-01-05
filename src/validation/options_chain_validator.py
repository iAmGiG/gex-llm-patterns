"""Options Chain Quality Validation (Issue #16)

Validates options chain data at ingress before storage in SQLite database.
Ensures data quality for GEX calculations and cross-asset analysis.

Integration point: SQLiteOptionsManager.store_options_chain()

Author: Claude Code
Date: December 18, 2025
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""

    CRITICAL = "critical"  # Reject record - data corruption
    WARNING = "warning"  # Flag but store - potential issue
    INFO = "info"  # Log only - informational


@dataclass
class ValidationIssue:
    """Single validation issue."""

    check_name: str
    severity: ValidationSeverity
    message: str
    record_index: Optional[int] = None
    field_name: Optional[str] = None
    field_value: Optional[Any] = None


@dataclass
class ValidationResult:
    """Result of validating an options chain."""

    symbol: str
    trading_date: str
    total_records: int
    valid_records: int = 0
    rejected_records: int = 0
    flagged_records: int = 0
    quality_score: float = 1.0
    issues: List[ValidationIssue] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """Check if validation passed (no critical issues)."""
        return not any(i.severity == ValidationSeverity.CRITICAL for i in self.issues)

    @property
    def critical_count(self) -> int:
        """Count of critical issues."""
        return sum(1 for i in self.issues if i.severity == ValidationSeverity.CRITICAL)

    @property
    def warning_count(self) -> int:
        """Count of warning issues."""
        return sum(1 for i in self.issues if i.severity == ValidationSeverity.WARNING)

    def to_dict(self) -> Dict:
        """Convert to dictionary for logging/storage."""
        return {
            "symbol": self.symbol,
            "trading_date": self.trading_date,
            "total_records": self.total_records,
            "valid_records": self.valid_records,
            "rejected_records": self.rejected_records,
            "flagged_records": self.flagged_records,
            "quality_score": round(self.quality_score, 4),
            "passed": self.passed,
            "critical_issues": self.critical_count,
            "warning_issues": self.warning_count,
        }


class OptionsChainValidator:
    """Validates options chain data quality before storage.

    Checks performed:
    - Critical: Bid <= Ask, Delta ranges, Gamma non-negative, Strike > 0, OI >= 0
    - Warning: IV range, Theta sign, Greeks coverage
    - Info: Pricing coverage, data completeness

    Example:
        >>> validator = OptionsChainValidator()
        >>> df = pd.DataFrame(...)  # options data
        >>> result = validator.validate(df, "SPY", "2024-01-15")
        >>> if result.passed:
        ...     # Store data
        >>> else:
        ...     # Handle validation failure
    """

    # Default validation thresholds
    DEFAULT_CONFIG = {
        # Critical thresholds (100% compliance required)
        "bid_ask_tolerance": 0.0,  # bid must be <= ask
        "call_delta_min": 0.0,
        "call_delta_max": 1.0,
        "put_delta_min": -1.0,
        "put_delta_max": 0.0,
        "gamma_min": 0.0,
        "strike_min": 0.0,
        "oi_min": 0,
        # Warning thresholds
        "iv_min": 0.01,  # 1%
        "iv_max": 5.0,  # 500%
        "theta_max": 0.0,  # Should be negative for long options
        "warning_threshold_pct": 5.0,  # >5% violations = warning
        # Quality scoring weights
        "weights": {
            "greeks_coverage": 0.30,
            "pricing_coverage": 0.20,
            "iv_quality": 0.20,
            "no_critical_issues": 0.30,
        },
        # Behavior
        "reject_on_critical": True,  # Reject entire chain if critical issues found
        "min_quality_score": 0.5,  # Minimum quality score to accept
    }

    def __init__(self, config: Optional[Dict] = None):
        """Initialize validator with optional config overrides.

        Args:
            config: Optional config dictionary to override defaults
        """
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}

    def validate(self, df: pd.DataFrame, symbol: str, trading_date: str) -> ValidationResult:
        """Validate an options chain DataFrame.

        Args:
            df: DataFrame with options data
            symbol: Stock symbol
            trading_date: Trading date

        Returns:
            ValidationResult with issues and quality score
        """
        result = ValidationResult(
            symbol=symbol,
            trading_date=trading_date,
            total_records=len(df),
        )

        if df.empty:
            result.issues.append(
                ValidationIssue(
                    check_name="empty_chain",
                    severity=ValidationSeverity.CRITICAL,
                    message="Empty options chain provided",
                )
            )
            return result

        # Standardize column names for validation
        df = self._standardize_columns(df.copy())

        # Run all validation checks
        self._check_bid_ask(df, result)
        self._check_call_delta(df, result)
        self._check_put_delta(df, result)
        self._check_gamma(df, result)
        self._check_strike(df, result)
        self._check_open_interest(df, result)
        self._check_implied_volatility(df, result)
        self._check_theta(df, result)
        self._check_greeks_coverage(df, result)
        self._check_pricing_coverage(df, result)

        # Calculate quality score
        result.quality_score = self._calculate_quality_score(df, result)

        # Count valid/rejected/flagged records
        result.valid_records = result.total_records - result.rejected_records - result.flagged_records

        return result

    def validate_and_filter(
        self, df: pd.DataFrame, symbol: str, trading_date: str
    ) -> Tuple[pd.DataFrame, ValidationResult]:
        """Validate and return filtered DataFrame with only valid records.

        Args:
            df: DataFrame with options data
            symbol: Stock symbol
            trading_date: Trading date

        Returns:
            Tuple of (filtered_df, validation_result)
        """
        result = self.validate(df, symbol, trading_date)

        if not result.passed and self.config["reject_on_critical"]:
            # Return empty DataFrame if critical issues and reject mode enabled
            logger.warning(f"Rejecting {symbol} {trading_date}: {result.critical_count} critical issues")
            return pd.DataFrame(), result

        # Filter out records with critical issues
        df = self._standardize_columns(df.copy())
        filtered_df = self._filter_invalid_records(df)

        result.valid_records = len(filtered_df)
        result.rejected_records = len(df) - len(filtered_df)

        return filtered_df, result

    def _standardize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize column names for validation."""
        column_mapping = {
            "contractID": "contract_symbol",
            "type": "option_type",
            "impliedVolatility": "implied_volatility",
            "openInterest": "open_interest",
            "bidSize": "bid_size",
            "askSize": "ask_size",
        }

        for old_name, new_name in column_mapping.items():
            if old_name in df.columns and new_name not in df.columns:
                df[new_name] = df[old_name]

        # Normalize option_type
        if "option_type" in df.columns:
            df["option_type"] = df["option_type"].str.lower().str.strip()
            df["option_type"] = df["option_type"].replace({"c": "call", "p": "put"})

        return df

    def _filter_invalid_records(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove records with critical validation issues."""
        mask = pd.Series(True, index=df.index)

        # Filter bid > ask (with valid bid/ask)
        if "bid" in df.columns and "ask" in df.columns:
            bid_ask_valid = ~(
                (df["bid"].notna()) & (df["ask"].notna()) & (df["bid"] > 0) & (df["ask"] > 0) & (df["bid"] > df["ask"])
            )
            mask &= bid_ask_valid

        # Filter invalid call delta
        if "delta" in df.columns and "option_type" in df.columns:
            call_delta_valid = ~(
                (df["option_type"] == "call")
                & (df["delta"].notna())
                & ((df["delta"] < self.config["call_delta_min"]) | (df["delta"] > self.config["call_delta_max"]))
            )
            mask &= call_delta_valid

            put_delta_valid = ~(
                (df["option_type"] == "put")
                & (df["delta"].notna())
                & ((df["delta"] < self.config["put_delta_min"]) | (df["delta"] > self.config["put_delta_max"]))
            )
            mask &= put_delta_valid

        # Filter negative gamma
        if "gamma" in df.columns:
            gamma_valid = ~((df["gamma"].notna()) & (df["gamma"] < self.config["gamma_min"]))
            mask &= gamma_valid

        # Filter invalid strikes
        if "strike" in df.columns:
            strike_valid = df["strike"] > self.config["strike_min"]
            mask &= strike_valid

        # Filter negative OI
        if "open_interest" in df.columns:
            oi_valid = ~((df["open_interest"].notna()) & (df["open_interest"] < self.config["oi_min"]))
            mask &= oi_valid

        return df[mask]

    # === CRITICAL CHECKS ===

    def _check_bid_ask(self, df: pd.DataFrame, result: ValidationResult):
        """Check bid <= ask constraint."""
        if "bid" not in df.columns or "ask" not in df.columns:
            return

        valid_df = df[(df["bid"].notna()) & (df["ask"].notna()) & (df["bid"] > 0) & (df["ask"] > 0)]
        violations = valid_df[valid_df["bid"] > valid_df["ask"]]

        if len(violations) > 0:
            pct = len(violations) / len(valid_df) * 100 if len(valid_df) > 0 else 0
            result.issues.append(
                ValidationIssue(
                    check_name="bid_ask",
                    severity=ValidationSeverity.CRITICAL if pct > 1 else ValidationSeverity.WARNING,
                    message=f"Bid > Ask: {len(violations)} records ({pct:.4f}%)",
                    field_name="bid/ask",
                )
            )
            result.rejected_records += len(violations)

    def _check_call_delta(self, df: pd.DataFrame, result: ValidationResult):
        """Check call delta in [0, 1] range."""
        if "delta" not in df.columns or "option_type" not in df.columns:
            return

        calls = df[(df["option_type"] == "call") & (df["delta"].notna())]
        violations = calls[
            (calls["delta"] < self.config["call_delta_min"]) | (calls["delta"] > self.config["call_delta_max"])
        ]

        if len(violations) > 0:
            pct = len(violations) / len(calls) * 100 if len(calls) > 0 else 0
            result.issues.append(
                ValidationIssue(
                    check_name="call_delta_range",
                    severity=ValidationSeverity.CRITICAL,
                    message=f"Call delta out of [0,1]: {len(violations)} records ({pct:.4f}%)",
                    field_name="delta",
                )
            )
            result.rejected_records += len(violations)

    def _check_put_delta(self, df: pd.DataFrame, result: ValidationResult):
        """Check put delta in [-1, 0] range."""
        if "delta" not in df.columns or "option_type" not in df.columns:
            return

        puts = df[(df["option_type"] == "put") & (df["delta"].notna())]
        violations = puts[
            (puts["delta"] < self.config["put_delta_min"]) | (puts["delta"] > self.config["put_delta_max"])
        ]

        if len(violations) > 0:
            pct = len(violations) / len(puts) * 100 if len(puts) > 0 else 0
            result.issues.append(
                ValidationIssue(
                    check_name="put_delta_range",
                    severity=ValidationSeverity.CRITICAL,
                    message=f"Put delta out of [-1,0]: {len(violations)} records ({pct:.4f}%)",
                    field_name="delta",
                )
            )
            result.rejected_records += len(violations)

    def _check_gamma(self, df: pd.DataFrame, result: ValidationResult):
        """Check gamma >= 0."""
        if "gamma" not in df.columns:
            return

        valid_df = df[df["gamma"].notna()]
        violations = valid_df[valid_df["gamma"] < self.config["gamma_min"]]

        if len(violations) > 0:
            pct = len(violations) / len(valid_df) * 100 if len(valid_df) > 0 else 0
            result.issues.append(
                ValidationIssue(
                    check_name="gamma_non_negative",
                    severity=ValidationSeverity.CRITICAL,
                    message=f"Negative gamma: {len(violations)} records ({pct:.4f}%)",
                    field_name="gamma",
                )
            )
            result.rejected_records += len(violations)

    def _check_strike(self, df: pd.DataFrame, result: ValidationResult):
        """Check strike > 0."""
        if "strike" not in df.columns:
            return

        violations = df[df["strike"] <= self.config["strike_min"]]

        if len(violations) > 0:
            pct = len(violations) / len(df) * 100
            result.issues.append(
                ValidationIssue(
                    check_name="strike_positive",
                    severity=ValidationSeverity.CRITICAL,
                    message=f"Non-positive strike: {len(violations)} records ({pct:.4f}%)",
                    field_name="strike",
                )
            )
            result.rejected_records += len(violations)

    def _check_open_interest(self, df: pd.DataFrame, result: ValidationResult):
        """Check open interest >= 0."""
        if "open_interest" not in df.columns:
            return

        valid_df = df[df["open_interest"].notna()]
        violations = valid_df[valid_df["open_interest"] < self.config["oi_min"]]

        if len(violations) > 0:
            pct = len(violations) / len(valid_df) * 100 if len(valid_df) > 0 else 0
            result.issues.append(
                ValidationIssue(
                    check_name="oi_non_negative",
                    severity=ValidationSeverity.CRITICAL,
                    message=f"Negative OI: {len(violations)} records ({pct:.4f}%)",
                    field_name="open_interest",
                )
            )
            result.rejected_records += len(violations)

    # === WARNING CHECKS ===

    def _check_implied_volatility(self, df: pd.DataFrame, result: ValidationResult):
        """Check IV in reasonable range."""
        if "implied_volatility" not in df.columns:
            return

        valid_df = df[df["implied_volatility"].notna()]
        violations = valid_df[
            (valid_df["implied_volatility"] < self.config["iv_min"])
            | (valid_df["implied_volatility"] > self.config["iv_max"])
        ]

        if len(violations) > 0:
            pct = len(violations) / len(valid_df) * 100 if len(valid_df) > 0 else 0
            severity = (
                ValidationSeverity.WARNING if pct > self.config["warning_threshold_pct"] else ValidationSeverity.INFO
            )
            result.issues.append(
                ValidationIssue(
                    check_name="iv_range",
                    severity=severity,
                    message=f"IV out of [{self.config['iv_min']*100}%, {self.config['iv_max']*100}%]: {len(violations)} records ({pct:.2f}%)",
                    field_name="implied_volatility",
                )
            )
            if severity == ValidationSeverity.WARNING:
                result.flagged_records += len(violations)

    def _check_theta(self, df: pd.DataFrame, result: ValidationResult):
        """Check theta < 0 for long options."""
        if "theta" not in df.columns:
            return

        valid_df = df[df["theta"].notna()]
        violations = valid_df[valid_df["theta"] > self.config["theta_max"]]

        if len(violations) > 0:
            pct = len(violations) / len(valid_df) * 100 if len(valid_df) > 0 else 0
            severity = (
                ValidationSeverity.WARNING if pct > self.config["warning_threshold_pct"] else ValidationSeverity.INFO
            )
            result.issues.append(
                ValidationIssue(
                    check_name="theta_sign",
                    severity=severity,
                    message=f"Positive theta: {len(violations)} records ({pct:.2f}%)",
                    field_name="theta",
                )
            )

    # === INFO CHECKS ===

    def _check_greeks_coverage(self, df: pd.DataFrame, result: ValidationResult):
        """Check percentage of records with complete Greeks."""
        greeks_cols = ["delta", "gamma", "theta", "vega"]
        present_cols = [c for c in greeks_cols if c in df.columns]

        if not present_cols:
            result.issues.append(
                ValidationIssue(
                    check_name="greeks_coverage",
                    severity=ValidationSeverity.WARNING,
                    message="No Greeks columns found",
                )
            )
            return

        has_all_greeks = df[present_cols].notna().all(axis=1)
        coverage_pct = has_all_greeks.sum() / len(df) * 100 if len(df) > 0 else 0

        if coverage_pct < 90:
            result.issues.append(
                ValidationIssue(
                    check_name="greeks_coverage",
                    severity=ValidationSeverity.WARNING if coverage_pct < 50 else ValidationSeverity.INFO,
                    message=f"Greeks coverage: {coverage_pct:.2f}%",
                )
            )

    def _check_pricing_coverage(self, df: pd.DataFrame, result: ValidationResult):
        """Check percentage of records with bid/ask pricing."""
        if "bid" not in df.columns or "ask" not in df.columns:
            result.issues.append(
                ValidationIssue(
                    check_name="pricing_coverage",
                    severity=ValidationSeverity.WARNING,
                    message="No bid/ask columns found",
                )
            )
            return

        has_pricing = (df["bid"].notna()) & (df["ask"].notna()) & (df["bid"] > 0) & (df["ask"] > 0)
        coverage_pct = has_pricing.sum() / len(df) * 100 if len(df) > 0 else 0

        if coverage_pct < 80:
            result.issues.append(
                ValidationIssue(
                    check_name="pricing_coverage",
                    severity=ValidationSeverity.WARNING if coverage_pct < 50 else ValidationSeverity.INFO,
                    message=f"Pricing coverage: {coverage_pct:.2f}%",
                )
            )

    def _calculate_quality_score(self, df: pd.DataFrame, result: ValidationResult) -> float:
        """Calculate overall quality score (0.0 - 1.0).

        Components:
        - Greeks coverage (30%)
        - Pricing coverage (20%)
        - IV quality (20%)
        - No critical issues (30%)
        """
        weights = self.config["weights"]
        score = 0.0

        # Greeks coverage (30%)
        greeks_cols = ["delta", "gamma", "theta", "vega"]
        present_cols = [c for c in greeks_cols if c in df.columns]
        if present_cols:
            has_greeks = df[present_cols].notna().all(axis=1)
            greeks_pct = has_greeks.sum() / len(df) if len(df) > 0 else 0
            score += weights["greeks_coverage"] * greeks_pct

        # Pricing coverage (20%)
        if "bid" in df.columns and "ask" in df.columns:
            has_pricing = (df["bid"].notna()) & (df["ask"].notna()) & (df["bid"] > 0) & (df["ask"] > 0)
            pricing_pct = has_pricing.sum() / len(df) if len(df) > 0 else 0
            score += weights["pricing_coverage"] * pricing_pct

        # IV quality (20%)
        if "implied_volatility" in df.columns:
            valid_iv = df["implied_volatility"].notna()
            reasonable_iv = (
                valid_iv
                & (df["implied_volatility"] >= self.config["iv_min"])
                & (df["implied_volatility"] <= self.config["iv_max"])
            )
            iv_quality = reasonable_iv.sum() / valid_iv.sum() if valid_iv.sum() > 0 else 0
            score += weights["iv_quality"] * iv_quality

        # No critical issues (30%)
        critical_pct = result.rejected_records / len(df) if len(df) > 0 else 0
        no_critical_score = max(0, 1 - critical_pct * 10)  # Penalize heavily for critical issues
        score += weights["no_critical_issues"] * no_critical_score

        return min(1.0, max(0.0, score))


# Convenience function for quick validation
def validate_options_chain(
    df: pd.DataFrame, symbol: str, trading_date: str, config: Optional[Dict] = None
) -> ValidationResult:
    """Convenience function to validate an options chain.

    Args:
        df: DataFrame with options data
        symbol: Stock symbol
        trading_date: Trading date
        config: Optional config overrides

    Returns:
        ValidationResult
    """
    validator = OptionsChainValidator(config)
    return validator.validate(df, symbol, trading_date)
