#!/usr/bin/env python3
"""
Gamma Pinning Validation Tool
Tests the hypothesis: "SPY prices move toward max gamma strikes on Fridays at key algo times"

Uses intraday database and cache system for validation.
"""

import logging
import sqlite3
import sys
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from src.data.market_data_system import UnifiedDataSystem
from src.utils.date_utils import date_range_trading_days, format_for_filename, parse_date_string

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class GammaPinningValidator:
    """Gamma pinning validation tool for Friday algo time analysis.

    Tests:
    1. Friday 3:30 PM gamma pinning behavior
    2. Movement toward max gamma strikes during final trading hour
    3. Algo time impact (10:00 AM, 2:30 PM FOMC, 3:30/3:40/3:50 PM)
    """

    def __init__(self, symbol: str = "SPY"):
        """Initialize validator with unified data system."""
        self.symbol = symbol
        self.data_system = UnifiedDataSystem()

        # Key algo times for validation
        self.key_times = {
            "09:30:00": "MARKET_OPEN",
            "10:00:00": "ALGO_10AM",
            "14:30:00": "FOMC_230PM",
            "15:30:00": "GAMMA_330PM",
            "15:40:00": "GAMMA_340PM",
            "15:50:00": "GAMMA_350PM",
            "16:00:00": "MARKET_CLOSE",
        }

        # Validation thresholds
        self.close_distance_threshold = 5.0  # $5 considered "close" to gamma strike
        self.moderate_distance_threshold = 10.0  # $10 considered "moderate"

    def validate_friday_gamma_pinning(self, start_date: str, end_date: str, target_time: str = "15:30:00") -> Dict:
        """Main validation of Friday gamma pinning at target time.

        Args:
            start_date: Start date for analysis
            end_date: End date for analysis
            target_time: Target time for analysis (default: 3:30 PM)

        Returns:
            Validation results dictionary
        """
        logger.info(f"Validating Friday gamma pinning for {self.symbol}")
        logger.info(f"Period: {start_date} to {end_date}")
        logger.info(f"Target time: {target_time}")

        # Get Friday dates in range
        friday_dates = self._get_friday_dates(start_date, end_date)
        logger.info(f"Found {len(friday_dates)} Fridays to analyze")

        if not friday_dates:
            return {"error": "No Friday dates found in range"}

        # Analyze each Friday
        validation_results = []
        for friday_date in friday_dates:
            result = self._analyze_friday(friday_date, target_time)
            if result:
                validation_results.append(result)

        if not validation_results:
            return {"error": "No data available for Friday analysis"}

        # Calculate summary statistics
        summary = self._calculate_summary_stats(validation_results)

        return {
            "symbol": self.symbol,
            "analysis_period": f"{start_date} to {end_date}",
            "target_time": target_time,
            "fridays_analyzed": len(validation_results),
            "validation_results": validation_results,
            "summary_statistics": summary,
            "data_system_stats": self.data_system.get_performance_stats(),
        }

    def _get_friday_dates(self, start_date: str, end_date: str) -> List[str]:
        """Get all Friday dates in the range."""
        try:
            trading_days = date_range_trading_days(start_date, end_date)
            friday_dates = []

            for date in trading_days:
                dt = parse_date_string(date)
                if dt.weekday() == 4:  # Friday
                    friday_dates.append(date)

            return friday_dates

        except Exception as e:
            logger.error(f"Failed to get Friday dates: {e}")
            return []

    def _analyze_friday(self, friday_date: str, target_time: str) -> Optional[Dict]:
        """Analyze a specific Friday for gamma pinning behavior."""
        try:
            timestamp = f"{friday_date} {target_time}"

            # Get GEX data at target time
            gex_data = self.data_system.fetch_gex_data(timestamp, self.symbol)
            if not gex_data:
                logger.debug(f"No GEX data for {friday_date} at {target_time}")
                return None

            # Get market data at target time
            market_data = self.data_system.fetch_market_data(timestamp, self.symbol)
            if not market_data:
                logger.debug(f"No market data for {friday_date} at {target_time}")
                return None

            # Get max gamma strike from database
            max_gamma_info = self._get_max_gamma_strike(timestamp)
            if not max_gamma_info:
                logger.debug(f"No gamma strike data for {friday_date} at {target_time}")
                return None

            # Calculate distances and movements
            spot_price = gex_data.get("spot_price") or market_data.get("close")
            max_gamma_strike = max_gamma_info["max_gamma_strike"]
            distance_to_gamma = abs(spot_price - max_gamma_strike)

            # Determine proximity category
            proximity_category = self._categorize_distance(distance_to_gamma)

            # Try to get price movement over the hour
            movement_analysis = self._analyze_price_movement(friday_date, target_time, max_gamma_strike)

            result = {
                "date": friday_date,
                "timestamp": timestamp,
                "spot_price": spot_price,
                "max_gamma_strike": max_gamma_strike,
                "max_gamma_value": max_gamma_info["max_gamma_value"],
                "distance_to_gamma": distance_to_gamma,
                "proximity_category": proximity_category,
                "is_close_pin": distance_to_gamma <= self.close_distance_threshold,
                "gex_regime": gex_data.get("gex_regime"),
                "total_gex": gex_data.get("total_gex"),
                "market_session": gex_data.get("market_session", "regular"),
                "movement_analysis": movement_analysis,
            }

            logger.debug(f"Analyzed {friday_date}: {proximity_category}, distance=${distance_to_gamma:.2f}")
            return result

        except Exception as e:
            logger.error(f"Failed to analyze Friday {friday_date}: {e}")
            return None

    def _get_max_gamma_strike(self, timestamp: str) -> Optional[Dict]:
        """Get max gamma strike for timestamp from database."""
        try:
            with sqlite3.connect(self.data_system.db_path) as conn:
                conn.row_factory = sqlite3.Row

                # Use the max_gamma_strikes view
                query = """
                SELECT max_gamma_strike, max_gamma_value, distance_from_spot
                FROM max_gamma_strikes
                WHERE symbol = ? AND timestamp = ?
                """

                cursor = conn.execute(query, (self.symbol, timestamp))
                row = cursor.fetchone()

                return dict(row) if row else None

        except Exception as e:
            logger.debug(f"Failed to get max gamma strike: {e}")
            return None

    def _categorize_distance(self, distance: float) -> str:
        """Categorize distance to gamma strike."""
        if distance <= self.close_distance_threshold:
            return "CLOSE"
        elif distance <= self.moderate_distance_threshold:
            return "MODERATE"
        else:
            return "FAR"

    def _analyze_price_movement(self, friday_date: str, target_time: str, max_gamma_strike: float) -> Dict:
        """Analyze price movement relative to gamma strike over time."""
        movement_data = {
            "has_movement_data": False,
            "moved_toward_gamma": False,
            "initial_distance": None,
            "final_distance": None,
            "distance_change_pct": 0.0,
        }

        try:
            # Get price at market open (9:30 AM)
            open_timestamp = f"{friday_date} 09:30:00"
            open_data = self.data_system.fetch_market_data(open_timestamp, self.symbol)

            # Get price at target time
            target_timestamp = f"{friday_date} {target_time}"
            target_data = self.data_system.fetch_market_data(target_timestamp, self.symbol)

            if open_data and target_data:
                open_price = open_data.get("close") or open_data.get("price")
                target_price = target_data.get("close") or target_data.get("price")

                if open_price and target_price:
                    initial_distance = abs(open_price - max_gamma_strike)
                    final_distance = abs(target_price - max_gamma_strike)

                    moved_toward_gamma = final_distance < initial_distance
                    distance_change_pct = (
                        ((initial_distance - final_distance) / initial_distance) * 100 if initial_distance > 0 else 0
                    )

                    movement_data.update(
                        {
                            "has_movement_data": True,
                            "moved_toward_gamma": moved_toward_gamma,
                            "initial_distance": initial_distance,
                            "final_distance": final_distance,
                            "distance_change_pct": distance_change_pct,
                            "open_price": open_price,
                            "target_price": target_price,
                        }
                    )

        except Exception as e:
            logger.debug(f"Failed to analyze price movement: {e}")

        return movement_data

    def _calculate_summary_stats(self, results: List[Dict]) -> Dict:
        """Calculate summary statistics from validation results."""
        if not results:
            return {}

        total_fridays = len(results)

        # Proximity analysis
        close_pins = sum(1 for r in results if r["is_close_pin"])
        proximity_counts = {}
        for category in ["CLOSE", "MODERATE", "FAR"]:
            proximity_counts[category] = sum(1 for r in results if r["proximity_category"] == category)

        # Movement analysis
        movement_results = [r for r in results if r["movement_analysis"]["has_movement_data"]]
        moved_toward_count = sum(1 for r in movement_results if r["movement_analysis"]["moved_toward_gamma"])

        # Distance statistics
        distances = [r["distance_to_gamma"] for r in results]
        distance_changes = [
            r["movement_analysis"]["distance_change_pct"]
            for r in movement_results
            if r["movement_analysis"]["distance_change_pct"] is not None
        ]

        summary = {
            "total_fridays": total_fridays,
            "close_pin_count": close_pins,
            "close_pin_rate_pct": (close_pins / total_fridays) * 100,
            "proximity_distribution": {
                "close_count": proximity_counts.get("CLOSE", 0),
                "moderate_count": proximity_counts.get("MODERATE", 0),
                "far_count": proximity_counts.get("FAR", 0),
                "close_rate_pct": (proximity_counts.get("CLOSE", 0) / total_fridays) * 100,
            },
            "movement_analysis": {
                "fridays_with_movement_data": len(movement_results),
                "moved_toward_gamma_count": moved_toward_count,
                "moved_toward_gamma_rate_pct": (
                    (moved_toward_count / len(movement_results)) * 100 if movement_results else 0
                ),
            },
            "distance_statistics": {
                "avg_distance": np.mean(distances) if distances else 0,
                "median_distance": np.median(distances) if distances else 0,
                "min_distance": np.min(distances) if distances else 0,
                "max_distance": np.max(distances) if distances else 0,
            },
            "distance_change_statistics": {
                "avg_change_pct": np.mean(distance_changes) if distance_changes else 0,
                "median_change_pct": np.median(distance_changes) if distance_changes else 0,
                "positive_changes": sum(1 for d in distance_changes if d > 0) if distance_changes else 0,
            },
        }

        return summary

    def validate_multiple_times(self, start_date: str, end_date: str, times: List[str] = None) -> Dict:
        """Validate gamma pinning at multiple algo times."""
        if times is None:
            times = ["10:00:00", "14:30:00", "15:30:00", "15:40:00", "15:50:00"]

        results_by_time = {}

        for time_str in times:
            logger.info(f"Validating at {time_str}...")
            time_results = self.validate_friday_gamma_pinning(start_date, end_date, time_str)
            results_by_time[time_str] = time_results

        return {
            "symbol": self.symbol,
            "analysis_period": f"{start_date} to {end_date}",
            "times_analyzed": times,
            "results_by_time": results_by_time,
            "comparison_summary": self._compare_time_results(results_by_time),
        }

    def _compare_time_results(self, results_by_time: Dict) -> Dict:
        """Compare results across different times."""
        comparison = {}

        for time_str, results in results_by_time.items():
            if "summary_statistics" in results:
                stats = results["summary_statistics"]
                comparison[time_str] = {
                    "close_pin_rate": stats.get("close_pin_rate_pct", 0),
                    "moved_toward_rate": stats.get("movement_analysis", {}).get("moved_toward_gamma_rate_pct", 0),
                    "avg_distance": stats.get("distance_statistics", {}).get("avg_distance", 0),
                }

        return comparison

    def export_results(self, results: Dict, output_file: str = None) -> str:
        """Export validation results to CSV file."""
        if output_file is None:
            timestamp = format_for_filename()
            output_file = f"reports/gamma_pinning_validation_{self.symbol}_{timestamp}.csv"

        # Create reports directory
        Path("reports").mkdir(exist_ok=True)

        try:
            # Convert results to DataFrame
            if "validation_results" in results:
                df_data = []
                for result in results["validation_results"]:
                    row = {
                        "date": result["date"],
                        "timestamp": result["timestamp"],
                        "spot_price": result["spot_price"],
                        "max_gamma_strike": result["max_gamma_strike"],
                        "distance_to_gamma": result["distance_to_gamma"],
                        "proximity_category": result["proximity_category"],
                        "is_close_pin": result["is_close_pin"],
                        "gex_regime": result["gex_regime"],
                        "total_gex": result["total_gex"],
                    }

                    # Add movement data if available
                    movement = result.get("movement_analysis", {})
                    row.update(
                        {
                            "has_movement_data": movement.get("has_movement_data", False),
                            "moved_toward_gamma": movement.get("moved_toward_gamma", False),
                            "distance_change_pct": movement.get("distance_change_pct", 0),
                        }
                    )

                    df_data.append(row)

                df = pd.DataFrame(df_data)
                df.to_csv(output_file, index=False)

                logger.info(f"Results exported to: {output_file}")
                return output_file

        except Exception as e:
            logger.error(f"Failed to export results: {e}")

        return ""


def main():
    """Run gamma pinning validation from command line."""
    import argparse

    parser = argparse.ArgumentParser(description="Validate Friday gamma pinning behavior")
    parser.add_argument("--symbol", default="SPY", help="Symbol to analyze")
    parser.add_argument("--start-date", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--time", default="15:30:00", help="Target time (HH:MM:SS)")
    parser.add_argument("--multi-time", action="store_true", help="Analyze multiple times")
    parser.add_argument("--export", action="store_true", help="Export results to CSV")

    args = parser.parse_args()

    validator = GammaPinningValidator(args.symbol)

    if args.multi_time:
        results = validator.validate_multiple_times(args.start_date, args.end_date)
    else:
        results = validator.validate_friday_gamma_pinning(args.start_date, args.end_date, args.time)

    # Print summary
    print(f"\n{'='*60}")
    print(f"GAMMA PINNING VALIDATION - {args.symbol}")
    print(f"{'='*60}")

    if "summary_statistics" in results:
        stats = results["summary_statistics"]
        print(f"Period: {results['analysis_period']}")
        print(f"Fridays analyzed: {stats['total_fridays']}")
        print(f"Close pins (<$5): {stats['close_pin_count']} ({stats['close_pin_rate_pct']:.1f}%)")

        if "movement_analysis" in stats:
            movement = stats["movement_analysis"]
            print(
                f"Moved toward gamma: {movement['moved_toward_gamma_count']} ({movement['moved_toward_gamma_rate_pct']:.1f}%)"
            )

    elif "results_by_time" in results:
        print("Multi-time analysis:")
        for time_str, time_results in results["results_by_time"].items():
            if "summary_statistics" in time_results:
                stats = time_results["summary_statistics"]
                print(f"  {time_str}: {stats['close_pin_rate_pct']:.1f}% close pin rate")

    # Export if requested
    if args.export:
        if "validation_results" in results:
            output_file = validator.export_results(results)
            print(f"\nResults exported to: {output_file}")


if __name__ == "__main__":
    main()
