"""
Pure load generation functions without circular dependencies.

This module contains the core load generation logic extracted from scia_bridge_geometry.py
to eliminate circular imports. It coordinates between theoretical and real tandem/UDL generators.
"""

from typing import Any, Callable

from src.data_models.scia_models import BridgeDimensionsData
from src.integrations.scia_integration.constants import DEFAULT_UDL_VALUE
from src.integrations.scia_integration.types import BridgeParams, LoadGroup, LoadMode, LoadType

# Type aliases for different function signatures
TheoreticalTandemFunc = Callable[[BridgeParams, float, float, float, float, float], list[dict[str, Any]]]
ActualTandemFunc = Callable[[BridgeParams, float, float], list[dict[str, Any]]]


def _raise_unsupported_mode_error(mode: LoadMode) -> None:
    """Helper function to raise unsupported mode error."""
    raise ValueError(f"Unsupported load mode: {mode}")


def _raise_unsupported_udl_mode_error(mode: LoadMode) -> None:
    """Helper function to raise unsupported UDL mode error."""
    raise ValueError(f"Unsupported UDL load mode: {mode}")


def get_load_mode_from_params(params: BridgeParams) -> LoadMode:
    """
    Extract load mode from bridge parameters based on berekeningsniveau.

    :param params: Bridge parameters containing berekeningsniveau setting
    :returns: Corresponding LoadMode enum value
    :rtype: LoadMode
    """
    # The berekeningsniveau parameter is directly under params, not under params.input.berekeningsinstellingen
    berekeningsniveau = params.berekeningsniveau

    if berekeningsniveau == "Theoretische wegindeling":
        return LoadMode.THEORETICAL
    if berekeningsniveau in [
        "Werkelijke wegindeling",
        "Werkelijke wegindeling onderliggend wegennet",
        "Werkelijke wegindeling met bebording",
    ]:
        return LoadMode.ACTUAL
    # This should never happen with radio button, but fallback for safety
    return LoadMode.THEORETICAL


def extract_bridge_dimensions(params: BridgeParams) -> BridgeDimensionsData:
    """
    Extract and validate key bridge dimensions from parametrization.

    Uses Pydantic validation to ensure dimensions are realistic and consistent.

    :param params: Bridge parameters with bridge_segments_array
    :returns: Bridge dimensions as a validated Pydantic model
    :raises IndexError: When no bridge segments are provided
    :raises ValidationError: When dimensions fail Pydantic validation (e.g., negative widths, unrealistic sizes)
    """
    if not params.bridge_segments_array:
        raise IndexError("No bridge segments provided")

    # Get first segment for width and thickness
    first_segment = params.bridge_segments_array[0]

    # Calculate totals
    total_length = sum(segment.l for segment in params.bridge_segments_array)
    total_width = first_segment.bz1 + first_segment.bz2 + first_segment.bz3

    # Pydantic validates all fields and cross-field constraints here
    return BridgeDimensionsData(
        total_length=total_length,
        total_width=total_width,
        thickness=first_segment.dz,
        zone1_width=first_segment.bz1,
        zone2_width=first_segment.bz2,
        zone3_width=first_segment.bz3,
        first_segment_thickness=first_segment.dz,
        first_segment_thickness_2=getattr(first_segment, "dz_2", 0.0),
    )


def generate_tandem_loads(params: BridgeParams, mode: LoadMode | str | None = None) -> list[dict[str, Any]]:
    """
    Generate all tandem loads for a bridge.

    :param params: Bridge parameters
    :param mode: Load generation mode (ignored - always uses berekeningsniveau parameter)
    :returns: List of all tandem load cases (BG8000, BG9000, BG10000)
    :raises ValueError: When mode is invalid or generation fails
    """
    # Always use mode from parameters (berekeningsniveau)
    mode = get_load_mode_from_params(params)
    # Import here to avoid circular imports
    from .real_tandem_generators import (
        tandem_systems_real_lanes_bg8000,
        tandem_systems_real_lanes_bg9000,
        tandem_systems_real_lanes_bg10000,
    )
    from .theoretical_tandem_generators import (
        tandem_systems_theoretical_lanes_bg8000,
        tandem_systems_theoretical_lanes_bg9000,
        tandem_systems_theoretical_lanes_bg10000,
    )

    # Convert string to enum if needed
    if isinstance(mode, str):
        try:
            mode = LoadMode(mode)
        except ValueError:
            raise ValueError(f"Invalid mode '{mode}'. Use 'theoretical' or 'actual'") from None

    # Extract bridge dimensions
    dims = extract_bridge_dimensions(params)

    # Function registries with proper typing
    theoretical_functions: dict[LoadGroup, TheoreticalTandemFunc] = {
        LoadGroup.BG8000: tandem_systems_theoretical_lanes_bg8000,
        LoadGroup.BG9000: tandem_systems_theoretical_lanes_bg9000,
        LoadGroup.BG10000: tandem_systems_theoretical_lanes_bg10000,
    }

    actual_functions: dict[LoadGroup, ActualTandemFunc] = {
        LoadGroup.BG8000: tandem_systems_real_lanes_bg8000,
        LoadGroup.BG9000: tandem_systems_real_lanes_bg9000,
        LoadGroup.BG10000: tandem_systems_real_lanes_bg10000,
    }

    # Generate loads for all load groups
    all_loads = []

    try:
        for load_group in LoadGroup:
            if mode == LoadMode.THEORETICAL:
                theoretical_func = theoretical_functions[load_group]
                # Theoretical functions need 6 parameters (including params)
                loads = theoretical_func(
                    params,
                    dims.total_length,
                    dims.total_width,
                    dims.thickness,
                    dims.zone3_width,
                    dims.zone2_width,
                )
            elif mode == LoadMode.ACTUAL:
                actual_func = actual_functions[load_group]
                # Actual functions need 3 parameters + params object (lane_width has default)
                loads = actual_func(
                    params,
                    dims.total_length,
                    dims.thickness,
                )
            else:
                _raise_unsupported_mode_error(mode)

            all_loads.extend(loads)
    except Exception as e:
        # Determine which load group failed if possible
        load_group_name = load_group.value if "load_group" in locals() else "unknown"
        raise ValueError(f"Failed to generate {mode.value} loads for {load_group_name}: {e}") from e

    return all_loads


def generate_udl_loads(params: BridgeParams, mode: LoadMode | str | None = None, udl_value: float = DEFAULT_UDL_VALUE) -> list[dict[str, Any]]:
    """
    Generate all UDL loads for a bridge.

    :param params: Bridge parameters
    :param mode: Load generation mode (ignored - always uses berekeningsniveau parameter)
    :param udl_value: UDL value in N/m² (default: DEFAULT_UDL_VALUE)
    :returns: List of all UDL load cases (BG4001, BG4002, BG4003)
    :raises ValueError: When mode is invalid or generation fails
    """
    # Always use mode from parameters (berekeningsniveau)
    mode = get_load_mode_from_params(params)
    # Import here to avoid circular imports
    from .udl_generators import create_real_udl_traffic_loads, create_theoretical_udl_traffic_loads

    # Convert string to enum if needed
    if isinstance(mode, str):
        try:
            mode = LoadMode(mode)
        except ValueError:
            raise ValueError(f"Invalid mode '{mode}'. Use 'theoretical' or 'actual'") from None

    # Extract bridge dimensions
    dims = extract_bridge_dimensions(params)

    # Generate UDL loads using the appropriate function based on mode
    try:
        if mode == LoadMode.THEORETICAL:
            udl_results = create_theoretical_udl_traffic_loads(
                params, dims.total_length, dims.total_width, dims.zone3_width, dims.zone2_width, udl_value
            )
        elif mode == LoadMode.ACTUAL:
            udl_results = create_real_udl_traffic_loads(params, dims.total_length, udl_value)
        else:
            _raise_unsupported_udl_mode_error(mode)

        # Convert to our standard format
        # New structure: each key (BG4001, BG4002, etc.) contains a single polygon with load and title
        all_loads = []
        for load_case_name, load_data in udl_results.items():
            all_loads.append(
                {
                    "load_case": load_case_name,
                    "load_type": "udl",
                    "polygon": load_data["polygon"],
                    "load_value": load_data["load"],
                    "title": load_data.get("title", ""),
                }
            )

    except Exception as e:
        raise ValueError(f"Failed to generate UDL loads: {e}") from e
    else:
        return all_loads


def generate_all_loads(
    params: BridgeParams, load_types: list[LoadType] | None = None, mode: LoadMode | str | None = None, udl_value: float = DEFAULT_UDL_VALUE
) -> dict[str, list[dict[str, Any]]]:
    """
    Generate all types of loads for a bridge.

    :param params: Bridge parameters
    :param load_types: Types of loads to generate (default: all available)
    :param mode: Load generation mode (ignored - always uses berekeningsniveau parameter)
    :param udl_value: UDL value for UDL loads (N/m²)
    :returns: Dictionary with load type as key, load cases as value
    :raises ValueError: When load generation fails
    """
    # Always use mode from parameters (berekeningsniveau)
    mode = get_load_mode_from_params(params)
    if load_types is None:
        load_types = list(LoadType)

    results = {}

    try:
        for load_type in load_types:
            if load_type == LoadType.TANDEM:
                results["tandem"] = generate_tandem_loads(params, mode)
            elif load_type == LoadType.UDL:
                results["udl"] = generate_udl_loads(params, mode, udl_value)
    except Exception as e:
        # Determine which load type failed if possible
        load_type_name = load_type.value if "load_type" in locals() else "unknown"
        raise ValueError(f"Failed to generate {load_type_name} loads: {e}") from e

    return results
