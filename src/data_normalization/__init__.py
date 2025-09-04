"""
Data Normalization Package
Standardizes data from various sources into unified schemas for analysis.
"""

from .options_normalizer import (
    OptionsDataNormalizer,
    DataSourceAdapter,
    AlphaVantageAdapter,
    SampleDataAdapter,
    DerivedFieldCalculator,
    QualityAssessment,
    NormalizationConfig,
    OptionType,
    DataSource,
    STANDARD_OPTIONS_SCHEMA,
    ALPHA_VANTAGE_FIELD_MAPPING,
    DEFAULT_PRECISION_RULES,
    DEFAULT_QUALITY_WEIGHTS,
    STANDARDIZATION_RULES
)

from .integration import (
    NormalizedDataPipeline,
    process_alpha_vantage_options,
    process_sample_options_data
)

from .schemas import (
    OPTIONS_SCHEMA,
    MARKET_SCHEMA,
    NEWS_SCHEMA,
    ECONOMIC_SCHEMA,
    create_empty_options_df,
    create_empty_market_df,
    create_empty_news_df,
    create_empty_economic_df,
    standardize_indicator_columns,
    normalize_alpha_vantage_market_data,
    normalize_polygon_market_data,
    validate_schema
)

__all__ = [
    # Options normalization (existing)
    'OptionsDataNormalizer',
    'DataSourceAdapter', 
    'AlphaVantageAdapter',
    'SampleDataAdapter',
    'DerivedFieldCalculator',
    'QualityAssessment',
    'NormalizationConfig',
    'OptionType',
    'DataSource',
    'STANDARD_OPTIONS_SCHEMA',
    'ALPHA_VANTAGE_FIELD_MAPPING',
    'DEFAULT_PRECISION_RULES',
    'DEFAULT_QUALITY_WEIGHTS',
    'STANDARDIZATION_RULES',
    'NormalizedDataPipeline',
    'process_alpha_vantage_options',
    'process_sample_options_data',
    
    # Common schemas (new)
    'OPTIONS_SCHEMA',
    'MARKET_SCHEMA',
    'NEWS_SCHEMA',
    'ECONOMIC_SCHEMA',
    'create_empty_options_df',
    'create_empty_market_df',
    'create_empty_news_df',
    'create_empty_economic_df',
    'standardize_indicator_columns',
    'normalize_alpha_vantage_market_data',
    'normalize_polygon_market_data',
    'validate_schema'
]