#!/usr/bin/env python3
"""Check collection progress by symbol."""

import sqlite3

conn = sqlite3.connect(".cache/options_historical.db")
cursor = conn.cursor()

cursor.execute(
    """
    SELECT symbol,
           COUNT(*) as dates,
           SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) as completed
    FROM collection_progress
    GROUP BY symbol
    ORDER BY symbol
"""
)

rows = cursor.fetchall()

print("Symbol   Total  Completed   %")
print("=" * 40)

total_dates = 0
total_completed = 0

for symbol, total, completed in rows:
    pct = 100 * completed / total if total > 0 else 0
    print(f"{symbol:8} {total:5}  {completed:9}  {pct:5.1f}%")
    total_dates += total
    total_completed += completed

print("=" * 40)
print(f"TOTAL    {total_dates:5}  {total_completed:9}  {100*total_completed/total_dates:.1f}%")

conn.close()
