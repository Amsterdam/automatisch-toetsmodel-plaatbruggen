"""
Pydantic data models for the bridge analysis application.

This package contains all Pydantic data models used for data validation and type safety.
Data models are organized by domain to keep related validation logic together.

Usage:
    from src.data_models.bridge_models import BridgeSegmentDimensions
    from src.data_models.load_models import LoadZoneData
    from src.data_models.combination_models import LoadCombinationConfig
    from src.data_models.plotting_models import BridgeBaseGeometry
    from src.data_models.material_models import MaterialConfig
    from src.data_models.geometry_models import TheoreticalLaneResult
"""

# Import commonly used models for convenience
from .bridge_models import BridgeSegmentDimensions
from .combination_models import LoadCombinationConfig
from .geometry_models import TheoreticalLaneResult
from .load_models import LoadZoneData
from .material_models import MaterialConfig
from .plotting_models import (
    BridgeBaseGeometry,
    PlotPresentationDetails,
    ZoneBoundaryLineStyle,
    ZonePlottingGeometry,
    ZoneStylingDefaults,
)

__all__ = [
    "BridgeBaseGeometry",
    "BridgeSegmentDimensions",
    "LoadCombinationConfig",
    "LoadZoneData",
    "MaterialConfig",
    "PlotPresentationDetails",
    "TheoreticalLaneResult",
    "ZoneBoundaryLineStyle",
    "ZonePlottingGeometry",
    "ZoneStylingDefaults",
]
