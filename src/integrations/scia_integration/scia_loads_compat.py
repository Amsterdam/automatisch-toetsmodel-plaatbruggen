"""
SCIA loads module - Backward compatibility layer.

This module provides backward compatibility by re-exporting functions from the
new focused modules. All load creation functions have been moved to specialized modules:

- scia_surface_loads.py: UDL and material surface loads
- scia_point_loads.py: Tandem and vehicle point loads
- scia_load_helpers.py: Utilities and orchestration

This module maintains the original API for existing code that imports from scia_loads.
"""

# Re-export all functions for backward compatibility
from src.geometry.load_zone_geometry import get_bridge_geom_data

# Re-export functions from other modules that tests need
from .scia_coordinate_utils import convert_loads_to_scia_format
from .scia_load_generators import extract_bridge_dimensions, generate_tandem_loads
from .scia_loads.scia_load_helpers import add_pedestrian_loads, create_all_loads
from .scia_loads.scia_point_loads import (
    add_accidental_vehicle_loads,
    add_actual_tandem_loads,
    add_service_vehicle_loads,
    add_theoretical_tandem_loads,
    dispersal_function,
)
from .scia_loads.scia_surface_loads import (
    add_asfalt_loads,
    add_concrete_fill_loads,
    add_crowd_loads,
    add_parapet_loads,
    add_pavement_loads,
    add_udl_loads,
)

# Re-export types for backward compatibility
from .types import AmsterdamWheelConfig, BridgeParametrization, WheelConfig

__all__ = [
    # Surface loads
    "add_udl_loads",
    "add_parapet_loads",
    "add_asfalt_loads",
    "add_concrete_fill_loads",
    "add_pavement_loads",
    "add_crowd_loads",
    # Point loads
    "add_theoretical_tandem_loads",
    "add_actual_tandem_loads",
    "add_service_vehicle_loads",
    "add_accidental_vehicle_loads",
    "dispersal_function",
    # Helpers
    "add_pedestrian_loads",
    "create_all_loads",
    # Functions from other modules (for test compatibility)
    "convert_loads_to_scia_format",
    "extract_bridge_dimensions",
    "generate_tandem_loads",
    "get_bridge_geom_data",
    # Types
    "WheelConfig",
    "AmsterdamWheelConfig",
    "BridgeParametrization",
]
