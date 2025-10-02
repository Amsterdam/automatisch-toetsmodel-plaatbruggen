"""
SCIA surface loads module.

This module provides functions for creating surface loads (UDL and material loads)
by calling the SciaModelBuilder interface. These functions handle uniformly distributed
loads and material-based surface loads.
"""

from typing import Any

from src.geometry.load_zone_geometry import get_bridge_geom_data
from src.integrations.scia_integration.scia_load_generators import generate_udl_loads
from src.integrations.scia_integration.scia_model_interface import SciaModelBuilder
from src.integrations.scia_integration.types import BridgeParametrization


def add_udl_loads(
    builder: SciaModelBuilder,
    params: Any,  # noqa: ANN401
    load_cases: dict[str, Any],
) -> None:
    """
    Create UDL traffic loads with separate polygons for main lane (9 kN/m²), other notional lanes (2.5 kN/m²),
    and remaining areas (2.5 kN/m²). Applied to load cases BG4001, BG4002, BG4003.

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

        # Convert from our standard format back to the expected format
        udl_results: dict[str, dict[str, Any]] = {}
        for load_data in udl_load_list:
            load_case = load_data["load_case"]
            # Extract the BG group from load_case (e.g., "BG4001_main" -> "BG4001")
            bg_group = load_case.split("_")[0]
            load_type = load_case.split("_")[1] if "_" in load_case else "main"

            if bg_group not in udl_results:
                udl_results[bg_group] = {"main": [], "other": [], "rest": []}

            udl_results[bg_group][load_type].append({"polygon": load_data["polygon"], "load": load_data["load_value"]})

        bg_to_rs = {"BG4001": "rs_1", "BG4002": "rs_2", "BG4003": "rs_3"}
        for key, udl in udl_results.items():
            rs_key = bg_to_rs.get(key)
            if rs_key and rs_key in load_cases["udl_traffic_cases"]:
                scia_case = load_cases["udl_traffic_cases"][rs_key]

                # Create surface loads for main notional lane(s)
                for i, main_load in enumerate(udl["main"]):
                    builder.create_surface_load(
                        name=f"udl_{key}_main_{i + 1}",
                        load_case_name=scia_case.name,
                        corner_points=main_load["polygon"],
                        load_value=-main_load["load"],
                    )

                # Create surface loads for other notional lanes
                for i, other_load in enumerate(udl["other"]):
                    builder.create_surface_load(
                        name=f"udl_{key}_other_{i + 1}",
                        load_case_name=scia_case.name,
                        corner_points=other_load["polygon"],
                        load_value=-other_load["load"],
                    )

                # Create surface loads for remaining areas
                for i, rest_load in enumerate(udl["rest"]):
                    builder.create_surface_load(
                        name=f"udl_{key}_rest_{i + 1}",
                        load_case_name=scia_case.name,
                        corner_points=rest_load["polygon"],
                        load_value=-rest_load["load"],
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

        load_value = leuning_numeric * 1000  # Convert to N/m

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
        from src.integrations.scia_integration.scia_loads_helper import add_material_loads

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
        from src.integrations.scia_integration.scia_loads_helper import add_material_loads

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
        from src.integrations.scia_integration.scia_loads_helper import add_material_loads

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
        crowd_load_per_sqm = 5.0  # kN/m²
        crowd_load_per_sqm_n = crowd_load_per_sqm * 1000  # Convert to N/m²

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
