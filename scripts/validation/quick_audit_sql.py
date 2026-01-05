#!/usr/bin/env python3
"""Quick SQL-based audit for large databases (Issue #183)."""

import sqlite3
import os
from pathlib import Path

db_path = Path(".cache/options_historical.db")

print("=" * 70)
print("OPTIONS DATA QUALITY AUDIT - Direct SQL")
print("=" * 70)
print(f"\nDatabase: {db_path}")
print(f"Size: {db_path.stat().st_size / (1024**3):.2f} GB")

with sqlite3.connect(db_path) as conn:
    total = conn.execute("SELECT COUNT(*) FROM options_chains").fetchone()[0]
    print(f"Total Records: {total:,}")

    # Symbol breakdown
    print("\nRecords by Symbol (top 10):")
    cursor = conn.execute(
        """
        SELECT symbol, COUNT(*) as cnt, MIN(trading_date) as min_d, MAX(trading_date) as max_d
        FROM options_chains
        GROUP BY symbol
        ORDER BY cnt DESC
        LIMIT 10
    """
    )
    for row in cursor:
        print(f"  {row[0]:8}: {row[1]:>12,} records ({row[2]} to {row[3]})")

    print("\n" + "-" * 70)
    print("CRITICAL CHECKS")
    print("-" * 70)

    # Track results
    critical_pass = 0
    critical_fail = 0
    important_pass = 0
    important_fail = 0

    # 1. Bid > Ask violations
    print("\n[CRITICAL] Bid <= Ask:")
    bid_ask_total = conn.execute(
        """
        SELECT COUNT(*) FROM options_chains
        WHERE bid IS NOT NULL AND ask IS NOT NULL AND bid > 0 AND ask > 0
    """
    ).fetchone()[0]
    bid_ask_violations = conn.execute(
        """
        SELECT COUNT(*) FROM options_chains
        WHERE bid IS NOT NULL AND ask IS NOT NULL AND bid > 0 AND ask > 0 AND bid > ask
    """
    ).fetchone()[0]
    pct = (bid_ask_violations / bid_ask_total * 100) if bid_ask_total > 0 else 0
    status = "PASS" if pct == 0 else "FAIL"
    if pct == 0:
        critical_pass += 1
    else:
        critical_fail += 1
    print(f"  Records checked: {bid_ask_total:,}")
    print(f"  Violations: {bid_ask_violations:,} ({pct:.4f}%)")
    print(f"  Status: {status}")

    # 2. Call delta range
    print("\n[CRITICAL] Call Delta [0, 1]:")
    call_total = conn.execute(
        """
        SELECT COUNT(*) FROM options_chains
        WHERE option_type = 'call' AND delta IS NOT NULL
    """
    ).fetchone()[0]
    call_violations = conn.execute(
        """
        SELECT COUNT(*) FROM options_chains
        WHERE option_type = 'call' AND delta IS NOT NULL AND (delta < 0 OR delta > 1)
    """
    ).fetchone()[0]
    pct = (call_violations / call_total * 100) if call_total > 0 else 0
    status = "PASS" if pct == 0 else "FAIL"
    if pct == 0:
        critical_pass += 1
    else:
        critical_fail += 1
    print(f"  Records checked: {call_total:,}")
    print(f"  Violations: {call_violations:,} ({pct:.4f}%)")
    print(f"  Status: {status}")

    # 3. Put delta range
    print("\n[CRITICAL] Put Delta [-1, 0]:")
    put_total = conn.execute(
        """
        SELECT COUNT(*) FROM options_chains
        WHERE option_type = 'put' AND delta IS NOT NULL
    """
    ).fetchone()[0]
    put_violations = conn.execute(
        """
        SELECT COUNT(*) FROM options_chains
        WHERE option_type = 'put' AND delta IS NOT NULL AND (delta < -1 OR delta > 0)
    """
    ).fetchone()[0]
    pct = (put_violations / put_total * 100) if put_total > 0 else 0
    status = "PASS" if pct == 0 else "FAIL"
    if pct == 0:
        critical_pass += 1
    else:
        critical_fail += 1
    print(f"  Records checked: {put_total:,}")
    print(f"  Violations: {put_violations:,} ({pct:.4f}%)")
    print(f"  Status: {status}")

    # 4. Gamma non-negative
    print("\n[CRITICAL] Gamma >= 0:")
    gamma_total = conn.execute(
        """
        SELECT COUNT(*) FROM options_chains WHERE gamma IS NOT NULL
    """
    ).fetchone()[0]
    gamma_violations = conn.execute(
        """
        SELECT COUNT(*) FROM options_chains WHERE gamma IS NOT NULL AND gamma < 0
    """
    ).fetchone()[0]
    pct = (gamma_violations / gamma_total * 100) if gamma_total > 0 else 0
    status = "PASS" if pct == 0 else "FAIL"
    if pct == 0:
        critical_pass += 1
    else:
        critical_fail += 1
    print(f"  Records checked: {gamma_total:,}")
    print(f"  Violations: {gamma_violations:,} ({pct:.4f}%)")
    print(f"  Status: {status}")

    # 5. Strike positive
    print("\n[CRITICAL] Strike > 0:")
    strike_violations = conn.execute(
        """
        SELECT COUNT(*) FROM options_chains WHERE strike <= 0
    """
    ).fetchone()[0]
    pct = (strike_violations / total * 100) if total > 0 else 0
    status = "PASS" if pct == 0 else "FAIL"
    if pct == 0:
        critical_pass += 1
    else:
        critical_fail += 1
    print(f"  Records checked: {total:,}")
    print(f"  Violations: {strike_violations:,} ({pct:.4f}%)")
    print(f"  Status: {status}")

    # 6. Open Interest non-negative
    print("\n[CRITICAL] Open Interest >= 0:")
    oi_total = conn.execute(
        """
        SELECT COUNT(*) FROM options_chains WHERE open_interest IS NOT NULL
    """
    ).fetchone()[0]
    oi_violations = conn.execute(
        """
        SELECT COUNT(*) FROM options_chains WHERE open_interest IS NOT NULL AND open_interest < 0
    """
    ).fetchone()[0]
    pct = (oi_violations / oi_total * 100) if oi_total > 0 else 0
    status = "PASS" if pct == 0 else "FAIL"
    if pct == 0:
        critical_pass += 1
    else:
        critical_fail += 1
    print(f"  Records checked: {oi_total:,}")
    print(f"  Violations: {oi_violations:,} ({pct:.4f}%)")
    print(f"  Status: {status}")

    print("\n" + "-" * 70)
    print("IMPORTANT CHECKS")
    print("-" * 70)

    # 7. IV reasonable range
    print("\n[IMPORTANT] IV in [1%, 500%]:")
    iv_total = conn.execute(
        """
        SELECT COUNT(*) FROM options_chains WHERE implied_volatility IS NOT NULL
    """
    ).fetchone()[0]
    iv_violations = conn.execute(
        """
        SELECT COUNT(*) FROM options_chains
        WHERE implied_volatility IS NOT NULL AND (implied_volatility < 0.01 OR implied_volatility > 5.0)
    """
    ).fetchone()[0]
    pct = (iv_violations / iv_total * 100) if iv_total > 0 else 0
    status = "PASS" if pct < 5 else "FAIL"
    if pct < 5:
        important_pass += 1
    else:
        important_fail += 1
    print(f"  Records checked: {iv_total:,}")
    print(f"  Violations: {iv_violations:,} ({pct:.2f}%)")
    print(f"  Status: {status}")

    # 8. Theta negative
    print("\n[IMPORTANT] Theta < 0:")
    theta_total = conn.execute(
        """
        SELECT COUNT(*) FROM options_chains WHERE theta IS NOT NULL
    """
    ).fetchone()[0]
    theta_violations = conn.execute(
        """
        SELECT COUNT(*) FROM options_chains WHERE theta IS NOT NULL AND theta > 0
    """
    ).fetchone()[0]
    pct = (theta_violations / theta_total * 100) if theta_total > 0 else 0
    status = "PASS" if pct < 5 else "FAIL"
    if pct < 5:
        important_pass += 1
    else:
        important_fail += 1
    print(f"  Records checked: {theta_total:,}")
    print(f"  Violations: {theta_violations:,} ({pct:.2f}%)")
    print(f"  Status: {status}")

    print("\n" + "-" * 70)
    print("INFO CHECKS")
    print("-" * 70)

    # 9. Greeks coverage
    print("\n[INFO] Greeks Coverage:")
    has_all_greeks = conn.execute(
        """
        SELECT COUNT(*) FROM options_chains
        WHERE delta IS NOT NULL AND gamma IS NOT NULL AND theta IS NOT NULL AND vega IS NOT NULL
    """
    ).fetchone()[0]
    coverage_pct = (has_all_greeks / total * 100) if total > 0 else 0
    print(f"  Records with complete Greeks: {has_all_greeks:,} ({coverage_pct:.2f}%)")

    # 10. Pricing coverage
    print("\n[INFO] Pricing Coverage:")
    has_pricing = conn.execute(
        """
        SELECT COUNT(*) FROM options_chains
        WHERE bid IS NOT NULL AND ask IS NOT NULL AND bid > 0 AND ask > 0
    """
    ).fetchone()[0]
    pricing_pct = (has_pricing / total * 100) if total > 0 else 0
    print(f"  Records with bid/ask: {has_pricing:,} ({pricing_pct:.2f}%)")

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    print(f"\nCritical Checks: {critical_pass}/{critical_pass + critical_fail} passed")
    print(f"Important Checks: {important_pass}/{important_pass + important_fail} passed")

    if critical_fail > 0:
        overall = "RED"
        print(f"\nOverall Status: {overall}")
        print("\nData quality has CRITICAL issues.")
        print("Papers 1 & 2 results may need review.")
        print("DO NOT proceed with Paper 3 until issues resolved.")
    elif important_fail > 0:
        overall = "YELLOW"
        print(f"\nOverall Status: {overall}")
        print("\nData quality has minor issues. Papers 1 & 2 likely OK.")
        print("Investigate important check failures before Paper 3.")
    else:
        overall = "GREEN"
        print(f"\nOverall Status: {overall}")
        print("\nData quality is GOOD. Papers 1 & 2 results are reliable.")
        print("Safe to proceed with Paper 3 cross-asset analysis.")

    print("=" * 70)
