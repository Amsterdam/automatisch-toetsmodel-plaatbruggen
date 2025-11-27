"""
Helper functions to calculate missing force values from available data.

This module provides functions to calculate missing force components when there's
no match between basis and elementaire dataframes during the merge operation.

The calculations are based on engineering relationships between different force
components. These are placeholder implementations that will be refined later with
proper structural engineering formulas.
"""

import pandas as pd


def calculate_missing_shear_forces(row: pd.Series) -> tuple[float, float]:  # type: ignore[type-arg]
    """
    Calculate missing shear forces (v_x, v_y) from available moment data.

    This is a placeholder implementation using a simplified relationship.
    TODO: Replace with proper structural engineering formulas.

    Debug prints show intermediate calculations.

    :param row: DataFrame row with force/moment data
    :type row: pd.Series
    :returns: Tuple of (v_x, v_y) calculated values
    :rtype: tuple[float, float]
    """
    print(f"DEBUG [calculate_missing_shear_forces]: Calculating shear forces for {row.get('Naam', 'unknown')}")

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

    print(f"DEBUG [calculate_missing_shear_forces]: Available moments - m_xD+={m_xd_plus}, m_xD-={m_xd_minus}, m_yD+={m_yd_plus}, m_yD-={m_yd_minus}")

    # Simplified approximation: V ≈ 2 * M (placeholder formula)
    # This assumes a characteristic length of 0.5m for the moment arm
    if m_xd_plus != 0.0 or m_xd_minus != 0.0:
        v_y = 2.0 * max(abs(m_xd_plus), abs(m_xd_minus))
        print(f"DEBUG [calculate_missing_shear_forces]: Calculated v_y from m_xD: {v_y}")

    if m_yd_plus != 0.0 or m_yd_minus != 0.0:
        v_x = 2.0 * max(abs(m_yd_plus), abs(m_yd_minus))
        print(f"DEBUG [calculate_missing_shear_forces]: Calculated v_x from m_yD: {v_x}")

    print(f"DEBUG [calculate_missing_shear_forces]: Final calculated shear forces - v_x={v_x}, v_y={v_y}")

    return v_x, v_y


def calculate_missing_moments(row: pd.Series) -> tuple[float, float, float, float]:  # type: ignore[type-arg]
    """
    Calculate missing moments (m_xD+, m_xD-, m_yD+, m_yD-) from available shear force data.

    This is a placeholder implementation using a simplified relationship.
    TODO: Replace with proper structural engineering formulas.

    Debug prints show intermediate calculations.

    :param row: DataFrame row with force/moment data
    :type row: pd.Series
    :returns: Tuple of (m_xD+, m_xD-, m_yD+, m_yD-) calculated values
    :rtype: tuple[float, float, float, float]
    """
    print(f"DEBUG [calculate_missing_moments]: Calculating moments for {row.get('Naam', 'unknown')}")

    # Try to derive moments from shear forces (simplified relationship)
    # In reality, M = ∫V dx, but we use a simplified approximation here
    m_xd_plus = 0.0
    m_xd_minus = 0.0
    m_yd_plus = 0.0
    m_yd_minus = 0.0

    # Check if we have shear force data to work with
    v_x = pd.to_numeric(row.get("v_x", 0.0), errors="coerce")
    v_y = pd.to_numeric(row.get("v_y", 0.0), errors="coerce")

    # Replace NaN with 0
    v_x = 0.0 if pd.isna(v_x) else v_x
    v_y = 0.0 if pd.isna(v_y) else v_y

    print(f"DEBUG [calculate_missing_moments]: Available shear forces - v_x={v_x}, v_y={v_y}")

    # Simplified approximation: M ≈ V * 0.5 (placeholder formula)
    # This assumes a characteristic length of 0.5m for the moment arm
    if v_y != 0.0:
        m_xd_plus = v_y * 0.5
        m_xd_minus = -v_y * 0.5  # Negative for opposite side
        print(f"DEBUG [calculate_missing_moments]: Calculated m_xD from v_y: m_xD+={m_xd_plus}, m_xD-={m_xd_minus}")

    if v_x != 0.0:
        m_yd_plus = v_x * 0.5
        m_yd_minus = -v_x * 0.5  # Negative for opposite side
        print(f"DEBUG [calculate_missing_moments]: Calculated m_yD from v_x: m_yD+={m_yd_plus}, m_yD-={m_yd_minus}")

    print(f"DEBUG [calculate_missing_moments]: Final calculated moments - m_xD+={m_xd_plus}, m_xD-={m_xd_minus}, m_yD+={m_yd_plus}, m_yD-={m_yd_minus}")

    return m_xd_plus, m_xd_minus, m_yd_plus, m_yd_minus


def calculate_missing_normal_forces(row: pd.Series) -> tuple[float, float]:  # type: ignore[type-arg]
    """
    Calculate missing normal forces (n_xD, n_yD) from available force/moment data.

    This is a placeholder implementation using a simplified relationship.
    TODO: Replace with proper structural engineering formulas.

    Debug prints show intermediate calculations.

    :param row: DataFrame row with force/moment data
    :type row: pd.Series
    :returns: Tuple of (n_xD, n_yD) calculated values
    :rtype: tuple[float, float]
    """
    print(f"DEBUG [calculate_missing_normal_forces]: Calculating normal forces for {row.get('Naam', 'unknown')}")

    # Try to derive normal forces from shear forces (simplified relationship)
    # This is a very rough approximation for placeholder purposes
    n_xd = 0.0
    n_yd = 0.0

    # Check if we have shear force data to work with
    v_x = pd.to_numeric(row.get("v_x", 0.0), errors="coerce")
    v_y = pd.to_numeric(row.get("v_y", 0.0), errors="coerce")

    # Replace NaN with 0
    v_x = 0.0 if pd.isna(v_x) else v_x
    v_y = 0.0 if pd.isna(v_y) else v_y

    print(f"DEBUG [calculate_missing_normal_forces]: Available shear forces - v_x={v_x}, v_y={v_y}")

    # Simplified approximation: N ≈ 2 * V (placeholder formula)
    # This is just a rough estimate for now
    if v_x != 0.0:
        n_xd = 2.0 * abs(v_x)
        print(f"DEBUG [calculate_missing_normal_forces]: Calculated n_xD from v_x: {n_xd}")

    if v_y != 0.0:
        n_yd = 2.0 * abs(v_y)
        print(f"DEBUG [calculate_missing_normal_forces]: Calculated n_yD from v_y: {n_yd}")

    print(f"DEBUG [calculate_missing_normal_forces]: Final calculated normal forces - n_xD={n_xd}, n_yD={n_yd}")

    return n_xd, n_yd


def fill_missing_force_values(df_merged: pd.DataFrame) -> pd.DataFrame:
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

    Debug prints show which rows are being processed and what calculations are performed.

    :param df_merged: Merged dataframe with potential NaN values
    :type df_merged: pd.DataFrame
    :returns: Dataframe with NaN values replaced by calculated values
    :rtype: pd.DataFrame
    """
    if df_merged.empty:
        return df_merged

    print("DEBUG [fill_missing_force_values]: Starting to fill missing force values")
    print(f"DEBUG [fill_missing_force_values]: Processing {len(df_merged)} rows")

    # Create a copy to avoid modifying the original
    df_filled = df_merged.copy()

    # Track which rows have missing data
    rows_with_missing_data = 0

    # Process each row - ONLY looking for NaN values, not zeros
    for idx, row in df_filled.iterrows():
        # Check for missing (NaN) values - IMPORTANT: pd.isna() checks for NaN, not 0!
        has_missing_shear = pd.isna(row.get("v_x")) or pd.isna(row.get("v_y"))
        has_missing_moments = (
            pd.isna(row.get("m_xD+"))
            or pd.isna(row.get("m_xD-"))
            or pd.isna(row.get("m_yD+"))
            or pd.isna(row.get("m_yD-"))
        )
        has_missing_normal = pd.isna(row.get("n_xD")) or pd.isna(row.get("n_yD"))

        # Only process rows that actually have NaN values (from unmatched merge)
        if has_missing_shear or has_missing_moments or has_missing_normal:
            rows_with_missing_data += 1
            print(f"DEBUG [fill_missing_force_values]: Row {idx} has missing (NaN) data: shear={has_missing_shear}, moments={has_missing_moments}, normal={has_missing_normal}")

            # Calculate missing shear forces ONLY if they are NaN
            if has_missing_shear:
                v_x_calc, v_y_calc = calculate_missing_shear_forces(row)
                if pd.isna(row.get("v_x")):
                    df_filled.at[idx, "v_x"] = v_x_calc
                    print(f"DEBUG [fill_missing_force_values]: Filled v_x at row {idx} with {v_x_calc} (was NaN)")
                if pd.isna(row.get("v_y")):
                    df_filled.at[idx, "v_y"] = v_y_calc
                    print(f"DEBUG [fill_missing_force_values]: Filled v_y at row {idx} with {v_y_calc} (was NaN)")

            # Calculate missing moments ONLY if they are NaN
            if has_missing_moments:
                m_xd_plus_calc, m_xd_minus_calc, m_yd_plus_calc, m_yd_minus_calc = calculate_missing_moments(row)
                if pd.isna(row.get("m_xD+")):
                    df_filled.at[idx, "m_xD+"] = m_xd_plus_calc
                    print(f"DEBUG [fill_missing_force_values]: Filled m_xD+ at row {idx} with {m_xd_plus_calc} (was NaN)")
                if pd.isna(row.get("m_xD-")):
                    df_filled.at[idx, "m_xD-"] = m_xd_minus_calc
                    print(f"DEBUG [fill_missing_force_values]: Filled m_xD- at row {idx} with {m_xd_minus_calc} (was NaN)")
                if pd.isna(row.get("m_yD+")):
                    df_filled.at[idx, "m_yD+"] = m_yd_plus_calc
                    print(f"DEBUG [fill_missing_force_values]: Filled m_yD+ at row {idx} with {m_yd_plus_calc} (was NaN)")
                if pd.isna(row.get("m_yD-")):
                    df_filled.at[idx, "m_yD-"] = m_yd_minus_calc
                    print(f"DEBUG [fill_missing_force_values]: Filled m_yD- at row {idx} with {m_yd_minus_calc} (was NaN)")

            # Calculate missing normal forces ONLY if they are NaN
            if has_missing_normal:
                n_xd_calc, n_yd_calc = calculate_missing_normal_forces(row)
                if pd.isna(row.get("n_xD")):
                    df_filled.at[idx, "n_xD"] = n_xd_calc
                    print(f"DEBUG [fill_missing_force_values]: Filled n_xD at row {idx} with {n_xd_calc} (was NaN)")
                if pd.isna(row.get("n_yD")):
                    df_filled.at[idx, "n_yD"] = n_yd_calc
                    print(f"DEBUG [fill_missing_force_values]: Filled n_yD at row {idx} with {n_yd_calc} (was NaN)")

    print(f"DEBUG [fill_missing_force_values]: Processed {rows_with_missing_data} rows with missing (NaN) data")
    print("DEBUG [fill_missing_force_values]: Finished filling missing force values")

    return df_filled
