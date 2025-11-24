"""
Fed Data Analyzer - Tools for breaking down and processing FRED data.

Provides utilities for:
- Analyzing economic indicator trends
- Summarizing Fed policy cycles
- Creating context-aware reports
- Pattern-specific Fed data processing
"""

import logging
from pathlib import Path
from typing import Dict

import pandas as pd

# Use date_utils for standardized datetime operations
from src.utils.date_utils import format_for_filename

logger = logging.getLogger(__name__)


class FedDataAnalyzer:
    """Analyzes and breaks down Fed data for pattern detection context."""

    def __init__(self, fed_integration):
        """Initialize analyzer with Fed data integration instance.

        Args:
            fed_integration: FedDataIntegration instance
        """
        self.fed = fed_integration
        self.cache_dir = Path(".cache/fed_analysis")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def analyze_policy_cycle(self, start_date, end_date):
        """Analyze the complete Fed policy cycle over a period.

        Args:
            start_date: Start date for analysis
            end_date: End date for analysis

        Returns:
            Dictionary with policy cycle analysis
        """
        logger.info(f"Analyzing Fed policy cycle: {start_date} to {end_date}")

        # Get FOMC calendar for period
        fomc_calendar = self.fed.fetch_fomc_calendar()
        period_meetings = fomc_calendar[
            (fomc_calendar["date"] >= start_date) & (fomc_calendar["date"] <= end_date)
        ].copy()

        if period_meetings.empty:
            return {"error": "No FOMC meetings in specified period"}

        # Policy cycle analysis
        cycle_analysis = {
            "period": f"{start_date} to {end_date}",
            "total_meetings": len(period_meetings),
            "rate_changes": {
                "hikes": len(period_meetings[period_meetings["decision"] == "hike"]),
                "cuts": len(period_meetings[period_meetings["decision"] == "cut"]),
                "holds": len(period_meetings[period_meetings["decision"] == "hold"]),
            },
            "rate_trajectory": {
                "start_rate": period_meetings.iloc[0]["rate"],
                "end_rate": period_meetings.iloc[-1]["rate"],
                "total_change": period_meetings.iloc[-1]["rate"] - period_meetings.iloc[0]["rate"],
                "max_rate": period_meetings["rate"].max(),
                "min_rate": period_meetings["rate"].min(),
            },
        }

        # Identify policy phases
        phases = []
        current_phase = None

        for _, meeting in period_meetings.iterrows():
            decision = meeting["decision"]

            if current_phase is None or current_phase["type"] != decision:
                # Start new phase
                if current_phase is not None:
                    phases.append(current_phase)

                current_phase = {
                    "type": decision,
                    "start_date": meeting["date"],
                    "start_rate": meeting["rate"],
                    "meetings": 1,
                    "total_change": meeting["rate_change"],
                }
            else:
                # Continue current phase
                current_phase["meetings"] += 1
                current_phase["total_change"] += meeting["rate_change"]
                current_phase["end_date"] = meeting["date"]
                current_phase["end_rate"] = meeting["rate"]

        # Add final phase
        if current_phase is not None:
            phases.append(current_phase)

        cycle_analysis["policy_phases"] = phases

        return cycle_analysis

    def analyze_market_stress_trends(self, indicators: pd.DataFrame, lookback_days: int = 60):
        """Analyze market stress indicator trends.

        Args:
            indicators: DataFrame with economic indicators
            lookback_days: Number of days to analyze trends

        Returns:
            Dictionary with stress trend analysis
        """
        if indicators.empty or lookback_days <= 0:
            return {}

        # Get recent period
        recent_data = indicators.tail(lookback_days)

        stress_analysis = {
            "period_days": len(recent_data),
            "latest_date": recent_data.index[-1] if not recent_data.empty else None,
        }

        # VIX analysis
        if "VIXCLS" in recent_data.columns:
            vix_data = recent_data["VIXCLS"].dropna()
            if not vix_data.empty:
                stress_analysis["vix"] = {
                    "current": float(vix_data.iloc[-1]),
                    "mean": float(vix_data.mean()),
                    "std": float(vix_data.std()),
                    "min": float(vix_data.min()),
                    "max": float(vix_data.max()),
                    "percentile_25": float(vix_data.quantile(0.25)),
                    "percentile_75": float(vix_data.quantile(0.75)),
                    "days_above_30": int((vix_data > 30).sum()),
                    "days_below_15": int((vix_data < 15).sum()),
                    "trend": self._calculate_trend(vix_data),
                }

        # Yield curve analysis
        if "T10Y2Y" in recent_data.columns:
            curve_data = recent_data["T10Y2Y"].dropna()
            if not curve_data.empty:
                stress_analysis["yield_curve"] = {
                    "current": float(curve_data.iloc[-1]),
                    "mean": float(curve_data.mean()),
                    "inverted_days": int((curve_data < 0).sum()),
                    "inversion_percentage": float((curve_data < 0).sum() / len(curve_data) * 100),
                    "trend": self._calculate_trend(curve_data),
                }

        # Credit spread analysis
        if "BAMLH0A0HYM2" in recent_data.columns:
            credit_data = recent_data["BAMLH0A0HYM2"].dropna()
            if not credit_data.empty:
                stress_analysis["credit_spreads"] = {
                    "current": float(credit_data.iloc[-1]),
                    "mean": float(credit_data.mean()),
                    "widening_days": int((credit_data.diff() > 0).sum()),
                    "trend": self._calculate_trend(credit_data),
                }

        return stress_analysis

    def _calculate_trend(self, series: pd.Series, window: int = 10) -> str:
        """Calculate trend direction for a time series."""
        if len(series) < window:
            return "insufficient_data"

        # Calculate moving averages
        short_ma = series.rolling(window // 2).mean().iloc[-1]
        long_ma = series.rolling(window).mean().iloc[-1]

        if pd.isna(short_ma) or pd.isna(long_ma):
            return "insufficient_data"

        diff_pct = (short_ma - long_ma) / long_ma * 100

        if diff_pct > 2:
            return "rising"
        elif diff_pct < -2:
            return "falling"
        else:
            return "stable"

    def create_context_summary(self, date: pd.Timestamp):
        """Create a concise summary of Fed context for a specific date.

        Args:
            date: Date to analyze

        Returns:
            Dictionary with concise context summary
        """
        full_context = self.fed.get_full_context(date)

        # Extract key insights
        fomc = full_context["fomc"]
        stress = full_context["stress"]

        # Create concise summary
        summary = {
            "date": date.strftime("%Y-%m-%d"),
            "fed_environment": self._describe_fed_environment(fomc),
            "market_stress_level": stress.get("stress_regime", "unknown"),
            "key_risks": self._identify_key_risks(fomc, stress),
            "pattern_implications": self._summarize_pattern_implications(full_context["pattern_weight_adjustments"]),
            "trading_considerations": self._generate_trading_considerations(fomc, stress),
        }

        return summary

    def _describe_fed_environment(self, fomc_context: Dict) -> str:
        """Generate human-readable Fed environment description."""
        rate = fomc_context.get("current_rate", 0)
        decision = fomc_context.get("last_decision", "unknown")
        days_to_fomc = fomc_context.get("days_to_fomc")

        env_parts = []

        # Rate environment
        if rate >= 5.0:
            env_parts.append("restrictive rates")
        elif rate >= 2.0:
            env_parts.append("elevated rates")
        else:
            env_parts.append("accommodative rates")

        # Policy stance
        if decision == "hike":
            env_parts.append("tightening cycle")
        elif decision == "cut":
            env_parts.append("easing cycle")
        else:
            env_parts.append("policy pause")

        # FOMC proximity
        if days_to_fomc is not None:
            if days_to_fomc <= 3:
                env_parts.append("FOMC week")
            elif days_to_fomc <= 10:
                env_parts.append("pre-FOMC blackout")

        return ", ".join(env_parts)

    def _identify_key_risks(self, fomc_context: Dict, stress_metrics: Dict):
        """Identify key market risks from Fed context."""
        risks = []

        # FOMC risks
        if fomc_context.get("is_fomc_week"):
            risks.append("FOMC volatility")

        if fomc_context.get("in_blackout_period"):
            risks.append("dealer positioning ahead of FOMC")

        # Stress risks
        vix_regime = stress_metrics.get("vix_regime")
        if vix_regime in ["elevated", "high"]:
            risks.append("elevated volatility regime")

        if stress_metrics.get("curve_inverted"):
            risks.append("yield curve inversion")

        stress_regime = stress_metrics.get("stress_regime")
        if stress_regime in ["elevated", "extreme"]:
            risks.append("broad market stress")

        return risks if risks else ["low risk environment"]

    def _summarize_pattern_implications(self, weight_adjustments: Dict):
        """Summarize how Fed context affects pattern detection."""
        implications = {}

        for pattern, weight in weight_adjustments.items():
            if weight > 1.1:
                implications[pattern] = f"enhanced (+{(weight-1)*100:.0f}%)"
            elif weight < 0.9:
                implications[pattern] = f"reduced (-{(1-weight)*100:.0f}%)"

        return implications if implications else {"all_patterns": "neutral weighting"}

    def _generate_trading_considerations(self, fomc_context: Dict, stress_metrics: Dict):
        """Generate practical trading considerations."""
        considerations = []

        # FOMC considerations
        days_to_fomc = fomc_context.get("days_to_fomc")
        if days_to_fomc is not None and days_to_fomc <= 10:
            considerations.append("elevated volatility risk near FOMC")

        # Stress considerations
        vix = stress_metrics.get("vix", 0)
        if vix > 25:
            considerations.append("high vol environment - gamma effects amplified")
        elif vix < 15:
            considerations.append("low vol environment - pin risk elevated")

        # Rate environment
        rate = fomc_context.get("current_rate", 0)
        if rate > 5.0:
            considerations.append("high rates - defensive positioning likely")

        return considerations if considerations else ["standard risk environment"]

    def export_analysis_report(self, start_date, end_date, output_path: str = None) -> str:
        """Export comprehensive Fed analysis report.

        Args:
            start_date: Start date for analysis
            end_date: End date for analysis
            output_path: Path for output file (None = auto-generate)

        Returns:
            Path to generated report
        """
        if output_path is None:
            output_path = self.cache_dir / f"fed_analysis_{start_date}_to_{end_date}.txt"

        # Gather analysis
        policy_cycle = self.analyze_policy_cycle(start_date, end_date)
        indicators = self.fed.fetch_economic_indicators(start_date, end_date)
        stress_trends = self.analyze_market_stress_trends(indicators)

        # Generate report
        report_lines = [
            "=" * 80,
            "FEDERAL RESERVE DATA ANALYSIS REPORT",
            "=" * 80,
            f"Analysis Period: {start_date} to {end_date}",
            f"Generated: {format_for_filename()}",
            "",
            "POLICY CYCLE ANALYSIS",
            "-" * 40,
            f"Total FOMC Meetings: {policy_cycle.get('total_meetings', 0)}",
            f"Rate Changes: {policy_cycle.get('rate_changes', {})}",
            f"Rate Trajectory: {policy_cycle.get('rate_trajectory', {})}",
            "",
            "MARKET STRESS TRENDS",
            "-" * 40,
        ]

        # Add VIX analysis
        if "vix" in stress_trends:
            vix = stress_trends["vix"]
            report_lines.extend(
                [
                    f"VIX Analysis:",
                    f"  Current: {vix['current']:.1f}",
                    f"  Mean: {vix['mean']:.1f} ± {vix['std']:.1f}",
                    f"  Range: {vix['min']:.1f} - {vix['max']:.1f}",
                    f"  High vol days (>30): {vix['days_above_30']}",
                    f"  Low vol days (<15): {vix['days_below_15']}",
                    f"  Trend: {vix['trend']}",
                    "",
                ]
            )

        # Add yield curve analysis
        if "yield_curve" in stress_trends:
            curve = stress_trends["yield_curve"]
            report_lines.extend(
                [
                    f"Yield Curve Analysis:",
                    f"  Current spread: {curve['current']:.2f}%",
                    f"  Inverted days: {curve['inverted_days']} ({curve['inversion_percentage']:.1f}%)",
                    f"  Trend: {curve['trend']}",
                    "",
                ]
            )

        report_lines.extend(["=" * 80, "End of Report"])

        # Write report
        with open(output_path, "w") as f:
            f.write("\n".join(report_lines))

        logger.info(f"Fed analysis report exported to {output_path}")
        return str(output_path)
