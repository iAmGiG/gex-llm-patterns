#!/usr/bin/env python3
"""Enhanced Experiment Orchestrator with YAML Reporting Includes data obfuscation, test metadata, and structured
output."""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import yaml

from src.agents.market_mechanics_agent import MarketMechanicsAgent
from src.utils.unified_reports_manager import yaml_reports
from gex_db_infrastructure.validation.data_obfuscation import DataObfuscator

logger = logging.getLogger(__name__)


def main():
    """Enhanced orchestration with YAML reporting and obfuscation."""
    parser = argparse.ArgumentParser(description="Enhanced Experiment Orchestrator")
    parser.add_argument("--experiment", type=str, required=True, help="Natural language experiment description")
    parser.add_argument("--symbol", type=str, default="SPY", help="Symbol to analyze")
    parser.add_argument(
        "--date",
        type=str,
        default="2024-06-28",
        help="Date for analysis (default: 2024-06-28 - Q2 end, high options volume)",
    )
    parser.add_argument(
        "--obfuscate",
        action="store_true",
        default=True,
        help="Obfuscate temporal/ticker references to prevent LLM cheating (default: True)",
    )
    parser.add_argument("--no-obfuscate", action="store_true", help="Disable obfuscation for debugging")
    parser.add_argument(
        "--test-type", type=str, default="gamma_analysis", help="Type of test (gamma_analysis, pattern_detection, etc.)"
    )
    parser.add_argument("--save-yaml", action="store_true", default=True, help="Save results in YAML format")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Obfuscation is default behavior unless explicitly disabled
    use_obfuscation = args.obfuscate and not args.no_obfuscate
    obfuscator = DataObfuscator() if use_obfuscation else None
    display_symbol = args.symbol
    display_date = args.date
    display_experiment = args.experiment

    if obfuscator:
        # Obfuscate inputs
        date_mapping = obfuscator.obfuscate_dates([args.date])
        ticker_mapping = obfuscator.obfuscate_tickers([args.symbol])
        display_date = date_mapping.get(args.date, args.date)
        display_symbol = ticker_mapping.get(args.symbol, args.symbol)
        display_experiment = obfuscator.obfuscate_text_content(args.experiment)

    print("=" * 60)
    print("ENHANCED EXPERIMENT ORCHESTRATOR")
    print("=" * 60)
    print(f"Experiment: {display_experiment}")
    print(f"Symbol: {display_symbol}")
    print(f"Date: {display_date}")
    print(f"Test Type: {args.test_type}")
    print(f"Obfuscation: {'Enabled' if use_obfuscation else 'Disabled'}")
    print("")

    # Explain why this date was chosen
    date_rationale = {
        "2024-06-28": "End of Q2 2024, quarterly expiration with high options volume",
        "2024-03-15": "Triple witching day with expected high gamma exposure",
        "2024-01-19": "Monthly OPEX with VIX expiration convergence",
        "2023-12-15": "Year-end positioning with tax loss harvesting effects",
    }

    if args.date in date_rationale:
        print(f"📅 Date Significance: {date_rationale[args.date]}")
        print("")

    try:
        # 1. Initialize agent
        print("🚀 Starting system...")
        agent = MarketMechanicsAgent(args.symbol)

        # 2. Run experiment (agent orchestrates tools autonomously)
        print("🤖 Agent running autonomous analysis...")
        result = agent.run_experiment(args.experiment, args.date)

        # 3. Structure results for YAML
        structured_results = {
            "experiment_type": args.test_type,
            "status": result.get("status", "unknown"),
            "mechanics_interpretation": result.get("mechanics_interpretation", {}),
            "gex_metrics": result.get("gex_metrics", {}),
            "patterns_detected": result.get("patterns_detected", []),
            "actionable_signal": result.get("actionable_signal", {}),
            "data_source": result.get("data_source", "unknown"),
            "llm_analysis": result.get("llm_analysis", {}),
            "agent_used": result.get("agent_used", "MarketMechanicsAgent"),
            "experiment_timestamp": result.get("experiment_timestamp", ""),
        }

        # 4. Save YAML report
        if args.save_yaml:
            print("\n📝 Saving YAML report...")
            report_path = yaml_reports.save_experiment_results(
                ticker=args.symbol,
                date=args.date,
                test_type=args.test_type,
                experiment_description=args.experiment,
                results=structured_results,
                obfuscate=use_obfuscation,
            )
            print(f"✅ Report saved: {report_path.name}")

        # 5. Display results
        print("")
        print("=" * 60)
        print("EXPERIMENT RESULTS")
        print("=" * 60)

        if structured_results["status"] == "error":
            print(f"❌ FAILED: {result.get('error', 'Unknown error')}")
            return 1

        # Display in YAML-like format for clarity
        print("\n--- Market Mechanics ---")
        mechanics = structured_results["mechanics_interpretation"]
        if mechanics:
            print(f"who: {mechanics.get('who', 'Unknown')}")
            print(f"whom: {mechanics.get('whom', 'Unknown')}")
            print(f"what: {mechanics.get('what', 'Unknown')}")
            print(f"confidence: {mechanics.get('confidence', 0)}%")

        print("\n--- GEX Metrics ---")
        gex = structured_results["gex_metrics"]
        if gex:
            print(f"total_gamma: ${gex.get('total_gamma', 0):,.0f}")
            print(f"spot_price: ${gex.get('spot_price', 0):.2f}")
            if gex.get("gamma_concentration"):
                print(f"gamma_concentration: {gex['gamma_concentration']*100:.1f}%")

        print("\n--- Trading Signal ---")
        signal = structured_results["actionable_signal"]
        if signal:
            print(f"action: {signal.get('action', 'HOLD')}")
            print(f"confidence: {signal.get('confidence', 0)}%")
            print(f"rationale: {signal.get('rationale', 'No clear edge')}")

        print("\n--- Data Source ---")
        print(f"primary: {structured_results.get('data_source', 'cache')}")

        print("\n" + "=" * 60)
        return 0

    except Exception as e:
        print(f"\n❌ ORCHESTRATION FAILED: {e}")
        logger.error(f"Orchestration error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit(main())
