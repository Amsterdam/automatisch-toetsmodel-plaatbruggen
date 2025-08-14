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

from src.combinations.load_factors import (
    get_leading_action_positions,
    get_project_scope,
    prepare_combination_table,
)

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

    # Helper to safely convert params to dict format
    def _convert_to_dict(params_obj: Any) -> dict:  # noqa: ANN401
        if isinstance(params_obj, dict):
            return params_obj
        return {
            "cc_class": getattr(params_obj, "cc_class", None),
            "design_code": getattr(params_obj, "design_code", None),
            "info": {"construction_year": getattr(getattr(params_obj, "info", None), "construction_year", None)},
        }

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

    # TODO: Extend with dominant lane and other active lanes combinations

    return combinations




