"""
Coordinate transformation utilities for SCIA integration.

This module provides pure utility functions for coordinate transformations
and load format conversions without any circular dependencies.
"""

from typing import Any

from .scia_load_generators import LoadType


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


def convert_loads_to_scia_format(load_data: list[dict[str, Any]], load_type: LoadType | str = LoadType.TANDEM) -> list[dict[str, Any]]:
    """
    Convert load data to SCIA-compatible format.

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
    """Convert tandem load data to SCIA-compatible format."""
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
    """Convert UDL load data to SCIA-compatible format."""
    scia_cases = []

    for udl_load in load_data:
        # UDL loads already have polygon coordinates
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


def extract_zone_boundaries(params: Any) -> dict[str, dict[str, float]]:
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
