"""
Functions for calculating elementary design magnitudes in SCIA.

This module implements the formulas for calculating design magnitudes (mxd+, mxd-, myd+, myd-, nxd, nyd)
based on the input moment and force components.
"""


def mxd_plus(mx: float, my: float, mxy: float) -> float:
    """
    Calculate the positive x-direction design moment (mxd+).

    Calculate the design moment in the positive x-direction based on the input moments.
    The calculation depends on the sign of my:

    - When my > 0 (positive moment): Uses the squared formula mx - mxy²/|my| to account
      for reduced torsional contribution when perpendicular moment is positive.
    - When my < 0 (negative moment): Uses mx - |mxy| for direct torsional contribution.
    - When my = 0: Returns 0.0 as no moment can be calculated without reference.

    The result is clamped to non-positive values (≤ 0) to ensure only compression
    is captured in this direction.

    Args:
        mx: Moment in x-direction (kNm/m)
        my: Moment in y-direction (kNm/m)
        mxy: Torsional moment (kNm/m)

    Returns:
        The positive x-direction design moment (kNm/m), clamped to non-positive values.

    """
    if my > 0:
        # Positive my: Use squared formula for reduced torsional contribution
        return min(mx - mxy**2 / abs(my), 0.0)
    if my < 0:
        # Negative my: Use linear formula for full torsional contribution
        return min(mx - abs(mxy), 0.0)
    # Zero my: No reference moment exists
    return 0.0


def mxd_minus(mx: float, my: float, mxy: float) -> float:
    """
    Calculate the negative x-direction design moment (mxd-).

    Calculate the design moment in the negative x-direction (compression) based on
    the input moments. The calculation depends on the sign of my:

    - When my < 0 (negative moment): Uses the squared formula mx + mxy²/|my| to account
      for reduced torsional contribution when perpendicular moment is negative.
    - When my >= 0 (positive or zero): Uses mx + |mxy| for direct torsional contribution.

    The result is clamped to non-negative values (≥ 0) as this represents compression
    in the negative x-direction.

    Args:
        mx: Moment in x-direction (kNm/m)
        my: Moment in y-direction (kNm/m)
        mxy: Torsional moment (kNm/m)

    Returns:
        The negative x-direction design moment (kNm/m), clamped to non-negative values.

    """
    if my < 0:
        # Negative my: Use squared formula for reduced torsional contribution
        return max(mx + mxy**2 / abs(my), 0.0)
    if my > 0:
        # Positive my: Use linear formula for full torsional contribution
        return max(mx + abs(mxy), 0.0)
    # Zero my: Use linear formula to avoid division issues
    return max(mx + abs(mxy), 0.0)


def myd_plus(mx: float, my: float, mxy: float) -> float:
    """
    Calculate the positive y-direction design moment (myd+).

    Calculate the design moment in the positive y-direction based on the input moments.
    The calculation depends on the sign of mx:

    - When mx > 0 (positive moment): Uses the squared formula my - mxy²/|mx| to account
      for reduced torsional contribution when perpendicular moment is positive.
    - When mx < 0 (negative moment): Uses my - |mxy| for direct torsional contribution.
    - When mx = 0: Returns 0.0 as no moment can be calculated without reference.

    The result is clamped to non-positive values (≤ 0) to ensure only compression
    is captured in this direction.

    Args:
        mx: Moment in x-direction (kNm/m)
        my: Moment in y-direction (kNm/m)
        mxy: Torsional moment (kNm/m)

    Returns:
        The positive y-direction design moment (kNm/m), clamped to non-positive values.

    """
    if mx > 0:
        # Positive mx: Use squared formula for reduced torsional contribution
        return min(my - mxy**2 / abs(mx), 0.0)
    if mx < 0:
        # Negative mx: Use linear formula for full torsional contribution
        return min(my - abs(mxy), 0.0)
    # Zero mx: No reference moment exists
    return 0.0


def myd_minus(mx: float, my: float, mxy: float) -> float:
    """
    Calculate the negative y-direction design moment (myd-).

    Calculate the design moment in the negative y-direction (compression) based on
    the input moments. The calculation is independent of the sign of mx:

    - When mx < 0 (negative moment): Uses my + |mxy| for direct torsional contribution.
    - When mx > 0 (positive moment): Uses my + |mxy| for direct torsional contribution.
    - When mx = 0: Uses my + |mxy| for direct torsional contribution.

    The result is clamped to non-negative values (≥ 0) as this represents compression
    in the negative y-direction.

    Args:
        mx: Moment in x-direction (kNm/m)
        my: Moment in y-direction (kNm/m)
        mxy: Torsional moment (kNm/m)

    Returns:
        The negative y-direction design moment (kNm/m), clamped to non-negative values.

    """
    if mx < 0:
        # Negative mx: Use linear formula for full torsional contribution
        return max(my + abs(mxy), 0.0)
    if mx > 0:
        # Positive mx: Use linear formula for full torsional contribution
        return max(my + abs(mxy), 0.0)
    # Zero mx: Use linear formula for full torsional contribution
    return max(my + abs(mxy), 0.0)


def nxd(nx: float, ny: float, nxy: float) -> float:
    """
    Calculate the x-direction design force (nxd).

    Calculate the design force in the x-direction based on the input forces.
    The calculation depends on the sign of ny:

    - When ny < 0 (negative force): Uses the squared formula nx + nxy²/|ny| to account
      for reduced shear force contribution when perpendicular force is negative.
    - When ny > 0 (positive force): Uses nx + |nxy| for direct shear contribution.
    - When ny = 0: Uses nx + |nxy| for direct shear contribution.

    The result is clamped to non-negative values (≥ 0) as this represents tension
    in the x-direction.

    Args:
        nx: Force in x-direction (kN/m)
        ny: Force in y-direction (kN/m)
        nxy: Shear force (kN/m)

    Returns:
        The x-direction design force (kN/m), clamped to non-negative values.

    """
    if ny < 0:
        # Negative ny: Use squared formula for reduced shear contribution
        return max(nx + nxy**2 / abs(ny), 0.0)
    if ny > 0:
        # Positive ny: Use linear formula for full shear contribution
        return max(nx + abs(nxy), 0.0)
    # Zero ny: Use linear formula for full shear contribution
    return max(nx + abs(nxy), 0.0)


def nyd(nx: float, ny: float, nxy: float) -> float:
    """
    Calculate the y-direction design force (nyd).

    Calculate the design force in the y-direction based on the input forces.
    The calculation depends on the sign of nx:

    - When nx > 0 (positive force): Uses ny + |nxy| for direct shear contribution.
    - When nx < 0 (negative force): Uses the squared formula ny + nxy²/|nx| for reduced
      shear contribution.
    - When nx = 0: Uses ny directly without shear contribution.

    The result clamping depends on nx sign: no clamping when nx > 0, clamped to
    non-positive values (≤ 0) when nx ≤ 0.

    Args:
        nx: Force in x-direction (kN/m)
        ny: Force in y-direction (kN/m)
        nxy: Shear force (kN/m)

    Returns:
        The y-direction design force (kN/m). Clamping depends on nx sign.

    """
    if nx > 0:
        # Positive nx: Use linear formula for full shear contribution
        return ny + abs(nxy)
    if nx < 0:
        # Negative nx: Use squared formula for reduced shear contribution
        return min(ny + nxy**2 / abs(nx), 0.0)
    # Zero nx: No shear contribution applied
    return min(ny, 0.0)
