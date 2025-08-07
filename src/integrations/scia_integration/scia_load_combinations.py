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
from typing import Any, cast

import pandas as pd
from pandas import DataFrame

from app.bridge.parametrization import BridgeParametrization
from src.combinations.load_factors import get_gamma_factors

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
# psi en alpha trend factors apply to load cases.
PSI_NEN_8701_PATH = PROJECT_PATH / "resources" / "data" / "code_tables" / "Psi_NEN_8701.csv"
ALPHA_TREND_NEN_8701_PATH = PROJECT_PATH / "resources" / "data" / "code_tables" / "Alpha_trend_NEN_8701.csv"
ALPHA_Q_q_NEN_EN_1991_2_PATH = PROJECT_PATH / "resources" / "data" / "code_tables" / "Alpha_Q_q_NEN_EN_1991_2.csv"

# ===================================================================================================================
# Functions
# ===================================================================================================================


def load_combination_table_without_rounding(params: BridgeParametrization) -> DataFrame:
    """
    Generate the load combination table for the bridge model, without rounding factors.

    This function reads the Eurocode/NEN load combination table from CSV, applies gamma factors
    based on the project parameters, and filters the table to include only relevant load cases and combinations.
    The resulting DataFrame contains the initial (non-rounded) factors for each combination and load case.

    :param params: The bridge parametrization object containing user/project input.
    :type params: BridgeParametrization
    :returns: DataFrame with load combination factors (not rounded), indexed by combination name.
    :rtype: pandas.DataFrame
    :raises FileNotFoundError: If the required CSV file is missing.
    :raises KeyError: If required parameters are missing from params.
    """
    # Read the code tables from CSV and set "Combinatie" as index
    df_combination_table_psi = pd.read_csv(PSI_NEN_8700_PATH, sep=";", decimal=",", index_col="Combinatie")

    # Lists for load cases related to permanent-, traffic-, wind- and other loads
    permanent_loads = ["Permanent", "Voorspanning", "Zetting"]
    traffic_loads = ["TS", "UDL", "Enkele as", "Horizontale belasting", "Fiets- en voetpaden", "Mensenmenigte", "Bijzondere voertuigen"]
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
        ("gr3", "Fiets- en voetpaden"),
        ("gr4", "Mensenmenigte"),
        ("gr5", "Bijzondere voertuigen"),
        ("Wind gr1a", "Wind Fwk"),
        ("Wind gr2", "Wind Fwk"),
        ("Temp gr1", "Temperatuur"),
        ("Temp gr2", "Temperatuur"),
        ("Sneeuw", "Sneeuw"),
        ("Cal gr1a", "Calamiteit"),
        ("Cal gr2", "Calamiteit"),
    }

    # Create load combination gamma values
    gamma_factors = get_gamma_factors(cc=params["cc_class"], safety_level=params["design_code"], building_year=params["info"]["construction_year"])

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
        combo_mask = df_combination_table_gamma_psi.index.str.startswith(combination)
        if combo_mask.any():
            # Multiply permanent loads with gamma_Gjsup
            df_combination_table_gamma_psi.loc[combo_mask, permanent_mask] = (
                df_combination_table_gamma_psi.loc[combo_mask, permanent_mask] * gamma_factors[combination]["gamma_Gjsup"]
            )
            # Multiply traffic loads with gamma_Qverkeer
            df_combination_table_gamma_psi.loc[combo_mask, traffic_mask] = (
                df_combination_table_gamma_psi.loc[combo_mask, traffic_mask] * gamma_factors[combination]["gamma_Qverkeer"]
            )
            # Multiply wind loads with gamma_Qwind
            df_combination_table_gamma_psi.loc[combo_mask, wind_mask] = (
                df_combination_table_gamma_psi.loc[combo_mask, wind_mask] * gamma_factors[combination]["gamma_Qwind"]
            )
            # Multiply other loads with gamma_Qoverig
            df_combination_table_gamma_psi.loc[combo_mask, other_mask] = (
                df_combination_table_gamma_psi.loc[combo_mask, other_mask] * gamma_factors[combination]["gamma_Qoverig"]
            )

    # Filter out rows that only contain zeros
    df_combination_table_gamma_psi = df_combination_table_gamma_psi[df_combination_table_gamma_psi.sum(axis=1) != 0]

    # Filter columns so that the load cases represent the project scope
    load_cases_project = ["Permanent", "TS", "UDL", "Fiets- en voetpaden", "Mensenmenigte", "Temperatuur"]
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


def create_scia_load_combinations(  # noqa: PLR0912, C901
    params: BridgeParametrization,
    builder: SciaModelBuilder,
    all_load_cases: dict[str, dict],
) -> list[SciaLoadCombination]:
    """
    Create the load combinations for the bridge model, according to Eurocode equations.

    This function generates ULS, SLS, and fatigue load combinations for the bridge model by
    filtering the load combination table using Eurocode row name prefixes. The resulting combinations
    are created using the SCIA model builder and returned as a list.

    :param params: The bridge parametrization object containing user/project input.
    :type params: BridgeParametrization
    :param builder: The SCIA model builder instance used to create load combinations.
    :type builder: SciaModelBuilder
    :param all_load_cases: Nested dictionary of all available SCIA load case objects, grouped by series name.
    :type all_load_cases: dict[str, dict]
    :returns: List of created SCIA load combination objects (ULS, SLS, and fatigue).
    :rtype: list[SciaLoadCombination]
    :raises KeyError: If required load cases are missing from all_load_cases.
    """
    combinations = []

    dataframe_loadcombination = load_combination_table_without_rounding(params)

    # Use row name prefixes for robust selection
    def _filter_by_prefix(df: DataFrame, prefixes: list[str]) -> DataFrame:
        """
        Filter DataFrame rows where the index starts with any of the given prefixes.

        :param df: DataFrame with string index
        :param prefixes: list of string prefixes
        :return: filtered DataFrame.
        """
        return df[df.index.to_series().str.startswith(tuple(prefixes))]

    uls_df = _filter_by_prefix(dataframe_loadcombination, ["6.10a", "6.10b"])
    sls_df = _filter_by_prefix(dataframe_loadcombination, ["6.14b", "6.15b", "6.16b"])
    fatigue_df = _filter_by_prefix(dataframe_loadcombination, ["6.67", "6.69"])

    subject_to_series: dict[str, list[str]] = {
        "Permanent": ["dead_load_cases"],
        "TS": ["tandem_cases"],
        "UDL": ["udl_traffic_cases"],
        "Fiets- en voetpaden": ["service_vehicle_cases"],
        "Mensenmenigte": ["pedestrian_cases"],
        "Temperatuur": ["temperature_cases"],
    }

    load_case_lookup = {}
    for series, cases in all_load_cases.items():
        if isinstance(cases, dict):
            load_case_lookup.update(cases)

    # ULS combinations
    for idx, row in uls_df.iterrows():
        load_case_factors = {}
        for subject, factor in row.items():
            if factor == 0:
                continue
            series_list = subject_to_series.get(subject, []) # type: ignore
            for series in series_list:
                cases_dict = all_load_cases.get(series, {})
                if isinstance(cases_dict, dict):
                    for case in cases_dict.values():
                        load_case_factors[case] = factor
        combination = create_load_combination(
            builder=builder,
            combination_type=SciaCombinationType.ENVELOPE_ULTIMATE,
            combination_name=str(idx),
            load_case_factors=load_case_factors,
            description=f"ULS Combination {idx}",
        )
        combinations.append(combination)

    # SLS combinations (characteristic)
    for idx, row in sls_df.iterrows():
        load_case_factors = {}
        for subject, factor in row.items():
            if factor == 0:
                continue
            series_list = subject_to_series.get(subject, []) # type: ignore
            for series in series_list:
                cases_dict = all_load_cases.get(series, {})
                if isinstance(cases_dict, dict):
                    for case in cases_dict.values():
                        load_case_factors[case] = factor
        combination = create_load_combination(
            builder=builder,
            combination_type=SciaCombinationType.ENVELOPE_SERVICEABILITY,
            combination_name=str(idx),
            load_case_factors=load_case_factors,
            description=f"SLS Combination {idx}",
        )
        combinations.append(combination)

    # Fatigue combinations
    for idx, row in fatigue_df.iterrows():
        load_case_factors = {}
        for subject, factor in row.items():
            if factor == 0:
                continue
            series_list = subject_to_series.get(subject, []) # type: ignore
            for series in series_list:
                cases_dict = all_load_cases.get(series, {})
                if isinstance(cases_dict, dict):
                    for case in cases_dict.values():
                        load_case_factors[case] = factor
        combination = create_load_combination(
            builder=builder,
            combination_type=SciaCombinationType.ENVELOPE_SERVICEABILITY,
            combination_name=str(idx),
            load_case_factors=load_case_factors,
            description=f"Fatigue Combination {idx}",
        )
        combinations.append(combination)

    return combinations


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
    params: BridgeParametrization, builder: SciaModelBuilder, all_load_cases: dict[str, dict]
) -> list[SciaLoadCombination]:
    """
    Create a list of standard ULS and SLS load combinations.

    This function serves as the main entry point for load combination creation.
    Colleagues should extend this function by adding more helper functions
    following the pattern shown in _create_example_combination().

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
    all_combinations = []

    all_combinations.extend(create_scia_load_combinations(params, builder, all_load_cases))

    return all_combinations


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
