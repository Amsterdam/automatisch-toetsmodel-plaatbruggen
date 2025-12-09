"""
VIKTOR View Functions for Integration Strip Results.

This module provides view functions to display integration strip results in VIKTOR tables.
Each of the 8 integration strip tables gets its own view function.
"""

from typing import Any

import pandas as pd
from viktor.views import TableResult

from .scia_integration_strips_processor import (
    INTEGRATION_STRIP_TABLES,
    extract_all_integration_strip_tables,
    process_all_integration_strips,
)


def _create_integration_strip_headers() -> list[str]:
    """
    Create column headers for integration strip result tables.

    :returns: List of column headers with units
    :rtype: list[str]
    """
    return [
        "Naam",
        "dx [m]",
        "Belasting",
        "N [kN]",
        "V_y [kN]",
        "V_z [kN]",
        "M_x [kNm]",
        "M_y [kNm]",
        "M_z [kNm]",
        "Zone",
        "Richting",
        "Type",
        "Strip nr",
    ]


def _format_integration_strip_table_data(df: pd.DataFrame) -> list[list[Any]]:
    """
    Format integration strip DataFrame for display in VIKTOR TableResult.

    :param df: DataFrame with integration strip results
    :type df: pd.DataFrame
    :returns: List of rows for table display
    :rtype: list[list[Any]]
    """
    if df.empty:
        # Return a single row with "No data" message to avoid empty table errors
        return [["Geen data", "", "", "", "", "", "", "", "", "", "", "", ""]]

    # Define columns to include in output
    output_columns = [
        "name",
        "dx",
        "load_case",
        "N",
        "V_y",
        "V_z",
        "M_x",
        "M_y",
        "M_z",
        "zone",
        "direction",
        "strip_type",
        "strip_number",
    ]

    # Filter to only include columns that exist
    available_columns = [col for col in output_columns if col in df.columns]

    # Convert DataFrame to list of lists
    data = []
    for _, row in df.iterrows():
        row_data = []
        for col in available_columns:
            value = row.get(col, "")
            # Format numeric values
            if col in ["dx", "N", "V_y", "V_z", "M_x", "M_y", "M_z"] and pd.notna(value):
                try:
                    row_data.append(f"{float(value):.2f}")
                except (ValueError, TypeError):
                    row_data.append(str(value))
            else:
                row_data.append(str(value) if pd.notna(value) else "")
        data.append(row_data)

    return data


def create_integration_strip_table_view(
    results: dict[str, Any],
    table_key: str,
) -> TableResult:
    """
    Create a VIKTOR TableResult for a single integration strip table.

    :param results: SCIA analysis results dictionary
    :type results: dict[str, Any]
    :param table_key: Key of the table to display (e.g., "ULS_x_reg")
    :type table_key: str
    :returns: TableResult with integration strip data
    :rtype: TableResult
    """    
    # Check if we have cached processed results
    integration_strips = results.get("integration_strips")

    if integration_strips is None:
        # Process integration strips if not cached
        integration_strips = process_all_integration_strips(results)
        # Note: Caching will be handled by the controller

    # Get the specific table
    tables = integration_strips.get("tables", {})
    
    df = tables.get(table_key, pd.DataFrame())

    # Format data for display (includes "No data" row if empty)
    data = _format_integration_strip_table_data(df)
    headers = _create_integration_strip_headers()

    return TableResult(data, column_headers=headers)


def create_integration_strip_envelope_table_view(
    results: dict[str, Any],
) -> TableResult:
    """
    Create a VIKTOR TableResult for the integration strip envelope (aggregated min/max values).

    :param results: SCIA analysis results dictionary
    :type results: dict[str, Any]
    :returns: TableResult with envelope data
    :rtype: TableResult
    """
    # Check if we have cached processed results
    integration_strips = results.get("integration_strips")

    if integration_strips is None:
        # Process integration strips if not cached
        integration_strips = process_all_integration_strips(results)
        # Note: Caching will be handled by the controller

    # Get the envelope DataFrame
    df_envelope = integration_strips.get("envelope", pd.DataFrame())

    headers = [
        "Zone",
        "Richting",
        "Grenstoestand",
        "Gefilterd voor",
        "dx [m]",
        "Belasting",
        "N [kN]",
        "V_y [kN]",
        "V_z [kN]",
        "M_x [kNm]",
        "M_y [kNm]",
        "M_z [kNm]",
    ]

    if df_envelope.empty:
        # Return single row with "No data" message to avoid empty table errors
        no_data_row = ["Geen data"] + [""] * 11  # 12 columns total
        return TableResult([no_data_row], column_headers=headers)

    # Define columns to include
    output_columns = [
        "zone",
        "direction",
        "limit_state",
        "filtered_for",
        "dx",
        "load_case",
        "N",
        "V_y",
        "V_z",
        "M_x",
        "M_y",
        "M_z",
    ]

    # Filter to only include columns that exist
    available_columns = [col for col in output_columns if col in df_envelope.columns]

    # Format data
    data = []
    for _, row in df_envelope.iterrows():
        row_data = []
        for col in available_columns:
            value = row.get(col, "")
            # Format numeric values
            if col in ["dx", "N", "V_y", "V_z", "M_x", "M_y", "M_z"] and pd.notna(value):
                try:
                    row_data.append(f"{float(value):.2f}")
                except (ValueError, TypeError):
                    row_data.append(str(value))
            else:
                row_data.append(str(value) if pd.notna(value) else "")
        data.append(row_data)

    return TableResult(data, column_headers=headers)


def create_all_integration_strip_views(
    results: dict[str, Any]
) -> dict[str, TableResult]:
    """
    Create VIKTOR TableResult views for all 8 integration strip tables.

    :param results: SCIA analysis results dictionary
    :type results: dict[str, Any]
    :returns: Dictionary mapping table keys to TableResult objects
    :rtype: dict[str, TableResult]
    """
    views = {}

    for table_key in INTEGRATION_STRIP_TABLES.keys():
        views[table_key] = create_integration_strip_table_view(results, table_key)

    return views


