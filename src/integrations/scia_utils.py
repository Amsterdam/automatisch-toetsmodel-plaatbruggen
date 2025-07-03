"""
SCIA Engineer utility functions for creating loads, load cases, and load combinations.

FRAMEWORK USAGE:
================
1. Create Load Group: create_load_group_by_type()
2. Create Load Case: create_load_case_complete()
3. Create Load Combination: create_load_combination_by_type()
4. Apply Loads: create_patch_surface_load()

See VIKTOR documentation for detailed parameters:
- LoadGroup: https://docs.viktor.ai/sdk/api/external/scia/#_LoadGroup
- LoadCase: https://docs.viktor.ai/sdk/api/external/scia/#_LoadCase
- LoadCombination: https://docs.viktor.ai/sdk/api/external/scia/#_LoadCombination
- Model methods: https://docs.viktor.ai/sdk/api/external/scia/#Model
"""

from typing import Any, TypeAlias

# Conditional import for VIKTOR SCIA module
try:
    from viktor.external import scia
except ImportError:
    # Mock scia module for environments without VIKTOR SDK
    scia = None

# Type aliases for SCIA objects
SciaModel: TypeAlias = Any
SciaNode: TypeAlias = Any
SciaPlane: TypeAlias = Any
SciaLoadGroup: TypeAlias = Any
SciaLoadCase: TypeAlias = Any
SciaLoadCombination: TypeAlias = Any
SciaFreeSurfaceLoad: TypeAlias = Any


def _check_scia_availability() -> None:
    """Check if VIKTOR SCIA module is available."""
    if scia is None:
        raise ImportError("VIKTOR SCIA module not available. This function requires VIKTOR SDK.")


def create_load_group_by_type(
    model: SciaModel,
    load_option: str,
    group_name: str,
    relation: str = "STANDARD",
) -> SciaLoadGroup:
    """
    Create SCIA load group with standardized settings.

    :param model: SCIA model instance
    :param load_option: "PERMANENT", "VARIABLE", "ACCIDENTAL", "SEISMIC"
    :param group_name: Name for the load group
    :param relation: "STANDARD", "EXCLUSIVE", "TOGETHER"

    See: https://docs.viktor.ai/sdk/api/external/scia/#Model.create_load_group
    """
    _check_scia_availability()

    load_option_map = {
        "PERMANENT": scia.LoadGroup.LoadOption.PERMANENT,
        "VARIABLE": scia.LoadGroup.LoadOption.VARIABLE,
        "ACCIDENTAL": scia.LoadGroup.LoadOption.ACCIDENTAL,
        "SEISMIC": scia.LoadGroup.LoadOption.SEISMIC,
    }

    relation_map = {
        "STANDARD": scia.LoadGroup.RelationOption.STANDARD,
        "EXCLUSIVE": scia.LoadGroup.RelationOption.EXCLUSIVE,
        "TOGETHER": scia.LoadGroup.RelationOption.TOGETHER,
    }

    return model.create_load_group(group_name, load_option_map[load_option], relation_map[relation], scia.LoadGroup.LoadTypeOption.CAT_A)


def create_load_case_complete(
    model: SciaModel,
    load_group: SciaLoadGroup,
    case_name: str,
    description: str,
    case_type: str,
    **kwargs: str,
) -> SciaLoadCase:
    """
    Create SCIA load case with all parameters.

    :param model: SCIA model instance
    :param load_group: Load group that this case belongs to
    :param case_name: Name for the load case
    :param description: Description of the load case
    :param case_type: "PERMANENT" or "VARIABLE"
    :param kwargs: Optional parameters:
        - permanent_type: "SELF_WEIGHT", "STANDARD", "PRIMARY_EFFECT" (default: "STANDARD")
        - variable_type: "STATIC", "PRIMARY_EFFECT" (default: "STATIC")
        - specification: "STANDARD", "STATIC_WIND", "SNOW", "TEMPERATURE", "EARTHQUAKE" (default: "STANDARD")
        - duration: "INSTANTANEOUS", "SHORT", "MEDIUM", "LONG" (default: "SHORT")

    See: https://docs.viktor.ai/sdk/api/external/scia/#_LoadCase
    """
    _check_scia_availability()

    # Extract kwargs with defaults
    permanent_type = kwargs.get("permanent_type", "STANDARD")
    variable_type = kwargs.get("variable_type", "STATIC")
    specification = kwargs.get("specification", "STANDARD")
    duration = kwargs.get("duration", "SHORT")

    permanent_type_map = {
        "SELF_WEIGHT": scia.LoadCase.PermanentLoadType.SELF_WEIGHT,
        "STANDARD": scia.LoadCase.PermanentLoadType.STANDARD,
        "PRIMARY_EFFECT": scia.LoadCase.PermanentLoadType.PRIMARY_EFFECT,
    }

    variable_type_map = {
        "STATIC": scia.LoadCase.VariableLoadType.STATIC,
        "PRIMARY_EFFECT": scia.LoadCase.VariableLoadType.PRIMARY_EFFECT,
    }

    specification_map = {
        "STANDARD": scia.LoadCase.Specification.STANDARD,
        "TEMPERATURE": scia.LoadCase.Specification.TEMPERATURE,
        "STATIC_WIND": scia.LoadCase.Specification.STATIC_WIND,
        "EARTHQUAKE": scia.LoadCase.Specification.EARTHQUAKE,
        "SNOW": scia.LoadCase.Specification.SNOW,
    }

    duration_map = {
        "LONG": scia.LoadCase.Duration.LONG,
        "MEDIUM": scia.LoadCase.Duration.MEDIUM,
        "SHORT": scia.LoadCase.Duration.SHORT,
        "INSTANTANEOUS": scia.LoadCase.Duration.INSTANTANEOUS,
    }

    if case_type.upper() == "PERMANENT":
        return model.create_permanent_load_case(case_name, description, load_group, permanent_type_map[permanent_type])
    if case_type.upper() == "VARIABLE":
        return model.create_variable_load_case(
            case_name, description, load_group, variable_type_map[variable_type], specification_map[specification], duration_map[duration]
        )
    raise ValueError(f"Invalid case_type '{case_type}'. Use 'PERMANENT' or 'VARIABLE'")


def create_load_combination_by_type(
    model: SciaModel,
    combination_type: str,
    combination_name: str,
    load_cases: dict[SciaLoadCase, float],
    description: str = "",
) -> SciaLoadCombination:
    """
    Create SCIA load combination with standardized types.

    :param model: SCIA model instance
    :param combination_type: "ULS", "SLS_CHAR", "SLS_FREQ", "SLS_QUASI", "ACCIDENTAL", "SEISMIC", etc.
    :param combination_name: Name for the combination
    :param load_cases: Dictionary mapping load cases to their factors
    :param description: Optional description

    See: https://docs.viktor.ai/sdk/api/external/scia/#_LoadCombination
    """
    _check_scia_availability()

    combination_type_map = {
        # Ultimate Limit State
        "ULS": scia.LoadCombination.Type.EN_ULS_SET_B,
        "ULS_SET_B": scia.LoadCombination.Type.EN_ULS_SET_B,
        "ULS_SET_C": scia.LoadCombination.Type.EN_ULS_SET_C,
        "ENVELOPE_ULS": scia.LoadCombination.Type.ENVELOPE_ULTIMATE,
        "LINEAR_ULS": scia.LoadCombination.Type.LINEAR_ULTIMATE,
        # Serviceability Limit State
        "SLS": scia.LoadCombination.Type.EN_SLS_CHAR,
        "SLS_CHAR": scia.LoadCombination.Type.EN_SLS_CHAR,
        "SLS_FREQ": scia.LoadCombination.Type.EN_SLS_FREQ,
        "SLS_QUASI": scia.LoadCombination.Type.EN_SLS_QUASI,
        "ENVELOPE_SLS": scia.LoadCombination.Type.ENVELOPE_SERVICEABILITY,
        "LINEAR_SLS": scia.LoadCombination.Type.LINEAR_SERVICEABILITY,
        # Special cases
        "ACCIDENTAL": scia.LoadCombination.Type.EN_ACC_ONE,
        "ACCIDENTAL_1": scia.LoadCombination.Type.EN_ACC_ONE,
        "ACCIDENTAL_2": scia.LoadCombination.Type.EN_ACC_TWO,
        "SEISMIC": scia.LoadCombination.Type.EN_SEISMIC,
    }

    if combination_type not in combination_type_map:
        raise ValueError(f"Invalid combination_type '{combination_type}'. Use: {list(combination_type_map.keys())}")

    return model.create_load_combination(
        combination_name, combination_type_map[combination_type], load_cases, description=description or f"Load combination: {combination_name}"
    )


def create_patch_surface_load(
    model: SciaModel,
    load_case: SciaLoadCase,
    corner_points: list[tuple[float, float, float]],
    load_value: float,
    load_name: str = "PatchLoad",
) -> SciaFreeSurfaceLoad:
    """
    Create free surface load on 4-point patch (XY-plane only).

    :param model: SCIA model instance
    :param load_case: SCIA load case for the load application
    :param corner_points: List of 4 corner coordinates [(x1,y1,z1), (x2,y2,z2), (x3,y3,z3), (x4,y4,z4)]
    :param load_value: Load magnitude in [N/m²] (positive = downward)
    :param load_name: Name identifier for the load
    """
    _check_scia_availability()

    if len(corner_points) != 4:
        raise ValueError(f"Exactly 4 corner points required, got {len(corner_points)}")

    # Convert 3D points to 2D (XY only) for free surface load
    xy_points = [(x, y) for x, y, z in corner_points]

    # Calculate patch area for load conversion from N/m² to total N
    # Using shoelace formula for polygon area
    def polygon_area(points: list[tuple[float, float]]) -> float:
        n = len(points)
        area = 0.0
        for i in range(n):
            j = (i + 1) % n
            area += points[i][0] * points[j][1]
            area -= points[j][0] * points[i][1]
        return abs(area) / 2.0

    patch_area = polygon_area(xy_points)
    total_load = load_value * patch_area  # Convert N/m² to N

    # Create free surface load with uniform distribution
    return model.create_free_surface_load(
        name=load_name,
        load_case=load_case,
        direction=scia.FreeSurfaceLoad.Direction.Z,
        q1=total_load,
        points=xy_points,
        distribution=scia.FreeSurfaceLoad.Distribution.UNIFORM,
    )


# Legacy function for backwards compatibility
def create_load_case_with_name(model: SciaModel, load_case_name: str, load_case_type: str = "VARIABLE") -> SciaLoadCase:
    """
    DEPRECATED: Use create_load_case_complete() instead.
    Helper function to create a SCIA load case with basic settings.
    """
    group_name = f"LG_{load_case_name}"
    load_group = create_load_group_by_type(model, load_case_type, group_name)
    return create_load_case_complete(model, load_group, load_case_name, f"{load_case_type} load case: {load_case_name}", load_case_type)
