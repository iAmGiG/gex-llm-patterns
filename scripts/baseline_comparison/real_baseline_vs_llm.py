#!/usr/bin/env python3
"""
Real Baseline vs LLM Comparison - Issue #58
Uses actual market data and MarketMechanicsAgent for realistic testing.
Configurable via config_defaults/baseline_comparison_config.yaml
"""

from utils.date_utils import add_business_days, date_range_trading_days
from tools.autogen_tools import fetch_market_data, fetch_options_data, calculate_gamma_exposure
from agents.market_mechanics_agent import MarketMechanicsAgent
from analysis.technical_indicator_baseline import TechnicalIndicatorBaseline
from analysis.baseline_gex_strategy import BaselineGEXStrategy
import sys
from pathlib import Path
import logging
import json
import yaml
import argparse
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))


logger = logging.getLogger(__name__)


class RealBaselineComparison:
    """
    Real baseline comparison using actual market data and O3-mini LLM.

    Tests:
    1. Raw negative GEX baseline (mechanical)
    2. Technical indicators baseline (MACD + RSI weighted)
    3. O3-mini LLM strategy (MarketMechanicsAgent)
    """

    def __init__(self, symbol: str = None, config_path: str = None):
        """Initialize with real components and configuration."""
        # Load configuration
        self.config = self._load_config(config_path)

        # Use symbol from config if not provided
        self.symbol = symbol or self.config['test_config']['default_symbol']

        # Initialize strategies with config
        self.gex_baseline = BaselineGEXStrategy()
        self.tech_baseline = TechnicalIndicatorBaseline()
        self.llm_agent = MarketMechanicsAgent(symbol=self.symbol)

        # Results storage
        self.results = {}

        logger.info(f"Initialized RealBaselineComparison for {self.symbol}")
        logger.info(f"Config: {config_path or 'default'}")

    def _load_config(self, config_path: str = None) -> dict:
        """Load configuration from YAML file."""
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / \
                'config_defaults' / 'baseline_comparison_config.yaml'

        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f"Loaded configuration from {config_path}")
            return config
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise

    def run_comprehensive_test(self,
                               start_date: str = None,
                               end_date: str = None) -> dict:
        """
        Run comprehensive test with real data.

        Args:
            start_date: Start date for testing (uses config default if None)
            end_date: End date for testing (uses config default if None)

        Returns:
            Complete comparison results
        """
        # Use config defaults if not provided
        start_date = start_date or self.config['test_config']['default_start_date']
        end_date = end_date or self.config['test_config']['default_end_date']

        logger.info(f"Starting comprehensive test: {start_date} to {end_date}")

        # 1. Get real market data
        market_data = self._fetch_real_market_data(start_date, end_date)
        if market_data is None or market_data.empty:
            logger.error("Failed to fetch market data")
            return {}

        # 2. Get real GEX data for negative GEX days (only if needed)
        gex_data = {}
        if (self.config['strategies']['raw_gex_baseline']['enabled'] or
                self.config['strategies']['llm_strategy']['enabled']):
            gex_data = self._fetch_real_gex_data(market_data)
            if not gex_data:
                logger.error("Failed to fetch GEX data")
                return {}
        else:
            logger.info(
                "Skipping GEX data collection - no GEX-dependent strategies enabled")

        # 3. Run baseline strategies (if enabled)
        logger.info("Running baseline strategies...")

        if self.config['strategies']['raw_gex_baseline']['enabled']:
            self.results['raw_gex_baseline'] = self._test_raw_gex_baseline(
                gex_data, market_data, start_date, end_date
            )

        if self.config['strategies']['technical_baseline']['enabled']:
            self.results['tech_baseline'] = self._test_technical_baseline(
                market_data, start_date, end_date
            )

        # 4. Run real LLM strategy (if enabled)
        if self.config['strategies']['llm_strategy']['enabled']:
            logger.info("Running O3-mini LLM strategy...")
            self.results['llm_strategy'] = self._test_llm_strategy(
                market_data, gex_data, start_date, end_date
            )

        # 5. Generate comparison
        comparison = self._generate_comparison()

        # 6. Save results
        self._save_results(comparison, start_date, end_date)

        return comparison

    def _fetch_real_market_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Fetch real market data using Alpha Vantage premium."""
        logger.info(f"Fetching real market data for {self.symbol}")

        try:
            result = fetch_market_data(
                symbol=self.symbol,
                start_date=start_date,
                end_date=end_date,
                use_cache=self.config['data_sources']['market_data']['use_cache']
            )

            if result['status'] == 'success':
                logger.info(
                    f"Fetched {len(result['data'])} days of market data from {result['source']}")
                return result['data']
            else:
                logger.error(
                    f"Market data fetch failed: {result.get('message')}")
                return pd.DataFrame()

        except Exception as e:
            logger.error(f"Error fetching market data: {e}")
            return pd.DataFrame()

    def _fetch_real_gex_data(self, market_data: pd.DataFrame) -> dict:
        """Fetch real GEX data for each trading day."""
        gex_data = {}

        logger.info("Fetching real GEX data...")

        for date_idx, row in market_data.iterrows():
            # Alpha Vantage returns date as index, not column
            date_str = date_idx.strftime(
                '%Y-%m-%d') if hasattr(date_idx, 'strftime') else str(date_idx)

            try:
                # Get options data
                options_result = fetch_options_data(
                    symbol=self.symbol,
                    trading_date=date_str,
                    use_cache=self.config['data_sources']['options_data']['use_cache']
                )

                if options_result['status'] != 'success':
                    continue

                # Calculate GEX
                gex_result = calculate_gamma_exposure(
                    symbol=self.symbol,
                    trading_date=date_str,
                    spot_price=row['close'],
                    use_cache=self.config['data_sources']['options_data']['use_cache']
                )

                if gex_result['status'] == 'success':
                    gex_data[date_str] = gex_result['metrics']['net_gex']

            except Exception as e:
                logger.warning(f"Failed to get GEX for {date_str}: {e}")
                continue

        logger.info(f"Collected GEX data for {len(gex_data)} days")

        # Count negative GEX days
        if len(gex_data) > 0:
            negative_days = sum(1 for gex in gex_data.values() if gex < 0)
            logger.info(
                f"Negative GEX days: {negative_days} ({negative_days/len(gex_data)*100:.1f}%)")
        else:
            logger.warning(
                "No GEX data collected - check API connectivity or fallback to sample data")
            negative_days = 0

        return gex_data

    def _test_raw_gex_baseline(self, gex_data: dict, market_data: pd.DataFrame,
                               start_date: str, end_date: str) -> dict:
        """Test raw negative GEX baseline with real data."""
        logger.info("Testing raw negative GEX baseline...")

        results = self.gex_baseline.backtest(
            gex_data=gex_data,
            price_data=market_data,
            symbol=self.symbol,
            test_period=f"{start_date} to {end_date} (real data)"
        )

        logger.info(f"Raw GEX: {results['total_trades']} trades, "
                    f"{results['win_rate']:.1%} win rate, "
                    f"{results['expected_value']:.3%} EV")

        return results

    def _test_technical_baseline(self, market_data: pd.DataFrame,
                                 start_date: str, end_date: str) -> dict:
        """Test technical indicator baseline with real data."""
        logger.info("Testing technical indicator baseline...")

        results = self.tech_baseline.backtest(
            price_data=market_data,
            symbol=self.symbol,
            test_period=f"{start_date} to {end_date} (real data)"
        )

        logger.info(f"Technical: {results['total_trades']} trades, "
                    f"{results['win_rate']:.1%} win rate, "
                    f"{results['expected_value']:.3%} EV")

        return results

    def _test_llm_strategy(self, market_data: pd.DataFrame, gex_data: dict,
                           start_date: str, end_date: str) -> dict:
        """Test real O3-mini LLM strategy using MarketMechanicsAgent."""
        logger.info("Testing O3-mini LLM strategy with MarketMechanicsAgent...")

        llm_trades = []
        negative_gex_days = [date for date, gex in gex_data.items() if gex < 0]

        # Get max trades limit from config
        max_trades = self.config['strategies']['llm_strategy']['max_trades_per_test']
        logger.info(
            f"Analyzing {len(negative_gex_days)} negative GEX days with LLM (limit: {max_trades})...")

        for i, date_str in enumerate(negative_gex_days[:max_trades]):
            if i % 5 == 0:
                logger.info(
                    f"Processing day {i+1}/{min(max_trades, len(negative_gex_days))}: {date_str}")

            try:
                # Run daily analysis with real LLM
                analysis = self.llm_agent.daily_analysis(date_str)

                confidence_threshold = self.config['strategies']['llm_strategy']['confidence_threshold']
                if not analysis or analysis.get('confidence', 0) < confidence_threshold:
                    continue

                signal = analysis.get('actionable_signal', {})

                if signal.get('action') in ['BUY', 'SELL']:
                    # Execute the trade
                    trade_result = self._execute_llm_trade(
                        date_str, signal, market_data
                    )

                    if trade_result:
                        trade_result.update({
                            'llm_confidence': analysis['confidence'],
                            'llm_interpretation': analysis['mechanics_interpretation'],
                            'gex_value': gex_data[date_str]
                        })
                        llm_trades.append(trade_result)

                        logger.info(f"LLM trade on {date_str}: {signal['action']} "
                                    f"(confidence: {analysis['confidence']:.0f}%)")

            except Exception as e:
                logger.warning(f"LLM analysis failed for {date_str}: {e}")
                continue

        # Calculate LLM strategy metrics
        if llm_trades:
            results = self._calculate_llm_metrics(
                llm_trades, start_date, end_date)
        else:
            results = {
                'strategy_type': 'o3_mini_llm',
                'total_trades': 0,
                'message': 'No high-confidence LLM trades executed'
            }

        logger.info(f"LLM Strategy: {results.get('total_trades', 0)} trades, "
                    f"{results.get('win_rate', 0):.1%} win rate, "
                    f"{results.get('expected_value', 0):.3%} EV")

        return results

    def _execute_llm_trade(self, date_str: str, signal: dict, market_data: pd.DataFrame) -> dict:
        """Execute a trade based on LLM signal."""
        try:
            date = pd.to_datetime(date_str)
            # Alpha Vantage data has date as index
            if date not in market_data.index:
                return None

            entry_price = market_data.loc[date, 'close']

            # Parse signal parameters
            direction = signal['action'].lower()

            # Use risk parameters from config
            stop_loss_pct = self.config['risk_management']['stop_loss_pct']
            target_pct = self.config['risk_management']['profit_target_pct']

            if direction == 'buy':
                stop_loss = entry_price * (1 - stop_loss_pct)
                target = entry_price * (1 + target_pct)
            else:  # sell
                stop_loss = entry_price * (1 + stop_loss_pct)
                target = entry_price * (1 - target_pct)

            # Find exit over max holding days from config
            max_days = self.config['risk_management']['max_holding_days']
            for days_held in range(1, max_days + 1):
                exit_date = date + timedelta(days=days_held)
                # Alpha Vantage data has date as index
                if exit_date not in market_data.index:
                    continue

                # Check stops/targets using Alpha Vantage data structure
                if direction == 'buy':
                    if market_data.loc[exit_date, 'low'] <= stop_loss:
                        exit_price = stop_loss
                        exit_reason = 'stop_loss'
                        break
                    elif market_data.loc[exit_date, 'high'] >= target:
                        exit_price = target
                        exit_reason = 'target'
                        break
                    elif days_held == max_days:
                        exit_price = market_data.loc[exit_date, 'close']
                        exit_reason = 'time_exit'
                        break
                else:  # sell
                    if market_data.loc[exit_date, 'high'] >= stop_loss:
                        exit_price = stop_loss
                        exit_reason = 'stop_loss'
                        break
                    elif market_data.loc[exit_date, 'low'] <= target:
                        exit_price = target
                        exit_reason = 'target'
                        break
                    elif days_held == max_days:
                        exit_price = market_data.loc[exit_date, 'close']
                        exit_reason = 'time_exit'
                        break
            else:
                return None

            # Calculate P&L
            if direction == 'buy':
                pnl_pct = (exit_price - entry_price) / entry_price
            else:
                pnl_pct = (entry_price - exit_price) / entry_price

            return {
                'entry_date': date_str,
                'exit_date': exit_date.strftime('%Y-%m-%d'),
                'entry_price': entry_price,
                'exit_price': exit_price,
                'exit_reason': exit_reason,
                'direction': direction,
                'pnl_pct': pnl_pct,
                'win': pnl_pct > 0,
                'days_held': days_held
            }

        except Exception as e:
            logger.error(f"Error executing LLM trade: {e}")
            return None

    def _calculate_llm_metrics(self, trades: list, start_date: str, end_date: str) -> dict:
        """Calculate metrics for LLM strategy."""
        if not trades:
            return {'strategy_type': 'o3_mini_llm', 'total_trades': 0}

        trade_df = pd.DataFrame(trades)
        wins = trade_df['win'].sum()
        total = len(trade_df)
        win_rate = wins / total

        # Expected value
        avg_win = trade_df[trade_df['win']
                           ]['pnl_pct'].mean() if wins > 0 else 0
        avg_loss = trade_df[~trade_df['win']]['pnl_pct'].mean() if (
            total - wins) > 0 else 0
        expected_value = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)

        # Sharpe ratio
        returns = trade_df['pnl_pct']
        if len(returns) > 1 and returns.std() > 0:
            sharpe = (returns.mean() / returns.std()) * \
                np.sqrt(252 / len(returns))
        else:
            sharpe = 0

        # Max drawdown
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()

        return {
            'strategy_type': 'o3_mini_llm',
            'total_trades': total,
            'wins': wins,
            'losses': total - wins,
            'win_rate': win_rate,
            'expected_value': expected_value,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_drawdown,
            'avg_confidence': trade_df['llm_confidence'].mean(),
            'exit_reasons': trade_df['exit_reason'].value_counts().to_dict(),
            'trades': trades,
            'metadata': {
                'symbol': self.symbol,
                'test_period': f"{start_date} to {end_date} (real data)",
                'strategy_version': 'o3_mini_market_mechanics_v1.0',
                'llm_model': 'O3-mini via MarketMechanicsAgent',
                'confidence_threshold': 75,
                'analysis_method': 'WHO/WHOM/WHAT market mechanics'
            }
        }

    def _generate_comparison(self) -> dict:
        """Generate comprehensive comparison."""
        logger.info("Generating comparison analysis...")

        summary = {}

        # Only include enabled strategies in summary
        if self.config['strategies']['raw_gex_baseline']['enabled'] and 'raw_gex_baseline' in self.results:
            summary['raw_gex_baseline'] = {
                'trades': self.results['raw_gex_baseline'].get('total_trades', 0),
                'win_rate': self.results['raw_gex_baseline'].get('win_rate', 0),
                'expected_value': self.results['raw_gex_baseline'].get('expected_value', 0),
                'type': 'Mechanical (every negative GEX)'
            }

        if self.config['strategies']['technical_baseline']['enabled'] and 'tech_baseline' in self.results:
            summary['tech_baseline'] = {
                'trades': self.results['tech_baseline'].get('total_trades', 0),
                'win_rate': self.results['tech_baseline'].get('win_rate', 0),
                'expected_value': self.results['tech_baseline'].get('expected_value', 0),
                'type': 'Technical (MACD + RSI weighted)'
            }

        if self.config['strategies']['llm_strategy']['enabled'] and 'llm_strategy' in self.results:
            summary['llm_strategy'] = {
                'trades': self.results['llm_strategy'].get('total_trades', 0),
                'win_rate': self.results['llm_strategy'].get('win_rate', 0),
                'expected_value': self.results['llm_strategy'].get('expected_value', 0),
                'type': 'O3-mini LLM (MarketMechanicsAgent)'
            }

        comparison = {
            'summary': summary,
            'value_add_analysis': self._analyze_llm_value_add(),
            'detailed_results': self.results,
            'test_metadata': {
                'symbol': self.symbol,
                'strategies_tested': list(summary.keys()),
                'config_used': {
                    'risk_management': self.config['risk_management'],
                    'targets': self.config['targets'],
                    'strategies': {k: v for k, v in self.config['strategies'].items() if v['enabled']}
                }
            }
        }

        return comparison

    def _analyze_llm_value_add(self) -> dict:
        """Analyze the value added by LLM over baselines."""
        llm_ev = self.results.get('llm_strategy', {}).get('expected_value', 0)
        raw_gex_ev = self.results.get(
            'raw_gex_baseline', {}).get('expected_value', 0)
        tech_ev = self.results.get(
            'tech_baseline', {}).get('expected_value', 0)

        llm_wr = self.results.get('llm_strategy', {}).get('win_rate', 0)
        raw_gex_wr = self.results.get(
            'raw_gex_baseline', {}).get('win_rate', 0)
        tech_wr = self.results.get('tech_baseline', {}).get('win_rate', 0)

        return {
            'vs_raw_gex': {
                'ev_improvement': llm_ev - raw_gex_ev,
                'wr_improvement': llm_wr - raw_gex_wr,
                'ev_improvement_pct': ((llm_ev - raw_gex_ev) / abs(raw_gex_ev) * 100) if raw_gex_ev != 0 else 0
            },
            'vs_technical': {
                'ev_improvement': llm_ev - tech_ev,
                'wr_improvement': llm_wr - tech_wr,
                'ev_improvement_pct': ((llm_ev - tech_ev) / abs(tech_ev) * 100) if tech_ev != 0 else 0
            },
            'targets_met': {
                'win_rate_target': llm_wr >= self.config['targets']['target_performance']['win_rate'],
                'ev_target': llm_ev >= self.config['targets']['target_performance']['expected_value'],
                'beat_baseline': llm_ev > max(raw_gex_ev, tech_ev)
            }
        }

    def _save_results(self, comparison: dict, start_date: str, end_date: str):
        """Save results to JSON file."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"real_baseline_comparison_{start_date}_{end_date}_{timestamp}.json"

        output_dir = Path(__file__).parent.parent.parent / \
            self.config['output']['results_directory']
        output_dir.mkdir(parents=True, exist_ok=True)
        filepath = output_dir / filename

        with open(filepath, 'w') as f:
            json.dump(comparison, f, indent=2, default=str)

        logger.info(f"Results saved to: {filepath}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Real Baseline vs LLM Comparison")
    parser.add_argument("--symbol", type=str,
                        help="Trading symbol (default from config)")
    parser.add_argument("--config", type=str,
                        help="Path to configuration file")
    parser.add_argument("--start-date", type=str,
                        help="Start date YYYY-MM-DD (default from config)")
    parser.add_argument("--end-date", type=str,
                        help="End date YYYY-MM-DD (default from config)")

    args = parser.parse_args()

    # Initialize comparison
    comparison = RealBaselineComparison(
        symbol=args.symbol, config_path=args.config)

    # Set up logging
    log_level = getattr(
        logging, comparison.config['output']['log_level'].upper())
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    logger.info("="*80)
    logger.info("REAL BASELINE vs LLM COMPARISON - Issue #58")
    logger.info("Using actual market data and O3-mini MarketMechanicsAgent")
    logger.info(f"Symbol: {comparison.symbol}")
    logger.info(f"Config: {args.config or 'default'}")
    logger.info("="*80)

    # Run comprehensive test
    results = comparison.run_comprehensive_test(
        start_date=args.start_date,
        end_date=args.end_date
    )

    if results:
        # Print summary
        logger.info("\n" + "="*60)
        logger.info("COMPARISON RESULTS SUMMARY")
        logger.info("="*60)

        for strategy, metrics in results['summary'].items():
            logger.info(f"\n{strategy.upper().replace('_', ' ')}:")
            logger.info(f"  Type: {metrics['type']}")
            logger.info(f"  Trades: {metrics['trades']}")
            logger.info(f"  Win Rate: {metrics['win_rate']:.1%}")
            logger.info(f"  Expected Value: {metrics['expected_value']:.3%}")

        # Print value add analysis if LLM strategy was tested
        value_add = results['value_add_analysis']
        if 'llm_strategy' in results['summary']:
            logger.info(f"\nLLM VALUE ADD vs RAW GEX:")
            logger.info(
                f"  EV Improvement: {value_add['vs_raw_gex']['ev_improvement']:+.3%}")
            logger.info(
                f"  WR Improvement: {value_add['vs_raw_gex']['wr_improvement']:+.1%}")

            # Print targets from config
            wr_target = comparison.config['targets']['target_performance']['win_rate']
            ev_target = comparison.config['targets']['target_performance']['expected_value']

            logger.info(f"\nTARGETS MET:")
            targets = value_add['targets_met']
            logger.info(
                f"  Win Rate ≥{wr_target:.0%}: {'✅' if targets['win_rate_target'] else '❌'}")
            logger.info(
                f"  EV ≥{ev_target:.1%}: {'✅' if targets['ev_target'] else '❌'}")
            logger.info(
                f"  Beat Baseline: {'✅' if targets['beat_baseline'] else '❌'}")
        else:
            logger.info(
                "\nLLM strategy not tested - no value add analysis available")

    logger.info("\n" + "="*80)
    logger.info("✅ REAL COMPARISON COMPLETE")
    logger.info("="*80)
