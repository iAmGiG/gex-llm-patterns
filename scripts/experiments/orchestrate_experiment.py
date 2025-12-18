#!/usr/bin/env python3
"""Simple Experiment Orchestrator Starts the system, then lets MarketMechanicsAgent take over and orchestrate tools."""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.agents.market_mechanics_agent import MarketMechanicsAgent

logger = logging.getLogger(__name__)


def process_date_result(date, result, args, high_confidence_signals, all_results):
    """Helper to process individual date results."""
    # Extract signal data
    signal = result.get("actionable_signal", {})
    confidence = signal.get("confidence", 0) if signal else 0
    # Ensure confidence is numeric
    if confidence is None:
        confidence = 0

    result_data = {
        "date": date,
        "confidence": confidence,
        "has_signal": bool(signal.get("action")) if signal else False,
        "pattern": signal.get("pattern", "None") if signal else "None",
        "gex_total": result.get("gex_metrics", {}).get("total_gamma", 0),
    }
    all_results.append(result_data)

    if confidence >= args.confidence_threshold:
        high_confidence_signals.append(result_data)
        print(f"  ✅ HIGH CONFIDENCE: {confidence}% - {result_data['pattern']}")
    else:
        print(f"  ⚠️  Low confidence: {confidence}%")


def run_batch_validation(args):
    """Run batch validation on multiple dates.

    Generic function that can test any date range with configurable parameters.
    """
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    print("=" * 80)
    print("BATCH VALIDATION TEST")
    print("=" * 80)
    print(f"Testing {len(args.batch_dates)} dates")
    print(f"Symbol: {args.symbol}")
    print(f"Time Window: {args.time_window}")
    print(f"Confidence Threshold: {args.confidence_threshold}%")
    print(f"Target Signals: {args.target_signals}")
    print(f"Batch Mode: {args.batch_mode if hasattr(args, 'batch_mode') else True}")
    print()

    high_confidence_signals = []
    all_results = []

    # Default experiment template if not provided
    experiment_template = args.experiment_template or (
        "Analyze {symbol} patterns on {date} at {time}. " "Focus on gamma dynamics and dealer positioning."
    )

    # Use batch processing if enabled (default) and multiple dates
    batch_mode = getattr(args, "batch_mode", True)

    if batch_mode and len(args.batch_dates) > 1:
        print("🚀 Using BATCH PROCESSING - single LLM call for all dates")
        print()

        try:
            agent = MarketMechanicsAgent(args.symbol)

            # Run batch experiment with obfuscation
            batch_result = agent.run_batch_experiments(
                dates=args.batch_dates,
                experiment_template=experiment_template,
                use_obfuscation=getattr(args, "obfuscate", True),
            )

            if batch_result.get("status") == "success":
                # Process individual results from batch
                individual_results = batch_result.get("individual_results", {})

                for date in args.batch_dates:
                    if date in individual_results:
                        result = individual_results[date]
                        process_date_result(date, result, args, high_confidence_signals, all_results)
                    else:
                        print(f"  ⚠️  No result for {date}")

                # Show batch insights
                if batch_result.get("batch_analysis"):
                    print("\n📊 BATCH INSIGHTS:")
                    print(f"  {batch_result.get('batch_analysis', {}).get('overall_analysis', 'No patterns found')}")
            else:
                print(f"❌ Batch processing failed: {batch_result.get('error')}")
                # Fall back to individual processing
                batch_mode = False

        except Exception as e:
            print(f"❌ Batch mode error: {e}")
            print("Falling back to individual processing...")
            batch_mode = False

    # Individual processing (fallback or if batch_mode=False)
    if not batch_mode or len(args.batch_dates) == 1:
        print("📝 Using INDIVIDUAL PROCESSING - separate LLM call per date")
        print()

        for date in args.batch_dates:
            # Build experiment description from template
            experiment_desc = experiment_template.format(symbol=args.symbol, date=date, time=args.time_window)

            print(f"📅 Testing {date}...")

            try:
                agent = MarketMechanicsAgent(args.symbol)
                result = agent.run_experiment(experiment_desc, date)
                process_date_result(date, result, args, high_confidence_signals, all_results)

            except Exception as e:
                print(f"  ❌ Error: {e}")
                all_results.append({"date": date, "error": str(e)})

    # Display results summary
    print()
    print("=" * 80)
    print("RESULTS SUMMARY")
    print("=" * 80)
    print(f"Dates Tested: {len(args.batch_dates)}")
    print(f"High-Confidence Signals: {len(high_confidence_signals)}")
    print(f"Target: {args.target_signals}")

    if high_confidence_signals:
        print("\n🎯 High-Confidence Signals:")
        for sig in high_confidence_signals:
            print(f"  • {sig['date']}: {sig['pattern']} @ {sig['confidence']}%")

    # Determine pass/fail
    validation_passed = len(high_confidence_signals) >= args.target_signals

    print()
    if validation_passed:
        print("✅ VALIDATION PASSED")
        print(f"  Found {len(high_confidence_signals)} signals (target: {args.target_signals})")
    else:
        print("❌ VALIDATION FAILED")
        print(f"  Found {len(high_confidence_signals)} signals (needed: {args.target_signals})")

    # Add results export
    if hasattr(args, "export_results") and args.export_results:
        import json

        output = {
            "summary": {
                "dates_tested": len(args.batch_dates),
                "high_confidence_signals": len(high_confidence_signals),
                "success_rate": len(high_confidence_signals) / len(args.batch_dates) if args.batch_dates else 0,
                "validation_passed": validation_passed,
            },
            "signals": high_confidence_signals,
            "all_results": all_results,
        }

        with open(f"validation_results_{args.symbol}_{args.time_window}.json", "w") as f:
            json.dump(output, f, indent=2)
        print(f"\n📊 Results exported to validation_results_{args.symbol}_{args.time_window}.json")

    print("=" * 80)
    return 0 if validation_passed else 1


def main():
    """Simple orchestration - start system, let agent take over."""
    parser = argparse.ArgumentParser(description="Experiment Orchestrator")
    parser.add_argument("--experiment", type=str, help="Natural language experiment description")
    parser.add_argument("--symbol", type=str, default="SPY", help="Symbol to analyze")
    parser.add_argument("--date", type=str, default="2024-06-28", help="Date for analysis")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    # Batch validation mode
    parser.add_argument("--batch-dates", type=str, nargs="+", help="Run batch validation on multiple dates")
    parser.add_argument("--time-window", type=str, default="15:30", help="Time window for analysis (default: 15:30)")
    parser.add_argument(
        "--confidence-threshold", type=int, default=60, help="Minimum confidence for signal counting (default: 60)"
    )
    parser.add_argument(
        "--target-signals", type=int, default=3, help="Target number of signals for validation pass (default: 3)"
    )
    parser.add_argument(
        "--experiment-template",
        type=str,
        help="Template for batch experiments. Use {symbol}, {date}, {time} as placeholders",
    )
    parser.add_argument(
        "--batch-mode",
        action="store_true",
        default=True,
        help="Use batch LLM processing for multiple dates (default: True)",
    )
    parser.add_argument("--no-batch-mode", action="store_true", help="Disable batch mode, process dates individually")
    parser.add_argument(
        "--obfuscate",
        action="store_true",
        default=True,
        help="Obfuscate dates/tickers to prevent LLM cheating (default: True)",
    )
    parser.add_argument("--no-obfuscate", action="store_true", help="Disable obfuscation for debugging")

    args = parser.parse_args()

    # Resolve conflicting boolean flags
    if args.no_batch_mode:
        args.batch_mode = False
    if args.no_obfuscate:
        args.obfuscate = False

    # Handle batch validation mode
    if args.batch_dates:
        return run_batch_validation(args)

    # Regular mode requires experiment
    if not args.experiment:
        parser.error("--experiment is required unless using --batch-dates")

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

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
        mechanics = result.get("mechanics_interpretation", {})
        if mechanics:
            print("🧠 MARKET MECHANICS:")
            print(f"  WHO: {mechanics.get('who', 'Unknown')}")
            print(f"  WHOM: {mechanics.get('whom', 'Unknown')}")
            print(f"  WHAT: {mechanics.get('what', 'Unknown')}")
            print(f"  CONFIDENCE: {mechanics.get('confidence', 0)}%")
            print("")

        # Show GEX metrics
        gex_metrics = result.get("gex_metrics", {})
        if gex_metrics:
            print("📊 GEX METRICS:")
            print(f"  Total GEX: ${gex_metrics.get('total_gamma', 0):,.0f}")
            print(f"  Spot Price: ${gex_metrics.get('spot_price', 0):.2f}")
            gamma_conc = gex_metrics.get("gamma_concentration", 0)
            if gamma_conc > 0:
                print(f"  Gamma Concentration: {gamma_conc*100:.1f}%")
            print("")

        # Show patterns detected
        patterns = result.get("patterns_detected", [])
        if patterns:
            print("🎯 PATTERNS DETECTED:")
            for pattern in patterns:
                print(f"  • {pattern}")
            print("")

        # Show actionable signal
        signal = result.get("actionable_signal", {})
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
