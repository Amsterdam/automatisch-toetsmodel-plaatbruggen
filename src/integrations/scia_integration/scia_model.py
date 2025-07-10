"""
SCIA model definition utilities.

This module handles the creation of definitions for complete SCIA bridge models, including geometry, nodes, and plates.
It is independent of the VIKTOR SDK.
"""

from typing import Any

# Import geometry extraction functions from dedicated module
from .scia_bridge_geometry import create_node_and_thickness_dict
from .scia_definitions import MaterialDefinition, NodeDefinition, PlateDefinition

# Import load application functions from dedicated module


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

    return {
        "nodes": node_defs,
        "materials": [material_def],
        "plates": plate_defs,
    }


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
    # Placeholder for future additions
    definitions["load_groups"] = []
    definitions["load_cases"] = []
    definitions["surface_loads"] = []
    definitions["load_combinations"] = []
    return definitions
