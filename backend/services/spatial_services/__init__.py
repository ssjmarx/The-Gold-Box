"""
Spatial Services Package for The Gold Box
Provides spatial awareness and scene filtering capabilities
"""

from .scene_spatial_filter import SceneSpatialFilter, parse_distance_unit, DistanceUnit

__all__ = [
    'SceneSpatialFilter',
    'parse_distance_unit',
    'DistanceUnit'
]
