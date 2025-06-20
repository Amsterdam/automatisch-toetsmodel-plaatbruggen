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
        safety_level: Assessment level ("Verbouw", "Afkeur", "Gebruik")
        building_year: Year of construction (e.g. "1964")

    Returns:
        Dictionary containing gamma factors with their values for both 6.10a and 6.10b

    :raises ValueError: If the CC class or safety level is not found in the table

    """
    # Read the code tables from CSV
    df_gamma = pd.read_csv(GAMMA_NEN8700_PATH, sep=";", index_col=0)

    # Filter rows based on consequence class and safety level
    mask = (df_gamma.index.str.startswith(cc)) & (df_gamma.index.str.contains(safety_level, case=False))
    matching_rows = df_gamma[mask]

    if matching_rows.empty:
        raise ValueError(f"No gamma factors found for CC class '{cc}' and safety level '{safety_level}'")

    # Create a dictionary with both 6.10a and 6.10b values
    gamma_factors = {
        "6.10a": {
            # Use only rows containing "6.10a"
            "gamma_Gjsup": float(matching_rows[matching_rows.index.str.contains("6.10a")]["gamma_Gjsup"].iloc[0]),
            "gamma_Gjsup_bb2003": float(matching_rows[matching_rows.index.str.contains("6.10a")]["gamma_Gjsup_bb2003"].iloc[0]),
            "gamma_Gjinf": float(matching_rows[matching_rows.index.str.contains("6.10a")]["gamma_Gjinf"].iloc[0]),
            "gamma_Qverkeer": float(matching_rows[matching_rows.index.str.contains("6.10a")]["gamma_Qverkeer"].iloc[0]),
            "gamma_Qverkeer_bb2003": float(matching_rows[matching_rows.index.str.contains("6.10a")]["gamma_Qverkeer_bb2003"].iloc[0]),
            "gamma_Qwind": float(matching_rows[matching_rows.index.str.contains("6.10a")]["gamma_Qwind"].iloc[0]),
            "gamma_Qoverig": float(matching_rows[matching_rows.index.str.contains("6.10a")]["gamma_Qoverig"].iloc[0]),
            "gamma_Gset_lin": float(matching_rows[matching_rows.index.str.contains("6.10a")]["gamma_Gset_lin"].iloc[0]),
            "gamma_Gset_nonlin": float(matching_rows[matching_rows.index.str.contains("6.10a")]["gamma_Gset_nonlin"].iloc[0]),
            "gamma_P": float(matching_rows[matching_rows.index.str.contains("6.10a")]["gamma_P"].iloc[0]),
        },
        "6.10b": {
            # Use only rows containing "6.10b"
            "gamma_Gjsup": float(matching_rows[matching_rows.index.str.contains("6.10b")]["gamma_Gjsup"].iloc[0]),
            "gamma_Gjsup_bb2003": float(matching_rows[matching_rows.index.str.contains("6.10b")]["gamma_Gjsup_bb2003"].iloc[0]),
            "gamma_Gjinf": float(matching_rows[matching_rows.index.str.contains("6.10b")]["gamma_Gjinf"].iloc[0]),
            "gamma_Qverkeer": float(matching_rows[matching_rows.index.str.contains("6.10b")]["gamma_Qverkeer"].iloc[0]),
            "gamma_Qverkeer_bb2003": float(matching_rows[matching_rows.index.str.contains("6.10b")]["gamma_Qverkeer_bb2003"].iloc[0]),
            "gamma_Qwind": float(matching_rows[matching_rows.index.str.contains("6.10b")]["gamma_Qwind"].iloc[0]),
            "gamma_Qoverig": float(matching_rows[matching_rows.index.str.contains("6.10b")]["gamma_Qoverig"].iloc[0]),
            "gamma_Gset_lin": float(matching_rows[matching_rows.index.str.contains("6.10b")]["gamma_Gset_lin"].iloc[0]),
            "gamma_Gset_nonlin": float(matching_rows[matching_rows.index.str.contains("6.10b")]["gamma_Gset_nonlin"].iloc[0]),
            "gamma_P": float(matching_rows[matching_rows.index.str.contains("6.10b")]["gamma_P"].iloc[0]),
        },
    }

    return gamma_factors


def create_load_combination_table(consequence_class: str, assessment_level: str, building_year: str) -> Styler:
    """
    Generates a styled table view of load combinations based on the NEN8700 combination table.

    Cells representing leading actions (value of 1) are highlighted with light green background
    based on the load combinations defined in the CSV file.

    Returns:
        Styled table showing load combinations and their active loads.

    """
    # Read the code tables from CSV
    df_combination_table_psi = pd.read_csv(PSI_NEN8700_PATH, sep=";", index_col=0)

    # Lists for load cases related to permanent-, traffic-, wind- and other loads
    permanent_loads = ["Perm", "Perm zet"]
    traffic_loads = ["gr1a", "gr1b", "gr2", "gr3", "gr4", "gr5"]
    wind_loads = ["Wind gr1a", "Wind gr2"]
    temperature_loads = ["Temp gr1", "Temp gr2"]
    snow_loads = ["Sneeuw"]
    accident_loads = ["Cal gr1a", "Cal gr2"]
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

    # Create styling function that uses the DataFrame structure to determine positions
    def highlight_leading_actions(val: str) -> str:
        """
        Process row value for highlighting.

        :param val: Cell value (not used in this approach)
        :type val: str
        :returns: Empty string (styling applied elsewhere)
        :rtype: str
        """
        return ""

    # Start with base styling
    styled_df = df_combination_table_psi.style

    # Apply light green background to specific cells using iloc positions
    for row_name, col_name in leading_action_positions:
        for index_label in df_combination_table_psi.index:
            index_label_modified = " ".join(index_label.split()[1:])
            if row_name == index_label_modified and col_name in df_combination_table_psi.columns:
                styled_df = styled_df.set_properties(subset=pd.IndexSlice[index_label, col_name], **{"background-color": "lightgreen"})

    return styled_df
