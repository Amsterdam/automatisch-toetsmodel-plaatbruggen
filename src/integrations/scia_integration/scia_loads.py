"""
Module for creating SCIA loads.

This module provides functions for creating SCIA loads by calling the SciaModelBuilder.
These functions are pure Python and can be used by the app layer to construct the actual SCIA model.
"""

from typing import Any

from app.bridge.parametrization import BridgeParametrization
from src.geometry.load_zone_geometry import get_bridge_geom_data

from .scia_bridge_geometry import (
    convert_tandem_data_to_scia_format,
    extract_tandem_parameters_from_bridge,
    generate_tandem_loads_for_bridge,
)
from .scia_loads_helper import add_material_loads
from .scia_model_interface import SciaModelBuilder


def add_theoretical_tandem_loads(
    builder: SciaModelBuilder,
    params: Any,  # noqa: ANN401
) -> None:
    """
    Create theoretical tandem loads and apply them to their existing load cases.

    This function assumes that the required load cases have already been created
    by `create_all_load_cases`.

    :param builder: The SCIA model builder instance.
    :param params: VIKTOR parameters for the bridge.
    """
    # 1. Extract bridge parameters needed for load geometry calculation
    bridge_params = extract_tandem_parameters_from_bridge(params)

    # 2. Generate tandem loads based on theoretical lanes
    raw_tandem_data = generate_tandem_loads_for_bridge(bridge_params, mode="theoretical")

    # 3. Convert tandem data to SCIA format for surface loads
    scia_tandem_data = convert_tandem_data_to_scia_format(raw_tandem_data)

    # 4. Create surface loads using the builder, applying them to the correct load case
    for tandem in scia_tandem_data:
        load_case_name = tandem["load_case"]
        for i, patch_load in enumerate(tandem["patch_loads"]):
            # volgens code dksokf, moeten we ,
            corner_points_dispersed, load_value_dispersed = dispersal_function(patch_load["corners"], patch_load["load_value"], BridgeParametrization=bridge_params)

            builder.create_surface_load(
                name=f"{load_case_name}_Wheel_{i + 1}",
                load_case_name=load_case_name,
                corner_points=corner_points_dispersed,
                load_value=-load_value_dispersed,  # Negative for downward load
            )
                
def dispersal_function(corner_points, load_value, BridgeParametrization: BridgeParametrization) -> tuple[list[tuple[float, float, float]], float]:
    """
    Disperse the load value across the corners based on the bridge parameters.

        # Only process dicts that have both 'load_case' and 'patch_loads' keys
        if "load_case" in tandem and "patch_loads" in tandem:
            load_case_name = tandem["load_case"]
            for i, patch_load in enumerate(tandem["patch_loads"]):
                builder.create_surface_load(
                    name=f"{load_case_name}_Wheel_{i + 1}",
                    load_case_name=load_case_name,
                    corner_points=patch_load["corners"],
                    load_value=-patch_load["load_value"],  # Negative for downward load
                )

    :param corner_points: List of corner points for the load.
    :param load_value: Load value to be dispersed.
    :param bridge_params: Bridge parameters for dispersal logic.
    :return: Tuple of dispersed corner points and adjusted load value.
    """
    # Placeholder logic for dispersal function
    # This should be replaced with actual logic based on bridge geometry
    dispersed_corners = corner_points  # No change in corners for now
    dispersed_load_value = load_value  # No change in load value for now

    for coordinate in dispersed_corners:
        layer_properties = get_layer_properties_at_coordinate(coordinate)  # helper function from App layer that retrieves a dict of materials as keys and their thicknesses as values
        # logica om de belasting te spreiden over een groter bereik van de hoekpunten (dus de corners verder uit elkaar) op basis van dikte van de brug en diktes van de toplaag

    # constructieve dikte brug
    # Materiaal van het brugdek (asfalt en beton bv)
    # Spreidingshoeken materialen uit de normen
    # Afmeting per wiel (breedte, lengte)
    # Is het TS (twee richginten) of UDL (één richting)


    return dispersed_corners, dispersed_load_value

def add_actual_tandem_loads(
    _builder: SciaModelBuilder,
    _params: Any,  # noqa: ANN401
) -> list[Any]:
    """PLACEHOLDER: Add actual tandem loads based on user-defined lanes."""
    # This will be implemented when user-defined lanes are supported.
    return []


def add_parapet_loads(
    builder: SciaModelBuilder,
    params: Any,  # noqa: ANN401
) -> list[Any]:
    """
    Add permanent line loads for parapets (railing) to the SCIA model.

    Places line loads:
    - On edge 1 of all zone 3 plates (Z3)
    - On edge 3 of all zone 1 plates (Z1)

    :param builder: SCIA model builder instance
    :param params: Bridge parameters (should provide plate_definitions)
    """
    try:
        load_value = params.input.belastingzones.lijnlast_leuning * 1000  # Convert to kN/m
    except AttributeError:
        load_value = 1000  # Fallback default if not present

    load_case_name = "BG2004"

    # builder.plates is now a dict: {plate_name: Plane}
    plates = getattr(builder, "plates", {})
    for plate_name, _plane in plates.items():  # noqa: PERF102
        # Expect plate_name like 'Z1_1', 'Z3_2', etc.
        try:
            zone_part = plate_name.split("_")[0]  # e.g., 'Z1'
            zone_number = int(zone_part[1:])
        except (IndexError, ValueError):
            continue
        if zone_number == 3:
            builder.create_line_load_on_plane(
                name=f"parapet_load_zone3_{plate_name}",
                load_case_name=load_case_name,
                plane_name=plate_name,
                edge_index=3,
                load_value=-load_value,
            )
        elif zone_number == 1:
            builder.create_line_load_on_plane(
                name=f"parapet_load_zone1_{plate_name}",
                load_case_name=load_case_name,
                plane_name=plate_name,
                edge_index=1,
                load_value=-load_value,
            )
    return []


def add_pedestrian_loads(
    _builder: SciaModelBuilder,
    _params: Any,  # noqa: ANN401
) -> list[Any]:
    """PLACEHOLDER: Add pedestrian loads to the SCIA model."""
    # This will be implemented based on pedestrian area parameters.
    return []


def add_asfalt_loads(
    builder: SciaModelBuilder,
    params: BridgeParametrization,
) -> list[Any]:
    """Add asphalt loads to the SCIA model."""
    material_config = {"Asfalt": "BG2001"}  # TODO is dit correct?
    add_material_loads(builder, params, material_config)
    return []


def add_concrete_fill_loads(
    builder: SciaModelBuilder,
    params: BridgeParametrization,
) -> list[Any]:
    """Add concrete fill loads to the SCIA model."""
    material_config = {
        "Beton (normaal)": "BG2002",  # TODO is dit correct?
        "Beton (gewapend)": "BG2002",  # TODO is dit correct?
    }
    add_material_loads(builder, params, material_config)
    return []


def add_pavement_loads(
    builder: SciaModelBuilder,
    params: BridgeParametrization,
) -> list[Any]:
    """Add pavement loads (klinkers, grind, tegels) to the SCIA model."""
    material_config = {
        "Klinkers": "BG2003",
        "Grind": "BG2003",
        "Tegels": "BG2003",
    }
    add_material_loads(builder, params, material_config)
    return []


def add_crowd_loads(
    builder: SciaModelBuilder,
    params: BridgeParametrization,
) -> list[Any]:
    """PLACEHOLDER: Add crowd loads to the SCIA model."""
    # Get unit weight for crowd loads

    # Get load zone information from params using the utility functions
    bridge_geom_data = get_bridge_geom_data(params)

    # Check if bridge geometry data is available
    if bridge_geom_data is None:
        return []

    y_top = bridge_geom_data.y_top_structural_edge_at_d_points[0]
    y_bottom = bridge_geom_data.y_bridge_bottom_at_d_points[0]
    x_left = bridge_geom_data.x_coords_d_points[0]
    x_right = bridge_geom_data.x_coords_d_points[-1]

    corners = [
        (x_left, y_top, 0.0),
        (x_right, y_top, 0.0),
        (x_right, y_bottom, 0.0),
        (x_left, y_bottom, 0.0),
    ]

    builder.create_surface_load(
        name="mensenmenigte_belasting",
        load_case_name="BG5001",  # TODO is dit correct?
        corner_points=corners,
        load_value=-5 * 1000,  # Convert to kN/m²
    )
    return []  # Placeholder return to match function signature


def create_all_loads(builder: SciaModelBuilder, params: BridgeParametrization) -> None:
    """
    Create and apply all load types to the bridge model.

    This function orchestrates the application of all loads, including:
    - Tandem system loads
    - Railing loads (placeholder)
    - Pedestrian loads (placeholder)

    :param builder: The SCIA model builder instance.
    :param params: Bridge parameters.
    """
    # Apply theoretical tandem loads
    add_asfalt_loads(builder, params)
    add_concrete_fill_loads(builder, params)
    add_pavement_loads(builder, params)
    add_parapet_loads(builder, params)
    add_crowd_loads(builder, params)
    add_theoretical_tandem_loads(builder, params)

    # TODO: Add calls to other load functions when they are implemented
    # add_actual_tandem_loads(builder, params)  # noqa: ERA001
    # add_railing_loads(builder, params)  # noqa: ERA001
    # add_pedestrian_loads(builder, params)  # noqa: ERA001
