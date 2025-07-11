"""
Module for creating SCIA load definitions.

This module provides functions for creating definitions of SCIA loads, load cases, and load combinations.
These definitions are pure Python objects that can be used by the app layer to construct the actual SCIA model.
"""

from typing import Any

from .scia_definitions import SurfaceLoadDefinition
from .scia_load_cases import create_tandem_rs_load_cases

# Import definition-based creators


def create_patch_surface_load(
    load_case_name: str,
    corner_points: list[tuple[float, float, float]],
    load_value: float,
    load_name: str = "PatchLoad",
) -> SurfaceLoadDefinition:
    """
    Create a definition for a free surface load on a 4-point patch.

    :param load_case_name: Name of the load case for the load application.
    :param corner_points: List of 4 corner coordinates [(x1,y1,z1), ...].
    :param load_value: Load magnitude in [N/m²] (positive = downward).
    :param load_name: Name identifier for the load.
    :return: A SurfaceLoadDefinition object.
    :rtype: SurfaceLoadDefinition
    """
    if len(corner_points) != 4:
        raise ValueError(f"Exactly 4 corner points required, got {len(corner_points)}")

    return SurfaceLoadDefinition(
        name=load_name,
        load_case_name=load_case_name,
        corner_points=corner_points,
        load_value=load_value,
    )


def add_theoretical_tandem_loads(
    params: Any,  # noqa: ANN401
    _traffic_group_name: str,
) -> dict[str, list]:
    """
    Create definitions for theoretical tandem loads and their load cases.

    :param params: VIKTOR parameters for the bridge.
    :param _traffic_group_name: The name of the traffic load group (unused, maintained for signature consistency).
    :return: A dict with "load_case_definitions" and "surface_load_definitions".
    :rtype: dict[str, list]
    """
    from src.loads.loadcase_helper_functions import generate_theoretical_lane_positions

    from .scia_bridge_geometry import (
        convert_tandem_data_to_scia_format,
        extract_tandem_parameters_from_bridge,
        generate_tandem_loads_for_bridge,
    )

    # 1. Extract bridge parameters for tandem loads
    bridge_params = extract_tandem_parameters_from_bridge(params)
    length = bridge_params["length"]
    thickness = bridge_params["thickness"]
    width = bridge_params["width"]

    # 2. Determine number of lanes and create load case definitions
    num_lanes = len(generate_theoretical_lane_positions(width))
    num_lanes = min(num_lanes, 3)

    load_case_definitions = []
    for rs in range(1, num_lanes + 1):
        load_case_definitions.extend(create_tandem_rs_load_cases(rs, length, thickness))

    # 3. Generate tandem loads based on theoretical lanes
    raw_tandem_data = generate_tandem_loads_for_bridge(bridge_params, mode="theoretical")

    # 4. Convert tandem data to SCIA format for surface loads
    scia_tandem_data = convert_tandem_data_to_scia_format(raw_tandem_data)

    # 5. Create surface load definitions from scia_tandem_data
    surface_load_definitions = []
    for tandem in scia_tandem_data:
        load_case_name = tandem["load_case"]
        for i, patch_load in enumerate(tandem["patch_loads"]):
            surface_load_definitions.append(
                create_patch_surface_load(
                    load_case_name,
                    patch_load["corners"],
                    -patch_load["load_value"],
                    f"{load_case_name}_Wheel_{i + 1}",
                )
            )

    return {"load_case_definitions": load_case_definitions, "surface_load_definitions": surface_load_definitions}


"""Add actual tandem loads based on user-defined lanes."""


def add_actual_tandem_loads(
    _model: Any,  # noqa: ANN401
    _params: Any,  # noqa: ANN401
    _traffic_group: Any,  # noqa: ANN401
) -> list[Any]:
    """PLACEHOLDER: Add actual tandem loads based on user-defined lanes."""
    # TODO: Implement logic for actual tandem loads
    # - Extract actual lane positions from params
    # - Generate tandem loads for those lanes
    # - Apply to model
    return []


"""Add railing loads to the SCIA model."""


def add_railing_loads(
    _model: Any,  # noqa: ANN401
    _params: Any,  # noqa: ANN401
    _permanent_group: Any,  # noqa: ANN401
) -> list[Any]:
    """PLACEHOLDER: Add railing loads to the SCIA model."""
    # TODO: Implement railing load application
    # - Get railing positions from geometry
    # - Apply line loads along railing paths
    return []


"""Add pedestrian loads to the SCIA model."""


def add_pedestrian_loads(
    _model: Any,  # noqa: ANN401
    _params: Any,  # noqa: ANN401
    _traffic_group: Any,  # noqa: ANN401
) -> list[Any]:
    """PLACEHOLDER: Add pedestrian loads to the SCIA model."""
    # TODO: Implement pedestrian load application
    # - Get pedestrian zone polygons
    # - Apply surface loads to pedestrian areas
    return []
