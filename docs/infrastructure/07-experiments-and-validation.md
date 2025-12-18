# Continuous Experiment Framework for GEX-LLM Trading System

## Overview

Implement a production-ready continuous experiment system based on the RH2MAS research framework, adapted for GEX-options trading strategies. This enables automated, resumable backtesting across multiple strategy versions with comprehensive metrics capture.

## System Architecture

### Core Components

1. **GEXContinuousBacktest**: Main orchestrator with checkpoint/resume functionality
2. **Strategy Architecture**: Modular GEX strategy implementations (V0-V4 pattern)
3. **3-Tier Fallback System**: Database → Cache → API optimization with graceful degradation
4. **Advanced Metrics Capture**: Real-time GEX performance tracking and options analysis

## Key Features

### 1. Resumable Experiment System

- ✅ **Checkpoint/Resume**: Save state every N trading days, resume from any point
- ✅ **Version-Specific Folders**: Organized output structure (`reports/continuous_backtests/V{X}/`)
- ✅ **Multi-Year Support**: Seamless progression across years (2024 → 2025 → ...)
- ✅ **Status Tracking**: Real-time progress monitoring and completion status

### 2. Performance-Optimized Architecture

- ✅ **3-Tier Fallback Strategy**:
  - **Tier 1**: Database direct access (90%+ faster, ~3-7s vs 10+ min)
  - **Tier 2**: UnifiedCacheManager for missing data
  - **Tier 3**: API fallback with sample data graceful degradation
- ✅ **Batch Processing**: Weekly LLM analysis to reduce API calls
- ✅ **Smart Caching**: SQLite + JSON-based with TTL and deduplication

### 3. GEX Strategy Framework (V0-V4)

**V0: Raw GEX Baseline** (Current BaselineGEXStrategy)

- Fixed mechanical rules: Negative GEX → Short bias
- Thresholds: `gex_thresholds.negative_high: -5e9`
- Simple gamma exposure aggregation

**V1: Enhanced Technical GEX** (Current TechnicalIndicatorBaseline)

- MACD + RSI + GEX combination with consensus voting
- 68.8% signal rate (33 signals from 48 trading days)
- Dynamic risk management: 50% weak signals, 100% strong consensus

**V2: Strike-Level GEX Discovery** (New - addresses Issue #71)

- Individual strike analysis instead of aggregate GEX
- High-volume strike detection (>100K contracts)
- Gamma concentration mapping and extreme imbalances (>10:1 ratios)
- Target: 20+ high-quality signals per month vs current 1-3

**V3: Multi-Strike Pattern Recognition** (Enhanced)

- Strike clustering analysis for options laddering patterns
- Expiration-specific behaviors and gamma walls
- Strike-specific hedging requirements and flip points

**V4: LLM-Enhanced GEX Analysis** (Current MarketMechanicsAgent + Batch)

- O3-mini with WHO/WHOM/WHAT market mechanics analysis
- Batch processing: 1 LLM call per week analyzing all 5 days
- Rich context: Strike-level data + market mechanics + dealer positioning

### 4. Advanced Metrics System

**Real-time Capture**:

- Enhanced trade tracking with strike-level attribution
- GEX regime monitoring (positive/negative transitions)
- Options Greeks effectiveness (gamma, delta concentrations)
- Risk-adjusted metrics: Sharpe ratio, Calmar ratio, max drawdown

**GEX-Specific Metrics**:

- Strike hit rates vs volume predictions
- Gamma flip point accuracy
- Dealer hedging pressure effectiveness
- Pin risk vs realized pinning behavior

**Performance by GEX Regime**:

- Positive GEX environment performance
- Negative GEX environment performance
- Transition period capture rates

## Implementation Requirements

### Core Files to Implement

```bash
scripts/experiments/
├── gex_continuous_backtest.py          # Main orchestrator
├── checkpoint_manager.py               # State persistence
└── gex_metrics_collector.py            # GEX performance tracking

src/strategies/
├── base_gex_strategy.py                # Common interface
├── gex_strategy_v0.py                  # Raw GEX baseline
├── gex_strategy_v1.py                  # Technical enhanced
├── gex_strategy_v2.py                  # Strike-level discovery
├── gex_strategy_v3.py                  # Multi-strike patterns
└── gex_strategy_v4.py                  # LLM batch analysis

src/analysis/
├── gex_metrics_analyzer.py            # Post-analysis
├── gex_metrics_capture.py             # Real-time metrics
└── strike_performance_calculator.py   # Strike-level returns
```

### CLI Interface

```bash
# Run single strategy version
python scripts/experiments/gex_continuous_backtest.py --version V2 --symbol SPY --year 2024

# Run all versions sequentially
python scripts/experiments/gex_continuous_backtest.py --all-versions --symbol SPY --year 2024

# Check status across all experiments
python scripts/experiments/gex_continuous_backtest.py --status

# Advanced GEX analysis
python scripts/analysis/generate_gex_results_summary.py --advanced --strike-level
```

## Data Flow Architecture

```text
Options Data (Database/Cache/API) → GEXCalculator → Strike-Level GEX
                                                          ↓
Strategy-Specific Data:
- V0: Aggregate GEX → Fixed Thresholds
- V1: GEX + Technical → Consensus Voting
- V2: Strike-Level → Volume/Imbalance Signals
- V3: Multi-Strike → Pattern Recognition
- V4: Strike + Context → LLM Batch Analysis
                                                          ↓
                                  StrategyAgent → Trading Decision
                                                          ↓
                              GEXMetricsCapture → Performance Tracking
```

## Expected Performance Gains

- **90%+ Speed Improvement**: Database-first architecture vs API calls
- **Fault Tolerance**: Checkpoint/resume prevents data loss from market data timeouts
- **API Efficiency**: Batch processing reduces quota usage by 80%
- **Scalability**: Multi-ticker, multi-year support with SQLite persistence

## Success Metrics

- Complete year-long backtests within reasonable timeframes
- Successful checkpoint/resume across system restarts
- 90%+ database hit rates for repeated experiments
- Comprehensive GEX performance analysis across all strategy versions
- Clear separation between strategy logic and execution framework

## Integration Points

**Data Sources**:

- `consolidated_historical.db`: Primary options and GEX data
- `UnifiedCacheManager`: Secondary caching layer
- AutoGen tools: API fallback system

**Caching Layer**:

- SQLite database for GEX calculations
- JSON checkpoints for experiment state
- Memory caching for repeated calculations

**Monitoring**:

- Status tracking with progress reporting
- GEX regime change detection
- Strike-level performance attribution

## Testing Strategy

1. **Unit Tests**: Individual strategy validation
2. **Integration Tests**: End-to-end backtest execution
3. **Performance Tests**: Database optimization verification
4. **Regression Tests**: Results consistency across versions

## Critical Adaptations for GEX System

### From RH2MAS Stock System → GEX Options System

**Stock Sentiment → Options GEX Analysis**:

- RH2MAS: News sentiment analysis for stock decisions
- GEX System: Strike-level gamma exposure for options decisions

**Batch Processing Adaptation**:

- RH2MAS: Weekly news sentiment batching
- GEX System: Weekly options data + strike analysis batching

**Fallback Strategy**:

- RH2MAS: News API → Neutral sentiment
- GEX System: Database → Cache → API → Sample data

**Strategy Versioning**:

- RH2MAS: V0-V4 sentiment sophistication
- GEX System: V0-V4 GEX analysis sophistication

## Next Implementation Steps

1. **Checkpoint Manager**: Implement state persistence for experiment resumption
2. **Base Strategy Interface**: Create common interface for V0-V4 strategies
3. **Strike-Level V2**: Build enhanced strategy addressing Issue #71 discovery
4. **Batch LLM Processing**: Adapt weekly analysis for options context
5. **Metrics Framework**: Implement GEX-specific performance tracking

---

## Navigation

**Prerequisites**: [06-implementation-guide.md](06-implementation-guide.md)
**Next**: [08-maintenance-and-audits.md](08-maintenance-and-audits.md)
**Related**: [docs/validation/](../validation/)
