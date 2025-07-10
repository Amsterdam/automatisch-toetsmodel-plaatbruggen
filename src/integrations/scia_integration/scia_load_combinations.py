"""
SCIA load combinations utility module.

This module provides utilities for creating and managing load combinations in SCIA Engineer.
Direct functions create specific load combinations with predefined parameters and factors.

Currently contains placeholder implementations for basic bridge analysis.
"""

from typing import Any

# Global VIKTOR imports with error handling for CI/testing environments
try:
    from viktor.external import scia

    VIKTOR_AVAILABLE = True
except ImportError:
    # Mock objects for environments without VIKTOR SDK
    scia = None  # type: ignore[misc,assignment]
    VIKTOR_AVAILABLE = False

# Type aliases for SCIA objects
SciaModel = Any
SciaLoadCase = Any
SciaLoadCombination = Any


def _check_scia_availability() -> None:
    """Check if SCIA module is available and raise ImportError if not."""
    if not VIKTOR_AVAILABLE or scia is None:
        raise ImportError("VIKTOR SCIA module not available. This function requires VIKTOR SDK.")


def create_load_combination_by_type(
    model: Any,  # noqa: ANN401
    combination_type: str,
    combination_name: str,
    load_cases: dict[Any, float],
    description: str = "",
) -> Any:  # noqa: ANN401
    """
    Create SCIA load combination with standardized types.

    :param model: SCIA model instance
    :param combination_type: "ULS", "SLS_CHAR", "SLS_FREQ", "SLS_QUASI", "ACCIDENTAL", "SEISMIC", etc.
    :param combination_name: Name for the combination
    :param load_cases: Dictionary mapping load cases to their factors
    :param description: Optional description
    :returns: SCIA load combination object
    :rtype: Any
    :raises ImportError: When VIKTOR SCIA module is not available
    :raises ValueError: When invalid combination_type is provided

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


def create_basic_uls_combination(
    model: SciaModel,
    self_weight_case: SciaLoadCase,
    traffic_case: SciaLoadCase,
    combination_name: str = "ULS_Basic_G0+TS",
) -> SciaLoadCombination:
    """
    Create basic ULS combination with predefined factors.

    Creates ULS combination with standard factors: 1.25*G0 + 1.25*TS

    PLACEHOLDER: Currently uses basic factors. Will be expanded to include
    proper NEN 8700 factors and more sophisticated combination logic.

    :param model: SCIA model instance
    :param self_weight_case: Self-weight load case
    :param traffic_case: Traffic load case
    :param combination_name: Name for the combination
    :returns: Created SCIA ULS combination
    :rtype: SciaLoadCombination
    """
    factors = {
        self_weight_case: 1.25,
        traffic_case: 1.25,
    }

    return create_load_combination_by_type(model, "ULS", combination_name, factors, "Basic ULS: 1.25*G0 + 1.25*TS (Self-weight + Traffic)")


def create_basic_sls_combination(
    model: SciaModel,
    self_weight_case: SciaLoadCase,
    traffic_case: SciaLoadCase,
    combination_name: str = "SLS_Basic_G0+TS",
) -> SciaLoadCombination:
    """
    Create basic SLS combination with predefined factors.

    Creates SLS combination with standard factors: 1.0*G0 + 1.0*TS

    PLACEHOLDER: Currently uses basic factors. Will be expanded to include
    proper NEN 8701 factors and serviceability limit state logic.

    :param model: SCIA model instance
    :param self_weight_case: Self-weight load case
    :param traffic_case: Traffic load case
    :param combination_name: Name for the combination
    :returns: Created SCIA SLS combination
    :rtype: SciaLoadCombination
    """
    factors = {
        self_weight_case: 1.0,
        traffic_case: 1.0,
    }

    return create_load_combination_by_type(model, "SLS_CHAR", combination_name, factors, "Basic SLS: 1.0*G0 + 1.0*TS (Self-weight + Traffic)")


def create_wind_uls_combination(
    model: SciaModel,
    self_weight_case: SciaLoadCase,
    traffic_case: SciaLoadCase,
    wind_case: SciaLoadCase,
    combination_name: str = "ULS_Wind_G0+TS+W",
) -> SciaLoadCombination:
    """
    Create ULS combination with wind loads and predefined factors.

    Creates ULS combination with wind factors: 1.35*G0 + 1.5*TS + 1.5*0.6*W

    PLACEHOLDER: Currently uses basic factors.

    :param model: SCIA model instance
    :param self_weight_case: Self-weight load case
    :param traffic_case: Traffic load case
    :param wind_case: Wind load case
    :param combination_name: Name for the combination
    :returns: Created SCIA ULS combination with wind
    :rtype: SciaLoadCombination
    """
    factors = {
        self_weight_case: 1.35,
        traffic_case: 1.5,
        wind_case: 1.5 * 0.6,  # Wind with reduction factor
    }

    return create_load_combination_by_type(
        model, "ULS", combination_name, factors, "ULS with Wind: 1.35*G0 + 1.5*TS + 0.9*W (Self-weight + Traffic + Wind)"
    )


# TODO: Additional load combination creation functions to be added for complete bridge analysis
# - create_advanced_uls_combination() - with configurable NEN 8700 factors
# - create_advanced_sls_combination() - with configurable NEN 8701 factors
# - create_multiple_traffic_combinations() - for multiple traffic scenarios
# - create_seismic_combinations() - for seismic load combinations
# - create_construction_stage_combinations() - for construction stages
# - create_fatigue_combinations() - for fatigue limit states
# - create_accidental_combinations() - for accidental situations
