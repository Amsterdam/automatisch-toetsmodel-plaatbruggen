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
    # Dutch column names (standard SCIA NL integration)
    "Naam": "name",
    "Net": "element",
    "x": "x",
    "y": "y",
    "z": "z",
    "Belasting": "load_case",
    # English column names (alternative SCIA EN integration)
    "Name": "name",
    "Case": "load_case",
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
            "Failed to extract data from table '%s'. Check whether the SCIA output format has changed.",
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

        sec_dir-{dir}_{type}[_{position}]_{zone}[_{coord}]_nr-{nr}[_part-{n}][_l-{length}]

    Examples
    --------
    - ``sec_dir-x_reg_Z1-1_y-10.36_nr-10_l-1.00``           → dir=x, type=reg, zone=Z1-1, length=1.00
    - ``sec_dir-x_sup-11.3_Z1-1_y-9.86_nr-2_part-1_l-0.50`` → dir=x, type=sup, zone=Z1-1, length=0.50
    - ``sec_dir-y_reg_Z1-1_x-5.55_nr-10_part-18_l-1.00``    → dir=y, type=reg, zone=Z1-1, length=1.00
    - ``sec_dir-y_sup-0.0_Z1-1_nr-17_l-1.00``               → dir=y, type=sup, zone=Z1-1, length=1.00

    :param section_name: Raw section name from SCIA output
    :type section_name: str
    :returns: Dictionary with keys ``direction``, ``section_type``, ``zone``,
              ``number``, ``length``; values are empty strings when a component cannot be found
    :rtype: dict[str, str]

    """
    parsed: dict[str, str] = {
        "direction": "",
        "section_type": "",
        "zone": "",
        "number": "",
        "length": "",
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
            elif part.startswith("l-"):
                parsed["length"] = part.replace("l-", "")
            # Remaining parts (x-, y-, part-) are positional metadata; skip

    except Exception as exc:
        logger.debug("Failed to parse section name '%s': %s", section_name, exc)

    return parsed


# ---------------------------------------------------------------------------
# Column augmentation
# ---------------------------------------------------------------------------


def add_parsed_columns_to_dataframe(df: pd.DataFrame) -> pd.DataFrame:  # noqa: C901
    """
    Augment a sections-on-plane DataFrame with parsed metadata columns.

    Adds ``direction``, ``section_type``, ``zone``, ``section_number``, and
    ``section_length`` columns derived from the ``name`` column.  When the
    section length encoded in the name differs from 1.0 m (tolerance 0.01 m),
    all force/moment values are divided by the section length to normalise them
    to per-metre values, and a ``corrected`` flag column is set to ``True``.

    Numeric force/moment and coordinate columns are coerced to ``float``.

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
    df["section_length"] = parsed_series.apply(lambda x: x["length"])

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

    # --- Section-length correction (analogous to integration-strip width correction) ---
    # Forces from SCIA sections-on-plane are totals over the section length.
    # When the section is shorter than 1.0 m, divide by the actual length to
    # obtain per-metre values.
    df["corrected"] = False
    df["section_length_numeric"] = pd.to_numeric(df["section_length"], errors="coerce").fillna(1.0)
    correction_mask = (df["section_length_numeric"] - 1.0).abs() > 0.01
    df.loc[correction_mask, "corrected"] = True

    valid_mask = correction_mask & (df["section_length_numeric"] != 0.0)
    if valid_mask.any():
        all_force_cols = FORCE_MOMENT_COLUMNS + ELEMENTARY_FORCE_MOMENT_COLUMNS
        for col in all_force_cols:
            if col in df.columns:
                df.loc[valid_mask, col] = df.loc[valid_mask, col] / df.loc[valid_mask, "section_length_numeric"]

    return df.drop(columns=["section_length_numeric"])


# ---------------------------------------------------------------------------
# Envelope processing
# ---------------------------------------------------------------------------


def process_sections_on_plane_envelopes(  # noqa: C901, PLR0912
    tables: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """
    Compute min/max force envelopes from all sections-on-plane tables.

    Basic and elementary quantity tables are processed **separately** so that
    their distinct column sets are never mixed in the same DataFrame.

    For each unique combination of zone, direction, and limit state (ULS / SLSfreq):

    **Basic quantities** (from ``*_basic_*`` tables):

    - ``v_x``, ``v_y``: min/max from *reg* sections only (shear forces).
    - All other basic columns (``m_x``, ``m_y``, ``n_x``, ``n_y``, ``m_xy``,
      ``n_xy``) are not needed and are not carried into the envelope.

    **Elementary design quantities** (from ``*_elementary_*`` tables):

    - ``m_xD_pos``, ``m_xD_neg``, ``m_yD_pos``, ``m_yD_neg``, ``n_xD``,
      ``n_yD``: min/max across both *reg* and *sup* sections.
    - ``m_cD_pos``, ``m_cD_neg``, ``n_cD`` are excluded — not used by IDEA or
      the envelope view.

    :param tables: Dictionary mapping table keys to DataFrames (output of
                   :func:`extract_all_sections_on_plane_tables` after column augmentation)
    :type tables: dict[str, pd.DataFrame]
    :returns: DataFrame with one row per governing min/max value; columns include
              ``zone``, ``direction``, ``limit_state``, ``filtered_for``,
              ``section_type``, ``x``, ``y``, ``load_case``, and the applicable
              force/moment columns for that row's quantity type
    :rtype: pd.DataFrame
    """
    envelope_rows: list[pd.Series] = []

    # Only v_x and v_y are needed from the basic tables (shear governing rows + enrichment).
    # m_x, m_y, n_x, n_y, m_xy, n_xy are not used by IDEA and are not carried into the envelope.
    basic_shear_cols = ["v_x", "v_y"]
    # Elementary design quantity columns
    # m_cD_pos, m_cD_neg, n_cD are twisting/compression quantities not used by IDEA — excluded
    elementary_cols = [c for c in ELEMENTARY_FORCE_MOMENT_COLUMNS if c not in ("m_cD_pos", "m_cD_neg", "n_cD")]

    for limit_state in ("ULS", "SLSfreq"):
        for direction in ("x", "y"):
            # --- Basic tables (kept separate from elementary) ---
            df_basic_reg = tables.get(f"{limit_state}_basic_{direction}_reg", pd.DataFrame())
            df_basic_sup = tables.get(f"{limit_state}_basic_{direction}_sup", pd.DataFrame())

            # --- Elementary tables (kept separate from basic) ---
            df_elem_reg = tables.get(f"{limit_state}_elementary_{direction}_reg", pd.DataFrame())
            df_elem_sup = tables.get(f"{limit_state}_elementary_{direction}_sup", pd.DataFrame())

            # Combine reg+sup within each quantity type
            basic_frames = [df for df in (df_basic_reg, df_basic_sup) if not df.empty]
            elem_frames = [df for df in (df_elem_reg, df_elem_sup) if not df.empty]
            df_basic_combined = pd.concat(basic_frames, ignore_index=True) if basic_frames else pd.DataFrame()
            df_elem_combined = pd.concat(elem_frames, ignore_index=True) if elem_frames else pd.DataFrame()

            if df_basic_reg.empty and df_basic_combined.empty and df_elem_combined.empty:
                continue

            # Collect unique zones across all data for this direction
            zones: set[str] = set()
            for df_part in (df_basic_combined, df_basic_reg, df_elem_combined):
                if not df_part.empty and "zone" in df_part.columns:
                    zones.update(df_part["zone"].dropna().unique())

            for zone in zones:
                zone_basic_combined = (
                    df_basic_combined[df_basic_combined["zone"] == zone]
                    if not df_basic_combined.empty and "zone" in df_basic_combined.columns
                    else pd.DataFrame()
                )
                zone_basic_reg = (
                    df_basic_reg[df_basic_reg["zone"] == zone] if not df_basic_reg.empty and "zone" in df_basic_reg.columns else pd.DataFrame()
                )
                zone_elem_combined = (
                    df_elem_combined[df_elem_combined["zone"] == zone]
                    if not df_elem_combined.empty and "zone" in df_elem_combined.columns
                    else pd.DataFrame()
                )

                # Build (name, load_case) lookup tables for cross-enrichment.
                # Both basic and elementary tables contain the same rows (same sections,
                # same load cases), so an exact (name, load_case) key is sufficient.
                basic_lookup: dict[tuple, pd.Series] = {}
                if not zone_basic_combined.empty and "name" in zone_basic_combined.columns:
                    for _, _r in zone_basic_combined.iterrows():
                        basic_lookup[(_r.get("name"), _r.get("load_case"))] = _r

                elem_lookup: dict[tuple, pd.Series] = {}
                if not zone_elem_combined.empty and "name" in zone_elem_combined.columns:
                    for _, _r in zone_elem_combined.iterrows():
                        elem_lookup[(_r.get("name"), _r.get("load_case"))] = _r

                def _enrich_with_elem(row: pd.Series) -> pd.Series:
                    """Fill in elementary columns on a basic governing row."""
                    key = (row.get("name"), row.get("load_case"))
                    match = elem_lookup.get(key)
                    if match is None:
                        same_name_keys = [k for k in elem_lookup if k[0] == key[0]]
                        logger.warning(
                            "ENRICH MISS (basic→elem): key=%s  available elem keys for same name: %s",
                            key,
                            same_name_keys,
                        )
                        return row
                    for c in elementary_cols:
                        if c in match.index and (c not in row.index or pd.isna(row.get(c))):
                            row[c] = match[c]
                    return row

                def _enrich_with_basic(row: pd.Series) -> pd.Series:
                    """Fill in basic shear columns (v_x, v_y) on an elementary governing row."""
                    key = (row.get("name"), row.get("load_case"))
                    match = basic_lookup.get(key)
                    if match is None:
                        same_name_keys = [k for k in basic_lookup if k[0] == key[0]]
                        logger.warning(
                            "ENRICH MISS (elem→basic): key=%s  available basic keys for same name: %s",
                            key,
                            same_name_keys,
                        )
                        return row
                    for c in basic_shear_cols:
                        if c in match.index and (c not in row.index or pd.isna(row.get(c))):
                            row[c] = match[c]
                    return row

                # Basic shear forces — from reg only (the only governing quantities from basic tables)
                for col in basic_shear_cols:
                    if zone_basic_reg.empty or col not in zone_basic_reg.columns:
                        continue
                    for envelope_type in ("min", "max"):
                        idx = zone_basic_reg[col].idxmin() if envelope_type == "min" else zone_basic_reg[col].idxmax()
                        if pd.notna(idx):
                            row = zone_basic_reg.loc[idx].copy()
                            row["filtered_for"] = f"{envelope_type}_{col}"
                            row["limit_state"] = limit_state
                            row = _enrich_with_elem(row)  # type: ignore[arg-type]
                            envelope_rows.append(row)

                # Elementary design quantity columns — from combined reg+sup elementary
                for col in elementary_cols:
                    if zone_elem_combined.empty or col not in zone_elem_combined.columns:
                        continue
                    for envelope_type in ("min", "max"):
                        idx = zone_elem_combined[col].idxmin() if envelope_type == "min" else zone_elem_combined[col].idxmax()
                        if pd.notna(idx):
                            row = zone_elem_combined.loc[idx].copy()
                            row["filtered_for"] = f"{envelope_type}_{col}"
                            row["limit_state"] = limit_state
                            row = _enrich_with_basic(row)  # type: ignore[arg-type]
                            envelope_rows.append(row)

    if not envelope_rows:
        return pd.DataFrame()

    df_envelope = pd.DataFrame(envelope_rows)
    sort_cols = [c for c in ("zone", "direction", "limit_state", "filtered_for") if c in df_envelope.columns]
    if sort_cols:
        df_envelope = df_envelope.sort_values(by=sort_cols).reset_index(drop=True)
    # Drop columns not needed for IDEA checks or the envelope view (may be present from source rows)
    cols_to_drop = [c for c in ("m_x", "m_y", "n_x", "n_y", "m_xy", "n_xy", "m_cD_pos", "m_cD_neg", "n_cD") if c in df_envelope.columns]
    if cols_to_drop:
        df_envelope = df_envelope.drop(columns=cols_to_drop)
    return df_envelope


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------


def extract_governing_section_names(envelope_df: pd.DataFrame) -> set[str]:
    """
    Extract unique governing section names from the sections-on-plane envelope DataFrame.

    The envelope contains one row per min/max force value; the ``"name"`` column holds
    the section name that produced that governing value.  This function returns the set
    of all unique names that are governing for **any** force component, which is used by
    :func:`~app.bridge.scia_model_builder.run_two_stage_scia_analysis_sections_on_plane`
    to determine which sections to rebuild for Stage 2.

    :param envelope_df: DataFrame produced by :func:`process_sections_on_plane_envelopes`
    :type envelope_df: pd.DataFrame
    :returns: Set of unique section names
    :rtype: set[str]
    """
    if envelope_df.empty or "name" not in envelope_df.columns:
        logger.warning("Sections-on-plane envelope DataFrame is empty or missing 'name' column")
        return set()

    governing_names: set[str] = set(envelope_df["name"].dropna().unique())
    logger.info("Extracted %d unique governing section names from envelope", len(governing_names))
    return governing_names


def extract_governing_section_names_from_results(results: dict[str, Any]) -> set[str]:
    """
    Extract unique section names directly from Stage 1 raw SCIA tables.

    The governing template already exports only one row per section (the governing
    load combination selected by SCIA), so no envelope computation is needed.
    This function collects all unique ``"name"`` values across the 16 raw tables
    and returns them as the set of governing sections for Stage 2.

    :param results: SCIA analysis results dictionary containing parsed XML data
    :type results: dict[str, Any]
    :returns: Set of unique section names found in any of the 16 result tables
    :rtype: set[str]
    """
    tables = extract_all_sections_on_plane_tables(results)
    governing_names: set[str] = set()
    for df in tables.values():
        if not df.empty and "name" in df.columns:
            governing_names.update(df["name"].dropna().unique())
    logger.info("Extracted %d unique governing section names from Stage 1 tables", len(governing_names))
    return governing_names


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
