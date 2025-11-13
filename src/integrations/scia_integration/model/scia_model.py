"""
SCIA model definition utilities.

This module handles the creation of complete SCIA bridge models by driving the
SciaModelBuilder interface. It is independent of the VIKTOR SDK.
"""

from typing import Any

from app.bridge.utils import _validate_first_and_last_supports
from src.geometry.bridge_geometry_data import create_node_and_thickness_dict
from src.integrations.idea_integration.constants.materials import DEFAULT_CONCRETE_STRENGTH_CLASS
from src.integrations.scia_integration.load_system.scia_load_cases import (
    create_all_load_cases,
)
from src.integrations.scia_integration.load_system.scia_load_combinations import create_all_load_combinations
from src.integrations.scia_integration.load_system.scia_load_group import create_all_load_groups
from src.integrations.scia_integration.results.scia_result_classes import create_all_result_classes
from src.integrations.scia_integration.scia_loads import create_all_loads

from .scia_model_interface import SciaModelBuilder
from .scia_section_on_plane import create_all_sections_on_plane, create_section_definitions
from .scia_supports import create_all_supports


def create_bridge_geometry(builder: SciaModelBuilder, params: Any) -> list[str]:  # noqa: ANN401
    """
    Define and create the geometry for a SCIA bridge model using the builder.

    :param builder: The SCIA model builder instance.
    :param params: Bridge parameters.
    :return: An ordered list of the created plate names.
    :rtype: list[str]
    """
    # Extract material properties
    concrete_strength_value = getattr(params, "concrete_strength_class", "")
    concrete_strength_class = concrete_strength_value.strip() if concrete_strength_value else DEFAULT_CONCRETE_STRENGTH_CLASS
    if not concrete_strength_class:
        concrete_strength_class = DEFAULT_CONCRETE_STRENGTH_CLASS

    # Define and create the material
    material_name = concrete_strength_class
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
    # 0. Validate support configuration before defining the model
    _validate_first_and_last_supports(params)

    # 1. Build Geometry and get back the ordered list of plate names
    plate_names = create_bridge_geometry(builder, params)
    section_definitions = create_section_definitions(params)

    # 2. Extract support types from parameters
    support_types = None
    try:
        # Access support types from the parametrization using the DynamicArray name
        if hasattr(params, "bridge_segments_array") and params.bridge_segments_array:
            support_types = [segment.is_support for segment in params.bridge_segments_array]
    except AttributeError:
        pass  # Will use default fallback in create_all_supports

    # 3. Build Line Supports with user-specified support types
    create_all_supports(builder, plate_names, support_types)

    # 4. Build Sections on Plane
    create_all_sections_on_plane(builder, section_definitions)

    # 5. Build Load Groups
    create_all_load_groups(builder)

    # 6. Build ALL Load Cases (standard and dynamic)
    all_load_cases = create_all_load_cases(builder, params)

    # 7. Apply all loads to the now-existing cases
    create_all_loads(builder, params, all_load_cases)

    # 8. Build Load Combinations (after loads are applied)
    all_load_combinations = create_all_load_combinations(params, builder, all_load_cases)

    # 9. Create Result Classes to tell SCIA which combinations to analyze
    create_all_result_classes(params, builder, all_load_combinations)
