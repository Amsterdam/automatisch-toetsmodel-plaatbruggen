"""
Sections-on-Plane to IDEA StatiCa Adapter Functions.

Converts sections-on-plane envelope results into the N / Qz / My format
expected by the IDEA RCS integration.

Force mapping for 2D shell forces (per unit width [kN/m, kNm/m]):

X-direction sections  →  dwars (transverse) cross-section in IDEA:
    N   = n_x   (membrane normal force in x-direction)
    Qz  = v_x   (shear force in x-direction)
    My  = m_x   (bending moment about x-axis)

Y-direction sections  →  langs (longitudinal) cross-section in IDEA:
    N   = n_y   (membrane normal force in y-direction)
    Qz  = v_y   (shear force in y-direction)
    My  = m_y   (bending moment about y-axis)

The approach mirrors ``scia_integration_strips_to_idea.py`` so that
``_apply_sections_on_plane_loads_to_slabs`` (in idea_interface.py) can
consume the resulting DataFrame with the same (zone, direction, filtered_for,
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
    - ``filtered_for`` – governing component (e.g. ``"min_m_x"``, ``"max_v_y"``)
    - ``name``         – section name from SCIA
    - ``load_case``    – governing load case
    - ``m_x``, ``m_y``, ``v_x``, ``v_y``, ``n_x``, ``n_y``, ...

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
    Map sections-on-plane 2D shell forces to IDEA's N / Qz / My format.

    For **X-direction** sections (transverse / *dwars* in IDEA)::

        N   = n_x
        Qz  = v_x
        My  = m_x

    For **Y-direction** sections (longitudinal / *langs* in IDEA)::

        N   = n_y
        Qz  = v_y
        My  = m_y

    Also normalises zone names: ``"Z1-1"`` → ``"1-1"`` to match the
    bridge-segment zone naming convention used by the IDEA slab logic.

    Missing or NaN source columns are silently treated as 0.

    :param df_sections: Sections-on-plane envelope DataFrame
    :type df_sections: pd.DataFrame
    :returns: DataFrame with ``N``, ``Qz``, ``My`` columns added
    :rtype: pd.DataFrame
    """
    if df_sections.empty:
        return pd.DataFrame()

    result_df = df_sections.copy()

    # Normalise zone names: "Z1-1" → "1-1"
    if "zone" in result_df.columns:
        result_df["zone"] = result_df["zone"].str.replace("Z", "", regex=False)

    # Initialise IDEA force columns to zero
    result_df["N"] = 0.0
    result_df["Qz"] = 0.0
    result_df["My"] = 0.0

    x_mask = result_df["direction"] == "x"
    y_mask = result_df["direction"] == "y"

    # X-direction sections → dwars slab: Qz = v_x, My = m_x, N = n_x
    if x_mask.any():
        if "v_x" in result_df.columns:
            result_df.loc[x_mask, "Qz"] = result_df.loc[x_mask, "v_x"].fillna(0.0)
        if "m_x" in result_df.columns:
            result_df.loc[x_mask, "My"] = result_df.loc[x_mask, "m_x"].fillna(0.0)
        if "n_x" in result_df.columns:
            result_df.loc[x_mask, "N"] = result_df.loc[x_mask, "n_x"].fillna(0.0)

    # Y-direction sections → langs slab: Qz = v_y, My = m_y, N = n_y
    if y_mask.any():
        if "v_y" in result_df.columns:
            result_df.loc[y_mask, "Qz"] = result_df.loc[y_mask, "v_y"].fillna(0.0)
        if "m_y" in result_df.columns:
            result_df.loc[y_mask, "My"] = result_df.loc[y_mask, "m_y"].fillna(0.0)
        if "n_y" in result_df.columns:
            result_df.loc[y_mask, "N"] = result_df.loc[y_mask, "n_y"].fillna(0.0)

    return result_df
