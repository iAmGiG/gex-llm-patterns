#!/usr/bin/env python3
"""
Issue #145: EOD Latent Information Analysis
============================================

Validates that EOD GEX data contains sufficient predictive power for next-day
(T+1/T+2) market outcomes, addressing MC's temporal mismatch criticism.

Three-part analysis:
1. EOD Feature Extraction: 13 GEX-based features from daily snapshots
2. Statistical Baseline: Logistic regression predicting next-day materialization
3. LLM Comparison: Does LLM detection outperform statistical baseline?

Expected deliverables:
- eod_features_2024.csv: N=242 rows, 14 columns (date + 13 features)
- next_day_outcomes_2024.csv: N=242 rows with binary materialization flags
- Statistical model AUC: Target > 0.70 (strong predictive power)
- LLM AUC: Target > statistical baseline (LLM adds value)

Author: Research Team (Chat C)
Date: November 25, 2025
"""

import sqlite3
import pandas as pd
import numpy as np
import yaml
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EODFeatureExtractor:
    """Extract EOD GEX features from consolidated database."""

    def __init__(self, db_path: str = '.cache/consolidated_historical.db'):
        """Initialize database connection."""
        self.db_path = db_path
        self.conn = None

    def connect(self):
        """Establish database connection."""
        try:
            self.conn = sqlite3.connect(self.db_path)
            logger.info(f"Connected to database: {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"Database connection failed: {e}")
            raise

    def disconnect(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")

    def get_eod_gex_data(self, date: str) -> Optional[Dict]:
        """
        Fetch EOD GEX metrics for a specific date.

        Args:
            date: Date string (YYYY-MM-DD)

        Returns:
            Dictionary with GEX metrics or None if not found
        """
        if not self.conn:
            return None

        cursor = self.conn.cursor()

        try:
            # Query daily_gex_metrics table
            cursor.execute("""
                SELECT
                    date,
                    total_gex,
                    gex_oi,
                    gex_volume,
                    activity_ratio,
                    economic_regime,
                    gamma_flip_point,
                    spot_price,
                    open,
                    high,
                    low,
                    close
                FROM daily_gex_metrics
                WHERE date = ? AND symbol = 'SPY'
                LIMIT 1
            """, (date,))

            row = cursor.fetchone()
            if not row:
                return None

            return {
                'date': row[0],
                'total_gex': float(row[1]) if row[1] else 0.0,
                'gex_oi': float(row[2]) if row[2] else 0.0,
                'gex_volume': float(row[3]) if row[3] else 0.0,
                'activity_ratio': float(row[4]) if row[4] else 0.0,
                'economic_regime': row[5],
                'gamma_flip_point': float(row[6]) if row[6] else 0.0,
                'spot_price': float(row[7]) if row[7] else 0.0,
                'open': float(row[8]) if row[8] else 0.0,
                'high': float(row[9]) if row[9] else 0.0,
                'low': float(row[10]) if row[10] else 0.0,
                'close': float(row[11]) if row[11] else 0.0
            }

        except Exception as e:
            logger.warning(f"Failed to fetch GEX data for {date}: {e}")
            return None

    def extract_features(self, dates: List[str]) -> pd.DataFrame:
        """
        Extract EOD features for a list of dates.

        Args:
            dates: List of date strings (YYYY-MM-DD)

        Returns:
            DataFrame with extracted features
        """
        features_list = []

        for i, date in enumerate(dates):
            if (i + 1) % 50 == 0:
                logger.info(f"Processing {i + 1}/{len(dates)} dates...")

            gex_data = self.get_eod_gex_data(date)
            if not gex_data:
                logger.warning(f"No GEX data for {date}")
                continue

            features = self._calculate_features(gex_data)
            features_list.append(features)

        df = pd.DataFrame(features_list)
        logger.info(f"Extracted features for {len(df)} dates")
        return df

    def _calculate_features(self, gex_data: Dict) -> Dict:
        """
        Calculate 13 EOD features from GEX data.

        Args:
            gex_data: Dictionary with raw GEX metrics

        Returns:
            Dictionary with calculated features
        """
        total_gex = gex_data['total_gex']

        # Feature 1: Total GEX magnitude
        total_gex_mag = abs(total_gex)

        # Feature 2: GEX regime indicator (1 = negative/short gamma)
        gex_sign = 1 if total_gex < 0 else 0

        # Feature 3: GEX OI ratio (gamma exposure relative to open interest)
        gex_oi = gex_data['gex_oi']

        # Feature 4: GEX volume ratio (gamma exposure relative to daily volume)
        gex_volume = gex_data['gex_volume']

        # Feature 5: Activity ratio (concentration metric)
        activity_ratio = gex_data['activity_ratio']

        # Feature 6-7: Flip point proximity
        spot = gex_data['spot_price']
        flip = gex_data['gamma_flip_point']
        zero_gamma_proximity = abs(spot - flip) / spot if spot > 0 else 0.0
        spot_above_flip = 1 if spot > flip else 0

        # Feature 8-10: OHLC-based features
        open_p = gex_data['open']
        high_p = gex_data['high']
        low_p = gex_data['low']
        close_p = gex_data['close']

        intraday_range = (high_p - low_p) / open_p if open_p > 0 else 0.0
        close_open_change = (close_p - open_p) / open_p if open_p > 0 else 0.0

        return {
            'date': gex_data['date'],
            'total_gex': total_gex_mag,
            'gex_sign': gex_sign,
            'gex_oi': gex_oi,
            'gex_volume': gex_volume,
            'activity_ratio': activity_ratio,
            'zero_gamma_proximity': zero_gamma_proximity,
            'spot_above_flip': spot_above_flip,
            'intraday_range': intraday_range,
            'close_open_change': close_open_change,
            'spot_price': spot,
            'economic_regime': gex_data['economic_regime']
        }


class NextDayOutcomeCalculator:
    """Calculate next-day outcome targets from OHLCV data."""

    def __init__(self, db_path: str = '.cache/consolidated_historical.db'):
        """Initialize database connection."""
        self.db_path = db_path
        self.conn = None

    def connect(self):
        """Establish database connection."""
        try:
            self.conn = sqlite3.connect(self.db_path)
            logger.info(f"Connected to database: {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"Database connection failed: {e}")
            raise

    def disconnect(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")

    def get_ohlcv(self, date: str, symbol: str = 'SPY') -> Optional[Dict]:
        """
        Fetch OHLCV data for a specific date.

        Args:
            date: Date string (YYYY-MM-DD)
            symbol: Stock symbol (default: SPY)

        Returns:
            Dictionary with OHLCV data or None if not found
        """
        if not self.conn:
            return None

        cursor = self.conn.cursor()

        try:
            # OHLCV is stored in daily_gex_metrics table
            cursor.execute("""
                SELECT
                    date,
                    open,
                    high,
                    low,
                    close,
                    volume
                FROM daily_gex_metrics
                WHERE date = ? AND symbol = ?
                LIMIT 1
            """, (date, symbol))

            row = cursor.fetchone()
            if not row:
                return None

            return {
                'date': row[0],
                'open': float(row[1]),
                'high': float(row[2]),
                'low': float(row[3]),
                'close': float(row[4]),
                'volume': float(row[5])
            }

        except Exception as e:
            logger.warning(f"Failed to fetch OHLCV data for {date}: {e}")
            return None

    def calculate_outcomes(self, eod_dates: List[str]) -> pd.DataFrame:
        """
        Calculate next-day outcome targets.

        Args:
            eod_dates: List of EOD dates (targets are for next trading day)

        Returns:
            DataFrame with binary materialization flags
        """
        outcomes_list = []

        # Get list of all trading dates for lookups
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT DISTINCT date FROM daily_gex_metrics
            WHERE symbol = 'SPY'
            ORDER BY date
        """)
        all_dates = sorted([row[0] for row in cursor.fetchall()])
        date_to_idx = {d: i for i, d in enumerate(all_dates)}

        for i, eod_date in enumerate(eod_dates):
            if (i + 1) % 50 == 0:
                logger.info(f"Computing outcomes for {i + 1}/{len(eod_dates)} dates...")

            # Get T+0 (EOD) and T+1 (next day) data
            eod_data = self.get_ohlcv(eod_date)

            # Find next trading date
            if eod_date not in date_to_idx:
                logger.warning(f"EOD date {eod_date} not in trading calendar")
                continue

            eod_idx = date_to_idx[eod_date]
            if eod_idx + 1 >= len(all_dates):
                logger.warning(f"No next trading day after {eod_date}")
                continue

            next_date = all_dates[eod_idx + 1]
            next_data = self.get_ohlcv(next_date)

            if not eod_data or not next_data:
                logger.warning(f"Missing OHLCV data for {eod_date} or {next_date}")
                continue

            outcomes = self._calculate_materialization_flags(eod_data, next_data)
            outcomes['date'] = eod_date
            outcomes_list.append(outcomes)

        df = pd.DataFrame(outcomes_list)
        logger.info(f"Calculated outcomes for {len(df)} dates")
        return df

    def _calculate_materialization_flags(self, eod_data: Dict, next_data: Dict) -> Dict:
        """
        Calculate binary materialization flags from OHLCV data.

        Args:
            eod_data: EOD (T+0) OHLCV dictionary
            next_data: Next day (T+1) OHLCV dictionary

        Returns:
            Dictionary with binary flags
        """
        # T+0 metrics
        close_t0 = eod_data['close']

        # T+1 metrics
        open_t1 = next_data['open']
        high_t1 = next_data['high']
        low_t1 = next_data['low']
        close_t1 = next_data['close']
        volume_t1 = next_data['volume']

        # Calculate derived metrics
        # 1. Return
        return_t1 = (close_t1 - close_t0) / close_t0
        abs_return_t1 = abs(return_t1)

        # 2. Range
        range_t1 = (high_t1 - low_t1) / open_t1

        # 3. Gap
        gap_t1 = abs(open_t1 - close_t0) / close_t0

        # 4. Volatility (simplified: use absolute return as proxy)
        realized_vol_t1 = abs_return_t1  # Simplified for daily data

        return {
            'high_volatility': 1 if realized_vol_t1 > 0.012 else 0,  # >1.2% move
            'range_expansion': 1 if range_t1 > 0.015 else 0,  # >1.5% range
            'directional_move': 1 if abs_return_t1 > 0.005 else 0,  # >0.5% absolute
            'gap_move': 1 if gap_t1 > 0.003 else 0,  # >0.3% gap
            'any_materialization': 1 if (realized_vol_t1 > 0.012 or
                                          range_t1 > 0.015 or
                                          abs_return_t1 > 0.005) else 0,
            # Continuous targets
            'return_pct': return_t1 * 100,
            'abs_return_pct': abs_return_t1 * 100,
            'range_pct': range_t1 * 100,
            'gap_pct': gap_t1 * 100,
            'volume': volume_t1
        }


class EODPredictiveAnalysis:
    """Main analysis orchestrator."""

    def __init__(self, output_dir: str = 'docs/papers/paper1/analysis'):
        """Initialize analysis."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Output directory: {self.output_dir}")

    def get_detection_dates(self) -> List[str]:
        """
        Load detection dates from Paper #1 validation YAML files.

        Returns:
            List of detection dates (YYYY-MM-DD)
        """
        dates = set()

        # Look for pattern validation YAML files
        pattern_dir = Path('reports/validation/paper1_pattern_taxonomy')
        if not pattern_dir.exists():
            logger.error(f"Pattern validation directory not found: {pattern_dir}")
            return []

        # Load gamma_positioning detections from 2024 (unbiased + biased)
        import glob
        yaml_files = glob.glob(str(pattern_dir / '*gamma_positioning*SPY*2024*.yaml'))

        logger.info(f"Found {len(yaml_files)} pattern YAML files")

        for yaml_file in yaml_files:
            try:
                with open(yaml_file, 'r') as f:
                    data = yaml.safe_load(f)

                if not data or 'detections' not in data:
                    continue

                for detection in data['detections']:
                    if detection.get('detected', False):
                        date = detection.get('date')
                        if date:
                            dates.add(date)
                logger.info(f"  Loaded {sum(1 for d in data.get('detections', []) if d.get('detected'))} detections from {Path(yaml_file).name}")

            except Exception as e:
                logger.warning(f"Failed to load {yaml_file}: {e}")

        return sorted(list(dates))

    def run_analysis(self):
        """Execute complete analysis pipeline."""
        logger.info("Starting EOD latent information analysis...")

        # Phase 1: Get detection dates
        logger.info("=== Phase 1: Loading detection dates ===")
        detection_dates = self.get_detection_dates()
        logger.info(f"Loaded {len(detection_dates)} detection dates")

        if not detection_dates:
            logger.error("No detection dates found. Cannot proceed.")
            return False

        # Phase 2: Extract EOD features
        logger.info("=== Phase 2: Extracting EOD features ===")
        feature_extractor = EODFeatureExtractor()
        feature_extractor.connect()
        try:
            eod_features = feature_extractor.extract_features(detection_dates)
            output_file = self.output_dir / 'issue_145_eod_features_2024.csv'
            eod_features.to_csv(output_file, index=False)
            logger.info(f"Saved EOD features to {output_file}")
        finally:
            feature_extractor.disconnect()

        # Phase 3: Calculate next-day outcomes
        logger.info("=== Phase 3: Calculating next-day outcomes ===")
        outcome_calculator = NextDayOutcomeCalculator()
        outcome_calculator.connect()
        try:
            # Use dates that have valid EOD features
            valid_dates = eod_features['date'].tolist()
            outcomes = outcome_calculator.calculate_outcomes(valid_dates)
            output_file = self.output_dir / 'issue_145_next_day_outcomes_2024.csv'
            outcomes.to_csv(output_file, index=False)
            logger.info(f"Saved next-day outcomes to {output_file}")
        finally:
            outcome_calculator.disconnect()

        # Phase 4: Summary statistics
        logger.info("=== Phase 4: Summary Statistics ===")
        self._print_summary_stats(eod_features, outcomes)

        # Phase 5: Train logistic regression
        logger.info("=== Phase 5: Logistic Regression Training ===")
        results = self._train_logistic_regression(eod_features, outcomes)

        if results:
            # Save results
            results_file = self.output_dir / 'issue_145_logistic_regression_results.yaml'
            import yaml
            with open(results_file, 'w') as f:
                yaml.dump(results, f, default_flow_style=False)
            logger.info(f"Saved logistic regression results to {results_file}")

        logger.info("Analysis complete!")
        return True

    def _print_summary_stats(self, features: pd.DataFrame, outcomes: pd.DataFrame):
        """Print summary statistics."""
        logger.info(f"\nEOD Features: {len(features)} dates, {len(features.columns)} features")
        logger.info(f"Next-day Outcomes: {len(outcomes)} dates")

        if len(outcomes) > 0:
            logger.info(f"\nOutcome materialization rates:")
            for col in ['any_materialization', 'high_volatility', 'range_expansion',
                       'directional_move', 'gap_move']:
                if col in outcomes.columns:
                    rate = outcomes[col].mean() * 100
                    logger.info(f"  {col}: {rate:.1f}%")

    def _train_logistic_regression(self, features: pd.DataFrame, outcomes: pd.DataFrame) -> Dict:
        """
        Train logistic regression model to predict T+1 materialization.

        Args:
            features: EOD feature DataFrame
            outcomes: Next-day outcome DataFrame

        Returns:
            Dictionary with model results and metrics
        """
        try:
            from sklearn.linear_model import LogisticRegression
            from sklearn.model_selection import TimeSeriesSplit, cross_val_score
            from sklearn.metrics import roc_auc_score, classification_report
            from sklearn.preprocessing import StandardScaler
        except ImportError:
            logger.error("scikit-learn not installed. Cannot train model.")
            return None

        # Merge features and outcomes on date
        merged = features.merge(outcomes, on='date', how='inner')
        logger.info(f"Merged dataset: {len(merged)} rows")

        # Feature columns (exclude date and target-related columns)
        feature_cols = ['total_gex', 'gex_sign', 'gex_oi', 'gex_volume',
                       'activity_ratio', 'zero_gamma_proximity', 'spot_above_flip',
                       'intraday_range', 'close_open_change', 'spot_price']

        # Check which columns exist
        available_features = [c for c in feature_cols if c in merged.columns]
        logger.info(f"Using features: {available_features}")

        # Prepare data
        X = merged[available_features].copy()
        y = merged['any_materialization'].copy()

        # Handle missing values
        X = X.fillna(0)

        # Scale features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # Time-series cross-validation (5 folds)
        tscv = TimeSeriesSplit(n_splits=5)

        # Train model
        model = LogisticRegression(
            penalty='l2',
            C=1.0,
            solver='lbfgs',
            max_iter=1000,
            random_state=42
        )

        # Cross-validated AUC scores
        auc_scores = []
        for fold, (train_idx, test_idx) in enumerate(tscv.split(X_scaled)):
            X_train, X_test = X_scaled[train_idx], X_scaled[test_idx]
            y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

            model.fit(X_train, y_train)
            y_pred_proba = model.predict_proba(X_test)[:, 1]

            # Calculate AUC
            try:
                auc = roc_auc_score(y_test, y_pred_proba)
                auc_scores.append(auc)
                logger.info(f"  Fold {fold + 1}: AUC = {auc:.4f}")
            except ValueError as e:
                logger.warning(f"  Fold {fold + 1}: Could not calculate AUC - {e}")

        # Final model on all data
        model.fit(X_scaled, y)
        y_pred_proba_full = model.predict_proba(X_scaled)[:, 1]

        try:
            full_auc = roc_auc_score(y, y_pred_proba_full)
        except ValueError:
            full_auc = 0.0

        # Calculate mean and std of CV AUC
        mean_auc = np.mean(auc_scores) if auc_scores else 0.0
        std_auc = np.std(auc_scores) if auc_scores else 0.0

        logger.info(f"\n=== Logistic Regression Results ===")
        logger.info(f"Mean CV AUC: {mean_auc:.4f} (+/- {std_auc:.4f})")
        logger.info(f"Full model AUC: {full_auc:.4f}")

        # Feature coefficients
        coef_dict = {f: float(c) for f, c in zip(available_features, model.coef_[0])}
        sorted_coef = sorted(coef_dict.items(), key=lambda x: abs(x[1]), reverse=True)

        logger.info(f"\nTop 5 features by coefficient magnitude:")
        for i, (feat, coef) in enumerate(sorted_coef[:5]):
            logger.info(f"  {i+1}. {feat}: {coef:.4f}")

        # Evaluate defense success criteria
        defense_status = "MINIMUM" if mean_auc > 0.60 else "FAILED"
        if mean_auc > 0.70:
            defense_status = "STRONG"
        if mean_auc > 0.75:
            defense_status = "OPTIMAL"

        logger.info(f"\n=== Defense Status: {defense_status} ===")
        logger.info(f"Target: AUC > 0.60 (minimum), > 0.70 (strong), > 0.75 (optimal)")

        return {
            'model_type': 'LogisticRegression',
            'n_samples': len(merged),
            'n_features': len(available_features),
            'features_used': available_features,
            'target': 'any_materialization',
            'cv_folds': 5,
            'cv_auc_scores': [float(s) for s in auc_scores],
            'mean_cv_auc': float(mean_auc),
            'std_cv_auc': float(std_auc),
            'full_model_auc': float(full_auc),
            'feature_coefficients': coef_dict,
            'top_features': [(f, float(c)) for f, c in sorted_coef[:5]],
            'defense_status': defense_status,
            'success_criteria': {
                'minimum': 0.60,
                'strong': 0.70,
                'optimal': 0.75,
                'achieved': float(mean_auc)
            }
        }


def main():
    """Main entry point."""
    try:
        analysis = EODPredictiveAnalysis()
        success = analysis.run_analysis()
        return 0 if success else 1

    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    exit(main())
