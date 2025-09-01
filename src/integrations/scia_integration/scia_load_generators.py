"""
Pure load generation functions without circular dependencies.

This module contains the core load generation logic extracted from scia_bridge_geometry.py
to eliminate circular imports. It only depends on scia_loads_helper for the actual calculations.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable

# Type alias to avoid importing from app layer
BridgeParams = Any

# Type aliases for different function signatures
TheoreticalTandemFunc = Callable[[BridgeParams, float, float, float, float, float], list[dict[str, Any]]]
ActualTandemFunc = Callable[[BridgeParams, float, float], list[dict[str, Any]]]


class LoadType(Enum):
    """Enumeration of available load types."""

    TANDEM = "tandem"
    UDL = "udl"


class LoadGroup(Enum):
    """Enumeration of available load groups for tandem loads."""

    BG8000 = "bg8000"
    BG9000 = "bg9000"
    BG10000 = "bg10000"


class UDLGroup(Enum):
    """Enumeration of available UDL load groups."""

    BG4001 = "bg4001"  # Leftmost lanes
    BG4002 = "bg4002"  # Rightmost lanes
    BG4003 = "bg4003"  # Center lanes


class LoadMode(Enum):
    """Enumeration of load generation modes."""

    THEORETICAL = "theoretical"
    ACTUAL = "actual"


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
    # The berekeningsniveau parameter is directly under params, not under params.input.belastingcombinaties
    berekeningsniveau = params.berekeningsniveau

    if berekeningsniveau == "Theoretische wegindeling":
        return LoadMode.THEORETICAL
    if berekeningsniveau in ["Werkelijke wegindeling", "Werkelijke wegindeling onderliggend wegennet"]:
        return LoadMode.ACTUAL
    # This should never happen with radio button, but fallback for safety
    return LoadMode.THEORETICAL


@dataclass(frozen=True)
class BridgeDimensions:
    """Bridge dimensions extracted from parametrization."""

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


def extract_bridge_dimensions(params: BridgeParams) -> BridgeDimensions:
    """
    Extract key bridge dimensions from parametrization.

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
    from .scia_loads_helper import (
        tandem_systems_real_lanes_bg8000,
        tandem_systems_real_lanes_bg9000,
        tandem_systems_real_lanes_bg10000,
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


def generate_udl_loads(params: BridgeParams, mode: LoadMode | str | None = None, udl_value: float = 9000.0) -> list[dict[str, Any]]:
    """
    Generate all UDL loads for a bridge.

    :param params: Bridge parameters
    :param mode: Load generation mode (ignored - always uses berekeningsniveau parameter)
    :param udl_value: UDL value in N/m² (default: 9000.0)
    :returns: List of all UDL load cases (BG4001, BG4002, BG4003)
    :raises ValueError: When mode is invalid or generation fails
    """
    # Always use mode from parameters (berekeningsniveau)
    mode = get_load_mode_from_params(params)
    # Import here to avoid circular imports
    from .scia_loads_helper import create_real_udl_traffic_loads, create_theoretical_udl_traffic_loads

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
        all_loads = []
        for group_name, group_data in udl_results.items():
            for load_type, polygons in group_data.items():
                all_loads.extend(
                    [
                        {
                            "load_case": f"{group_name}_{load_type}",
                            "load_type": "udl",
                            "polygon": polygon_data["polygon"],
                            "load_value": polygon_data["load"],
                        }
                        for polygon_data in polygons
                    ]
                )

    except Exception as e:
        raise ValueError(f"Failed to generate UDL loads: {e}") from e
    else:
        return all_loads


def generate_all_loads(
    params: BridgeParams, load_types: list[LoadType] | None = None, mode: LoadMode | str | None = None, udl_value: float = 9000.0
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
