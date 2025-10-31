"""
Material load application helpers for SCIA model building.

This module provides functions for creating and adding material surface loads
to SCIA models based on pavement material properties.
"""

from typing import TYPE_CHECKING, Any

from src.data_models.geometry_data_models import LoadZoneGeometryData
from src.geometry.load_zone_geometry import calculate_zone_geometry_properties, get_bridge_geom_data, get_load_zones_data_from_params
from src.integrations.scia_integration.constants.units import KN_PER_SQM_TO_N_PER_SQM
from src.integrations.scia_integration.load_system.load_value_calculators import calculate_pavement_load_from_material

if TYPE_CHECKING:
    from app.bridge.parametrization import BridgeParametrization
    from src.integrations.scia_integration.model.scia_model_interface import SciaModelBuilder


# This function is used to create the load cases 2001/2002/2003
def create_material_surface_load(
    builder: "SciaModelBuilder",
    load_config: dict[str, Any],
    bridge_geom_data: LoadZoneGeometryData,
) -> None:
    """
    Create a surface load for a specific material in a load zone span.

    :param builder: SCIA model builder instance
    :param load_config: Configuration containing all load parameters:
        - load_zone: Load zone data containing coordinates and properties
        - zone_index: Index of the load zone
        - span: Span index within the load zone
        - material_name: Name of the material for load naming
        - load_case_name: Name of the load case to apply the load to
    :param bridge_geom_data: Bridge geometry data
    """
    # Extract parameters from load_config
    load_zone = load_config["load_zone"]
    zone_index = load_config["zone_index"]
    span = load_config["span"]
    material_name = load_config["material_name"]
    load_case_name = load_config["load_case_name"]

    # Calculate coordinates for the surface load
    y_coord_top_left = round(getattr(load_zone, "y_coords_top_current_zone", [])[span], 2)
    y_coord_top_right = round(getattr(load_zone, "y_coords_top_current_zone", [])[span + 1], 2)
    y_coord_bottom_left = round(y_coord_top_left - getattr(load_zone, "zone_widths_per_d", [])[span], 2)
    y_coord_bottom_right = round(y_coord_top_right - getattr(load_zone, "zone_widths_per_d", [])[span + 1], 2)
    x_coord_left = round(bridge_geom_data.x_coords_d_points[span], 2)
    x_coord_right = round(bridge_geom_data.x_coords_d_points[span + 1], 2)

    corners = [
        (x_coord_left, y_coord_top_left, 0.0),
        (x_coord_right, y_coord_top_right, 0.0),
        (x_coord_right, y_coord_bottom_right, 0.0),
        (x_coord_left, y_coord_bottom_left, 0.0),
    ]

    builder.create_surface_load(
        name=f"{load_zone.zone_type}_{zone_index}_{material_name}_{span}_d{load_zone.pavement_thickness}",
        load_case_name=load_case_name,
        corner_points=corners,
        load_value=-calculate_pavement_load_from_material(load_zone.pavement_thickness, load_zone.pavement_material)
        * KN_PER_SQM_TO_N_PER_SQM,  # Convert to kN/m²
    )


# This function is used to create the load cases 2001/2002/2003
def add_material_loads(
    builder: "SciaModelBuilder",
    params: "BridgeParametrization",
    material_config: dict[str, str],
) -> None:
    """
    Add surface loads for specified materials to the SCIA model.

    :param builder: SCIA model builder instance
    :param params: Bridge parameters
    :param material_config: Dictionary mapping material names to their load case names
    """
    # Get load zone information from params using the utility functions
    load_zones_data_params = get_load_zones_data_from_params(params)
    bridge_geom_data = get_bridge_geom_data(params)

    # Check if bridge geometry data is available
    if bridge_geom_data is None:
        return

    # Update load zones data with geometry properties
    load_zones_data_params = calculate_zone_geometry_properties(load_zones_data_params, bridge_geom_data)

    # Iterate through load zones and apply loads for specified materials
    for i, load_zone in enumerate(load_zones_data_params):
        pavement_material = getattr(load_zone, "pavement_material", "")

        if pavement_material in material_config:
            load_case_name = material_config[pavement_material]
            # Clean material name for use in load naming
            material_name = pavement_material.replace(" ", "_").replace("(", "").replace(")", "").lower()

            # Iterate through spans
            for span in range(len(getattr(load_zone, "y_coords_top_current_zone", [])) - 1):
                load_config = {
                    "load_zone": load_zone,
                    "zone_index": i,
                    "span": span,
                    "material_name": material_name,
                    "load_case_name": load_case_name,
                }

                create_material_surface_load(builder, load_config, bridge_geom_data)
