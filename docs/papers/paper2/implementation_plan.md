# Paper #2: Sequential GEX Implementation Plan

**Status**: Planning Phase
**Last Updated**: November 3, 2025

---

## Implementation Strategy

Based on the existing codebase architecture, here's how to set up the 5-day sequential validation:

### Architecture Analysis

**Current (Paper #1) - Single-Day Snapshot**:

```
validate_pattern_taxonomy.py
  └─> MarketMechanicsAgent.run_experiment()
      └─> fetch_options_data(date)  # Single day
      └─> GEXCalculator.calculate_gex_profile()  # Single snapshot
      └─> LLM prompt with single-day metrics
```

**New (Paper #2) - 5-Day Sequential**:

```
validate_sequential_patterns.py (NEW)
  └─> SequentialValidator (NEW)
      └─> fetch_sequential_gex(date, lookback=5)  # 5 days
      └─> SequentialPromptBuilder (NEW)  # Build trajectory prompt
      └─> LLM prompt with 5-day sequence
```

---

## Implementation Components

### 1. Data Retrieval Layer

**Create**: `src/data_sources/sequential_gex_fetcher.py`

```python
class SequentialGEXFetcher:
    """Fetch 5-day GEX sequences for temporal analysis."""

    def __init__(self, cache_manager: UnifiedCacheManager):
        self.cache = cache_manager
        self.gex_cache = cache_manager.gex_cache

    def get_sequential_gex(
        self,
        symbol: str,
        end_date: str,
        lookback_days: int = 5
    ) -> List[Dict]:
        """
        Fetch GEX data for [T-4, T-3, T-2, T-1, T+0].

        Args:
            symbol: Trading symbol (SPY)
            end_date: Final date in sequence (Day T+0)
            lookback_days: Number of historical days (default 5)

        Returns:
            List of GEX summaries, one per day:
            [
                {'date': 'T-4', 'net_gex': -2.1, 'flip_point': 520, ...},
                {'date': 'T-3', 'net_gex': -3.2, 'flip_point': 518, ...},
                ...
            ]
        """
        # Get 5 trading days before end_date
        dates = self._get_trading_days_before(end_date, lookback_days)

        # Fetch GEX summary for each day
        gex_sequence = []
        for date in dates:
            gex_summary = self.gex_cache.get_gex_summary(symbol, date)
            if gex_summary:
                gex_sequence.append(gex_summary)
            else:
                # Data gap - log and skip or return partial sequence
                logger.warning(f"Missing GEX data for {symbol} on {date}")

        return gex_sequence

    def _get_trading_days_before(
        self,
        end_date: str,
        n_days: int
    ) -> List[str]:
        """
        Get N trading days before end_date (business days - holidays).

        Uses existing date_utils.subtract_business_days() or similar.
        Returns: ['2024-01-05', '2024-01-08', ..., '2024-01-15']
        """
        # Implementation using pandas or existing date utilities
        pass
```

**Key Methods**:

- `get_sequential_gex()` - Main entry point
- `_get_trading_days_before()` - Business day calculation
- `_detect_trajectory_type()` - Classify sequence (accumulation, relief, etc.)

---

### 2. Prompt Builder Layer

**Create**: `src/llm/sequential_prompt_builder.py`

```python
class SequentialPromptBuilder:
    """Build LLM prompts with 5-day GEX trajectories."""

    def build_sequential_prompt(
        self,
        gex_sequence: List[Dict],
        obfuscate: bool = True
    ) -> str:
        """
        Generate prompt showing GEX trajectory over 5 days.

        Example Output (obfuscated):
        ---
        Analyze the following 5-day gamma exposure trajectory for INDEX_1:

        Day T-4: Net GEX = -$2.1B, Flip Point = $520
        Day T-3: Net GEX = -$3.2B, Flip Point = $518
        Day T-2: Net GEX = -$4.1B, Flip Point = $515
        Day T-1: Net GEX = -$4.8B, Flip Point = $513
        Day T+0: Net GEX = -$5.2B, Flip Point = $510

        Trajectory Type: Gamma Accumulation (escalating negative exposure)

        Question: What constraints does this trajectory place on dealers?
        Predict the likely outcome for Day T+1.
        ---
        """
        # Build trajectory narrative
        trajectory_type = self._classify_trajectory(gex_sequence)
        trajectory_narrative = self._build_narrative(gex_sequence)

        # Obfuscate dates/tickers if requested
        if obfuscate:
            trajectory_narrative = self._obfuscate(trajectory_narrative)

        # Construct prompt
        prompt = f"""
        Analyze the following 5-day gamma exposure trajectory:

        {trajectory_narrative}

        Trajectory Classification: {trajectory_type}

        Based on dealer hedging constraints:
        1. What forced actions must dealers take?
        2. What is the likely outcome for Day T+1?
        3. Confidence level (0-100)?
        """

        return prompt

    def _classify_trajectory(self, gex_sequence: List[Dict]) -> str:
        """
        Classify trajectory type based on GEX changes.

        Returns:
        - "Gamma Accumulation" if |GEX| increasing
        - "Gamma Relief" if |GEX| decreasing
        - "Gamma Reversal" if sign flips
        - "Persistent Constraint" if stable
        """
        pass
```

**Key Methods**:

- `build_sequential_prompt()` - Main prompt construction
- `_classify_trajectory()` - Detect pattern type (accumulation/relief/reversal/persistent)
- `_build_narrative()` - Format 5-day sequence for LLM
- `_obfuscate()` - Apply date/ticker obfuscation

---

### 3. Validation Script Layer

**Create**: `scripts/validation/validate_sequential_patterns.py`

```python
class SequentialPatternValidator:
    """
    Validate sequential GEX patterns with 5-day lookback.
    Extends PatternTaxonomyValidator with temporal analysis.
    """

    def __init__(self, symbol: str = "SPY"):
        self.symbol = symbol
        self.cache = UnifiedCacheManager()
        self.sequential_fetcher = SequentialGEXFetcher(self.cache)
        self.sequential_prompt_builder = SequentialPromptBuilder()
        self.agent = MarketMechanicsAgent(symbol=symbol)

        # Reuse existing components
        self.obfuscator = DataObfuscator()
        self.outcome_calculator = OutcomeCalculator(self.cache)

    def validate_sequential(
        self,
        start_date: str,
        end_date: str,
        lookback_days: int = 5
    ) -> Dict:
        """
        Run sequential validation across date range.

        Args:
            start_date: First test date (2024-01-08, after 5-day warmup)
            end_date: Last test date (2024-12-31)
            lookback_days: Sequence length (default 5)

        Returns:
            Validation results with sequential metrics
        """
        # Get test dates (skip first 4 days of each quarter for warmup)
        test_dates = self._get_test_dates(start_date, end_date, lookback_days)

        logger.info(f"Testing {len(test_dates)} sequential windows")

        results = []
        for date in test_dates:
            # Fetch 5-day GEX sequence ending at date
            gex_sequence = self.sequential_fetcher.get_sequential_gex(
                self.symbol,
                date,
                lookback_days
            )

            # Skip if incomplete sequence
            if len(gex_sequence) < lookback_days:
                logger.warning(f"Incomplete sequence for {date}, skipping")
                continue

            # Build sequential prompt
            prompt = self.sequential_prompt_builder.build_sequential_prompt(
                gex_sequence,
                obfuscate=True  # Always obfuscate for validation
            )

            # Get LLM prediction
            llm_response = self.agent.llm.analyze_mechanics(prompt)

            # Calculate actual outcome (T+1 forward return)
            outcome = self.outcome_calculator.calculate_outcomes(
                self.symbol,
                date
            )

            # Compare prediction vs reality
            result = self._evaluate_prediction(llm_response, outcome)
            results.append(result)

        # Aggregate results
        return self._aggregate_results(results)

    def _get_test_dates(
        self,
        start_date: str,
        end_date: str,
        warmup_days: int
    ) -> List[str]:
        """
        Get test dates with warmup period.

        For Q1 2024:
        - Full range: 2024-01-02 to 2024-03-29 (53 days)
        - Warmup: 2024-01-02 to 2024-01-05 (4 days)
        - Test range: 2024-01-08 to 2024-03-29 (49 days)

        Returns: ['2024-01-08', '2024-01-09', ...]
        """
        pass
```

**Usage**:

```bash
# Run sequential validation for Q1 2024
python scripts/validation/validate_sequential_patterns.py \
  --symbol SPY \
  --start-date 2024-01-08 \
  --end-date 2024-03-29 \
  --lookback 5 \
  --output reports/validation/sequential/sequential_SPY_2024Q1.yaml
```

---

### 4. Comparative Analysis Layer

**Create**: `scripts/analysis/compare_single_vs_sequential.py`

```python
def compare_validation_approaches():
    """
    Compare single-day (Paper #1) vs sequential (Paper #2) results.

    Metrics:
    - Detection rate (single vs sequential)
    - Predictive accuracy (single vs sequential)
    - Confidence levels (single vs sequential)
    - False positive rate (single vs sequential)
    - Pattern-specific improvements
    """

    # Load Paper #1 results (baseline)
    single_day_results = load_paper1_results()

    # Load Paper #2 results (test)
    sequential_results = load_sequential_results()

    # Compare metrics
    comparison = {
        'detection_rate': {
            'single_day': single_day_results['detection_pct'],
            'sequential': sequential_results['detection_pct'],
            'delta': sequential_results['detection_pct'] - single_day_results['detection_pct']
        },
        'accuracy': {
            'single_day': single_day_results['accuracy_pct'],
            'sequential': sequential_results['accuracy_pct'],
            'delta': sequential_results['accuracy_pct'] - single_day_results['accuracy_pct']
        },
        ...
    }

    # Generate comparison report
    generate_comparison_report(comparison)
    generate_comparison_figures(comparison)
```

---

## Implementation Timeline (5 Days)

### Day 1: Data Layer (4-6 hours)

- [ ] Create `SequentialGEXFetcher` class
- [ ] Implement `get_sequential_gex()` method
- [ ] Implement `_get_trading_days_before()` helper
- [ ] Unit tests for data retrieval
- [ ] Test on Q1 2024 sample dates

**Deliverable**: Working data fetcher returning 5-day GEX sequences

---

### Day 2: Prompt Layer (4-6 hours)

- [ ] Create `SequentialPromptBuilder` class
- [ ] Implement `build_sequential_prompt()` method
- [ ] Implement `_classify_trajectory()` method
- [ ] Add obfuscation logic (reuse existing `DataObfuscator`)
- [ ] Generate sample prompts for inspection

**Deliverable**: Prompt builder generating sequential LLM prompts

---

### Day 3-4: Validation Layer (12-16 hours)

- [ ] Create `validate_sequential_patterns.py` script
- [ ] Implement `SequentialPatternValidator` class
- [ ] Add CLI argument parsing (start/end dates, lookback, output path)
- [ ] Run validation on Q1 2024 (49 5-day windows)
- [ ] Run validation on Q3 2024 (60 5-day windows)
- [ ] Run validation on Q4 2024 (60 5-day windows)
- [ ] Generate YAML output files

**Deliverable**: Complete validation results for 169 5-day windows

---

### Day 5: Analysis Layer (6-8 hours)

- [ ] Create `compare_single_vs_sequential.py` script
- [ ] Load Paper #1 baseline results
- [ ] Load Paper #2 sequential results
- [ ] Calculate delta metrics (detection, accuracy, confidence)
- [ ] Generate comparison tables (LaTeX)
- [ ] Generate comparison figures (matplotlib)
- [ ] Write interpretation summary

**Deliverable**: Comparative analysis determining if sequential adds value

---

## Expected Outputs

### YAML Validation Files

```
reports/validation/sequential/
├── sequential_SPY_2024Q1.yaml  # 49 windows (Jan 8 - Mar 29)
├── sequential_SPY_2024Q3.yaml  # 60 windows (Jul 5 - Sep 30)
└── sequential_SPY_2024Q4.yaml  # 60 windows (Oct 3 - Dec 31)
```

### Comparison Tables (LaTeX)

```
docs/papers/paper2/tables/
├── table1_detection_comparison.tex      # Single vs Sequential detection
├── table2_accuracy_comparison.tex       # Single vs Sequential accuracy
└── table3_trajectory_performance.tex    # Performance by trajectory type
```

### Comparison Figures

```
docs/papers/paper2/figures/
├── fig1_detection_improvement.png       # Bar chart: Single vs Sequential
├── fig2_accuracy_by_trajectory.png      # Line chart: 4 trajectory types
└── fig3_confidence_distribution.png     # Histogram: Confidence levels
```

---

## Key Design Decisions

### 1. Reuse Existing Infrastructure

- **UnifiedCacheManager** - Already has GEX data cached
- **GEXCacheManager** - `get_gex_summary()` works for single days
- **DataObfuscator** - Reuse for date/ticker obfuscation
- **OutcomeCalculator** - Reuse for forward returns
- **MarketMechanicsAgent** - Reuse LLM integration

### 2. Minimal Code Duplication

- Don't fork `validate_pattern_taxonomy.py`
- Create new `SequentialValidator` that inherits/delegates
- Share outcome calculation logic (Issue #80)
- Share obfuscation logic (Issue #81)

### 3. Consistent Output Format

- Use same YAML structure as Paper #1 (add `trajectory_type` field)
- Use same metrics (detection_rate_pct, accuracy_pct, net_alpha_pct)
- Enable direct comparison without format conversion

### 4. Warmup Period Handling

- Q1: Skip first 4 days (Jan 2-5), test starts Jan 8
- Q3: Skip first 4 days (Jul 1-3), test starts Jul 5
- Q4: Skip first 4 days (Oct 1-4), test starts Oct 7
- Total test windows: 169 (down from 181 single-day tests)

---

## Testing Strategy

### Unit Tests

- `test_sequential_gex_fetcher.py` - Data retrieval
- `test_sequential_prompt_builder.py` - Prompt generation
- `test_trajectory_classification.py` - Pattern detection

### Integration Tests

- Run on 5 sample dates from Q1 2024
- Verify GEX sequence matches manual inspection
- Verify obfuscation working (no real dates in prompts)
- Verify outcomes calculated correctly

### Full Validation

- Run on complete Q1 2024 (49 windows)
- Compare detection rate vs Paper #1 Q1 baseline (100%)
- Verify YAML output format matches Paper #1 structure

---

## Risk Mitigation

### Risk 1: Data Gaps in Sequences

**Problem**: Missing GEX data for 1+ days in 5-day sequence
**Mitigation**: Skip incomplete sequences, log data continuity report

### Risk 2: LLM Prompt Length

**Problem**: 5-day prompts may be too long for context window
**Mitigation**: Test prompt length, summarize if needed (unlikely with 5 days)

### Risk 3: No Performance Improvement

**Problem**: Sequential shows no accuracy gain over single-day
**Mitigation**: Document as negative result, fold into Paper #3 discussion

### Risk 4: Trajectory Classification Ambiguity

**Problem**: Some sequences don't fit 4 trajectory types cleanly
**Mitigation**: Add "Mixed" category, analyze separately

---

## Next Steps (Immediate)

1. ✅ Review this implementation plan with user
2. ⏳ Create `SequentialGEXFetcher` stub (Day 1)
3. ⏳ Create `SequentialPromptBuilder` stub (Day 2)
4. ⏳ Create `validate_sequential_patterns.py` stub (Day 3)
5. ⏳ Run pilot test on 5 dates (Day 3)
6. ⏳ Full Q1 validation (Day 4)
7. ⏳ Comparative analysis (Day 5)

---

## Questions for User

1. **Trajectory Types**: Are the 4 types sufficient (accumulation, relief, reversal, persistent)? Or add "mixed"?
2. **Warmup Period**: Is 4 days sufficient for meaningful trajectory? Or test 3-day and 7-day?
3. **Obfuscation**: Use same approach as Paper #1 (Day T-4, T-3, etc.)?
4. **Output Format**: Keep YAML same as Paper #1 with added `trajectory_type` field?
5. **Target Quarters**: Test Q1+Q3+Q4 (match Paper #1) or add Q2 if data available?

---

**Status**: Ready for implementation after user review
