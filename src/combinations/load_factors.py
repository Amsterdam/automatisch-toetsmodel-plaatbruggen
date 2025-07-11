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
PSI_NEN8700_PATH = PROJECT_PATH / "resources" / "data" / "code_tables" / "Psi_NEN8700.csv"
GAMMA_NEN8700_PATH = PROJECT_PATH / "resources" / "data" / "code_tables" / "Gamma_NEN8700.csv"
PSI_NEN8701_PATH = PROJECT_PATH / "resources" / "data" / "code_tables" / "Psi_nen8701.csv"
ALPHA_TREND_NEN8701_PATH = PROJECT_PATH / "resources" / "data" / "code_tables" / "Alpha_trend_NEN8701.csv"

# PSI Factors from NEN 8701 - extracted from CSV for efficient access
PSI_FACTORS_NEN8701: dict[float, dict[int, float]] = {
    100.0: {20: 1.0, 50: 1.0, 100: 1.0, 200: 1.0},
    50.0: {20: 0.99, 50: 0.99, 100: 0.99, 200: 0.99},
    30.0: {20: 0.99, 50: 0.99, 100: 0.98, 200: 0.97},
    15.0: {20: 0.98, 50: 0.98, 100: 0.96, 200: 0.96},
    1.0: {20: 0.95, 50: 0.94, 100: 0.89, 200: 0.88},
    1.0 / 12.0: {20: 0.91, 50: 0.91, 100: 0.81, 200: 0.81},  # 0.08333333333
}

# ===================================================================================================================
# Functions
# ===================================================================================================================


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


def get_interpolation_data() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Get interpolation data from PSI_FACTORS_NEN8701 for use with RegularGridInterpolator.

    :returns: Tuple of (spans, periods, values) arrays for interpolation
    :rtype: tuple[np.ndarray, np.ndarray, np.ndarray]
    """
    # Extract spans (sorted) and periods (sorted descending for interpolator)
    spans = np.array(sorted(PSI_FACTORS_NEN8701[100.0].keys()))  # [20, 50, 100, 200]
    periods = np.array(sorted(PSI_FACTORS_NEN8701.keys(), reverse=True))  # [100.0, 50.0, 30.0, 15.0, 1.0, 0.083...]

    # Create values array
    values = np.zeros((len(periods), len(spans)))
    for i, period in enumerate(periods):
        for j, span in enumerate(spans):
            values[i, j] = PSI_FACTORS_NEN8701[period][span]

    return spans, periods, values


def validate_input(span: float, reference_period: float) -> tuple[float, float]:
    """
    Validate and clamp input parameters for PSI factor calculation.

    :param span: Span length in meters
    :type span: float | int
    :param reference_period: Reference period in years
    :type reference_period: float | int
    :returns: Tuple of (clamped_span, reference_period)
    :rtype: tuple[float, float]
    :raises TypeError: If span or reference_period are not numeric
    :raises ValueError: If span or reference_period are not positive or reference_period exceeds maximum
    """
    # Type validation
    if not isinstance(span, (int, float)) or not isinstance(reference_period, (int, float)):
        raise TypeError("Span and reference period must be numeric values")

    # Value validation
    if span <= 0:
        raise ValueError("Span must be positive")
    if reference_period <= 0:
        raise ValueError("Reference period must be positive")
    if reference_period > 100.0:  # Max from PSI_FACTORS_NEN8701
        raise ValueError("Reference period must not exceed 100 years")

    # Get valid ranges from PSI_FACTORS_NEN8701
    valid_spans = sorted(PSI_FACTORS_NEN8701[100.0].keys())  # [20, 50, 100, 200]
    min_span, max_span = min(valid_spans), max(valid_spans)

    # Clamp span to valid range
    clamped_span = _clamp(float(span), float(min_span), float(max_span))

    return clamped_span, float(reference_period)


def _clamp(value: float, min_val: float, max_val: float) -> float:
    """
    Clamp a value to a specified range.

    :param value: Value to clamp
    :type value: float
    :param min_val: Minimum allowed value
    :type min_val: float
    :param max_val: Maximum allowed value
    :type max_val: float
    :returns: Clamped value
    :rtype: float
    """
    return min(max(value, min_val), max_val)


def get_psi_nen8701(span: float, reference_period: float) -> float:
    """
    Calculate the psi factor according to NEN 8701 based on span length and reference period.

    The psi factor is determined by interpolating values from NEN 8701 based on
    the span length and reference period. The function uses bilinear interpolation
    to calculate intermediate values for combinations not directly available in the table.

    For spans outside the valid range:
    - Spans < 20m are calculated using span = 20m
    - Spans > 200m are calculated using span = 200m

    For reference periods outside the valid range:
    - Reference periods < 1 year are calculated using reference_period = 1 year
    - Reference periods > 100 years are calculated using reference_period = 100 years

    Args:
        span: Length of the span in meters
        reference_period: Reference period in years

    Returns:
        float: Interpolated psi factor value

    Raises:
        ValueError: If reference period is outside the valid range
        TypeError: If inputs are not numeric

    """
    # Validate and clamp input parameters
    clamped_span, clamped_reference_period = validate_input(span, reference_period)

    # Get interpolation data from extracted constant
    x_coords, y_coords, z_values = get_interpolation_data()

    # Create interpolator
    interpolator = RegularGridInterpolator(
        (y_coords, x_coords),
        z_values,
        method="linear",
        bounds_error=False,  # Use clamping for out-of-bounds values
        fill_value=None,  # Will use nearest value for out-of-bounds points
    )

    # Clamp reference period to interpolation range (additional safety check)
    final_reference_period = _clamp(clamped_reference_period, min(y_coords), max(y_coords))

    # Return interpolated value - extract first (and only) element from the array
    result = interpolator([final_reference_period, clamped_span])
    return float(result.item())


# Backward compatibility alias
get_psi_factor = get_psi_nen8701


def get_alpha_trend_nen8701(span: float, design_life: int) -> float:
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
    alpha_trend_data = pd.read_csv(ALPHA_TREND_NEN8701_PATH, sep=";", decimal=",")

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
