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

from pathlib import Path

import numpy as np
import pandas as pd
from pandas.io.formats.style import Styler
from scipy.interpolate import RegularGridInterpolator  # type: ignore[import-untyped]

from app.constants import PSI_FACTORS_NEN8701

# ===================================================================================================================
# Paths
# ===================================================================================================================

PROJECT_PATH = Path(__file__).parent.parent.parent
PSI_NEN8700_PATH = PROJECT_PATH / "resources" / "data" / "code_tables" / "Psi_NEN8700.csv"
GAMMA_NEN8700_PATH = PROJECT_PATH / "resources" / "data" / "code_tables" / "Gamma_NEN8700.csv"

# ===================================================================================================================
# Functions
# ===================================================================================================================


def _clamp(value: float, min_value: float, max_value: float) -> float:
    """
    Clamps a value between min and max values.

    Args:
        value: The value to clamp
        min_value: The minimum allowed value
        max_value: The maximum allowed value

    Returns:
        The clamped value

    """
    return max(min_value, min(value, max_value))


def validate_input(span: float, reference_period: float) -> tuple[float, float]:
    """
    Validate input parameters for psi factor calculation and clamp span between 20 and 200.

    Args:
        span: Bridge span length in meters
        reference_period: Reference period in years

    Returns:
        Tuple of (clamped_span, reference_period)

    Raises:
        TypeError: If inputs are not numeric values
        ValueError: If inputs are invalid values

    """
    if not isinstance(span, int | float) or not isinstance(reference_period, int | float):
        raise TypeError("Span and reference period must be numeric values")

    if span <= 0:
        raise ValueError("Span must be positive")
    if reference_period <= 0:
        raise ValueError("Reference period must be positive")

    valid_periods = sorted(PSI_FACTORS_NEN8701.keys())

    if reference_period > max(valid_periods):
        raise ValueError(f"Reference period must not exceed {max(valid_periods)} years")

    # Clamp span between 20 and 200 meters
    clamped_span = _clamp(span, 20, 200)

    return clamped_span, reference_period


def get_interpolation_data() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Prepare data for 2D interpolation from PSI_FACTORS_NEN8701 table.

    Returns:
        Tuple containing span values, period values, and psi values as 2D array

    """
    spans = sorted(PSI_FACTORS_NEN8701[100].keys())
    periods = sorted(PSI_FACTORS_NEN8701.keys(), reverse=True)  # Sort periods in descending order

    values = np.zeros((len(periods), len(spans)))
    for i, period in enumerate(periods):
        for j, span in enumerate(spans):
            values[i, j] = PSI_FACTORS_NEN8701[period][span]

    return np.array(spans), np.array(periods), values


def get_psi_factor(span: float, reference_period: float) -> float:
    """
    Calculate psi factor using bilinear interpolation.

    Args:
        span: Bridge span length in meters (will be clamped between 20 and 200)
        reference_period: Reference period in years

    Returns:
        Interpolated psi factor value

    Raises:
        ValueError: If inputs are invalid or interpolation fails

    """
    clamped_span, ref_period = validate_input(span, reference_period)

    spans, periods, values = get_interpolation_data()
    interpolator = RegularGridInterpolator((periods, spans), values, method="linear", bounds_error=False, fill_value=None)

    result = interpolator(np.array([ref_period, clamped_span]))

    if result is None or np.isnan(result[0]):
        raise ValueError("Interpolation failed. Input values may be outside valid range.")

    return float(result[0])


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
    df_gamma = pd.read_csv(GAMMA_NEN8700_PATH, sep=";", decimal=",")

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

        for gamma_key in gamma_keys:
            try:
                gamma_factors[combination][gamma_key] = float(combination_rows[gamma_key].iloc[0])
            except (KeyError, IndexError, ValueError) as e:
                raise ValueError(f"Failed to extract {gamma_key} for combination {combination}") from e

    # Correct gamma factors for the case if building year is 2003 or before
    if int(building_year) <= 2003:
        for combination in ["6.10a", "6.10b"]:
            gamma_factors[combination]["gamma_Gjsup"] = gamma_factors[combination]["gamma_Gjsup_bb2003"]
            gamma_factors[combination]["gamma_Qverkeer"] = gamma_factors[combination]["gamma_Qverkeer_bb2003"]

    return gamma_factors


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
    # Validate required parameters
    if not all(key in params for key in ["cc_class", "design_code"]):
        raise KeyError("Missing required parameters: cc_class and/or design_code")
    if "info" not in params or "construction_year" not in params["info"]:
        raise KeyError("Missing required parameter: info.construction_year")

    # Read the code tables from CSV and set "Combinatie" as index
    df_combination_table_psi = pd.read_csv(PSI_NEN8700_PATH, sep=";", decimal=",", index_col="Combinatie")

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
    gamma_factors = get_gamma_factors(
        cc=params["cc_class"],
        safety_level=params["design_code"],
        building_year=params["info"]["construction_year"]
    )

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
    df_combination_table_gamma_psi = df_combination_table_gamma_psi[
        [idx.split(" ", 1)[1] in valid_row_names if len(idx.split(" ", 1)) > 1 else False for idx in df_combination_table_gamma_psi.index]
    ]

    # Round values in table to 5 decimal places
    df_combination_table_gamma_psi = df_combination_table_gamma_psi.round(5)

    def highlight_leading_actions(df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply highlighting to leading action cells in the load combination table.
        
        :param df: DataFrame to style
        :type df: pd.DataFrame
        :returns: DataFrame with background-color styling applied
        :rtype: pd.DataFrame
        """
        # Create empty styling DataFrame with same shape
        styling = pd.DataFrame("", index=df.index, columns=df.columns)
        
        # Apply highlighting to leading action positions
        for row_name, col_name in leading_action_positions:
            # Skip if column doesn't exist in the DataFrame
            if col_name not in df.columns:
                continue
                
            # Find matching indices in the current DataFrame
            matching_indices = [
                idx for idx in df.index 
                if len(idx.split(" ", 1)) > 1 and row_name == idx.split(" ", 1)[1]
            ]
            
            for idx in matching_indices:
                if idx in df.index and col_name in df.columns:
                    styling.loc[idx, col_name] = "background-color: lightgreen"
        
        return styling

    # Apply styling using the apply method (type-safe approach)
    styled_df = df_combination_table_gamma_psi.style.apply(
        lambda _: highlight_leading_actions(df_combination_table_gamma_psi), 
        axis=None
    )

    return styled_df
