# Reports Directory Structure

This directory contains all analysis outputs, calculation results, and generated reports.
**IMPORTANT**: This is separate from `.cache/` which only stores raw input data.

## Directory Structure

```
reports/
├── gex_calculations/          # GEX calculation results and metrics
├── pattern_analysis/          # Pattern detection and LLM analysis outputs
├── data_quality/             # Data validation and quality reports
├── agent_outputs/            # Multi-agent conversation logs and results
├── demo_results/             # Testing and demo outputs (safe to delete)
└── README.md                 # This file
```

## Usage Guidelines

### ✅ **Store Here**
- GEX calculation results (JSON/CSV)
- Pattern analysis reports
- Agent conversation logs
- Data quality assessments
- Generated charts and visualizations
- Research findings and summaries
- Demo and testing outputs

### ❌ **Don't Store Here**
- Raw market data (belongs in `.cache/`)
- Original options chains (belongs in `.cache/`)
- Input datasets (belongs in `samples/` or `.cache/`)
- Source code or configuration files

## File Naming Conventions

### GEX Calculations
```
gex_calculations/
├── SPY_2024-01-15_gex_results.json
├── SPX_2024-01-15_gex_results.json
└── daily_gex_summary_2024-01.csv
```

### Pattern Analysis
```
pattern_analysis/
├── short_put_arbitrage_2024-01-15.json
├── pattern_detection_log_2024-01.txt
└── llm_analysis_SPY_jan2024.md
```

### Agent Outputs
```
agent_outputs/
├── multi_agent_conversation_20240115_143022.json
├── data_retrieval_log_SPY_jan2024.txt
└── gex_calculation_session_20240115.json
```

### Demo Results
```
demo_results/
├── test_gex_calculation_20240115.json
├── sample_pattern_analysis.json
└── agent_workflow_demo.txt
```

## File Formats

### Recommended Formats
- **JSON**: Structured data, API responses, calculation results
- **CSV**: Tabular data, time series, summary statistics
- **Markdown**: Analysis reports, documentation, summaries
- **TXT**: Logs, conversation transcripts, debugging output

### Timestamp Format
Use ISO format for timestamps: `YYYYMMDD_HHMMSS`
- Example: `20240115_143022` for 2024-01-15 14:30:22

## Cleanup Policy

### Keep Indefinitely
- `gex_calculations/` - Research results
- `pattern_analysis/` - Analysis outputs
- `data_quality/` - Quality assessments

### Regular Cleanup (Monthly)
- `demo_results/` - Testing outputs
- Old files in `agent_outputs/` (>30 days)

### Git Tracking
- Include report structure in git
- **Exclude large data files** with .gitignore
- Include sample reports as examples

## Integration with Tools

Tools should save outputs using this pattern:
```python
import json
from datetime import datetime
from pathlib import Path

def save_gex_results(symbol, results):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{symbol}_{timestamp}_gex_results.json"
    
    reports_dir = Path("reports/gex_calculations")
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    with open(reports_dir / filename, 'w') as f:
        json.dump(results, f, indent=2)
```

This separation ensures:
- Clean cache containing only input data
- Organized research outputs
- Easy cleanup of temporary results
- Clear distinction between data and analysis