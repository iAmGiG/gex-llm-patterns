#!/usr/bin/env python3
"""
Monitor Automated Data Collection Progress

Shows real-time status of the automated collection system.
"""

import sys
import json
from pathlib import Path
from datetime import datetime
import time

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root / 'src'))

from cache.unified_cache import UnifiedCacheManager


def monitor_collection():
    """Monitor collection progress in real-time."""
    cache = UnifiedCacheManager()
    progress_file = cache.base_dir / "automated_collection_progress.json"
    
    print("Automated Data Collection Monitor")
    print("=" * 60)
    print("Press Ctrl+C to exit")
    print()
    
    while True:
        try:
            # Load progress
            if progress_file.exists():
                with open(progress_file, 'r') as f:
                    progress = json.load(f)
            else:
                progress = {}
            
            # Clear screen (works on Unix/Linux/Mac)
            print("\033[H\033[J", end="")
            
            # Header
            print("📊 Data Collection Status")
            print("=" * 60)
            print(f"Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print()
            
            # Options Collection
            print("📈 OPTIONS DATA (Alpha Vantage - 25/day limit)")
            print("-" * 40)
            options_collected = progress.get('options_collected', {})
            total_options_dates = sum(len(dates) for dates in options_collected.values())
            
            print(f"Symbols with data: {len(options_collected)}")
            print(f"Total date-symbol pairs: {total_options_dates}")
            print(f"API calls today: {progress.get('options_calls_today', 0)}/25")
            print(f"Calls remaining: {25 - progress.get('options_calls_today', 0)}")
            
            if options_collected:
                print("\nSymbol Coverage:")
                for symbol, dates in list(options_collected.items())[:5]:
                    earliest = min(dates) if dates else "N/A"
                    latest = max(dates) if dates else "N/A"
                    print(f"  {symbol}: {len(dates)} days ({earliest} to {latest})")
                if len(options_collected) > 5:
                    print(f"  ... and {len(options_collected) - 5} more symbols")
            print()
            
            # Stock Collection
            print("📊 STOCK DATA (Polygon.io - 7,200/day)")
            print("-" * 40)
            stocks_collected = progress.get('stocks_collected', {})
            print(f"Symbols collected: {len(stocks_collected)}")
            
            total_bars = 0
            for stock_info in stocks_collected.values():
                if isinstance(stock_info, dict):
                    total_bars += stock_info.get('bars', 0)
            print(f"Total price bars: {total_bars:,}")
            
            if stocks_collected:
                print("\nTop Stocks:")
                for symbol, info in list(stocks_collected.items())[:5]:
                    if isinstance(info, dict):
                        print(f"  {symbol}: {info.get('bars', 0):,} bars")
            print()
            
            # GEX Calculations
            print("🧮 GEX CALCULATIONS")
            print("-" * 40)
            gex_calculated = progress.get('gex_calculated', {})
            print(f"Total GEX calculations cached: {len(gex_calculated)}")
            
            # Cache Statistics
            print("\n💾 CACHE STATISTICS")
            print("-" * 40)
            cache_summary = cache.get_cache_summary()
            
            print(f"Total files: {cache_summary['total_files']}")
            print(f"Total size: {cache_summary['total_size_mb']:.1f} MB")
            
            if cache_summary['options']:
                print("\nOptions cache:")
                for ticker, count in cache_summary['options'].items():
                    print(f"  {ticker}: {count} files")
            
            if cache_summary['market_data']:
                print("\nMarket data cache:")
                for ticker, count in cache_summary['market_data'].items():
                    print(f"  {ticker}: {count} files")
            
            # Detailed options cache info
            options_summary = cache.get_options_cache_summary()
            if options_summary['tickers']:
                print("\n📋 OPTIONS DETAILS")
                print("-" * 40)
                for ticker, info in options_summary['tickers'].items():
                    print(f"{ticker}:")
                    print(f"  Dates cached: {info['date_count']}")
                    print(f"  Total contracts: {info['total_contracts']:,}")
                    if info['dates']:
                        print(f"  Date range: {min(info['dates'])} to {max(info['dates'])}")
            
            # Collection rate estimates
            print("\n⏱️  COLLECTION ESTIMATES")
            print("-" * 40)
            
            # Options rate
            if total_options_dates > 0:
                days_to_1_year = (252 - total_options_dates) / 25
                print(f"Options: ~{days_to_1_year:.1f} days to complete 1 year of data")
            
            # Check if collector is running
            log_file = Path("automated_collection.log")
            if log_file.exists():
                # Get last modified time
                last_modified = datetime.fromtimestamp(log_file.stat().st_mtime)
                time_since = (datetime.now() - last_modified).total_seconds()
                
                if time_since < 120:  # Active if log updated in last 2 minutes
                    print("\n✅ Collector Status: RUNNING")
                else:
                    print(f"\n⚠️  Collector Status: INACTIVE (last activity {time_since/60:.1f} min ago)")
            else:
                print("\n❌ Collector Status: NOT STARTED")
            
            print("\n" + "=" * 60)
            
            # Wait before refresh
            time.sleep(10)
            
        except KeyboardInterrupt:
            print("\nMonitoring stopped.")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    monitor_collection()