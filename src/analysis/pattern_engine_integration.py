"""Pattern Engine Integration.

Integrates Pattern Probability Mapper with existing GEX pattern detection and Fed context for comprehensive pattern
analysis workflow.
"""

import datetime
import logging
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

# Use date_utils instead of datetime (in addition to existing import)
from src.utils.date_utils import add_business_days, calculate_duration_minutes, today_str

from ..data_sources.fed_data_analyzer import FedDataAnalyzer
from ..data_sources.fed_data_integration import FedDataIntegration
from ..gex.calculator import GEXCalculator
from ..utils.date_utils import now_iso, parse_date_string
from .confidence_scorer import ConfidenceScorer
from .pattern_probability_mapper import PatternProbabilityMapper
from .statistical_validator import StatisticalValidator

logger = logging.getLogger(__name__)


class PatternEngineIntegration:
    """
    Unified pattern analysis engine that integrates:
    - GEX pattern detection
    - Fed context analysis
    - Pattern probability mapping
    - Statistical validation
    - Confidence scoring
    """

    def __init__(self, historical_database_path: str = None):
        """Initialize integrated pattern engine.

        Args:
            historical_database_path: Path to historical database
        """
        self.historical_db_path = historical_database_path

        # Initialize components
        self.gex_calculator = GEXCalculator()
        self.fed_integration = FedDataIntegration()
        self.fed_analyzer = FedDataAnalyzer(self.fed_integration)
        self.probability_mapper = PatternProbabilityMapper(historical_database_path)
        self.statistical_validator = StatisticalValidator()
        self.confidence_scorer = ConfidenceScorer()

        logger.info("PatternEngineIntegration initialized")

    def analyze_current_patterns(self, gex_data: Dict, price_data: Dict, analysis_date: str = None) -> Dict:
        """Comprehensive pattern analysis for current market conditions.

        Args:
            gex_data: GEX data from calculate_daily_gex_metrics
            price_data: Current price data
            analysis_date: Date for analysis (default: today)

        Returns:
            Dictionary with comprehensive pattern analysis
        """
        if analysis_date is None:
            analysis_date = datetime.datetime.now().strftime("%Y-%m-%d")

        logger.info(f"Analyzing current patterns for {analysis_date}")

        analysis_timestamp = pd.Timestamp(analysis_date)

        # 1. Get Fed context
        fed_context = self.fed_integration.get_full_context(analysis_timestamp)
        fed_summary = self.fed_analyzer.create_context_summary(analysis_timestamp)

        # 2. Enhanced context with Fed data
        enhanced_context = {
            "is_opex": self._check_opex_date(analysis_date),
            "upcoming_fomc": fed_context["fomc"]["is_fomc_week"],
            "days_to_fomc": fed_context["fomc"]["days_to_fomc"],
            "days_after_opex": self._calculate_days_after_opex(analysis_date),
            "fed_context": fed_context,
            "near_technical_level": False,  # Would need technical analysis
        }

        # 3. Detect GEX patterns
        detected_patterns = self.gex_calculator.detect_patterns(
            gex_data=gex_data, price_data=price_data, context=enhanced_context
        )

        # 4. Apply Fed weight adjustments
        pattern_adjustments = fed_context["pattern_weight_adjustments"]
        adjusted_patterns = self._apply_fed_adjustments(detected_patterns, pattern_adjustments)

        # 5. Calculate confidence scores (if historical data available)
        confidence_scores = self._calculate_pattern_confidences(adjusted_patterns, fed_summary)

        return {
            "analysis_date": analysis_date,
            "analysis_timestamp": now_iso(),
            # Core results
            "detected_patterns": adjusted_patterns,
            "confidence_scores": confidence_scores,
            "pattern_count": len(adjusted_patterns),
            # Context
            "fed_context": fed_summary,
            "market_context": enhanced_context,
            "gex_metrics": self._extract_key_gex_metrics(gex_data),
            # Fed adjustments
            "pattern_weight_adjustments": pattern_adjustments,
            "fed_insights": self._generate_fed_insights(fed_context, gex_data),
            # Summary
            "top_pattern": self._identify_top_pattern(adjusted_patterns, confidence_scores),
            "risk_assessment": self._assess_current_risk(fed_context, gex_data, adjusted_patterns),
        }

    def run_historical_analysis(
        self, historical_data: pd.DataFrame, start_date: str = None, end_date: str = None
    ) -> Dict:
        """Run comprehensive historical pattern analysis.

        Args:
            historical_data: DataFrame with historical GEX and price data
            start_date: Start date for analysis
            end_date: End date for analysis

        Returns:
            Dictionary with historical analysis results
        """
        logger.info("Running historical pattern analysis")

        # Filter date range if specified
        if start_date or end_date:
            historical_data = self._filter_date_range(historical_data, start_date, end_date)

        if len(historical_data) < 50:
            logger.warning("Insufficient historical data for reliable analysis")
            return {"error": "Insufficient historical data (minimum 50 days required)"}

        # 1. Analyze pattern outcomes
        pattern_outcomes = {}
        pattern_names = self._extract_pattern_names(historical_data)

        for pattern in pattern_names:
            outcome_analysis = self.probability_mapper.analyze_pattern_outcomes(
                pattern_name=pattern, historical_data=historical_data, lookforward_days=1
            )
            pattern_outcomes[pattern] = outcome_analysis

        # 2. Calculate conditional probabilities
        conditional_probs = self.probability_mapper.calculate_conditional_probabilities(
            historical_data=historical_data, pattern_names=pattern_names
        )

        # 3. Statistical validation
        statistical_results = self.statistical_validator.calculate_significance(pattern_outcomes)

        # 4. Identify high conviction setups
        high_conviction = self.probability_mapper.identify_high_conviction_setups(
            conditional_probs=conditional_probs, min_win_rate=0.65, min_sample_size=20
        )

        # 5. Confidence scoring
        confidence_results = self.confidence_scorer.batch_score_patterns(
            patterns_data=pattern_outcomes, statistical_results=statistical_results
        )

        return {
            "analysis_period": f"{historical_data.index[0]} to {historical_data.index[-1]}",
            "total_days": len(historical_data),
            "patterns_analyzed": len(pattern_names),
            # Core results
            "pattern_outcomes": pattern_outcomes,
            "conditional_probabilities": conditional_probs,
            "statistical_validation": statistical_results,
            "high_conviction_setups": high_conviction,
            "confidence_scores": confidence_results,
            # Summary insights
            "best_performing_patterns": self._identify_best_patterns(pattern_outcomes),
            "statistically_significant_patterns": self._extract_significant_patterns(statistical_results),
            "recommended_strategies": self._generate_strategy_recommendations(high_conviction),
        }

    def generate_comprehensive_report(
        self, current_analysis: Dict = None, historical_analysis: Dict = None, output_path: str = None
    ) -> str:
        """Generate comprehensive pattern analysis report.

        Args:
            current_analysis: Current pattern analysis results
            historical_analysis: Historical pattern analysis results
            output_path: Output file path

        Returns:
            Path to generated report
        """
        if output_path is None:
            timestamp = now_iso().replace(":", "-")
            output_path = Path(".cache/pattern_analysis") / f"comprehensive_report_{timestamp}.txt"
            output_path.parent.mkdir(parents=True, exist_ok=True)

        report_lines = [
            "=" * 100,
            "COMPREHENSIVE PATTERN ANALYSIS REPORT",
            "=" * 100,
            f"Generated: {now_iso()}",
            f"Analysis Engine: Pattern-Outcome Probability Mapping (Issue #37)",
            "",
        ]

        # Current analysis section
        if current_analysis:
            report_lines.extend(
                [
                    "CURRENT MARKET ANALYSIS",
                    "-" * 50,
                    f"Analysis Date: {current_analysis['analysis_date']}",
                    f"Patterns Detected: {current_analysis['pattern_count']}",
                    f"Fed Environment: {current_analysis['fed_context']['fed_environment']}",
                    f"Market Stress: {current_analysis['fed_context']['market_stress_level']}",
                    "",
                ]
            )

            # Current patterns
            if current_analysis["detected_patterns"]:
                report_lines.append("Detected Patterns:")
                for pattern in current_analysis["detected_patterns"]:
                    conf = pattern.get("confidence", 0)
                    report_lines.append(f"  • {pattern['pattern'].upper()}: {conf}% confidence")
                    report_lines.append(f"    └─ {pattern.get('details', 'No details')}")
                report_lines.append("")

            # Top pattern
            if current_analysis.get("top_pattern"):
                top = current_analysis["top_pattern"]
                report_lines.extend(
                    [
                        f"TOP PATTERN: {top['pattern'].upper()}",
                        f"  Confidence: {top['confidence']}%",
                        f"  Details: {top.get('details', 'No details')}",
                        "",
                    ]
                )

        # Historical analysis section
        if historical_analysis:
            report_lines.extend(
                [
                    "HISTORICAL PATTERN ANALYSIS",
                    "-" * 50,
                    f"Analysis Period: {historical_analysis['analysis_period']}",
                    f"Total Days: {historical_analysis['total_days']}",
                    f"Patterns Analyzed: {historical_analysis['patterns_analyzed']}",
                    "",
                ]
            )

            # High conviction setups
            if historical_analysis.get("high_conviction_setups"):
                report_lines.append("HIGH CONVICTION SETUPS:")
                for i, setup in enumerate(historical_analysis["high_conviction_setups"][:5], 1):
                    report_lines.extend(
                        [
                            f"  {i}. {setup['pattern'].upper()}",
                            f"     Win Rate: {setup['win_rate']*100:.1f}%",
                            f"     Sample Size: {setup['sample_size']}",
                            f"     Context: {setup['context']}",
                            "",
                        ]
                    )

            # Statistical significance
            if historical_analysis.get("statistically_significant_patterns"):
                sig_patterns = historical_analysis["statistically_significant_patterns"]
                report_lines.extend(
                    ["STATISTICALLY SIGNIFICANT PATTERNS:", f"  Total: {len(sig_patterns)} patterns", ""]
                )
                for pattern in sig_patterns[:3]:  # Top 3
                    report_lines.append(f"  • {pattern}")

        report_lines.extend(
            [
                "=" * 100,
                "METHODOLOGY NOTES",
                "-" * 50,
                "• Pattern detection uses 6-category GEX framework",
                "• Fed context integration enhances pattern reliability",
                "• Statistical validation ensures significance vs random chance",
                "• Confidence scoring combines multiple reliability factors",
                "• Conditional probabilities account for market regime effects",
                "",
                "=" * 100,
                "End of Report",
            ]
        )

        # Write report
        with open(output_path, "w") as f:
            f.write("\n".join(report_lines))

        logger.info(f"Comprehensive report saved to: {output_path}")
        return str(output_path)

    def _apply_fed_adjustments(self, patterns: List[Dict], adjustments: Dict) -> List[Dict]:
        """Apply Fed context weight adjustments to pattern confidence."""
        adjusted_patterns = []

        for pattern in patterns:
            pattern_name = pattern["pattern"]
            base_confidence = pattern["confidence"]

            # Get Fed weight adjustment
            weight = adjustments.get(pattern_name, 1.0)
            adjusted_confidence = min(95, base_confidence * weight)

            adjusted_pattern = pattern.copy()
            adjusted_pattern["confidence"] = round(adjusted_confidence, 1)
            adjusted_pattern["fed_weight"] = weight
            adjusted_pattern["base_confidence"] = base_confidence

            if weight != 1.0:
                adjusted_pattern["details"] += f" (Fed-adjusted: {weight:.1f}x)"

            adjusted_patterns.append(adjusted_pattern)

        return adjusted_patterns

    def _calculate_pattern_confidences(self, patterns: List[Dict], fed_context: Dict) -> Dict:
        """Calculate confidence scores for detected patterns."""
        confidence_scores = {}

        for pattern in patterns:
            pattern_name = pattern["pattern"]

            # Create mock pattern data for confidence scoring
            pattern_data = {
                "pattern": pattern_name,
                "total_occurrences": 50,  # Mock data - would use real historical data
                "win_rate": pattern["confidence"],
                "mean_return": 1.5,  # Mock data
            }

            # Calculate confidence score
            confidence_result = self.confidence_scorer.calculate_pattern_confidence(
                pattern_data=pattern_data, market_context=fed_context
            )

            confidence_scores[pattern_name] = confidence_result

        return confidence_scores

    def _extract_key_gex_metrics(self, gex_data: Dict) -> Dict:
        """Extract key GEX metrics for reporting."""
        return {
            "net_gex": gex_data.get("net_gex", 0),
            "spot_price": gex_data.get("spot_price", 0),
            "flip_point": gex_data.get("flip_point"),
            "regime": gex_data.get("regime", "unknown"),
            "call_wall": gex_data.get("call_wall"),
            "put_support": gex_data.get("put_support"),
        }

    def _generate_fed_insights(self, fed_context: Dict, gex_data: Dict) -> List[str]:
        """Generate Fed-specific insights for current conditions."""
        insights = []

        # FOMC proximity insights
        days_to_fomc = fed_context["fomc"].get("days_to_fomc")
        if days_to_fomc and days_to_fomc <= 7:
            insights.append(f"FOMC meeting in {days_to_fomc} days - volatility risk elevated")

        # Market stress insights
        stress_regime = fed_context["stress"].get("stress_regime", "normal")
        if stress_regime == "elevated":
            insights.append("Elevated market stress - pattern reliability may be reduced")
        elif stress_regime == "extreme":
            insights.append("Extreme market stress - focus on high-confidence patterns only")

        # GEX regime insights
        gex_regime = gex_data.get("regime", "")
        if "NEGATIVE_GAMMA" in gex_regime:
            insights.append("Negative gamma regime - dealer hedging amplifies moves")
        elif "POSITIVE_GAMMA" in gex_regime:
            insights.append("Positive gamma regime - dealer hedging provides support")

        return insights

    def _identify_top_pattern(self, patterns: List[Dict], confidence_scores: Dict) -> Optional[Dict]:
        """Identify the highest confidence pattern."""
        if not patterns:
            return None

        top_pattern = max(patterns, key=lambda p: p["confidence"])

        # Enhance with confidence score data if available
        pattern_name = top_pattern["pattern"]
        if pattern_name in confidence_scores:
            confidence_data = confidence_scores[pattern_name]
            top_pattern["confidence_level"] = confidence_data["confidence_level"]
            top_pattern["reliability"] = confidence_data["reliability"]

        return top_pattern

    def _assess_current_risk(self, fed_context: Dict, gex_data: Dict, patterns: List[Dict]) -> Dict:
        """Assess current market risk based on all factors."""
        risk_factors = []
        risk_score = 50  # Base neutral score

        # Fed risk factors
        if fed_context["fomc"].get("is_fomc_week"):
            risk_factors.append("FOMC week volatility")
            risk_score += 15

        if fed_context["stress"].get("stress_regime") == "elevated":
            risk_factors.append("Elevated market stress")
            risk_score += 10
        elif fed_context["stress"].get("stress_regime") == "extreme":
            risk_factors.append("Extreme market stress")
            risk_score += 25

        # GEX risk factors
        net_gex = gex_data.get("net_gex", 0)
        if net_gex < -5e9:
            risk_factors.append("Extreme negative gamma")
            risk_score += 20
        elif net_gex < 0:
            risk_factors.append("Negative gamma regime")
            risk_score += 10

        # Pattern risk factors
        high_conf_patterns = [p for p in patterns if p["confidence"] > 80]
        if len(high_conf_patterns) > 2:
            risk_factors.append("Multiple high-confidence patterns")
            risk_score += 5

        # Determine risk level
        if risk_score > 80:
            risk_level = "High Risk"
        elif risk_score > 60:
            risk_level = "Elevated Risk"
        elif risk_score > 40:
            risk_level = "Moderate Risk"
        else:
            risk_level = "Low Risk"

        return {
            "risk_level": risk_level,
            "risk_score": min(100, risk_score),
            "risk_factors": risk_factors,
            "recommendation": self._generate_risk_recommendation(risk_level, risk_factors),
        }

    def _generate_risk_recommendation(self, risk_level: str, risk_factors: List[str]) -> str:
        """Generate risk-based trading recommendation."""
        if risk_level == "High Risk":
            return "Consider defensive positioning and reduced position sizes"
        elif risk_level == "Elevated Risk":
            return "Exercise caution and focus on highest confidence setups only"
        elif risk_level == "Moderate Risk":
            return "Normal trading with standard risk management"
        else:
            return "Favorable environment for pattern-based strategies"

    def _check_opex_date(self, date_str: str) -> bool:
        """Check if date is options expiration (simplified)."""
        # Simplified OpEx detection - 3rd Friday of month
        # In production, would use proper options calendar
        date_obj = parse_date_string(date_str)
        return date_obj.weekday() == 4 and 15 <= date_obj.day <= 21

    def _calculate_days_after_opex(self, date_str: str) -> int:
        """Calculate days since last OpEx (simplified)."""
        # Simplified calculation - would use proper options calendar in production
        return 5  # Mock value

    def _filter_date_range(self, df: pd.DataFrame, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """Filter DataFrame by date range."""
        if start_date:
            df = df[df.index >= start_date]
        if end_date:
            df = df[df.index <= end_date]
        return df

    def _extract_pattern_names(self, df: pd.DataFrame) -> List[str]:
        """Extract pattern column names from DataFrame."""
        pattern_columns = [
            col
            for col in df.columns
            if col.startswith("pattern_")
            or col in ["gamma_trap", "gamma_flip", "pin_risk", "vol_squeeze", "dealer_reload", "liquidity_cascade"]
        ]
        return pattern_columns

    def _identify_best_patterns(self, pattern_outcomes: Dict) -> List[Dict]:
        """Identify best performing patterns from outcomes."""
        valid_patterns = [
            (name, data) for name, data in pattern_outcomes.items() if isinstance(data, dict) and "win_rate" in data
        ]

        sorted_patterns = sorted(valid_patterns, key=lambda x: x[1]["win_rate"], reverse=True)

        return [
            {
                "pattern": name,
                "win_rate": data["win_rate"],
                "sample_size": data.get("total_occurrences", 0),
                "avg_return": data.get("mean_return", 0),
            }
            for name, data in sorted_patterns[:5]
        ]

    def _extract_significant_patterns(self, statistical_results: Dict) -> List[str]:
        """Extract statistically significant patterns."""
        if "results" not in statistical_results:
            return []

        significant = []
        for pattern, result in statistical_results["results"].items():
            if isinstance(result, dict) and result.get("overall_significant", False):
                significant.append(pattern)

        return significant

    def _generate_strategy_recommendations(self, high_conviction: List[Dict]) -> List[str]:
        """Generate trading strategy recommendations."""
        if not high_conviction:
            return ["No high conviction setups identified - focus on risk management"]

        recommendations = []

        # Group by pattern type
        pattern_types = {}
        for setup in high_conviction:
            pattern = setup["pattern"]
            if pattern not in pattern_types:
                pattern_types[pattern] = []
            pattern_types[pattern].append(setup)

        for pattern, setups in pattern_types.items():
            avg_win_rate = np.mean([s["win_rate"] for s in setups])
            recommendations.append(f"Focus on {pattern.upper()} setups (avg {avg_win_rate*100:.1f}% win rate)")

        return recommendations[:3]  # Top 3 recommendations
