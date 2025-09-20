#!/usr/bin/env python3
"""
Simple Experiment Orchestrator
Starts the system, then lets MarketMechanicsAgent take over and orchestrate tools.
"""

from agents.market_mechanics_agent import MarketMechanicsAgent
import sys
from pathlib import Path
import logging
import argparse

# Add both src and root paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
sys.path.insert(0, str(Path(__file__).parent.parent))


logger = logging.getLogger(__name__)


def main():
    """Simple orchestration - start system, let agent take over."""
    parser = argparse.ArgumentParser(description="Experiment Orchestrator")
    parser.add_argument("--experiment", type=str, required=True,
                        help="Natural language experiment description")
    parser.add_argument("--symbol", type=str, default="SPY",
                        help="Symbol to analyze")
    parser.add_argument("--date", type=str, default="2024-06-28",
                        help="Date for analysis")
    parser.add_argument("--verbose", action="store_true",
                        help="Enable verbose logging")

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("=" * 60)
    print("EXPERIMENT ORCHESTRATOR")
    print("=" * 60)
    print(f"Experiment: {args.experiment}")
    print(f"Symbol: {args.symbol}")
    print(f"Date: {args.date}")
    print("")

    try:
        # 1. Start the system - initialize agent
        print("🚀 Starting system...")
        agent = MarketMechanicsAgent(args.symbol)

        # 2. Let agent take over - it will orchestrate tools and analysis
        print("🤖 Agent taking over...")
        result = agent.run_experiment(args.experiment, args.date)

        # 3. Display results
        print("")
        print("=" * 60)
        print("EXPERIMENT RESULTS")
        print("=" * 60)

        if result.get("status") == "error":
            print(f"❌ FAILED: {result.get('error')}")
            return 1

        print(f"✅ SUCCESS: {result.get('experiment_type', 'unknown')}")
        print("")

        # Show key findings
        mechanics = result.get('mechanics_interpretation', {})
        if mechanics:
            print("🧠 MARKET MECHANICS:")
            print(f"  WHO: {mechanics.get('who', 'Unknown')}")
            print(f"  WHOM: {mechanics.get('whom', 'Unknown')}")
            print(f"  WHAT: {mechanics.get('what', 'Unknown')}")
            print(f"  CONFIDENCE: {mechanics.get('confidence', 0)}%")
            print("")

        # Show GEX metrics
        gex_metrics = result.get('gex_metrics', {})
        if gex_metrics:
            print("📊 GEX METRICS:")
            print(f"  Total GEX: ${gex_metrics.get('total_gamma', 0):,.0f}")
            print(f"  Spot Price: ${gex_metrics.get('spot_price', 0):.2f}")
            gamma_conc = gex_metrics.get('gamma_concentration', 0)
            if gamma_conc > 0:
                print(f"  Gamma Concentration: {gamma_conc*100:.1f}%")
            print("")

        # Show patterns detected
        patterns = result.get('patterns_detected', [])
        if patterns:
            print("🎯 PATTERNS DETECTED:")
            for pattern in patterns:
                print(f"  • {pattern}")
            print("")

        # Show actionable signal
        signal = result.get('actionable_signal', {})
        if signal:
            print("📈 TRADING SIGNAL:")
            print(f"  Action: {signal.get('action', 'None')}")
            print(f"  Confidence: {signal.get('confidence', 0)}%")
            print(f"  Rationale: {signal.get('rationale', 'None')}")
            print("")

        print(f"🤖 Agent: {result.get('agent_used', 'MarketMechanicsAgent')}")
        print(f"⏰ Completed: {result.get('experiment_timestamp', 'Unknown')}")

        print("=" * 60)
        return 0

    except Exception as e:
        print(f"\n❌ ORCHESTRATION FAILED: {e}")
        logger.error(f"Orchestration error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
