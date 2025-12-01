"""
Mechanics Prompt Builder - Matches exact format from Issue #51
Builds prompts for LLM to identify WHO is forcing WHOM to do WHAT
"""

import datetime
import logging
from typing import Dict, List

from src.utils.config_manager import get_config

# Use date_utils for datetime operations
from src.utils.date_utils import (
    add_business_days,
    calculate_duration_minutes,
    now_timestamp,
    parse_date_string,
    today_str,
)

logger = logging.getLogger(__name__)


class MechanicsPromptBuilder:
    """Build prompts that match the exact format for market mechanics interpretation."""

    def __init__(self):
        """Initialize prompt builder with config values."""
        config = get_config()

        # Load IV thresholds from config
        self.iv_extremely_low = config.get("llm_market_mechanics.prompt_builder.iv_thresholds.extremely_low", 12)
        self.iv_low = config.get("llm_market_mechanics.prompt_builder.iv_thresholds.low", 15)
        self.iv_moderate = config.get("llm_market_mechanics.prompt_builder.iv_thresholds.moderate", 20)
        self.iv_elevated = config.get("llm_market_mechanics.prompt_builder.iv_thresholds.elevated", 25)
        self.iv_high = config.get("llm_market_mechanics.prompt_builder.iv_thresholds.high", 35)

    @staticmethod
    def build_analysis_prompt(
        date: datetime.datetime, gex_metrics: Dict, options_flow: Dict, market_context: Dict
    ) -> str:
        """Build analysis prompt in the exact format from the example.

        Args:
            date: Analysis date
            gex_metrics: GEX calculations
            options_flow: Options flow patterns
            market_context: Price action and temporal context

        Returns:
            Formatted prompt for LLM analysis
        """

        # Format date
        date_str = date.strftime("%B %d, %Y")

        # Enhanced GEX analysis with strike-level intelligence
        gex_section = f"""ENHANCED GEX ANALYSIS - {date_str}
- Net GEX: ${gex_metrics.get('net_gex', 0)/1e9:.1f}B ({gex_metrics.get('gex_regime', 'UNKNOWN')})"""

        # Add strike-level intelligence if available
        if "strike_level_patterns" in market_context:
            patterns = market_context["strike_level_patterns"]

            # Gamma concentration intelligence
            gamma_data = patterns.get("gamma_concentration", {})
            if gamma_data:
                gex_section += f"""
- GAMMA CONCENTRATION: {gamma_data.get('concentration_pct', 0):.1%} at ${gamma_data.get('max_strike', 0):.0f} strike
- Distance from spot: {gamma_data.get('distance_from_spot', 0):.3f}% ({abs(gamma_data.get('distance_from_spot', 0)):.1%} away)"""

            # Volume anomalies
            volume_data = patterns.get("volume_anomalies", {})
            if volume_data.get("detected", False):
                gex_section += f"""
- VOLUME ANOMALY: {volume_data.get('max_volume', 0):,.0f} contracts at ${volume_data.get('max_volume_strike', 0):.0f} ({volume_data.get('vs_average', 0):.1f}x average)"""

            # Pin setup intelligence (Issue #73 validated)
            pin_data = patterns.get("pin_setup", {})
            if pin_data.get("pin_probability", 0) > 0.60:
                validation_note = " (75% VALIDATED SETUP)" if pin_data.get("validated_setup", False) else ""
                gex_section += f"""
- PIN SETUP: {pin_data.get('pin_probability', 0):.1%} probability toward ${pin_data.get('target_strike', 0):.0f}{validation_note}"""

            # Gamma walls
            gamma_walls = patterns.get("gamma_walls", {})
            if gamma_walls.get("resistance_strikes") or gamma_walls.get("support_strikes"):
                resistance = gamma_walls.get("resistance_strikes", [])
                support = gamma_walls.get("support_strikes", [])
                gex_section += f"""
- GAMMA WALLS: Resistance at {resistance[:3]}, Support at {support[:3]} ({gamma_walls.get('strength', 'medium')} strength)"""

        # Add basic GEX metrics
        gex_section += f"""
- Flip point: ${gex_metrics.get('flip_point', 0):.0f}
- Current price: ${gex_metrics.get('spot_price', 0):.2f}"""

        # Add key strikes if available
        if "key_strikes" in gex_metrics:
            strikes_info = gex_metrics["key_strikes"]
            if "heavy_put_oi" in strikes_info:
                gex_section += f"\n- Key strikes: Heavy put OI at ${strikes_info['heavy_put_oi']}"
            if "call_walls" in strikes_info:
                gex_section += f", call walls at ${strikes_info['call_walls']}"
        elif "strike_distribution" in market_context:
            strike_dist = market_context["strike_distribution"]
            if strike_dist.get("max_oi_strike"):
                gex_section += f"\n- Key strikes: Max OI at ${strike_dist['max_oi_strike']:.0f}"

        # Build options flow section
        flow_section = "OPTIONS FLOW:"

        # Morning flow
        if "morning_flow" in options_flow:
            flow_section += f"\n- Morning: {options_flow['morning_flow']}"
        elif "sweep_orders" in options_flow:
            flow_section += f"\n- Morning: {options_flow['sweep_orders']}"
        else:
            # Generate from put/call ratios
            pcr = options_flow.get("put_call_ratio", 0)
            if pcr > 1.2:
                flow_section += f"\n- Morning: Heavy put buying (P/C ratio: {pcr:.2f})"
            elif pcr < 0.8:
                flow_section += f"\n- Morning: Heavy call buying (P/C ratio: {pcr:.2f})"
            else:
                flow_section += f"\n- Morning: Balanced flow (P/C ratio: {pcr:.2f})"

        # Afternoon flow
        if "afternoon_flow" in options_flow:
            flow_section += f"\n- Afternoon: {options_flow['afternoon_flow']}"
        elif "price_action" in market_context:
            price_action = market_context["price_action"]
            if price_action.get("tests_of_level"):
                flow_section += f"\n- Afternoon: {price_action['tests_of_level']}"
            else:
                flow_section += f"\n- Afternoon: {price_action.get('trend', 'Sideways')} trend continuation"

        # Unusual activity
        if "unusual_activity" in options_flow:
            flow_section += f"\n- Unusual: {options_flow['unusual_activity']}"
        else:
            # Generate unusual activity from data
            if gex_metrics.get("gex_regime") == "NEGATIVE_GAMMA_LOW":
                oipcr = options_flow.get("oi_put_call_ratio", 0)
                if oipcr < 0.7:
                    flow_section += "\n- Unusual: Put selling despite negative gamma"
                elif options_flow.get("volume_vs_oi", 0) > 0.5:
                    flow_section += "\n- Unusual: High volume vs OI - new positioning"

        # Build context section
        context_section = "CONTEXT:"

        # Temporal context
        temporal = market_context.get("temporal_context", {})

        # OPEX context
        if temporal.get("is_opex"):
            if temporal.get("day_of_week") == "Thursday":
                context_section += "\n- Day before OPEX"
            elif temporal.get("day_of_week") == "Friday":
                context_section += "\n- OPEX day"
            else:
                context_section += "\n- OPEX week"
        elif temporal.get("days_to_fomc", 999) <= 1:
            context_section += "\n- Day before FOMC"
        elif temporal.get("is_month_end"):
            context_section += "\n- Month-end rebalancing period"

        # Volatility context
        if "volatility_surface" in market_context:
            vol_surface = market_context["volatility_surface"]
            atm_iv = vol_surface.get("atm_iv", 0)
            if atm_iv > 0:
                # Use instance method instead of static
                builder_instance = MechanicsPromptBuilder()
                iv_percentile = builder_instance._get_iv_percentile(atm_iv)
                context_section += f"\n- VIX at {atm_iv*100:.0f} ({iv_percentile} volatility environment)"

        # Price tests/levels
        if "price_tests" in market_context:
            context_section += f"\n- {market_context['price_tests']}"
        else:
            # Generate from price action
            spot = gex_metrics.get("spot_price", 0)
            flip = gex_metrics.get("flip_point", 0)
            if spot and flip:
                distance_pct = abs(spot - flip) / flip * 100
                if distance_pct < 0.5:
                    context_section += f"\n- Price pinned at flip point ${flip:.0f}"
                elif spot < flip and distance_pct < 2:
                    context_section += f"\n- Testing resistance at flip point ${flip:.0f}"
                elif spot > flip and distance_pct < 2:
                    context_section += f"\n- Testing support at flip point ${flip:.0f}"

        # Build the final prompt
        prompt = f"""{gex_section}

{flow_section}

{context_section}

QUESTION: Analyze the market mechanics using the WHO forces WHOM to do WHAT framework.

WHO: Identify the key market participant taking action (retail traders, institutions, dealers, etc.)
WHOM: Identify who is being forced to respond (dealers, market makers, other participants)
WHAT: Describe the specific forced action (buy/sell, hedge, rebalance)

Provide your analysis in this exact format:
WHO: [Primary actor]
WHOM: [Forced participant]
WHAT: [Specific forced action]
CONFIDENCE: [0-100%]
NARRATIVE: [2-3 sentence explanation of the mechanics]"""

        return prompt

    @staticmethod
    def build_expected_response_template(
        pattern_identified: str,
        key_players: List[Dict],
        mechanics: str,
        likely_outcome: Dict,
        actionable_intelligence: List[str],
    ) -> str:
        """Build expected response format for validation.

        This shows what we expect the LLM to return.
        """

        response = f"""MARKET MECHANICS ANALYSIS:

PATTERN IDENTIFIED: "{pattern_identified}"

KEY PLAYERS:"""

        for i, player in enumerate(key_players, 1):
            response += f"\n{i}. {player['who']}: {player['what']}"

        response += f"\n\nMECHANICS:\n{mechanics}"

        response += f"\n\nLIKELY OUTCOME:"
        for outcome, probability in likely_outcome.items():
            response += f"\n- {probability}% probability: {outcome}"

        response += f"\n\nACTIONABLE INTELLIGENCE:"
        for action in actionable_intelligence:
            response += f"\n- {action}"

        return response

    @staticmethod
    def parse_llm_response(response: str) -> Dict:
        """Parse LLM response into structured format.

        Args:
            response: Raw LLM response text

        Returns:
            Structured interpretation dict
        """

        try:
            # Initialize result
            result = {
                "pattern_identified": None,
                "key_players": [],
                "mechanics": None,
                "likely_outcomes": [],
                "actionable_intelligence": [],
                "raw_response": response,
            }

            lines = response.split("\n")
            current_section = None

            for line in lines:
                line = line.strip()

                # Identify sections
                if "PATTERN IDENTIFIED:" in line:
                    # Extract pattern name in quotes
                    import re

                    pattern_match = re.search(r'"([^"]+)"', line)
                    if pattern_match:
                        result["pattern_identified"] = pattern_match.group(1)
                    current_section = "pattern"

                elif "KEY PLAYERS:" in line:
                    current_section = "players"

                elif "MECHANICS:" in line:
                    current_section = "mechanics"
                    mechanics_text = []

                elif "LIKELY OUTCOME:" in line:
                    current_section = "outcomes"

                elif "ACTIONABLE INTELLIGENCE:" in line:
                    current_section = "actionable"

                # Parse sections
                elif current_section == "players" and line.startswith(("1.", "2.", "3.")):
                    # Parse player line
                    parts = line[2:].split(":", 1)
                    if len(parts) == 2:
                        result["key_players"].append({"who": parts[0].strip(), "what": parts[1].strip()})

                elif current_section == "mechanics" and line and not line.startswith("LIKELY"):
                    if "mechanics_text" not in locals():
                        mechanics_text = []
                    mechanics_text.append(line)

                elif current_section == "outcomes" and line.startswith("-"):
                    # Parse outcome probability
                    import re

                    prob_match = re.search(r"(\d+)%\s+probability:\s+(.+)", line)
                    if prob_match:
                        result["likely_outcomes"].append(
                            {"probability": int(prob_match.group(1)), "outcome": prob_match.group(2)}
                        )

                elif current_section == "actionable" and line.startswith("-"):
                    # Parse actionable item
                    action = line[1:].strip()
                    result["actionable_intelligence"].append(action)

            # Join mechanics text
            if "mechanics_text" in locals():
                result["mechanics"] = "\n".join(mechanics_text)

            return result

        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
            return {"pattern_identified": "Parse Error", "raw_response": response, "error": str(e)}

    def _get_iv_percentile(self, iv: float) -> str:
        """Convert IV to percentile description using config thresholds."""
        vix_equiv = iv * 100

        if vix_equiv < self.iv_extremely_low:
            return "extremely low"
        elif vix_equiv < self.iv_low:
            return "low"
        elif vix_equiv < self.iv_moderate:
            return "moderate"
        elif vix_equiv < self.iv_elevated:
            return "elevated"
        elif vix_equiv < self.iv_high:
            return "high"
        else:
            return "extreme"

    @staticmethod
    def build_regime_prompt(gex_sequence: List[Dict], end_date: str = None) -> str:
        """Build regime detection prompt for 30-day GEX window analysis (Paper #2).

        NOTE: Prompt structure is documented in config_defaults/llm_prompts.yaml under
        paper2_prompts.regime_classification. Current implementation uses hardcoded prompt
        for simplicity. Config-based loading can be implemented when A/B testing is needed.

        Args:
            gex_sequence: List of dicts with 'date', 'net_gex_usd', 'positive_gex', 'negative_gex'
            end_date: Optional end date for logging (not used in prompt - obfuscation)

        Returns:
            Complete regime detection prompt text
        """
        # Format GEX data table
        gex_lines = []
        for day in gex_sequence:
            date_label = day["date"]  # Already obfuscated (Day T-29, etc.)
            net_gex_b = day["net_gex_usd"] / 1e9  # Convert to billions
            sign = "+" if net_gex_b >= 0 else ""
            gex_lines.append(f"{date_label}: {sign}{net_gex_b:.2f}B")

        gex_data_table = "\n".join(gex_lines)

        # Build prompt (hardcoded for stability, documented in config)
        # See config_defaults/llm_prompts.yaml for externalized structure
        prompt = f"""You are a market structure analyst specializing in dealer gamma positioning regimes.

TASK: Analyze this 30-day period and determine if it represents a PERSISTENT regime where dealer constraints create forced, directional flows.

## 30-DAY GEX DATA

{gex_data_table}

## REGIME CLASSIFICATION FRAMEWORK

### PERSISTENT REGIMES (Detect These)

**1. PERSISTENT POSITIVE REGIME**
- Definition: Dealers are LONG gamma, forced to sell into strength
- Criteria:
  * >70% of days (21+/30) have positive net GEX
  * Average magnitude >$5B
  * ≤5 sign flips across 30 days
  * Stable directional constraint

**Mechanism**: When dealers hold long gamma:
- Price rises → Dealers MUST sell shares (rebalance)
- Price falls → Dealers MUST buy shares (rebalance)
- Creates dampening, mean-reverting flows
- Constraint is STRUCTURAL (dealers cannot avoid)

**2. PERSISTENT NEGATIVE REGIME**
- Definition: Dealers are SHORT gamma, forced to buy into strength
- Criteria:
  * >70% of days (21+/30) have negative net GEX
  * Average magnitude >$5B
  * ≤5 sign flips across 30 days
  * Stable directional constraint

**Mechanism**: When dealers hold short gamma:
- Price rises → Dealers MUST buy shares (chase)
- Price falls → Dealers MUST sell shares (chase)
- Creates amplifying, momentum flows
- Constraint is STRUCTURAL (dealers cannot avoid)

---

### NON-REGIMES (Reject These)

**3. TRANSITIONAL (Reject)**
- Frequent sign flips between positive/negative GEX
- No dominant regime direction (less than 70% same sign)
- Market in regime change period
- Example: 15 positive days, 15 negative days (50/50 split)

**Why Reject**: No persistent constraint. Dealers face mixed conditions daily. Not a structural regime.

**4. LOW CONVICTION (Reject)**
- Consistent sign BUT weak magnitude (<$5B average)
- Example: 25 days positive, avg $2B GEX
- Insufficient constraint to create persistent forced flows

**Why Reject**: Even if sign is consistent, magnitude too weak to force dealers into meaningful positions. Not a structural constraint.

---

## ANALYSIS QUESTIONS

Systematically evaluate the 30-day window:

**Step 1: Sign Persistence**
1. Count days with positive net GEX
2. Count days with negative net GEX
3. Calculate persistence percentage: max(positive_days, negative_days) / 30 * 100
4. Does it meet 70% threshold (21+ days)?

**Step 2: Magnitude Assessment**
1. Calculate average GEX magnitude (absolute value): sum(|net_gex|) / 30
2. Is average magnitude ≥$5B?
3. Check for extreme outliers that might distort average

**Step 3: Stability Check**
1. Count sign flips: How many times does GEX switch from pos→neg or neg→pos?
2. Are there ≤5 sign flips across 30 days?
3. Stable regime should have low flip count

**Step 4: Regime Classification**
- If Steps 1, 2, 3 all pass AND positive dominates → PERSISTENT POSITIVE
- If Steps 1, 2, 3 all pass AND negative dominates → PERSISTENT NEGATIVE
- If Step 1 passes but Step 2 fails → LOW CONVICTION (reject)
- If Step 1 fails → TRANSITIONAL (reject)

---

## CONFIDENCE CALIBRATION (Mechanical Guidance)

Use these concrete anchors to calibrate confidence:

**90-100 (Very High Confidence)**
- 25-30 days same sign (83-100% persistence)
- Average magnitude >$10B
- 0-2 sign flips (highly stable)
- Example: "29 negative days, avg $15B, 1 flip"

**70-89 (High Confidence)**
- 21-24 days same sign (70-80% persistence)
- Average magnitude $5-10B
- 2-4 sign flips (moderately stable)
- Example: "23 negative days, avg $7B, 3 flips"

**50-69 (Borderline - Use with Caution)**
- 18-20 days same sign (60-67% persistence)
- Average magnitude $3-5B
- 5-7 sign flips
- Example: "20 negative days, avg $4B, 6 flips"
- **Note**: Borderline cases should generally be REJECTED unless other factors strengthen confidence

**0-49 (Reject - Not Persistent)**
- <18 days same sign (<60% persistence)
- OR average magnitude <$3B
- OR >7 sign flips
- These are NOT persistent regimes

**Important**: Confidence is a FILTER, not a probability. Use it to distinguish clear regimes (70+) from borderline (50-69) from noise (<50).

---

## OUTPUT FORMAT (JSON)

Provide your analysis in this exact JSON structure:

```json
{{
    "regime_detected": true/false,
    "regime_type": "persistent_positive|persistent_negative|transitional|low_conviction",
    "positive_days": <count as integer>,
    "negative_days": <count as integer>,
    "avg_magnitude_billions": <value as number>,
    "sign_flips": <count as integer>,
    "persistence_pct": <percentage as number>,
    "confidence": <integer 0-100>,
    "reasoning": "Explain step-by-step why this is/isn't a persistent regime. Reference specific metrics (persistence %, avg magnitude, sign flips). If rejecting, state which criterion failed."
}}
```

**IMPORTANT**: All numeric fields (confidence, positive_days, negative_days, sign_flips, avg_magnitude_billions, persistence_pct) MUST be numbers (integers or decimals), NOT words like "thirty-five" or "fifty".

**regime_detected Rules**:
- `true` ONLY if regime_type is "persistent_positive" or "persistent_negative"
- `false` if regime_type is "transitional" or "low_conviction"

---

## KEY PRINCIPLES

1. **Selectivity is Expected**: Most windows will NOT be persistent regimes (expect 30-50% detection rate)

2. **ALL Criteria Must Pass**: Persistence + Magnitude + Stability required for detection

3. **Rejection is Valid**: Saying "no persistent regime" is a correct answer for transitional/weak periods

4. **Mechanical Over Qualitative**: Use concrete thresholds (70%, $5B, 5 flips) rather than subjective judgment

5. **Structural Focus**: Only detect when dealers are FORCED into directional positions by constraints

Analyze the 30-day GEX data above and provide your regime classification in JSON format."""

        return prompt
