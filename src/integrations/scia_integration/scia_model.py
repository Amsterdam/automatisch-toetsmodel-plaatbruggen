"""
SCIA model definition utilities.

This module handles the creation of complete SCIA bridge models by driving the
SciaModelBuilder interface. It is independent of the VIKTOR SDK.
"""

from typing import Any

from .scia_bridge_geometry import create_node_and_thickness_dict
from .scia_load_cases import (
    create_all_load_cases,
)
from .scia_load_combinations import create_all_load_combinations
from .scia_load_group import create_all_load_groups
from .scia_loads import create_all_loads
from .scia_model_interface import SciaModelBuilder
from .scia_results import create_result_classes_for_bridge
from .scia_supports import create_all_supports


def create_bridge_geometry(builder: SciaModelBuilder, params: Any) -> list[str]:  # noqa: ANN401
    """
    Define and create the geometry for a SCIA bridge model using the builder.

    :param builder: The SCIA model builder instance.
    :param params: Bridge parameters.
    :return: An ordered list of the created plate names.
    :rtype: list[str]
    """
    # Define and create the material
    material_name = "C30/37"
    builder.create_material(name=material_name)

    # Get geometry data (node coordinates and plate thicknesses)
    nodes_dict, thickness_dict = create_node_and_thickness_dict(params)

    # Create nodes
    for name, coords in nodes_dict.items():
        builder.create_node(name=name, x=coords[0], y=coords[1], z=coords[2])

    # Create plates and collect their names
    plate_names = []
    dynamic_arrays = len(params.bridge_segments_array)

    # Create plates between cross sections
    for span in range(1, dynamic_arrays):
        next_span = span + 1

        # Zone 1 plate
        z1_thickness = thickness_dict.get(f"Z1_{span}")
        if z1_thickness is None:
            raise ValueError(f"Thickness for plate Z1_{span} not found.")
        plate_name_z1 = f"Z1_{span}"
        builder.create_plate(
            name=plate_name_z1,
            corner_node_names=[
                f"K_dek:{span}_1",
                f"K_dek:{next_span}_1",
                f"K_dek:{next_span}_2",
                f"K_dek:{span}_2",
            ],
            thickness=z1_thickness,
            material_name=material_name,
        )
        plate_names.append(plate_name_z1)

        # Zone 2 plate
        z2_thickness = thickness_dict.get(f"Z2_{span}")
        if z2_thickness is None:
            raise ValueError(f"Thickness for plate Z2_{span} not found.")
        plate_name_z2 = f"Z2_{span}"
        builder.create_plate(
            name=plate_name_z2,
            corner_node_names=[
                f"K_dek:{span}_2",
                f"K_dek:{next_span}_2",
                f"K_dek:{next_span}_3",
                f"K_dek:{span}_3",
            ],
            thickness=z2_thickness,
            material_name=material_name,
        )
        plate_names.append(plate_name_z2)

        # Zone 3 plate
        z3_thickness = thickness_dict.get(f"Z3_{span}")
        if z3_thickness is None:
            raise ValueError(f"Thickness for plate Z3_{span} not found.")
        plate_name_z3 = f"Z3_{span}"
        builder.create_plate(
            name=plate_name_z3,
            corner_node_names=[
                f"K_dek:{span}_3",
                f"K_dek:{next_span}_3",
                f"K_dek:{next_span}_4",
                f"K_dek:{span}_4",
            ],
            thickness=z3_thickness,
            material_name=material_name,
        )
        plate_names.append(plate_name_z3)

    return plate_names


def define_complete_bridge_model(builder: SciaModelBuilder, params: Any) -> None:  # noqa: ANN401
    """
    Define and build a complete SCIA bridge model using the provided builder.

    This function orchestrates the entire model creation process, including
    geometry, loads, and combinations, by calling the builder's methods.

    :param builder: The SCIA model builder instance.
    :param params: Bridge parameters.
    """
    # 1. Build Geometry and get back the ordered list of plate names
    plate_names = create_bridge_geometry(builder, params)

    # 2. Build Line Supports
    create_all_supports(builder, plate_names)

    # 3. Build Load Groups
    create_all_load_groups(builder)

    # 4. Build ALL Load Cases (standard and dynamic)
    all_load_cases = create_all_load_cases(builder, params)

    # 5. Apply all loads to the now-existing cases
    create_all_loads(builder, params, all_load_cases)

    # 6. Build Load Combinations (after loads are applied)
    create_all_load_combinations(builder, all_load_cases)

    # 7. Create Result Classes to tell SCIA which combinations to analyze
    if hasattr(builder, "load_combinations") and builder.load_combinations:
        create_result_classes_for_bridge(builder, builder.load_combinations)
