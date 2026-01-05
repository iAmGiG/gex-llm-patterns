#!/usr/bin/env python3
"""Issue #183: Options Data Quality Audit.

Quick audit script to validate data quality of options records in SQLite database.
Checks for violations that would indicate data corruption or bad source data.

Usage:
    python scripts/validation/audit_options_data.py
    python scripts/validation/audit_options_data.py --symbols SPY,UVXY,QQQ --sample 1000
    python scripts/validation/audit_options_data.py --full  # All records (slow)

Author: Claude Code
Date: December 18, 2025
"""

import argparse
import os
import logging
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Results from a single validation check."""

    check_name: str
    total_records: int
    violations: int
    violation_pct: float
    severity: str  # 'critical', 'important', 'info'
    sample_violations: List[Dict] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """Check if validation passed based on severity thresholds."""
        if self.severity == "critical":
            return self.violation_pct == 0
        elif self.severity == "important":
            return self.violation_pct < 5.0
        return True


@dataclass
class AuditReport:
    """Complete audit report."""

    db_path: str
    symbols_audited: List[str]
    total_records: int
    sample_size: Optional[int]
    results: List[ValidationResult] = field(default_factory=list)

    @property
    def overall_status(self) -> str:
        """Determine overall status: GREEN, YELLOW, RED."""
        critical_fails = sum(1 for r in self.results if r.severity == "critical" and not r.passed)
        important_fails = sum(1 for r in self.results if r.severity == "important" and not r.passed)

        if critical_fails > 0:
            return "RED"
        elif important_fails > 0:
            return "YELLOW"
        return "GREEN"

    def to_dict(self) -> Dict:
        """Convert to dictionary for YAML output."""
        return {
            "db_path": self.db_path,
            "symbols_audited": self.symbols_audited,
            "total_records": self.total_records,
            "sample_size": self.sample_size,
            "overall_status": self.overall_status,
            "checks": [
                {
                    "name": r.check_name,
                    "severity": r.severity,
                    "total_records": r.total_records,
                    "violations": r.violations,
                    "violation_pct": round(r.violation_pct, 4),
                    "passed": r.passed,
                    "sample_violations": r.sample_violations[:5],  # Limit to 5 examples
                }
                for r in self.results
            ],
        }


class OptionsDataAuditor:
    """Audit options data quality in SQLite database."""

    def __init__(self, db_path: str = ".cache/options_historical.db"):
        """Initialize auditor.

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {db_path}")

    def get_database_summary(self) -> Dict:
        """Get summary of database contents."""
        with sqlite3.connect(self.db_path) as conn:
            # Total records
            total = conn.execute("SELECT COUNT(*) FROM options_chains").fetchone()[0]

            # Records by symbol
            cursor = conn.execute(
                """
                SELECT symbol, COUNT(*) as count,
                       MIN(trading_date) as min_date,
                       MAX(trading_date) as max_date
                FROM options_chains
                GROUP BY symbol
                ORDER BY count DESC
            """
            )
            by_symbol = {row[0]: {"count": row[1], "min_date": row[2], "max_date": row[3]} for row in cursor.fetchall()}

            return {
                "total_records": total,
                "by_symbol": by_symbol,
                "db_size_mb": self.db_path.stat().st_size / (1024 * 1024),
            }

    def _get_sample_query(self, symbols: List[str], sample_size: Optional[int]) -> Tuple[str, List]:
        """Build query with optional sampling."""
        where_clause = ""
        params = []

        if symbols:
            placeholders = ",".join(["?" for _ in symbols])
            where_clause = f"WHERE symbol IN ({placeholders})"
            params = [s.upper() for s in symbols]

        if sample_size:
            # Random sample using SQLite RANDOM()
            query = f"""
                SELECT * FROM options_chains
                {where_clause}
                ORDER BY RANDOM()
                LIMIT {sample_size}
            """
        else:
            query = f"SELECT * FROM options_chains {where_clause}"

        return query, params

    def run_audit(self, symbols: Optional[List[str]] = None, sample_size: Optional[int] = None) -> AuditReport:
        """Run complete data quality audit.

        Args:
            symbols: List of symbols to audit (None for all)
            sample_size: Number of records to sample (None for all)

        Returns:
            AuditReport with all validation results
        """
        logger.info(f"Starting audit of {self.db_path}")

        # Load data
        query, params = self._get_sample_query(symbols or [], sample_size)
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query(query, conn, params=params)

        logger.info(f"Loaded {len(df)} records for audit")

        # Get symbols actually audited
        symbols_audited = df["symbol"].unique().tolist() if not df.empty else []

        # Create report
        report = AuditReport(
            db_path=str(self.db_path),
            symbols_audited=symbols_audited,
            total_records=len(df),
            sample_size=sample_size,
        )

        # Run all checks
        report.results.append(self._check_bid_ask_relationship(df))
        report.results.append(self._check_call_delta_range(df))
        report.results.append(self._check_put_delta_range(df))
        report.results.append(self._check_gamma_non_negative(df))
        report.results.append(self._check_strike_positive(df))
        report.results.append(self._check_open_interest_non_negative(df))
        report.results.append(self._check_iv_reasonable(df))
        report.results.append(self._check_theta_negative(df))
        report.results.append(self._check_greeks_coverage(df))
        report.results.append(self._check_pricing_coverage(df))

        return report

    def _check_bid_ask_relationship(self, df: pd.DataFrame) -> ValidationResult:
        """Check bid <= ask (critical constraint)."""
        check_name = "Bid <= Ask"

        # Filter to records with both bid and ask
        valid_df = df[(df["bid"].notna()) & (df["ask"].notna()) & (df["bid"] > 0) & (df["ask"] > 0)]
        violations = valid_df[valid_df["bid"] > valid_df["ask"]]

        samples = []
        for _, row in violations.head(5).iterrows():
            samples.append(
                {
                    "symbol": row["symbol"],
                    "date": row["trading_date"],
                    "strike": row["strike"],
                    "type": row["option_type"],
                    "bid": row["bid"],
                    "ask": row["ask"],
                }
            )

        return ValidationResult(
            check_name=check_name,
            total_records=len(valid_df),
            violations=len(violations),
            violation_pct=(len(violations) / len(valid_df) * 100) if len(valid_df) > 0 else 0,
            severity="critical",
            sample_violations=samples,
        )

    def _check_call_delta_range(self, df: pd.DataFrame) -> ValidationResult:
        """Check call delta in [0, 1] range."""
        check_name = "Call Delta [0, 1]"

        calls = df[(df["option_type"] == "call") & (df["delta"].notna())]
        violations = calls[(calls["delta"] < 0) | (calls["delta"] > 1)]

        samples = []
        for _, row in violations.head(5).iterrows():
            samples.append(
                {
                    "symbol": row["symbol"],
                    "date": row["trading_date"],
                    "strike": row["strike"],
                    "delta": row["delta"],
                }
            )

        return ValidationResult(
            check_name=check_name,
            total_records=len(calls),
            violations=len(violations),
            violation_pct=(len(violations) / len(calls) * 100) if len(calls) > 0 else 0,
            severity="critical",
            sample_violations=samples,
        )

    def _check_put_delta_range(self, df: pd.DataFrame) -> ValidationResult:
        """Check put delta in [-1, 0] range."""
        check_name = "Put Delta [-1, 0]"

        puts = df[(df["option_type"] == "put") & (df["delta"].notna())]
        violations = puts[(puts["delta"] < -1) | (puts["delta"] > 0)]

        samples = []
        for _, row in violations.head(5).iterrows():
            samples.append(
                {
                    "symbol": row["symbol"],
                    "date": row["trading_date"],
                    "strike": row["strike"],
                    "delta": row["delta"],
                }
            )

        return ValidationResult(
            check_name=check_name,
            total_records=len(puts),
            violations=len(violations),
            violation_pct=(len(violations) / len(puts) * 100) if len(puts) > 0 else 0,
            severity="critical",
            sample_violations=samples,
        )

    def _check_gamma_non_negative(self, df: pd.DataFrame) -> ValidationResult:
        """Check gamma >= 0 for long options."""
        check_name = "Gamma >= 0"

        valid_df = df[df["gamma"].notna()]
        violations = valid_df[valid_df["gamma"] < 0]

        samples = []
        for _, row in violations.head(5).iterrows():
            samples.append(
                {
                    "symbol": row["symbol"],
                    "date": row["trading_date"],
                    "strike": row["strike"],
                    "type": row["option_type"],
                    "gamma": row["gamma"],
                }
            )

        return ValidationResult(
            check_name=check_name,
            total_records=len(valid_df),
            violations=len(violations),
            violation_pct=(len(violations) / len(valid_df) * 100) if len(valid_df) > 0 else 0,
            severity="critical",
            sample_violations=samples,
        )

    def _check_strike_positive(self, df: pd.DataFrame) -> ValidationResult:
        """Check strike > 0."""
        check_name = "Strike > 0"

        violations = df[df["strike"] <= 0]

        samples = []
        for _, row in violations.head(5).iterrows():
            samples.append(
                {
                    "symbol": row["symbol"],
                    "date": row["trading_date"],
                    "strike": row["strike"],
                }
            )

        return ValidationResult(
            check_name=check_name,
            total_records=len(df),
            violations=len(violations),
            violation_pct=(len(violations) / len(df) * 100) if len(df) > 0 else 0,
            severity="critical",
            sample_violations=samples,
        )

    def _check_open_interest_non_negative(self, df: pd.DataFrame) -> ValidationResult:
        """Check open interest >= 0."""
        check_name = "Open Interest >= 0"

        valid_df = df[df["open_interest"].notna()]
        violations = valid_df[valid_df["open_interest"] < 0]

        samples = []
        for _, row in violations.head(5).iterrows():
            samples.append(
                {
                    "symbol": row["symbol"],
                    "date": row["trading_date"],
                    "strike": row["strike"],
                    "open_interest": row["open_interest"],
                }
            )

        return ValidationResult(
            check_name=check_name,
            total_records=len(valid_df),
            violations=len(violations),
            violation_pct=(len(violations) / len(valid_df) * 100) if len(valid_df) > 0 else 0,
            severity="critical",
            sample_violations=samples,
        )

    def _check_iv_reasonable(self, df: pd.DataFrame) -> ValidationResult:
        """Check IV in reasonable range [0.01, 5.0] (1% to 500%)."""
        check_name = "IV Range [1%, 500%]"

        valid_df = df[df["implied_volatility"].notna()]
        # Note: IV stored as decimal (0.25 = 25%)
        violations = valid_df[(valid_df["implied_volatility"] < 0.01) | (valid_df["implied_volatility"] > 5.0)]

        samples = []
        for _, row in violations.head(5).iterrows():
            samples.append(
                {
                    "symbol": row["symbol"],
                    "date": row["trading_date"],
                    "strike": row["strike"],
                    "iv": row["implied_volatility"],
                    "iv_pct": row["implied_volatility"] * 100,
                }
            )

        return ValidationResult(
            check_name=check_name,
            total_records=len(valid_df),
            violations=len(violations),
            violation_pct=(len(violations) / len(valid_df) * 100) if len(valid_df) > 0 else 0,
            severity="important",
            sample_violations=samples,
        )

    def _check_theta_negative(self, df: pd.DataFrame) -> ValidationResult:
        """Check theta < 0 for long options (time decay)."""
        check_name = "Theta < 0"

        valid_df = df[df["theta"].notna()]
        violations = valid_df[valid_df["theta"] > 0]

        samples = []
        for _, row in violations.head(5).iterrows():
            samples.append(
                {
                    "symbol": row["symbol"],
                    "date": row["trading_date"],
                    "strike": row["strike"],
                    "type": row["option_type"],
                    "theta": row["theta"],
                }
            )

        return ValidationResult(
            check_name=check_name,
            total_records=len(valid_df),
            violations=len(violations),
            violation_pct=(len(violations) / len(valid_df) * 100) if len(valid_df) > 0 else 0,
            severity="important",
            sample_violations=samples,
        )

    def _check_greeks_coverage(self, df: pd.DataFrame) -> ValidationResult:
        """Check percentage of records with complete Greeks."""
        check_name = "Greeks Coverage"

        greeks_cols = ["delta", "gamma", "theta", "vega"]
        has_all_greeks = df[greeks_cols].notna().all(axis=1)
        missing_greeks = ~has_all_greeks

        samples = []
        for _, row in df[missing_greeks].head(5).iterrows():
            samples.append(
                {
                    "symbol": row["symbol"],
                    "date": row["trading_date"],
                    "strike": row["strike"],
                    "delta": row["delta"],
                    "gamma": row["gamma"],
                    "theta": row["theta"],
                    "vega": row["vega"],
                }
            )

        return ValidationResult(
            check_name=check_name,
            total_records=len(df),
            violations=int(missing_greeks.sum()),
            violation_pct=(missing_greeks.sum() / len(df) * 100) if len(df) > 0 else 0,
            severity="info",
            sample_violations=samples,
        )

    def _check_pricing_coverage(self, df: pd.DataFrame) -> ValidationResult:
        """Check percentage of records with bid/ask pricing."""
        check_name = "Pricing Coverage"

        has_pricing = (df["bid"].notna()) & (df["ask"].notna()) & (df["bid"] > 0) & (df["ask"] > 0)
        missing_pricing = ~has_pricing

        samples = []
        for _, row in df[missing_pricing].head(5).iterrows():
            samples.append(
                {
                    "symbol": row["symbol"],
                    "date": row["trading_date"],
                    "strike": row["strike"],
                    "bid": row["bid"],
                    "ask": row["ask"],
                }
            )

        return ValidationResult(
            check_name=check_name,
            total_records=len(df),
            violations=int(missing_pricing.sum()),
            violation_pct=(missing_pricing.sum() / len(df) * 100) if len(df) > 0 else 0,
            severity="info",
            sample_violations=samples,
        )


def print_report(report: AuditReport):
    """Print formatted audit report to console."""
    print("\n" + "=" * 70)
    print("OPTIONS DATA QUALITY AUDIT REPORT")
    print("=" * 70)

    print(f"\nDatabase: {report.db_path}")
    print(f"Symbols Audited: {', '.join(report.symbols_audited)}")
    print(f"Total Records: {report.total_records:,}")
    if report.sample_size:
        print(f"Sample Size: {report.sample_size:,}")

    status_color = {"GREEN": "\033[92m", "YELLOW": "\033[93m", "RED": "\033[91m"}
    reset = "\033[0m"
    status = report.overall_status
    print(f"\nOverall Status: {status_color.get(status, '')}{status}{reset}")

    print("\n" + "-" * 70)
    print("VALIDATION CHECKS")
    print("-" * 70)

    for result in report.results:
        status_str = "PASS" if result.passed else "FAIL"
        status_color_code = "\033[92m" if result.passed else "\033[91m"

        print(f"\n[{result.severity.upper():8}] {result.check_name}")
        print(f"  Records: {result.total_records:,}")
        print(f"  Violations: {result.violations:,} ({result.violation_pct:.2f}%)")
        print(f"  Status: {status_color_code}{status_str}{reset}")

        if result.sample_violations and not result.passed:
            print("  Sample violations:")
            for v in result.sample_violations[:3]:
                print(f"    - {v}")

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    critical_checks = [r for r in report.results if r.severity == "critical"]
    important_checks = [r for r in report.results if r.severity == "important"]
    info_checks = [r for r in report.results if r.severity == "info"]

    critical_pass = sum(1 for r in critical_checks if r.passed)
    important_pass = sum(1 for r in important_checks if r.passed)

    print(f"\nCritical Checks: {critical_pass}/{len(critical_checks)} passed")
    print(f"Important Checks: {important_pass}/{len(important_checks)} passed")
    print(f"Info Checks: {len(info_checks)} (informational only)")

    print("\n" + "-" * 70)

    if report.overall_status == "GREEN":
        print("Data quality is GOOD. Papers 1 & 2 results are reliable.")
        print("Safe to proceed with Paper 3 cross-asset analysis.")
    elif report.overall_status == "YELLOW":
        print("Data quality has minor issues. Papers 1 & 2 likely OK.")
        print("Investigate important check failures before Paper 3.")
    else:
        print("Data quality has CRITICAL issues. Papers 1 & 2 may need review.")
        print("DO NOT proceed with Paper 3 until issues are resolved.")

    print("=" * 70 + "\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Audit options data quality (Issue #183)")
    parser.add_argument(
        "--symbols",
        type=str,
        default=None,
        help="Comma-separated list of symbols to audit (default: all)",
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=10000,
        help="Sample size for audit (default: 10000, use --full for all)",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Audit all records (may be slow for large databases)",
    )
    parser.add_argument(
        "--db",
        type=str,
        default=".cache/options_historical.db",
        help="Path to SQLite database",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output path for YAML report",
    )

    args = parser.parse_args()

    # Parse symbols
    symbols = None
    if args.symbols:
        symbols = [s.strip() for s in args.symbols.split(",")]

    # Sample size
    sample_size = None if args.full else args.sample

    try:
        auditor = OptionsDataAuditor(args.db)

        # Show database summary first
        summary = auditor.get_database_summary()
        print("\nDatabase Summary:")
        print(f"  Total Records: {summary['total_records']:,}")
        print(f"  Database Size: {summary['db_size_mb']:.2f} MB")
        print(f"  Symbols: {len(summary['by_symbol'])}")
        for sym, info in list(summary["by_symbol"].items())[:5]:
            print(f"    {sym}: {info['count']:,} records ({info['min_date']} to {info['max_date']})")
        if len(summary["by_symbol"]) > 5:
            print(f"    ... and {len(summary['by_symbol']) - 5} more")

        # Run audit
        report = auditor.run_audit(symbols=symbols, sample_size=sample_size)

        # Print report
        print_report(report)

        # Save YAML if requested
        if args.output:
            import yaml

            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                yaml.dump(report.to_dict(), f, default_flow_style=False)
            print(f"Report saved to: {output_path}")

        # Return exit code based on status
        if report.overall_status == "RED":
            return 1
        return 0

    except FileNotFoundError as e:
        logger.error(str(e))
        return 1
    except Exception as e:
        logger.exception(f"Audit failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
