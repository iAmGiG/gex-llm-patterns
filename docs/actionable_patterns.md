# Actionable Trading Patterns Framework

## Overview
Define specific gamma exposure patterns that translate to actionable swing/intraday trades.

## Pattern Categories

### 1. Gamma Squeeze Patterns

#### High Call Gamma Concentration
**When**: Call gamma > 80% of total gamma at strikes within 2% of spot
**Mechanics**: Dealers short calls → forced to buy shares on upward moves
**Timeframe**: Intraday (1-4 hours)
**Action**:
- Long underlying on breakouts above gamma concentration
- Target: Next major resistance or +1-2%
- Stop: Below gamma concentration strikes

#### Gamma Flip Zone
**When**: Spot price near the gamma flip point (positive to negative gamma)
**Mechanics**: Transition from stabilizing to destabilizing flows
**Timeframe**: Swing (1-3 days)
**Action**:
- Direction depends on momentum approaching flip
- Above flip = accelerated moves up
- Below flip = accelerated moves down

### 2. Pin Risk Patterns

#### Friday Expiration Pin
**When**: Large open interest at strike within 0.5% of spot on expiration day
**Mechanics**: Dealers manipulate price toward max pain to minimize payouts
**Timeframe**: Intraday (final 2 hours of trading)
**Action**:
- Fade moves away from pin strike
- Target: Pin strike ± 0.2%
- Stop: Beyond 0.8% from pin

#### Quarterly Pin Compression
**When**: Monthly + quarterly expirations create overlapping pin zones
**Mechanics**: Multiple expiration calendars create price compression
**Timeframe**: Week of expiration
**Action**:
- Sell volatility/premium
- Range trade between pin boundaries

### 3. Dealer Hedging Patterns

#### Delta Hedge Amplification
**When**: Large position changes force significant dealer re-hedging
**Mechanics**: Dealers buy high/sell low amplifying moves
**Timeframe**: 30-60 minutes
**Action**:
- Momentum continuation plays
- Enter on volume confirmation
- Exit when hedging complete

#### Negative Gamma Acceleration
**When**: In negative gamma regime with momentum
**Mechanics**: Dealers forced to sell into declines, buy into rallies
**Timeframe**: Intraday trend
**Action**:
- Trend following
- Tight stops (moves can reverse quickly)

## Implementation Status ✅

### ✅ **Pattern Recognition - IMPLEMENTED**
- **ActionablePatternDetector class** - `src/analysis/actionable_patterns.py`
- **Pattern detection algorithms** - Gamma squeeze, dealer trap, pin risk
- **Confidence thresholds** - 60%+ for signal generation

### ✅ **Risk Management - IMPLEMENTED**
- **Position sizing rules** - 0.5-2% based on confidence scores
- **Stop-loss algorithms** - Dynamic based on pattern type (1.5-3%)
- **Profit-taking rules** - Risk/reward ratios 1.5:1 minimum

### ✅ **Signal Generation - IMPLEMENTED**
- **LLM integration** - WHO/WHOM/WHAT mechanics confirmation
- **Real-time monitoring** - Live pattern detection
- **Execution timing** - Entry triggers and stop management

## Technical Implementation

### Core Classes

#### `ActionablePatternDetector`
**Location**: `src/analysis/actionable_patterns.py`

**Key Methods**:
- `detect_gamma_squeeze_signals()` - Identifies squeeze setups
- `detect_dealer_trap_signals()` - Finds dealer positioning traps
- `detect_pin_risk_signals()` - Calculates expiration pin dynamics

#### `ActionableSignal` Dataclass
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

### Usage Example
```python
from src.analysis.actionable_patterns import ActionablePatternDetector

detector = ActionablePatternDetector()
signals = detector.detect_all_signals(gex_metrics, mechanics_analysis)
for signal in signals:
    if signal.signal_strength == SignalStrength.STRONG:
        # Execute trade with signal parameters
        enter_position(signal.entry_price, signal.stop_loss, signal.position_size_pct)
```

## Risk Considerations
- Patterns work until they don't (regime changes)
- Options market makers are sophisticated
- Regulatory changes can break patterns
- Need multiple confirmation signals

## Success Metrics
- Win rate > 55%
- Risk/reward > 1.5:1
- Maximum drawdown < 5%
- Sharpe ratio > 1.0