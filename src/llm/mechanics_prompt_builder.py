"""
Mechanics Prompt Builder - Matches exact format from Issue #51
Builds prompts for LLM to identify WHO is forcing WHOM to do WHAT
"""

from typing import Dict, List
import logging
import datetime

# Use date_utils instead of datetime
from src.utils.date_utils import (
    today_str,
    now_timestamp,
    parse_date_string,
    add_business_days,
    calculate_duration_minutes
)

logger = logging.getLogger(__name__)


class MechanicsPromptBuilder:
    """Build prompts that match the exact format for market mechanics interpretation."""

    @staticmethod
    def build_analysis_prompt(
        date: datetime.datetime,
        gex_metrics: Dict,
        options_flow: Dict,
        market_context: Dict
    ) -> str:
        """
        Build analysis prompt in the exact format from the example.

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

        # Build GEX analysis section
        gex_section = f"""GEX ANALYSIS - {date_str}
- Net GEX: ${gex_metrics.get('net_gex', 0)/1e9:.1f}B ({gex_metrics.get('gex_regime', 'UNKNOWN')})
- Flip point: ${gex_metrics.get('flip_point', 0):.0f}
- Current price: ${gex_metrics.get('spot_price', 0):.2f}"""

        # Add key strikes if available
        if 'key_strikes' in gex_metrics:
            strikes_info = gex_metrics['key_strikes']
            if 'heavy_put_oi' in strikes_info:
                gex_section += f"\n- Key strikes: Heavy put OI at ${strikes_info['heavy_put_oi']}"
            if 'call_walls' in strikes_info:
                gex_section += f", call walls at ${strikes_info['call_walls']}"
        elif 'strike_distribution' in market_context:
            strike_dist = market_context['strike_distribution']
            if strike_dist.get('max_oi_strike'):
                gex_section += f"\n- Key strikes: Max OI at ${strike_dist['max_oi_strike']:.0f}"

        # Build options flow section
        flow_section = "OPTIONS FLOW:"

        # Morning flow
        if 'morning_flow' in options_flow:
            flow_section += f"\n- Morning: {options_flow['morning_flow']}"
        elif 'sweep_orders' in options_flow:
            flow_section += f"\n- Morning: {options_flow['sweep_orders']}"
        else:
            # Generate from put/call ratios
            pcr = options_flow.get('put_call_ratio', 0)
            if pcr > 1.2:
                flow_section += f"\n- Morning: Heavy put buying (P/C ratio: {pcr:.2f})"
            elif pcr < 0.8:
                flow_section += f"\n- Morning: Heavy call buying (P/C ratio: {pcr:.2f})"
            else:
                flow_section += f"\n- Morning: Balanced flow (P/C ratio: {pcr:.2f})"

        # Afternoon flow
        if 'afternoon_flow' in options_flow:
            flow_section += f"\n- Afternoon: {options_flow['afternoon_flow']}"
        elif 'price_action' in market_context:
            price_action = market_context['price_action']
            if price_action.get('tests_of_level'):
                flow_section += f"\n- Afternoon: {price_action['tests_of_level']}"
            else:
                flow_section += f"\n- Afternoon: {price_action.get('trend', 'Sideways')} trend continuation"

        # Unusual activity
        if 'unusual_activity' in options_flow:
            flow_section += f"\n- Unusual: {options_flow['unusual_activity']}"
        else:
            # Generate unusual activity from data
            if gex_metrics.get('gex_regime') == 'NEGATIVE_GAMMA_LOW':
                oipcr = options_flow.get('oi_put_call_ratio', 0)
                if oipcr < 0.7:
                    flow_section += "\n- Unusual: Put selling despite negative gamma"
                elif options_flow.get('volume_vs_oi', 0) > 0.5:
                    flow_section += "\n- Unusual: High volume vs OI - new positioning"

        # Build context section
        context_section = "CONTEXT:"

        # Temporal context
        temporal = market_context.get('temporal_context', {})

        # OPEX context
        if temporal.get('is_opex'):
            if temporal.get('day_of_week') == 'Thursday':
                context_section += "\n- Day before OPEX"
            elif temporal.get('day_of_week') == 'Friday':
                context_section += "\n- OPEX day"
            else:
                context_section += "\n- OPEX week"
        elif temporal.get('days_to_fomc', 999) <= 1:
            context_section += "\n- Day before FOMC"
        elif temporal.get('is_month_end'):
            context_section += "\n- Month-end rebalancing period"

        # Volatility context
        if 'volatility_surface' in market_context:
            vol_surface = market_context['volatility_surface']
            atm_iv = vol_surface.get('atm_iv', 0)
            if atm_iv > 0:
                iv_percentile = MechanicsPromptBuilder._get_iv_percentile(
                    atm_iv)
                context_section += f"\n- VIX at {atm_iv*100:.0f} ({iv_percentile} volatility environment)"

        # Price tests/levels
        if 'price_tests' in market_context:
            context_section += f"\n- {market_context['price_tests']}"
        else:
            # Generate from price action
            spot = gex_metrics.get('spot_price', 0)
            flip = gex_metrics.get('flip_point', 0)
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
        actionable_intelligence: List[str]
    ) -> str:
        """
        Build expected response format for validation.

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
        """
        Parse LLM response into structured format.

        Args:
            response: Raw LLM response text

        Returns:
            Structured interpretation dict
        """

        try:
            # Initialize result
            result = {
                'pattern_identified': None,
                'key_players': [],
                'mechanics': None,
                'likely_outcomes': [],
                'actionable_intelligence': [],
                'raw_response': response
            }

            lines = response.split('\n')
            current_section = None

            for line in lines:
                line = line.strip()

                # Identify sections
                if 'PATTERN IDENTIFIED:' in line:
                    # Extract pattern name in quotes
                    import re
                    pattern_match = re.search(r'"([^"]+)"', line)
                    if pattern_match:
                        result['pattern_identified'] = pattern_match.group(1)
                    current_section = 'pattern'

                elif 'KEY PLAYERS:' in line:
                    current_section = 'players'

                elif 'MECHANICS:' in line:
                    current_section = 'mechanics'
                    mechanics_text = []

                elif 'LIKELY OUTCOME:' in line:
                    current_section = 'outcomes'

                elif 'ACTIONABLE INTELLIGENCE:' in line:
                    current_section = 'actionable'

                # Parse sections
                elif current_section == 'players' and line.startswith(('1.', '2.', '3.')):
                    # Parse player line
                    parts = line[2:].split(':', 1)
                    if len(parts) == 2:
                        result['key_players'].append({
                            'who': parts[0].strip(),
                            'what': parts[1].strip()
                        })

                elif current_section == 'mechanics' and line and not line.startswith('LIKELY'):
                    if 'mechanics_text' not in locals():
                        mechanics_text = []
                    mechanics_text.append(line)

                elif current_section == 'outcomes' and line.startswith('-'):
                    # Parse outcome probability
                    import re
                    prob_match = re.search(
                        r'(\d+)%\s+probability:\s+(.+)', line)
                    if prob_match:
                        result['likely_outcomes'].append({
                            'probability': int(prob_match.group(1)),
                            'outcome': prob_match.group(2)
                        })

                elif current_section == 'actionable' and line.startswith('-'):
                    # Parse actionable item
                    action = line[1:].strip()
                    result['actionable_intelligence'].append(action)

            # Join mechanics text
            if 'mechanics_text' in locals():
                result['mechanics'] = '\n'.join(mechanics_text)

            return result

        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
            return {
                'pattern_identified': 'Parse Error',
                'raw_response': response,
                'error': str(e)
            }

    @staticmethod
    def _get_iv_percentile(iv: float) -> str:
        """Convert IV to percentile description."""
        vix_equiv = iv * 100

        if vix_equiv < 12:
            return "extremely low"
        elif vix_equiv < 15:
            return "low"
        elif vix_equiv < 20:
            return "moderate"
        elif vix_equiv < 25:
            return "elevated"
        elif vix_equiv < 35:
            return "high"
        else:
            return "extreme"

