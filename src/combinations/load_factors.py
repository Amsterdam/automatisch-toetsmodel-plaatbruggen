"""
Module for calculating psi factors for bridge load combinations.

This module provides functionality to calculate psi factors based on bridge span length
and reference period using bilinear interpolation. The psi factors are used in load
combinations for bridge design and assessment according to Dutch standards.

The module includes a predefined lookup table of psi factors for various span lengths
and reference periods, and provides interpolation for intermediate values. For span
lengths outside the valid range (20-200m), the values are clamped to the nearest
valid value.
"""

import datetime
import zoneinfo
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd
from pandas.io.formats.style import Styler
from scipy.interpolate import RegularGridInterpolator  # type: ignore[import-untyped]

from src.common.constants import SIGNAGE_LOAD_FACTORS
from src.data_models.combination_models import LoadCombinationConfig
from src.integrations.scia_integration.constants.loads import (
    ALPHA_Q_MAIN_LANE_ONDERLIGGEND,
    ALPHA_Q_ONDERLIGGEND,
    ALPHA_Q_OTHER_LANE_ONDERLIGGEND,
    NOBS_DEFAULT,
    SIGNAGE_WEIGHT_OPTIONS,
    UDL_MAIN_LANE_FACTOR,
    UDL_OTHER_LANE_FACTOR,
    UDL_REST_AREA_FACTOR,
)
from src.integrations.scia_integration.load_system.lane_calculations import get_reference_period

if TYPE_CHECKING:
    pass

# ===================================================================================================================
# Paths
# ===================================================================================================================

PROJECT_PATH = Path(__file__).parent.parent.parent
PSI_NEN_8700_PATH = PROJECT_PATH / "resources" / "data" / "code_tables" / "Psi_NEN_8700.csv"
GAMMA_NEN_8700_PATH = PROJECT_PATH / "resources" / "data" / "code_tables" / "Gamma_NEN_8700.csv"
PSI_NEN_8701_PATH = PROJECT_PATH / "resources" / "data" / "code_tables" / "Psi_NEN_8701.csv"
ALPHA_TREND_NEN_8701_PATH = PROJECT_PATH / "resources" / "data" / "code_tables" / "Alpha_trend_NEN_8701.csv"
ALPHA_Q_q_NEN_EN_1991_2_PATH = PROJECT_PATH / "resources" / "data" / "code_tables" / "Alpha_Q_q_NEN_EN_1991_2.csv"

# ===================================================================================================================
# Functions
# ===================================================================================================================


# Type alias for boolean mask inputs (pandas or numpy)
MaskType = pd.Series | np.ndarray


def apply_gamma_for_combination(  # noqa: PLR0913 - clear, explicit arguments preferred here
    df: pd.DataFrame,
    combination: str,
    gamma_factors: dict[str, dict[str, float]],
    permanent_mask: MaskType,
    traffic_mask: MaskType,
    wind_mask: MaskType,
    other_mask: MaskType,
) -> None:
    """
    Apply gamma factors to the given DataFrame for a specific combination key.

    Updates df in place for rows whose index starts with the given combination prefix.
    """
    combo_mask = df.index.str.startswith(combination)
    if not combo_mask.any():
        return

    df.loc[combo_mask, permanent_mask] = df.loc[combo_mask, permanent_mask] * gamma_factors[combination]["gamma_Gjsup"]
    df.loc[combo_mask, traffic_mask] = df.loc[combo_mask, traffic_mask] * gamma_factors[combination]["gamma_Qverkeer"]
    df.loc[combo_mask, wind_mask] = df.loc[combo_mask, wind_mask] * gamma_factors[combination]["gamma_Qwind"]
    df.loc[combo_mask, other_mask] = df.loc[combo_mask, other_mask] * gamma_factors[combination]["gamma_Qoverig"]


def get_gamma_factors(cc: str, safety_level: str, building_year: str) -> dict:
    """
    Extract gamma factors based on consequence class (CC), assessment level and building year.

    Args:
        cc: Consequence class ("CC1a/b", "CC2", "CC3")
        safety_level: Assessment level ("NEN 8700 verbouw", "NEN 8700 gebruik", "NEN 8700 afkeur")
        building_year: Year of construction (e.g. "1964")

    Returns:
        Dictionary containing gamma factors with their values for both 6.10a and 6.10b

    Raises:
        ValueError: If the CC class or safety level is not found in the table, or if gamma factors cannot be extracted

    """
    # Read the code tables from CSV
    df_gamma = pd.read_csv(GAMMA_NEN_8700_PATH, sep=";", decimal=",")

    # Extract the safety level if design code is NEN 8700
    if "NEN 8700" in safety_level:
        safety_level = safety_level.replace("NEN 8700 ", "").strip().capitalize()

    # Filter rows based on consequence class (gevolgklasse) and assessment level (toetsniveau)
    mask = (df_gamma["gevolgklasse"].str.startswith(cc)) & (df_gamma["toetsniveau"].str.contains(safety_level, case=False))
    matching_rows = df_gamma[mask]

    if matching_rows.empty:
        raise ValueError(f"No gamma factors found for CC class '{cc}' and safety level '{safety_level}'")

    # Create a dictionary with both 6.10a and 6.10b values
    gamma_factors: dict[str, dict[str, float]] = {
        "6.10a": {},
        "6.10b": {},
    }

    # Define the gamma factor types to extract
    gamma_keys = [
        "gamma_Gjsup",
        "gamma_Gjsup_bb2003",
        "gamma_Gjinf",
        "gamma_Qverkeer",
        "gamma_Qverkeer_bb2003",
        "gamma_Qwind",
        "gamma_Qoverig",
        "gamma_Gset_lin",
        "gamma_Gset_nonlin",
        "gamma_P",
    ]

    # Populate gamma factors for both combinations
    for combination in ["6.10a", "6.10b"]:
        combination_rows = matching_rows[matching_rows["vergelijking"].str.contains(combination)]
        if combination_rows.empty:
            raise ValueError(f"No data found for combination {combination}")

        try:
            # Extract all gamma factors for the current combination at once
            gamma_values = {gamma_key: float(combination_rows[gamma_key].iloc[0]) for gamma_key in gamma_keys}
            gamma_factors[combination].update(gamma_values)
        except (KeyError, IndexError, ValueError) as e:
            raise ValueError(f"Failed to extract gamma factors for combination {combination}") from e

    # Correct gamma factors for the case if building year is 2003 or before
    if int(building_year) <= 2003:
        for combination in ["6.10a", "6.10b"]:
            gamma_factors[combination]["gamma_Gjsup"] = gamma_factors[combination]["gamma_Gjsup_bb2003"]
            gamma_factors[combination]["gamma_Qverkeer"] = gamma_factors[combination]["gamma_Qverkeer_bb2003"]

    return gamma_factors


def get_load_categories() -> dict[str, list[str]]:
    """
    Get the categorized lists of load cases.

    Returns:
        Dictionary containing lists of load cases by category.

    """
    return {
        "permanent": ["Permanent", "Voorspanning", "Zetting"],
        "traffic": [
            "TS - rs 1",
            "TS - rs 2",
            "TS - rs 3",
            "UDL - Main",
            "UDL - Other",
            "UDL - Rest",
            "Enkele as",
            "Horizontale belasting",
            "Dienstvoertuig Qserv",
            "Fiets- en voetpaden",
            "Mensenmenigte",
            "Bijzondere voertuigen",
            "Onbedoeld voertuig",
        ],
        "wind": ["Wind Fwk", "Wind Fw*"],
        "temperature": ["Temperatuur"],
        "snow": ["Sneeuw"],
    }


def get_leading_action_positions() -> set[tuple[str, str]]:
    """
    Get the table positions for leading actions which should be highlighted.

    Returns:
        Set of tuples containing (row_name, col_name) pairs for leading actions.

    """
    return {
        ("Perm", "Permanent"),
        ("Perm", "Voorspanning"),
        ("Perm zet", "Zetting"),
        ("gr1a", "TS - rs 1"),
        ("gr1a", "TS - rs 2"),
        ("gr1a", "TS - rs 3"),
        ("gr1a", "UDL - Main"),
        ("gr1a", "UDL - Other"),
        ("gr1a", "UDL - Rest"),
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


def get_project_scope() -> list[str]:
    """
    Get the load cases that represent the project scope.

    Returns:
        List of load case names included in the project scope.

    """
    return [
        "Permanent",
        "TS - rs 1",
        "TS - rs 2",
        "TS - rs 3",
        "UDL - Main",
        "UDL - Other",
        "UDL - Rest",
        "Dienstvoertuig Qserv",
        "Fiets- en voetpaden",
        "Mensenmenigte",
        "Bijzondere voertuigen",
        "Onbedoeld voertuig",
        "Temperatuur",
    ]


def validate_combination_params(params: dict) -> tuple[str, str, str]:
    """
    Validate and extract required parameters for load combination generation.

    This function is deprecated. Use LoadCombinationConfig.from_params_dict() instead.

    Args:
        params: Parameter dictionary containing configuration values

    Returns:
        Tuple of (cc_class, design_code, construction_year)

    Raises:
        KeyError: If required parameters are missing
        ValidationError: If parameter values are invalid

    """
    # Use Pydantic model for validation
    config = LoadCombinationConfig.from_params_dict(params)
    return config.to_tuple()


def calculate_dynamic_udl_factor(  # noqa: PLR0912
    params: Any,  # noqa: ANN401
    length_bridgedeck: float,
    lane_type: str,
) -> float:
    """
    Calculate the dynamic UDL factor for load combinations.

    NEW SYSTEM: All UDL loads in SCIA have base value 2500 N/m².
    This function calculates the dynamic factor that should be multiplied with
    the base psi/gamma factor from the combination table.

    The calculation method depends on berekeningsniveau:
    - "Theoretische wegindeling": alpha_trend × alpha_q (from NEN-EN 1991-2) × lane_factor
    - "Werkelijke wegindeling": alpha_trend × alpha_q (from NEN-EN 1991-2) × lane_factor
    - "Werkelijke wegindeling onderliggend wegennet": alpha_trend × 0.8 × lane_factor
    - "Werkelijke wegindeling met bebording": signage_factor (replaces all other factors)

    Where lane_factor: 3.6 for main lane, 1.0 for other lanes and rest areas

    :param params: Bridge parameters (dict or BridgeParametrization) containing reference period,
                   berekeningsniveau, and signage settings
    :type params: Any
    :param length_bridgedeck: Length of the bridge deck in meters
    :type length_bridgedeck: float
    :param lane_type: Type of lane ("main", "other", or "rest")
    :type lane_type: str
    :returns: Dynamic factor to multiply with base psi/gamma factor
    :rtype: float
    """
    # Extract berekeningsniveau and signage from params
    berekeningsniveau = None
    signage = None
    try:
        if isinstance(params, dict):
            berekeningsniveau = params.get("berekeningsniveau")
            signage = params.get("signage")
        else:
            berekeningsniveau = getattr(params, "berekeningsniveau", None)
            signage = getattr(params, "signage", None)
    except (AttributeError, TypeError):
        pass

    # Get lane factor
    if lane_type == "main":
        lane_factor = UDL_MAIN_LANE_FACTOR  # 3.6
    elif lane_type == "other":
        lane_factor = UDL_OTHER_LANE_FACTOR  # 1.0
    else:  # rest
        lane_factor = UDL_REST_AREA_FACTOR  # 1.0

    # Special case: signage-based calculation (replaces all other factors)
    if berekeningsniveau == "Werkelijke wegindeling met bebording" and signage:
        try:
            signage_index = SIGNAGE_WEIGHT_OPTIONS.index(signage)
            signage_factor = SIGNAGE_LOAD_FACTORS[signage_index]
            # For signage mode, the factor replaces psi × alpha_trend × alpha_q
            # We still apply the lane factor to account for lane importance
            return float(signage_factor * lane_factor)
        except (ValueError, IndexError):
            # Fallback if signage value is invalid
            pass

    # Calculate alpha_trend factor (used for all non-signage modes)
    reference_period = get_reference_period(params)
    alpha_trend = get_alpha_trend_nen_8701(length_bridgedeck, reference_period + 2010)

    # Calculate alpha_q factor based on berekeningsniveau
    if berekeningsniveau == "Werkelijke wegindeling onderliggend wegennet":
        # Use fixed alpha_q values for underlying road network
        alpha_q_factors = [ALPHA_Q_MAIN_LANE_ONDERLIGGEND, ALPHA_Q_OTHER_LANE_ONDERLIGGEND]
        # Main lane uses different value than other lanes/rest areas
        if lane_type == "main":
            alpha_q = alpha_q_factors[0]  # 1.35
        elif lane_type == "other":
            alpha_q = alpha_q_factors[1]
        else:  # rest
            alpha_q = alpha_q_factors[1]
    else:
        # Default: use standard alpha_q from NEN-EN 1991-2
        # Returns [alpha_Q_q, alpha_qr] where:
        # - alpha_Q_q (index 0): for main lanes and other lanes
        # - alpha_qr (index 1): for rest areas only
        alpha_q_factors = get_alpha_q_nen_en_1991_2(length_bridgedeck, nobs=NOBS_DEFAULT)
        # Rest areas use alpha_qr (index 1), main/other lanes use alpha_Q_q (index 0)
        alpha_q = alpha_q_factors[1] if lane_type == "rest" else alpha_q_factors[0]

    # Calculate and return dynamic factor
    dynamic_factor = alpha_trend * alpha_q * lane_factor
    return float(dynamic_factor)


def calculate_dynamic_tandem_factor(
    params: Any,  # noqa: ANN401
    length_bridgedeck: float,
    lane_type: str,
) -> float:
    """
    Calculate the dynamic tandem factor for load combinations.

    NEW SYSTEM: All tandem loads in SCIA have base value 100 kN (625000 N/m²).
    This function calculates the dynamic factor that should be multiplied with
    the base psi/gamma factor from the combination table.

    The calculation method depends on berekeningsniveau:
    - "Theoretische wegindeling": psi × alpha_trend × alpha_q (from NEN-EN 1991-2) × lane_factor
    - "Werkelijke wegindeling": psi × alpha_trend × alpha_q (from NEN-EN 1991-2) × lane_factor
    - "Werkelijke wegindeling onderliggend wegennet": psi × alpha_trend × 0.8 × lane_factor
    - "Werkelijke wegindeling met bebording": signage_factor (replaces all other factors)

    Where lane_factor: 3 for rs 1, 2 for rs 2, 1 for rs 3

    :param params: Bridge parameters (dict or BridgeParametrization) containing reference period,
                   berekeningsniveau, and signage settings
    :type params: Any
    :param length_bridgedeck: Length of the bridge deck in meters
    :type length_bridgedeck: float
    :param lane_type: Type of lane ("rs 1", "rs 2", or "rs 3")
    :type lane_type: str
    :returns: Dynamic factor to multiply with base psi/gamma factor
    :rtype: float
    """
    from src.integrations.scia_integration.constants.loads import (
        TANDEM_MAIN_LANE_FACTOR,
        TANDEM_SECOND_LANE_FACTOR,
        TANDEM_THIRD_LANE_FACTOR,
    )

    # Extract berekeningsniveau and signage from params
    berekeningsniveau = None
    signage = None
    try:
        if isinstance(params, dict):
            berekeningsniveau = params.get("berekeningsniveau")
            signage = params.get("signage")
        else:
            berekeningsniveau = getattr(params, "berekeningsniveau", None)
            signage = getattr(params, "signage", None)
    except (AttributeError, TypeError):
        pass

    # Get lane factor
    if lane_type == "rs 1":
        lane_factor = TANDEM_MAIN_LANE_FACTOR  # 3
    elif lane_type == "rs 2":
        lane_factor = TANDEM_SECOND_LANE_FACTOR  # 2
    else:  # "rs 3"
        lane_factor = TANDEM_THIRD_LANE_FACTOR  # 1

    # Special case: signage-based calculation (replaces all other factors)
    if berekeningsniveau == "Werkelijke wegindeling met bebording" and signage:
        try:
            signage_index = SIGNAGE_WEIGHT_OPTIONS.index(signage)
            signage_factor = SIGNAGE_LOAD_FACTORS[signage_index]
            # For signage mode, the factor replaces psi × alpha_trend × alpha_q
            # We still apply the lane factor to account for lane importance
            return float(signage_factor * lane_factor)
        except (ValueError, IndexError):
            # Fallback if signage value is invalid
            pass

    # Calculate psi factor
    reference_period = get_reference_period(params)
    psi_factor = get_psi_nen_8701(length_bridgedeck, reference_period)

    # Calculate alpha_trend factor
    alpha_trend = get_alpha_trend_nen_8701(length_bridgedeck, reference_period + 2010)

    # Calculate alpha_q factor based on berekeningsniveau
    if berekeningsniveau == "Werkelijke wegindeling onderliggend wegennet":
        # Use fixed alpha_q value for underlying road network
        alpha_q = ALPHA_Q_ONDERLIGGEND  # 0.8
    else:
        # Default: use standard alpha_q from NEN-EN 1991-2 (first value for tandem)
        alpha_q_factors = get_alpha_q_nen_en_1991_2(length_bridgedeck, nobs=NOBS_DEFAULT)
        alpha_q = alpha_q_factors[0]  # Tandem systems use alpha_Q_q (first value)

    # Calculate and return dynamic factor
    dynamic_factor = psi_factor * alpha_trend * alpha_q * lane_factor
    return float(dynamic_factor)


def get_initial_combination_table() -> pd.DataFrame:
    """
    Read and prepare the initial combination table from the NEN 8700 CSV file.

    Returns:
        DataFrame containing the initial psi factors with 'Combinatie' as index

    """
    return pd.read_csv(PSI_NEN_8700_PATH, sep=";", decimal=",", index_col="Combinatie")


def prepare_combination_table(params: dict) -> pd.DataFrame:
    """
    Prepare the combination table with gamma factors applied.

    Args:
        params: Parameter dictionary containing configuration values

    Returns:
        DataFrame with gamma factors applied to the psi factors

    """
    # Validate parameters using Pydantic model
    config = LoadCombinationConfig.from_params_dict(params)
    cc_class, design_code, construction_year = config.cc_class, config.design_code, str(config.construction_year)

    # Get initial table
    df_combination_table_psi = get_initial_combination_table()

    # Get gamma factors
    gamma_factors = get_gamma_factors(cc=cc_class, safety_level=design_code, building_year=construction_year)

    # Convert to float64 to ensure dtype compatibility
    df_combination_table_gamma_psi = df_combination_table_psi.astype("float64")

    # Get load categories
    load_categories = get_load_categories()

    # Create masks for different load types
    permanent_mask = df_combination_table_gamma_psi.columns.isin(load_categories["permanent"])
    traffic_mask = df_combination_table_gamma_psi.columns.isin(load_categories["traffic"])
    wind_mask = df_combination_table_gamma_psi.columns.isin(load_categories["wind"])
    other_mask = df_combination_table_gamma_psi.columns.isin(load_categories["temperature"] + load_categories["snow"])

    # Apply gamma factors for both combinations
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

    # Apply dynamic UDL factors to the three UDL columns
    # Extract bridge length from params
    if params.get("bridge_segments_array"):
        total_length = sum(segment["l"] for segment in params["bridge_segments_array"])

        # Calculate dynamic factors for each UDL lane type
        udl_main_factor = calculate_dynamic_udl_factor(params, total_length, "main")
        udl_other_factor = calculate_dynamic_udl_factor(params, total_length, "other")
        udl_rest_factor = calculate_dynamic_udl_factor(params, total_length, "rest")

        # Apply dynamic factors to UDL columns if they exist
        if "UDL - Main" in df_combination_table_gamma_psi.columns:
            df_combination_table_gamma_psi["UDL - Main"] *= udl_main_factor
        if "UDL - Other" in df_combination_table_gamma_psi.columns:
            df_combination_table_gamma_psi["UDL - Other"] *= udl_other_factor
        if "UDL - Rest" in df_combination_table_gamma_psi.columns:
            df_combination_table_gamma_psi["UDL - Rest"] *= udl_rest_factor

        # Calculate dynamic factors for each tandem lane type
        tandem_rs1_factor = calculate_dynamic_tandem_factor(params, total_length, "rs 1")
        tandem_rs2_factor = calculate_dynamic_tandem_factor(params, total_length, "rs 2")
        tandem_rs3_factor = calculate_dynamic_tandem_factor(params, total_length, "rs 3")

        # Apply dynamic factors to tandem columns if they exist
        if "TS - rs 1" in df_combination_table_gamma_psi.columns:
            df_combination_table_gamma_psi["TS - rs 1"] *= tandem_rs1_factor
        if "TS - rs 2" in df_combination_table_gamma_psi.columns:
            df_combination_table_gamma_psi["TS - rs 2"] *= tandem_rs2_factor
        if "TS - rs 3" in df_combination_table_gamma_psi.columns:
            df_combination_table_gamma_psi["TS - rs 3"] *= tandem_rs3_factor

    # Round UDL and tandem columns to 3 decimal places for better readability
    udl_columns = ["UDL - Main", "UDL - Other", "UDL - Rest"]
    tandem_columns = ["TS - rs 1", "TS - rs 2", "TS - rs 3"]
    for col in udl_columns + tandem_columns:
        if col in df_combination_table_gamma_psi.columns:
            df_combination_table_gamma_psi[col] = df_combination_table_gamma_psi[col].round(3)

    # Filter out zero rows and return
    return df_combination_table_gamma_psi[df_combination_table_gamma_psi.sum(axis=1) != 0]


def highlight_leading_actions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply highlighting to leading action cells in the load combination table.

    Args:
        df: DataFrame to style
    Returns:
        DataFrame with background-color styling applied

    """
    # Create empty styling DataFrame with same shape
    styling = pd.DataFrame("", index=df.index, columns=df.columns)

    # Apply highlighting to leading action positions
    for row_name, col_name in get_leading_action_positions():
        # Skip if column doesn't exist in the DataFrame
        if col_name not in df.columns:
            continue

        # Find matching indices in the current DataFrame
        matching_indices = [idx for idx in df.index if len(idx.split(" ", 1)) > 1 and row_name == idx.split(" ", 1)[1]]

        for idx in matching_indices:
            if idx in df.index and col_name in df.columns:
                styling.loc[idx, col_name] = "background-color: lightgreen"

    return styling


def create_load_combination_table(params: dict) -> Styler:
    """
    Generates a styled table view of load combinations based on the NEN8700 combination table.

    Args:
        params (dict): Object containing parameters for load combination generation.
                      Required keys:
                      - cc_class: The consequence class
                      - design_code: The safety level code
                      - info: Dictionary containing construction_year

    Returns:
        Styled table showing load combinations and their active loads.

    Raises:
        KeyError: If required parameters are missing from the params dict.

    """
    # Prepare the initial table with gamma factors applied
    df_combination_table_gamma_psi = prepare_combination_table(params)

    # Filter columns so that the load cases represent the project scope
    load_cases_project = get_project_scope()
    df_combination_table_gamma_psi = df_combination_table_gamma_psi[df_combination_table_gamma_psi.columns.intersection(load_cases_project)]

    # Filter rows so that the load cases represent the project scope
    load_combinations_project = [(row_name, col_name) for row_name, col_name in get_leading_action_positions() if col_name in load_cases_project]

    # Filter rows based on load_combinations_project
    valid_row_names = {row_name for row_name, _ in load_combinations_project}
    df_combination_table_gamma_psi = df_combination_table_gamma_psi[
        [idx.split(" ", 1)[1] in valid_row_names if len(idx.split(" ", 1)) > 1 else False for idx in df_combination_table_gamma_psi.index]
    ]

    # Round values in table to 5 decimal places
    df_combination_table_gamma_psi = df_combination_table_gamma_psi.round(5)

    # Round UDL columns specifically to 3 decimal places (they tend to have larger values)
    udl_columns = ["UDL - Main", "UDL - Other", "UDL - Rest"]
    for col in udl_columns:
        if col in df_combination_table_gamma_psi.columns:
            df_combination_table_gamma_psi[col] = df_combination_table_gamma_psi[col].round(3)

    # Apply styling using the apply method (type-safe approach) and return directly
    return df_combination_table_gamma_psi.style.apply(lambda _: highlight_leading_actions(df_combination_table_gamma_psi), axis=None)


def get_psi_nen_8701(span: float, reference_period: float) -> float:
    """
    Calculate the psi factor according to NEN 8701 based on span length and reference period.

    The psi factor is determined by interpolating values from NEN 8701 based on
    the span length and reference period. The function uses bilinear interpolation
    to calculate intermediate values for combinations not directly available in the table.

    For spans outside the valid range:
    - Spans < 20m are calculated using span = 20m
    - Spans > 200m are calculated using span = 200m

    For reference periods outside the valid range:
    - Reference periods < 1/12 year are calculated using reference_period = 1/12 year
    - Reference periods > 100 years are calculated using reference_period = 100 years

    Args:
        span: Length of the span in meters
        reference_period: Reference period in years

    Returns:
        float: Interpolated psi factor value

    """
    # Read the CSV file
    psi_data = pd.read_csv(PSI_NEN_8701_PATH, sep=";", decimal=",")

    # Extract x (spans) and y (reference periods) coordinates from column headers and index
    spans = np.array([float(col) for col in psi_data.columns[1:]])  # spans from columns

    # Handle reference periods - use list comprehension instead of for loop
    reference_periods = np.array([float(period_str) for period_str in psi_data.iloc[:, 0]])

    # Extract z values (psi factors)
    z_values = psi_data.iloc[:, 1:].to_numpy()

    # Create interpolator
    interpolator = RegularGridInterpolator(
        (reference_periods, spans),
        z_values,
        method="linear",
        bounds_error=False,  # Allow extrapolation
        fill_value=None,  # Will use nearest value for out-of-bounds points
    )

    # Clamp span to valid ranges
    clamped_span = min(max(span, min(spans)), max(spans))

    # Clamp reference period to valid ranges
    clamped_reference_period = min(max(reference_period, min(reference_periods)), max(reference_periods))

    # Return interpolated value - extract first (and only) element from the array
    result = interpolator([clamped_reference_period, clamped_span])
    return float(result.item())


def get_alpha_trend_nen_8701(span: float, design_life: int) -> float:
    """
    Calculate the alpha trend factor according to NEN 8701 based on span length and design life.

    The alpha trend factor is determined by interpolating values from NEN 8701 based on
    the span length and design life. Design life determines the target year relative to 2010
    (design life + 2010).

    For spans outside the valid range:
    - Spans < 0m are calculated using span = 0m
    - Spans > 100m are calculated using span = 100m

    For target years outside the table range:
    - Years before 2010 use the 2010 values
    - Years after 2060 use the 2060 values

    Args:
        span: Length of the span in meters
        design_life: Design life in years from the present (e.g., 30 for a 30-year design life)

    Returns:
        float: Interpolated alpha trend factor value

    """
    # Read the CSV file
    alpha_trend_data = pd.read_csv(ALPHA_TREND_NEN_8701_PATH, sep=";", decimal=",")

    # Extract x (years) and y (spans) coordinates from column headers and index
    years = np.array([int(col) for col in alpha_trend_data.columns[1:]])  # years from columns
    spans = np.array([float(row) for row in alpha_trend_data.iloc[:, 0]])  # spans from first column

    # Extract z values (alpha trend factors)
    z_values = alpha_trend_data.iloc[:, 1:].to_numpy()

    # Create interpolator
    interpolator = RegularGridInterpolator(
        (spans, years),
        z_values,
        method="linear",
        bounds_error=False,  # Allow extrapolation for years
        fill_value=None,  # Will use nearest value for out-of-bounds points
    )

    # Clamp span to valid ranges
    clamped_span = min(max(span, min(spans)), max(spans))

    # Calculate target year (relative to 2010 base year)
    present_year = datetime.datetime.now(tz=zoneinfo.ZoneInfo("UTC")).year
    target_year = present_year + design_life
    clamped_year = min(max(target_year, min(years)), max(years))

    # Return interpolated value - extract first (and only) element from the array
    result = interpolator([clamped_span, clamped_year])
    return float(result.item())


def get_dynamic_load_factor(span: float) -> float:
    """
    Calculate the dynamic factor Φ for tram loads according to NEN-EN 1991-2 art. 4.3.4.2 (d).

    The dynamic factor accounts for dynamic amplification of static loads due to
    vehicle-structure interaction for railway and tramway traffic.

    According to NEN-EN 1991-2 art. 4.3.4.2 (d), for tram traffic:
    Φ = 1.40 - L / 500

    Where:
    - L is the span length in meters

    The dynamic factor is limited to a minimum value:
    - Minimum Φ = 1.0 (no amplification below static load)

    For single-span bridges, L is the span length. For multi-span continuous bridges,
    L should be determined according to the standard.

    :param span: Length of the span in meters (L)
    :type span: float
    :returns: Dynamic factor Φ for tram loads (Φ ≥ 1.0)
    :rtype: float

    :raises ValueError: If span <= 0

    """
    if span <= 0:
        raise ValueError("Span length must be greater than 0")

    # Calculate dynamic factor: 1.40 minus span divided by 500
    # According to NEN-EN 1991-2 art. 4.3.4.2 (d)
    dynamic_factor = 1.40 - span / 500.0

    # Apply minimum limit
    dynamic_factor = max(1.0, dynamic_factor)

    return float(dynamic_factor)


def get_alpha_q_nen_en_1991_2(span: float, nobs: int) -> list:
    """
    Calculate the alpha_Q, alpha_q and alpha_qr factors according to NEN-EN 1991-2 based on span length and number of trucks per year.

    The alpha_Q and alpha_q factors are determined by interpolating values from NEN-EN 1991-2 based on
    the span length and Nobs (number of trucks per year). The function uses bilinear interpolation
    to calculate intermediate values for combinations not directly available in the table.

    The alpha_qr factor is only dependent on Nobs and is taken from the last column of the table.

    For spans outside the valid range:
    - Spans < 20m are calculated using span = 20m
    - Spans > 200m are calculated using span = 200m

    For Nobs outside the valid range:
    - Nobs < 200 are calculated using Nobs = 200
    - Nobs > 2000000 are calculated using Nobs = 2000000

    Args:
        span: Length of the span in meters
        nobs: Number of trucks per year (Nobs)

    Returns:
        list: [alpha_Q_q, alpha_qr]

    """
    # Read the CSV file
    alpha_data = pd.read_csv(ALPHA_Q_q_NEN_EN_1991_2_PATH, sep=";", decimal=",")

    # Extract x (spans) and y (Nobs) coordinates from column headers and index
    spans = np.array([float(col) for col in alpha_data.columns[1:-1]])  # spans from columns (excluding first and last)
    nobs_values = np.array([float(row) for row in alpha_data.iloc[:, 0]])  # Nobs from first column

    # Extract z values for alpha_Q_q (all columns except first and last)
    z_values_alpha_q = alpha_data.iloc[:, 1:-1].to_numpy()

    # Extract alpha_qr values (last column only)
    alpha_qr_values = alpha_data.iloc[:, -1].to_numpy()

    # Create interpolator for alpha_Q_q
    interpolator_alpha_q = RegularGridInterpolator(
        (nobs_values, spans),
        z_values_alpha_q,
        method="linear",
        bounds_error=False,  # Allow extrapolation
        fill_value=None,  # Will use nearest value for out-of-bounds points
    )

    # Create interpolator for alpha_qr (1D interpolation based on Nobs only)
    interpolator_alpha_qr = RegularGridInterpolator(
        (nobs_values,),
        alpha_qr_values,
        method="linear",
        bounds_error=False,  # Allow extrapolation
        fill_value=None,  # Will use nearest value for out-of-bounds points
    )

    # Clamp span to valid ranges
    clamped_span = min(max(span, min(spans)), max(spans))

    # Clamp Nobs to valid ranges
    clamped_nobs = min(max(nobs, min(nobs_values)), max(nobs_values))

    # Calculate alpha_Q_q using 2D interpolation
    result_alpha_q = interpolator_alpha_q([clamped_nobs, clamped_span])
    alpha_q = float(result_alpha_q.item())

    # Calculate alpha_qr using 1D interpolation (only depends on Nobs)
    result_alpha_qr = interpolator_alpha_qr([clamped_nobs])
    alpha_qr = float(result_alpha_qr.item())

    return [alpha_q, alpha_qr]
