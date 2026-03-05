# ruff: noqa: PD901, PD008
"""
Sections-on-Plane Results Processing for SCIA Analysis.

This module handles the extraction and processing of sections-on-plane results from
SCIA XML output.  Sections on plane are an alternative to integration strips and return
2D shell internal forces at each finite-element integration point along the cross-section.

The module processes 16 tables from SCIA output (4 combinations × 4 sub-tables):

Load-combination groups
-----------------------
- ULS_basic   : ULS basic design quantities ("basis grootheden")
- ULS_elementary : ULS elementary design quantities ("elementaire ontwerpgrootheden")
- SLSfreq_basic    : SLS frequent basic design quantities
- SLSfreq_elementary : SLS frequent elementary design quantities

Sub-tables per group (result objects split by direction and type)
-----------------------------------------------------------------
- *_x_reg  : x-direction regular sections (field zones)
- *_y_reg  : y-direction regular sections (field zones)
- *_x_sup  : x-direction support sections
- *_y_sup  : y-direction support sections

Each table contains 2D shell internal forces with SCIA XML column names:
- Naam          section name
- Net           element identifier (e.g. "Element: 28")
- x, y, z       position coordinates [m]
- Belasting     governing load-case/combination name
- m_x           bending moment about the x-axis [N·m/m]
- m_y           bending moment about the y-axis [N·m/m]
- m_xy          torsional moment [N·m/m]
- v_x           shear force in x-direction [N/m]
- v_y           shear force in y-direction [N/m]
- n_x           normal force in x-direction [N/m]
- n_y           normal force in y-direction [N/m]
- n_xy          in-plane shear force [N/m]

Section naming convention (examples)
--------------------------------------
- sec_dir-x_reg_Z1-1_y-10.36_nr-10
- sec_dir-x_sup-11.3_Z1-1_y-9.86_nr-2_part-1
- sec_dir-y_reg_Z1-1_x-5.55_nr-10_part-18
- sec_dir-y_sup-0.0_Z1-1_nr-17
"""

import logging
from typing import Any

import pandas as pd

from .scia_results_processor import extract_nested_table_data

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Table registry
# ---------------------------------------------------------------------------

SECTIONS_ON_PLANE_TABLES: dict[str, str] = {
    "ULS_basic_x_reg": "ULS_basic_x_reg",
    "ULS_basic_y_reg": "ULS_basic_y_reg",
    "ULS_basic_x_sup": "ULS_basic_x_sup",
    "ULS_basic_y_sup": "ULS_basic_y_sup",
    "ULS_elementary_x_reg": "ULS_elementary_x_reg",
    "ULS_elementary_y_reg": "ULS_elementary_y_reg",
    "ULS_elementary_x_sup": "ULS_elementary_x_sup",
    "ULS_elementary_y_sup": "ULS_elementary_y_sup",
    "SLSfreq_basic_x_reg": "SLSfreq_basic_x_reg",
    "SLSfreq_basic_y_reg": "SLSfreq_basic_y_reg",
    "SLSfreq_basic_x_sup": "SLSfreq_basic_x_sup",
    "SLSfreq_basic_y_sup": "SLSfreq_basic_y_sup",
    "SLSfreq_elementary_x_reg": "SLSfreq_elementary_x_reg",
    "SLSfreq_elementary_y_reg": "SLSfreq_elementary_y_reg",
    "SLSfreq_elementary_x_sup": "SLSfreq_elementary_x_sup",
    "SLSfreq_elementary_y_sup": "SLSfreq_elementary_y_sup",
}

# Column mapping: SCIA XML attribute name → internal DataFrame column name
SECTION_COLUMN_MAPPING: dict[str, str] = {
    "Naam": "name",
    "Net": "element",
    "x": "x",
    "y": "y",
    "z": "z",
    "Belasting": "load_case",
    "m_x": "m_x",
    "m_y": "m_y",
    "m_xy": "m_xy",
    "v_x": "v_x",
    "v_y": "v_y",
    "n_x": "n_x",
    "n_y": "n_y",
    "n_xy": "n_xy",
}

# Force/moment columns used for numeric operations (unit conversion, envelopes)
FORCE_MOMENT_COLUMNS: list[str] = ["m_x", "m_y", "m_xy", "v_x", "v_y", "n_x", "n_y", "n_xy"]

# Column mapping for elementary design quantities (basis → elementaire ontwerpgrootheden)
# Covers only the elementary-specific result columns; shared columns already in SECTION_COLUMN_MAPPING
ELEMENTARY_SECTION_COLUMN_MAPPING: dict[str, str] = {
    "m_xD+": "m_xD_pos",
    "m_xD-": "m_xD_neg",
    "m_yD+": "m_yD_pos",
    "m_yD-": "m_yD_neg",
    "m_cD+": "m_cD_pos",
    "m_cD-": "m_cD_neg",
    "n_xD": "n_xD",
    "n_yD": "n_yD",
    "n_cD": "n_cD",
}

# Elementary design quantity columns for numeric coercion
ELEMENTARY_FORCE_MOMENT_COLUMNS: list[str] = [
    "m_xD_pos",
    "m_xD_neg",
    "m_yD_pos",
    "m_yD_neg",
    "m_cD_pos",
    "m_cD_neg",
    "n_xD",
    "n_yD",
    "n_cD",
]

# Nested-data key used by SCIA for sections-on-plane (2D shell results)
_SECTIONS_ON_PLANE_DATA_KEY = "Basis grootheden - Resultaten op snedes:"


# ---------------------------------------------------------------------------
# Single-table extraction
# ---------------------------------------------------------------------------


def extract_sections_on_plane_table(
    results: dict[str, Any],
    table_name: str,
) -> pd.DataFrame:
    """
    Extract a single sections-on-plane table from SCIA XML results.

    :param results: SCIA analysis results dictionary containing parsed XML data
    :type results: dict[str, Any]
    :param table_name: Name of the table to extract (e.g., ``"ULS_basic_x_reg"``)
    :type table_name: str
    :returns: DataFrame with sections-on-plane results; empty DataFrame when the
              table is absent or the data cannot be extracted
    :rtype: pd.DataFrame
    """
    if "xml_parsing" not in results:
        logger.debug("No xml_parsing in results for table '%s'", table_name)
        return pd.DataFrame()

    parsed_tables = results.get("xml_parsing", {}).get("parsed_tables", {})
    if not parsed_tables:
        logger.debug("No parsed_tables in xml_parsing for table '%s'", table_name)
        return pd.DataFrame()

    table_data = parsed_tables.get(table_name)
    if not table_data:
        logger.debug("Table '%s' not found in parsed_tables", table_name)
        return pd.DataFrame()

    expected_columns = list(SECTION_COLUMN_MAPPING.keys())
    section_data = extract_nested_table_data(table_data, expected_columns)

    if not section_data:
        logger.warning(
            "Failed to extract data from table '%s'. "
            "Check whether the SCIA output format has changed.",
            table_name,
        )
        return pd.DataFrame()

    df = pd.DataFrame(section_data)
    logger.debug(
        "Extracted %d rows from table '%s' with columns: %s",
        len(df),
        table_name,
        list(df.columns),
    )
    df = df.rename(columns=SECTION_COLUMN_MAPPING)
    # Elementary tables have different result columns (m_xD+, m_xD-, etc.) — rename those too
    if "elementary" in table_name:
        df = df.rename(columns=ELEMENTARY_SECTION_COLUMN_MAPPING)
    return df


# ---------------------------------------------------------------------------
# All-tables extraction
# ---------------------------------------------------------------------------


def extract_all_sections_on_plane_tables(
    results: dict[str, Any],
) -> dict[str, pd.DataFrame]:
    """
    Extract all 16 sections-on-plane tables from SCIA XML results.

    :param results: SCIA analysis results dictionary containing parsed XML data
    :type results: dict[str, Any]
    :returns: Dictionary mapping table names to DataFrames (empty DataFrame when
              a table is missing)
    :rtype: dict[str, pd.DataFrame]
    """
    extracted: dict[str, pd.DataFrame] = {}
    for table_key, table_name in SECTIONS_ON_PLANE_TABLES.items():
        extracted[table_key] = extract_sections_on_plane_table(results, table_name)
    return extracted


# ---------------------------------------------------------------------------
# Section-name parsing
# ---------------------------------------------------------------------------


def parse_section_name(section_name: str) -> dict[str, str]:
    """
    Parse a sections-on-plane name into its constituent components.

    Section names follow the pattern::

        sec_dir-{dir}_{type}[_{position}]_{zone}[_{coord}]_nr-{nr}[_part-{n}]

    Examples
    --------
    - ``sec_dir-x_reg_Z1-1_y-10.36_nr-10``          → dir=x, type=reg, zone=Z1-1
    - ``sec_dir-x_sup-11.3_Z1-1_y-9.86_nr-2_part-1`` → dir=x, type=sup, zone=Z1-1
    - ``sec_dir-y_reg_Z1-1_x-5.55_nr-10_part-18``    → dir=y, type=reg, zone=Z1-1
    - ``sec_dir-y_sup-0.0_Z1-1_nr-17``               → dir=y, type=sup, zone=Z1-1

    :param section_name: Raw section name from SCIA output
    :type section_name: str
    :returns: Dictionary with keys ``direction``, ``section_type``, ``zone``,
              ``number``; values are empty strings when a component cannot be found
    :rtype: dict[str, str]

    """
    parsed: dict[str, str] = {
        "direction": "",
        "section_type": "",
        "zone": "",
        "number": "",
    }

    if not section_name or not isinstance(section_name, str):
        return parsed

    try:
        parts = section_name.split("_")

        for part in parts:
            if part.startswith("dir-"):
                parsed["direction"] = part.replace("dir-", "")
            elif part == "reg":
                parsed["section_type"] = "reg"
            elif part.startswith("sup"):
                # Handles both bare "sup" and "sup-11.3"
                parsed["section_type"] = "sup"
            elif part.startswith("Z"):
                parsed["zone"] = part
            elif part.startswith("nr-"):
                parsed["number"] = part.replace("nr-", "")
            # Remaining parts (x-, y-, part-) are positional metadata; skip

    except Exception as exc:
        logger.debug("Failed to parse section name '%s': %s", section_name, exc)

    return parsed


# ---------------------------------------------------------------------------
# Column augmentation
# ---------------------------------------------------------------------------


def add_parsed_columns_to_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Augment a sections-on-plane DataFrame with parsed metadata columns.

    Adds ``direction``, ``section_type``, ``zone``, and ``section_number`` columns
    derived from the ``name`` column.  Numeric force/moment and coordinate columns
    are coerced to ``float``.

    :param df: DataFrame with sections-on-plane results (must contain ``"name"`` column)
    :type df: pd.DataFrame
    :returns: DataFrame with additional parsed columns; returns *df* unchanged when
              empty or missing the ``"name"`` column
    :rtype: pd.DataFrame
    """
    if df.empty or "name" not in df.columns:
        return df

    parsed_series = df["name"].apply(parse_section_name)
    df["direction"] = parsed_series.apply(lambda x: x["direction"])
    df["section_type"] = parsed_series.apply(lambda x: x["section_type"])
    df["zone"] = parsed_series.apply(lambda x: x["zone"])
    df["section_number"] = parsed_series.apply(lambda x: x["number"])

    # Coerce numeric columns
    for col in FORCE_MOMENT_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in ELEMENTARY_FORCE_MOMENT_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    for coord in ("x", "y", "z"):
        if coord in df.columns:
            df[coord] = pd.to_numeric(df[coord], errors="coerce")

    return df


# ---------------------------------------------------------------------------
# Envelope processing
# ---------------------------------------------------------------------------


def process_sections_on_plane_envelopes(  # noqa: C901, PLR0912
    tables: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """
    Compute min/max force envelopes from all sections-on-plane tables.

    For each unique combination of zone, direction, and limit state (ULS / SLSfreq):

    - ``m_x``, ``m_y``, ``m_xy``, ``n_x``, ``n_y``, ``n_xy``: use both *reg*
      and *sup* sections (both *basic* and *elementary* quantities).
    - ``v_x``, ``v_y``: use only *reg* sections.

    :param tables: Dictionary mapping table keys to DataFrames (output of
                   :func:`extract_all_sections_on_plane_tables` after column augmentation)
    :type tables: dict[str, pd.DataFrame]
    :returns: DataFrame with one row per governing min/max value; columns include
              ``zone``, ``direction``, ``limit_state``, ``filtered_for``,
              ``name``, ``x``, ``y``, ``load_case``, and all force/moment columns
    :rtype: pd.DataFrame
    """
    envelope_rows: list[pd.Series] = []

    # Force/moment columns to envelope
    moment_normal_cols = ["m_x", "m_y", "m_xy", "n_x", "n_y", "n_xy"]
    shear_cols = ["v_x", "v_y"]

    for limit_state in ("ULS", "SLSfreq"):
        for direction in ("x", "y"):
            # Collect basic + elementary tables for reg and sup
            reg_frames: list[pd.DataFrame] = []
            sup_frames: list[pd.DataFrame] = []

            for quantity in ("basic", "elementary"):
                reg_key = f"{limit_state}_{quantity}_{direction}_reg"
                sup_key = f"{limit_state}_{quantity}_{direction}_sup"

                if reg_key in tables and not tables[reg_key].empty:
                    reg_frames.append(tables[reg_key])
                if sup_key in tables and not tables[sup_key].empty:
                    sup_frames.append(tables[sup_key])

            df_reg = pd.concat(reg_frames, ignore_index=True) if reg_frames else pd.DataFrame()
            df_sup = pd.concat(sup_frames, ignore_index=True) if sup_frames else pd.DataFrame()

            if df_reg.empty and df_sup.empty:
                continue

            # Combine for moments/normals envelope
            df_combined = pd.concat([df_reg, df_sup], ignore_index=True)

            # Collect unique zones
            zones: set[str] = set()
            for df_part in (df_combined, df_reg):
                if not df_part.empty and "zone" in df_part.columns:
                    zones.update(df_part["zone"].dropna().unique())

            for zone in zones:
                zone_combined = (
                    df_combined[df_combined["zone"] == zone]
                    if not df_combined.empty and "zone" in df_combined.columns
                    else pd.DataFrame()
                )
                zone_reg = (
                    df_reg[df_reg["zone"] == zone]
                    if not df_reg.empty and "zone" in df_reg.columns
                    else pd.DataFrame()
                )

                # Moments + normals — from combined reg+sup
                for col in moment_normal_cols:
                    if zone_combined.empty or col not in zone_combined.columns:
                        continue
                    for envelope_type in ("min", "max"):
                        idx = (
                            zone_combined[col].idxmin()
                            if envelope_type == "min"
                            else zone_combined[col].idxmax()
                        )
                        if pd.notna(idx):
                            row = zone_combined.loc[idx].copy()
                            row["filtered_for"] = f"{envelope_type}_{col}"
                            row["limit_state"] = limit_state
                            envelope_rows.append(row)

                # Shear forces — from reg only
                for col in shear_cols:
                    if zone_reg.empty or col not in zone_reg.columns:
                        continue
                    for envelope_type in ("min", "max"):
                        idx = (
                            zone_reg[col].idxmin()
                            if envelope_type == "min"
                            else zone_reg[col].idxmax()
                        )
                        if pd.notna(idx):
                            row = zone_reg.loc[idx].copy()
                            row["filtered_for"] = f"{envelope_type}_{col}"
                            row["limit_state"] = limit_state
                            envelope_rows.append(row)

    if not envelope_rows:
        return pd.DataFrame()

    df_envelope = pd.DataFrame(envelope_rows)
    sort_cols = [c for c in ("zone", "direction", "limit_state", "filtered_for") if c in df_envelope.columns]
    if sort_cols:
        df_envelope = df_envelope.sort_values(by=sort_cols).reset_index(drop=True)
    return df_envelope


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------


def process_all_sections_on_plane(
    results: dict[str, Any],
) -> dict[str, Any]:
    """
    Complete processing of sections-on-plane results from a SCIA analysis.

    Steps performed:

    1. Extract all 16 sections-on-plane tables from the XML output.
    2. Add parsed metadata columns (zone, direction, section_type, section_number).
    3. Build a governing-value envelope DataFrame.

    :param results: SCIA analysis results dictionary containing parsed XML data
    :type results: dict[str, Any]
    :returns: Dictionary with keys:

              - ``"tables"`` → ``dict[str, pd.DataFrame]`` (one entry per table)
              - ``"envelope"`` → ``pd.DataFrame`` (min/max governing values)
    :rtype: dict[str, Any]
    """
    tables = extract_all_sections_on_plane_tables(results)

    processed_tables: dict[str, pd.DataFrame] = {}
    for key, df in tables.items():
        processed_tables[key] = add_parsed_columns_to_dataframe(df) if not df.empty else df

    df_envelope = process_sections_on_plane_envelopes(processed_tables)

    return {
        "tables": processed_tables,
        "envelope": df_envelope,
    }
