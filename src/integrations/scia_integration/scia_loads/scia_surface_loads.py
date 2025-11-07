"""
SCIA surface loads module.

This module provides functions for creating surface loads (UDL and material loads)
by calling the SciaModelBuilder interface. These functions handle uniformly distributed
loads and material-based surface loads.
"""

from typing import Any

from src.geometry.load_zone_geometry import get_bridge_geom_data
from src.integrations.scia_integration.constants import (
    CROWD_LOAD_PER_SQM_N,
    KN_PER_M_TO_N_PER_M,
)
from src.integrations.scia_integration.load_system.scia_load_generators import generate_udl_loads
from src.integrations.scia_integration.model.scia_model_interface import SciaModelBuilder
from src.integrations.scia_integration.types import BridgeParametrization


def add_udl_loads(
    builder: SciaModelBuilder,
    params: Any,  # noqa: ANN401
    load_cases: dict[str, Any],
) -> None:
    """
    Create UDL traffic loads with one polygon per load case.

    Each polygon is applied to its specific load case (BG4001, BG4002, etc.)
    as determined by the UDL generators. Each load case contains a single
    polygon with its associated load value and title.

    :param builder: The SCIA model builder instance
    :type builder: SciaModelBuilder
    :param params: VIKTOR parameters for the bridge
    :type params: Any
    :param load_cases: Dictionary of created load cases
    :type load_cases: dict[str, Any]
    :raises ValueError: When UDL generation fails
    """
    try:
        # Generate UDL loads - this will auto-detect mode from berekeningsniveau
        udl_load_list = generate_udl_loads(params)

        # Map each polygon to its specific load case
        for load_item in udl_load_list:
            load_case_name = load_item.get("load_case")
            if not load_case_name:
                continue

            # Find the corresponding SCIA load case
            if load_case_name in load_cases["udl_traffic_cases"]:
                scia_case = load_cases["udl_traffic_cases"][load_case_name]

                # Create surface load for this polygon on its specific load case
                builder.create_surface_load(
                    name=f"udl_{load_case_name}",
                    load_case_name=scia_case.name,
                    corner_points=load_item["polygon"],
                    load_value=-load_item["load_value"],
                )
    except Exception as e:
        raise ValueError(f"Failed to add UDL loads: {e}") from e


def add_parapet_loads(
    builder: SciaModelBuilder,
    params: Any,  # noqa: ANN401
    load_cases: dict[str, Any],
) -> list[Any]:
    """
    Add permanent line loads for parapets (railing) to the SCIA model.

    Places line loads:
    - On edge 1 of all zone 3 plates (Z3)
    - On edge 3 of all zone 1 plates (Z1)

    :param builder: SCIA model builder instance
    :type builder: SciaModelBuilder
    :param params: Bridge parameters (should provide plate_definitions)
    :type params: Any
    :param load_cases: Dictionary of created load cases
    :type load_cases: dict[str, Any]
    :returns: Empty list for compatibility
    :rtype: list[Any]
    :raises ValueError: When parapet load creation fails
    """
    try:
        # Get parapet line load value, defaulting to 0 if not specified
        try:
            leuning_value = params.input.belastingzones.lijnlast_leuning
            leuning_numeric = float(leuning_value) if leuning_value is not None else 0.0
        except (AttributeError, ValueError, TypeError):
            # If the parameter structure is missing or invalid, use default value
            leuning_numeric = 0.0

        load_value = leuning_numeric * KN_PER_M_TO_N_PER_M  # Convert to N/m

        # Get the parapet load case name from the load cases dictionary
        parapet_load_case = load_cases["dead_load_cases"]["leuning"]
        load_case_name = parapet_load_case.name

        # builder.plates is now a dict: {plate_name: Plane}
        plates = getattr(builder, "plates", {})
        if not isinstance(plates, dict):
            return []
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
    except Exception as e:
        raise ValueError(f"Failed to add parapet loads: {e}") from e
    else:
        return []


def add_asfalt_loads(
    builder: SciaModelBuilder,
    params: BridgeParametrization,
    load_cases: dict[str, Any],
) -> list[Any]:
    """
    Add asphalt loads to the SCIA model.

    :param builder: SCIA model builder instance
    :type builder: SciaModelBuilder
    :param params: Bridge parameters
    :type params: BridgeParametrization
    :param load_cases: Dictionary of created load cases
    :type load_cases: dict[str, Any]
    :returns: Empty list for compatibility
    :rtype: list[Any]
    :raises ValueError: When asphalt load creation fails
    """
    try:
        # Get the asphalt load case name from the load cases dictionary
        asphalt_load_case = load_cases["dead_load_cases"]["asfalt"]
        load_case_name = asphalt_load_case.name

        material_config = {"Asfalt": load_case_name}
        from src.integrations.scia_integration.scia_loads.material_load_helpers import add_material_loads

        add_material_loads(builder, params, material_config)
    except Exception as e:
        raise ValueError(f"Failed to add asphalt loads: {e}") from e
    else:
        return []


def add_concrete_fill_loads(
    builder: SciaModelBuilder,
    params: BridgeParametrization,
    load_cases: dict[str, Any],
) -> list[Any]:
    """
    Add concrete fill loads to the SCIA model.

    :param builder: SCIA model builder instance
    :type builder: SciaModelBuilder
    :param params: Bridge parameters
    :type params: BridgeParametrization
    :param load_cases: Dictionary of created load cases
    :type load_cases: dict[str, Any]
    :returns: Empty list for compatibility
    :rtype: list[Any]
    :raises ValueError: When concrete fill load creation fails
    """
    try:
        # Get the concrete fill load case name from the load cases dictionary
        concrete_fill_load_case = load_cases["dead_load_cases"]["uitvulling"]
        load_case_name = concrete_fill_load_case.name

        material_config = {
            "Beton (normaal)": load_case_name,
            "Beton (gewapend)": load_case_name,
        }
        from src.integrations.scia_integration.scia_loads.material_load_helpers import add_material_loads

        add_material_loads(builder, params, material_config)
    except Exception as e:
        raise ValueError(f"Failed to add concrete fill loads: {e}") from e
    else:
        return []


def add_pavement_loads(
    builder: SciaModelBuilder,
    params: BridgeParametrization,
    load_cases: dict[str, Any],
) -> list[Any]:
    """
    Add pavement loads (klinkers, grind, tegels) to the SCIA model.

    :param builder: SCIA model builder instance
    :type builder: SciaModelBuilder
    :param params: Bridge parameters
    :type params: BridgeParametrization
    :param load_cases: Dictionary of created load cases
    :type load_cases: dict[str, Any]
    :returns: Empty list for compatibility
    :rtype: list[Any]
    :raises ValueError: When pavement load creation fails
    """
    try:
        # Get the pavement load case name from the load cases dictionary
        pavement_load_case = load_cases["dead_load_cases"]["ophogingen"]
        load_case_name = pavement_load_case.name

        material_config = {
            "Klinkers": load_case_name,
            "Grind": load_case_name,
            "Tegels": load_case_name,
        }
        from src.integrations.scia_integration.scia_loads.material_load_helpers import add_material_loads

        add_material_loads(builder, params, material_config)
    except Exception as e:
        raise ValueError(f"Failed to add pavement loads: {e}") from e
    else:
        return []


def add_crowd_loads(
    builder: SciaModelBuilder,
    params: BridgeParametrization,
    load_cases: dict[str, Any],
) -> list[Any]:
    """
    Add crowd loads to the SCIA model according to NEN-EN 1991-2 art. 5.3.2.1 (LM4).

    :param builder: SCIA model builder instance
    :type builder: SciaModelBuilder
    :param params: Bridge parameters
    :type params: BridgeParametrization
    :param load_cases: Dictionary of created load cases
    :type load_cases: dict[str, Any]
    :returns: Empty list for compatibility
    :rtype: list[Any]
    :raises ValueError: When crowd load creation fails
    """
    try:
        # Crowd load according to NEN-EN 1991-2 art. 5.3.2.1 (LM4)
        crowd_load_per_sqm_n = CROWD_LOAD_PER_SQM_N

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

        # Get the pedestrian load case name from the load cases dictionary
        pedestrian_load_case = load_cases["pedestrian"]
        load_case_name = pedestrian_load_case.name

        builder.create_surface_load(
            name="mensenmenigte_belasting",
            load_case_name=load_case_name,
            corner_points=corners,
            load_value=-crowd_load_per_sqm_n,  # Negative for downward load
        )
    except Exception as e:
        raise ValueError(f"Failed to add crowd loads: {e}") from e
    else:
        return []  # Placeholder return to match function signature
