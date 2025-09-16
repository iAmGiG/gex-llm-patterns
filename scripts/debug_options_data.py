#!/usr/bin/env python3
"""
Debug script to examine cached options data structure
"""
import sys
import os
sys.path.append('/mnt/bst/yxie2/cregan1/gex-llm-patterns')
sys.path.append('/mnt/bst/yxie2/cregan1/gex-llm-patterns/src')

import pandas as pd
import pickle

# Load a sample cached options file
cache_file = '.cache/options/SPY/2024-02-14.pickle'

try:
    with open(cache_file, 'rb') as f:
        options_data = pickle.load(f)

    print(f"Loaded options data from {cache_file}")
    print(f"Shape: {options_data.shape}")
    print(f"Columns: {list(options_data.columns)}")
    print(f"Data types:\n{options_data.dtypes}")
    print(f"\nFirst few rows:")
    print(options_data.head())

    # Check for option type indicators
    for col in options_data.columns:
        if 'type' in col.lower() or 'call' in col.lower() or 'put' in col.lower():
            print(f"\nUnique values in {col}: {options_data[col].unique()}")

except Exception as e:
    print(f"Error loading data: {e}")