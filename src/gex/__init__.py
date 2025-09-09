"""
GEX Calculation Module

Core gamma exposure calculation engine for dealer positioning analysis.
Provides comprehensive GEX calculations, validation, and market regime analysis.
"""

from .calculator import GEXCalculator
from .validator import GEXValidator

# Legacy imports (existing modules)
try:
    from .flip_point_detector import FlipPointDetector
    from .level_aggregator import LevelAggregator
    from .gex_calculator import GEXCalculator as LegacyGEXCalculator
except ImportError:
    pass

__all__ = [
    'GEXCalculator', 
    'GEXValidator',
    'FlipPointDetector', 
    'LevelAggregator'
]