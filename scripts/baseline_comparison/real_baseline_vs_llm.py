#!/usr/bin/env python3
"""
Real Baseline vs LLM Comparison - Issue #58
Uses actual market data and MarketMechanicsAgent for realistic testing.
Configurable via config_defaults/baseline_comparison_config.yaml
"""

from utils.date_utils import date_range_trading_days
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
from datetime import timedelta
import pandas as pd
import numpy as np

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

# Also add the project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


logger = logging.getLogger(__name__)


class RealBaselineComparison:
    """
    Real baseline comparison using actual market data and O3-mini LLM.

    Tests:
    1. Raw negative GEX baseline (mechanical)
    2. Technical indicators baseline (MACD + RSI weighted)
    3. O3-mini LLM strategy (MarketMechanicsAgent)
    """

    def __init__(self, symbol: str = None, config_path: str = None, **overrides):
        """Initialize with real components and configuration."""
        # Load configuration
        self.config = self._load_config(config_path)

        # Apply command-line overrides
        self._apply_overrides(overrides)

        # Use symbol from config if not provided (after overrides)
        self.symbol = symbol or self.config['test_config']['default_symbol']

        # Initialize strategies with config
        self.gex_baseline = BaselineGEXStrategy()
        self.tech_baseline = TechnicalIndicatorBaseline()
        # Pass LLM config to MarketMechanicsAgent
        llm_config = self.config.get('llm_config', {})
        self.llm_agent = MarketMechanicsAgent(
            symbol=self.symbol, config=llm_config)

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

    def _apply_overrides(self, overrides: dict):
        """Apply command-line overrides to configuration."""
        for key, value in overrides.items():
            if value is not None:  # Only override if value provided
                if key in ['start_date', 'end_date']:
                    # Update test_config dates
                    if key == 'start_date':
                        self.config['test_config']['default_start_date'] = value
                    elif key == 'end_date':
                        self.config['test_config']['default_end_date'] = value
                elif key == 'symbol':
                    self.config['test_config']['default_symbol'] = value
                elif key == 'experiment_type':
                    self.config['experiment_config']['type'] = value
                # Add other overrides as needed
                logger.debug(f"Applied override: {key} = {value}")

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
                market_data = result['data']

                # Ensure consistent format - Alpha Vantage uses date as index
                if 'date' not in market_data.columns and hasattr(market_data.index, 'dtype'):
                    # Reset index to convert datetime index to date column
                    market_data = market_data.reset_index()
                    # Check if the index column is named something different
                    if market_data.columns[0] in ['index', 'Date', 'date'] or str(market_data.index.dtype).startswith('datetime'):
                        market_data = market_data.rename(
                            columns={market_data.columns[0]: 'date'})
                    logger.info(
                        f"Converted market data format - columns: {list(market_data.columns)}")

                # Fix timezone issue: normalize dates to date-only format for matching
                if 'date' in market_data.columns:
                    # Remove timezone and normalize to midnight for signal matching
                    market_data['date'] = pd.to_datetime(
                        market_data['date']).dt.tz_localize(None).dt.normalize()
                    logger.info(f"Normalized dates to remove timezone info")

                return market_data
            else:
                logger.error(
                    f"Market data fetch failed: {result.get('message')}")
                return pd.DataFrame()

        except Exception as e:
            logger.error(f"Error fetching market data: {e}")
            return pd.DataFrame()

    def _fetch_real_gex_data(self, market_data: pd.DataFrame) -> dict:
        """Fetch real GEX data using direct database access for debugging."""
        gex_data = {}

        logger.info("Fetching real GEX data from consolidated database...")

        # Use direct database access to get the values we saw earlier
        import sqlite3
        db_path = "./.cache/consolidated_historical.db"

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            for idx, row in market_data.iterrows():
                # Handle both date column and date index formats
                if 'date' in market_data.columns:
                    date_str = row['date'].strftime(
                        '%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date'])
                else:
                    # Alpha Vantage returns date as index, not column
                    date_str = idx.strftime(
                        '%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx)

                # Query database directly
                cursor.execute(
                    "SELECT total_gex FROM daily_gex_metrics WHERE symbol = ? AND date = ?",
                    (self.symbol, date_str)
                )
                result = cursor.fetchone()

                if result:
                    gex_value = result[0]
                    gex_data[date_str] = gex_value
                    logger.info(
                        f"Database GEX for {date_str}: {gex_value:.2e}")
                else:
                    logger.warning(f"No database GEX data for {date_str}")

            conn.close()

        except Exception as e:
            logger.error(f"Database query failed: {e}")
            return {}

        logger.info(f"Collected GEX data for {len(gex_data)} days")

        # DEBUG: Print all GEX data collected
        logger.info("DEBUG - GEX data collected:")
        for date, gex_value in sorted(gex_data.items()):
            logger.info(
                f"  {date}: {gex_value:.2e} ({'NEGATIVE' if gex_value < 0 else 'POSITIVE'})")

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

        # DEBUG: Check inputs
        logger.info(f"DEBUG - GEX data input: {len(gex_data)} days")
        logger.info(f"DEBUG - Market data input: {len(market_data)} rows")
        logger.info(
            f"DEBUG - Market data columns: {list(market_data.columns)}")

        # DEBUG: Check market data format
        if not market_data.empty:
            logger.info(f"DEBUG - Market data sample:")
            logger.info(
                f"  First row date: {market_data.iloc[0]['date']} (type: {type(market_data.iloc[0]['date'])})")
            logger.info(f"  Date column dtype: {market_data['date'].dtype}")
            logger.info(market_data.head(2).to_string())

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

        # Track confidence distribution and reasoning
        confidence_scores = []
        llm_analysis_log = []

        # Get max trades limit from config
        max_trades = self.config['strategies']['llm_strategy']['max_trades_per_test']
        confidence_threshold = self.config['strategies']['llm_strategy']['confidence_threshold']

        logger.info(
            f"Analyzing {len(negative_gex_days)} negative GEX days with LLM (limit: {max_trades})...")
        logger.info(f"Confidence threshold: {confidence_threshold}%")

        for i, date_str in enumerate(negative_gex_days[:max_trades]):
            logger.info(
                f"Processing day {i+1}/{min(max_trades, len(negative_gex_days))}: {date_str}")

            try:
                # Run daily analysis with real LLM
                analysis = self.llm_agent.daily_analysis(date_str)

                if analysis:
                    confidence = analysis.get('confidence', 0)
                    confidence_scores.append(confidence)

                    # Log ALL confidence scores and reasoning
                    mechanics = analysis.get('mechanics_interpretation', {})
                    signal = analysis.get('actionable_signal', {})

                    logger.info(f"LLM Analysis for {date_str}:")
                    logger.info(f"  Confidence: {confidence:.1f}%")
                    logger.info(
                        f"  Primary Mechanic: {mechanics.get('primary_mechanic', 'Unknown')}")
                    logger.info(f"  WHO: {mechanics.get('who', 'Unknown')}")
                    logger.info(f"  WHOM: {mechanics.get('whom', 'Unknown')}")
                    logger.info(f"  WHAT: {mechanics.get('what', 'Unknown')}")
                    logger.info(
                        f"  Signal Action: {signal.get('action', 'None')}")
                    logger.info(
                        f"  Signal Rationale: {signal.get('rationale', 'No rationale')}")

                    # Store detailed analysis
                    llm_analysis_log.append({
                        'date': date_str,
                        'confidence': confidence,
                        'gex_value': gex_data[date_str],
                        'mechanics': mechanics,
                        'signal': signal,
                        'above_threshold': confidence >= confidence_threshold
                    })

                    # Check if trade qualifies
                    if confidence < confidence_threshold:
                        logger.info(
                            f"  ❌ Trade REJECTED: Confidence {confidence:.1f}% < {confidence_threshold}%")
                        logger.info(
                            f"  Reasoning: {mechanics.get('narrative', 'No narrative available')}")
                        continue

                    logger.info(
                        f"  ✅ Trade QUALIFIED: Confidence {confidence:.1f}% >= {confidence_threshold}%")

                    if signal.get('action') in ['BUY', 'SELL']:
                        # Execute the trade
                        trade_result = self._execute_llm_trade(
                            date_str, signal, market_data
                        )

                        if trade_result:
                            trade_result.update({
                                'llm_confidence': confidence,
                                'llm_interpretation': mechanics,
                                'llm_signal_reasoning': signal.get('rationale', ''),
                                'gex_value': gex_data[date_str]
                            })
                            llm_trades.append(trade_result)

                            logger.info(f"  🚀 LLM TRADE EXECUTED: {signal['action']} "
                                        f"(confidence: {confidence:.0f}%)")
                        else:
                            logger.warning(
                                f"  ⚠️ Trade execution failed for {date_str}")
                    else:
                        logger.info(
                            f"  ⚠️ No actionable signal: {signal.get('action', 'None')}")
                else:
                    logger.warning(
                        f"  ❌ LLM analysis returned None for {date_str}")
                    confidence_scores.append(0)

            except Exception as e:
                logger.warning(f"LLM analysis failed for {date_str}: {e}")
                confidence_scores.append(0)
                continue

        # Generate comprehensive confidence analysis
        if confidence_scores:
            logger.info("=" * 60)
            logger.info("LLM CONFIDENCE DISTRIBUTION ANALYSIS")
            logger.info("=" * 60)
            logger.info(f"Total days analyzed: {len(confidence_scores)}")
            logger.info(f"Mean confidence: {np.mean(confidence_scores):.1f}%")
            logger.info(
                f"Median confidence: {np.median(confidence_scores):.1f}%")
            logger.info(f"Max confidence: {max(confidence_scores):.1f}%")
            logger.info(f"Min confidence: {min(confidence_scores):.1f}%")
            logger.info(
                f"Trades above {confidence_threshold}% threshold: {sum(c >= confidence_threshold for c in confidence_scores)}")

            # Confidence buckets
            buckets = [(0, 25), (25, 50), (50, 75), (75, 90), (90, 100)]
            for low, high in buckets:
                count = sum(low <= c < high for c in confidence_scores)
                logger.info(
                    f"  {low}-{high}%: {count} days ({count/len(confidence_scores)*100:.1f}%)")
            logger.info("=" * 60)

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

        # Add confidence analysis to results
        results['confidence_analysis'] = {
            'total_days_analyzed': len(confidence_scores),
            'mean_confidence': np.mean(confidence_scores) if confidence_scores else 0,
            'median_confidence': np.median(confidence_scores) if confidence_scores else 0,
            'max_confidence': max(confidence_scores) if confidence_scores else 0,
            'min_confidence': min(confidence_scores) if confidence_scores else 0,
            'qualified_trades': sum(c >= confidence_threshold for c in confidence_scores),
            'confidence_threshold': confidence_threshold,
            'confidence_distribution': {
                f"{low}-{high}%": sum(low <= c < high for c in confidence_scores)
                for low, high in [(0, 25), (25, 50), (50, 75), (75, 90), (90, 100)]
            } if confidence_scores else {},
            # Store first 5 for debugging
            'detailed_analysis': llm_analysis_log[:5]
        }

        logger.info(f"LLM Strategy: {results.get('total_trades', 0)} trades, "
                    f"{results.get('win_rate', 0):.1%} win rate, "
                    f"{results.get('expected_value', 0):.3%} EV")

        return results

    def _execute_llm_trade(self, date_str: str, signal: dict, market_data: pd.DataFrame) -> dict:
        """Execute a trade based on LLM signal."""
        try:
            date = pd.to_datetime(date_str)
            # Check if data has date column or uses date as index
            if 'date' in market_data.columns:
                entry_row = market_data[market_data['date'] == date]
                if entry_row.empty:
                    return None
                entry_price = entry_row['close'].iloc[0]
            else:
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

                # Check data format and get exit data
                if 'date' in market_data.columns:
                    exit_row = market_data[market_data['date'] == exit_date]
                    if exit_row.empty:
                        continue
                    exit_data = exit_row.iloc[0]
                else:
                    # Alpha Vantage data has date as index
                    if exit_date not in market_data.index:
                        continue
                    exit_data = market_data.loc[exit_date]

                # Check stops/targets
                if direction == 'buy':
                    if exit_data['low'] <= stop_loss:
                        exit_price = stop_loss
                        exit_reason = 'stop_loss'
                        break
                    elif exit_data['high'] >= target:
                        exit_price = target
                        exit_reason = 'target'
                        break
                    elif days_held == max_days:
                        exit_price = exit_data['close']
                        exit_reason = 'time_exit'
                        break
                else:  # sell
                    if exit_data['high'] >= stop_loss:
                        exit_price = stop_loss
                        exit_reason = 'stop_loss'
                        break
                    elif exit_data['low'] <= target:
                        exit_price = target
                        exit_reason = 'target'
                        break
                    elif days_held == max_days:
                        exit_price = exit_data['close']
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
        """Save results to JSON file with clean naming."""
        # Get experiment type and range from config
        experiment_type = self.config['experiment_config']['type']
        date_key = f"{start_date}_{end_date}"
        range_name = self.config['experiment_config']['range_naming'].get(
            date_key, f"{start_date}-{end_date}")

        # Format: experiment_ticker_range.json
        filename = f"{experiment_type}_{self.symbol}_{range_name}.json"

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
    parser.add_argument("--experiment-type", type=str,
                        help="Experiment type for naming (default from config)")

    args = parser.parse_args()

    # Initialize comparison with overrides
    overrides = {
        'start_date': getattr(args, 'start_date'),
        'end_date': getattr(args, 'end_date'),
        'experiment_type': getattr(args, 'experiment_type')
    }
    comparison = RealBaselineComparison(
        symbol=args.symbol, config_path=args.config, **overrides)

    # Set up logging - force INFO level for debugging
    logging.basicConfig(
        level=logging.INFO,
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
