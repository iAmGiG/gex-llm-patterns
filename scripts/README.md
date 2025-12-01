# Scripts Directory

This directory contains all executable scripts for the GEX-LLM Patterns project, organized by purpose.

## Directory Structure

### `baseline_comparison/` - **Primary Testing Framework**

Production-ready baseline comparison system

- `real_baseline_vs_llm.py` - **Main test runner** comparing O3-mini LLM vs mechanical baselines
  - Uses real market data with configurable parameters
  - Configurable via `config_defaults/baseline_comparison_config.yaml`
  - Issue #58 implementation

### `runs/` - **Experiment Management**

Continuous experiment state management

- `checkpoint_manager.py` - Handles resumable long-running backtests
  - Progress tracking and state persistence
  - Checkpoint every 5 trading days
  - Supports experiment resume from any checkpoint

### `validation/` - **Enhanced Pattern Testing**

Enhanced strike-level pattern validation (75% validated success rate)

- `test_enhanced_patterns.py` - Enhanced pattern detection validation
- `test_enhanced_daily.py` - Daily enhanced pattern testing
- `test_compound_patterns.py` - **Compound pattern testing** with multiple signal confirmation
  - High Probability Pin (gamma + volume + timing)
  - Volume Gamma Breakout (volume spike + gamma shift)
  - Gamma-Volume-Time Confluence (all signals align)
- `test_time_patterns.py` - **Time-based pattern testing** with intraday timing analysis
  - Friday 3:30 PM validated patterns (75% success rate)
  - Daily algo times (10:00, 14:30, 15:30, 15:50)
  - Expiration timing effects (0DTE, weekly, monthly)
  - Intraday gamma shift detection
- `test_daily_signal_generation.py` - **Daily signal capacity validation**
  - Tests 30+ monthly signal target (10x Friday-only improvement)
  - SPY + QQQ daily 0DTE opportunity analysis
  - Signal generation rate and quality metrics
- `test_pattern_stability.py` - **Pattern robustness across market conditions**
  - Low VIX (complacency), Normal VIX, High VIX (stress) testing
  - Pattern effectiveness across volatility regimes
- `test_10am_reversal.py` - **10 AM reversal pattern (specific)**
  - Fade strong overnight moves when gamma > 30% at strike
  - Expected 65% success rate validation
- `test_afternoon_drift.py` - **Afternoon drift pattern (specific)**
  - Follow momentum in low gamma zones after 2 PM
  - Expected 60% success rate validation

### `analysis/`

Data analysis and exploration

- `explain_options_data.py` - Analyzes and explains options data structure
- `gamma_pinning_validator.py` - Validates gamma pinning patterns (Issue #73)

### `data_collection/`

Data gathering and management

- `start_historical_collection.py` - Starts historical data collection
- `automation/` - 24/7 automated collection system
  - `automated_data_collector.py` - Main collection service
  - `monitor_collection.py` - Progress monitoring
  - `test_spx_access.py` - API access validation
  - `test_polygon_collection.py` - Stock data testing

### `database/`

Database operations and migrations

- `migrate_to_intraday.py` - Migrates data to support intraday timestamps (Issue #72)

### `examples/`

Example implementations and demonstrations

- `example_flexible_algo_times.py` - Flexible algorithm timing examples

### `experiments/`

Experimental scripts and research

### `utils/` - **Experiment Infrastructure**

Shared utilities for experiment management

- `experiment_reporter.py` - **Unified results storage** for all experiment types
  - Consistent JSON format with metadata
  - Organized storage: `reports/{experiment_type}/{name}_{timestamp}.json`
  - Methods for validation, baseline comparison, continuous testing results
  - Experiment listing and retrieval utilities

## Primary Usage Patterns

**Main Testing (Issue #71 - Production Deployment):**

```bash
# Run comprehensive baseline comparison with real data
python scripts/baseline_comparison/real_baseline_vs_llm.py

# With custom parameters
python scripts/baseline_comparison/real_baseline_vs_llm.py --symbol SPY --start-date 2024-01-01 --end-date 2024-03-31
```

**Enhanced Pattern Validation:**

```bash
# Test enhanced patterns (75% validated gamma pinning)
python scripts/validation/test_enhanced_patterns.py
python scripts/validation/test_enhanced_daily.py

# Test compound patterns with multiple signal confirmation
python scripts/validation/test_compound_patterns.py --symbol SPY --start-date 2024-06-01 --end-date 2024-06-30

# Test time-based patterns with intraday timing
python scripts/validation/test_time_patterns.py --symbol SPY --start-date 2024-06-01 --end-date 2024-06-30

# Test daily signal generation capacity (30+ monthly target)
python scripts/validation/test_daily_signal_generation.py --start-date 2024-06-01 --end-date 2024-06-30

# Test pattern stability across VIX regimes
python scripts/validation/test_pattern_stability.py --start-date 2024-03-01 --end-date 2024-06-30

# Test specific intraday patterns
python scripts/validation/test_10am_reversal.py --symbol SPY --start-date 2024-06-01 --end-date 2024-06-30
python scripts/validation/test_afternoon_drift.py --symbol SPY --start-date 2024-06-01 --end-date 2024-06-30
```

**Checkpoint Management:**

```bash
# Check experiment status
python -c "from scripts.runs.checkpoint_manager import CheckpointManager; cm = CheckpointManager(); print(cm.get_experiment_status())"
```

**Data Collection:**

```bash
# Start historical collection
python scripts/data_collection/start_historical_collection.py

# Monitor automated collection
python scripts/data_collection/automation/monitor_collection.py
```

**Experiment Results Management:**

```bash
# Import and use experiment reporter in scripts
from scripts.utils.experiment_reporter import ExperimentReporter

reporter = ExperimentReporter()
# Store validation results
reporter.store_validation_results("0dte_gamma", "SPY", "2024-06-25", "2024-06-28", results)
# Store baseline comparison
reporter.store_baseline_comparison("enhanced_vs_basic", ["SPY"], "2024-01-01", "2024-03-31", results)
```

## Current Focus: Production Testing (Issue #71)

The enhanced strike-level pattern detection system is deployed and validated. Primary testing approach:

1. **`real_baseline_vs_llm.py`** - Comprehensive comparison with real market data
2. **Checkpoint manager** - For continuous/resumable experiments
3. **Enhanced pattern validators** - For the 75% validated gamma pinning system

## Organization Principles

- **Production-ready testing** - Main testing framework uses real market data
- **Resumable experiments** - Checkpoint system for long-running backtests
- **Validated patterns** - Enhanced detection with 75% success rate
- **Logical grouping** - Scripts grouped by primary purpose
- **Clear naming** - Descriptive filenames indicating functionality
