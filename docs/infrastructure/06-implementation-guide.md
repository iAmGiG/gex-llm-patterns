# Implementation Guide: Patterns and Intraday Support

## Overview

This guide consolidates actionable trading pattern implementation with comprehensive intraday support for gamma pinning validation. It provides both practical trading rules and technical implementation details.

---

## Part 1: Actionable Trading Patterns

### Overview

Define specific gamma exposure patterns that translate to actionable swing/intraday trades.

**Note**: This section complements the pattern library (`src/analysis/pattern_library.py`) by focusing on trading implementation. The pattern library contains the 15 core WHO/WHOM/WHAT patterns for LLM analysis, while this guide provides practical trading rules and risk management.

### Pattern Categories

#### 1. Gamma Squeeze Patterns

**High Call Gamma Concentration**

**When**: Call gamma > 80% of total gamma at strikes within 2% of spot
**Mechanics**: Dealers short calls → forced to buy shares on upward moves
**Timeframe**: Intraday (1-4 hours)
**Action**:

- Long underlying on breakouts above gamma concentration
- Target: Next major resistance or +1-2%
- Stop: Below gamma concentration strikes

**Gamma Flip Zone**

**When**: Spot price near the gamma flip point (positive to negative gamma)
**Mechanics**: Transition from stabilizing to destabilizing flows
**Timeframe**: Swing (1-3 days)
**Action**:

- Direction depends on momentum approaching flip
- Above flip = accelerated moves up
- Below flip = accelerated moves down

#### 2. Pin Risk Patterns

**Friday Expiration Pin**

**When**: Large open interest at strike within 0.5% of spot on expiration day
**Mechanics**: Dealers manipulate price toward max pain to minimize payouts
**Timeframe**: Intraday (final 2 hours of trading)
**Action**:

- Fade moves away from pin strike
- Target: Pin strike ± 0.2%
- Stop: Beyond 0.8% from pin

**Quarterly Pin Compression**

**When**: Monthly + quarterly expirations create overlapping pin zones
**Mechanics**: Multiple expiration calendars create price compression
**Timeframe**: Week of expiration
**Action**:

- Sell volatility/premium
- Range trade between pin boundaries

#### 3. Dealer Hedging Patterns

**Delta Hedge Amplification**

**When**: Large position changes force significant dealer re-hedging
**Mechanics**: Dealers buy high/sell low amplifying moves
**Timeframe**: 30-60 minutes
**Action**:

- Momentum continuation plays
- Enter on volume confirmation
- Exit when hedging complete

**Negative Gamma Acceleration**

**When**: In negative gamma regime with momentum
**Mechanics**: Dealers forced to sell into declines, buy into rallies
**Timeframe**: Intraday trend
**Action**:

- Trend following
- Tight stops (moves can reverse quickly)

### Implementation Status ✅

#### ✅ Pattern Recognition - IMPLEMENTED

- **ActionablePatternDetector class** - `src/analysis/actionable_patterns.py`
- **Pattern detection algorithms** - Gamma squeeze, dealer trap, pin risk
- **Confidence thresholds** - 60%+ for signal generation

#### ✅ Risk Management - IMPLEMENTED

- **Position sizing rules** - 0.5-2% based on confidence scores
- **Stop-loss algorithms** - Dynamic based on pattern type (1.5-3%)
- **Profit-taking rules** - Risk/reward ratios 1.5:1 minimum

#### ✅ Signal Generation - IMPLEMENTED

- **LLM integration** - WHO/WHOM/WHAT mechanics confirmation
- **Real-time monitoring** - Live pattern detection
- **Execution timing** - Entry triggers and stop management

### Technical Implementation

#### Core Classes

**ActionablePatternDetector**

**Location**: `src/analysis/actionable_patterns.py`

**Key Methods**:

- `detect_gamma_squeeze_signals()` - Identifies squeeze setups
- `detect_dealer_trap_signals()` - Finds dealer positioning traps
- `detect_pin_risk_signals()` - Calculates expiration pin dynamics

**ActionableSignal Dataclass**

**Components**:

```python
@dataclass
class ActionableSignal:
    pattern: MarketMechanicsPattern
    signal_strength: SignalStrength  # STRONG/MODERATE/WEAK
    entry_price: float
    entry_trigger: str
    stop_loss: float
    initial_target: float
    position_size_pct: float  # 0.5-2% of portfolio
    risk_reward_ratio: float  # Minimum 1.5:1
    confidence_factors: List[str]
```

#### Usage Example

```python
from src.analysis.actionable_patterns import ActionablePatternDetector

detector = ActionablePatternDetector()
signals = detector.detect_all_signals(gex_metrics, mechanics_analysis)
for signal in signals:
    if signal.signal_strength == SignalStrength.STRONG:
        # Execute trade with signal parameters
        enter_position(signal.entry_price, signal.stop_loss, signal.position_size_pct)
```

### Risk Considerations

- Patterns work until they don't (regime changes)
- Options market makers are sophisticated
- Regulatory changes can break patterns
- Need multiple confirmation signals

### Success Metrics

- Win rate > 55%
- Risk/reward > 1.5:1
- Maximum drawdown < 5%
- Sharpe ratio > 1.0

---

## Part 2: Intraday Implementation

### Overview

Successfully implemented comprehensive intraday support for gamma pinning validation with 10-minute intervals aligned to algo system updates and key market times.

### ✅ Components Implemented

#### 1. Database Schema (Issue #72)

**Files**: `scripts/database/create_intraday_schema.sql`, `scripts/database/migrate_to_intraday.py`

**New Tables**:

- `intraday_gex_metrics` - 10-minute GEX snapshots
- `intraday_strike_details` - Strike-level gamma data with timestamps
- `algo_time_markers` - Key trading time markers

**Views Created**:

- `friday_gamma_analysis` - Friday-specific GEX data
- `key_algo_times` - Algo trading time analysis
- `max_gamma_strikes` - Max gamma strike finder
- `friday_330_validation` - Friday 3:30 PM validation query

**Migration**: ✅ Successfully applied to `.cache/consolidated_historical.db`

#### 2. Intraday Cache System

**File**: `src/cache/intraday_cache.py`

**Features**:

- Timestamp-based storage: `.cache/intraday_options/SPY/2024-01-17/1530.json`
- Market hours validation (9:30 AM - 4:15 PM ET)
- 10-minute interval alignment with algo times
- Automatic cleanup of old data
- Session type tracking (regular/extended)

**Key Methods**:

```python
cache.store_intraday_options(symbol, timestamp, data)
cache.get_intraday_gex(symbol, timestamp)
cache.get_friday_algo_times(symbol, start_date, end_date)
```

#### 3. Enhanced 2-Tier Data System

**File**: `src/data/enhanced_two_tier_system.py`

**Capabilities**:

- Seamless daily + intraday queries
- Database → Cache fallback for timestamps
- Automatic data promotion between tiers
- Enhanced performance tracking

**Methods**:

```python
system.fetch_intraday_gex_data(timestamp, symbol)
system.get_friday_gamma_data(start_date, end_date, symbol)
system.store_intraday_data(timestamp, symbol, options_data, market_data, gex_data)
```

#### 4. Gamma Pinning Validation Tool

**File**: `scripts/analysis/gamma_pinning_validator.py`

**Validation Capabilities**:

- Friday gamma pinning hypothesis testing
- Multi-time algo analysis (9:30, 10:00, 14:30, 15:30, 15:40, 15:50)
- Price movement tracking toward max gamma strikes
- Statistical summary with proximity categorization
- CSV export for further analysis

**Usage**:

```bash
# Single time validation
python scripts/analysis/gamma_pinning_validator.py --start-date 2024-01-01 --end-date 2024-03-31 --time 15:30:00

# Multi-time analysis
python scripts/analysis/gamma_pinning_validator.py --start-date 2024-01-01 --end-date 2024-03-31 --multi-time --export
```

### Key Algo Times Supported

Based on user requirements for algo system alignment:

- **09:30:00** - Market open
- **10:00:00** - Algo 10am updates
- **14:30:00** - FOMC/Fed 2:30 PM (special days)
- **15:30:00** - Gamma 3:30 PM (key validation time)
- **15:40:00** - Gamma 3:40 PM
- **15:50:00** - Gamma 3:50 PM
- **16:00:00** - Market close
- **16:15:00** - Extended ETF close

### Storage Architecture

#### Database Location

**Confirmed Optimal**: `.cache/consolidated_historical.db`

- Unified data strategy with existing cache
- Simple backup/recovery (single directory)
- Scales appropriately (36KB → ~1MB projected for full intraday year)

#### Storage Impact

- **10-minute intervals**: 42 snapshots per trading day
- **Annual storage**: ~10,584 records per symbol per year
- **Database size projection**: ~1-2MB for SPY full year intraday data

#### Performance Characteristics

- **Database hit rate**: Expected >90% for repeated experiments
- **Query performance**: <2 seconds for intraday time series
- **Indexes**: Optimized for symbol+timestamp and time-only queries

### Validation Framework

#### Gamma Pinning Hypothesis

**Test**: "SPY prices move toward max gamma strikes on Fridays at key algo times"

**Validation Metrics**:

- **Close pin rate**: % of Fridays with price within $5 of max gamma strike
- **Movement rate**: % of Fridays showing price movement toward gamma strike
- **Distance statistics**: Average, median distance to max gamma strikes
- **Proximity distribution**: CLOSE (<$5), MODERATE ($5-10), FAR (>$10)

#### Statistical Analysis

```python
# Example validation output
{
    'total_fridays': 52,
    'close_pin_rate_pct': 23.1,
    'moved_toward_gamma_rate_pct': 67.3,
    'avg_distance': 7.8,
    'proximity_distribution': {
        'close_count': 12,
        'moderate_count': 25,
        'far_count': 15
    }
}
```

### Integration with Continuous Framework

#### Strategy Enhancement

The intraday system integrates with existing strategy framework:

- **V0-V1**: Daily strategies unchanged
- **V2**: Enhanced strike-level analysis with intraday data
- **V3-V4**: Time-aware pattern recognition and LLM analysis

#### Checkpoint System

Batch processing enhanced for intraday:

- Weekly batches include intraday timestamps
- Checkpoint state preserves intraday analysis progress
- Resume capability for time-series experiments

### Next Steps for Full Implementation

#### 1. Data Population

```python
# Collect intraday data during market hours
python scripts/data_collection/intraday_collector.py --symbol SPY --start-time 09:30 --end-time 16:15 --interval 10min
```

#### 2. GEX Calculator Enhancement (Deferred to AutoTrader-AgentEdge #573, 2026-04)

- Real-time GEX calculation at 10-minute intervals
- Strike-level gamma exposure tracking
- Time-series gamma flip point detection

#### 3. Alpha Vantage Integration (Completed 2025; used by Paper 1 and Paper 2 data collection)

- Historical options data population via API
- Intraday options chain fetching
- Automatic database population

#### 4. Production Deployment

- Market hours data collection
- Real-time gamma pinning monitoring
- Automated validation reporting

### API Reference

#### Database Queries

```sql
-- Friday 3:30 PM validation
SELECT * FROM friday_330_validation
WHERE symbol = 'SPY' AND friday_date BETWEEN '2024-01-01' AND '2024-03-31';

-- Max gamma strikes at specific time
SELECT * FROM max_gamma_strikes
WHERE symbol = 'SPY' AND timestamp LIKE '2024-01-05 15:30:00';

-- Key algo times analysis
SELECT * FROM key_algo_times
WHERE symbol = 'SPY' AND DATE(timestamp) = '2024-01-05';
```

#### Python Interface

```python
from src.data.enhanced_two_tier_system import EnhancedTwoTierSystem
from scripts.analysis.gamma_pinning_validator import GammaPinningValidator

# Initialize systems
data_system = EnhancedTwoTierSystem()
validator = GammaPinningValidator('SPY')

# Fetch intraday data
gex_data = data_system.fetch_intraday_gex_data('2024-01-05 15:30:00', 'SPY')

# Run validation
results = validator.validate_friday_gamma_pinning('2024-01-01', '2024-03-31', '15:30:00')
```

### Success Criteria ✅

- [x] **10-minute granularity**: Database and cache support timestamp storage
- [x] **Algo time alignment**: Key times (9:30, 10:00, 14:30, 15:30, 15:40, 15:50) supported
- [x] **Market hours validation**: 9:30 AM - 4:15 PM ET with session tracking
- [x] **Friday gamma pinning**: Complete validation framework implemented
- [x] **Database migration**: Intraday schema successfully applied
- [x] **Performance optimization**: Indexed queries and 2-tier caching
- [x] **Export capabilities**: CSV export for statistical analysis
- [x] **Backward compatibility**: Daily data systems remain functional

---

The implementation provides a complete foundation for sophisticated intraday gamma pinning analysis while maintaining the existing daily analysis capabilities. Ready for data population and production validation testing.

---

## Navigation

**Prerequisites**: [05-llm-integration.md](05-llm-integration.md)
**Next**: [07-experiments-and-validation.md](07-experiments-and-validation.md)
**Related**: [src/analysis/pattern_library.py](../../src/analysis/pattern_library.py), [scripts/analysis/gamma_pinning_validator.py](../../scripts/analysis/gamma_pinning_validator.py)
