"""
SCIA load cases utility module.

This module provides direct load case creation functions using create_load_case_complete()
with predefined parameters. The calling code just needs to provide the model and load group.

Currently contains placeholder implementations for basic bridge analysis.
"""

from typing import Any, TypeAlias

# Global VIKTOR imports with error handling for CI/testing environments
try:
    from viktor.external import scia

    VIKTOR_AVAILABLE = True
except ImportError:
    # Mock objects for environments without VIKTOR SDK
    scia = None  # type: ignore[misc,assignment]
    VIKTOR_AVAILABLE = False

# Type aliases for SCIA objects
SciaModel: TypeAlias = Any
SciaLoadGroup: TypeAlias = Any
SciaLoadCase: TypeAlias = Any


def _check_scia_availability() -> None:
    """Check if SCIA module is available and raise ImportError if not."""
    if not VIKTOR_AVAILABLE or scia is None:
        raise ImportError("VIKTOR SCIA module not available. This function requires VIKTOR SDK.")


def create_load_case_complete(
    model: Any,  # noqa: ANN401
    load_group: Any,  # noqa: ANN401
    case_name: str,
    description: str,
    case_type: str,
    **kwargs: str,
) -> Any:  # noqa: ANN401
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
    :returns: SCIA load case object
    :rtype: Any
    :raises ImportError: When VIKTOR SCIA module is not available
    :raises ValueError: When invalid case_type is provided

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


def create_self_weight_load_case(
    model: SciaModel,
    load_group: SciaLoadGroup,
) -> SciaLoadCase:
    """
    Create self-weight load case BG01 matching SCIA interface.

    Creates "BG01" self-weight load case with description "Eigen gewicht"
    using direct SCIA API to match SCIA Engineer interface exactly.

    :param model: SCIA model instance
    :param load_group: SCIA load group for permanent loads (should be LG1)
    :returns: Created SCIA self-weight load case BG01
    :rtype: SciaLoadCase
    :raises ImportError: When VIKTOR SCIA module is not available
    """
    return model.create_permanent_load_case(
        "BG01",
        "Eigen gewicht",
        load_group,
        scia.LoadCase.PermanentLoadType.SELF_WEIGHT,
    )


def create_wind_load_case(
    model: SciaModel,
    load_group: SciaLoadGroup,
) -> SciaLoadCase:
    """
    Create wind load case with predefined parameters.

    Creates a variable load case for wind loads on the bridge structure.

    PLACEHOLDER: Currently uses basic implementation for demonstration.

    :param model: SCIA model instance
    :param load_group: SCIA load group for variable loads
    :returns: Created SCIA wind load case
    :rtype: SciaLoadCase
    """
    return create_load_case_complete(
        model=model,
        load_group=load_group,
        case_name="Q2_Wind",
        description="Wind Load",
        case_type="VARIABLE",
        variable_type="STATIC",
        specification="STATIC_WIND",
        duration="SHORT",
    )


def create_tandem_load_case(
    model: SciaModel,
    load_group: SciaLoadGroup,
    case_name: str,
    mode: str = "theoretical",
) -> SciaLoadCase:
    """
    Create tandem load case with predefined parameters.

    Creates a variable load case for traffic tandem loads.

    PLACEHOLDER: Currently uses basic implementation. Used by apply_tandem_loads_to_scia_model.
    Will be expanded for proper tandem load case configuration.

    :param model: SCIA model instance
    :param load_group: SCIA load group for variable loads
    :param case_name: Name for the tandem load case (e.g., "TH6001", "BG6001")
    :param mode: Load case mode ("theoretical", "actual", "shiftable")
    :returns: Created SCIA tandem load case
    :rtype: SciaLoadCase
    """
    mode_descriptions = {
        "theoretical": "Tandem System - Theoretical Lane",
        "eurocode": "Load Model 1 - Tandem System",
        "shiftable": "Tandem System - Shiftable Position",
        "actual": "Tandem System - Actual Lane",
    }
    description = f"{mode_descriptions.get(mode, 'Tandem System')} {case_name}"

    return create_load_case_complete(
        model=model,
        load_group=load_group,
        case_name=case_name,
        description=description,
        case_type="VARIABLE",
        variable_type="STATIC",
        specification="STANDARD",
        duration="SHORT",
    )


def create_basic_permanent_load_cases(
    model: SciaModel,
    permanent_group: SciaLoadGroup,
) -> dict[str, SciaLoadCase]:
    """
    Create basic permanent load cases for bridge analysis.

    Creates self-weight load case for bridge structural analysis.

    PLACEHOLDER: Currently only creates self-weight. Will be expanded.

    :param model: SCIA model instance
    :param permanent_group: SCIA load group for permanent loads
    :returns: Dictionary with created permanent load cases
    :rtype: dict[str, SciaLoadCase]
    """
    self_weight_case = create_self_weight_load_case(model, permanent_group)

    return {
        "self_weight": self_weight_case,
    }


# TODO: Additional load case creation functions to be added for complete bridge analysis
# - create_udl_load_case() - for uniformly distributed loads
# - create_pedestrian_load_case() - for pedestrian loads
# - create_temperature_load_case() - for temperature effects
# - create_multiple_tandem_load_cases() - for multiple tandem positions
# - create_special_vehicle_load_case() - for special vehicle loads
# - create_settlement_load_case() - for settlement effects
# - create_seismic_load_case() - for seismic loads
# - create_construction_stage_load_case() - for construction stages

