"""
Bridge geometry extraction and parameter calculation.

This module provides pure Python functions that extract geometry data from bridge parameters.
No SCIA SDK dependencies - can be used by any load type (traffic, wind, temperature, etc.).

Functions moved from:
- scia_model.py: create_node_and_thickness_dict
- scia_loads.py: extract_tandem_parameters_from_bridge, determine_tandem_function_for_bridge, etc.
"""

from typing import Any

from .scia_loads_helper import (
    tandem_systems_actual_lanes,
    tandem_systems_theoretical_lanes_bg8000,
    tandem_systems_theoretical_lanes_bg9000,
    tandem_systems_theoretical_lanes_bg10000,
)

# Type alias to avoid importing from app layer
BridgeParametrization = Any

def extract_bridge_dimensions(params: Any) -> dict[str, Any]:  # noqa: ANN401
    """
    Extract basic bridge dimensions from bridge parameters.

    :param params: Bridge parameters
    :returns: Dictionary with basic bridge dimensions
    :rtype: dict[str, Any]
    :raises IndexError: When no bridge segments are provided
    """
    if not params.bridge_segments_array:
        raise IndexError("No bridge segments provided")

    # Calculate total bridge length (cumulative sum of segment lengths)
    total_length = sum(segment.l for segment in params.bridge_segments_array)

    # Calculate total bridge width from first segment (bz1 + bz2 + bz3)
    first_segment = params.bridge_segments_array[0]
    total_width = first_segment.bz1 + first_segment.bz2 + first_segment.bz3

    # Calculate individual zone widths
    zone_widths = {
        "bz1": first_segment.bz1,
        "bz2": first_segment.bz2,
        "bz3": first_segment.bz3,
    }

    return {
        "total_length": total_length,
        "total_width": total_width,
        "zone_widths": zone_widths,
        "first_segment_thickness": first_segment.dz,
        "first_segment_thickness_2": first_segment.dz_2,
    }


def extract_zone_boundaries(params: Any) -> dict[str, dict[str, float]]:  # noqa: ANN401
    """
    Extract zone boundaries for each segment.

    :param params: Bridge parameters
    :returns: Dictionary with zone boundaries per segment
    :rtype: dict[str, dict[str, float]]
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


def extract_tandem_parameters_from_bridge(params: Any) -> dict[str, float]:  # noqa: ANN401
    """
    Extract parameters needed for scia_loads_helper from bridge data.

    :param params: Bridge parameters
    :returns: Dictionary with length_bridgedeck, width_bridgedeck, thickness_bridgedeck
    :rtype: dict[str, float]
    :raises IndexError: When no bridge segments are provided
    """
    if not params.bridge_segments_array:
        raise IndexError("No bridge segments provided")

    # Calculate total bridge length (cumulative sum of segment lengths)
    length_bridgedeck = sum(segment.l for segment in params.bridge_segments_array)

    # Calculate total bridge width from first segment (bz1 + bz2 + bz3)
    first_segment = params.bridge_segments_array[0]
    width_bridgedeck = first_segment.bz1 + first_segment.bz2 + first_segment.bz3

    # Use thickness from first segment (dz)
    thickness_bridgedeck = first_segment.dz

    return {
        "width_firstsegment_zone3": first_segment.bz3,
        "width_firstsegment_zone2": first_segment.bz2,
        "width_firstsegment_zone1": first_segment.bz1,
        "length_bridgedeck": length_bridgedeck,
        "width_bridgedeck": width_bridgedeck,
        "thickness_bridgedeck": thickness_bridgedeck,
    }


def determine_tandem_function_for_bridge(bridge_dims: dict[str, float], mode: str = "theoretical") -> dict[str, Any]:
    """
    Determine appropriate tandem function for bridge based on dimensions.

    :param bridge_dims: Bridge dimensions from extract_tandem_parameters_from_bridge
    :param mode: Calculation mode ('theoretical' or 'actual')
    :returns: Dictionary with tandem function details
    :rtype: dict[str, Any]
    :raises ValueError: When mode is not supported
    """
    if mode not in ["theoretical", "actual"]:
        raise ValueError(f"Unsupported mode: {mode}. Use 'theoretical' or 'actual'")

    if mode == "theoretical":
        # Theoretical mode uses theoretical lanes regardless of bridge width
        tandem_function = tandem_systems_theoretical_lanes_bg8000
        function_name = "tandem_systems_theoretical_lanes_BG8000"
        tandem_function2 = tandem_systems_theoretical_lanes_bg9000
        function_name2 = "tandem_systems_theoretical_lanes_BG9000"
        tandem_function3 = tandem_systems_theoretical_lanes_bg10000
        function_name3 = "tandem_systems_theoretical_lanes_BG10000"
        # Calculate theoretical lane count (bridge_width / 3.0m per lane)
        lane_count = int(bridge_dims["width_bridgedeck"] // 3.0)

        return {
            "function": tandem_function,
            "function_name": function_name,
            "lane_count": lane_count,
            "mode": mode,
            "description": f"Theoretical lanes: {lane_count} lanes across {bridge_dims['width_bridgedeck']}m",
            "bridge_dimensions": bridge_dims,
            "function2": tandem_function2,
            "function_name2": function_name2,
            "function3": tandem_function3,
            "function_name3": function_name3,
        }

    if mode == "actual":
        # Actual mode uses actual lane positions from bridge parametrization
        tandem_function = tandem_systems_actual_lanes  # type: ignore[assignment]
        function_name = "tandem_systems_actual_lanes"

        # Note: This will require actual lane positions from params.input.belastingzones
        # For now, return the function - actual lane positions will be extracted elsewhere
        return {
            "function": tandem_function,
            "function_name": function_name,
            "mode": mode,
            "description": "Actual lanes: using real lane positions from bridge parametrization",
            "bridge_dimensions": bridge_dims,
        }

    # This should never be reached due to the mode validation at the beginning
    raise ValueError(f"Unsupported mode: {mode}. Use 'theoretical' or 'actual'")


def generate_tandem_loads_for_bridge(params: BridgeParametrization, bridge_params: dict[str, float], mode: str = "theoretical") -> list[dict[str, Any]]:
    """
    Generate tandem load data for bridge using appropriate function.

    :param bridge_params: Bridge parameters from extract_tandem_parameters_from_bridge
    :param mode: Calculation mode ('theoretical' or 'actual')
    :returns: List of tandem load dictionaries
    :rtype: list[dict[str, Any]]
    :raises ImportError: When load calculation modules are not available
    """
    # Get the appropriate tandem function
    tandem_info = determine_tandem_function_for_bridge(bridge_params, mode)
    tandem_function = tandem_info["function"]
    tandem_function2 = tandem_info["function2"]
    tandem_function3 = tandem_info["function3"]

    # Generate tandem loads using the selected function
    try:
        tandem_loads_bg8000 = tandem_function(
            params,
            bridge_params["length_bridgedeck"],
            bridge_params["width_bridgedeck"],
            bridge_params["thickness_bridgedeck"],
            bridge_params["width_firstsegment_zone3"],  # Use bz3 from first segment for lane width
            bridge_params["width_firstsegment_zone2"],  # Use bz2 from first segment for lane width
        )
    except Exception as e:
        raise ValueError(f"Failed to generate tandem loads: {e!s}") from e
    # Generate tandem loads for configuration with reversed lane order (9000 series)
    try:
        tandem_loads_bg9000 = tandem_function2(
            params,
            bridge_params["length_bridgedeck"],
            bridge_params["width_bridgedeck"],
            bridge_params["thickness_bridgedeck"],
            bridge_params["width_firstsegment_zone3"],  # Use bz3 from first segment for lane width
            bridge_params["width_firstsegment_zone2"],  # Use bz2 from first segment for lane width
        )
    except Exception as e:
        raise ValueError(f"Failed to generate tandem loads: {e!s}") from e
    tandem_loads_bg8000.extend(tandem_loads_bg9000)
    # Generate tandem loads for configuration with middle lane order (10000 series)
    try:
        tandem_loads_bg10000 = tandem_function3(
            params,
            bridge_params["length_bridgedeck"],
            bridge_params["width_bridgedeck"],
            bridge_params["thickness_bridgedeck"],
            bridge_params["width_firstsegment_zone3"],  # Use bz3 from first segment for lane width
            bridge_params["width_firstsegment_zone2"],  # Use bz2 from first segment for lane width
        )
    except Exception as e:
        raise ValueError(f"Failed to generate tandem loads: {e!s}") from e
    tandem_loads_bg8000.extend(tandem_loads_bg10000)

    return tandem_loads_bg8000


def convert_wheel_coordinates_to_3d(wheel_2d: list[list[float]]) -> list[tuple[float, float, float]]:
    """
    Convert 2D wheel coordinates to 3D coordinates for SCIA.

    :param wheel_2d: List of 2D wheel coordinates [[x1, y1], [x2, y2], ...]
    :returns: List of 3D coordinates [(x1, y1, 0), (x2, y2, 0), ...]
    :rtype: list[tuple[float, float, float]]
    """
    return [(x, y, 0.0) for x, y in wheel_2d]


def align_bridge_coordinates_to_scia(coords: list[tuple[float, float, float]], bridge_center_y: float = 0.0) -> list[tuple[float, float, float]]:
    """
    Align bridge coordinates to SCIA coordinate system.

    :param coords: List of 3D coordinates
    :param bridge_center_y: Y-coordinate of bridge center line
    :returns: List of aligned coordinates
    :rtype: list[tuple[float, float, float]]
    """
    # Apply bridge center offset
    return [(x, y + bridge_center_y, z) for x, y, z in coords]


def convert_tandem_data_to_scia_format(tandem_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Convert tandem load data to a SCIA-compatible definition format.

    This function transforms the output of `tandem_systems_theoretical_lanes`
    into a structure suitable for creating SCIA load definitions.

    :param tandem_data: List of tandem load dictionaries from the helper function.
    :returns: A list of dictionaries, where each represents a load case
              with its associated patch load definitions.
    :rtype: list[dict[str, Any]]
    """
    scia_load_cases = []

    for tandem in tandem_data:
        patch_loads = []
        # Loop over all loads in the tandem dict (standard structure)
        for load in tandem.get("loads", []):
            for wheel_coords_2d in load.get("wheels", []):
                wheel_coords_3d = convert_wheel_coordinates_to_3d(wheel_coords_2d)
                aligned_coords = align_bridge_coordinates_to_scia(wheel_coords_3d)
                patch_loads.append(
                    {
                        "corners": aligned_coords,
                        "load_value": load.get("load", 0.0),
                    }
                )

        scia_load_cases.append(
            {
                "load_case": tandem["load_case"],
                "patch_loads": patch_loads,
            }
        )

    return scia_load_cases


def create_node_and_thickness_dict(params: Any) -> tuple[dict[str, list[float]], dict[str, float]]:  # noqa: ANN401
    """
    Create node positions and thickness data from bridge parameters.

    This function extracts the geometric information needed to create SCIA nodes and plates.
    It returns pure Python data structures without creating actual SCIA objects.

    :param params: Bridge parameters
    :returns: (nodes_dict, thickness_dict)
    :rtype: tuple[dict[str, list[float]], dict[str, float]]
    """
    dynamic_arrays = len(params.bridge_segments_array)
    nodes_dict = {}
    thickness_dict = {}

    def calculate_cross_section_positions(segment_idx: int) -> dict[str, float]:
        """Calculate node positions for cross section."""
        l_sum = sum(item.l for item in params.bridge_segments_array[: segment_idx + 1])
        segment = params.bridge_segments_array[segment_idx]

        return {
            "x": l_sum,
            "z1_left": segment.bz1 + segment.bz2 / 2,
            "z1_right": segment.bz2 / 2,
            "z3_left": -segment.bz2 / 2,
            "z3_right": -segment.bz3 - segment.bz2 / 2,
        }

    # Create first cross section
    if dynamic_arrays > 0:
        pos = calculate_cross_section_positions(0)
        nodes_dict.update(
            {
                "K_dek:1_1": [pos["x"], pos["z1_left"], 0],
                "K_dek:1_2": [pos["x"], pos["z1_right"], 0],
                "K_dek:1_3": [pos["x"], pos["z3_left"], 0],
                "K_dek:1_4": [pos["x"], pos["z3_right"], 0],
            }
        )

    # Create remaining cross sections and thickness data
    for dynamic_array in range(1, dynamic_arrays):
        pos = calculate_cross_section_positions(dynamic_array)
        d_num = dynamic_array + 1

        nodes_dict.update(
            {
                f"K_dek:{d_num}_1": [pos["x"], pos["z1_left"], 0],
                f"K_dek:{d_num}_2": [pos["x"], pos["z1_right"], 0],
                f"K_dek:{d_num}_3": [pos["x"], pos["z3_left"], 0],
                f"K_dek:{d_num}_4": [pos["x"], pos["z3_right"], 0],
            }
        )

        thickness_dict.update(
            {
                f"Z1_{dynamic_array}": params.bridge_segments_array[dynamic_array].dz,
                f"Z2_{dynamic_array}": params.bridge_segments_array[dynamic_array].dz_2,
                f"Z3_{dynamic_array}": params.bridge_segments_array[dynamic_array].dz,
            }
        )

    return nodes_dict, thickness_dict
