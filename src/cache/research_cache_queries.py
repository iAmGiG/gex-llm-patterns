"""ResearchCache Query Utilities

Common query patterns for Papers 1-5.

Usage:
    from gex_db_infrastructure.cache.research_cache_queries import *

    # Get all 2021 detections with high confidence
    detections = get_detections_by_year(2021, min_confidence=80.0)

    # Get detection statistics by year
    stats = get_detection_stats_by_year()
"""

import sqlite3
from typing import Dict, List

from gex_db_infrastructure.cache.research_cache import ResearchCache


def get_detections_by_year(year: int, min_confidence: float = 0.0) -> List[Dict]:
    """Get all detections for a specific year.

    Args:
        year: Year to query (e.g., 2021)
        min_confidence: Minimum confidence score (0-100)

    Returns:
        List of detection dictionaries
    """
    cache = ResearchCache()
    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"

    # Use SQL-level filtering for better performance
    detections_df = cache.get_detections(
        symbol="SPY",
        start_date=start_date,
        end_date=end_date,
        pattern_ids=["regime_30day"],
        min_confidence=int(min_confidence) if min_confidence > 0 else None,
    )

    # Convert DataFrame to list of dicts
    if detections_df.empty:
        return []

    return detections_df.to_dict("records")


def get_detection_stats_by_year() -> Dict[int, Dict]:
    """Get detection statistics grouped by year.

    Returns:
        Dict mapping year -> {detected, total, rate, avg_confidence}
    """
    stats = {}

    for year in range(2020, 2026):
        detections = get_detections_by_year(year)

        detected = sum(1 for d in detections if d.get("detected", False))
        total = len(detections)
        rate = (detected / total * 100) if total > 0 else 0.0

        # Filter out None values before calculating average
        confidences = [d.get("confidence") for d in detections if d.get("confidence") is not None]
        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

        stats[year] = {
            "detected": detected,
            "total": total,
            "detection_rate": rate,
            "avg_confidence": avg_conf,
        }

    return stats


def get_experiment_history(run_id_pattern: str = None) -> List[Dict]:
    """Get experiment run history.

    Args:
        run_id_pattern: Optional pattern to match (e.g., "paper2")

    Returns:
        List of experiment run dictionaries
    """
    cache = ResearchCache()

    # Query all experiments
    conn = sqlite3.connect(cache.db_path)
    cursor = conn.cursor()

    # Use created_date (correct column name per ResearchCache schema)
    if run_id_pattern:
        cursor.execute(
            "SELECT * FROM experiment_runs WHERE run_id LIKE ? ORDER BY created_date DESC",
            (f"%{run_id_pattern}%",),
        )
    else:
        cursor.execute("SELECT * FROM experiment_runs ORDER BY created_date DESC")

    columns = [desc[0] for desc in cursor.description]
    results = [dict(zip(columns, row)) for row in cursor.fetchall()]
    conn.close()
    return results


def compare_detections_by_confidence(threshold: float = 70.0) -> Dict:
    """Compare detection rates above/below confidence threshold.

    Args:
        threshold: Confidence threshold (0-100)

    Returns:
        Dict with above/below statistics
    """
    cache = ResearchCache()

    # Get all detections
    all_detections_df = cache.get_detections(
        symbol="SPY",
        start_date="2020-01-01",
        end_date="2025-12-31",
        pattern_ids=["regime_30day"],
    )

    # Convert DataFrame to list of dicts
    if all_detections_df.empty:
        return {
            "threshold": threshold,
            "above": {"total": 0, "detected": 0, "rate": 0.0},
            "below": {"total": 0, "detected": 0, "rate": 0.0},
        }

    all_detections = all_detections_df.to_dict("records")

    # Handle None confidence values safely
    above = [d for d in all_detections if (d.get("confidence") or 0) >= threshold]
    below = [d for d in all_detections if (d.get("confidence") or 0) < threshold]

    above_detected = sum(1 for d in above if d.get("detected", False))
    below_detected = sum(1 for d in below if d.get("detected", False))

    return {
        "threshold": threshold,
        "above": {
            "total": len(above),
            "detected": above_detected,
            "rate": (above_detected / len(above) * 100) if above else 0.0,
        },
        "below": {
            "total": len(below),
            "detected": below_detected,
            "rate": (below_detected / len(below) * 100) if below else 0.0,
        },
    }
