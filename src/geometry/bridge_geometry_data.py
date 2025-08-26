"""
Bridge geometry data extraction functions.

This module provides functions to extract geometric information from bridge parameters
without dependencies on SCIA or IDEA specific modules, to avoid circular imports.
"""

from typing import Any


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
