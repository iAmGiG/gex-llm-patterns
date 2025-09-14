"""
Options Data Normalization System
Standardizes options data from various sources into a unified schema for GEX analysis.
"""

import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from dataclasses import dataclass
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class OptionType(Enum):
    """Standardized option types."""
    CALL = "call"
    PUT = "put"


class DataSource(Enum):
    """Supported data sources."""
    ALPHA_VANTAGE = "alpha_vantage"
    CBOE = "cboe"
    IEX_CLOUD = "iex_cloud"
    CSV_FILE = "csv_file"
    SAMPLE_DATA = "sample_data"


@dataclass
class NormalizationConfig:
    """Configuration for options data normalization."""
    precision_rules: Dict[str, int]
    quality_weights: Dict[str, float]
    validation_thresholds: Dict[str, float]
    enable_derived_fields: bool = True
    strict_validation: bool = False


# Standard Options Schema Definition
STANDARD_OPTIONS_SCHEMA = {
    # Identifiers
    'contract_id': 'str',
    'symbol': 'str',
    'trading_date': 'datetime64[ns]',
    'expiration': 'datetime64[ns]',
    'strike': 'float64',
    'option_type': 'str',  # 'call' or 'put'

    # Pricing Data
    'last_price': 'float64',
    'mark_price': 'float64',
    'bid': 'float64',
    'ask': 'float64',
    'bid_size': 'int64',
    'ask_size': 'int64',

    # Volume and Interest
    'volume': 'int64',
    'open_interest': 'int64',

    # Greeks
    'implied_volatility': 'float64',
    'delta': 'float64',
    'gamma': 'float64',
    'theta': 'float64',
    'vega': 'float64',
    'rho': 'float64',

    # Derived Fields (calculated during normalization)
    'mid_price': 'float64',
    'spread': 'float64',
    'spread_pct': 'float64',
    'time_to_expiry': 'float64',
    'moneyness': 'float64',
    'vol_oi_ratio': 'float64',
    'intrinsic_value': 'float64',
    'time_value': 'float64',

    # Quality Flags
    'data_quality_score': 'float64',
    'has_pricing': 'bool',
    'has_greeks': 'bool',
    'has_volume': 'bool',
    'validation_flags': 'object'  # List of validation issues
}

# Field mappings for different data sources
ALPHA_VANTAGE_FIELD_MAPPING = {
    'contractID': 'contract_id',
    'symbol': 'symbol',
    'date': 'trading_date',
    'expiration': 'expiration',
    'strike': 'strike',
    'type': 'option_type',
    'last': 'last_price',
    'mark': 'mark_price',
    'bid': 'bid',
    'ask': 'ask',
    'bid_size': 'bid_size',
    'ask_size': 'ask_size',
    'volume': 'volume',
    'open_interest': 'open_interest',
    'implied_volatility': 'implied_volatility',
    'delta': 'delta',
    'gamma': 'gamma',
    'theta': 'theta',
    'vega': 'vega',
    'rho': 'rho'
}

# Default precision rules
DEFAULT_PRECISION_RULES = {
    'strike': 2,
    'prices': 2,
    'implied_volatility': 4,
    'greeks': 5,
    'ratios': 3,
    'percentages': 2
}

# Default quality weights for scoring
DEFAULT_QUALITY_WEIGHTS = {
    'pricing': 0.40,  # Valid bid/ask
    'greeks': 0.30,   # Complete Greeks
    'volume': 0.20,   # Non-zero volume
    'base': 0.10      # Base score for having contract
}

# Standardization rules for common fields
STANDARDIZATION_RULES = {
    'option_type': {
        'call': ['call', 'Call', 'CALL', 'C', 'c'],
        'put': ['put', 'Put', 'PUT', 'P', 'p']
    },
    'symbol': {
        'SPY': ['SPY', 'spy', 'SPDR'],
        'SPX': ['SPX', 'spx', '$SPX', 'SP500']
    }
}


class DataSourceAdapter(ABC):
    """Abstract base class for data source adapters."""

    @abstractmethod
    def parse_raw_data(self, raw_data: Any) -> pd.DataFrame:
        """Parse source-specific raw data into DataFrame."""
        pass

    @abstractmethod
    def get_field_mapping(self):
        """Get field mapping from source schema to standard schema."""
        pass

    @abstractmethod
    def apply_source_specific_processing(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply any source-specific data processing."""
        pass


class AlphaVantageAdapter(DataSourceAdapter):
    """Adapter for Alpha Vantage options data."""

    def parse_raw_data(self, raw_data: Any) -> pd.DataFrame:
        """Parse Alpha Vantage data format."""
        if isinstance(raw_data, dict) and 'data' in raw_data:
            return pd.DataFrame(raw_data['data'])
        elif isinstance(raw_data, pd.DataFrame):
            return raw_data
        elif isinstance(raw_data, list):
            return pd.DataFrame(raw_data)
        else:
            raise ValueError(
                f"Unsupported Alpha Vantage data format: {type(raw_data)}")

    def get_field_mapping(self):
        """Get Alpha Vantage field mapping."""
        return ALPHA_VANTAGE_FIELD_MAPPING

    def apply_source_specific_processing(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply Alpha Vantage specific processing."""
        # Handle contractID parsing if needed
        if 'contract_id' in df.columns and df['contract_id'].dtype == 'object':
            # Extract symbol, date, type, strike from contract ID if not already present
            if 'symbol' not in df.columns:
                df['symbol'] = df['contract_id'].str.extract(r'^([A-Z]+)')

        return df


class SampleDataAdapter(DataSourceAdapter):
    """Adapter for our sample/test data."""

    def parse_raw_data(self, raw_data: Any) -> pd.DataFrame:
        """Parse sample data format (already in DataFrame usually)."""
        if isinstance(raw_data, pd.DataFrame):
            return raw_data
        elif isinstance(raw_data, list):
            return pd.DataFrame(raw_data)
        else:
            raise ValueError(
                f"Unsupported sample data format: {type(raw_data)}")

    def get_field_mapping(self):
        """Sample data field mapping - much of it already matches standard schema."""
        # Map sample data field names to standard schema
        return {
            'contractID': 'contract_id',
            'type': 'option_type',
            'date': 'trading_date',
            'last': 'last_price',
            'mark': 'mark_price'
            # Most other fields like bid, ask, volume, etc. already match
        }

    def apply_source_specific_processing(self, df: pd.DataFrame) -> pd.DataFrame:
        """No special processing needed for sample data."""
        return df


class DerivedFieldCalculator:
    """Calculates derived fields for options data."""

    def __init__(self, precision_rules: Dict[str, int]):
        self.precision_rules = precision_rules

    def calculate_pricing_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate pricing-related derived fields."""
        df = df.copy()

        # Mid price
        df['mid_price'] = (df['bid'] + df['ask']) / 2

        # Spread calculations
        df['spread'] = df['ask'] - df['bid']
        df['spread_pct'] = np.where(
            df['mid_price'] > 0,
            (df['spread'] / df['mid_price'] * 100),
            0
        )

        # Round to appropriate precision
        price_precision = self.precision_rules.get('prices', 2)
        pct_precision = self.precision_rules.get('percentages', 2)

        df['mid_price'] = df['mid_price'].round(price_precision)
        df['spread'] = df['spread'].round(price_precision)
        df['spread_pct'] = df['spread_pct'].round(pct_precision)

        return df

    def calculate_moneyness_fields(self, df: pd.DataFrame,
                                   underlying_price) -> pd.DataFrame:
        """Calculate moneyness and intrinsic value fields."""
        if underlying_price is None or underlying_price <= 0:
            logger.warning(
                "Invalid underlying price, skipping moneyness calculations")
            df['moneyness'] = np.nan
            df['intrinsic_value'] = np.nan
            df['time_value'] = np.nan
            return df

        df = df.copy()

        # Moneyness
        df['moneyness'] = df['strike'] / underlying_price

        # Intrinsic value calculation
        calls_mask = df['option_type'] == 'call'
        puts_mask = df['option_type'] == 'put'

        df['intrinsic_value'] = 0.0
        df.loc[calls_mask, 'intrinsic_value'] = np.maximum(
            underlying_price - df.loc[calls_mask, 'strike'], 0)
        df.loc[puts_mask, 'intrinsic_value'] = np.maximum(
            df.loc[puts_mask, 'strike'] - underlying_price, 0)

        # Time value (using mark price as fair value)
        df['time_value'] = df['mark_price'] - df['intrinsic_value']

        # Round to appropriate precision
        ratio_precision = self.precision_rules.get('ratios', 3)
        price_precision = self.precision_rules.get('prices', 2)

        df['moneyness'] = df['moneyness'].round(ratio_precision)
        df['intrinsic_value'] = df['intrinsic_value'].round(price_precision)
        df['time_value'] = df['time_value'].round(price_precision)

        return df

    def calculate_activity_ratios(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate volume and activity-related ratios."""
        df = df.copy()

        # Volume to open interest ratio
        df['vol_oi_ratio'] = np.where(
            df['open_interest'] > 0,
            df['volume'] / df['open_interest'],
            # Infinite ratio for new contracts
            np.where(df['volume'] > 0, np.inf, 0)
        )

        # Round to appropriate precision
        ratio_precision = self.precision_rules.get('ratios', 3)
        df['vol_oi_ratio'] = df['vol_oi_ratio'].replace(
            [np.inf], 999.999).round(ratio_precision)

        return df

    def calculate_time_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate time-related fields."""
        df = df.copy()

        # Time to expiry in days
        df['time_to_expiry'] = (df['expiration'] - df['trading_date']).dt.days

        # Handle negative time to expiry (expired options)
        df['time_to_expiry'] = np.maximum(df['time_to_expiry'], 0)

        return df


class QualityAssessment:
    """Assesses data quality and assigns quality scores."""

    def __init__(self, quality_weights: Dict[str, float]):
        self.weights = quality_weights

    def assess_data_completeness(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add data quality flags and scores."""
        df = df.copy()

        # Pricing quality
        df['has_pricing'] = (
            (df['bid'] >= 0) &
            (df['ask'] > 0) &
            (df['bid'] <= df['ask']) &
            (df['ask'] - df['bid'] < df['ask'] * 0.5)  # Spread < 50% of ask
        )

        # Greeks completeness
        greek_columns = ['delta', 'gamma',
                         'theta', 'vega', 'implied_volatility']
        available_greeks = [col for col in greek_columns if col in df.columns]
        if available_greeks:
            df['has_greeks'] = df[available_greeks].notna().all(axis=1)
        else:
            df['has_greeks'] = False

        # Volume activity
        df['has_volume'] = df['volume'] > 0

        # Calculate overall quality score (0-100)
        quality_score = 0.0
        quality_score += df['has_pricing'].astype(
            float) * (self.weights['pricing'] * 100)
        quality_score += df['has_greeks'].astype(
            float) * (self.weights['greeks'] * 100)
        quality_score += df['has_volume'].astype(
            float) * (self.weights['volume'] * 100)
        quality_score += self.weights['base'] * 100  # Base score

        df['data_quality_score'] = quality_score.round(1)

        return df

    def add_validation_flags(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add validation flags for data issues."""
        df = df.copy()
        validation_flags = []

        for idx, row in df.iterrows():
            flags = []

            # Pricing validation
            if row['bid'] < 0:
                flags.append('negative_bid')
            if row['ask'] <= 0:
                flags.append('invalid_ask')
            if row['bid'] > row['ask']:
                flags.append('inverted_spread')

            # Greeks validation
            if 'delta' in df.columns and not np.isnan(row['delta']):
                if row['option_type'] == 'call' and (row['delta'] < 0 or row['delta'] > 1):
                    flags.append('invalid_call_delta')
                elif row['option_type'] == 'put' and (row['delta'] < -1 or row['delta'] > 0):
                    flags.append('invalid_put_delta')

            if 'implied_volatility' in df.columns and not np.isnan(row['implied_volatility']):
                if row['implied_volatility'] < 0 or row['implied_volatility'] > 5:  # 500% max IV
                    flags.append('extreme_iv')

            # Time validation
            if row['time_to_expiry'] < 0:
                flags.append('expired_option')

            validation_flags.append(flags)

        df['validation_flags'] = validation_flags
        return df


class OptionsDataNormalizer:
    """Main options data normalization engine."""

    def __init__(self, config=None):
        """Initialize the normalizer with configuration."""
        if config is None:
            config = NormalizationConfig(
                precision_rules=DEFAULT_PRECISION_RULES,
                quality_weights=DEFAULT_QUALITY_WEIGHTS,
                validation_thresholds={},
                enable_derived_fields=True,
                strict_validation=False
            )

        self.config = config
        self.field_calculator = DerivedFieldCalculator(config.precision_rules)
        self.quality_assessor = QualityAssessment(config.quality_weights)

        # Initialize adapters
        self.adapters = {
            DataSource.ALPHA_VANTAGE: AlphaVantageAdapter(),
            DataSource.SAMPLE_DATA: SampleDataAdapter()
        }

    def register_adapter(self, source: DataSource, adapter: DataSourceAdapter):
        """Register a new data source adapter."""
        self.adapters[source] = adapter

    def normalize_options_data(self,
                               raw_data: Any,
                               source: Union[DataSource, str],
                               underlying_price=None,
                               symbol=None):
        """
        Normalize options data from any supported source.

        Args:
            raw_data: Raw data in source-specific format
            source: Data source identifier
            underlying_price: Current underlying price for calculations
            symbol: Symbol override if not in data

        Returns:
            Tuple of (normalized_dataframe, metadata_dict)
        """
        # Convert string source to enum
        if isinstance(source, str):
            try:
                source = DataSource(source)
            except ValueError:
                raise ValueError(f"Unsupported data source: {source}")

        if source not in self.adapters:
            raise ValueError(f"No adapter registered for source: {source}")

        adapter = self.adapters[source]
        metadata = {
            'source': source.value,
            'processing_steps': [],
            'warnings': [],
            'errors': []
        }

        try:
            # Step 1: Parse raw data
            parsed_data = adapter.parse_raw_data(raw_data)
            metadata['processing_steps'].append('parse_raw_data')
            metadata['input_contracts'] = len(parsed_data)

            if parsed_data.empty:
                return self._create_empty_normalized_df(), metadata

            # Step 2: Apply field mapping
            mapped_data = self._apply_field_mapping(
                parsed_data, adapter.get_field_mapping())
            metadata['processing_steps'].append('apply_field_mapping')

            # Step 3: Apply source-specific processing
            processed_data = adapter.apply_source_specific_processing(
                mapped_data)
            metadata['processing_steps'].append('source_specific_processing')

            # Step 4: Standardize data types
            typed_data = self._standardize_types(processed_data)
            metadata['processing_steps'].append('standardize_types')

            # Step 5: Standardize field values
            standardized_data = self._standardize_field_values(typed_data)
            metadata['processing_steps'].append('standardize_field_values')

            # Add symbol if provided and not present
            if symbol and 'symbol' in standardized_data.columns:
                standardized_data['symbol'] = symbol

            # Step 6: Calculate derived fields
            if self.config.enable_derived_fields:
                enriched_data = self._calculate_derived_fields(
                    standardized_data, underlying_price)
                metadata['processing_steps'].append('calculate_derived_fields')
            else:
                enriched_data = standardized_data

            # Step 7: Apply quality assessment
            quality_data = self.quality_assessor.assess_data_completeness(
                enriched_data)
            quality_data = self.quality_assessor.add_validation_flags(
                quality_data)
            metadata['processing_steps'].append('quality_assessment')

            # Step 8: Apply standard sorting and indexing
            final_data = self._apply_standard_sorting(quality_data)
            metadata['processing_steps'].append('standard_sorting')

            # Update metadata
            metadata['output_contracts'] = len(final_data)
            metadata['avg_quality_score'] = final_data['data_quality_score'].mean(
            ) if 'data_quality_score' in final_data.columns else 0

            logger.info(f"Normalized {metadata['input_contracts']} contracts from {source.value} "
                        f"(avg quality: {metadata['avg_quality_score']:.1f})")

            return final_data, metadata

        except Exception as e:
            error_msg = f"Normalization failed for {source.value}: {str(e)}"
            metadata['errors'].append(error_msg)
            logger.error(error_msg)
            raise

    def _apply_field_mapping(self, df: pd.DataFrame, field_mapping: Dict[str, str]) -> pd.DataFrame:
        """Apply field mapping from source schema to standard schema."""
        mapped_df = df.copy()

        # Rename columns according to mapping
        rename_dict = {old: new for old,
                       new in field_mapping.items() if old in mapped_df.columns}
        mapped_df = mapped_df.rename(columns=rename_dict)

        return mapped_df

    def _standardize_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize data types according to schema."""
        typed_df = df.copy()

        for field, dtype in STANDARD_OPTIONS_SCHEMA.items():
            if field in typed_df.columns:
                try:
                    if dtype.startswith('datetime'):
                        typed_df[field] = pd.to_datetime(
                            typed_df[field], utc=True)
                    elif dtype.startswith('float'):
                        typed_df[field] = pd.to_numeric(
                            typed_df[field], errors='coerce')
                    elif dtype.startswith('int'):
                        typed_df[field] = pd.to_numeric(
                            typed_df[field], errors='coerce', downcast='integer')
                    elif dtype == 'bool':
                        typed_df[field] = typed_df[field].astype(bool)
                    elif dtype == 'str':
                        typed_df[field] = typed_df[field].astype(str)
                except Exception as e:
                    logger.warning(
                        f"Failed to convert {field} to {dtype}: {e}")

        return typed_df

    def _standardize_field_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize field values according to standardization rules."""
        standardized_df = df.copy()

        for field, rules in STANDARDIZATION_RULES.items():
            if field in standardized_df.columns:
                for standard_value, variants in rules.items():
                    mask = standardized_df[field].isin(variants)
                    standardized_df.loc[mask, field] = standard_value

        return standardized_df

    def _calculate_derived_fields(self, df: pd.DataFrame, underlying_price: Optional[float]) -> pd.DataFrame:
        """Calculate all derived fields."""
        enriched_df = df.copy()

        # Pricing fields
        enriched_df = self.field_calculator.calculate_pricing_fields(
            enriched_df)

        # Time fields
        enriched_df = self.field_calculator.calculate_time_fields(enriched_df)

        # Activity ratios
        enriched_df = self.field_calculator.calculate_activity_ratios(
            enriched_df)

        # Moneyness fields (if underlying price available)
        if underlying_price is not None:
            enriched_df = self.field_calculator.calculate_moneyness_fields(
                enriched_df, underlying_price)

        return enriched_df

    def _apply_standard_sorting(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply standard sorting and indexing."""
        sorted_df = df.copy()

        # Standard sort order: option_type, expiration, strike
        sort_columns = []
        if 'option_type' in sorted_df.columns:
            sort_columns.append('option_type')
        if 'expiration' in sorted_df.columns:
            sort_columns.append('expiration')
        if 'strike' in sorted_df.columns:
            sort_columns.append('strike')

        if sort_columns:
            sorted_df = sorted_df.sort_values(sort_columns)

        # Reset index
        sorted_df = sorted_df.reset_index(drop=True)

        return sorted_df

    def _create_empty_normalized_df(self) -> pd.DataFrame:
        """Create empty DataFrame with standard schema."""
        return pd.DataFrame({field: pd.Series(dtype=dtype)
                             for field, dtype in STANDARD_OPTIONS_SCHEMA.items()})
