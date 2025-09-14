#!/usr/bin/env python3
"""
Demo: Pattern Probability Mapper (Issue #37)

Demonstrates the complete Pattern-Outcome Probability Engine:
1. PatternProbabilityMapper - analyzes historical pattern-outcome relationships
2. StatisticalValidator - provides statistical significance testing
3. ConfidenceScorer - generates calibrated confidence scores
4. PatternEngineIntegration - unified analysis workflow

This showcases exactly what main chat requested for Issue #37.
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import json

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.analysis.pattern_probability_mapper import PatternProbabilityMapper
from src.analysis.statistical_validator import StatisticalValidator
from src.analysis.confidence_scorer import ConfidenceScorer
from src.analysis.pattern_engine_integration import PatternEngineIntegration
from src.gex.calculator import GEXCalculator
from src.data_sources.fed_data_integration import FedDataIntegration


def create_mock_historical_data(n_days: int = 500) -> pd.DataFrame:
    """Create realistic mock historical data for demo."""
    print(f"📊 Creating mock historical dataset ({n_days} days)")
    
    # Generate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=n_days)
    dates = pd.date_range(start=start_date, end=end_date, freq='D')
    
    np.random.seed(42)  # For reproducible demo
    
    # Generate realistic price data with some trends
    base_price = 450.0
    returns = np.random.normal(0.0005, 0.015, len(dates))  # ~0.05% daily drift, 1.5% vol
    
    # Add some volatility clustering
    vol_regime = np.random.choice([0.8, 1.0, 1.5], len(dates), p=[0.6, 0.3, 0.1])
    returns = returns * vol_regime
    
    prices = [base_price]
    for ret in returns[1:]:
        prices.append(prices[-1] * (1 + ret))
    
    # Create DataFrame
    df = pd.DataFrame({
        'close': prices,
        'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
        'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
        'volume': np.random.randint(50000000, 150000000, len(dates))
    }, index=dates)
    
    # Add forward returns for outcome analysis
    df['forward_return'] = df['close'].pct_change().shift(-1) * 100  # Next day return %
    
    # Generate realistic pattern occurrences
    df['gamma_trap'] = False
    df['gamma_flip'] = False
    df['pin_risk'] = False
    df['vol_squeeze'] = False
    df['dealer_reload'] = False
    df['liquidity_cascade'] = False
    
    # Gamma trap: occurs during high vol periods, 65% win rate
    gamma_trap_dates = np.random.choice(len(df), size=int(len(df) * 0.08), replace=False)
    df.iloc[gamma_trap_dates, df.columns.get_loc('gamma_trap')] = True
    
    # Create outcome bias for gamma_trap (65% win rate)
    for idx in gamma_trap_dates:
        if np.random.random() < 0.65:  # 65% win rate
            df.iloc[idx, df.columns.get_loc('forward_return')] = abs(df.iloc[idx]['forward_return']) + np.random.normal(0.5, 0.3)
        else:
            df.iloc[idx, df.columns.get_loc('forward_return')] = -abs(df.iloc[idx]['forward_return']) - np.random.normal(0.2, 0.2)
    
    # Gamma flip: occurs randomly, 58% win rate
    gamma_flip_dates = np.random.choice(len(df), size=int(len(df) * 0.05), replace=False)
    df.iloc[gamma_flip_dates, df.columns.get_loc('gamma_flip')] = True
    
    for idx in gamma_flip_dates:
        if np.random.random() < 0.58:  # 58% win rate
            df.iloc[idx, df.columns.get_loc('forward_return')] = abs(df.iloc[idx]['forward_return']) + np.random.normal(0.3, 0.2)
        else:
            df.iloc[idx, df.columns.get_loc('forward_return')] = -abs(df.iloc[idx]['forward_return']) - np.random.normal(0.1, 0.1)
    
    # Pin risk: occurs rarely, 72% win rate (high confidence when it happens)
    pin_risk_dates = np.random.choice(len(df), size=int(len(df) * 0.03), replace=False)
    df.iloc[pin_risk_dates, df.columns.get_loc('pin_risk')] = True
    
    for idx in pin_risk_dates:
        if np.random.random() < 0.72:  # 72% win rate
            df.iloc[idx, df.columns.get_loc('forward_return')] = abs(df.iloc[idx]['forward_return']) + np.random.normal(0.8, 0.4)
        else:
            df.iloc[idx, df.columns.get_loc('forward_return')] = -abs(df.iloc[idx]['forward_return']) - np.random.normal(0.3, 0.2)
    
    # Vol squeeze: 51% win rate (barely better than random)
    vol_squeeze_dates = np.random.choice(len(df), size=int(len(df) * 0.06), replace=False)
    df.iloc[vol_squeeze_dates, df.columns.get_loc('vol_squeeze')] = True
    
    for idx in vol_squeeze_dates:
        if np.random.random() < 0.51:  # 51% win rate (barely significant)
            df.iloc[idx, df.columns.get_loc('forward_return')] = abs(df.iloc[idx]['forward_return']) + np.random.normal(0.1, 0.1)
    
    # Add some pattern confidence scores
    df['pattern_confidence'] = 50.0  # Base confidence
    df.loc[df['gamma_trap'], 'pattern_confidence'] = np.random.normal(75, 10, sum(df['gamma_trap']))
    df.loc[df['gamma_flip'], 'pattern_confidence'] = np.random.normal(65, 15, sum(df['gamma_flip']))
    df.loc[df['pin_risk'], 'pattern_confidence'] = np.random.normal(85, 8, sum(df['pin_risk']))
    df.loc[df['vol_squeeze'], 'pattern_confidence'] = np.random.normal(60, 12, sum(df['vol_squeeze']))
    
    # Add market regime data
    regimes = ['low_vol', 'normal', 'high_vol', 'trending_up', 'trending_down']
    df['market_regime'] = np.random.choice(regimes, len(df), p=[0.2, 0.4, 0.2, 0.1, 0.1])
    
    # Add Fed context flags
    df['is_fomc_week'] = False
    df['in_blackout_period'] = False
    df['stress_regime'] = np.random.choice(['normal', 'elevated', 'extreme'], len(df), p=[0.7, 0.25, 0.05])
    
    # FOMC weeks (8 times per year)
    fomc_weeks = np.random.choice(len(df), size=int(len(df) * 8 / 365), replace=False)
    df.iloc[fomc_weeks, df.columns.get_loc('is_fomc_week')] = True
    
    print(f"✅ Generated {len(df)} days of historical data")
    print(f"   📈 Patterns: gamma_trap={sum(df['gamma_trap'])}, gamma_flip={sum(df['gamma_flip'])}, pin_risk={sum(df['pin_risk'])}")
    
    return df


def demo_pattern_probability_mapper():
    """Demonstrate PatternProbabilityMapper capabilities."""
    print("\n" + "="*80)
    print("🎯 DEMO: PATTERN PROBABILITY MAPPER")
    print("="*80)
    
    # Create mock data
    historical_data = create_mock_historical_data(n_days=500)
    
    # Initialize mapper
    mapper = PatternProbabilityMapper()
    
    # 1. Analyze pattern outcomes
    print("\n📊 1. ANALYZING PATTERN OUTCOMES")
    print("-" * 50)
    
    patterns_to_analyze = ['gamma_trap', 'gamma_flip', 'pin_risk', 'vol_squeeze']
    pattern_outcomes = {}
    
    for pattern in patterns_to_analyze:
        print(f"\n🔍 Analyzing {pattern}...")
        outcome = mapper.analyze_pattern_outcomes(
            pattern_name=pattern,
            historical_data=historical_data,
            lookforward_days=1
        )
        pattern_outcomes[pattern] = outcome
        
        if 'error' not in outcome:
            print(f"   ✅ Win Rate: {outcome['win_rate']}%")
            print(f"   📈 Avg Return: {outcome['mean_return']}%")
            print(f"   📊 Sample Size: {outcome['total_occurrences']}")
            print(f"   🎯 Sharpe Ratio: {outcome.get('sharpe_ratio', 'N/A')}")
        else:
            print(f"   ❌ Error: {outcome['error']}")
    
    # 2. Calculate conditional probabilities
    print("\n🧮 2. CALCULATING CONDITIONAL PROBABILITIES")
    print("-" * 50)
    
    conditional_probs = mapper.calculate_conditional_probabilities(
        historical_data=historical_data,
        pattern_names=patterns_to_analyze
    )
    
    print(f"✅ Analyzed conditional probabilities for {conditional_probs['patterns_analyzed']} patterns")
    
    for pattern, data in conditional_probs['conditional_probabilities'].items():
        print(f"\n📋 {pattern.upper()}:")
        base_prob = data['base_probability']
        print(f"   Base: {base_prob.get('win_rate', 0)}% win rate ({base_prob.get('sample_size', 0)} samples)")
        
        # Fed conditional
        if data['fed_conditional']:
            print(f"   Fed Conditional:")
            for context, fed_data in data['fed_conditional'].items():
                if isinstance(fed_data, dict):
                    print(f"     • {context}: {fed_data.get('win_rate', 0)}% ({fed_data.get('sample_size', 0)} samples)")
    
    # 3. Identify high conviction setups
    print("\n🚀 3. IDENTIFYING HIGH CONVICTION SETUPS")
    print("-" * 50)
    
    high_conviction = mapper.identify_high_conviction_setups(
        conditional_probs=conditional_probs,
        min_win_rate=0.60,  # Lower threshold for demo
        min_sample_size=10
    )
    
    print(f"✅ Found {len(high_conviction)} high conviction setups")
    
    for i, setup in enumerate(high_conviction[:5], 1):
        print(f"\n🎯 {i}. {setup['pattern'].upper()}")
        print(f"   Win Rate: {setup['win_rate']*100:.1f}%")
        print(f"   Avg Return: {setup['avg_return']:.2f}%")
        print(f"   Sample Size: {setup['sample_size']}")
        print(f"   Context: {setup['context']}")
    
    return pattern_outcomes, conditional_probs, high_conviction


def demo_statistical_validator(pattern_outcomes):
    """Demonstrate StatisticalValidator capabilities."""
    print("\n" + "="*80)
    print("📈 DEMO: STATISTICAL VALIDATOR")
    print("="*80)
    
    validator = StatisticalValidator(confidence_level=0.95, min_samples=20)
    
    # Calculate significance
    print("\n🔬 STATISTICAL SIGNIFICANCE TESTING")
    print("-" * 50)
    
    significance_results = validator.calculate_significance(pattern_outcomes)
    
    print(f"✅ Tested {significance_results['patterns_tested']} patterns")
    print(f"📊 Confidence Level: {significance_results['confidence_level']*100}%")
    
    for pattern, result in significance_results['results'].items():
        if isinstance(result, dict) and 'overall_significant' in result:
            print(f"\n📋 {pattern.upper()}:")
            print(f"   Overall Significant: {'✅ YES' if result['overall_significant'] else '❌ NO'}")
            print(f"   Significant Tests: {result['significant_test_count']}/{result['total_tests']}")
            
            # T-test results
            if 't_test' in result:
                t_test = result['t_test']
                print(f"   T-test p-value: {t_test.get('p_value', 'N/A'):.4f}")
            
            # Bootstrap CI
            if 'bootstrap_ci' in result:
                ci = result['bootstrap_ci']
                print(f"   95% CI: [{ci.get('lower_bound', 0):.3f}, {ci.get('upper_bound', 0):.3f}]")
                print(f"   Excludes Zero: {'✅' if ci.get('excludes_zero') else '❌'}")
        else:
            print(f"\n📋 {pattern.upper()}: {result.get('reason', 'Error')}")
    
    return significance_results


def demo_confidence_scorer(pattern_outcomes, significance_results):
    """Demonstrate ConfidenceScorer capabilities."""
    print("\n" + "="*80)
    print("🎯 DEMO: CONFIDENCE SCORER")
    print("="*80)
    
    scorer = ConfidenceScorer()
    
    # Mock market context
    market_context = {
        'fed_environment': 'accommodative rates, policy pause',
        'market_stress_level': 'normal',
        'vix_regime': 'low'
    }
    
    print("\n🏦 MARKET CONTEXT:")
    for key, value in market_context.items():
        print(f"   {key}: {value}")
    
    # Batch score patterns
    print("\n🎯 CONFIDENCE SCORING")
    print("-" * 50)
    
    confidence_results = scorer.batch_score_patterns(
        patterns_data=pattern_outcomes,
        statistical_results=significance_results,
        market_context=market_context
    )
    
    print(f"✅ Scored {confidence_results['patterns_scored']} patterns")
    
    summary = confidence_results['summary']
    print(f"\n📊 SUMMARY STATISTICS:")
    print(f"   Average Confidence: {summary['avg_confidence']}%")
    print(f"   High Confidence Patterns: {summary['high_confidence_patterns']}")
    print(f"   Medium Confidence Patterns: {summary['medium_confidence_patterns']}")
    print(f"   Low Confidence Patterns: {summary['low_confidence_patterns']}")
    
    print(f"\n🏆 TOP 3 PATTERNS:")
    for i, pattern in enumerate(summary['top_3_patterns'], 1):
        print(f"   {i}. {pattern['pattern'].upper()}: {pattern['confidence']}% ({pattern['level']})")
    
    # Detailed breakdown for top pattern
    if confidence_results['pattern_scores']:
        top_pattern_name = list(confidence_results['pattern_scores'].keys())[0]
        top_pattern = confidence_results['pattern_scores'][top_pattern_name]
        
        print(f"\n🔍 DETAILED BREAKDOWN: {top_pattern_name.upper()}")
        print(f"   Overall Confidence: {top_pattern['overall_confidence']}%")
        print(f"   Confidence Level: {top_pattern['confidence_level']}")
        print(f"   Reliability: {top_pattern['reliability']}")
        print(f"   Sample Size: {top_pattern['sample_size']}")
        
        print(f"\n   Component Scores:")
        for component, score in top_pattern['component_scores'].items():
            weight = top_pattern['component_weights'][component]
            print(f"     • {component}: {score}% (weight: {weight*100}%)")
    
    return confidence_results


def demo_pattern_engine_integration():
    """Demonstrate PatternEngineIntegration unified workflow."""
    print("\n" + "="*80)
    print("🔧 DEMO: PATTERN ENGINE INTEGRATION")
    print("="*80)
    
    # Initialize integrated engine
    engine = PatternEngineIntegration()
    
    # Mock current GEX and price data
    print("\n📊 CREATING MOCK CURRENT DATA")
    print("-" * 50)
    
    mock_gex_data = {
        'net_gex': -2.5e9,  # Negative gamma regime
        'spot_price': 452.50,
        'flip_point': 448.75,
        'regime': 'NEGATIVE_GAMMA_LOW',
        'call_wall': 460.0,
        'put_support': 445.0,
        'high_gamma_strikes': [445.0, 450.0, 455.0, 460.0, 465.0],
        'strikes_detail': {
            445.0: {'total_gex': -5e8, 'call_gex': 2e8, 'put_gex': -7e8},
            450.0: {'total_gex': -3e8, 'call_gex': 1e8, 'put_gex': -4e8},
            455.0: {'total_gex': 2e8, 'call_gex': 3e8, 'put_gex': -1e8},
            460.0: {'total_gex': 8e8, 'call_gex': 9e8, 'put_gex': -1e8},
        }
    }
    
    mock_price_data = {
        'spot': 452.50,
        'close': 452.50,
        'volume': 95000000
    }
    
    print(f"✅ Net GEX: ${mock_gex_data['net_gex']:,.0f}")
    print(f"✅ Spot Price: ${mock_gex_data['spot_price']:.2f}")
    print(f"✅ Flip Point: ${mock_gex_data['flip_point']:.2f}")
    print(f"✅ Regime: {mock_gex_data['regime']}")
    
    # Analyze current patterns
    print("\n🎯 COMPREHENSIVE CURRENT ANALYSIS")
    print("-" * 50)
    
    try:
        current_analysis = engine.analyze_current_patterns(
            gex_data=mock_gex_data,
            price_data=mock_price_data,
            analysis_date='2024-09-11'
        )
        
        print(f"✅ Analysis completed for {current_analysis['analysis_date']}")
        print(f"📊 Patterns Detected: {current_analysis['pattern_count']}")
        print(f"🏦 Fed Environment: {current_analysis['fed_context']['fed_environment']}")
        print(f"📈 Market Stress: {current_analysis['fed_context']['market_stress_level']}")
        
        # Show detected patterns
        if current_analysis['detected_patterns']:
            print(f"\n🎯 DETECTED PATTERNS:")
            for pattern in current_analysis['detected_patterns']:
                conf = pattern.get('confidence', 0)
                fed_weight = pattern.get('fed_weight', 1.0)
                print(f"   • {pattern['pattern'].upper()}: {conf}% confidence")
                if fed_weight != 1.0:
                    base_conf = pattern.get('base_confidence', conf)
                    print(f"     └─ Base: {base_conf}% → Fed Adjusted: {conf}% ({fed_weight:.1f}x)")
                print(f"     └─ {pattern.get('details', 'No details')}")
        
        # Show top pattern
        if current_analysis.get('top_pattern'):
            top = current_analysis['top_pattern']
            print(f"\n🏆 TOP PATTERN: {top['pattern'].upper()}")
            print(f"   Confidence: {top['confidence']}%")
            print(f"   Details: {top.get('details', 'No details')}")
        
        # Show risk assessment
        risk = current_analysis['risk_assessment']
        print(f"\n⚠️  RISK ASSESSMENT:")
        print(f"   Risk Level: {risk['risk_level']}")
        print(f"   Risk Score: {risk['risk_score']}/100")
        print(f"   Recommendation: {risk['recommendation']}")
        if risk['risk_factors']:
            print(f"   Risk Factors:")
            for factor in risk['risk_factors']:
                print(f"     • {factor}")
        
        # Fed insights
        if current_analysis.get('fed_insights'):
            print(f"\n💡 FED INSIGHTS:")
            for insight in current_analysis['fed_insights']:
                print(f"   • {insight}")
        
        return current_analysis
        
    except Exception as e:
        print(f"❌ Error in current analysis: {e}")
        import traceback
        traceback.print_exc()
        return None


def demo_comprehensive_workflow():
    """Demonstrate the complete workflow matching main chat's request."""
    print("\n" + "="*100)
    print("🚀 COMPREHENSIVE DEMO: PATTERN PROBABILITY MAPPING (ISSUE #37)")
    print("="*100)
    print("This demonstrates the complete PatternProbabilityMapper as requested by main chat:")
    print("- Next-day return distributions after each pattern")
    print("- Success rates by confidence level")  
    print("- Fed context impact on pattern outcomes")
    print("- High conviction setups identification")
    print("")
    
    # Run all demos
    pattern_outcomes, conditional_probs, high_conviction = demo_pattern_probability_mapper()
    significance_results = demo_statistical_validator(pattern_outcomes)
    confidence_results = demo_confidence_scorer(pattern_outcomes, significance_results)
    current_analysis = demo_pattern_engine_integration()
    
    # Generate reports
    print("\n" + "="*80)
    print("📄 GENERATING REPORTS")
    print("="*80)
    
    try:
        # Initialize mapper for report generation
        mapper = PatternProbabilityMapper()
        
        # Generate comprehensive report
        report_path = mapper.generate_probability_report(
            pattern_outcomes=pattern_outcomes.get('gamma_trap', {}),
            conditional_probs=conditional_probs,
            high_conviction=high_conviction
        )
        
        print(f"✅ Text report generated: {report_path}")
        
        # Export JSON data
        json_path = mapper.export_results_json(
            pattern_outcomes=pattern_outcomes,
            conditional_probs=conditional_probs,
            high_conviction=high_conviction
        )
        
        print(f"✅ JSON data exported: {json_path}")
        
        return {
            'pattern_outcomes': pattern_outcomes,
            'conditional_probabilities': conditional_probs,
            'high_conviction_setups': high_conviction,
            'statistical_validation': significance_results,
            'confidence_scores': confidence_results,
            'current_analysis': current_analysis,
            'reports': {
                'text_report': report_path,
                'json_data': json_path
            }
        }
        
    except Exception as e:
        print(f"❌ Error generating reports: {e}")
        return None


def main():
    """Main execution for Pattern Probability Mapping demo."""
    print("🎯 PATTERN PROBABILITY MAPPING DEMO (ISSUE #37)")
    print("Demonstrating exactly what main chat requested:")
    print("class PatternProbabilityMapper:")
    print("    - analyze_pattern_outcomes()")
    print("    - calculate_conditional_probabilities()")  
    print("    - identify_high_conviction_setups()")
    print("")
    
    try:
        results = demo_comprehensive_workflow()
        
        if results:
            print("\n" + "="*100)
            print("✅ DEMO COMPLETED SUCCESSFULLY")
            print("="*100)
            print("🎯 Pattern Probability Mapping (Issue #37) Implementation Complete!")
            print("")
            print("📊 RESULTS SUMMARY:")
            print(f"   • Patterns Analyzed: {len(results['pattern_outcomes'])}")
            print(f"   • High Conviction Setups: {len(results['high_conviction_setups'])}")
            print(f"   • Statistical Validation: Complete")
            print(f"   • Confidence Scoring: Complete")
            print(f"   • Fed Integration: Complete")
            print(f"   • Reports Generated: ✅")
            print("")
            print("🚀 Ready for LLM training data generation and backtesting!")
            print("")
            print("📄 Reports available at:")
            if results.get('reports'):
                for report_type, path in results['reports'].items():
                    print(f"   • {report_type}: {path}")
            
        else:
            print("❌ Demo failed - check logs for details")
            
    except Exception as e:
        print(f"❌ Fatal error during demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()