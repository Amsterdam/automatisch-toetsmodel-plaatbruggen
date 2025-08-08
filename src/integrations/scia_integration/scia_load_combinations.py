"""
SCIA load combinations utility module.

This module provides utilities for creating and managing load combinations in SCIA Engineer
by calling methods on the SciaModelBuilder interface.

.. warning::
    The load combination factors and logic implemented in this module are simplified placeholders for architectural and demonstration purposes.
    They are **not** based on official Eurocode or NEN standards.
    A future task is to implement correct, configurable load combination logic based on relevant engineering codes (e.g., NEN 8700/8701).
"""

import traceback
from pathlib import Path
from typing import Any

import pandas as pd
from pandas import DataFrame

from src.combinations.load_factors import apply_gamma_for_combination, get_gamma_factors

from .scia_model_interface import SciaCombinationType, SciaLoadCombination, SciaModelBuilder

# Type aliases for SCIA objects
SciaModel = Any
SciaLoadCase = Any

# ===================================================================================================================
# Paths
# ===================================================================================================================

PROJECT_PATH = Path(__file__).parent.parent.parent.parent
PSI_NEN_8700_PATH = PROJECT_PATH / "resources" / "data" / "code_tables" / "Psi_NEN_8700.csv"
GAMMA_NEN_8700_PATH = PROJECT_PATH / "resources" / "data" / "code_tables" / "Gamma_NEN_8700.csv"

# ===================================================================================================================
# Functions
# ===================================================================================================================

# Mapping from table subject columns to load case series keys
SUBJECT_TO_SERIES: dict[str, list[str]] = {
    "Permanent": ["self_weight", "dead_load_cases"],
    "TS": ["tandem_cases"],
    "UDL": ["udl_traffic_cases"],
    "Dienstvoertuig Qserv": ["service_vehicle_cases"],
    "Fiets- en voetpaden": ["pedestrian"],
    "Mensenmenigte": ["pedestrian"],
    "Onbedoeld voertuig": ["unintended_vehicle_cases"],
    "Temperatuur": ["temperature_cases"],
}


def _series_list(subject: str) -> list[str]:
    return SUBJECT_TO_SERIES.get(subject, [])


def _add_series_to_factors_generic(
    all_load_cases: dict[str, Any],
    series_key: str,
    factor: float,
    out: dict[SciaLoadCase, float],
) -> None:
    series_obj = all_load_cases.get(series_key)
    if series_obj is None:
        return
    if isinstance(series_obj, dict):
        for case in series_obj.values():
            out[case] = factor
    else:
        out[series_obj] = factor


def _create_combinations_from_df(
    *,
    builder: SciaModelBuilder,
    df: DataFrame,
    combination_type: SciaCombinationType,
    desc_prefix: str,
    all_load_cases: dict[str, Any],
) -> list[SciaLoadCombination]:
    results: list[SciaLoadCombination] = []
    for idx, row in df.iterrows():
        load_case_factors: dict[SciaLoadCase, float] = {}
        for subject, factor in row.items():
            # Skip non-numeric, NaN, or zero factors
            if factor is None:
                continue
            try:
                numeric_factor = float(factor)
            except (TypeError, ValueError):
                continue
            if pd.isna(numeric_factor) or numeric_factor == 0.0:
                continue
            for series in _series_list(str(subject)):
                _add_series_to_factors_generic(all_load_cases, series_key=series, factor=numeric_factor, out=load_case_factors)
        if not load_case_factors:
            continue
        results.append(
            create_load_combination(
                builder=builder,
                combination_type=combination_type,
                combination_name=str(idx),
                load_case_factors=load_case_factors,
                description=f"{desc_prefix} {idx}",
            )
        )
    return results


def _filter_by_prefix(df: DataFrame, prefixes: list[str]) -> DataFrame:
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

    # Helper to safely read params as dict or attribute object
    def _get_value(obj: object, key: str) -> object:
        if isinstance(obj, dict):
            return obj.get(key)
        return getattr(obj, key, None)

    # Read the code tables from CSV and set "Combinatie" as index
    df_combination_table_psi = pd.read_csv(PSI_NEN_8700_PATH, sep=";", decimal=",", index_col="Combinatie")

    # Lists for load cases related to permanent-, traffic-, wind- and other loads
    permanent_loads = ["Permanent", "Voorspanning", "Zetting"]
    traffic_loads = [
        "TS",
        "UDL",
        "Enkele as",
        "Horizontale belasting",
        "Dienstvoertuig Qserv",
        "Fiets- en voetpaden",
        "Mensenmenigte",
        "Bijzondere voertuigen",
        "Onbedoeld voertuig",
    ]
    wind_loads = ["Wind Fwk", "Wind Fw*"]
    temperature_loads = ["Temperatuur"]
    snow_loads = ["Sneeuw"]
    other_loads = temperature_loads + snow_loads

    # Table positions for leading actions which should be highlighted
    leading_action_positions = {
        ("Perm", "Permanent"),
        ("Perm", "Voorspanning"),
        ("Perm zet", "Zetting"),
        ("gr1a", "TS"),
        ("gr1a", "UDL"),
        ("gr1b", "Enkele as"),
        ("gr2", "Horizontale belasting"),
        ("gr2", "Dienstvoertuig Qserv"),
        ("gr3", "Fiets- en voetpaden"),
        ("gr4", "Mensenmenigte"),
        ("gr5", "Bijzondere voertuigen"),
        ("Onb. vrtg.", "Onbedoeld voertuig"),
        ("Wind gr1a", "Wind Fwk"),
        ("Wind gr2", "Wind Fwk"),
        ("Temp gr1", "Temperatuur"),
        ("Temp gr2", "Temperatuur"),
        ("Sneeuw", "Sneeuw"),
        ("Cal gr1a", "Calamiteit"),
        ("Cal gr2", "Calamiteit"),
    }

    # Create load combination gamma values
    cc_class = _get_value(params, "cc_class")
    design_code = _get_value(params, "design_code")
    info = _get_value(params, "info")
    construction_year = _get_value(info, "construction_year") if info is not None else None

    if cc_class is None or design_code is None or construction_year is None:
        raise KeyError("Missing required parameters: cc_class, design_code and/or info.construction_year")

    gamma_factors = get_gamma_factors(cc=str(cc_class), safety_level=str(design_code), building_year=str(construction_year))

    # Multiply the psi factors with the gamma factors for all load cases
    # Create a copy and convert to float64 to ensure dtype compatibility
    df_combination_table_gamma_psi = df_combination_table_psi.astype("float64")

    # Create masks for different load types based on column names
    permanent_mask = df_combination_table_gamma_psi.columns.isin(permanent_loads)
    traffic_mask = df_combination_table_gamma_psi.columns.isin(traffic_loads)
    wind_mask = df_combination_table_gamma_psi.columns.isin(wind_loads)
    other_mask = df_combination_table_gamma_psi.columns.isin(other_loads)

    # Apply gamma factors based on combination type (6.10a or 6.10b)
    for combination in ["6.10a", "6.10b"]:
        apply_gamma_for_combination(
            df=df_combination_table_gamma_psi,
            combination=combination,
            gamma_factors=gamma_factors,
            permanent_mask=permanent_mask,
            traffic_mask=traffic_mask,
            wind_mask=wind_mask,
            other_mask=other_mask,
        )

    # Filter out rows that only contain zeros
    df_combination_table_gamma_psi = df_combination_table_gamma_psi[df_combination_table_gamma_psi.sum(axis=1) != 0]

    # Filter columns so that the load cases represent the project scope
    load_cases_project = [
        "Permanent",
        "TS",
        "UDL",
        "Dienstvoertuig Qserv",
        "Fiets- en voetpaden",
        "Mensenmenigte",
        "Onbedoeld voertuig",
        "Temperatuur",
    ]
    df_combination_table_gamma_psi = df_combination_table_gamma_psi[df_combination_table_gamma_psi.columns.intersection(load_cases_project)]

    # Filter rows so that the load cases represent the project scope
    load_combinations_project = [(row_name, col_name) for row_name, col_name in leading_action_positions if col_name in load_cases_project]

    # Filter rows based on load_combinations_project
    valid_row_names = {row_name for row_name, _ in load_combinations_project}

    return df_combination_table_gamma_psi[
        [idx.split(" ", 1)[1] in valid_row_names if len(idx.split(" ", 1)) > 1 else False for idx in df_combination_table_gamma_psi.index]
    ]


def create_load_combination(
    builder: SciaModelBuilder,
    combination_type: SciaCombinationType,
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
    uls_df = _filter_by_prefix(df_combinations, ["6.10a", "6.10b"])
    return _create_combinations_from_df(
        builder=builder,
        df=uls_df,
        combination_type=SciaCombinationType.ENVELOPE_ULTIMATE,
        desc_prefix="ULS Combination",
        all_load_cases=all_load_cases,
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
    sls_df = _filter_by_prefix(df_combinations, ["6.14b", "6.15b", "6.16b"])
    return _create_combinations_from_df(
        builder=builder,
        df=sls_df,
        combination_type=SciaCombinationType.ENVELOPE_SERVICEABILITY,
        desc_prefix="SLS Combination",
        all_load_cases=all_load_cases,
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
    fatigue_df = _filter_by_prefix(df_combinations, ["6.67", "6.69"])
    return _create_combinations_from_df(
        builder=builder,
        df=fatigue_df,
        combination_type=SciaCombinationType.ENVELOPE_SERVICEABILITY,
        desc_prefix="Fatigue Combination",
        all_load_cases=all_load_cases,
    )


def _create_example_combination(
    builder: SciaModelBuilder, self_weight_case: SciaLoadCase, all_load_cases: dict[str, dict]
) -> list[SciaLoadCombination]:
    """
    Create an example load combination to demonstrate the pattern.

    This function serves as an example for colleagues to understand:
    - How to access load cases from the all_load_cases dictionary
    - How to define load factors
    - How to create combinations using the builder

    :param builder: The SCIA model builder instance.
    :param self_weight_case: The self-weight load case object.
    :param all_load_cases: A nested dictionary of all available SciaLoadCase objects.
    :return: A list of created SciaLoadCombination objects.
    :rtype: list[SciaLoadCombination]
    """
    combinations = []

    # Example: Get pedestrian load case from the nested dictionary
    pedestrian_case = all_load_cases.get("pedestrian")

    if pedestrian_case:
        # Example: Define load factors for ULS combination
        # These are placeholder values - colleagues should replace with proper NEN/Eurocode factors
        load_factors = {
            self_weight_case: 1.35,  # γG for permanent loads (ULS)
            pedestrian_case: 1.50,  # γQ for variable loads (ULS)
        }

        try:
            # Try creating a simple self-weight only combination first
            simple_factors = {self_weight_case: 1.0}

            # Try different combination types
            combo_types_to_try = [
                SciaCombinationType.EN_ULS_SET_B,
                SciaCombinationType.LINEAR_ULTIMATE,
                SciaCombinationType.ENVELOPE_ULTIMATE,
            ]

            for combo_type in combo_types_to_try:
                try:
                    simple_combo = create_load_combination(
                        builder=builder,
                        combination_type=combo_type,
                        combination_name=f"Test_{combo_type.value}",
                        load_case_factors=simple_factors,
                        description=f"Test: 1.0*G (Self-weight only) - {combo_type.value}",
                    )
                    combinations.append(simple_combo)
                    break  # Stop if one works
                except Exception:
                    continue

            # Now try the full combination
            uls_combo = create_load_combination(
                builder=builder,
                combination_type=SciaCombinationType.EN_ULS_SET_B,
                combination_name="ULS_Example_SW_Pedestrian",
                load_case_factors=load_factors,
                description="Example ULS: 1.35*G + 1.50*Q (Self-weight + Pedestrian)",
            )
            combinations.append(uls_combo)
        except Exception:
            traceback.print_exc()
    else:
        # Try to create a simple self-weight only combination as fallback
        try:
            load_factors = {self_weight_case: 1.0}
            simple_combo = create_load_combination(
                builder=builder,
                combination_type=SciaCombinationType.EN_ULS_SET_B,
                combination_name="ULS_Self_Weight_Only",
                load_case_factors=load_factors,
                description="Simple ULS: 1.0*G (Self-weight only)",
            )
            combinations.append(simple_combo)
        except Exception:
            pass

    return combinations


def create_all_load_combinations(
    params: Any,  # noqa: ANN401
    builder: SciaModelBuilder,
    all_load_cases: dict[str, Any],
) -> list[SciaLoadCombination]:
    """
    Create all load combinations for the bridge model (ULS, SLS, fatigue, ...).

    This function aggregates outputs from dedicated helper creators, similar to
    how `create_all_load_cases` composes all load cases. Extend this function
    with extra families (temperature-only, accidental scenarios, etc.) when
    implemented.

    :param builder: The SCIA model builder instance.
    :param all_load_cases: A nested dictionary of all available SciaLoadCase objects.
        Structure example:
        {
            "standard_cases": {"self_weight": SciaLoadCase, "pedestrian": SciaLoadCase},
            "dead_load_cases": {"asfalt": SciaLoadCase, "uitvulling": SciaLoadCase, ...},
            "temperature_cases": {"combi_1": SciaLoadCase, ...},
            "udl_traffic_cases": {"rs_1": SciaLoadCase, ...},
            "tandem_cases": {"tandem_rs1_x1.2": SciaLoadCase, ...},
            ...
        }
    :return: A list of created SciaLoadCombination objects.
    :rtype: list[SciaLoadCombination]
    """
    combinations: list[SciaLoadCombination] = []

    # Standard combinations from the NEN 8700 table (one function per family)
    combinations.extend(create_uls_combinations_from_table(params, builder, all_load_cases))
    combinations.extend(create_sls_combinations_from_table(params, builder, all_load_cases))
    combinations.extend(create_fatigue_combinations_from_table(params, builder, all_load_cases))

    # TODO: Extend with additional families when available

    return combinations


# TODO: Additional load combination creation functions to be added by colleagues:
#
# Example structure for _create_temperature_combinations:
# - Get temperature_cases from all_load_cases.get("temperature_cases", {})
# - Define appropriate load factors for temperature combinations
# - Create combinations using create_load_combination function
#
# Example structure for _create_traffic_combinations:
# - Get tandem_cases from all_load_cases.get("tandem_cases", {})
# - Get udl_cases from all_load_cases.get("udl_traffic_cases", {})
# - Define appropriate load factors for traffic combinations
# - Create combinations using create_load_combination function
#
# Example structure for _create_dead_load_combinations:
# - Get dead_load_cases from all_load_cases.get("dead_load_cases", {})
# - Define appropriate load factors for dead load combinations
# - Create combinations using create_load_combination function
