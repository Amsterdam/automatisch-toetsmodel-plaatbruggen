"""
Module for creating SCIA loads.

This module provides functions for creating SCIA loads by calling the SciaModelBuilder.
These functions are pure Python and can be used by the app layer to construct the actual SCIA model.
"""

from typing import Any

from .scia_bridge_geometry import (
    convert_tandem_data_to_scia_format,
    extract_tandem_parameters_from_bridge,
    generate_tandem_loads_for_bridge,
)
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
            builder.create_surface_load(
                name=f"{load_case_name}_Wheel_{i + 1}",
                load_case_name=load_case_name,
                corner_points=patch_load["corners"],
                load_value=-patch_load["load_value"],  # Negative for downward load
            )


def add_dead_loads(
    builder: SciaModelBuilder,
    params: Any,  # noqa: ANN401
) -> None:
    """
    Add dead loads (permanent loads) to the SCIA model.

    This function applies uniform surface loads for asphalt, filling, and other permanent loads.
    Load values are based on typical Dutch bridge construction standards.

    :param builder: The SCIA model builder instance.
    :param params: VIKTOR parameters for the bridge.
    """
    # Extract bridge dimensions for load application
    bridge_params = extract_tandem_parameters_from_bridge(params)

    # Get bridge geometry bounds for full-surface loads
    length = bridge_params["length_bridgedeck"]
    width = bridge_params["width_bridgedeck"]

    # Define corner points for full bridge surface (assuming bridge starts at origin)
    full_bridge_corners = [
        (0.0, 0.0, 0.0),  # Bottom-left
        (length, 0.0, 0.0),  # Bottom-right
        (length, width, 0.0),  # Top-right
        (0.0, width, 0.0),  # Top-left
    ]

    # Define dead load values (kN/m²) - typical values for Dutch bridges
    dead_load_values = {
        "BG2001": 2.4,  # Asphalt: ~2.4 kN/m² (100mm asphalt @ 24 kN/m³)
        "BG2002": 1.0,  # Filling: ~1.0 kN/m² (50mm filling @ 20 kN/m³)
        "BG2003": 0.5,  # Sidewalk/kerb: ~0.5 kN/m² (distributed over full area)
        "BG2004": 0.1,  # Railing: ~0.1 kN/m² (distributed over full area)
        "BG2005": 0.05,  # Light poles: ~0.05 kN/m² (distributed over full area)
    }

    # Apply dead loads to their respective load cases
    for load_case_name, load_value in dead_load_values.items():
        builder.create_surface_load(
            name=f"{load_case_name}_Dead_Load",
            load_case_name=load_case_name,
            corner_points=full_bridge_corners,
            load_value=-load_value,  # Negative for downward load
        )


def add_pedestrian_loads(
    builder: SciaModelBuilder,
    params: Any,  # noqa: ANN401
) -> None:
    """
    Add pedestrian loads (LM4) to the SCIA model.

    This function applies uniform surface loads for pedestrian loading according to EN 1991-2.
    Standard pedestrian load is 5.0 kN/m² over the loaded area.

    :param builder: The SCIA model builder instance.
    :param params: VIKTOR parameters for the bridge.
    """
    # Extract bridge dimensions
    bridge_params = extract_tandem_parameters_from_bridge(params)

    # Get bridge geometry bounds
    length = bridge_params["length_bridgedeck"]
    width = bridge_params["width_bridgedeck"]

    # Define corner points for full bridge surface
    full_bridge_corners = [
        (0.0, 0.0, 0.0),  # Bottom-left
        (length, 0.0, 0.0),  # Bottom-right
        (length, width, 0.0),  # Top-right
        (0.0, width, 0.0),  # Top-left
    ]

    # Apply pedestrian load (5.0 kN/m² according to EN 1991-2)
    builder.create_surface_load(
        name="BG5001_Pedestrian_Load",
        load_case_name="BG5001",
        corner_points=full_bridge_corners,
        load_value=-5.0,  # Negative for downward load
    )


def add_temperature_loads(
    builder: SciaModelBuilder,
    params: Any,  # noqa: ANN401
) -> None:
    """
    Add temperature loads to the SCIA model.

    Temperature loads are typically applied as thermal actions rather than surface loads.
    This is a placeholder implementation that demonstrates the pattern.
    In practice, temperature loads would be applied as thermal gradients or uniform temperature changes.

    :param builder: The SCIA model builder instance.
    :param params: VIKTOR parameters for the bridge.
    """
    # NOTE: Temperature loads are typically applied as thermal actions in SCIA,
    # not as surface loads. This would require additional builder methods.
    # For now, we'll skip temperature load application.
    # TODO: Implement temperature load application when thermal action methods are available


def add_udl_traffic_loads(
    builder: SciaModelBuilder,
    params: Any,  # noqa: ANN401
) -> None:
    """
    Add UDL (Uniformly Distributed Load) traffic loads to the SCIA model.

    These loads represent the distributed component of LM1 traffic loading.
    Load values depend on the roadway configuration and lane positions.

    :param builder: The SCIA model builder instance.
    :param params: VIKTOR parameters for the bridge.
    """
    # Extract bridge dimensions
    bridge_params = extract_tandem_parameters_from_bridge(params)

    # Get bridge geometry bounds
    length = bridge_params["length_bridgedeck"]
    width = bridge_params["width_bridgedeck"]

    # Define UDL values for different road systems (kN/m²)
    # Based on EN 1991-2 for LM1 loading
    udl_values = {
        "BG4001": 9.0,  # LM1 UDL RS 1: 9.0 kN/m² (first lane)
        "BG4002": 2.5,  # LM1 UDL RS 2: 2.5 kN/m² (second lane)
        "BG4003": 2.5,  # LM1 UDL RS 3: 2.5 kN/m² (third lane)
        "BG4004": 2.5,  # LM1 UDL rest: 2.5 kN/m² (remaining area)
    }

    # For simplicity, apply UDL over full bridge area
    # In practice, these would be applied to specific lane areas
    full_bridge_corners = [
        (0.0, 0.0, 0.0),  # Bottom-left
        (length, 0.0, 0.0),  # Bottom-right
        (length, width, 0.0),  # Top-right
        (0.0, width, 0.0),  # Top-left
    ]

    # Apply UDL loads to their respective load cases
    for load_case_name, load_value in udl_values.items():
        builder.create_surface_load(
            name=f"{load_case_name}_UDL_Load",
            load_case_name=load_case_name,
            corner_points=full_bridge_corners,
            load_value=-load_value,  # Negative for downward load
        )


def add_actual_tandem_loads(
    _builder: SciaModelBuilder,
    _params: Any,  # noqa: ANN401
) -> list[Any]:
    """PLACEHOLDER: Add actual tandem loads based on user-defined lanes."""
    # This will be implemented when user-defined lanes are supported.
    return []


def add_railing_loads(
    builder: SciaModelBuilder,
    params: Any,  # noqa: ANN401
) -> None:
    """
    Add railing loads to the SCIA model as line loads.

    Railing loads are typically applied as line loads along the bridge edges.
    Standard railing load is 1.0 kN/m according to EN 1991-2.

    :param builder: The SCIA model builder instance.
    :param params: VIKTOR parameters for the bridge.
    """
    # Extract bridge dimensions
    bridge_params = extract_tandem_parameters_from_bridge(params)

    # Get bridge geometry bounds
    length = bridge_params["length_bridgedeck"]
    width = bridge_params["width_bridgedeck"]

    # Define railing load value (kN/m)
    railing_load_value = 1.0

    # Apply railing loads along both edges of the bridge
    # Left edge (y = 0)
    builder.create_free_line_load(
        name="BG2004_Railing_Left",
        load_case_name="BG2004",
        point_1=(0.0, 0.0),
        point_2=(length, 0.0),
        load_value=-railing_load_value,  # Negative for downward load
        direction="Z",
    )

    # Right edge (y = width)
    builder.create_free_line_load(
        name="BG2004_Railing_Right",
        load_case_name="BG2004",
        point_1=(0.0, width),
        point_2=(length, width),
        load_value=-railing_load_value,  # Negative for downward load
        direction="Z",
    )


def create_all_loads(builder: SciaModelBuilder, params: Any) -> None:  # noqa: ANN401
    """
    Create and apply all load types to the bridge model.

    This function orchestrates the application of all loads, including:
    - Self-weight loads (automatic in SCIA for SELF_WEIGHT load cases)
    - Dead loads (asphalt, filling, sidewalk, railing, light poles)
    - Tandem system loads (theoretical lanes)
    - Pedestrian loads (LM4)
    - UDL traffic loads (LM1 distributed loads)
    - Railing loads (line loads along edges)

    :param builder: The SCIA model builder instance.
    :param params: Bridge parameters.
    """
    # NOTE: Self-weight loads are automatically applied by SCIA for load cases
    # with permanent_type="SELF_WEIGHT", so no explicit load application needed for BG1001

    # Apply dead loads (permanent loads)
    add_dead_loads(builder, params)

    # Apply theoretical tandem loads
    add_theoretical_tandem_loads(builder, params)

    # Apply pedestrian loads
    add_pedestrian_loads(builder, params)

    # Apply UDL traffic loads
    add_udl_traffic_loads(builder, params)

    # Apply railing loads as line loads
    add_railing_loads(builder, params)

    # Apply temperature loads (placeholder for now)
    add_temperature_loads(builder, params)

    # TODO: Add calls to other load functions when they are implemented
    # add_actual_tandem_loads(builder, params)  # noqa: ERA001
