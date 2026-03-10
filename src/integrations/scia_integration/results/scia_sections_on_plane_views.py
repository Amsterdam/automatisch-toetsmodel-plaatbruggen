# ruff: noqa: PD901
"""
VIKTOR View Functions for Sections-on-Plane Results.

Public API
----------
- :func:`create_sections_on_plane_uls_x_reg`
- :func:`create_sections_on_plane_uls_y_reg`
- :func:`create_sections_on_plane_uls_x_sup`
- :func:`create_sections_on_plane_uls_y_sup`
- :func:`create_sections_on_plane_slsfreq_x_reg`
- :func:`create_sections_on_plane_slsfreq_y_reg`
- :func:`create_sections_on_plane_slsfreq_x_sup`
- :func:`create_sections_on_plane_slsfreq_y_sup`
- :func:`create_sections_on_plane_envelopes`
"""

from typing import Any

import pandas as pd
from viktor.views import TableResult

from .scia_sections_on_plane_processor import process_all_sections_on_plane

# ---------------------------------------------------------------------------
# Column order and headers for the combined view
# ---------------------------------------------------------------------------

# Ordered output columns for the combined (basic + elementary) table.
# The merge key is "name"; both tables supply the common geometry columns.
_COMBINED_OUTPUT_COLUMNS: list[str] = [
    "name",
    "x",
    "y",
    "z",
    "zone",
    "direction",
    "section_type",
    "section_number",
    "load_case",
    # basic design quantities (retained)
    "v_x",
    "v_y",
    # elementary design quantities (retained)
    "m_xD_pos",
    "m_xD_neg",
    "m_yD_pos",
    "m_yD_neg",
    "n_xD",
    "n_yD",
]

_COMBINED_HEADERS: list[str] = [
    "Naam",
    "x [m]",
    "y [m]",
    "z [m]",
    "Zone",
    "Richting",
    "Type",
    "Sectie nr",
    "Belasting",
    # basic
    "v_x [kN/m]",
    "v_y [kN/m]",
    # elementary
    "m_xD+ [kN\u00b7m/m]",
    "m_xD- [kN\u00b7m/m]",
    "m_yD+ [kN\u00b7m/m]",
    "m_yD- [kN\u00b7m/m]",
    "n_xD [kN/m]",
    "n_yD [kN/m]",
]

_NUM_COMBINED_COLUMNS: int = len(_COMBINED_HEADERS)

# Governing-quantity values that are shown in the envelope table view.
# Only the 8 design quantities requested by the user are included.
_ENVELOPE_FILTERED_FOR: frozenset[str] = frozenset([
    "min_v_x", "max_v_x",
    "min_v_y", "max_v_y",
    "min_m_xD_pos", "max_m_xD_pos",
    "min_m_xD_neg", "max_m_xD_neg",
    "min_m_yD_pos", "max_m_yD_pos",
    "min_m_yD_neg", "max_m_yD_neg",
    "min_n_xD", "max_n_xD",
    "min_n_yD", "max_n_yD",
])

_ENVELOPE_OUTPUT_COLUMNS: list[str] = [
    "zone",
    "direction",
    "limit_state",
    "filtered_for",
    "section_type",
    "x",
    "y",
    "load_case",
    # Basic shear forces
    "v_x",
    "v_y",
    # Elementary design quantities (subset)
    "m_xD_pos",
    "m_xD_neg",
    "m_yD_pos",
    "m_yD_neg",
    "n_xD",
    "n_yD",
]

_ENVELOPE_HEADERS: list[str] = [
    "Zone",
    "Richting",
    "Grenstoestand",
    "Maatgevende grootheid",
    "type",
    "x [m]",
    "y [m]",
    "Belasting",
    # Basic shear forces
    "v_x [kN/m]",
    "v_y [kN/m]",
    # Elementary design quantities (subset)
    "m_xD+ [kN\u00b7m/m]",
    "m_xD- [kN\u00b7m/m]",
    "m_yD+ [kN\u00b7m/m]",
    "m_yD- [kN\u00b7m/m]",
    "n_xD [kN/m]",
    "n_yD [kN/m]",
]

_NUM_ENVELOPE_COLUMNS: int = len(_ENVELOPE_HEADERS)

# Columns that should be converted N → kN (divide by 1000)
_FORCE_COLS: frozenset[str] = frozenset(
    [
        "m_x", "m_y", "m_xy", "v_x", "v_y", "n_x", "n_y", "n_xy",
        "m_xD_pos", "m_xD_neg", "m_yD_pos", "m_yD_neg",
        "m_cD_pos", "m_cD_neg", "n_xD", "n_yD", "n_cD",
    ]
)

# Columns formatted as 3-decimal coordinate values
_COORD_COLS: frozenset[str] = frozenset(["x", "y", "z"])


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _no_data_row(message: str) -> list[list[str]]:
    return [[message] + [""] * (_NUM_COMBINED_COLUMNS - 1)]


def _get_sections_on_plane(results: dict[str, Any]) -> dict[str, Any]:
    """Return cached sections-on-plane data, falling back to re-processing."""
    sections_on_plane = results.get("sections_on_plane")
    if sections_on_plane is None:
        sections_on_plane = process_all_sections_on_plane(results)
    return sections_on_plane


def _format_value(col: str, value: object) -> str:
    """Format a single cell value with appropriate unit conversion."""
    if col == "corrected":
        return "Ja" if value else "Nee"
    if pd.isna(value) if not isinstance(value, str) else not value:
        return ""
    if col in _COORD_COLS:
        try:
            return f"{float(value):.3f}"
        except (ValueError, TypeError):
            return str(value)
    if col in _FORCE_COLS:
        try:
            return f"{float(value) / 1000.0:.3f}"
        except (ValueError, TypeError):
            return str(value)
    return str(value)


def _build_combined_df(df_basic: pd.DataFrame, df_elem: pd.DataFrame) -> pd.DataFrame:  # noqa: C901
    """
    Outer-join basic and elementary DataFrames on section name.

    ``load_case`` is renamed to ``load_case_basis`` / ``load_case_elementair``
    before merging so both can coexist in the joined result.  Geometry columns
    from the elementary side are used to fill gaps when a name has no matching
    basic row.
    """
    if df_basic.empty and df_elem.empty:
        return pd.DataFrame()

    _geometry_cols = ["element", "x", "y", "z", "zone", "direction", "section_type", "section_number"]

    _basic_cols = ["name", *_geometry_cols,
        "load_case", "m_x", "m_y", "m_xy", "v_x", "v_y", "n_x", "n_y", "n_xy",
    ]
    # Include geometry in elementary too so it can fill gaps after the outer join
    _elem_cols = ["name", *_geometry_cols,
        "load_case", "m_xD_pos", "m_xD_neg", "m_yD_pos", "m_yD_neg",
        "m_cD_pos", "m_cD_neg", "n_xD", "n_yD", "n_cD",
    ]

    if not df_basic.empty:
        basic_avail = [c for c in _basic_cols if c in df_basic.columns]
        df_b = df_basic[basic_avail].rename(columns={"load_case": "load_case_basis"})
    else:
        df_b = pd.DataFrame(columns=[c if c != "load_case" else "load_case_basis" for c in _basic_cols])

    if not df_elem.empty:
        elem_avail = [c for c in _elem_cols if c in df_elem.columns]
        df_e = df_elem[elem_avail].rename(
            columns={
                "load_case": "load_case_elementair",
                **{c: f"{c}_e" for c in _geometry_cols if c in df_elem.columns},
            }
        )
    else:
        df_e = pd.DataFrame(
            columns=[
                (f"{c}_e" if c in _geometry_cols else c if c != "load_case" else "load_case_elementair")
                for c in _elem_cols
            ]
        )

    if df_b.empty:
        # Rename *_e geometry back to plain names
        return df_e.rename(columns={f"{c}_e": c for c in _geometry_cols})
    if df_e.empty:
        return df_b

    df = df_b.merge(df_e, on="name", how="outer")

    # Coalesce geometry: prefer basic, fall back to elementary
    for col in _geometry_cols:
        col_e = f"{col}_e"
        if col in df.columns and col_e in df.columns:
            df[col] = df[col].where(df[col].notna(), df[col_e])
            df = df.drop(columns=[col_e])

    # Coalesce the two load_case columns into a single Belasting column
    if "load_case_basis" in df.columns and "load_case_elementair" in df.columns:
        df["load_case"] = df["load_case_basis"].where(df["load_case_basis"].notna(), df["load_case_elementair"])
        df = df.drop(columns=["load_case_basis", "load_case_elementair"])
    elif "load_case_basis" in df.columns:
        df = df.rename(columns={"load_case_basis": "load_case"})
    elif "load_case_elementair" in df.columns:
        df = df.rename(columns={"load_case_elementair": "load_case"})

    return df


def _format_combined_data(df: pd.DataFrame) -> list[list[Any]]:
    """Format the combined DataFrame as rows for a VIKTOR TableResult."""
    if df.empty:
        return _no_data_row("Geen data")

    available = [col for col in _COMBINED_OUTPUT_COLUMNS if col in df.columns]
    if not available:
        return _no_data_row("Data extractie mislukt — controleer SCIA output formaat")

    data: list[list[Any]] = []
    for _, row in df.iterrows():
        data.append([_format_value(col, row.get(col, "")) for col in available])
    return data


# ---------------------------------------------------------------------------
# Core combined-view factory
# ---------------------------------------------------------------------------


def _get_combined_df(
    results: dict[str, Any],
    limit_state: str,
    section_type: str,
    direction: str,
) -> pd.DataFrame:
    """Return the raw merged DataFrame for one limit-state/section-type/direction, tagged with limit_state."""
    tables = _get_sections_on_plane(results).get("tables", {})
    basic_key = f"{limit_state}_basic_{direction}_{section_type}"
    elem_key = f"{limit_state}_elementary_{direction}_{section_type}"
    df = _build_combined_df(
        tables.get(basic_key, pd.DataFrame()),
        tables.get(elem_key, pd.DataFrame()),
    )
    if not df.empty:
        df["limit_state"] = limit_state
    return df


def _create_combined_view(
    results: dict[str, Any],
    limit_state: str,
    section_type: str,
    direction: str,
) -> TableResult:
    """Build a combined basic + elementary TableResult for one direction."""
    df = _get_combined_df(results, limit_state, section_type, direction)
    return TableResult(_format_combined_data(df), column_headers=_COMBINED_HEADERS)


# ---------------------------------------------------------------------------
# Public view functions (8 views — one per limit-state/section-type/direction)
# ---------------------------------------------------------------------------


def create_sections_on_plane_uls_x_reg(results: dict[str, Any]) -> TableResult:
    """ULS veld x-richting: basis + elementaire grootheden."""
    return _create_combined_view(results, "ULS", "reg", "x")


def create_sections_on_plane_uls_y_reg(results: dict[str, Any]) -> TableResult:
    """ULS veld y-richting: basis + elementaire grootheden."""
    return _create_combined_view(results, "ULS", "reg", "y")


def create_sections_on_plane_uls_x_sup(results: dict[str, Any]) -> TableResult:
    """ULS steunpunt x-richting: basis + elementaire grootheden."""
    return _create_combined_view(results, "ULS", "sup", "x")


def create_sections_on_plane_uls_y_sup(results: dict[str, Any]) -> TableResult:
    """ULS steunpunt y-richting: basis + elementaire grootheden."""
    return _create_combined_view(results, "ULS", "sup", "y")


def create_sections_on_plane_slsfreq_x_reg(results: dict[str, Any]) -> TableResult:
    """SLS frequent veld x-richting: basis + elementaire grootheden."""
    return _create_combined_view(results, "SLSfreq", "reg", "x")


def create_sections_on_plane_slsfreq_y_reg(results: dict[str, Any]) -> TableResult:
    """SLS frequent veld y-richting: basis + elementaire grootheden."""
    return _create_combined_view(results, "SLSfreq", "reg", "y")


def create_sections_on_plane_slsfreq_x_sup(results: dict[str, Any]) -> TableResult:
    """SLS frequent steunpunt x-richting: basis + elementaire grootheden."""
    return _create_combined_view(results, "SLSfreq", "sup", "x")


def create_sections_on_plane_slsfreq_y_sup(results: dict[str, Any]) -> TableResult:
    """SLS frequent steunpunt y-richting: basis + elementaire grootheden."""
    return _create_combined_view(results, "SLSfreq", "sup", "y")


def create_sections_on_plane_envelopes(results: dict[str, Any]) -> TableResult:
    """
    Display the min/max force envelope per zone, direction, and limit state.

    Uses the pre-computed envelope from :func:`process_all_sections_on_plane`.
    Each row represents the governing min or max value for one force column at a
    specific zone × direction × limit-state combination.

    Columns: Zone, Richting, Grenstoestand, Maatgevende grootheid, type,
    x, y, Belasting, basic force columns, elementary force columns.
    """
    sections_data = _get_sections_on_plane(results)
    df_env = sections_data.get("envelope", pd.DataFrame())

    no_data_envelope_row = ["Geen data"] + [""] * (_NUM_ENVELOPE_COLUMNS - 1)

    if df_env.empty:
        return TableResult([no_data_envelope_row], column_headers=_ENVELOPE_HEADERS)
    # Limit rows to the governing quantities of interest
    if "filtered_for" in df_env.columns:
        df_env = df_env[df_env["filtered_for"].isin(_ENVELOPE_FILTERED_FOR)]

    if df_env.empty:
        return TableResult([no_data_envelope_row], column_headers=_ENVELOPE_HEADERS)
    available = [col for col in _ENVELOPE_OUTPUT_COLUMNS if col in df_env.columns]
    if not available:
        return TableResult(
            [["Envelope data extractie mislukt"] + [""] * (_NUM_ENVELOPE_COLUMNS - 1)],
            column_headers=_ENVELOPE_HEADERS,
        )

    data: list[list[Any]] = []
    for _, row in df_env.iterrows():
        data.append([_format_value(col, row.get(col, "")) for col in available])
    return TableResult(data, column_headers=_ENVELOPE_HEADERS)
