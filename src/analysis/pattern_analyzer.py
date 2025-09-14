"""
Simple Pattern Analyzer
Working implementation of pattern probability analysis without complex imports.
"""

import sqlite3
import pandas as pd


class SimplePatternAnalyzer:
    """
    Simple pattern analyzer for immediate use.
    Analyzes pattern outcomes and identifies high conviction setups.
    """

    def __init__(self, db_path):
        """Initialize with database path."""
        self.db_path = db_path

    def analyze_patterns(self, symbol: str = 'SPY', min_samples: int = 2):
        """
        Analyze all patterns for the given symbol.

        Args:
            symbol: Symbol to analyze (default: SPY)
            min_samples: Minimum samples required for analysis

        Returns:
            Dictionary with pattern analysis results
        """
        conn = sqlite3.connect(self.db_path)

        # Core pattern analysis query
        query = '''
            WITH pattern_days AS (
                SELECT 
                    p.symbol,
                    p.date as pattern_date,
                    p.pattern_name,
                    p.confidence,
                    d1.spot_price as day0_price
                FROM pattern_detections p
                JOIN daily_gex_metrics d1 
                    ON p.symbol = d1.symbol AND p.date = d1.date
                WHERE p.symbol = ?
            ),
            returns AS (
                SELECT 
                    pd.*,
                    d2.spot_price as day1_price,
                    (d2.spot_price - pd.day0_price) / pd.day0_price * 100 as return_pct
                FROM pattern_days pd
                LEFT JOIN daily_gex_metrics d2 
                    ON pd.symbol = d2.symbol 
                    AND date(d2.date) = date(pd.pattern_date, "+1 day")
                WHERE d2.spot_price IS NOT NULL
            )
            SELECT 
                pattern_name,
                COUNT(*) as sample_size,
                AVG(return_pct) as avg_return,
                SUM(CASE WHEN return_pct > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as win_rate,
                AVG(confidence) as avg_confidence,
                MAX(return_pct) as max_return,
                MIN(return_pct) as min_return,
                (SUM(CASE WHEN return_pct > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) / 50.0 as win_rate_score,
                ABS(AVG(return_pct)) as avg_return_magnitude
            FROM returns
            GROUP BY pattern_name
            HAVING COUNT(*) >= ?
            ORDER BY win_rate DESC, avg_return DESC
        '''

        results_df = pd.read_sql(query, conn, params=[symbol, min_samples])
        conn.close()

        # Convert to dictionary format
        analysis = {
            'symbol': symbol,
            'total_patterns': len(results_df),
            'patterns': {}
        }

        for _, row in results_df.iterrows():
            pattern_name = row['pattern_name']
            analysis['patterns'][pattern_name] = {
                'sample_size': int(row['sample_size']),
                # Convert to decimal
                'win_rate': float(row['win_rate']) / 100.0,
                'avg_return': float(row['avg_return']),
                'avg_confidence': float(row['avg_confidence']),
                'max_return': float(row['max_return']),
                'min_return': float(row['min_return']),
                'return_magnitude': float(row['avg_return_magnitude'])
            }

        return analysis

    def get_high_conviction_patterns(self, symbol: str = 'SPY',
                                     min_win_rate: float = 0.6,
                                     min_samples: int = 3):
        """
        Identify high conviction trading setups.

        Args:
            symbol: Symbol to analyze
            min_win_rate: Minimum win rate (0.6 = 60%)
            min_samples: Minimum sample size

        Returns:
            List of high conviction patterns
        """
        analysis = self.analyze_patterns(symbol, min_samples)

        high_conviction = []
        for pattern_name, stats in analysis['patterns'].items():
            if stats['win_rate'] >= min_win_rate and stats['sample_size'] >= min_samples:
                high_conviction.append({
                    'pattern': pattern_name,
                    'win_rate': stats['win_rate'],
                    'avg_return': stats['avg_return'],
                    'sample_size': stats['sample_size'],
                    'confidence': stats['avg_confidence'],
                    # Boost for more samples
                    'conviction_score': stats['win_rate'] * (stats['sample_size'] / 10.0)
                })

        # Sort by conviction score
        high_conviction.sort(key=lambda x: x['conviction_score'], reverse=True)
        return high_conviction

    def generate_pattern_report(self, symbol: str = 'SPY') -> str:
        """Generate a comprehensive pattern analysis report."""

        analysis = self.analyze_patterns(symbol)
        high_conviction = self.get_high_conviction_patterns(
            symbol, min_win_rate=0.5)

        report = f"""
PATTERN PROBABILITY ANALYSIS REPORT
Symbol: {symbol}
Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}
{'=' * 60}

PATTERN SUMMARY:
Total patterns analyzed: {analysis['total_patterns']}

INDIVIDUAL PATTERN PERFORMANCE:
"""

        for pattern_name, stats in analysis['patterns'].items():
            report += f"""
{pattern_name.upper()}:
  Sample size: {stats['sample_size']} occurrences
  Win rate: {stats['win_rate']:.1%}
  Average return: {stats['avg_return']:.2f}%
  Return range: {stats['min_return']:.2f}% to {stats['max_return']:.2f}%
  Average confidence: {stats['avg_confidence']:.1f}%
"""

        report += f"""
HIGH CONVICTION SETUPS (≥50% win rate):
"""

        if high_conviction:
            for setup in high_conviction:
                report += f"""
  {setup['pattern'].upper()}:
    Win rate: {setup['win_rate']:.1%}
    Average return: {setup['avg_return']:.2f}%
    Sample size: {setup['sample_size']} trades
    Conviction score: {setup['conviction_score']:.2f}
"""
        else:
            report += "  No patterns meet high conviction criteria\n"

        report += f"""
STATISTICAL NOTES:
- Minimum sample size for analysis: 2 occurrences
- High conviction threshold: ≥50% win rate
- Current data provides {sum(stats['sample_size'] for stats in analysis['patterns'].values())} total pattern-outcome pairs
- Need >10 samples per pattern for full statistical significance

NEXT STEPS:
1. Expand historical database for more robust statistics
2. Implement Fed context filtering for pattern refinement
3. Add regime-based pattern analysis
4. Create LLM prompts based on pattern insights
"""

        return report
