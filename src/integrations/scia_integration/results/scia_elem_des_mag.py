"""
Functions for calculating elementary design magnitudes in SCIA.

This module implements the formulas for calculating design magnitudes (mxd+, mxd-, myd+, myd-, nxd, nyd)
based on the input moment and force components.
"""


def mxd_plus(mx: float, my: float, mxy: float) -> float:
    """
    Calculate the positive x-direction design moment (mxd+).

    This function calculates the design moment in the positive x-direction based on
    the input moments. The calculation depends on the sign of mx:

    - When mx < 0 (compression): Uses mx - |mxy| to account for torsional effects,
      then clamps the result to non-positive values (≤ 0).
    - When mx >= 0 (tension or zero): Returns 0.0 as positive moments in x-direction
      are not expected in typical bridge deck design cases.

    Args:
        mx: Moment in x-direction (kNm/m)
        my: Moment in y-direction (kNm/m)
        mxy: Torsional moment (kNm/m)

    Returns:
        The positive x-direction design moment (kNm/m), clamped to non-positive values.

    """
    if mx < 0:
        # Negative mx (compression): subtract torsional contribution, clamp to non-positive
        return min(mx - abs(mxy), 0.0)
    if mx > 0:
        # Positive mx (tension): no positive design moment expected
        return 0.0
    # Zero mx: no moment exists
    return 0.0


def mxd_minus(mx: float, my: float, mxy: float) -> float:
    """
    Calculate the negative x-direction design moment (mxd-).

    This function calculates the design moment in the negative x-direction (compression)
    based on the input moments. The calculation depends on the sign of my:

    - When my < 0 (negative moment): Uses the squared formula mx + mxy²/|my| to account
      for reduced torsional contribution when perpendicular moment is negative.
    - When my >= 0 (positive or zero): Uses mx + |mxy| for direct torsional contribution.

    The result is always clamped to non-negative values (≥ 0) as this represents
    compression in the negative x-direction.

    Args:
        mx: Moment in x-direction (kNm/m)
        my: Moment in y-direction (kNm/m)
        mxy: Torsional moment (kNm/m)

    Returns:
        The negative x-direction design moment (kNm/m), clamped to non-negative values.

    """
    if my < 0:
        # Negative my: use squared formula for reduced torsional contribution
        return max(mx + mxy**2 / abs(my), 0.0)
    if my > 0:
        # Positive my: use linear formula for full torsional contribution
        return max(mx + abs(mxy), 0.0)
    # Zero my: use linear formula to avoid division issues
    return max(mx + abs(mxy), 0.0)


def myd_plus(mx: float, my: float, mxy: float) -> float:
    """
    Calculate the positive y-direction design moment (myd+).

    This function calculates the design moment in the positive y-direction based on
    the input moments. The calculation depends on the sign of mx:

    - When mx > 0 (positive moment): Uses the squared formula my - mxy²/|mx| to account
      for reduced torsional contribution when perpendicular moment is positive.
    - When mx < 0 (negative moment): Uses my - |mxy| for direct torsional contribution.
    - When mx = 0: Returns 0.0 as no moment can be calculated without reference.

    The result is always clamped to non-positive values (≤ 0) to ensure only
    compression is captured in this direction.

    Args:
        mx: Moment in x-direction (kNm/m)
        my: Moment in y-direction (kNm/m)
        mxy: Torsional moment (kNm/m)

    Returns:
        The positive y-direction design moment (kNm/m), clamped to non-positive values.

    """
    if mx > 0:
        # Positive mx: use squared formula for reduced torsional contribution
        return min(my - mxy**2 / abs(mx), 0.0)
    if mx < 0:
        # Negative mx: use linear formula for full torsional contribution
        return min(my - abs(mxy), 0.0)
    # Zero mx: no reference moment exists
    return 0.0


def myd_minus(mx: float, my: float, mxy: float) -> float:
    """
    Calculate the negative y-direction design moment (myd-).

    This function calculates the design moment in the negative y-direction (compression)
    based on the input moments. Unlike other functions, this calculation is independent
    of the perpendicular moment direction and always uses a direct linear contribution:

    - Uses my + |mxy| to add the absolute torsional contribution to the y-moment.
    - The result is clamped to non-negative values (≥ 0) as this represents compression.

    Args:
        mx: Moment in x-direction (kNm/m)
        my: Moment in y-direction (kNm/m)
        mxy: Torsional moment (kNm/m)

    Returns:
        The negative y-direction design moment (kNm/m), clamped to non-negative values.

    """
    if mx < 0:
        # Negative mx: use linear formula (independent of mx sign)
        return max(my + abs(mxy), 0.0)
    if mx > 0:
        # Positive mx: use linear formula (independent of mx sign)
        return max(my + abs(mxy), 0.0)
    # Zero mx: use linear formula (independent of mx sign)
    return max(my + abs(mxy), 0.0)


def nxd(nx: float, ny: float, nxy: float) -> float:
    """
    Calculate the x-direction design force (nxd).

    This function calculates the design force in the x-direction based on the input
    forces. The calculation depends on the sign of ny:

    - When ny < 0 (compression): Uses the squared formula nx + nxy²/|ny| to account
      for reduced shear force contribution when perpendicular force is compressive.
    - When ny >= 0 (tension or zero): Uses nx + |nxy| for direct shear contribution.

    The result is always clamped to non-negative values (≥ 0) as this represents
    tension in the x-direction.

    Args:
        nx: Force in x-direction (kN/m)
        ny: Force in y-direction (kN/m)
        nxy: Shear force (kN/m)

    Returns:
        The x-direction design force (kN/m), clamped to non-negative values.

    """
    if ny < 0:
        # Negative ny: use squared formula for reduced shear contribution
        return max(nx + nxy**2 / abs(ny), 0.0)
    if ny > 0:
        # Positive ny: use linear formula for full shear contribution
        return max(nx + abs(nxy), 0.0)
    # Zero ny: use linear formula to avoid division issues
    return max(nx + abs(nxy), 0.0)


def nyd(nx: float, ny: float, nxy: float) -> float:
    """
    Calculate the y-direction design force (nyd).

    This function calculates the design force in the y-direction based on the input
    forces. The calculation depends on the sign of nx:

    - When nx > 0 (tension): Uses ny + |nxy| for direct shear contribution, no clamping.
    - When nx < 0 (compression): Uses the squared formula ny + nxy²/|nx| for reduced
      shear contribution, clamped to non-positive values (≤ 0).
    - When nx = 0: Uses ny directly without shear contribution, clamped to non-positive values.

    Args:
        nx: Force in x-direction (kN/m)
        ny: Force in y-direction (kN/m)
        nxy: Shear force (kN/m)

    Returns:
        The y-direction design force (kN/m). Clamping depends on nx sign.

    """
    if nx > 0:
        # Positive nx: use linear formula, no clamping
        return ny + abs(nxy)
    if nx < 0:
        # Negative nx: use squared formula for reduced shear contribution
        return min(ny + nxy**2 / abs(nx), 0.0)
    # Zero nx: use ny directly without shear contribution
    return min(ny, 0.0)
