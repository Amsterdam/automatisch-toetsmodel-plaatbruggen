"""
SCIA model definition utilities.

This module handles the creation of definitions for complete SCIA bridge models, including geometry, nodes, and plates.
It is independent of the VIKTOR SDK.
"""

from typing import Any

# Import geometry extraction functions from dedicated module
from .scia_bridge_geometry import create_node_and_thickness_dict
from .scia_definitions import (
    LineSupportDefinition,
    MaterialDefinition,
    NodeDefinition,
    PlateDefinition,
)
from .scia_load_cases import create_basic_permanent_load_cases
from .scia_load_combinations import create_standard_load_combinations
from .scia_load_group import create_all_load_groups
from .scia_loads import add_theoretical_tandem_loads


def _define_bridge_geometry(params: Any) -> dict[str, list]:  # noqa: ANN401
    """
    Define the geometry for a SCIA bridge model (nodes, materials, plates).

    :param params: Bridge parameters.
    :return: A dictionary containing lists of node, material, and plate definitions.
    :rtype: dict[str, list]
    """
    # Define the material
    material_def = MaterialDefinition(name="C30/37")

    # Get geometry data (node coordinates and plate thicknesses)
    nodes_dict, thickness_dict = create_node_and_thickness_dict(params)

    node_defs = [NodeDefinition(name=name, x=coords[0], y=coords[1], z=coords[2]) for name, coords in nodes_dict.items()]

    plate_defs = []
    dynamic_arrays = len(params.bridge_segments_array)

    # Create plates between cross sections
    for span in range(1, dynamic_arrays):
        next_span = span + 1

        # Zone 1 plate
        z1_thickness = thickness_dict.get(f"Z1_{span}")
        if z1_thickness is None:
            raise ValueError(f"Thickness for plate Z1_{span} not found.")
        plate_defs.append(
            PlateDefinition(
                name=f"Z1_{span}",
                corner_node_names=[
                    f"K_dek:{span}_1",
                    f"K_dek:{next_span}_1",
                    f"K_dek:{next_span}_2",
                    f"K_dek:{span}_2",
                ],
                thickness=z1_thickness,
                material_name=material_def.name,
            )
        )
        # Zone 2 plate
        z2_thickness = thickness_dict.get(f"Z2_{span}")
        if z2_thickness is None:
            raise ValueError(f"Thickness for plate Z2_{span} not found.")
        plate_defs.append(
            PlateDefinition(
                name=f"Z2_{span}",
                corner_node_names=[
                    f"K_dek:{span}_2",
                    f"K_dek:{next_span}_2",
                    f"K_dek:{next_span}_3",
                    f"K_dek:{span}_3",
                ],
                thickness=z2_thickness,
                material_name=material_def.name,
            )
        )
        # Zone 3 plate
        z3_thickness = thickness_dict.get(f"Z3_{span}")
        if z3_thickness is None:
            raise ValueError(f"Thickness for plate Z3_{span} not found.")
        plate_defs.append(
            PlateDefinition(
                name=f"Z3_{span}",
                corner_node_names=[
                    f"K_dek:{span}_3",
                    f"K_dek:{next_span}_3",
                    f"K_dek:{next_span}_4",
                    f"K_dek:{span}_4",
                ],
                thickness=z3_thickness,
                material_name=material_def.name,
            )
        )

    return {
        "nodes": node_defs,
        "materials": [material_def],
        "plates": plate_defs,
    }


def _define_line_supports(plate_definitions: list[PlateDefinition]) -> list[LineSupportDefinition]:
    """
    Define line supports on the first and last edges of the bridge deck.

    :param plate_definitions: A list of PlateDefinition objects.
    :return: A list of LineSupportDefinition objects.
    """
    if not plate_definitions:
        return []

    # Determine the last section number. It is max_span_number + 1.
    max_span_number = 0
    for plate_def in plate_definitions:
        try:
            span_num = int(plate_def.name.split("_")[1])
            if span_num > max_span_number:
                max_span_number = span_num
        except (IndexError, ValueError):
            continue  # Should not happen with current naming convention
    last_section_number = max_span_number + 1

    # The logic from `get_line_support_edges_for_bridge` assumes an ordered list of planes.
    # The plate definitions are created span-by-span, zone-by-zone (Z1, Z2, Z3).
    # This order is consistent and can be used directly.
    support_defs = []

    # Supports at the start of the bridge (cross section 1)
    for plate_def in plate_definitions[:3]:
        zone_number = int(plate_def.name.split("_")[0][1:])
        support_defs.append(
            LineSupportDefinition(
                name=f"SLB_opleg_as_1:{zone_number}",
                plane_name=plate_def.name,
                edge_index=4,
                freedom={"x": "FLEXIBLE", "y": "FLEXIBLE", "z": "RIGID", "rx": "FREE", "ry": "RIGID", "rz": "RIGID"},
                stiffness={"stiffness_x": 1e7, "stiffness_y": 1e6},
            )
        )

    # Supports at the end of the bridge (last 3 plates, edge index 2)
    for plate_def in plate_definitions[-3:]:
        zone_number = int(plate_def.name.split("_")[0][1:])
        support_defs.append(
            LineSupportDefinition(
                name=f"SLB_opleg_as_{last_section_number}:{zone_number}",
                plane_name=plate_def.name,
                edge_index=2,
                freedom={"x": "FLEXIBLE", "y": "FLEXIBLE", "z": "RIGID", "rx": "FREE", "ry": "RIGID", "rz": "RIGID"},
                stiffness={"stiffness_x": 1e7, "stiffness_y": 1e6},
            )
        )

    return support_defs


def define_complete_bridge_model(params: Any) -> dict[str, list]:  # noqa: ANN401
    """
    Define a complete SCIA bridge model, including geometry, loads, etc.

    This function aggregates definitions for geometry, loads, and combinations.
    Currently, it only generates the geometry.

    :param params: Bridge parameters.
    :return: A dictionary containing all model part definitions.
    :rtype: dict[str, list]
    """
    definitions = _define_bridge_geometry(params)
    definitions["line_supports"] = _define_line_supports(definitions["plates"])

    # 1. Define Load Groups
    load_group_defs = create_all_load_groups()
    definitions["load_groups"] = list(load_group_defs.values())

    # 2. Define basic Load Cases
    # Permanent loads
    permanent_group_name = load_group_defs["permanent"].name
    permanent_case_defs = create_basic_permanent_load_cases(permanent_group_name)
    definitions["load_cases"] = list(permanent_case_defs.values())

    # 3. Define Tandem Loads and their Load Cases
    traffic_group_name = load_group_defs["ts_lane_1"].name  # Use TS Lane 1 group for now
    tandem_load_defs = add_theoretical_tandem_loads(params, traffic_group_name)
    print(tandem_load_defs)
    definitions["load_cases"].extend(tandem_load_defs["load_case_definitions"])
    definitions["surface_loads"] = tandem_load_defs["surface_load_definitions"]

    # 4. Define Load Combinations
    self_weight_case_name = permanent_case_defs["self_weight"].name
    tandem_case_names = [case.name for case in tandem_load_defs["load_case_definitions"]]

    combination_defs = create_standard_load_combinations(self_weight_case_name, tandem_case_names)
    definitions["load_combinations"] = combination_defs

    return definitions
