"""
SCIA load combinations utility module.

This module provides utilities for creating and managing load combinations in SCIA Engineer
by calling methods on the SciaModelBuilder interface.

.. warning::
    The load combination factors and logic implemented in this module are simplified placeholders for architectural and demonstration purposes.
    They are **not** based on official Eurocode or NEN standards.
    A future task is to implement correct, configurable load combination logic based on relevant engineering codes (e.g., NEN 8700/8701).
"""

from typing import TYPE_CHECKING, Any

import pandas as pd
from pandas import DataFrame

from src.combinations.load_factors import (
    get_leading_action_positions,
    get_project_scope,
    prepare_combination_table,
)
from src.integrations.scia_integration.model.scia_model_interface import SciaLoadCombination, SciaModelBuilder
from src.integrations.scia_integration.scia_enums import LoadCombinationType
from src.integrations.scia_integration.types import LoadConfiguration

if TYPE_CHECKING:
    pass

# Type aliases for SCIA objects
SciaModel = Any
SciaLoadCase = Any

# ===================================================================================================================
# Functions
# ===================================================================================================================

# Mapping from table subject columns to load case series keys
SUBJECT_TO_SERIES: dict[str, list[str]] = {
    "Permanent": ["self_weight", "dead_load_cases"],
    "TS": ["tandem_cases"],
    "UDL - Main": ["udl_main_cases"],  # Main notional lane (RS 1)
    "UDL - Other": ["udl_other_cases"],  # Adjacent notional lanes (RS 2, RS 3, etc.)
    "UDL - Rest": ["udl_rest_cases"],  # Rest areas
    "Dienstvoertuig Qserv": ["service_vehicle_cases"],
    "Fiets- en voetpaden": ["pedestrian"],
    "Mensenmenigte": ["pedestrian"],
    "Bijzondere voertuigen": ["tram_track_tandem_cases"],
    "Onbedoeld voertuig": ["unintended_vehicle_cases"],
    "Temperatuur": ["temperature_cases"],
}


def _series_list(subject: str) -> list[str]:
    return SUBJECT_TO_SERIES.get(subject, [])


def _get_numeric_factor(factor: Any) -> float | None:  # noqa: ANN401
    """
    Extract numeric factor from value, skipping None, NaN, or zero.

    :param factor: Factor value to validate
    :type factor: Any
    :returns: Numeric factor or None if invalid
    :rtype: float | None
    """
    if factor is None:
        return None
    try:
        numeric_factor = float(factor)
    except (TypeError, ValueError):
        return None
    if pd.isna(numeric_factor) or numeric_factor == 0.0:
        return None
    return numeric_factor


def _add_series_to_factors_generic(
    all_load_cases: dict[str, Any],
    series_key: str,
    factor: float,
    out: dict[SciaLoadCase, float],
    configuration: LoadConfiguration | None = None,
) -> None:
    """
    Add load cases from a series to the factors dictionary.

    :param all_load_cases: Dictionary of all load cases
    :type all_load_cases: dict[str, Any]
    :param series_key: Key for the load case series (e.g., "tandem_cases")
    :type series_key: str
    :param factor: Load factor to apply
    :type factor: float
    :param out: Output dictionary to add cases to
    :type out: dict[SciaLoadCase, float]
    :param configuration: Optional configuration filter (A, B, or C) for traffic loads
    :type configuration: LoadConfiguration | None
    """
    series_obj = all_load_cases.get(series_key)
    if series_obj is None:
        return

    # If no configuration filter, add all cases (for non-traffic loads)
    if configuration is None:
        if isinstance(series_obj, dict):
            for case in series_obj.values():
                out[case] = factor
        else:
            out[series_obj] = factor
        return

    # For traffic loads, filter by configuration
    if isinstance(series_obj, dict):
        for key, case in series_obj.items():
            # Skip backward compatibility aliases
            if key in ["rs_1", "rs_2", "rs_3"]:
                continue

            # Get case description to extract configuration
            case_desc = _get_case_description(case)
            case_config = _extract_configuration_from_description(case_desc)

            # Only add if configuration matches
            if case_config == configuration:
                out[case] = factor
    else:
        # Single load case - check its configuration
        case_desc = _get_case_description(series_obj)
        case_config = _extract_configuration_from_description(case_desc)
        if case_config == configuration:
            out[series_obj] = factor


def _get_case_description(load_case: Any) -> str:  # noqa: ANN401
    """
    Get the description from a load case object.

    :param load_case: SCIA load case object
    :type load_case: Any
    :returns: Description string
    :rtype: str
    """
    if hasattr(load_case, "description"):
        return str(load_case.description)
    if hasattr(load_case, "Description"):
        return str(load_case.Description)
    return ""


def _extract_configuration_from_description(description: str) -> LoadConfiguration:
    """
    Extract configuration (A, B, C, D) from load case description.

    Configuration D is used for the second half of BG10000 series tandem loads
    where notional lanes 2 and 3 are switched compared to Configuration C.

    :param description: Load case description/title
    :type description: str
    :returns: Configuration enum value
    :rtype: LoadConfiguration
    """
    desc_lower = description.lower()
    if "conf. a" in desc_lower or "config. a" in desc_lower:
        return LoadConfiguration.CONF_A
    if "conf. b" in desc_lower or "config. b" in desc_lower:
        return LoadConfiguration.CONF_B
    if "conf. d" in desc_lower or "config. d" in desc_lower:
        return LoadConfiguration.CONF_D
    if "conf. c" in desc_lower or "config. c" in desc_lower:
        return LoadConfiguration.CONF_C
    return LoadConfiguration.NONE


def _create_combinations_from_df(  # noqa: C901, PLR0912
    *,
    builder: SciaModelBuilder,
    df: DataFrame,
    combination_type: LoadCombinationType,
    desc_prefix: str,
    all_load_cases: dict[str, Any],
    params: Any,  # noqa: ANN401
) -> list[SciaLoadCombination]:
    """
    Create SCIA load combinations from a DataFrame of combination factors.

    Creates 4 versions of each combination (one per configuration A, B, C, D) ONLY when
    traffic loads (TS or UDL) are present. For combinations without traffic loads,
    creates a single combination without configuration suffix.

    Special handling for Config D:
    - Config D is used for the second half of BG10000 series (lanes 2/3 switched)
    - Config D tandems combine with Config C UDLs (governing lane position matching)

    :param builder: SCIA model builder
    :type builder: SciaModelBuilder
    :param df: DataFrame with combination factors
    :type df: DataFrame
    :param combination_type: Type of combination (ULS, SLS, etc.)
    :type combination_type: LoadCombinationType
    :param desc_prefix: Description prefix for combinations
    :type desc_prefix: str
    :param all_load_cases: Dictionary of all load cases
    :type all_load_cases: dict[str, Any]
    :param params: Bridge parameters
    :type params: Any
    :returns: List of created combinations
    :rtype: list[SciaLoadCombination]
    """
    results: list[SciaLoadCombination] = []

    # Define traffic load subjects that need configuration filtering
    traffic_subjects = {"TS", "UDL - Main", "UDL - Other", "UDL - Rest"}

    for idx, row in df.iterrows():
        # Check if this combination has any traffic loads
        has_traffic_loads = False
        for subject, factor in row.items():
            numeric_factor = _get_numeric_factor(factor)
            if numeric_factor is None:
                continue

            subject_str = str(subject)
            if subject_str in traffic_subjects:
                has_traffic_loads = True
                break

        # If no traffic loads, create a single combination without configuration
        if not has_traffic_loads:
            load_case_factors: dict[SciaLoadCase, float] = {}

            for subject, factor in row.items():
                numeric_factor = _get_numeric_factor(factor)
                if numeric_factor is None:
                    continue

                # Add all load cases without configuration filter
                for series in _series_list(str(subject)):
                    _add_series_to_factors_generic(
                        all_load_cases, series_key=series, factor=numeric_factor, out=load_case_factors, configuration=None
                    )

            # Only create combination if it has load cases
            if load_case_factors:
                results.append(
                    create_load_combination(
                        builder=builder,
                        combination_type=combination_type,
                        combination_name=str(idx),
                        load_case_factors=load_case_factors,
                        description=f"{desc_prefix} {idx}",
                    )
                )
            continue

        # Has traffic loads - create 4 versions (one per configuration A, B, C, D)
        for config in [LoadConfiguration.CONF_A, LoadConfiguration.CONF_B, LoadConfiguration.CONF_C, LoadConfiguration.CONF_D]:
            load_case_factors = {}

            for subject, factor in row.items():
                numeric_factor = _get_numeric_factor(factor)
                if numeric_factor is None:
                    continue

                # Determine if this subject is traffic-related
                subject_str = str(subject)
                is_traffic = subject_str in traffic_subjects

                # Note: For UDL loads, dynamic factors are already applied in prepare_combination_table()

                # Special handling for Config D: tandems are Config D, but UDLs are Config C
                if config == LoadConfiguration.CONF_D and is_traffic:
                    # For Config D, we need different configs for TS vs UDL
                    if subject_str == "TS":
                        # Tandem systems: use Config D
                        for series in _series_list(subject_str):
                            _add_series_to_factors_generic(
                                all_load_cases,
                                series_key=series,
                                factor=numeric_factor,
                                out=load_case_factors,
                                configuration=LoadConfiguration.CONF_D,
                            )
                    elif subject_str in ["UDL - Main", "UDL - Other", "UDL - Rest"]:
                        # UDL loads: use Config C (governing lane position matching)
                        for series in _series_list(subject_str):
                            _add_series_to_factors_generic(
                                all_load_cases,
                                series_key=series,
                                factor=numeric_factor,
                                out=load_case_factors,
                                configuration=LoadConfiguration.CONF_C,
                            )
                else:
                    # Normal handling for configs A, B, C
                    for series in _series_list(subject_str):
                        _add_series_to_factors_generic(
                            all_load_cases,
                            series_key=series,
                            factor=numeric_factor,
                            out=load_case_factors,
                            configuration=config if is_traffic else None,
                        )

            # Only create combination if it has load cases
            if not load_case_factors:
                continue

            # Create combination with configuration suffix
            config_suffix = f" - Config {config.value}"
            results.append(
                create_load_combination(
                    builder=builder,
                    combination_type=combination_type,
                    combination_name=f"{idx}{config_suffix}",
                    load_case_factors=load_case_factors,
                    description=f"{desc_prefix} {idx}{config_suffix}",
                )
            )

    return results


def filter_by_prefix(df: DataFrame, prefixes: list[str]) -> DataFrame:
    """Filter DataFrame rows where the index starts with any of the given prefixes."""
    return df[df.index.to_series().str.startswith(tuple(prefixes))]


def load_combination_table_without_rounding(params: Any) -> DataFrame:  # noqa: ANN401
    """
    Generate the load combination table for the bridge model, without rounding factors.

    This function reads the Eurocode/NEN load combination table from CSV, applies gamma factors
    based on the project parameters, and filters the table to include only relevant load cases and combinations.
    The resulting DataFrame contains the initial (non-rounded) factors for each combination and load case.

    :param params: The bridge parameters object or dict containing user/project input.
    :type params: Any
    :returns: DataFrame with load combination factors (not rounded), indexed by combination name.
    :rtype: pandas.DataFrame
    :raises FileNotFoundError: If the required CSV file is missing.
    :raises KeyError: If required parameters are missing from params.
    :raises ValueError: If gamma factors could not be derived for given parameters.
    """

    # Helper to safely convert params to dict format
    def _convert_to_dict(params_obj: Any) -> dict:  # noqa: ANN401
        # Check if it's already a plain dict with the required keys
        if isinstance(params_obj, dict) and not hasattr(params_obj, "input") and "cc_class" in params_obj and "design_code" in params_obj:
            return params_obj

        # Try to get cc_class and design_code from the named fields first (VIKTOR parametrization)
        cc_class = getattr(params_obj, "cc_class", None)
        design_code = getattr(params_obj, "design_code", None)

        # If not found directly, try to get from nested structure
        if cc_class is None and hasattr(params_obj, "input") and hasattr(params_obj.input, "berekeningsinstellingen"):
            cc_class = getattr(params_obj.input.berekeningsinstellingen, "cc_class", None)
        if design_code is None and hasattr(params_obj, "input") and hasattr(params_obj.input, "berekeningsinstellingen"):
            design_code = getattr(params_obj.input.berekeningsinstellingen, "design_code", None)

        # Extract bridge_segments_array for dynamic UDL factor calculation
        bridge_segments_array = None
        if hasattr(params_obj, "bridge_segments_array"):
            # Convert to list of dicts for compatibility
            bridge_segments_array = [{"l": getattr(segment, "l", 0)} for segment in params_obj.bridge_segments_array]
        elif hasattr(params_obj, "geometry") and hasattr(params_obj.geometry, "bridge_segments_array"):
            bridge_segments_array = [{"l": getattr(segment, "l", 0)} for segment in params_obj.geometry.bridge_segments_array]

        # Extract berekeningsniveau and signage for UDL factor calculation
        berekeningsniveau = getattr(params_obj, "berekeningsniveau", None)
        signage = getattr(params_obj, "signage", None)

        result = {
            "cc_class": cc_class,
            "design_code": design_code,
            "info": {"construction_year": getattr(getattr(params_obj, "info", None), "construction_year", None)},
        }

        # Add optional parameters if available
        if bridge_segments_array:
            result["bridge_segments_array"] = bridge_segments_array
        if berekeningsniveau:
            result["berekeningsniveau"] = berekeningsniveau
        if signage:
            result["signage"] = signage

        return result

    # Convert params to dict format and prepare the initial table
    params_dict = _convert_to_dict(params)
    df_combination_table_gamma_psi = prepare_combination_table(params_dict)

    # Filter columns so that the load cases represent the project scope
    load_cases_project = get_project_scope()
    df_combination_table_gamma_psi = df_combination_table_gamma_psi[df_combination_table_gamma_psi.columns.intersection(load_cases_project)]

    # Filter rows so that the load cases represent the project scope
    load_combinations_project = [(row_name, col_name) for row_name, col_name in get_leading_action_positions() if col_name in load_cases_project]

    # Filter rows based on load_combinations_project
    valid_row_names = {row_name for row_name, _ in load_combinations_project}
    return df_combination_table_gamma_psi[
        [idx.split(" ", 1)[1] in valid_row_names if len(idx.split(" ", 1)) > 1 else False for idx in df_combination_table_gamma_psi.index]
    ]


def create_load_combination(
    builder: SciaModelBuilder,
    combination_type: LoadCombinationType,
    combination_name: str,
    load_case_factors: dict[SciaLoadCase, float],
    description: str = "",
) -> SciaLoadCombination:
    """
    Create a SCIA load combination using the builder.

    :param builder: The SCIA model builder instance.
    :param combination_type: "ULS", "SLS_CHAR", etc.
    :param combination_name: Name for the combination.
    :param load_case_factors: Dictionary mapping load case objects to their factors.
    :param description: Optional description.
    :return: The created SCIA Load Combination object.
    :rtype: SciaLoadCombination
    """
    return builder.create_load_combination(
        name=combination_name,
        combination_type=combination_type,
        load_case_factors=load_case_factors,
        description=description or f"Load combination: {combination_name}",
    )


def create_uls_combinations_from_table(
    params: Any,  # noqa: ANN401
    builder: SciaModelBuilder,
    all_load_cases: dict[str, Any],
) -> list[SciaLoadCombination]:
    """
    Create ULS combinations (6.10a/6.10b) from the NEN 8700 combination table.

    :returns: List of SCIA load combinations for ULS.
    :rtype: list[SciaLoadCombination]
    """
    df_combinations = load_combination_table_without_rounding(params)
    uls_df = filter_by_prefix(df_combinations, ["6.10a", "6.10b"])
    return _create_combinations_from_df(
        builder=builder,
        df=uls_df,
        combination_type=LoadCombinationType.ENVELOPE_ULTIMATE,
        desc_prefix="ULS Combination",
        all_load_cases=all_load_cases,
        params=params,
    )


def create_sls_combinations_from_table(
    params: Any,  # noqa: ANN401
    builder: SciaModelBuilder,
    all_load_cases: dict[str, Any],
) -> list[SciaLoadCombination]:
    """
    Create SLS combinations (6.14b/6.15b/6.16b) from the NEN 8700 combination table.

    :returns: List of SCIA load combinations for SLS.
    :rtype: list[SciaLoadCombination]
    """
    df_combinations = load_combination_table_without_rounding(params)
    sls_df = filter_by_prefix(df_combinations, ["6.14b", "6.15b", "6.16b"])
    return _create_combinations_from_df(
        builder=builder,
        df=sls_df,
        combination_type=LoadCombinationType.ENVELOPE_SERVICEABILITY,
        desc_prefix="SLS Combination",
        all_load_cases=all_load_cases,
        params=params,
    )


def create_fatigue_combinations_from_table(
    params: Any,  # noqa: ANN401
    builder: SciaModelBuilder,
    all_load_cases: dict[str, Any],
) -> list[SciaLoadCombination]:
    """
    Create fatigue combinations (6.67/6.69) from the NEN 8700 combination table.

    :returns: List of SCIA load combinations for fatigue.
    :rtype: list[SciaLoadCombination]
    """
    df_combinations = load_combination_table_without_rounding(params)
    fatigue_df = filter_by_prefix(df_combinations, ["6.67", "6.69"])
    return _create_combinations_from_df(
        builder=builder,
        df=fatigue_df,
        combination_type=LoadCombinationType.ENVELOPE_SERVICEABILITY,
        desc_prefix="Fatigue Combination",
        all_load_cases=all_load_cases,
        params=params,
    )


def create_all_load_combinations(
    params: Any,  # noqa: ANN401
    builder: SciaModelBuilder,
    all_load_cases: dict[str, Any],
) -> list[SciaLoadCombination]:
    """
    Create all load combinations for the bridge model (ULS, SLS, fatigue, ...).

    This function creates load combinations based on the NEN 8700 combination table.
    To prevent incorrect mixing of traffic load configurations, each combination
    WITH traffic loads (TS or UDL) is created in FOUR versions - one for each
    configuration (A, B, C, D). Combinations WITHOUT traffic loads are created once.

    For example, "ULS 6.10a LC1" (with traffic) becomes:
    - "ULS 6.10a LC1 - Config A" (with only Config A traffic loads)
    - "ULS 6.10a LC1 - Config B" (with only Config B traffic loads)
    - "ULS 6.10a LC1 - Config C" (with only Config C traffic loads)
    - "ULS 6.10a LC1 - Config D" (with Config D tandems + Config C UDLs)

    But "ULS 6.10a Perm" (no traffic) becomes:
    - "ULS 6.10a Perm" (single combination, no configuration suffix)

    Configuration D is special:
    - Used for second half of BG10000 series (notional lanes 2/3 switched)
    - Config D tandems combine with Config C UDLs (governing lane position matching)

    This ensures that:
    1. Traffic loads from different configurations are never mixed
    2. Only tandem systems and UDLs from compatible configurations are combined
    3. Matching governing lanes on the same position can be combined (per configuration)
    4. Combinations without traffic loads are not unnecessarily duplicated
    5. Config D prevents incorrect same-position loads on switched lanes

    Non-traffic loads (permanent, temperature, etc.) are included in all combinations.

    :param params: Bridge parameters object or dict containing user/project input
    :type params: Any
    :param builder: The SCIA model builder instance
    :type builder: SciaModelBuilder
    :param all_load_cases: A nested dictionary of all available SciaLoadCase objects.
        Structure example:
        {
            "standard_cases": {"self_weight": SciaLoadCase, "pedestrian": SciaLoadCase},
            "dead_load_cases": {"asfalt": SciaLoadCase, "uitvulling": SciaLoadCase, ...},
            "temperature_cases": {"combi_1": SciaLoadCase, ...},
            "udl_main_cases": {"BG4001": SciaLoadCase, ...},
            "udl_other_cases": {"BG4002": SciaLoadCase, ...},
            "udl_rest_cases": {"BG4003": SciaLoadCase, ...},
            "tandem_cases": {"tandem_rs1_x1.2": SciaLoadCase, ...},
            ...
        }
    :return: A list of created SciaLoadCombination objects
    :rtype: list[SciaLoadCombination]
    """
    combinations: list[SciaLoadCombination] = []

    # Standard combinations from the NEN 8700 table
    # Creates 4 versions per combination ONLY when traffic loads are present (A, B, C, D)
    # Single version for combinations without traffic loads
    # Config D tandems combine with Config C UDLs
    combinations.extend(create_uls_combinations_from_table(params, builder, all_load_cases))
    combinations.extend(create_sls_combinations_from_table(params, builder, all_load_cases))
    combinations.extend(create_fatigue_combinations_from_table(params, builder, all_load_cases))

    return combinations
