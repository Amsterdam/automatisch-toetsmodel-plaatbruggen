"""
Helper functions to calculate missing force values from available data.

This module provides functions to calculate missing force components when there's
no match between basis and elementaire dataframes during the merge operation.

The calculations are based on engineering relationships between different force
components and implement the SCIA elementary design magnitude formulas.
"""

import pandas as pd

from src.integrations.scia_integration.results.scia_elem_des_mag import (
    mxd_minus,
    mxd_plus,
    myd_minus,
    myd_plus,
    nxd,
    nyd,
)


def calculate_missing_shear_forces(row: pd.Series) -> tuple[float, float]:  # type: ignore[type-arg]
    """
    Calculate missing shear forces (v_x, v_y) from available moment data.

    This is a placeholder implementation using a simplified relationship.
    TODO: Replace with proper structural engineering formulas.

    :param row: DataFrame row with force/moment data
    :type row: pd.Series
    :returns: Tuple of (v_x, v_y) calculated values
    :rtype: tuple[float, float]
    """
    # Try to derive shear forces from moments (simplified relationship)
    # In reality, V = dM/dx, but we use a simplified approximation here
    v_x = 0.0
    v_y = 0.0

    # Check if we have moment data to work with
    m_xd_plus = pd.to_numeric(row.get("m_xD+", 0.0), errors="coerce")
    m_xd_minus = pd.to_numeric(row.get("m_xD-", 0.0), errors="coerce")
    m_yd_plus = pd.to_numeric(row.get("m_yD+", 0.0), errors="coerce")
    m_yd_minus = pd.to_numeric(row.get("m_yD-", 0.0), errors="coerce")

    # Replace NaN with 0
    m_xd_plus = 0.0 if pd.isna(m_xd_plus) else m_xd_plus
    m_xd_minus = 0.0 if pd.isna(m_xd_minus) else m_xd_minus
    m_yd_plus = 0.0 if pd.isna(m_yd_plus) else m_yd_plus
    m_yd_minus = 0.0 if pd.isna(m_yd_minus) else m_yd_minus

    # Simplified approximation: V ≈ 2 * M (placeholder formula)
    # This assumes a characteristic length of 0.5m for the moment arm
    if m_xd_plus != 0.0 or m_xd_minus != 0.0:
        v_y = 2.0 * max(abs(m_xd_plus), abs(m_xd_minus))

    if m_yd_plus != 0.0 or m_yd_minus != 0.0:
        v_x = 2.0 * max(abs(m_yd_plus), abs(m_yd_minus))

    return v_x, v_y


def calculate_missing_moments(row: pd.Series) -> tuple[float, float, float, float]:  # type: ignore[type-arg]
    """
    Calculate missing moments (m_xD+, m_xD-, m_yD+, m_yD-) from available moment data.

    Uses the SCIA elementary design magnitude formulas based on basic moment components
    (m_x, m_y, m_xy) to calculate the design moments.

    :param row: DataFrame row with force/moment data (must contain m_x, m_y, m_xy)
    :type row: pd.Series
    :returns: Tuple of (m_xD+, m_xD-, m_yD+, m_yD-) calculated values
    :rtype: tuple[float, float, float, float]
    """
    # Get basic moment components (these should come from the basis table)
    m_x = pd.to_numeric(row.get("m_x", 0.0), errors="coerce")
    m_y = pd.to_numeric(row.get("m_y", 0.0), errors="coerce")
    m_xy = pd.to_numeric(row.get("m_xy", 0.0), errors="coerce")

    # Replace NaN with 0
    m_x = 0.0 if pd.isna(m_x) else m_x
    m_y = 0.0 if pd.isna(m_y) else m_y
    m_xy = 0.0 if pd.isna(m_xy) else m_xy

    # Calculate design moments using SCIA formulas
    m_xd_plus = mxd_plus(m_x, m_y, m_xy)
    m_xd_minus = mxd_minus(m_x, m_y, m_xy)
    m_yd_plus = myd_plus(m_x, m_y, m_xy)
    m_yd_minus = myd_minus(m_x, m_y, m_xy)

    return m_xd_plus, m_xd_minus, m_yd_plus, m_yd_minus


def calculate_missing_normal_forces(row: pd.Series) -> tuple[float, float]:  # type: ignore[type-arg]
    """
    Calculate missing normal forces (n_xD, n_yD) from available force data.

    Uses the SCIA elementary design magnitude formulas based on basic force components
    (n_x, n_y, n_xy) to calculate the design normal forces.

    :param row: DataFrame row with force/moment data (must contain n_x, n_y, n_xy)
    :type row: pd.Series
    :returns: Tuple of (n_xD, n_yD) calculated values
    :rtype: tuple[float, float]
    """
    # Get basic force components (these should come from the basis table)
    n_x = pd.to_numeric(row.get("n_x", 0.0), errors="coerce")
    n_y = pd.to_numeric(row.get("n_y", 0.0), errors="coerce")
    n_xy = pd.to_numeric(row.get("n_xy", 0.0), errors="coerce")

    # Replace NaN with 0
    n_x = 0.0 if pd.isna(n_x) else n_x
    n_y = 0.0 if pd.isna(n_y) else n_y
    n_xy = 0.0 if pd.isna(n_xy) else n_xy

    # Calculate design normal forces using SCIA formulas
    n_xd_calc = nxd(n_x, n_y, n_xy)
    n_yd_calc = nyd(n_x, n_y, n_xy)

    return n_xd_calc, n_yd_calc


def fill_missing_force_values(df_merged: pd.DataFrame) -> pd.DataFrame:  # noqa: C901, PLR0912
    """
    Fill missing force/moment values in merged dataframe with calculated values.

    CRITICAL: This function ONLY fills NaN values (missing data from unmatched rows).
    Zero (0) is a valid structural result and will NOT be replaced.

    This function detects NaN values in force/moment columns after merging
    basis and elementaire dataframes, and calculates the missing values based
    on available data using simplified engineering relationships.

    WHY THIS IS NEEDED:
    When performing an outer merge between basis and elementaire tables,
    rows that don't have a match in the other table will get NaN values.
    These NaN values cause JSON serialization errors. We calculate them
    using placeholder formulas that will be refined later.

    BRON COLUMN:
    Adds a "Bron" column to track data source:
    - "SCIA": Values come from a match between basis and elementaire tables
    - "Afgeleid": Values were calculated because no match existed

    :param df_merged: Merged dataframe with potential NaN values
    :type df_merged: pd.DataFrame
    :returns: Dataframe with NaN values replaced by calculated values and "Bron" column added
    :rtype: pd.DataFrame
    """
    if df_merged.empty:
        return df_merged

    # Create a copy to avoid modifying the original
    df_filled = df_merged.copy()

    # Initialize Bron column - default to "SCIA" (matched data)
    df_filled["Bron"] = "SCIA"

    # Process each row - ONLY looking for NaN values, not zeros
    for idx, row in df_filled.iterrows():
        # Check for missing (NaN) values - IMPORTANT: pd.isna() checks for NaN, not 0!
        has_missing_shear = pd.isna(row.get("v_x")) or pd.isna(row.get("v_y"))
        has_missing_moments = pd.isna(row.get("m_xD+")) or pd.isna(row.get("m_xD-")) or pd.isna(row.get("m_yD+")) or pd.isna(row.get("m_yD-"))
        has_missing_normal = pd.isna(row.get("n_xD")) or pd.isna(row.get("n_yD"))

        # Only process rows that actually have NaN values (from unmatched merge)
        if has_missing_shear or has_missing_moments or has_missing_normal:
            # Mark this row as derived (calculated) since it has missing data
            df_filled.at[idx, "Bron"] = "Afgeleid"  # type: ignore[index]

            # Calculate missing shear forces ONLY if they are NaN
            if has_missing_shear:
                v_x_calc, v_y_calc = calculate_missing_shear_forces(row)
                if pd.isna(row.get("v_x")):
                    df_filled.at[idx, "v_x"] = v_x_calc  # type: ignore[index]
                if pd.isna(row.get("v_y")):
                    df_filled.at[idx, "v_y"] = v_y_calc  # type: ignore[index]

            # Calculate missing moments ONLY if they are NaN
            if has_missing_moments:
                m_xd_plus_calc, m_xd_minus_calc, m_yd_plus_calc, m_yd_minus_calc = calculate_missing_moments(row)
                if pd.isna(row.get("m_xD+")):
                    df_filled.at[idx, "m_xD+"] = m_xd_plus_calc  # type: ignore[index]
                if pd.isna(row.get("m_xD-")):
                    df_filled.at[idx, "m_xD-"] = m_xd_minus_calc  # type: ignore[index]
                if pd.isna(row.get("m_yD+")):
                    df_filled.at[idx, "m_yD+"] = m_yd_plus_calc  # type: ignore[index]
                if pd.isna(row.get("m_yD-")):
                    df_filled.at[idx, "m_yD-"] = m_yd_minus_calc  # type: ignore[index]

            # Calculate missing normal forces ONLY if they are NaN
            if has_missing_normal:
                n_xd_calc, n_yd_calc = calculate_missing_normal_forces(row)
                if pd.isna(row.get("n_xD")):
                    df_filled.at[idx, "n_xD"] = n_xd_calc  # type: ignore[index]
                if pd.isna(row.get("n_yD")):
                    df_filled.at[idx, "n_yD"] = n_yd_calc  # type: ignore[index]

    return df_filled
