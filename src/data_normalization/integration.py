"""
Integration utilities for connecting options normalization with existing systems.
"""

import pandas as pd
import logging
from typing import Any
try:
    from ..validation.options_data_validator import OptionsDataValidator
    from ..cache.unified_cache import UnifiedCacheManager
except ImportError:
    # Handle when running as standalone script
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent))

    from validation.options_data_validator import OptionsDataValidator
    from cache.unified_cache import UnifiedCacheManager

logger = logging.getLogger(__name__)


class NormalizedDataPipeline:
    """
    Integrated pipeline for normalized options data processing.
    Combines normalization, validation, and caching.
    """

    def __init__(self,
                 normalizer_config=None,
                 cache_manager=None,
                 enable_validation: bool = True):
        """
        Initialize the integrated pipeline.

        Args:
            normalizer_config: Configuration for data normalization
            cache_manager: Cache manager instance
            enable_validation: Whether to run validation after normalization
        """
        self.normalizer = OptionsDataNormalizer(normalizer_config)
        self.cache_manager = cache_manager or UnifiedCacheManager()
        self.enable_validation = enable_validation

        if enable_validation:
            self.validator = OptionsDataValidator(strict_mode=False)

    def process_options_data(self,
                             raw_data: Any,
                             source,
                             symbol,
                             trading_date,
                             underlying_price=None,
                             cache_result: bool = True,
                             cache_format: str = "pickle"):
        """
        Process options data through the complete pipeline.

        Args:
            raw_data: Raw options data from source
            source: Data source identifier
            symbol: Stock symbol
            trading_date: Trading date (YYYY-MM-DD)
            underlying_price: Current underlying price
            cache_result: Whether to cache normalized data
            cache_format: Cache storage format

        Returns:
            Processing results dictionary
        """
        result = {
            'success': False,
            'symbol': symbol,
            'trading_date': trading_date,
            'source': source,
            'data': None,
            'normalization_metadata': {},
            'validation_report': {},
            'cache_status': 'not_attempted',
            'warnings': [],
            'errors': []
        }

        try:
            # Step 1: Normalize data
            logger.info(
                f"Normalizing {symbol} options data from {source} for {trading_date}")

            normalized_df, norm_metadata = self.normalizer.normalize_options_data(
                raw_data=raw_data,
                source=source,
                underlying_price=underlying_price,
                symbol=symbol
            )

            result['data'] = normalized_df
            result['normalization_metadata'] = norm_metadata

            if normalized_df.empty:
                result['warnings'].append(
                    "Normalization produced empty dataset")
                return result

            # Step 2: Validation (if enabled)
            if self.enable_validation:
                logger.info(f"Validating normalized data for {symbol}")

                # Create a copy with fields mapped back for validation
                validation_df = normalized_df.copy()

                # Map normalized field names back to what validator expects
                if 'option_type' in validation_df.columns and 'type' not in validation_df.columns:
                    validation_df['type'] = validation_df['option_type']
                if 'trading_date' in validation_df.columns and 'date' not in validation_df.columns:
                    validation_df['date'] = validation_df['trading_date']
                if 'contract_id' in validation_df.columns and 'contractID' not in validation_df.columns:
                    validation_df['contractID'] = validation_df['contract_id']

                validated_df, validation_report = self.validator.validate(
                    validation_df)

                # Map back to normalized schema
                if 'type' in validated_df.columns and 'option_type' not in validated_df.columns:
                    validated_df['option_type'] = validated_df['type']
                if 'date' in validated_df.columns and 'trading_date' not in validated_df.columns:
                    validated_df['trading_date'] = validated_df['date']
                if 'contractID' in validated_df.columns and 'contract_id' not in validated_df.columns:
                    validated_df['contract_id'] = validated_df['contractID']

                result['data'] = validated_df
                result['validation_report'] = validation_report

                if validation_report.get('dropped_rows', 0) > 0:
                    warning_msg = f"Validation dropped {validation_report['dropped_rows']} rows"
                    result['warnings'].append(warning_msg)
                    logger.warning(warning_msg)

            # Step 3: Cache normalized data (if requested)
            if cache_result and not result['data'].empty:
                try:
                    cache_success = self.cache_manager.store_options_data(
                        symbol=symbol,
                        trading_date=trading_date,
                        df=result['data'],
                        format_type=cache_format
                    )

                    result['cache_status'] = 'success' if cache_success else 'failed'

                    if cache_success:
                        logger.info(
                            f"Cached normalized data for {symbol} {trading_date} ({cache_format})")
                    else:
                        result['warnings'].append(
                            f"Failed to cache normalized data")

                except Exception as e:
                    result['cache_status'] = 'error'
                    result['warnings'].append(f"Cache error: {str(e)}")
                    logger.warning(
                        f"Cache error for {symbol} {trading_date}: {e}")

            # Success
            result['success'] = True

            # Add summary statistics
            result['summary'] = {
                'contract_count': len(result['data']),
                'avg_quality_score': result['data']['data_quality_score'].mean() if 'data_quality_score' in result['data'].columns else 0,
                'has_pricing_pct': (result['data']['has_pricing'].sum() / len(result['data']) * 100) if 'has_pricing' in result['data'].columns else 0,
                'has_greeks_pct': (result['data']['has_greeks'].sum() / len(result['data']) * 100) if 'has_greeks' in result['data'].columns else 0,
                'unique_expirations': result['data']['expiration'].nunique() if 'expiration' in result['data'].columns else 0,
                'strike_range': {
                    'min': float(result['data']['strike'].min()) if 'strike' in result['data'].columns else 0,
                    'max': float(result['data']['strike'].max()) if 'strike' in result['data'].columns else 0
                } if 'strike' in result['data'].columns and len(result['data']) > 0 else {}
            }

            logger.info(f"Successfully processed {result['summary']['contract_count']} contracts "
                        f"(avg quality: {result['summary']['avg_quality_score']:.1f})")

        except Exception as e:
            error_msg = f"Pipeline processing failed: {str(e)}"
            result['errors'].append(error_msg)
            logger.error(error_msg)

        return result

    def process_cached_data(self,
                            symbol,
                            trading_date,
                            underlying_price=None,
                            reprocess_derived: bool = True):
        """
        Load and optionally reprocess cached options data.

        Args:
            symbol: Stock symbol
            trading_date: Trading date
            underlying_price: Underlying price for derived calculations
            reprocess_derived: Whether to recalculate derived fields

        Returns:
            Processing results dictionary
        """
        result = {
            'success': False,
            'symbol': symbol,
            'trading_date': trading_date,
            'source': 'cache',
            'data': None,
            'warnings': [],
            'errors': []
        }

        try:
            # Load from cache
            cached_df = self.cache_manager.get_options_data(
                symbol, trading_date)

            if cached_df is None:
                result['errors'].append(
                    f"No cached data found for {symbol} {trading_date}")
                return result

            if cached_df.empty:
                result['warnings'].append("Cached data is empty")
                result['data'] = cached_df
                return result

            result['data'] = cached_df

            # Optionally reprocess derived fields with new underlying price
            if reprocess_derived and underlying_price is not None:
                logger.info(
                    f"Reprocessing derived fields with underlying price {underlying_price}")

                enriched_df = self.normalizer.field_calculator.calculate_moneyness_fields(
                    cached_df, underlying_price
                )
                result['data'] = enriched_df

            result['success'] = True

            # Add summary
            result['summary'] = {
                'contract_count': len(result['data']),
                'from_cache': True,
                'reprocessed_derived': reprocess_derived and underlying_price is not None
            }

            logger.info(
                f"Loaded {len(result['data'])} cached contracts for {symbol} {trading_date}")

        except Exception as e:
            error_msg = f"Failed to process cached data: {str(e)}"
            result['errors'].append(error_msg)
            logger.error(error_msg)

        return result

    def get_pipeline_status(self):
        """Get status information about the pipeline."""
        cache_stats = self.cache_manager.get_options_cache_summary()

        return {
            'normalizer_config': {
                'enable_derived_fields': self.normalizer.config.enable_derived_fields,
                'strict_validation': self.normalizer.config.strict_validation,
                'precision_rules': self.normalizer.config.precision_rules,
                'quality_weights': self.normalizer.config.quality_weights
            },
            'validation_enabled': self.enable_validation,
            'cache_stats': cache_stats,
            'supported_sources': [source.value for source in self.normalizer.adapters.keys()]
        }


def process_alpha_vantage_options(raw_data: Any,
                                  symbol,
                                  trading_date,
                                  underlying_price=None):
    """
    Convenience function for processing Alpha Vantage options data.

    Args:
        raw_data: Raw Alpha Vantage options data
        symbol: Stock symbol
        trading_date: Trading date
        underlying_price: Underlying price for calculations

    Returns:
        Tuple of (normalized_dataframe, metadata)
    """
    pipeline = NormalizedDataPipeline()

    result = pipeline.process_options_data(
        raw_data=raw_data,
        source=DataSource.ALPHA_VANTAGE.value,
        symbol=symbol,
        trading_date=trading_date,
        underlying_price=underlying_price
    )

    if not result['success']:
        logger.error(
            f"Failed to process Alpha Vantage data: {result['errors']}")
        return pd.DataFrame(), result

    return result['data'], result


def process_sample_options_data(raw_data: Any,
                                symbol,
                                trading_date,
                                underlying_price=None):
    """
    Convenience function for processing sample/test options data.

    Args:
        raw_data: Raw sample options data
        symbol: Stock symbol  
        trading_date: Trading date
        underlying_price: Underlying price for calculations

    Returns:
        Tuple of (normalized_dataframe, metadata)
    """
    pipeline = NormalizedDataPipeline()

    result = pipeline.process_options_data(
        raw_data=raw_data,
        source=DataSource.SAMPLE_DATA.value,
        symbol=symbol,
        trading_date=trading_date,
        underlying_price=underlying_price
    )

    if not result['success']:
        logger.error(f"Failed to process sample data: {result['errors']}")
        return pd.DataFrame(), result

    return result['data'], result
