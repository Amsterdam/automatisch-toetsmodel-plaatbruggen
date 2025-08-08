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

import numpy as np
import pandas as pd
from pandas.io.formats.style import Styler
from scipy.interpolate import RegularGridInterpolator  # type: ignore[import-untyped]

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


def _apply_gamma_for_combination(
    df: pd.DataFrame,
    combination: str,
    gamma_factors: dict[str, dict[str, float]],
    permanent_mask: pd.Series,
    traffic_mask: pd.Series,
    wind_mask: pd.Series,
    other_mask: pd.Series,
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
        _apply_gamma_for_combination(
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
            matching_indices = [idx for idx in df.index if len(idx.split(" ", 1)) > 1 and row_name == idx.split(" ", 1)[1]]

            for idx in matching_indices:
                if idx in df.index and col_name in df.columns:
                    styling.loc[idx, col_name] = "background-color: lightgreen"

        return styling

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
