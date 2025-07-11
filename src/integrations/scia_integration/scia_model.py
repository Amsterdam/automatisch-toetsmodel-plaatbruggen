"""
SCIA model definition utilities.

This module handles the creation of definitions for complete SCIA bridge models, including geometry, nodes, and plates.
It is independent of the VIKTOR SDK.
"""

from typing import Any

from .scia_bridge_geometry import (
    create_node_and_thickness_dict,
)
from .scia_load_cases import (
    create_all_standard_load_cases,
)
from .scia_load_combinations import create_standard_load_combinations
from .scia_load_group import create_all_load_groups
from .scia_loads import add_theoretical_tandem_loads
from .scia_model_builder import SciaModelBuilder
from .scia_supports import define_line_supports


def _define_bridge_geometry(params: Any, builder: SciaModelBuilder) -> list[str]:
    """
    Define the complete bridge geometry in the SCIA model.

    :param params: The VIKTOR parametrization object.
    :param builder: The SCIA model builder.
    :return: A list of the created plate names.
    """
    node_and_thickness_dict = create_node_and_thickness_dict(params)

    # Add default material
    builder.add_material("C30/37")

    # Add all nodes to the model
    for node_name, node_data in node_and_thickness_dict["nodes"].items():
        builder.add_node(name=node_name, x=node_data["x"], y=node_data["y"], z=node_data["z"])

    # Add all plates to the model
    plate_names = []
    for plate_name, plate_data in node_and_thickness_dict["plates"].items():
        builder.add_plate(
            name=plate_name,
            corner_node_names=plate_data["node_names"],
            thickness=plate_data["thickness"],
            material_name="C30/37",
        )
        plate_names.append(plate_name)

    return plate_names


def build_complete_bridge_model(params: Any, builder: SciaModelBuilder) -> None:
    """
    Build a complete SCIA bridge model, including geometry, loads, and combinations.

    This function orchestrates the entire model creation process by calling the relevant
    functions for each part of the model.

    :param params: The VIKTOR parametrization object.
    :param builder: The SCIA model builder.
    """
    # Step 1: Create geometry (nodes and plates)
    plate_names = _define_bridge_geometry(params, builder)

    # Step 2: Define line supports on the bridge edges
    define_line_supports(builder, plate_names)

    # Step 3: Create load groups and standard load cases
    create_all_load_groups(builder)
    create_all_standard_load_cases(builder)

    # Step 4: Add tandem loads and get their case names
    tandem_case_names = add_theoretical_tandem_loads(params, builder, plate_names)

    # Step 5: Create load combinations
    # We assume BG1001 is always the self-weight case
    create_standard_load_combinations(builder, self_weight_case="BG1001", tandem_cases=tandem_case_names)
