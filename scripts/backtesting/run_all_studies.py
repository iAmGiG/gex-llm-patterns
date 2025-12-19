"""
Master Script: Run All Backtesting Studies

Orchestrates running all backtesting studies and consolidates results.
"""

import logging
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = Path(__file__).parent.parent.parent / "reports" / "backtesting_research"

STUDIES = [
    ("baseline_study", "run_baseline_study.py"),
    ("regime_analysis", "run_regime_analysis.py"),
    ("gex_vs_technicals", "run_gex_vs_technicals.py"),
]


def run_study(study_name: str, script_name: str) -> dict:
    """Run a single study and return status."""
    script_path = SCRIPT_DIR / script_name
    start_time = datetime.now()

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute timeout
        )

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        return {
            "study": study_name,
            "status": "success" if result.returncode == 0 else "failed",
            "duration_seconds": round(duration, 2),
            "return_code": result.returncode,
        }

    except subprocess.TimeoutExpired:
        return {
            "study": study_name,
            "status": "timeout",
            "duration_seconds": 600,
            "return_code": -1,
        }
    except Exception as e:
        return {
            "study": study_name,
            "status": "error",
            "error": str(e),
            "return_code": -1,
        }


def main():
    """Run all studies in parallel."""
    logger.info("=" * 70)
    logger.info("BACKTESTING RESEARCH SUITE")
    logger.info(f"Running {len(STUDIES)} studies in parallel")
    logger.info("=" * 70)

    start_time = datetime.now()
    results = []

    # Run studies in parallel
    with ProcessPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(run_study, name, script): name for name, script in STUDIES}

        for future in as_completed(futures):
            study_name = futures[future]
            try:
                result = future.result()
                results.append(result)
                logger.info(f"  {study_name}: {result['status']} ({result['duration_seconds']}s)")
            except Exception as e:
                logger.error(f"  {study_name}: error - {e}")
                results.append({"study": study_name, "status": "error", "error": str(e)})

    end_time = datetime.now()
    total_duration = (end_time - start_time).total_seconds()

    # Compile summary
    summary = {
        "run_date": start_time.isoformat(),
        "total_duration_seconds": round(total_duration, 2),
        "studies_run": len(results),
        "successful": sum(1 for r in results if r["status"] == "success"),
        "failed": sum(1 for r in results if r["status"] != "success"),
        "study_results": results,
    }

    # Save summary
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    summary_file = OUTPUT_DIR / "research_summary.yaml"

    with open(summary_file, "w") as f:
        yaml.dump(summary, f, default_flow_style=False, sort_keys=False)

    # Print summary
    print("\n" + "=" * 70)
    print("RESEARCH SUITE COMPLETE")
    print("=" * 70)
    print(f"Total Duration: {total_duration:.1f}s")
    print(f"Studies Run: {summary['studies_run']}")
    print(f"Successful: {summary['successful']}")
    print(f"Failed: {summary['failed']}")
    print(f"\nResults saved to: {OUTPUT_DIR}")
    print("=" * 70)

    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
