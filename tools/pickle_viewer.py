#!/usr/bin/env python3
"""
Quick utility to view pickle files as CSV or inspect data.
Usage: python tools/pickle_viewer.py path/to/file.pickle
"""

import sys
from pathlib import Path

import pandas as pd


def view_pickle(pickle_path, output_csv: bool = False):
    """View or convert pickle file to CSV."""
    try:
        df = pd.read_pickle(pickle_path)

        print(f"📄 Pickle file: {pickle_path}")
        print(f"📊 Shape: {df.shape} (rows, columns)")
        print(f"📅 Index: {type(df.index).__name__}")

        if hasattr(df.index, "min") and hasattr(df.index, "max"):
            print(f"🗓️  Date range: {df.index.min()} to {df.index.max()}")

        print(f"\n🏷️  Columns: {list(df.columns)}")
        print(f"📈 Data types:")
        for col, dtype in df.dtypes.items():
            print(f"   {col}: {dtype}")

        print(f"\n👀 First 5 rows:")
        print(df.head())

        print(f"\n📋 Summary:")
        print(df.describe())

        if output_csv:
            csv_path = Path(pickle_path).with_suffix(".csv")
            df.to_csv(csv_path)
            print(f"\n💾 Saved as CSV: {csv_path}")

    except Exception as e:
        print(f"❌ Error reading pickle file: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tools/pickle_viewer.py <pickle_file> [--csv]")
        sys.exit(1)

    pickle_file = sys.argv[1]
    output_csv = "--csv" in sys.argv

    view_pickle(pickle_file, output_csv)
