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

import numpy as np
import pandas as pd
from pandas.io.formats.style import Styler
from scipy.interpolate import RegularGridInterpolator  # type: ignore[import-untyped]

from app.constants import COMBINATION_TABLE, PSI_FACTORS_NEN8701

""""tedstandard: psi_factor.py"""


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


def create_load_combination_table() -> Styler:
    """
    Generates a styled table view of load combinations based on the COMBINATION_TABLE constant.

    Cells representing leading actions (capital "X") are highlighted with light green background
    based on predefined positions from NEN-EN 1990 table NB.19.

    :returns: Styled table showing load combinations and their active loads.
    :rtype: Styler
    """
    # Get all unique loads (rows) from the first combination
    loads = list(next(iter(COMBINATION_TABLE.values())).keys())

    # Create DataFrame with loads as index and combinations as columns
    data = []
    for load in loads:
        row = [COMBINATION_TABLE[combination][load] for combination in COMBINATION_TABLE]
        data.append(row)

    df_combination_table = pd.DataFrame(data=data, columns=list(COMBINATION_TABLE.keys()), index=loads)

    # Replace empty values with '-' for better readability
    df_combination_table = df_combination_table.fillna("-")

    # Predefined positions for leading actions (capital "X") that should be highlighted
    # Format: (row_name, column_name) - these positions are fixed per NEN-EN 1990 table NB.19
    leading_action_positions = {
        ("Permanente belasting", "Perm"),
        ("Zetting", "Perm zet"),
        ("TS", "gr1a"),
        ("UDL", "gr1a"),
        ("Enkele as", "gr1b"),
        ("Horizontale belasting", "gr2"),
        ("Fiets- en voetpaden", "gr3"),
        ("Mensenmenigte", "gr4"),
        ("Bijzonder voertuigen", "gr5"),
        ("Wind Fwk", "Wind gr1a"),
        ("Wind Fwk", "Wind gr2"),
        ("Temperatuur", "Temp gr1"),
        ("Temperatuur", "Temp gr2"),
        ("Sneeuw", "Sneeuw"),
        ("Impact op of onder de brug", "Aanrijding gr1a"),
        ("Impact op of onder de brug", "Aanrijding gr2"),
    }

    # Create styling function that uses the DataFrame structure to determine positions
    def highlight_leading_actions(val: str) -> str:
        """
        This is a placeholder function - actual styling is applied using set_properties.

        :param val: Cell value (not used in this approach)
        :type val: str
        :returns: Empty string (styling applied elsewhere)
        :rtype: str
        """
        return ""

    # Start with base styling
    styled_df = df_combination_table.style

    # Apply light green background to specific cells using iloc positions
    for row_name, col_name in leading_action_positions:
        if row_name in df_combination_table.index and col_name in df_combination_table.columns:
            row_idx = df_combination_table.index.get_loc(row_name)
            col_idx = df_combination_table.columns.get_loc(col_name)
            styled_df = styled_df.set_properties(subset=pd.IndexSlice[row_name, col_name], **{"background-color": "lightgreen"})

    return styled_df
