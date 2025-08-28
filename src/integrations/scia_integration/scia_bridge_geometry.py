"""
Bridge Geometry and Load Generation for SCIA Integration.

This module provides a clean, simple interface for:
1. Extracting bridge dimensions from parametrization
2. Generating tandem loads (theoretical or actual lanes)
3. Converting load data for SCIA format

Easy to extend for new load types (UDL, wind, temperature, etc.)
"""

from typing import Any

from .scia_loads_helper import (
    tandem_systems_real_lanes_bg8000,
    tandem_systems_real_lanes_bg9000,
    tandem_systems_real_lanes_bg10000,
    tandem_systems_theoretical_lanes_bg8000,
    tandem_systems_theoretical_lanes_bg9000,
    tandem_systems_theoretical_lanes_bg10000,
)

BridgeParametrization = Any


# =============================================================================
# BRIDGE DIMENSION EXTRACTION
# =============================================================================


def extract_bridge_dimensions(params: BridgeParametrization) -> dict[str, Any]:
    """
    Extract key bridge dimensions from parametrization.

    :param params: Bridge parameters with bridge_segments_array
    :returns: Dictionary with bridge dimensions
    :raises IndexError: When no bridge segments are provided
    """
    if not params.bridge_segments_array:
        raise IndexError("No bridge segments provided")

    # Get first segment for width and thickness
    first_segment = params.bridge_segments_array[0]

    # Calculate totals
    total_length = sum(segment.l for segment in params.bridge_segments_array)
    total_width = first_segment.bz1 + first_segment.bz2 + first_segment.bz3

    return {
        "total_length": total_length,
        "total_width": total_width,
        "thickness": first_segment.dz,
        "zone_widths": {
            "bz1": first_segment.bz1,
            "bz2": first_segment.bz2,
            "bz3": first_segment.bz3,
        },
        "zone1_width": first_segment.bz1,
        "zone2_width": first_segment.bz2,
        "zone3_width": first_segment.bz3,
        "first_segment_thickness": first_segment.dz,
        "first_segment_thickness_2": getattr(first_segment, "dz_2", 0.0),
    }


def extract_zone_boundaries(params: BridgeParametrization) -> dict[str, dict[str, float]]:
    """
    Extract zone boundaries for each segment.

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


def generate_tandem_loads(params: BridgeParametrization, mode: str = "theoretical") -> list[dict[str, Any]]:
    """
    Generate all tandem loads for a bridge.

    This is the main function you should use. It handles all the complexity
    of calling the right functions with the right parameters.

    :param params: Bridge parameters
    :param mode: "theoretical" (3m lanes) or "actual" (real lane positions)
    :returns: List of all tandem load cases (BG8000, BG9000, BG10000)
    :raises ValueError: When mode is invalid or generation fails
    """
    if mode not in ["theoretical", "actual"]:
        raise ValueError(f"Invalid mode '{mode}'. Use 'theoretical' or 'actual'")

    # Extract bridge dimensions
    dims = extract_bridge_dimensions(params)

    # Generate loads for all load groups
    all_loads = []
    load_groups = ["bg8000", "bg9000", "bg10000"]

    for group in load_groups:
        try:
            if mode == "theoretical":
                loads = _generate_theoretical_loads(group, dims)
            else:  # mode == "actual"
                loads = _generate_actual_loads(group, params, dims)

            all_loads.extend(loads)

        except Exception as e:
            raise ValueError(f"Failed to generate {mode} loads for {group}: {e}") from e

    return all_loads


def _generate_theoretical_loads(group: str, dims: dict[str, float]) -> list[dict[str, Any]]:
    """Generate theoretical tandem loads for one load group."""
    # Call the appropriate function directly - no complex mapping needed
    if group == "bg8000":
        return tandem_systems_theoretical_lanes_bg8000(
            dims["length"],
            dims["width"],
            dims["thickness"],
            dims["zone3_width"],
            dims["zone2_width"],
        )
    if group == "bg9000":
        return tandem_systems_theoretical_lanes_bg9000(
            dims["length"],
            dims["width"],
            dims["thickness"],
            dims["zone3_width"],
            dims["zone2_width"],
        )
    if group == "bg10000":
        return tandem_systems_theoretical_lanes_bg10000(
            dims["length"],
            dims["width"],
            dims["thickness"],
            dims["zone3_width"],
            dims["zone2_width"],
        )
    raise ValueError(f"Unknown load group: {group}")


def _generate_actual_loads(group: str, params: BridgeParametrization, dims: dict[str, float]) -> list[dict[str, Any]]:
    """Generate actual lane tandem loads for one load group."""
    # Call the appropriate function directly - no complex mapping needed
    if group == "bg8000":
        return tandem_systems_real_lanes_bg8000(
            params,
            dims["length"],
            dims["thickness"],
        )
    if group == "bg9000":
        return tandem_systems_real_lanes_bg9000(
            params,
            dims["length"],
            dims["thickness"],
        )
    if group == "bg10000":
        return tandem_systems_real_lanes_bg10000(
            params,
            dims["length"],
            dims["thickness"],
        )
    raise ValueError(f"Unknown load group: {group}")


# =============================================================================
# SCIA FORMAT CONVERSION
# =============================================================================


def convert_wheel_coordinates_to_3d(wheel_2d: list[list[float]]) -> list[tuple[float, float, float]]:
    """
    Convert 2D wheel coordinates to 3D coordinates for SCIA.

    :param wheel_2d: List of 2D wheel coordinates [[x1, y1], [x2, y2], ...]
    :returns: List of 3D coordinates [(x1, y1, 0), (x2, y2, 0), ...]
    """
    return [(x, y, 0.0) for x, y in wheel_2d]


def align_bridge_coordinates_to_scia(coords: list[tuple[float, float, float]], bridge_center_y: float = 0.0) -> list[tuple[float, float, float]]:
    """
    Align bridge coordinates to SCIA coordinate system.

    :param coords: List of 3D coordinates
    :param bridge_center_y: Y-coordinate of bridge center line
    :returns: List of aligned coordinates
    """
    return [(x, y + bridge_center_y, z) for x, y, z in coords]


def convert_loads_to_scia_format(load_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
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


def convert_tandem_data_to_scia_format(tandem_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Legacy function name for backward compatibility.

    DEPRECATED: Use convert_loads_to_scia_format() instead.
    """
    return convert_loads_to_scia_format(tandem_data)
