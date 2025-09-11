"""
Trading Rules Generator
Based on statistical pattern analysis, generates concrete trading rules and LLM prompts.
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime


class TradingRulesGenerator:
    """Generates trading rules and LLM prompts based on pattern analysis."""
    
    def __init__(self, db_path):
        self.db_path = db_path
        self.pattern_stats = {}
        self.trading_rules = []
        
    def analyze_patterns_for_rules(self) :
        """Analyze patterns and extract trading rules."""
        
        conn = sqlite3.connect(self.db_path)
        
        # Get comprehensive pattern data
        query = '''
            SELECT 
                p.pattern_name,
                p.confidence,
                p.fed_weight,
                p.date,
                d1.spot_price as entry_price,
                d1.gex_regime,
                f.is_fomc_week,
                f.days_to_fomc,
                f.market_stress_level,
                d2.spot_price as exit_price,
                (d2.spot_price - d1.spot_price) / d1.spot_price * 100 as return_pct,
                CASE WHEN d2.spot_price > d1.spot_price THEN 1 ELSE 0 END as is_winner
            FROM pattern_detections p
            JOIN daily_gex_metrics d1 ON p.symbol = d1.symbol AND p.date = d1.date
            LEFT JOIN fed_context f ON p.date = f.date
            LEFT JOIN daily_gex_metrics d2 
                ON d2.symbol = 'SPY'
                AND date(d2.date) = date(p.date, '+1 day')
            WHERE p.symbol = 'SPY' AND d2.spot_price IS NOT NULL
        '''
        
        data = pd.read_sql(query, conn)
        conn.close()
        
        # Analyze by pattern
        pattern_groups = data.groupby('pattern_name')
        
        for pattern_name, group in pattern_groups:
            returns = group['return_pct'].values
            wins = group['is_winner'].values
            
            stats = {
                'pattern': pattern_name,
                'sample_size': len(returns),
                'win_rate': np.mean(wins) * 100,
                'avg_return': np.mean(returns),
                'std_return': np.std(returns, ddof=1) if len(returns) > 1 else 0,
                'max_return': np.max(returns),
                'min_return': np.min(returns),
                'avg_confidence': np.mean(group['confidence']),
                'regime': group['gex_regime'].iloc[0],  # Most common regime
                'returns_list': returns.tolist()
            }
            
            self.pattern_stats[pattern_name] = stats
            
            # Generate trading rule if pattern is profitable
            if stats['win_rate'] >= 55.0:  # 55%+ win rate threshold
                rule = self._generate_trading_rule(stats)
                self.trading_rules.append(rule)
        
        return self.pattern_stats
    
    def _generate_trading_rule(self, stats: Dict) :
        """Generate a trading rule from pattern statistics."""
        
        rule = {
            'pattern': stats['pattern'].upper(),
            'condition': f"When {stats['pattern'].upper()} pattern detected",
            'win_rate': stats['win_rate'],
            'expected_return': stats['avg_return'],
            'confidence_threshold': max(stats['avg_confidence'] - 5, 80),  # Slightly below avg
            'regime_context': stats['regime'],
            'risk_note': f"Max observed loss: {stats['min_return']:.2f}%",
            'sample_basis': f"{stats['sample_size']} historical trades",
            'rule_strength': self._calculate_rule_strength(stats)
        }
        
        return rule
    
    def _calculate_rule_strength(self, stats: Dict) -> str:
        """Calculate rule strength based on statistics."""
        
        win_rate = stats['win_rate']
        sample_size = stats['sample_size']
        
        if win_rate >= 70 and sample_size >= 10:
            return "HIGH"
        elif win_rate >= 60 and sample_size >= 5:
            return "MEDIUM"
        elif win_rate >= 55 and sample_size >= 3:
            return "LOW"
        else:
            return "INSUFFICIENT_DATA"
    
    def generate_llm_prompt(self, date, gex_data: Dict, patterns: List[Dict]) -> str:
        """
        Generate context-aware LLM prompt based on statistical findings.
        
        Args:
            date: Trading date
            gex_data: Current GEX metrics
            patterns: Detected patterns for the date
            
        Returns:
            Formatted LLM prompt with statistical context
        """
        
        prompt_lines = [
            f"Market Analysis for {date}",
            "=" * 50,
            "",
            "GAMMA EXPOSURE ANALYSIS:",
            f"- Net GEX: ${gex_data.get('net_gex', 0):,.0f}",
            f"- GEX Regime: {gex_data.get('gex_regime', 'Unknown')}",
            f"- Flip Point: ${gex_data.get('flip_point', 0):.2f}",
            f"- Current Price: ${gex_data.get('spot_price', 0):.2f}",
            "",
            "PATTERN DETECTION:",
        ]
        
        if patterns:
            for pattern in patterns:
                pattern_name = pattern.get('pattern_name', 'unknown')
                confidence = pattern.get('confidence', 0)
                
                prompt_lines.append(f"- {pattern_name.upper()}: {confidence:.0f}% confidence")
                
                # Add statistical context if we have it
                if pattern_name in self.pattern_stats:
                    stats = self.pattern_stats[pattern_name]
                    prompt_lines.append(f"  Historical Performance: {stats['win_rate']:.1f}% win rate ({stats['sample_size']} samples)")
                    prompt_lines.append(f"  Expected Return: {stats['avg_return']:.2f}%")
        else:
            prompt_lines.append("- No high-confidence patterns detected")
        
        prompt_lines.extend([
            "",
            "STATISTICAL TRADING RULES:",
        ])
        
        # Add relevant trading rules
        applicable_rules = []
        for rule in self.trading_rules:
            for pattern in patterns:
                if pattern.get('pattern_name', '').upper() == rule['pattern']:
                    if pattern.get('confidence', 0) >= rule['confidence_threshold']:
                        applicable_rules.append(rule)
        
        if applicable_rules:
            for rule in applicable_rules:
                prompt_lines.extend([
                    f"✅ {rule['pattern']} RULE ACTIVATED:",
                    f"  - Win Rate: {rule['win_rate']:.1f}% (based on {rule['sample_basis']})",
                    f"  - Expected Return: {rule['expected_return']:.2f}%",
                    f"  - Confidence Threshold: {rule['confidence_threshold']:.0f}%+",
                    f"  - Rule Strength: {rule['rule_strength']}",
                    f"  - Risk Warning: {rule['risk_note']}",
                    ""
                ])
        else:
            prompt_lines.append("- No statistical rules triggered for current patterns")
        
        prompt_lines.extend([
            "",
            "RECOMMENDATION REQUEST:",
            "Based on the GEX analysis, detected patterns, and historical statistics:",
            "1. Provide directional bias (bullish/bearish/neutral)",
            "2. Suggest position sizing based on pattern confidence",
            "3. Define risk management parameters",
            "4. Specify time horizon for the trade",
            "",
            "Focus on patterns with statistical significance and consider the GEX regime context."
        ])
        
        return "\n".join(prompt_lines)
    
    def generate_rules_report(self) -> str:
        """Generate a comprehensive trading rules report."""
        
        if not hasattr(self, 'pattern_stats') or not self.pattern_stats:
            self.analyze_patterns_for_rules()
        
        report_lines = [
            "STATISTICAL TRADING RULES REPORT",
            "=" * 60,
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Database: {self.db_path}",
            "",
            "PATTERN STATISTICS SUMMARY:",
            "-" * 40,
        ]
        
        for pattern_name, stats in self.pattern_stats.items():
            report_lines.extend([
                f"{pattern_name.upper()}:",
                f"  Sample Size: {stats['sample_size']} trades",
                f"  Win Rate: {stats['win_rate']:.1f}%",
                f"  Average Return: {stats['avg_return']:.3f}%",
                f"  Return Range: {stats['min_return']:.2f}% to {stats['max_return']:.2f}%",
                f"  Average Confidence: {stats['avg_confidence']:.1f}%",
                f"  Primary Regime: {stats['regime']}",
                ""
            ])
        
        report_lines.extend([
            "ACTIVE TRADING RULES:",
            "-" * 40,
        ])
        
        if self.trading_rules:
            for rule in self.trading_rules:
                report_lines.extend([
                    f"RULE: {rule['pattern']}",
                    f"  Condition: {rule['condition']}",
                    f"  Expected Win Rate: {rule['win_rate']:.1f}%",
                    f"  Expected Return: {rule['expected_return']:.2f}%",
                    f"  Min Confidence: {rule['confidence_threshold']:.0f}%",
                    f"  Strength: {rule['rule_strength']}",
                    f"  Risk: {rule['risk_note']}",
                    ""
                ])
        else:
            report_lines.extend([
                "No patterns currently meet trading rule criteria.",
                "Minimum requirements: 55%+ win rate, 3+ samples",
                ""
            ])
        
        report_lines.extend([
            "IMPLEMENTATION NOTES:",
            "-" * 40,
            "1. Rules are based on next-day return analysis",
            "2. Historical performance may not predict future results",
            "3. Consider position sizing based on rule strength",
            "4. Monitor rule performance and adjust thresholds as needed",
            "5. Expand historical database for more robust statistics",
            "",
            "NEXT STEPS:",
            "- Collect more historical data for statistical significance",
            "- Add exit strategy rules based on pattern decay",
            "- Implement regime-specific rule variations",
            "- Add Fed context timing rules (FOMC proximity)",
        ])
        
        return "\n".join(report_lines)


def test_trading_rules_generator():
    """Test the trading rules generator with current data."""
    
    db_path = '.cache/test_gex_pipeline.db'
    generator = TradingRulesGenerator(db_path)
    
    print("TESTING TRADING RULES GENERATOR")
    print("=" * 60)
    
    # Analyze patterns
    stats = generator.analyze_patterns_for_rules()
    
    print("Pattern Statistics:")
    for pattern, stat in stats.items():
        print(f"  {pattern}: {stat['win_rate']:.1f}% win rate, {stat['sample_size']} samples")
    
    print(f"\nTrading Rules Generated: {len(generator.trading_rules)}")
    
    # Generate sample LLM prompt
    print("\nSample LLM Prompt:")
    print("-" * 30)
    
    sample_gex = {
        'net_gex': -5000000,
        'gex_regime': 'NEGATIVE_GAMMA_LOW', 
        'flip_point': 450.0,
        'spot_price': 455.0
    }
    
    sample_patterns = [{
        'pattern_name': 'gamma_trap',
        'confidence': 90.0
    }]
    
    prompt = generator.generate_llm_prompt('2024-01-15', sample_gex, sample_patterns)
    print(prompt)
    
    print("\n" + "=" * 60)
    print("Full Rules Report:")
    print(generator.generate_rules_report())
    
    return generator


if __name__ == "__main__":
    test_trading_rules_generator()