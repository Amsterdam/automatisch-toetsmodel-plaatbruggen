"""
Module for constructing SCIA models from definitions.

This module acts as a bridge between the pure Python definitions from the src layer
and the VIKTOR SDK's SCIA integration. It translates the definition objects into
actual scia.Model components.
"""

from typing import Any, TypeAlias

from src.integrations.scia_integration.scia_definitions import (
    LoadCaseDefinition,
    LoadCombinationDefinition,
    LoadGroupDefinition,
    SurfaceLoadDefinition,
)
from src.integrations.scia_integration.scia_load_combinations import SciaLoadCombination

# Global VIKTOR imports with error handling for CI/testing environments
try:
    from viktor.external import scia

    VIKTOR_AVAILABLE = True
except ImportError:
    # Mock scia module for environments without VIKTOR SDK
    scia = None  # type: ignore[misc,assignment]
    VIKTOR_AVAILABLE = False

# Type aliases for SCIA objects
SciaModel: TypeAlias = Any
SciaLoadGroup: TypeAlias = Any
SciaLoadCase: TypeAlias = Any


def _check_scia_availability() -> None:
    """Check if VIKTOR SCIA module is available."""
    if not VIKTOR_AVAILABLE or scia is None:
        raise ImportError("VIKTOR SCIA module not available. This function requires VIKTOR SDK.")


def create_load_group_from_definition(model: SciaModel, definition: LoadGroupDefinition) -> SciaLoadGroup:
    """
    Create a SCIA load group from a LoadGroupDefinition.

    :param model: The SCIA model object.
    :param definition: The LoadGroupDefinition object.
    :return: The created SCIA load group object.
    :rtype: scia.LoadGroup
    """
    _check_scia_availability()
    load_option_map = {
        "PERMANENT": scia.LoadGroup.LoadOption.PERMANENT,
        "VARIABLE": scia.LoadGroup.LoadOption.VARIABLE,
    }
    relation_map = {
        "STANDARD": scia.LoadGroup.RelationOption.STANDARD,
        "EXCLUSIVE": scia.LoadGroup.RelationOption.EXCLUSIVE,
    }
    load_type_map = {
        "CAT_G": scia.LoadGroup.LoadTypeOption.CAT_G,
        "CAT_H": scia.LoadGroup.LoadTypeOption.CAT_H,
        "VARIABLE_LOADS": scia.LoadGroup.LoadTypeOption.VARIABLE_LOADS,
    }

    return model.create_load_group(
        definition.name,
        load_option_map[definition.load_option],
        relation_map[definition.relation],
        load_type_map[definition.load_type],
    )


def create_load_case_from_definition(model: SciaModel, definition: LoadCaseDefinition, load_groups: dict[str, SciaLoadGroup]) -> SciaLoadCase:
    """
    Create a SCIA load case from a LoadCaseDefinition.

    :param model: The SCIA model object.
    :param definition: The LoadCaseDefinition object.
    :param load_groups: A dictionary of existing SCIA load groups.
    :return: The created SCIA load case object.
    :rtype: scia.LoadCase
    """
    _check_scia_availability()
    if definition.group_name not in load_groups:
        raise ValueError(f"Load group '{definition.group_name}' not found in the provided load groups.")

    group = load_groups[definition.group_name]

    if definition.case_type == "PERMANENT":
        permanent_type_map = {
            "SELF_WEIGHT": scia.LoadCase.PermanentLoadType.SELF_WEIGHT,
            "STANDARD": scia.LoadCase.PermanentLoadType.STANDARD,
            "PRIMARY_EFFECT": scia.LoadCase.PermanentLoadType.PRIMARY_EFFECTS_OF_PRESTRESSING,
        }
        if definition.permanent_type is None:
            raise ValueError("Permanent load case type must be specified.")
        return model.create_permanent_load_case(
            definition.name,
            definition.description,
            group,
            permanent_type_map[definition.permanent_type],
        )

    if definition.case_type == "VARIABLE":
        variable_type_map = {
            "STATIC": scia.LoadCase.VariableLoadType.STATIC,
            "PRIMARY_EFFECT": scia.LoadCase.VariableLoadType.PRIMARY_EFFECTS_OF_PRESTRESSING,
        }
        specification_map = {
            "STANDARD": scia.LoadCase.Specification.STANDARD,
            "STATIC_WIND": scia.LoadCase.Specification.STATIC_WIND,
            "SNOW": scia.LoadCase.Specification.SNOW,
            "TEMPERATURE": scia.LoadCase.Specification.TEMPERATURE,
            "EARTHQUAKE": scia.LoadCase.Specification.EARTHQUAKE,
        }
        duration_map = {
            "INSTANTANEOUS": scia.LoadCase.Duration.INSTANTANEOUS,
            "SHORT": scia.LoadCase.Duration.SHORT,
            "MEDIUM": scia.LoadCase.Duration.MEDIUM,
            "LONG": scia.LoadCase.Duration.LONG,
        }
        if definition.variable_type is None:
            raise ValueError("Variable load case type must be specified.")
        if definition.specification is None:
            raise ValueError("Variable load case specification must be specified.")
        if definition.duration is None:
            raise ValueError("Variable load case duration must be specified.")
        return model.create_variable_load_case(
            definition.name,
            definition.description,
            group,
            variable_type_map[definition.variable_type],
            specification_map[definition.specification],
            duration_map[definition.duration],
        )

    raise ValueError(f"Unsupported load case type: {definition.case_type}")


def create_patch_surface_load(
    model: SciaModel,
    load_case: SciaLoadCase,
    corner_points: list[tuple[float, float, float]],
    load_value: float,
    load_name: str = "PatchLoad",
) -> None:
    """
    Create a free surface load on a 4-point patch in the SCIA model.

    :param model: The SCIA model object.
    :param load_case: The SCIA load case object for the load application.
    :param corner_points: List of 4 corner coordinates [(x1,y1,z1), ...].
    :param load_value: Load magnitude in [N/m²] (positive = downward).
    :param load_name: Name identifier for the load.
    """
    _check_scia_availability()
    if len(corner_points) != 4:
        raise ValueError(f"Exactly 4 corner points required, got {len(corner_points)}")

    # Convert 3D corner points to 2D for free surface load
    points_2d = [(p[0], p[1]) for p in corner_points]

    model.create_free_surface_load(
        name=load_name,
        load_case=load_case,
        direction=scia.FreeSurfaceLoad.Direction.Z,
        q1=load_value,
        points=points_2d,
        distribution=scia.FreeSurfaceLoad.Distribution.UNIFORM,
    )


def create_load_combination_from_definition(
    model: SciaModel, combo_def: LoadCombinationDefinition, load_cases: dict[str, SciaLoadCase]
) -> SciaLoadCombination:
    """
    Create a SCIA load combination from a LoadCombinationDefinition.

    :param model: The SCIA model object.
    :param combo_def: The LoadCombinationDefinition object.
    :param load_cases: A dictionary of existing SCIA load cases.
    :return: The created SCIA load combination object.
    """
    _check_scia_availability()
    combination_type_map = {
        "ULS": scia.LoadCombination.Type.EN_ULS_SET_B,
        "SLS_CHAR": scia.LoadCombination.Type.EN_SLS_CHARACTERISTIC,
        "SLS_FREQ": scia.LoadCombination.Type.EN_SLS_FREQUENT,
        "SLS_QUASI": scia.LoadCombination.Type.EN_SLS_QUASI_PERMANENT,
    }

    case_factors = {}
    for case_name, factor in combo_def.load_case_factors.items():
        if case_name not in load_cases:
            raise ValueError(f"Load case '{case_name}' not found in the provided load cases.")
        case_factors[load_cases[case_name]] = factor

    combo_type = combination_type_map[combo_def.combination_type.value]

    return model.create_load_combination(
        name=combo_def.name,
        combination_type=combo_type,
        case_factors=case_factors,
        description=combo_def.description,
    )


def build_load_infrastructure(model: SciaModel, definitions: dict[str, Any]) -> dict[str, dict]:
    """
    Build the entire load infrastructure (groups, cases) from definitions.

    This function orchestrates the creation of SCIA objects from their pure
    Python definitions.

    :param model: The scia.Model object to build upon.
    :param definitions: A dictionary containing 'load_group_definitions' and
                        'basic_load_case_definitions'.
    :return: A dictionary containing the created 'load_groups' and 'load_cases'.
    """
    # 1. Build Load Groups
    created_load_groups = {}
    for name, group_def in definitions["load_group_definitions"].items():
        created_load_groups[name] = create_load_group_from_definition(model, group_def)

    # 2. Build Load Cases
    created_load_cases = {}
    for name, case_def in definitions["basic_load_case_definitions"].items():
        # The builder function will find the correct group object from the created_load_groups dict
        created_load_cases[name] = create_load_case_from_definition(model, case_def, created_load_groups)

    return {"load_groups": created_load_groups, "load_cases": created_load_cases}


def build_geometry_from_definitions(model: SciaModel, definitions: dict[str, list]) -> dict[str, dict]:
    """
    Build the geometry (nodes, materials, plates) from definitions.

    :param model: The scia.Model object to build upon.
    :param definitions: A dictionary containing 'nodes', 'materials', and 'plates' definitions.
    :return: A dictionary containing the created 'nodes', 'materials', and 'plates'.
    """
    _check_scia_availability()

    # 1. Build Materials
    created_materials = {mat_def.name: model.create_material(mat_def.material_id, mat_def.name) for mat_def in definitions["materials"]}

    # 2. Build Nodes
    created_nodes = {node_def.name: model.create_node(node_def.name, node_def.x, node_def.y, node_def.z) for node_def in definitions["nodes"]}

    # 3. Build Plates
    created_plates = {}
    for plate_def in definitions["plates"]:
        corner_nodes = [created_nodes[name] for name in plate_def.corner_node_names]
        material = created_materials[plate_def.material_name]
        created_plates[plate_def.name] = model.create_plane(
            corner_nodes,
            plate_def.thickness,
            name=plate_def.name,
            material=material,
        )

    return {"nodes": created_nodes, "materials": created_materials, "plates": created_plates}


def build_surface_loads_from_definitions(
    model: SciaModel,
    definitions: list[SurfaceLoadDefinition],
    load_cases: dict[str, SciaLoadCase],
) -> list:
    """
    Build surface loads from their definitions.

    :param model: The scia.Model object to build upon.
    :param definitions: A list of SurfaceLoadDefinition objects.
    :param load_cases: A dictionary of already created scia.LoadCase objects.
    :return: A list of the created scia.FreeSurfaceLoad objects.
    """
    _check_scia_availability()
    created_loads = []
    for load_def in definitions:
        load_case = load_cases.get(load_def.load_case_name)
        if not load_case:
            raise ValueError(f"Load case '{load_def.load_case_name}' not found for surface load '{load_def.name}'.")

        xy_points = [(x, y) for x, y, z in load_def.corner_points]

        def polygon_area(points: list[tuple[float, float]]) -> float:
            n = len(points)
            area = 0.0
            for i in range(n):
                j = (i + 1) % n
                area += points[i][0] * points[j][1]
                area -= points[j][0] * points[i][1]
            return abs(area) / 2.0

        patch_area = polygon_area(xy_points)
        total_load = load_def.load_value * patch_area

        created_loads.append(
            model.create_free_surface_load(
                name=load_def.name,
                load_case=load_case,
                direction=scia.FreeSurfaceLoad.Direction.Z,
                q1=total_load,
                points=xy_points,
                distribution=scia.FreeSurfaceLoad.Distribution.UNIFORM,
            )
        )
    return created_loads


def build_load_combinations_from_definitions(
    model: SciaModel,
    definitions: list[LoadCombinationDefinition],
    load_cases: dict[str, SciaLoadCase],
) -> list:
    """
    Build load combinations from their definitions.

    :param model: The scia.Model object to build upon.
    :param definitions: A list of LoadCombinationDefinition objects.
    :param load_cases: A dictionary of already created scia.LoadCase objects.
    :return: A list of the created scia.LoadCombination objects.
    """
    _check_scia_availability()

    combination_type_map = {
        "ULS": scia.LoadCombination.Type.EN_ULS_SET_B,
        "ULS_SET_B": scia.LoadCombination.Type.EN_ULS_SET_B,
        "ULS_SET_C": scia.LoadCombination.Type.EN_ULS_SET_C,
        "ENVELOPE_ULS": scia.LoadCombination.Type.ENVELOPE_ULTIMATE,
        "LINEAR_ULS": scia.LoadCombination.Type.LINEAR_ULTIMATE,
        "SLS": scia.LoadCombination.Type.EN_SLS_CHAR,
        "SLS_CHAR": scia.LoadCombination.Type.EN_SLS_CHARACTERISTIC,
        "SLS_FREQ": scia.LoadCombination.Type.EN_SLS_FREQUENT,
        "SLS_QUASI": scia.LoadCombination.Type.EN_SLS_QUASI_PERMANENT,
        "ENVELOPE_SLS": scia.LoadCombination.Type.ENVELOPE_SERVICEABILITY,
        "LINEAR_SLS": scia.LoadCombination.Type.LINEAR_SERVICEABILITY,
        "ACCIDENTAL": scia.LoadCombination.Type.EN_ACC_ONE,
        "ACCIDENTAL_1": scia.LoadCombination.Type.EN_ACC_ONE,
        "ACCIDENTAL_2": scia.LoadCombination.Type.EN_ACC_TWO,
        "SEISMIC": scia.LoadCombination.Type.EN_SEISMIC,
    }

    created_combinations = []
    for combo_def in definitions:
        scia_case_factors = {load_cases[name]: factor for name, factor in combo_def.load_case_factors.items()}
        combo_type = combination_type_map[combo_def.combination_type]
        created_combinations.append(
            model.create_load_combination(
                combo_def.name,
                combo_type,
                scia_case_factors,
                description=combo_def.description,
            )
        )
    return created_combinations


def build_scia_model_from_definitions(definitions: dict[str, list]) -> SciaModel:
    """
    Build a complete SCIA model from a set of definitions.

    This is the master builder function that orchestrates the entire model
    construction process.

    :param definitions: A dictionary containing all model part definitions.
    :return: A fully constructed scia.Model object.
    """
    _check_scia_availability()
    model = scia.Model()

    # 1. Build Geometry
    build_geometry_from_definitions(model, definitions)

    # 2. Build Load Infrastructure (Groups and Cases)
    # Re-structure definitions for the builder
    load_infra_defs = {
        "load_group_definitions": {group.name: group for group in definitions["load_groups"]},
        "basic_load_case_definitions": {case.name: case for case in definitions["load_cases"]},
    }
    load_infra_parts = build_load_infrastructure(model, load_infra_defs)
    all_load_cases = load_infra_parts["load_cases"]

    # 3. Build Surface Loads
    build_surface_loads_from_definitions(model, definitions["surface_loads"], all_load_cases)

    # 4. Build Load Combinations
    build_load_combinations_from_definitions(model, definitions["load_combinations"], all_load_cases)

    return model
