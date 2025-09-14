"""
High Conviction LLM Prompts
Generates refined prompts based on statistical pattern analysis with proper risk context.
"""

from typing import Dict, List


class HighConvictionPromptGenerator:
    """Generates high-conviction LLM prompts based on statistical analysis."""

    def __init__(self):
        # Statistical findings from our analysis
        self.pattern_insights = {
            'gamma_trap': {
                'win_rate': 60.0,
                'avg_return': -0.482,
                'max_return': 1.12,
                'min_return': -2.43,
                'sample_size': 5,
                'confidence_avg': 90.0,
                'regime': 'NEGATIVE_GAMMA_LOW',
                'key_insight': 'High win rate but negative avg return suggests timing/exit issues'
            }
        }

    def generate_refined_trading_prompt(self, date, gex_data: Dict, patterns: List[Dict]) -> str:
        """
        Generate refined LLM prompt that addresses the statistical findings properly.

        Focus: High win rate but negative expected return suggests the pattern 
        identifies direction correctly but exit timing needs refinement.
        """

        prompt_lines = [
            f"STATISTICAL PATTERN ANALYSIS - {date}",
            "=" * 60,
            "",
            "🎯 GAMMA EXPOSURE METRICS:",
            f"  Net GEX: ${gex_data.get('net_gex', 0):,.0f}",
            f"  Regime: {gex_data.get('gex_regime', 'Unknown')}",
            f"  Flip Point: ${gex_data.get('flip_point', 0):.2f}",
            f"  Spot Price: ${gex_data.get('spot_price', 0):.2f}",
            f"  Distance from Flip: {((gex_data.get('spot_price', 0) - gex_data.get('flip_point', 0)) / gex_data.get('flip_point', 1) * 100):.1f}%",
            "",
            "📊 PATTERN DETECTION & STATISTICAL VALIDATION:",
        ]

        high_conviction_patterns = []

        for pattern in patterns:
            pattern_name = pattern.get('pattern_name', 'unknown').lower()
            confidence = pattern.get('confidence', 0)

            if pattern_name in self.pattern_insights:
                insights = self.pattern_insights[pattern_name]

                prompt_lines.extend([
                    f"",
                    f"🔍 {pattern_name.upper()} DETECTED:",
                    f"  Current Confidence: {confidence:.0f}%",
                    f"  Historical Win Rate: {insights['win_rate']:.1f}% ({insights['sample_size']} samples)",
                    f"  Return Profile: {insights['min_return']:.2f}% to +{insights['max_return']:.2f}%",
                    f"  Average Return: {insights['avg_return']:.2f}%",
                    "",
                    f"  📈 STATISTICAL INSIGHT:",
                    f"  {insights['key_insight']}",
                    f"  → Pattern correctly identifies DIRECTION ({insights['win_rate']:.1f}% accuracy)",
                    f"  → EXIT TIMING needs refinement (negative avg return despite high win rate)",
                ])

                if confidence >= 85:  # High conviction threshold
                    high_conviction_patterns.append({
                        'name': pattern_name,
                        'confidence': confidence,
                        'insights': insights
                    })

        if high_conviction_patterns:
            prompt_lines.extend([
                "",
                "🎯 HIGH CONVICTION TRADING SETUP:",
                "=" * 40,
            ])

            for pattern_info in high_conviction_patterns:
                insights = pattern_info['insights']
                prompt_lines.extend([
                    f"Pattern: {pattern_info['name'].upper()}",
                    f"Confidence: {pattern_info['confidence']:.0f}%",
                    f"Historical Edge: {insights['win_rate']:.1f}% directional accuracy",
                    "",
                    f"⚠️  CRITICAL ANALYSIS REQUIRED:",
                    f"1. DIRECTION: Pattern shows {insights['win_rate']:.1f}% win rate → directional bias reliable",
                    f"2. MAGNITUDE: Average return {insights['avg_return']:.2f}% → small moves expected",
                    f"3. RISK: Max loss observed: {insights['min_return']:.2f}%",
                    f"4. OPPORTUNITY: Max gain observed: +{insights['max_return']:.2f}%",
                    "",
                ])
        else:
            prompt_lines.extend([
                "",
                "❌ No high-conviction patterns detected at this time.",
                "   Proceed with standard GEX regime analysis only.",
                ""
            ])

        prompt_lines.extend([
            "",
            "🧠 STRATEGIC ANALYSIS REQUEST:",
            "=" * 40,
            "",
            "Given the statistical evidence above, provide:",
            "",
            "1. DIRECTIONAL BIAS:",
            f"   - Primary direction based on {gex_data.get('gex_regime', 'current')} regime",
            "   - Pattern-based directional confirmation",
            "   - Probability assessment for the move",
            "",
            "2. POSITION STRUCTURE:",
            "   - Optimal position type (long/short, options/shares)",
            "   - Position sizing based on pattern confidence",
            "   - Time horizon (intraday vs. multi-day hold)",
            "",
            "3. RISK MANAGEMENT:",
            "   - Stop loss level based on historical max loss",
            "   - Profit taking strategy to address negative avg return issue",
            "   - Position monitoring criteria",
            "",
            "4. EXIT STRATEGY REFINEMENT:",
            "   - How to capture the directional edge while avoiding the negative drag",
            "   - Specific exit triggers or time-based rules",
            "   - Risk/reward optimization",
            "",
            "🎯 FOCUS: The pattern identifies direction well but exit timing needs work.",
            "   Design a strategy that captures the 60% directional accuracy",
            "   while minimizing the impact of poor average returns.",
        ])

        return "\n".join(prompt_lines)

    def generate_pattern_specific_rules(self, pattern_name):
        """Generate specific trading rules for a pattern based on statistical analysis."""

        if pattern_name.lower() not in self.pattern_insights:
            return {}

        insights = self.pattern_insights[pattern_name.lower()]

        return {
            'pattern': pattern_name.upper(),
            'entry_rule': f"Enter when {pattern_name.upper()} confidence ≥ 85%",
            'directional_bias': f"Pattern shows {insights['win_rate']:.1f}% directional accuracy",
            'position_sizing': "Conservative (2-5% portfolio) due to negative expected return",
            'stop_loss': f"Set stop at -{abs(insights['min_return']) * 0.8:.1f}% (80% of max observed loss)",
            'profit_target': f"Take profits at +{insights['max_return'] * 0.7:.1f}% (70% of max observed gain)",
            'time_horizon': "1-2 days maximum to avoid return drag",
            'regime_context': f"Most effective in {insights['regime']} regime",
            'risk_warning': f"Negative expected return ({insights['avg_return']:.2f}%) despite {insights['win_rate']:.1f}% win rate",
            'refinement_needed': "Exit strategy optimization critical for profitability"
        }

    def create_llm_system_prompt(self) -> str:
        """Create system prompt for LLM with statistical context."""

        return """You are a quantitative trading analyst specializing in gamma exposure (GEX) pattern analysis. 

Your analysis is informed by statistical research showing:

GAMMA_TRAP Pattern:
- 60% directional accuracy (5 historical samples)
- Average return: -0.48% (indicates exit timing issues)
- Max gain: +1.12% | Max loss: -2.43%
- Most effective in NEGATIVE_GAMMA_LOW regimes

KEY INSIGHTS:
1. Patterns show directional edge but poor average returns
2. This suggests correct direction identification but suboptimal exit timing
3. Focus on capturing directional accuracy while minimizing return drag

ANALYSIS FRAMEWORK:
1. Assess GEX regime impact on market behavior
2. Validate patterns against statistical historical performance
3. Design risk-managed strategies that optimize for win rate over average return
4. Emphasize exit strategy refinement for pattern-based trades

Always provide specific, actionable recommendations with clear risk parameters."""
