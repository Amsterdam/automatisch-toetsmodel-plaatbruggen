"""
SCIA loads package.

This package contains specialized modules for different types of SCIA loads:
- scia_surface_loads: UDL and material surface loads
- scia_point_loads: Tandem and vehicle point loads
- scia_load_helpers: Utilities and orchestration functions

The package provides a clean separation of concerns for load creation functionality.
"""

# Re-export main functions for backward compatibility
from src.geometry.load_zone_geometry import get_bridge_geom_data
from src.integrations.scia_integration.load_system.scia_load_generators import extract_bridge_dimensions, generate_tandem_loads

# Re-export functions from other modules that tests need
from src.integrations.scia_integration.model.scia_coordinate_utils import convert_loads_to_scia_format

# Re-export types for backward compatibility
# Note: WheelConfig and AmsterdamWheelConfig TypedDicts are deprecated.
# Use WheelLoadConfig and AmsterdamWheelLoadConfig from src.data_models.scia_models instead.
from src.integrations.scia_integration.types import BridgeParametrization

from .scia_load_helpers import add_pedestrian_loads, create_all_loads
from .scia_point_loads import (
    add_accidental_vehicle_loads,
    add_actual_tandem_loads,
    add_service_vehicle_loads,
    add_theoretical_tandem_loads,
    dispersal_function,
)
from .scia_surface_loads import (
    add_asfalt_loads,
    add_concrete_fill_loads,
    add_crowd_loads,
    add_parapet_loads,
    add_pavement_loads,
    add_udl_loads,
)
from .scia_temperature_loads import add_temperature_loads

__all__ = [
    "BridgeParametrization",
    "add_accidental_vehicle_loads",
    "add_actual_tandem_loads",
    "add_asfalt_loads",
    "add_concrete_fill_loads",
    "add_crowd_loads",
    "add_parapet_loads",
    "add_pavement_loads",
    "add_pedestrian_loads",
    "add_service_vehicle_loads",
    "add_temperature_loads",
    "add_theoretical_tandem_loads",
    "add_udl_loads",
    "convert_loads_to_scia_format",
    "create_all_loads",
    "dispersal_function",
    "extract_bridge_dimensions",
    "generate_tandem_loads",
    "get_bridge_geom_data",
]
