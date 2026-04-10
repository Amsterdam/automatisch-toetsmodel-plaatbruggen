# ruff: noqa: PD901, PD008
"""
Integration Strip Results Processing for SCIA Analysis.

This module handles the extraction and processing of integration strip results from SCIA XML output.
Integration strips replace the previous cross-section (section on plane) approach.

The module processes 8 types of tables from SCIA:
- ULS_x_reg: ULS results for x-direction regular strips
- ULS_y_reg: ULS results for y-direction regular strips
- ULS_x_sup: ULS results for x-direction support strips
- ULS_y_sup: ULS results for y-direction support strips
- SLSfreq_x_reg: SLS frequent results for x-direction regular strips
- SLSfreq_y_reg: SLS frequent results for y-direction regular strips
- SLSfreq_x_sup: SLS frequent results for x-direction support strips
- SLSfreq_y_sup: SLS frequent results for y-direction support strips

Each table contains internal 1D forces with columns:
- Naam (strip name)
- dx (position along strip)
- Belasting (load case name)
- N (normal force)
- V_y (shear force y)
- V_z (shear force z)
- M_x (torsion moment)
- M_y (bending moment y)
- M_z (bending moment z)
"""

import logging
from typing import Any

import pandas as pd

from .scia_results_processor import extract_nested_table_data

logger = logging.getLogger(__name__)

# Table names expected in SCIA XML output
INTEGRATION_STRIP_TABLES = {
    "ULS_x_reg": "ULS_x_reg",
    "ULS_y_reg": "ULS_y_reg",
    "ULS_x_sup": "ULS_x_sup",
    "ULS_y_sup": "ULS_y_sup",
    "SLSfreq_x_reg": "SLSfreq_x_reg",
    "SLSfreq_y_reg": "SLSfreq_y_reg",
    "SLSfreq_x_sup": "SLSfreq_x_sup",
    "SLSfreq_y_sup": "SLSfreq_y_sup",
}

# Column mapping from SCIA XML to internal names (Dutch and English variants)
STRIP_COLUMN_MAPPING = {
    # Dutch column names (standard SCIA NL integration)
    "Naam": "name",
    "Belasting": "load_case",
    # English column names (alternative SCIA integration)
    "Name": "name",
    "Case": "load_case",
    # Common to both
    "dx": "dx",
    "N": "N",
    "V_y": "V_y",
    "V_z": "V_z",
    "M_x": "M_x",
    "M_y": "M_y",
    "M_z": "M_z",
}

# Force/moment columns to process for envelopes
FORCE_MOMENT_COLUMNS = ["N", "V_y", "V_z", "M_x", "M_y", "M_z"]


def extract_integration_strip_table(
    results: dict[str, Any],
    table_name: str,
) -> pd.DataFrame:
    """
    Extract a single integration strip table from SCIA XML results.

    :param results: SCIA analysis results dictionary containing parsed XML data
    :type results: dict[str, Any]
    :param table_name: Name of the table to extract (e.g., "ULS_x_reg")
    :type table_name: str
    :returns: DataFrame with integration strip results
    :rtype: pd.DataFrame
    :raises KeyError: If table not found in results
    """
    # Check if we have xml_parsing data
    if "xml_parsing" not in results:
        logger.debug("No xml_parsing in results for table '%s'", table_name)
        return pd.DataFrame()

    parsed_tables = results.get("xml_parsing", {}).get("parsed_tables", {})
    if not parsed_tables:
        logger.debug("No parsed_tables in xml_parsing for table '%s'", table_name)
        return pd.DataFrame()

    table_data = parsed_tables.get(table_name)
    if not table_data:
        logger.warning(
            "Table '%s' not found in parsed_tables. Available tables: %s",
            table_name,
            list(parsed_tables.keys()),
        )
        return pd.DataFrame()

    # Detect SCIA-level parse errors (table_data is an error response, not actual data)
    if isinstance(table_data, dict) and table_data.get("status") in ("error", "not_found"):
        logger.warning(
            "SCIA failed to extract table '%s': %s (error: %s)",
            table_name,
            table_data.get("message", "unknown"),
            table_data.get("error", "none"),
        )
        return pd.DataFrame()

    # Use the shared extraction utility with expected column names for validation
    expected_columns = list(STRIP_COLUMN_MAPPING.keys())
    strip_data = extract_nested_table_data(table_data, expected_columns)

    if not strip_data:
        logger.warning(
            "Failed to extract data from table '%s'. Check if SCIA output format has changed. "
            "Table data keys: %s",
            table_name,
            list(table_data.keys()) if isinstance(table_data, dict) else type(table_data).__name__,
        )
        return pd.DataFrame()

    # Convert to DataFrame and rename columns
    df = pd.DataFrame(strip_data)
    logger.debug(
        "Extracted %d rows from table '%s' with columns: %s",
        len(df),
        table_name,
        list(df.columns),
    )
    return df.rename(columns=STRIP_COLUMN_MAPPING)


def extract_all_integration_strip_tables(
    results: dict[str, Any],
) -> dict[str, pd.DataFrame]:
    """
    Extract all 8 integration strip tables from SCIA XML results.

    :param results: SCIA analysis results dictionary containing parsed XML data
    :type results: dict[str, Any]
    :returns: Dictionary mapping table names to DataFrames
    :rtype: dict[str, pd.DataFrame]
    """
    extracted_tables = {}

    for table_key, table_name in INTEGRATION_STRIP_TABLES.items():
        df = extract_integration_strip_table(results, table_name)
        extracted_tables[table_key] = df

    return extracted_tables


def parse_strip_name(strip_name: str) -> dict[str, str]:
    """
    Parse integration strip name to extract zone, direction, type, and number.

    Example strip name: "strip_dir-x_reg_Z1-1_w-1.0_nr-1"

    Extracts:
    - direction: "x" or "y"
    - strip_type: "reg" (regular) or "sup" (support)
    - zone: "Z1-1" (zone identifier)
    - width: "1.0"
    - number: "1" (strip number within zone)

    :param strip_name: Name of the integration strip from SCIA
    :type strip_name: str
    :returns: Dictionary with parsed components
    :rtype: dict[str, str]
    """
    parsed = {
        "direction": "",
        "strip_type": "",
        "zone": "",
        "width": "",
        "number": "",
    }

    if not strip_name or not isinstance(strip_name, str):
        return parsed

    try:
        # Split by underscores
        parts = strip_name.split("_")

        for part in parts:
            if part.startswith("dir-"):
                parsed["direction"] = part.replace("dir-", "")
            elif part in ["reg", "sup"]:
                parsed["strip_type"] = part
            elif part.startswith("Z"):
                parsed["zone"] = part
            elif part.startswith("w-"):
                parsed["width"] = part.replace("w-", "")
            elif part.startswith("nr-"):
                parsed["number"] = part.replace("nr-", "")

    except Exception as e:
        # Log parsing failures for debugging purposes
        logger.debug("Failed to parse strip name '%s': %s", strip_name, e)

    return parsed


def add_parsed_columns_to_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add parsed zone, direction, and strip type columns to integration strip DataFrame.

    Also applies width correction to force and moment values when strip width != 1.0 m.
    The values from SCIA are total forces/moments over the strip width, so we need to
    divide by the width to get per-meter values when width != 1.0.

    :param df: DataFrame with integration strip results
    :type df: pd.DataFrame
    :returns: DataFrame with additional parsed columns and width-corrected values
    :rtype: pd.DataFrame
    """
    if df.empty or "name" not in df.columns:
        return df

    # Parse all strip names
    parsed_data = df["name"].apply(parse_strip_name)

    # Add parsed columns
    df["direction"] = parsed_data.apply(lambda x: x["direction"])
    df["strip_type"] = parsed_data.apply(lambda x: x["strip_type"])
    df["zone"] = parsed_data.apply(lambda x: x["zone"])
    df["strip_width"] = parsed_data.apply(lambda x: x["width"])
    df["strip_number"] = parsed_data.apply(lambda x: x["number"])

    # Apply width correction to force/moment columns (vectorized for performance)
    # Initialize corrected flag
    df["corrected"] = False

    force_moment_cols = ["N", "V_y", "V_z", "M_x", "M_y", "M_z"]

    # Convert force/moment columns to numeric to avoid type comparison errors
    for col in force_moment_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Also convert dx column to numeric if present
    if "dx" in df.columns:
        df["dx"] = pd.to_numeric(df["dx"], errors="coerce")

    # Convert strip_width to numeric, defaulting to 1.0 for missing/invalid values
    df["strip_width_numeric"] = pd.to_numeric(df["strip_width"], errors="coerce").fillna(1.0)

    # Create mask for rows that need correction (width != 1.0 with tolerance)
    # Use vectorized abs() operation instead of loop
    correction_mask = (df["strip_width_numeric"].abs() - 1.0).abs() > 0.01

    # Set corrected flag for rows that need correction
    df.loc[correction_mask, "corrected"] = True

    # Apply width correction vectorized: divide force/moment columns by width
    # Only for rows where correction_mask is True and width is not zero
    valid_width_mask = correction_mask & (df["strip_width_numeric"] != 0.0)

    if valid_width_mask.any():
        for col in force_moment_cols:
            if col in df.columns:
                # Divide column values by width for rows that need correction
                df.loc[valid_width_mask, col] = df.loc[valid_width_mask, col] / df.loc[valid_width_mask, "strip_width_numeric"]

    # Drop temporary numeric width column
    return df.drop(columns=["strip_width_numeric"])


def process_integration_strip_envelopes(  # noqa: C901, PLR0912
    tables: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """
    Process integration strip tables to extract force/moment envelopes.

    For each unique combination of zone, direction, and limit state (ULS/SLS freq):
    - Find min/max N, M_x, M_y, M_z from both reg and sup strips
    - Find min/max V_y, V_z from reg strips only

    Returns a DataFrame with one row per envelope value, including:
    - zone: Zone identifier (e.g., "Z1-1")
    - direction: "x" or "y"
    - limit_state: "ULS" or "SLSfreq"
    - filtered_for: What this row represents (e.g., "max_N", "min_V_y")
    - All force/moment columns with the envelope value
    - load_case: Load case name for this envelope value
    - dx: Position where envelope occurs

    :param tables: Dictionary of DataFrames for all integration strip tables
    :type tables: dict[str, pd.DataFrame]
    :returns: DataFrame with envelope results
    :rtype: pd.DataFrame
    """
    envelope_rows = []

    # Define which columns to extract from which strip types
    # N, M_x, M_y, M_z: use both reg and sup
    # V_y, V_z: use only reg
    all_moment_normal_cols = ["N", "M_x", "M_y", "M_z"]
    shear_cols = ["V_y", "V_z"]

    # Process each limit state and direction combination
    for limit_state in ["ULS", "SLSfreq"]:
        for direction in ["x", "y"]:
            # Get relevant tables
            reg_key = f"{limit_state}_{direction}_reg"
            sup_key = f"{limit_state}_{direction}_sup"

            df_reg = tables.get(reg_key, pd.DataFrame())
            df_sup = tables.get(sup_key, pd.DataFrame())

            # Add parsed columns if not already present
            if not df_reg.empty and "zone" not in df_reg.columns:
                df_reg = add_parsed_columns_to_dataframe(df_reg)

            if not df_sup.empty and "zone" not in df_sup.columns:
                df_sup = add_parsed_columns_to_dataframe(df_sup)

            # Skip if both are empty
            if df_reg.empty and df_sup.empty:
                continue

            # Get unique zones from both tables
            zones: set[str] = set()
            if not df_reg.empty and "zone" in df_reg.columns:
                zones.update(df_reg["zone"].unique())
            if not df_sup.empty and "zone" in df_sup.columns:
                zones.update(df_sup["zone"].unique())

            # Process each zone
            for zone in zones:
                # Filter data for this zone
                zone_reg = df_reg[df_reg["zone"] == zone] if not df_reg.empty else pd.DataFrame()
                zone_sup = df_sup[df_sup["zone"] == zone] if not df_sup.empty else pd.DataFrame()

                # Combine reg and sup for N, M_x, M_y, M_z
                zone_combined = pd.concat([zone_reg, zone_sup], ignore_index=True)

                # Process each force/moment column
                for col in all_moment_normal_cols:
                    if col not in zone_combined.columns:
                        continue

                    # Find min and max
                    for envelope_type in ["min", "max"]:
                        idx = zone_combined[col].idxmin() if envelope_type == "min" else zone_combined[col].idxmax()

                        if pd.notna(idx):
                            row = zone_combined.loc[idx].copy()
                            row["filtered_for"] = f"{envelope_type}_{col}"
                            row["limit_state"] = limit_state
                            envelope_rows.append(row)

                # Process shear forces (V_y, V_z) from reg only
                for col in shear_cols:
                    if zone_reg.empty or col not in zone_reg.columns:
                        continue

                    # Find min and max
                    for envelope_type in ["min", "max"]:
                        idx = zone_reg[col].idxmin() if envelope_type == "min" else zone_reg[col].idxmax()

                        if pd.notna(idx):
                            row = zone_reg.loc[idx].copy()
                            row["filtered_for"] = f"{envelope_type}_{col}"
                            row["limit_state"] = limit_state
                            envelope_rows.append(row)

    # Create result DataFrame
    if envelope_rows:
        df_envelope = pd.DataFrame(envelope_rows)
        # Sort by zone, direction, limit_state, and filtered_for for readability
        sort_cols = ["zone", "direction", "limit_state", "filtered_for"]
        sort_cols = [col for col in sort_cols if col in df_envelope.columns]
        if sort_cols:
            df_envelope = df_envelope.sort_values(by=sort_cols).reset_index(drop=True)
        return df_envelope

    return pd.DataFrame()


def extract_governing_strip_names(envelope_df: pd.DataFrame) -> set[str]:
    """
    Extract unique governing strip names from envelope DataFrame.

    The envelope DataFrame contains one row per min/max force value.
    Each row has a 'name' column with the strip name that had that governing value.
    This function extracts all unique strip names that are governing for any force component.

    :param envelope_df: DataFrame with envelope results (output of process_integration_strip_envelopes)
    :type envelope_df: pd.DataFrame
    :returns: Set of unique strip names that are governing
    :rtype: set[str]
    """
    if envelope_df.empty or "name" not in envelope_df.columns:
        logger.warning("Envelope DataFrame is empty or missing 'name' column")
        return set()

    # Extract unique strip names from the envelope
    governing_names = set(envelope_df["name"].dropna().unique())

    logger.info(f"Extracted {len(governing_names)} unique governing strip names from envelope")

    return governing_names


def process_all_integration_strips(
    results: dict[str, Any],
) -> dict[str, Any]:
    """
    Complete processing of integration strip results from SCIA.

    This function:
    1. Extracts all 8 integration strip tables from SCIA XML
    2. Adds parsed columns (zone, direction, strip_type)
    3. Creates envelope DataFrame with min/max forces
    4. Returns all processed data for caching

    :param results: SCIA analysis results dictionary containing parsed XML data
    :type results: dict[str, Any]
    :returns: Dictionary containing all processed integration strip data
    :rtype: dict[str, Any]
    """
    # Extract all tables
    tables = extract_all_integration_strip_tables(results)

    # Add parsed columns to each table
    processed_tables = {}
    for key, df in tables.items():
        processed_df = add_parsed_columns_to_dataframe(df) if not df.empty else df
        processed_tables[key] = processed_df

    # Create envelope DataFrame
    df_envelope = process_integration_strip_envelopes(processed_tables)

    return {
        "tables": processed_tables,
        "envelope": df_envelope,
    }
