#!/usr/bin/env python3
"""
Issue #143: Raw Option Chain Validation (The Nuclear Option)

This script validates LLM structural reasoning by providing ONLY raw option
chain data (Strike, OI, IV, Bid/Ask) WITHOUT pre-calculated GEX metrics.

The goal is to prove the LLM can detect dealer constraints from the
distribution shape, not just by reading pre-calculated values.

Author: Claude Code (Chat C)
Date: November 25, 2025
"""

import sqlite3
import logging
import yaml
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RawChainExtractor:
    """Extract raw option chain data from database WITHOUT GEX calculations."""

    def __init__(self, db_path: str = '/mnt/bst/yxie2/cregan1/gex-llm-patterns/.cache/consolidated_historical.db'):
        """Initialize database connection."""
        self.db_path = db_path
        self.conn = None

    def connect(self):
        """Establish database connection."""
        self.conn = sqlite3.connect(self.db_path)
        logger.info(f"Connected to database: {self.db_path}")

    def disconnect(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")

    def get_raw_chain(self, date: str, symbol: str = 'SPY') -> pd.DataFrame:
        """
        Extract raw option chain aggregated by strike and type.

        DOES NOT calculate GEX, flip points, or any derived metrics.
        Only provides: strike, type, total OI, avg IV, total volume, bid/ask spread.

        Args:
            date: Date string (YYYY-MM-DD)
            symbol: Stock symbol (default: SPY)

        Returns:
            DataFrame with raw chain data aggregated by strike
        """
        if not self.conn:
            raise RuntimeError("Database not connected")

        # Aggregate across all expirations by strike and type
        query = """
            SELECT
                strike,
                option_type,
                SUM(open_interest) as total_oi,
                AVG(implied_volatility) as avg_iv,
                SUM(volume) as total_volume,
                AVG(bid) as avg_bid,
                AVG(ask) as avg_ask,
                MAX(underlying_price) as spot_price
            FROM raw_options_chain
            WHERE date = ? AND symbol = ?
            GROUP BY strike, option_type
            HAVING SUM(open_interest) > 0
            ORDER BY strike, option_type
        """

        df = pd.read_sql_query(query, self.conn, params=(date, symbol))
        return df

    def get_spot_price(self, date: str, symbol: str = 'SPY') -> Optional[float]:
        """Get spot price for a given date."""
        if not self.conn:
            return None

        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT MAX(underlying_price) FROM raw_options_chain
            WHERE date = ? AND symbol = ?
        """, (date, symbol))

        result = cursor.fetchone()
        return result[0] if result else None


class RawChainPromptBuilder:
    """Build LLM prompts from raw option chain data (NO pre-calculated GEX)."""

    # Template for raw chain analysis
    RAW_CHAIN_TEMPLATE = """Analyze this options market data to identify any structural constraints or forced actions.

**IMPORTANT**: You are provided ONLY with raw option chain data. You must reason about market structure from the distribution of open interest, implied volatility, and bid/ask spreads. NO pre-calculated metrics are provided.

---

**Date**: {obfuscated_date}
**Asset**: {obfuscated_ticker}
**Spot Price**: ${spot_price:.2f}

---

**Options Chain (Aggregated by Strike)**:

{strike_table}

---

**Analysis Task**:

Based ONLY on the raw options data above, identify:

1. **WHO**: What market participants are likely positioned and how? (e.g., dealers, institutional investors, retail)

2. **WHOM**: Who are the counterparties to these positions?

3. **WHAT**: What actions, if any, are these participants FORCED to take? What structural constraints exist?

4. **WHY**: Explain the mechanism - why are these actions forced?

5. **OUTCOME**: What market behavior would you expect as a result?

**Confidence**: Rate your confidence (0-100) that you have identified a genuine structural constraint.

Provide your analysis in the structured format above. If you do not detect any clear structural constraint, indicate "No pattern detected" with confidence = 0.
"""

    def __init__(self):
        """Initialize prompt builder."""
        pass

    def format_strike_table(self, chain_df: pd.DataFrame,
                           spot_price: float,
                           max_strikes: int = 60) -> str:
        """
        Format raw chain data as a readable table for LLM.

        Args:
            chain_df: DataFrame with raw chain data
            spot_price: Current spot price
            max_strikes: Maximum number of strikes to include (centered around spot)

        Returns:
            Formatted string table
        """
        if chain_df.empty:
            return "No options data available."

        # Get unique strikes and filter to those near the money
        unique_strikes = sorted(chain_df['strike'].unique())

        # Find ATM strike
        atm_strike = min(unique_strikes, key=lambda x: abs(x - spot_price))
        atm_idx = unique_strikes.index(atm_strike)

        # Select strikes around ATM
        half_window = max_strikes // 2
        start_idx = max(0, atm_idx - half_window)
        end_idx = min(len(unique_strikes), atm_idx + half_window)
        selected_strikes = unique_strikes[start_idx:end_idx]

        # Filter data
        filtered_df = chain_df[chain_df['strike'].isin(selected_strikes)]

        # Build table header
        lines = [
            "| Strike | Type | Open Interest | Avg IV | Volume | Bid/Ask Spread |",
            "|--------|------|---------------|--------|--------|----------------|"
        ]

        # Add rows
        for _, row in filtered_df.iterrows():
            strike = row['strike']
            opt_type = row['option_type'].capitalize()
            oi = int(row['total_oi'])
            iv = row['avg_iv'] * 100 if row['avg_iv'] else 0  # Convert to percentage
            volume = int(row['total_volume'])
            spread = row['avg_ask'] - row['avg_bid'] if row['avg_bid'] and row['avg_ask'] else 0

            # Mark ATM
            atm_marker = " (ATM)" if abs(strike - spot_price) < 1 else ""

            lines.append(
                f"| ${strike:,.0f}{atm_marker} | {opt_type:4} | {oi:>13,} | {iv:>5.1f}% | {volume:>6,} | ${spread:>6.2f} |"
            )

        return "\n".join(lines)

    def build_prompt(self, chain_df: pd.DataFrame,
                    spot_price: float,
                    date: str) -> str:
        """
        Build complete LLM prompt from raw chain data.

        Args:
            chain_df: DataFrame with raw chain data
            spot_price: Current spot price
            date: Original date (will be obfuscated)

        Returns:
            Complete prompt string
        """
        # Obfuscate date and ticker
        obfuscated_date = "Day T+0"
        obfuscated_ticker = "INDEX_1"

        # Format strike table
        strike_table = self.format_strike_table(chain_df, spot_price)

        # Build prompt
        prompt = self.RAW_CHAIN_TEMPLATE.format(
            obfuscated_date=obfuscated_date,
            obfuscated_ticker=obfuscated_ticker,
            spot_price=spot_price,
            strike_table=strike_table
        )

        return prompt


class RawChainResponseParser:
    """Parse LLM responses for raw chain analysis."""

    def parse_response(self, response: str) -> Dict:
        """
        Parse LLM response to extract detection and reasoning.

        Args:
            response: Raw LLM response text

        Returns:
            Dictionary with parsed fields
        """
        import re

        result = {
            'detected': False,
            'confidence': 0,
            'who': '',
            'whom': '',
            'what': '',
            'why': '',
            'outcome': '',
            'raw_response': response
        }

        # Check for "No pattern detected"
        if re.search(r'no (pattern|constraint|structure) detected', response, re.I):
            result['detected'] = False
            result['confidence'] = 0
            return result

        # Extract confidence
        confidence_match = re.search(r'confidence[:\s]*(\d+)', response, re.I)
        if confidence_match:
            result['confidence'] = int(confidence_match.group(1))
            result['detected'] = result['confidence'] >= 60

        # Extract WHO
        who_match = re.search(r'\*?\*?WHO\*?\*?[:\s]*(.+?)(?=\n\n|\*?\*?WHOM|\Z)', response, re.I | re.S)
        if who_match:
            result['who'] = who_match.group(1).strip()[:500]

        # Extract WHOM
        whom_match = re.search(r'\*?\*?WHOM\*?\*?[:\s]*(.+?)(?=\n\n|\*?\*?WHAT|\Z)', response, re.I | re.S)
        if whom_match:
            result['whom'] = whom_match.group(1).strip()[:500]

        # Extract WHAT
        what_match = re.search(r'\*?\*?WHAT\*?\*?[:\s]*(.+?)(?=\n\n|\*?\*?WHY|\Z)', response, re.I | re.S)
        if what_match:
            result['what'] = what_match.group(1).strip()[:500]

        # Extract WHY
        why_match = re.search(r'\*?\*?WHY\*?\*?[:\s]*(.+?)(?=\n\n|\*?\*?OUTCOME|\Z)', response, re.I | re.S)
        if why_match:
            result['why'] = why_match.group(1).strip()[:500]

        # Extract OUTCOME
        outcome_match = re.search(r'\*?\*?OUTCOME\*?\*?[:\s]*(.+?)(?=\n\n|\*?\*?Confidence|\Z)', response, re.I | re.S)
        if outcome_match:
            result['outcome'] = outcome_match.group(1).strip()[:500]

        return result

    def analyze_reasoning_quality(self, parsed: Dict) -> Dict:
        """
        Analyze the quality of LLM reasoning.

        Args:
            parsed: Parsed response dictionary

        Returns:
            Dictionary with reasoning quality scores
        """
        import re

        response = parsed.get('raw_response', '')

        quality = {
            'mentions_distribution_shape': bool(re.search(
                r'distribution|shape|skew|concentration|weighted|heavy', response, re.I)),
            'mentions_put_call_imbalance': bool(re.search(
                r'put.*call|call.*put|imbalance|ratio|skew', response, re.I)),
            'infers_positioning': bool(re.search(
                r'net (long|short)|aggregate|sum|total position', response, re.I)),
            'explains_hedging_mechanism': bool(re.search(
                r'hedge|delta|gamma|rebalance|forced|constrained|must', response, re.I)),
            'identifies_market_makers': bool(re.search(
                r'dealer|market maker|mm|liquidity provider', response, re.I)),
            'identifies_customers': bool(re.search(
                r'customer|retail|institutional|investor|trader', response, re.I))
        }

        # Calculate reasoning score (0-6)
        quality['reasoning_score'] = sum(quality.values()) - 1  # Subtract 1 for reasoning_score itself
        quality['reasoning_score'] = sum([
            quality['mentions_distribution_shape'],
            quality['mentions_put_call_imbalance'],
            quality['infers_positioning'],
            quality['explains_hedging_mechanism'],
            quality['identifies_market_makers'],
            quality['identifies_customers']
        ])

        return quality


class RawChainValidator:
    """Main validation orchestrator for raw chain analysis."""

    def __init__(self, output_dir: str = 'docs/papers/paper1/analysis'):
        """Initialize validator."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.extractor = RawChainExtractor()
        self.prompt_builder = RawChainPromptBuilder()
        self.parser = RawChainResponseParser()

    def get_test_sample(self, n_high: int = 25, n_low: int = 25) -> Tuple[List[str], List[str]]:
        """
        Get test sample dates: high-detection and low-detection from baseline.

        Args:
            n_high: Number of high-detection days to include
            n_low: Number of low-detection days to include

        Returns:
            Tuple of (high_detection_dates, low_detection_dates)
        """
        # Load baseline detection results
        baseline_path = Path('/mnt/bst/yxie2/cregan1/gex-llm-patterns/reports/validation/paper1_pattern_taxonomy/gamma_positioning_SPY_2024_unbiased.yaml')

        if not baseline_path.exists():
            logger.error(f"Baseline file not found: {baseline_path}")
            return [], []

        with open(baseline_path, 'r') as f:
            baseline = yaml.safe_load(f)

        detections = baseline.get('detections', [])

        high_detection_dates = []
        low_detection_dates = []

        for d in detections:
            date = d.get('date')
            detected = d.get('detected', False)
            confidence = d.get('narrative', {}).get('confidence', 0)

            if detected and confidence >= 80:
                high_detection_dates.append(date)
            elif not detected or confidence < 60:
                low_detection_dates.append(date)

        # Sample
        import random
        random.seed(42)  # Reproducibility

        high_sample = random.sample(high_detection_dates, min(n_high, len(high_detection_dates)))
        low_sample = random.sample(low_detection_dates, min(n_low, len(low_detection_dates)))

        logger.info(f"Selected {len(high_sample)} high-detection dates, {len(low_sample)} low-detection dates")

        return high_sample, low_sample

    def generate_prompt_for_date(self, date: str) -> Optional[str]:
        """
        Generate raw chain prompt for a specific date.

        Args:
            date: Date string (YYYY-MM-DD)

        Returns:
            Prompt string or None if data unavailable
        """
        try:
            self.extractor.connect()
            chain_df = self.extractor.get_raw_chain(date)
            spot_price = self.extractor.get_spot_price(date)
            self.extractor.disconnect()

            if chain_df.empty or spot_price is None:
                logger.warning(f"No data for {date}")
                return None

            prompt = self.prompt_builder.build_prompt(chain_df, spot_price, date)
            return prompt

        except Exception as e:
            logger.error(f"Error generating prompt for {date}: {e}")
            return None

    def save_sample_prompts(self, n_samples: int = 5):
        """
        Generate and save sample prompts for review.

        Args:
            n_samples: Number of sample prompts to generate
        """
        high_dates, low_dates = self.get_test_sample(n_high=n_samples, n_low=n_samples)

        samples = []

        for date in high_dates[:n_samples]:
            prompt = self.generate_prompt_for_date(date)
            if prompt:
                samples.append({
                    'date': date,
                    'baseline_detection': 'high',
                    'prompt': prompt
                })

        for date in low_dates[:n_samples]:
            prompt = self.generate_prompt_for_date(date)
            if prompt:
                samples.append({
                    'date': date,
                    'baseline_detection': 'low',
                    'prompt': prompt
                })

        # Save to file
        output_file = self.output_dir / 'issue_143_sample_prompts.yaml'
        with open(output_file, 'w') as f:
            yaml.dump(samples, f, default_flow_style=False, width=120)

        logger.info(f"Saved {len(samples)} sample prompts to {output_file}")

        # Also save a single example prompt for review
        if samples:
            example_file = self.output_dir / 'issue_143_example_prompt.txt'
            with open(example_file, 'w') as f:
                f.write(f"# Example Raw Chain Prompt\n")
                f.write(f"# Date: {samples[0]['date']}\n")
                f.write(f"# Baseline Detection: {samples[0]['baseline_detection']}\n\n")
                f.write(samples[0]['prompt'])

            logger.info(f"Saved example prompt to {example_file}")


def main():
    """Main entry point."""
    logger.info("Issue #143: Raw Chain Validation - Setup")

    validator = RawChainValidator()

    # Generate sample prompts for review
    logger.info("Generating sample prompts...")
    validator.save_sample_prompts(n_samples=3)

    # Show test sample statistics
    high_dates, low_dates = validator.get_test_sample()
    logger.info(f"\nTest sample ready:")
    logger.info(f"  High-detection dates: {len(high_dates)}")
    logger.info(f"  Low-detection dates: {len(low_dates)}")
    logger.info(f"  Total: {len(high_dates) + len(low_dates)}")

    logger.info("\nSetup complete. Review sample prompts before proceeding to full validation.")


if __name__ == '__main__':
    main()
