"""
Bridge Geometry and Load Generation for SCIA Integration.

This module provides a clean, simple interface for:
1. Extracting bridge dimensions from parametrization
2. Generating tandem loads (theoretical or actual lanes)
3. Converting load data for SCIA format

Easy to extend for new load types (UDL, etc.).

HOW TO ADD NEW LOAD TYPES (e.g., UDL):
========================================
1. Add new load type to LoadType enum below
2. Create load group enums if needed (e.g., UDLGroup)
3. Add your load generation functions to the registry dictionaries
4. Create a generate_[loadtype]_loads() function following the same pattern
5. Optionally add to the unified generate_all_loads() function

See the comments throughout this file for specific examples!
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable

from .scia_loads_helper import (
    create_real_udl_traffic_loads,  # UDL function added!
    tandem_systems_real_lanes_bg8000,
    tandem_systems_real_lanes_bg9000,
    tandem_systems_real_lanes_bg10000,
    tandem_systems_theoretical_lanes_bg8000,
    tandem_systems_theoretical_lanes_bg9000,
    tandem_systems_theoretical_lanes_bg10000,
)

BridgeParametrization = Any


class LoadType(Enum):
    """
    Enumeration of available load types.
    """

    TANDEM = "tandem"
    UDL = "udl"  # UDL support added!
    # Can add other loads here


class UDLGroup(Enum):
    """
    Enumeration of available UDL load groups.

    These represent different UDL positioning strategies:
    - BG4001: Leftmost lanes (BG8000 logic)
    - BG4002: Rightmost lanes (BG9000 logic)
    - BG4003: Center lanes with dynamic distribution
    """

    BG4001 = "bg4001"  # Leftmost lanes
    BG4002 = "bg4002"  # Rightmost lanes
    BG4003 = "bg4003"  # Center lanes


class LoadGroup(Enum):
    """
    Enumeration of available load groups for tandem loads.

    These represent different bridge classes (BG8000, BG9000, BG10000).
    For UDL loads, you might want to create a separate UDLGroup enum
    with values like TRAFFIC_UDL, PEDESTRIAN_UDL, etc.
    """

    BG8000 = "bg8000"
    BG9000 = "bg9000"
    BG10000 = "bg10000"


class LoadMode(Enum):
    """
    Enumeration of load generation modes.

    THEORETICAL: Uses idealized lane configurations
    ACTUAL: Uses real-world lane configurations from bridge data

    UDL loads typically only have one mode, but you could extend this
    if you need different UDL calculation methods.
    """

    THEORETICAL = "theoretical"
    ACTUAL = "actual"


@dataclass(frozen=True)
class BridgeDimensions:
    """
    Bridge dimensions extracted from parametrization.

    This dataclass provides a clean, structured way to access bridge dimensions.
    All load generation functions (tandem, UDL, etc.) can use this
    same interface, making it easy to add new load types.

    TO ADD UDL SUPPORT: Your UDL functions can access these same dimensions
    - total_length: Total bridge length
    - total_width: Total bridge width
    - thickness: Bridge deck thickness
    - zone1_width, zone2_width, zone3_width: Traffic lane widths
    """

    total_length: float
    total_width: float
    thickness: float
    zone1_width: float
    zone2_width: float
    zone3_width: float
    first_segment_thickness: float
    first_segment_thickness_2: float = 0.0

    @property
    def zone_widths(self) -> dict[str, float]:
        """Get zone widths as a dictionary for backward compatibility."""
        return {
            "bz1": self.zone1_width,
            "bz2": self.zone2_width,
            "bz3": self.zone3_width,
        }


# =============================================================================
# BRIDGE DIMENSION EXTRACTION
# =============================================================================


def extract_bridge_dimensions(params: BridgeParametrization) -> BridgeDimensions:
    """
    Extract key bridge dimensions from parametrization.

    This function is used by ALL load generation functions (tandem, UDL, etc.).
    When you add UDL support, your UDL functions will call this same function
    to get the bridge dimensions they need.

    :param params: Bridge parameters with bridge_segments_array
    :returns: Bridge dimensions as a structured dataclass
    :raises IndexError: When no bridge segments are provided
    """
    if not params.bridge_segments_array:
        raise IndexError("No bridge segments provided")

    # Get first segment for width and thickness
    first_segment = params.bridge_segments_array[0]

    # Calculate totals
    total_length = sum(segment.l for segment in params.bridge_segments_array)
    total_width = first_segment.bz1 + first_segment.bz2 + first_segment.bz3

    return BridgeDimensions(
        total_length=total_length,
        total_width=total_width,
        thickness=first_segment.dz,
        zone1_width=first_segment.bz1,
        zone2_width=first_segment.bz2,
        zone3_width=first_segment.bz3,
        first_segment_thickness=first_segment.dz,
        first_segment_thickness_2=getattr(first_segment, "dz_2", 0.0),
    )


def extract_zone_boundaries(params: BridgeParametrization) -> dict[str, dict[str, float]]:
    """
    Extract zone boundaries for each segment.

    This function is also available for all load types.
    UDL loads might need this to determine where to place distributed loads.

    :param params: Bridge parameters
    :returns: Dictionary with zone boundaries per segment
    :raises IndexError: When no bridge segments are provided
    """
    if not params.bridge_segments_array:
        raise IndexError("No bridge segments provided")

    boundaries = {}

    for i, segment in enumerate(params.bridge_segments_array):
        segment_id = f"segment_{i + 1}"

        # Calculate zone boundaries from center line
        # Zone layout: Zone 3 | Zone 2 | Zone 1
        z1_left = segment.bz1 + segment.bz2 / 2
        z1_right = segment.bz2 / 2
        z3_left = -segment.bz2 / 2
        z3_right = -segment.bz3 - segment.bz2 / 2

        boundaries[segment_id] = {
            "z1_left": z1_left,
            "z1_right": z1_right,
            "z3_left": z3_left,
            "z3_right": z3_right,
        }

    return boundaries


# =============================================================================
# TANDEM LOAD GENERATION
# =============================================================================

# Load function registries for clean dispatch
#
# TO ADD UDL SUPPORT: Create similar registries for UDL functions
# UDL_LOAD_FUNCTIONS: dict[UDLGroup, Callable] = {
#     UDLGroup.TRAFFIC_UDL: your_udl_function,
#     UDLGroup.PEDESTRIAN_UDL: your_pedestrian_udl_function,
# }
#
# The registry pattern makes it easy to add new load types without
# changing the core logic - just add to the dictionary!
THEORETICAL_LOAD_FUNCTIONS: dict[LoadGroup, Callable] = {
    LoadGroup.BG8000: tandem_systems_theoretical_lanes_bg8000,
    LoadGroup.BG9000: tandem_systems_theoretical_lanes_bg9000,
    LoadGroup.BG10000: tandem_systems_theoretical_lanes_bg10000,
}

ACTUAL_LOAD_FUNCTIONS: dict[LoadGroup, Callable] = {
    LoadGroup.BG8000: tandem_systems_real_lanes_bg8000,
    LoadGroup.BG9000: tandem_systems_real_lanes_bg9000,
    LoadGroup.BG10000: tandem_systems_real_lanes_bg10000,
}

# UDL Load function registry
# Your colleague's UDL function generates all UDL groups (BG4001, BG4002, BG4003) at once,
# so we create wrapper functions that extract the specific group from the results
UDL_LOAD_FUNCTIONS: dict[UDLGroup, Callable] = {
    UDLGroup.BG4001: lambda params, length, udl_value=9000.0: _extract_udl_group(create_real_udl_traffic_loads(params, length, udl_value), "BG4001"),
    UDLGroup.BG4002: lambda params, length, udl_value=9000.0: _extract_udl_group(create_real_udl_traffic_loads(params, length, udl_value), "BG4002"),
    UDLGroup.BG4003: lambda params, length, udl_value=9000.0: _extract_udl_group(create_real_udl_traffic_loads(params, length, udl_value), "BG4003"),
}


def _extract_udl_group(udl_results: dict[str, dict[str, Any]], group_name: str) -> list[dict[str, Any]]:
    """
    Extract a specific UDL group from your colleague's function results.

    Your colleague's function returns all groups at once, but our architecture
    expects individual group results. This helper extracts the specific group.

    :param udl_results: Results from create_real_udl_traffic_loads()
    :param group_name: Name of the group to extract (BG4001, BG4002, BG4003)
    :returns: List of load cases for the specific group
    """
    if group_name not in udl_results:
        return []

    group_data = udl_results[group_name]
    load_cases = []

    # Convert the group data to our standard format
    for load_type, polygons in group_data.items():
        for polygon_data in polygons:
            load_cases.append(
                {
                    "load_case": f"{group_name}_{load_type}",
                    "load_type": "udl",
                    "polygon": polygon_data["polygon"],
                    "load_value": polygon_data["load"],
                }
            )

    return load_cases


def generate_udl_loads(params: BridgeParametrization, mode: LoadMode | str = LoadMode.THEORETICAL, udl_value: float = 9000.0) -> list[dict[str, Any]]:
    """
    Generate all UDL loads for a bridge.

    This function integrates your colleague's UDL function into our clean architecture.
    It follows the exact same pattern as generate_tandem_loads().

    :param params: Bridge parameters
    :param mode: Load generation mode (currently only supports THEORETICAL for UDL)
    :param udl_value: UDL value in N/m² (default: 9000.0)
    :returns: List of all UDL load cases (BG4001, BG4002, BG4003)
    :raises ValueError: When mode is invalid or generation fails
    """
    # Convert string to enum if needed
    if isinstance(mode, str):
        try:
            mode = LoadMode(mode)
        except ValueError:
            raise ValueError(f"Invalid mode '{mode}'. Use 'theoretical' or 'actual'") from None

    # UDL loads currently only support theoretical mode
    # (Your colleague's function generates "real" UDL loads, which we treat as theoretical)
    if mode != LoadMode.THEORETICAL:
        raise ValueError("UDL loads currently only support THEORETICAL mode")

    # Extract bridge dimensions
    dims = extract_bridge_dimensions(params)

    # Generate UDL loads for all UDL groups
    all_loads = []

    for udl_group in UDLGroup:
        try:
            loads = _generate_udl_for_group(udl_group, params, dims, udl_value)
            all_loads.extend(loads)
        except Exception as e:
            raise ValueError(f"Failed to generate UDL loads for {udl_group.value}: {e}") from e

    return all_loads


def _generate_udl_for_group(
    udl_group: UDLGroup,
    params: BridgeParametrization,
    dims: BridgeDimensions,
    udl_value: float = 9000.0,
) -> list[dict[str, Any]]:
    """
    Generate UDL loads for a specific UDL group.

    This function calls your colleague's UDL function with the right parameters
    and extracts the specific group results.

    :param udl_group: UDL group to generate (BG4001, BG4002, BG4003)
    :param params: Bridge parameters (needed by your colleague's function)
    :param dims: Bridge dimensions (we use dims.total_length)
    :param udl_value: UDL value in N/m²
    :returns: List of load cases for the specific UDL group
    """
    func = UDL_LOAD_FUNCTIONS[udl_group]

    # Your colleague's function needs params, length, and udl_value
    # We get the length from our BridgeDimensions dataclass
    return func(params, dims.total_length, udl_value)


def generate_tandem_loads(params: BridgeParametrization, mode: LoadMode | str = LoadMode.THEORETICAL) -> list[dict[str, Any]]:
    """
    Generate all tandem loads for a bridge.

    This is the main function you should use. It handles all the complexity
    of calling the right functions with the right parameters.

    TO ADD UDL SUPPORT: Create a similar function called generate_udl_loads()
    that follows this exact same pattern:

    def generate_udl_loads(params: BridgeParametrization, mode: LoadMode | str = LoadMode.THEORETICAL):
        # Convert string to enum if needed
        if isinstance(mode, str):
            mode = LoadMode(mode)

        # Extract bridge dimensions (same as here!)
        dims = extract_bridge_dimensions(params)

        # Generate UDL loads for all UDL groups
        all_loads = []
        for udl_group in UDLGroup:  # Your new UDLGroup enum
            loads = _generate_udl_for_group(udl_group, mode, params, dims)
            all_loads.extend(loads)

        return all_loads

    :param params: Bridge parameters
    :param mode: Load generation mode (theoretical or actual)
    :returns: List of all tandem load cases (BG8000, BG9000, BG10000)
    :raises ValueError: When mode is invalid or generation fails
    """
    # Convert string to enum if needed
    if isinstance(mode, str):
        try:
            mode = LoadMode(mode)
        except ValueError:
            raise ValueError(f"Invalid mode '{mode}'. Use 'theoretical' or 'actual'") from None

    # Extract bridge dimensions
    dims = extract_bridge_dimensions(params)

    # Generate loads for all load groups
    all_loads = []

    for load_group in LoadGroup:
        try:
            loads = _generate_loads_for_group(load_group, mode, params, dims)
            all_loads.extend(loads)
        except Exception as e:
            raise ValueError(f"Failed to generate {mode.value} loads for {load_group.value}: {e}") from e

    return all_loads


def _generate_loads_for_group(
    load_group: LoadGroup,
    mode: LoadMode,
    params: BridgeParametrization,
    dims: BridgeDimensions,
) -> list[dict[str, Any]]:
    """
    Generate loads for a specific load group using the specified mode.

    This unified function handles both theoretical and actual load generation
    using the strategy pattern.

    TO ADD UDL SUPPORT: Create a similar function called _generate_udl_for_group()
    that follows this exact same pattern:

    def _generate_udl_for_group(udl_group: UDLGroup, mode: LoadMode, params: BridgeParametrization, dims: BridgeDimensions):
        func = UDL_LOAD_FUNCTIONS[udl_group]  # Your UDL registry

        # UDL functions typically need different parameters than tandem
        # Adjust these based on what your UDL functions expect
        return func(
            dims.total_length,      # Bridge length
            dims.total_width,       # Bridge width
            dims.zone3_width,       # Zone 3 width
            dims.zone2_width,       # Zone 2 width
            # Add any other parameters your UDL functions need
        )

    The key insight: All load generation functions can use the same
    BridgeDimensions dataclass, making the code consistent and maintainable.
    """
    if mode == LoadMode.THEORETICAL:
        func = THEORETICAL_LOAD_FUNCTIONS[load_group]
        # Theoretical functions need 5 parameters
        return func(
            dims.total_length,
            dims.total_width,
            dims.thickness,
            dims.zone3_width,
            dims.zone2_width,
        )
    if mode == LoadMode.ACTUAL:
        func = ACTUAL_LOAD_FUNCTIONS[load_group]
        # Actual functions need 3 parameters + params object
        return func(
            params,
            dims.total_length,
            dims.thickness,
        )
    raise ValueError(f"Unsupported load mode: {mode}")


# =============================================================================
# SCIA FORMAT CONVERSION
# =============================================================================


def convert_wheel_coordinates_to_3d(wheel_2d: list[list[float]]) -> list[tuple[float, float, float]]:
    """
    Convert 2D wheel coordinates to 3D coordinates for SCIA.

    This function is specific to tandem loads (wheel loads).
    For UDL loads, you might need a different conversion function
    that converts distributed load areas to SCIA patch loads.

    :param wheel_2d: List of 2D wheel coordinates [[x1, y1], [x2, y2], ...]
    :returns: List of 3D coordinates [(x1, y1, 0), (x2, y2, 0), ...]
    """
    return [(x, y, 0.0) for x, y in wheel_2d]


def align_bridge_coordinates_to_scia(coords: list[tuple[float, float, float]], bridge_center_y: float = 0.0) -> list[tuple[float, float, float]]:
    """
    Align bridge coordinates to SCIA coordinate system.

    This function is generic and can be used by all load types.
    UDL loads will use this same function to align their load areas.

    :param coords: List of 3D coordinates
    :param bridge_center_y: Y-coordinate of bridge center line
    :returns: List of aligned coordinates
    """
    return [(x, y + bridge_center_y, z) for x, y, z in coords]


def convert_loads_to_scia_format(load_data: list[dict[str, Any]], load_type: LoadType | str = LoadType.TANDEM) -> list[dict[str, Any]]:
    """
    Convert load data to SCIA-compatible format.

    This function now handles both tandem and UDL loads!

    :param load_data: Raw load data from generate_tandem_loads() or generate_udl_loads()
    :param load_type: Type of loads to convert (TANDEM or UDL)
    :returns: SCIA-formatted load cases
    :raises ValueError: When load_type is unsupported
    """
    # Convert string to enum if needed
    if isinstance(load_type, str):
        try:
            load_type = LoadType(load_type)
        except ValueError:
            raise ValueError(f"Invalid load_type '{load_type}'. Use 'tandem' or 'udl'") from None

    if load_type == LoadType.TANDEM:
        return _convert_tandem_to_scia(load_data)
    if load_type == LoadType.UDL:
        return _convert_udl_to_scia(load_data)
    raise ValueError(f"Unsupported load type: {load_type}")


def _convert_tandem_to_scia(load_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Convert tandem load data to SCIA-compatible format.

    :param load_data: Raw tandem load data from generate_tandem_loads()
    :returns: SCIA-formatted load cases
    """
    scia_cases = []

    for tandem in load_data:
        patch_loads = []

        # Extract wheel loads and convert to 3D coordinates
        for load in tandem.get("loads", []):
            for wheel_2d in load.get("wheels", []):
                # Convert 2D wheel coordinates to 3D (add z=0)
                wheel_3d = convert_wheel_coordinates_to_3d(wheel_2d)
                aligned_coords = align_bridge_coordinates_to_scia(wheel_3d)

                patch_loads.append(
                    {
                        "corners": aligned_coords,
                        "load_value": load.get("load", 0.0),
                    }
                )

        scia_cases.append(
            {
                "load_case": tandem["load_case"],
                "patch_loads": patch_loads,
            }
        )

    return scia_cases


def _convert_udl_to_scia(load_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Convert UDL load data to SCIA-compatible format.

    UDL function already provides polygon coordinates,
    just need to format them for SCIA.

    :param load_data: Raw UDL load data from generate_udl_loads()
    :returns: SCIA-formatted load cases
    """
    scia_cases = []

    for udl_load in load_data:
        # UDL loads already have polygon coordinates from your colleague's function
        polygon_coords = udl_load.get("polygon", [])
        load_value = udl_load.get("load_value", 0.0)

        # Align coordinates to SCIA coordinate system
        aligned_coords = align_bridge_coordinates_to_scia(polygon_coords)

        patch_loads = [
            {
                "corners": aligned_coords,
                "load_value": load_value,
            }
        ]

        scia_cases.append(
            {
                "load_case": udl_load["load_case"],
                "patch_loads": patch_loads,
            }
        )

    return scia_cases


# =============================================================================
# UNIFIED LOAD GENERATION
# =============================================================================


def generate_all_loads(
    params: BridgeParametrization, load_types: list[LoadType] | None = None, mode: LoadMode | str = LoadMode.THEORETICAL, udl_value: float = 9000.0
) -> dict[str, list[dict[str, Any]]]:
    """
    Generate all types of loads for a bridge.

    This is the ultimate function - generates everything at once!
    Perfect for when you need both tandem and UDL loads.

    :param params: Bridge parameters
    :param load_types: Types of loads to generate (default: all available)
    :param mode: Load generation mode
    :param udl_value: UDL value for UDL loads (N/m²)
    :returns: Dictionary with load type as key, load cases as value
    :raises ValueError: When load generation fails

    Usage:
        # Generate all load types
        all_loads = generate_all_loads(params)
        tandem_loads = all_loads["tandem"]
        udl_loads = all_loads["udl"]

        # Generate only specific load types
        specific_loads = generate_all_loads(params, [LoadType.UDL])
        udl_loads = specific_loads["udl"]
    """
    if load_types is None:
        load_types = list(LoadType)

    results = {}

    for load_type in load_types:
        try:
            if load_type == LoadType.TANDEM:
                results["tandem"] = generate_tandem_loads(params, mode)
            elif load_type == LoadType.UDL:
                results["udl"] = generate_udl_loads(params, mode, udl_value)
            # Add more load types here as they become available
            # elif load_type == LoadType.WIND:
            #     results["wind"] = generate_wind_loads(params, mode)
        except Exception as e:
            raise ValueError(f"Failed to generate {load_type.value} loads: {e}") from e

    return results
