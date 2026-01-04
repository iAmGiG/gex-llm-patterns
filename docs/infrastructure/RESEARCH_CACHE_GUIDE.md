# ResearchCache Usage Guide

## Overview

ResearchCache provides a structured way to store and query:

- LLM detection results with chain-of-thought
- Validation outcomes
- Experiment runs with git versioning
- Pattern library versions

## Quick Start

```python
from src.cache.research_cache import ResearchCache

# Initialize
cache = ResearchCache()

# Store a detection
detection_id = cache.store_detection(
    symbol="SPY",
    trading_date="2024-01-15",
    pattern_id="regime_30day",
    model_name="o4-mini",
    confidence_score=85.0,
    chain_of_thought="Analysis shows...",
    detected=True
)

# Query detections
detections = cache.get_detections(
    symbol="SPY",
    start_date="2024-01-01",
    end_date="2024-12-31",
    pattern_ids=["regime_30day"]
)

# Record experiment
cache.record_experiment_run(
    run_id="my_experiment_v1",
    description="Testing new regime criteria",
    config={"threshold": 70, "window": 30}
)
```

## Common Queries

### Get Detection Statistics by Year

```python
from src.cache.research_cache_queries import get_detection_stats_by_year

stats = get_detection_stats_by_year()
for year, data in stats.items():
    print(f"{year}: {data['detection_rate']:.1f}% ({data['detected']}/{data['total']})")
```

### Compare High vs Low Confidence

```python
from src.cache.research_cache_queries import compare_detections_by_confidence

comparison = compare_detections_by_confidence(threshold=80.0)
print(f"Above 80%: {comparison['above']['rate']:.1f}%")
print(f"Below 80%: {comparison['below']['rate']:.1f}%")
```

### Get Experiment History

```python
from src.cache.research_cache_queries import get_experiment_history

# All Paper 2 experiments
experiments = get_experiment_history("paper2")
for exp in experiments:
    print(f"{exp['run_id']}: {exp['description']}")
```

## Integration with YAML Reports

ResearchCache complements existing YAML reports:

```python
import yaml
from src.cache.research_cache import ResearchCache

cache = ResearchCache()

# Store in ResearchCache (queryable)
detection_id = cache.store_detection(...)

# Also save as YAML (human-readable)
with open('reports/validation/result.yaml', 'w') as f:
    yaml.dump(detection_data, f)
```

## Database Schema

### llm_detections

- Stores pattern detection results
- Links to validation_results via foreign key
- Includes chain-of-thought reasoning

### experiment_runs

- Tracks all experiment runs
- Stores git commit hash for reproducibility
- Links to detections via metadata

### validation_results

- Stores outcome verification (T+1, T+3, T+5 returns)
- Links to detections

## Best Practices

1. **Always record experiment runs** before generating detections
2. **Use git commit hashes** for reproducibility
3. **Store chain-of-thought** for reviewer transparency
4. **Keep YAML backups** for human review
5. **Query by year/pattern** for performance

## Troubleshooting

**Database locked?**

- ResearchCache uses threading.Lock() for safety
- Wait a few seconds and retry

**Missing detections?**

- Check date format: "YYYY-MM-DD"
- Verify pattern_id matches exactly
- Use cache.get_detections() with no filters to see all

## For Papers 3-5

ResearchCache is designed to scale across all papers:

- Paper 3: Multi-symbol detections
- Paper 4: Graph neural network results
- Paper 5: Real-time detection tracking

See `src/cache/research_cache.py` for full API documentation.
