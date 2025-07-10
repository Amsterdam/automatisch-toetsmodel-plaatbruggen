"""
SCIA load application utilities.

This module handles the application of loads to SCIA models, focusing purely on load creation and application.
Showcases usage of dedicated modules: scia_load_cases.py, scia_load_combinations.py, and scia_load_group.py.

Functions that were moved to scia_bridge_geometry.py:
- extract_tandem_parameters_from_bridge
- determine_tandem_function_for_bridge
- generate_tandem_loads_for_bridge
- convert_wheel_coordinates_to_3d
- align_bridge_coordinates_to_scia
- convert_tandem_data_to_scia_format
"""

from typing import Any

# Global VIKTOR imports with error handling for CI/testing environments
try:
    from viktor.external import scia

    VIKTOR_AVAILABLE = True
except ImportError:
    # Mock objects for environments without VIKTOR SDK
    scia = None  # type: ignore[misc,assignment]
    VIKTOR_AVAILABLE = False

# Import geometry extraction functions from dedicated module
# PLACEHOLDER imports - these modules contain placeholder implementations
# that will be properly implemented by colleagues later
from src.integrations.scia_integration.scia_load_cases import (
    create_basic_permanent_load_cases,
    create_tandem_load_case,
    create_wind_load_case,
)
from src.integrations.scia_integration.scia_load_combinations import (
    create_basic_sls_combination,
    create_basic_uls_combination,
    create_wind_uls_combination,
)
from src.integrations.scia_integration.scia_load_group import (
    create_basic_load_groups,
)

from .scia_bridge_geometry import (
    convert_tandem_data_to_scia_format,
    extract_tandem_parameters_from_bridge,
    generate_tandem_loads_for_bridge,
)

# =============================================================================
# LOAD UTILITIES
# =============================================================================


def _check_scia_availability() -> None:
    """Check if SCIA module is available and raise ImportError if not."""
    if not VIKTOR_AVAILABLE or scia is None:
        raise ImportError("VIKTOR SCIA module not available. This function requires VIKTOR SDK.")


def create_patch_surface_load(
    model: Any,  # noqa: ANN401
    load_case: Any,  # noqa: ANN401
    corner_points: list[tuple[float, float, float]],
    load_value: float,
    load_name: str = "PatchLoad",
) -> Any:  # noqa: ANN401
    """
    Create free surface load on 4-point patch (XY-plane only).

    :param model: SCIA model instance
    :param load_case: SCIA load case for the load application
    :param corner_points: List of 4 corner coordinates [(x1,y1,z1), (x2,y2,z2), (x3,y3,z3), (x4,y4,z4)]
    :param load_value: Load magnitude in [N/m²] (positive = downward)
    :param load_name: Name identifier for the load
    :returns: SCIA free surface load object
    :rtype: Any
    :raises ValueError: When corner points count is not 4
    :raises ImportError: When VIKTOR SCIA module is not available
    """
    _check_scia_availability()

    if len(corner_points) != 4:
        raise ValueError(f"Exactly 4 corner points required, got {len(corner_points)}")

    # Convert 3D points to 2D (XY only) for free surface load
    xy_points = [(x, y) for x, y, z in corner_points]

    # Calculate patch area for load conversion from N/m² to total N
    # Using shoelace formula for polygon area
    def polygon_area(points: list[tuple[float, float]]) -> float:
        n = len(points)
        area = 0.0
        for i in range(n):
            j = (i + 1) % n
            area += points[i][0] * points[j][1]
            area -= points[j][0] * points[i][1]
        return abs(area) / 2.0

    patch_area = polygon_area(xy_points)
    total_load = load_value * patch_area  # Convert N/m² to N

    # Create free surface load with uniform distribution
    return model.create_free_surface_load(
        name=load_name,
        load_case=load_case,
        direction=scia.FreeSurfaceLoad.Direction.Z,
        q1=total_load,
        points=xy_points,
        distribution=scia.FreeSurfaceLoad.Distribution.UNIFORM,
    )


# =============================================================================
# INFRASTRUCTURE SETUP
# =============================================================================


def create_load_infrastructure(model: Any) -> dict[str, Any]:  # noqa: ANN401
    """
    Create basic load infrastructure: groups and fundamental load cases.

    Creates the foundation for all load applications using PLACEHOLDER functions:
    - Load groups (permanent, traffic, wind) via scia_load_group.py
    - Basic permanent load cases (self-weight) via scia_load_cases.py
    - Basic variable load cases (wind) via scia_load_cases.py

    NOTE: All imported functions are PLACEHOLDERS that will be properly
    implemented by colleagues later.

    :param model: SCIA model instance
    :returns: Dictionary with load_groups and basic_load_cases
    :rtype: dict[str, Any]
    """
    # Create load groups using PLACEHOLDER function
    load_groups = create_basic_load_groups(model)
    permanent_group = load_groups["permanent"]
    wind_group = load_groups["wind"]

    # Create basic load cases using PLACEHOLDER functions
    basic_load_cases = create_basic_load_cases(model, permanent_group, wind_group)

    return {
        "load_groups": load_groups,
        "basic_load_cases": basic_load_cases,
    }


def create_basic_load_cases(
    model: Any,  # noqa: ANN401
    permanent_group: Any,  # noqa: ANN401
    wind_group: Any,  # noqa: ANN401
) -> dict[str, Any]:
    """
    Create basic load cases using provided load groups.

    Creates fundamental load cases using PLACEHOLDER functions:
    - Self-weight (permanent) via scia_load_cases.py
    - Wind (variable) via scia_load_cases.py

    NOTE: All imported functions are PLACEHOLDERS that will be properly
    implemented by colleagues later.

    :param model: SCIA model instance
    :param permanent_group: SCIA permanent load group
    :param wind_group: SCIA wind load group
    :returns: Dictionary with basic load cases
    :rtype: dict[str, Any]
    """
    # Create basic permanent load cases using PLACEHOLDER function
    permanent_load_cases = create_basic_permanent_load_cases(model, permanent_group)
    self_weight_case = permanent_load_cases["self_weight"]

    # Create wind load case using PLACEHOLDER function
    wind_case = create_wind_load_case(model, wind_group)

    return {
        "self_weight": self_weight_case,
        "wind": wind_case,
    }


# =============================================================================
# SPECIFIC LOAD ADDITION FUNCTIONS
# =============================================================================


def add_theoretical_tandem_loads(
    model: Any,  # noqa: ANN401
    params: Any,  # noqa: ANN401
    traffic_group: Any,  # noqa: ANN401
) -> list[Any]:
    """
    Add theoretical tandem loads to SCIA model.

    Creates tandem load cases with theoretical lane positions and applies
    the corresponding wheel loads to each case.

    Uses PLACEHOLDER function create_tandem_load_case() from scia_load_cases.py
    that will be properly implemented by colleagues later.

    :param model: SCIA model instance
    :param params: Bridge parameters
    :param traffic_group: SCIA traffic load group
    :returns: List of created tandem load cases
    :rtype: list[Any]
    """
    # Extract geometry and generate tandem data
    bridge_params = extract_tandem_parameters_from_bridge(params)
    tandem_mode = "theoretical"

    # Generate tandem loads using bridge geometry
    raw_tandem_data = generate_tandem_loads_for_bridge(bridge_params, mode=tandem_mode)
    scia_tandem_data = convert_tandem_data_to_scia_format(raw_tandem_data)

    # Create tandem load cases and apply loads
    tandem_load_cases = []

    for load_case_data in scia_tandem_data:
        load_case_name = load_case_data["load_case"]
        patch_loads = load_case_data["patch_loads"]

        # Create load case using PLACEHOLDER function
        load_case = create_tandem_load_case(model, traffic_group, load_case_name, tandem_mode)

        # Apply all patch loads for this load case
        for i, patch_load in enumerate(patch_loads):
            corners = patch_load["corners"]
            load_value = patch_load["load_value"]
            load_name = f"{load_case_name}_Wheel_{i + 1}"

            # Apply loads as negative values to point downward (correct direction for bridge loads)
            create_patch_surface_load(model, load_case, corners, -load_value, load_name)

        tandem_load_cases.append(load_case)

    return tandem_load_cases


def add_actual_tandem_loads(
    _model: Any,  # noqa: ANN401
    _params: Any,  # noqa: ANN401
    _traffic_group: Any,  # noqa: ANN401
) -> list[Any]:
    """
    Add actual tandem loads to SCIA model.

    PLACEHOLDER: Creates tandem load cases with actual lane positions.

    :param _model: SCIA model instance (unused in placeholder)
    :param _params: Bridge parameters (unused in placeholder)
    :param _traffic_group: SCIA traffic load group (unused in placeholder)
    :returns: List of created tandem load cases
    :rtype: list[Any]
    """
    # TODO: Implement actual tandem load logic
    return []


def add_railing_loads(
    _model: Any,  # noqa: ANN401
    _params: Any,  # noqa: ANN401
    _permanent_group: Any,  # noqa: ANN401
) -> list[Any]:
    """
    Add railing loads to SCIA model.

    PLACEHOLDER: Creates load cases for railing dead loads.

    :param _model: SCIA model instance (unused in placeholder)
    :param _params: Bridge parameters (unused in placeholder)
    :param _permanent_group: SCIA permanent load group (unused in placeholder)
    :returns: List of created railing load cases
    :rtype: list[Any]
    """
    # TODO: Implement railing load logic
    return []


def add_pedestrian_loads(
    _model: Any,  # noqa: ANN401
    _params: Any,  # noqa: ANN401
    _traffic_group: Any,  # noqa: ANN401
) -> list[Any]:
    """
    Add pedestrian loads to SCIA model.

    PLACEHOLDER: Creates load cases for pedestrian traffic loads.

    :param _model: SCIA model instance (unused in placeholder)
    :param _params: Bridge parameters (unused in placeholder)
    :param _traffic_group: SCIA traffic load group (unused in placeholder)
    :returns: List of created pedestrian load cases
    :rtype: list[Any]
    """
    # TODO: Implement pedestrian load logic
    return []


# =============================================================================
# LOAD COMBINATIONS
# =============================================================================


def create_standard_load_combinations(
    model: Any,  # noqa: ANN401
    self_weight_case: Any,  # noqa: ANN401
    wind_case: Any,  # noqa: ANN401
    tandem_load_cases: list[Any],
) -> dict[str, Any]:
    """
    Create standard load combinations for bridge analysis.

    Creates ULS and SLS combinations using PLACEHOLDER functions from
    scia_load_combinations.py that will be properly implemented by colleagues later.

    :param model: SCIA model instance
    :param self_weight_case: Self-weight load case
    :param wind_case: Wind load case
    :param tandem_load_cases: List of tandem load cases
    :returns: Dictionary with created load combinations
    :rtype: dict[str, Any]
    """
    combinations = {}

    if tandem_load_cases:
        # Use first tandem case as primary traffic load
        primary_tandem = tandem_load_cases[0]

        # Create combinations using PLACEHOLDER functions
        uls_basic = create_basic_uls_combination(model, self_weight_case, primary_tandem)
        combinations["uls_basic"] = uls_basic

        sls_basic = create_basic_sls_combination(model, self_weight_case, primary_tandem)
        combinations["sls_basic"] = sls_basic

        uls_wind = create_wind_uls_combination(model, self_weight_case, primary_tandem, wind_case)
        combinations["uls_wind"] = uls_wind

    return combinations
