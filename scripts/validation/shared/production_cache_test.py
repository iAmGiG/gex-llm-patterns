#!/usr/bin/env python3
"""
Production Cache Test
Tests the complete production flow: Cache -> API -> Real Data with LLM analysis
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.agents.market_mechanics_agent import MarketMechanicsAgent
from src.tools.autogen_tools import calculate_gamma_exposure, fetch_options_data
from src.utils.date_utils import is_valid_trading_date
from src.utils.unified_reports_manager import reports_manager

logger = logging.getLogger(__name__)


class ProductionCacheTest:
    """Production test of cache->live data flow with LLM analysis."""

    def __init__(self):
        # Using global reports_manager instead of ExperimentReporter
        pass

    def test_production_flow(self, symbol: str, date: str) -> dict:
        """Test complete production flow for a single symbol/date."""
        logger.info(f"Testing production flow: {symbol} on {date}")

        # Validate date first
        if not is_valid_trading_date(date):
            return {"status": "error", "message": f"Invalid trading date: {date}"}

        results = {
            "symbol": symbol,
            "date": date,
            "data_flow_test": {},
            "gex_calculation": {},
            "llm_analysis": {},
            "pattern_detection": {},
            "overall_status": "pending",
        }

        # Test 1: Options Data Retrieval
        logger.info("Testing options data retrieval...")
        try:
            options_result = fetch_options_data(symbol, date)
            if options_result.get("status") == "success":
                data = options_result["data"]
                results["data_flow_test"] = {
                    "status": "success",
                    "data_source": options_result.get("source", "unknown"),
                    "contracts_count": len(data) if hasattr(data, "__len__") else 0,
                    "data_columns": list(data.columns) if hasattr(data, "columns") else [],
                    "message": "Options data retrieved successfully",
                }
                logger.info(f"✅ Options data: {len(data)} contracts from {options_result.get('source', 'unknown')}")
            else:
                results["data_flow_test"] = {
                    "status": "error",
                    "message": options_result.get("message", "Unknown options data error"),
                }
                logger.error(f"❌ Options data failed: {results['data_flow_test']['message']}")
                return results
        except Exception as e:
            results["data_flow_test"] = {"status": "error", "message": f"Options data exception: {str(e)}"}
            logger.error(f"❌ Options data exception: {e}")
            return results

        # Test 2: GEX Calculation
        logger.info("Testing GEX calculation...")
        try:
            gex_result = calculate_gamma_exposure(symbol, date)
            if gex_result.get("status") == "success":
                metrics = gex_result.get("metrics", {})
                results["gex_calculation"] = {
                    "status": "success",
                    "total_gex": metrics.get("total_gex", 0),
                    "spot_price": metrics.get("spot_price", 0),
                    "flip_point": metrics.get("flip_point"),
                    "peak_gamma_strike": metrics.get("peak_gamma_strike"),
                    "data_source": gex_result.get("source", "unknown"),
                    "message": "GEX calculation successful",
                }
                logger.info(f"✅ GEX: ${metrics.get('total_gex', 0):,.0f} at ${metrics.get('spot_price', 0):.2f}")
            else:
                results["gex_calculation"] = {
                    "status": "error",
                    "message": gex_result.get("message", "Unknown GEX error"),
                }
                logger.error(f"❌ GEX calculation failed: {results['gex_calculation']['message']}")
                return results
        except Exception as e:
            results["gex_calculation"] = {"status": "error", "message": f"GEX calculation exception: {str(e)}"}
            logger.error(f"❌ GEX exception: {e}")
            return results

        # Test 3: LLM Analysis
        logger.info("Testing LLM analysis...")
        try:
            agent = MarketMechanicsAgent(symbol)

            # Add detailed logging for LLM responses
            logger.info("=" * 60)
            logger.info("RAW_LLM_RESPONSE_START")
            logger.info(f"Date: {date}")
            logger.info(f"Symbol: {symbol}")
            logger.info(f"Method: daily_analysis")

            llm_response = agent.daily_analysis(date)

            logger.info("RESPONSE_CONTENT:")
            logger.info(f"Type: {type(llm_response)}")
            logger.info(f"Content: {llm_response}")
            logger.info("RAW_LLM_RESPONSE_END")
            logger.info("=" * 60)

            if llm_response:
                # Check for LLM errors in response
                if isinstance(llm_response, dict):
                    mechanics = llm_response.get("mechanics_interpretation", {})
                    if mechanics.get("error") or mechanics.get("who") == "Error":
                        # LLM analysis failed - retry with higher tokens or fail the test
                        error_msg = mechanics.get("narrative", "Unknown LLM error")
                        logger.error(f"❌ LLM analysis failed: {error_msg}")

                        # Check if it's a token limit error
                        if "max_tokens" in error_msg:
                            logger.info("🔄 Retrying LLM analysis with higher token limit...")
                            # TODO: Implement retry with higher max_tokens
                            results["llm_analysis"] = {
                                "status": "error",
                                "error_type": "token_limit",
                                "message": f"LLM token limit exceeded: {error_msg}",
                                "retry_needed": True,
                            }
                        else:
                            results["llm_analysis"] = {
                                "status": "error",
                                "error_type": "llm_failure",
                                "message": f"LLM analysis failed: {error_msg}",
                            }

                        logger.error("❌ LLM analysis failed - marking test as invalid")
                        return results

                # Extract response attributes
                confidence = getattr(llm_response, "confidence", None)
                direction = getattr(llm_response, "direction", None)
                reasoning = getattr(llm_response, "reasoning", str(llm_response))

                # Additional validation for dict responses
                if isinstance(llm_response, dict):
                    mechanics = llm_response.get("mechanics_interpretation", {})
                    confidence = mechanics.get("confidence", confidence)

                results["llm_analysis"] = {
                    "status": "success",
                    "confidence": confidence,
                    "direction": direction,
                    "reasoning": reasoning,
                    "response_type": str(type(llm_response)),
                    "has_confidence": confidence is not None,
                    "has_direction": direction is not None,
                    "message": "LLM analysis completed",
                }
                logger.info(f"✅ LLM: {confidence}% confidence, direction: {direction}")
            else:
                results["llm_analysis"] = {"status": "error", "message": "LLM returned no response"}
                logger.error("❌ LLM analysis failed: No response")
                return results
        except Exception as e:
            results["llm_analysis"] = {"status": "error", "message": f"LLM analysis exception: {str(e)}"}
            logger.error(f"❌ LLM exception: {e}")
            return results

        # Test 4: Pattern Detection
        logger.info("Testing pattern detection...")
        try:
            # Check if it's Friday (common gamma pin day)
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            is_friday = date_obj.weekday() == 4

            # Analyze gamma concentration from GEX data
            gex_metrics = results["gex_calculation"]
            total_gex = abs(gex_metrics.get("total_gex", 0))

            # Simple pattern detection
            pattern_signals = []
            if is_friday and total_gex > 1e9:  # $1B+ GEX on Friday
                pattern_signals.append("friday_gamma_concentration")

            llm_confidence = results["llm_analysis"].get("confidence", 0) or 0
            if llm_confidence > 70:
                pattern_signals.append("high_confidence_llm")

            results["pattern_detection"] = {
                "status": "success",
                "is_friday": is_friday,
                "total_gex_billions": total_gex / 1e9,
                "pattern_signals": pattern_signals,
                "signal_count": len(pattern_signals),
                "message": f"Detected {len(pattern_signals)} pattern signals",
            }
            logger.info(f"✅ Patterns: {len(pattern_signals)} signals detected")

        except Exception as e:
            results["pattern_detection"] = {"status": "error", "message": f"Pattern detection exception: {str(e)}"}
            logger.error(f"❌ Pattern detection exception: {e}")

        # Overall assessment
        test_components = [
            results["data_flow_test"],
            results["gex_calculation"],
            results["llm_analysis"],
            results["pattern_detection"],
        ]

        success_count = sum(1 for test in test_components if test.get("status") == "success")
        failed_tests = [test for test in test_components if test.get("status") == "error"]

        # Check for critical failures (LLM token limits, etc.)
        critical_failures = [test for test in failed_tests if test.get("retry_needed")]

        if critical_failures:
            results["overall_status"] = "failed_retry_needed"
            logger.error("❌ Production test FAILED: Critical errors require retry")
            for failure in critical_failures:
                logger.error(f"  - {failure.get('error_type', 'unknown')}: {failure.get('message', 'unknown error')}")
        elif success_count == 4:
            results["overall_status"] = "success"
            logger.info("🎯 Production test PASSED: All components working")
        elif success_count >= 3:
            results["overall_status"] = "partial"
            logger.warning(f"⚠️ Production test PARTIAL: {success_count}/4 components working")
        else:
            results["overall_status"] = "failed"
            logger.error(f"❌ Production test FAILED: Only {success_count}/4 components working")

        return results

    def run_production_test(self, symbol: str, date: str) -> str:
        """Run production test and store results."""
        logger.info(f"Running production cache test: {symbol} on {date}")

        results = self.test_production_flow(symbol, date)

        # Store results
        experiment_name = f"production_cache_test_{symbol}"
        metadata = {
            "test_type": "production_cache_flow",
            "symbol": symbol,
            "date": date,
            "test_description": "Complete production flow test: Cache->API->LLM->Patterns",
        }

        # Save validation results using reports_manager
        filepath = reports_manager.save_agent_results(
            agent_name="ProductionCacheTest", task=experiment_name, results=results
        )

        # Log comprehensive summary
        logger.info("=" * 80)
        logger.info("PRODUCTION TEST SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Symbol: {symbol}")
        logger.info(f"Date: {date}")
        logger.info(f"Overall Status: {results['overall_status'].upper()}")
        logger.info("")

        # Component status
        for component, data in results.items():
            if isinstance(data, dict) and "status" in data:
                status = "✅ PASS" if data["status"] == "success" else "❌ FAIL"
                message = data.get("message", "")
                logger.info(f"{component.replace('_', ' ').title()}: {status} - {message}")

        # Key metrics
        if results["gex_calculation"].get("status") == "success":
            gex = results["gex_calculation"]
            logger.info("")
            logger.info("📊 GEX METRICS:")
            logger.info(f"  • Total GEX: ${gex.get('total_gex', 0):,.0f}")
            logger.info(f"  • Spot Price: ${gex.get('spot_price', 0):.2f}")
            if gex.get("flip_point"):
                logger.info(f"  • Flip Point: ${gex.get('flip_point'):.2f}")

        if results["llm_analysis"].get("status") == "success":
            llm = results["llm_analysis"]
            logger.info("")
            logger.info("🤖 LLM ANALYSIS:")
            logger.info(f"  • Confidence: {llm.get('confidence', 'N/A')}%")
            logger.info(f"  • Direction: {llm.get('direction', 'N/A')}")

        if results["pattern_detection"].get("status") == "success":
            patterns = results["pattern_detection"]
            logger.info("")
            logger.info("🎯 PATTERN DETECTION:")
            logger.info(f"  • Is Friday: {'✅' if patterns.get('is_friday') else '❌'}")
            logger.info(f"  • Pattern Signals: {patterns.get('signal_count', 0)}")
            if patterns.get("pattern_signals"):
                for signal in patterns["pattern_signals"]:
                    logger.info(f"    - {signal}")

        logger.info("")
        logger.info(f"Results stored: {filepath}")
        logger.info("=" * 80)

        return filepath


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Production Cache Test")
    parser.add_argument("--symbol", type=str, default="SPY", help="Trading symbol")
    parser.add_argument("--date", type=str, required=True, help="Date YYYY-MM-DD")

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    tester = ProductionCacheTest()
    result_file = tester.run_production_test(args.symbol, args.date)

    logger.info(f"Production cache test complete. Results: {result_file}")
