#!/usr/bin/env python3
"""
Example: Flexible Algo Time Analysis
Demonstrates the new parameterizable algo time system.
"""

import sys
from pathlib import Path

from src.data.market_data_system import UnifiedDataSystem

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def demonstrate_flexible_algo_times():
    """Show the new flexible algo time capabilities."""
    print("🕐 Flexible Algo Time Analysis Examples")
    print("=" * 50)

    system = UnifiedDataSystem()

    # Example 1: SPY 0DTE - check multiple algo times
    print("\n📈 SPY (Daily 0DTE) - Multiple Algo Times:")
    print("-" * 40)

    # Standard 3:30 PM gamma time
    data_330 = system.get_algo_time_data("2024-06-01", "2024-06-30", "SPY", "15:30:00")
    print(f"3:30 PM data points: {len(data_330)}")

    # Advanced 3:50 PM algo plays
    data_350 = system.get_algo_time_data("2024-06-01", "2024-06-30", "SPY", "15:50:00")
    print(f"3:50 PM data points: {len(data_350)}")

    # Market close
    data_close = system.get_algo_time_data("2024-06-01", "2024-06-30", "SPY", "16:00:00")
    print(f"Market close data points: {len(data_close)}")

    # Example 2: QQQ 0DTE - using config names
    print("\n📊 QQQ (Daily 0DTE) - Using Config Names:")
    print("-" * 40)

    # Use config name instead of raw time
    gamma_time = system.get_algo_time_from_config("gamma_350pm")
    print(f"gamma_350pm resolves to: {gamma_time}")

    qqq_data = system.get_algo_time_data("2024-06-01", "2024-06-30", "QQQ", gamma_time)
    print(f"QQQ 3:50 PM data points: {len(qqq_data)}")

    # Example 3: Regular ticker - Friday only
    print("\n🍎 AAPL (Friday Expiration Only):")
    print("-" * 40)

    # AAPL will default to Friday only
    aapl_data = system.get_algo_time_data("2024-06-01", "2024-06-30", "AAPL", "15:30:00")
    print(f"AAPL Friday 3:30 PM data points: {len(aapl_data)}")

    # Example 4: Specific weekday targeting
    print("\n📅 Weekday-Specific Analysis:")
    print("-" * 40)

    # SPY Wednesdays only (mid-week positioning)
    wed_data = system.get_algo_time_data("2024-06-01", "2024-06-30", "SPY", "15:30:00", weekday=2)
    print(f"SPY Wednesday 3:30 PM data points: {len(wed_data)}")

    # SPY Fridays only (expiration behavior)
    fri_data = system.get_algo_time_data("2024-06-01", "2024-06-30", "SPY", "15:50:00", weekday=4)
    print(f"SPY Friday 3:50 PM data points: {len(fri_data)}")

    # Example 5: LLM Tool Integration
    print("\n🤖 LLM Tool Usage Examples:")
    print("-" * 40)

    print("Available for LLM tools:")
    print("• fetch_algo_time_analysis(symbol='SPY', algo_time='15:50:00')")
    print("• fetch_algo_time_analysis(symbol='QQQ', algo_time='gamma_350pm')")
    print("• fetch_algo_time_analysis(symbol='AAPL', weekday_filter='friday')")
    print("• fetch_algo_time_analysis(symbol='SPY', weekday_filter='wednesday')")

    # Performance stats
    stats = system.get_performance_stats()
    print(f"\n📊 Performance: {stats['total_requests']} total requests")

    print("\n" + "=" * 50)
    print("🎉 Flexible Algo Time System Ready!")
    print("✅ Supports SPY/QQQ daily 0DTE")
    print("✅ Supports regular tickers (Friday only)")
    print("✅ Parameterizable algo times (3:30, 3:50, etc.)")
    print("✅ Weekday-specific filtering")
    print("✅ LLM tool integration")
    print("✅ Backward compatibility maintained")


if __name__ == "__main__":
    demonstrate_flexible_algo_times()
