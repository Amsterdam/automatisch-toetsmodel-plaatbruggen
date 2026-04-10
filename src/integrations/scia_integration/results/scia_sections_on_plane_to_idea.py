"""
Sections-on-Plane to IDEA StatiCa Adapter Functions.

Converts sections-on-plane envelope results into the N / Qz / My format
expected by the IDEA RCS integration.

Force mapping using elementary design quantities (per unit width [kN/m, kNm/m]):

X-direction sections  →  dwars (transverse) cross-section in IDEA:
    N   = n_xD          (elementary design normal force in x-direction)
    Qz  = v_x           (shear force in x-direction)
    My  = m_xD+  if filtered_for contains ``m_xD_pos``
    My  = m_xD-  if filtered_for contains ``m_xD_neg``
    Rows governed by m_yD cases (max/min_m_yD_pos/neg) are **skipped**.

Y-direction sections  →  langs (longitudinal) cross-section in IDEA:
    N   = n_yD          (elementary design normal force in y-direction)
    Qz  = v_y           (shear force in y-direction)
    My  = m_yD+  if filtered_for contains ``m_yD_pos``
    My  = m_yD-  if filtered_for contains ``m_yD_neg``
    Rows governed by m_xD cases (max/min_m_xD_pos/neg) are **skipped**.

``_apply_sections_on_plane_loads_to_slabs`` (in idea_interface.py) consumes
the resulting DataFrame with the same (zone, direction, filtered_for,
limit_state, N, Qz, My) structure.
"""

from typing import Any

import pandas as pd


def process_sections_on_plane_for_idea(
    results: dict[str, Any],
) -> pd.DataFrame:
    """
    Process sections-on-plane envelope results for IDEA StatiCa integration.

    Reads ``results["sections_on_plane"]["envelope"]`` and maps 2D shell
    force/moment components to the ``N``, ``Qz``, ``My`` columns that
    ``_apply_sections_on_plane_loads_to_slabs`` expects.

    Input envelope DataFrame columns (from
    :func:`~scia_sections_on_plane_processor.process_sections_on_plane_envelopes`):

    - ``zone``         – zone identifier (e.g. ``"Z1-1"``)
    - ``direction``    – ``"x"`` or ``"y"``
    - ``limit_state``  – ``"ULS"`` or ``"SLSfreq"``
    - ``filtered_for`` – governing component (e.g. ``"min_m_xD_neg"``, ``"max_v_y"``)
    - ``name``         – section name from SCIA
    - ``load_case``    – governing load case
    - ``v_x``, ``v_y``        – basic shear forces
    - ``n_xD``, ``n_yD``      – elementary design normal forces
    - ``m_xD_pos``, ``m_xD_neg``, ``m_yD_pos``, ``m_yD_neg`` – elementary design moments

    Returned DataFrame adds:

    - ``N``  – normal force  [kN/m × 1 m slab width]
    - ``Qz`` – shear force   [kN/m × 1 m slab width]
    - ``My`` – bending moment [kNm/m × 1 m slab width]

    :param results: SCIA analysis results dictionary containing
                    ``"sections_on_plane"`` data
    :type results: dict[str, Any]
    :returns: DataFrame formatted for
              ``_apply_sections_on_plane_loads_to_slabs``
    :rtype: pd.DataFrame
    :raises ValueError: If ``sections_on_plane`` data is missing or required
                        columns are absent
    """
    sections_on_plane = results.get("sections_on_plane")

    if sections_on_plane is None:
        msg = "Sections-on-plane data not found in results. Ensure SCIA analysis has been run with sections-on-plane result objects."
        raise ValueError(msg)

    df_envelope = sections_on_plane.get("envelope", pd.DataFrame())

    if df_envelope.empty:
        return pd.DataFrame()

    required_columns = ["zone", "direction", "limit_state", "filtered_for"]
    missing_columns = [col for col in required_columns if col not in df_envelope.columns]

    if missing_columns:
        msg = f"Missing required columns for IDEA integration: {missing_columns}"
        raise ValueError(msg)

    return _map_section_forces_to_idea_format(df_envelope)


def _map_section_forces_to_idea_format(  # noqa: C901
    df_sections: pd.DataFrame,
) -> pd.DataFrame:
    """
    Map sections-on-plane elementary design forces to IDEA's N / Qz / My format.

    Rows governed by cross-direction m_D cases are dropped before mapping:

    - X-direction rows where ``filtered_for`` contains ``m_yD`` are skipped.
    - Y-direction rows where ``filtered_for`` contains ``m_xD`` are skipped.

    For **X-direction** sections (transverse / *dwars* in IDEA)::

        N   = n_xD          (elementary design normal force)
        Qz  = v_x
        My  = value with largest absolute value among m_xD_neg and m_xD_pos
              (sign preserved — e.g. m_xD_neg=-100, m_xD_pos=50 → My=-100)

    For **Y-direction** sections (longitudinal / *langs* in IDEA)::

        N   = n_yD          (elementary design normal force)
        Qz  = v_y
        My  = value with largest absolute value among m_yD_neg and m_yD_pos
              (sign preserved — e.g. m_yD_neg=-100, m_yD_pos=50 → My=-100)

    Also normalises zone names: ``"Z1-1"`` → ``"1-1"`` to match the
    bridge-segment zone naming convention used by the IDEA slab logic.

    Missing or NaN source columns are silently treated as 0.

    :param df_sections: Sections-on-plane envelope DataFrame
    :type df_sections: pd.DataFrame
    :returns: DataFrame with ``N``, ``Qz``, ``My`` columns added (cross-direction
              m_D rows removed)
    :rtype: pd.DataFrame
    """
    if df_sections.empty:
        return pd.DataFrame()

    result_df = df_sections.copy()

    # Normalise zone names: "Z1-1" → "1-1"
    if "zone" in result_df.columns:
        result_df["zone"] = result_df["zone"].str.replace("Z", "", regex=False)

    # Drop rows where the governing quantity belongs to the cross-direction m_D family.
    # X-direction sections use m_xD for My; Y-direction sections use m_yD for My.
    if "filtered_for" in result_df.columns:
        skip_mask = ((result_df["direction"] == "x") & result_df["filtered_for"].str.contains("m_yD", na=False)) | (
            (result_df["direction"] == "y") & result_df["filtered_for"].str.contains("m_xD", na=False)
        )
        result_df = result_df[~skip_mask].copy()

    if result_df.empty:
        return pd.DataFrame()

    # Initialise IDEA force columns to zero
    result_df["N"] = 0.0
    result_df["Qz"] = 0.0
    result_df["My"] = 0.0

    x_mask = result_df["direction"] == "x"
    y_mask = result_df["direction"] == "y"

    # X-direction sections → dwars slab: N = n_xD, Qz = v_x, My = max(|m_xD_neg|, |m_xD_pos|) with sign
    if x_mask.any():
        if "n_xD" in result_df.columns:
            result_df.loc[x_mask, "N"] = result_df.loc[x_mask, "n_xD"].fillna(0.0)
        if "v_x" in result_df.columns:
            result_df.loc[x_mask, "Qz"] = result_df.loc[x_mask, "v_x"].fillna(0.0)
        # My: pick the value with the largest absolute value between m_xD_neg and m_xD_pos (keep sign)
        x_neg = result_df.loc[x_mask, "m_xD_neg"].fillna(0.0) if "m_xD_neg" in result_df.columns else pd.Series(0.0, index=result_df.index[x_mask])
        x_pos = result_df.loc[x_mask, "m_xD_pos"].fillna(0.0) if "m_xD_pos" in result_df.columns else pd.Series(0.0, index=result_df.index[x_mask])
        result_df.loc[x_mask, "My"] = x_neg.where(x_neg.abs() >= x_pos.abs(), x_pos)

    # Y-direction sections → langs slab: N = n_yD, Qz = v_y, My = max(|m_yD_neg|, |m_yD_pos|) with sign
    if y_mask.any():
        if "n_yD" in result_df.columns:
            result_df.loc[y_mask, "N"] = result_df.loc[y_mask, "n_yD"].fillna(0.0)
        if "v_y" in result_df.columns:
            result_df.loc[y_mask, "Qz"] = result_df.loc[y_mask, "v_y"].fillna(0.0)
        # My: pick the value with the largest absolute value between m_yD_neg and m_yD_pos (keep sign)
        y_neg = result_df.loc[y_mask, "m_yD_neg"].fillna(0.0) if "m_yD_neg" in result_df.columns else pd.Series(0.0, index=result_df.index[y_mask])
        y_pos = result_df.loc[y_mask, "m_yD_pos"].fillna(0.0) if "m_yD_pos" in result_df.columns else pd.Series(0.0, index=result_df.index[y_mask])
        result_df.loc[y_mask, "My"] = y_neg.where(y_neg.abs() >= y_pos.abs(), y_pos)

    return result_df
