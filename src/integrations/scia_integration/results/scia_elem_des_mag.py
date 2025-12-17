"""
Functions for calculating elementary design magnitudes in SCIA.

This module implements the formulas for calculating design magnitudes (mxd+, mxd-, myd+, myd-, nxd, nyd)
based on the input moment and force components.
"""


def mxd_plus(mx: float, my: float, mxy: float) -> float:
    """
    Calculate the positive x-direction design moment (mxd+).

    Bottom layer (tension) design moment in x-direction.
    Based on EC2 Table G.2: Required capacity mRdx.

    Args:
        mx: Moment in x-direction (kNm/m) - corresponds to mEdx
        my: Moment in y-direction (kNm/m) - corresponds to mEdy
        mxy: Torsional moment (kNm/m) - corresponds to mEdxy

    Returns:
        mxd+: Design moment for bottom reinforcement in x-direction (kNm/m) - corresponds to mRdx

    """
    # Row 1: mEdx >= -|mEdxy|, mEdy >= -|mEdxy|
    if mx >= -abs(mxy) and my >= -abs(mxy):
        return mx + abs(mxy)
    
    # Row 2: mEdx <= mEdy, mEdx < -|mEdxy|, mEdx*mEdy >= m²Edxy
    if mx <= my and mx < -abs(mxy) and mx * my >= mxy**2:
        return 0.0
    
    # Row 3: mEdx >= mEdy, mEdy < -|mEdxy|, mEdx*mEdy <= m²Edxy
    if mx >= my and my < -abs(mxy) and mx * my <= mxy**2:
        return mx + mxy**2 / abs(my)
    
    # Row 4: mEdx < 0, mEdy < 0, mEdx*mEdy > m²Edxy
    if mx < 0 and my < 0 and mx * my > mxy**2:
        return 0.0
    
    # Default fallback
    return 0.0


def mxd_minus(mx: float, my: float, mxy: float) -> float:
    """
    Calculate the negative x-direction design moment (mxd-).

    Top layer (compression/tension) design moment in x-direction.
    Based on EC2 Table G.3: Required capacity m'Rdx.

    Args:
        mx: Moment in x-direction (kNm/m) - corresponds to mEdx
        my: Moment in y-direction (kNm/m) - corresponds to mEdy
        mxy: Torsional moment (kNm/m) - corresponds to mEdxy

    Returns:
        mxd-: Design moment for top reinforcement in x-direction (kNm/m) - corresponds to m'Rdx

    """
    # Row 1: mEdx <= |mEdxy|, mEdy <= |mEdxy|
    if mx <= abs(mxy) and my <= abs(mxy):
        return -mx + abs(mxy)
    
    # Row 2: mEdx >= mEdy, mEdx > |mEdxy|, mEdx*mEdy <= m²Edxy
    if mx >= my and mx > abs(mxy) and mx * my <= mxy**2:
        return 0.0
    
    # Row 3: mEdx <= mEdy, mEdy > |mEdxy|, mEdx*mEdy <= m²Edxy
    if mx <= my and my > abs(mxy) and mx * my <= mxy**2:
        return -mx + mxy**2 / abs(my)
    
    # Row 4: mEdx > 0, mEdy > 0, mEdx*mEdy > m²Edxy
    if mx > 0 and my > 0 and mx * my > mxy**2:
        return 0.0
    
    # Default fallback
    return 0.0


def myd_plus(mx: float, my: float, mxy: float) -> float:
    """
    Calculate the positive y-direction design moment (myd+).

    Bottom layer (tension) design moment in y-direction.
    Based on EC2 Table G.2: Required capacity mRdy.

    Args:
        mx: Moment in x-direction (kNm/m) - corresponds to mEdx
        my: Moment in y-direction (kNm/m) - corresponds to mEdy
        mxy: Torsional moment (kNm/m) - corresponds to mEdxy

    Returns:
        myd+: Design moment for bottom reinforcement in y-direction (kNm/m) - corresponds to mRdy

    """
    # Row 1: mEdx >= -|mEdxy|, mEdy >= -|mEdxy|
    if mx >= -abs(mxy) and my >= -abs(mxy):
        return my + abs(mxy)
    
    # Row 2: mEdx <= mEdy, mEdx < -|mEdxy|, mEdx*mEdy >= m²Edxy
    if mx <= my and mx < -abs(mxy) and mx * my >= mxy**2:
        return my + mxy**2 / abs(mx)
    
    # Row 3: mEdx >= mEdy, mEdy < -|mEdxy|, mEdx*mEdy <= m²Edxy
    if mx >= my and my < -abs(mxy) and mx * my <= mxy**2:
        return 0.0
    
    # Row 4: mEdx < 0, mEdy < 0, mEdx*mEdy > m²Edxy
    if mx < 0 and my < 0 and mx * my > mxy**2:
        return 0.0
    
    # Default fallback
    return 0.0


def myd_minus(mx: float, my: float, mxy: float) -> float:
    """
    Calculate the negative y-direction design moment (myd-).

    Top layer (compression/tension) design moment in y-direction.
    Based on EC2 Table G.3: Required capacity m'Rdy.

    Args:
        mx: Moment in x-direction (kNm/m) - corresponds to mEdx
        my: Moment in y-direction (kNm/m) - corresponds to mEdy
        mxy: Torsional moment (kNm/m) - corresponds to mEdxy

    Returns:
        myd-: Design moment for top reinforcement in y-direction (kNm/m) - corresponds to m'Rdy

    """
    # Row 1: mEdx <= |mEdxy|, mEdy <= |mEdxy|
    if mx <= abs(mxy) and my <= abs(mxy):
        return -my + abs(mxy)
    
    # Row 2: mEdx >= mEdy, mEdx > |mEdxy|, mEdx*mEdy <= m²Edxy
    if mx >= my and mx > abs(mxy) and mx * my <= mxy**2:
        return -my + mxy**2 / abs(mx)
    
    # Row 3: mEdx <= mEdy, mEdy > |mEdxy|, mEdx*mEdy <= m²Edxy
    if mx <= my and my > abs(mxy) and mx * my <= mxy**2:
        return 0.0
    
    # Row 4: mEdx > 0, mEdy > 0, mEdx*mEdy > m²Edxy
    if mx > 0 and my > 0 and mx * my > mxy**2:
        return 0.0
    
    # Default fallback
    return 0.0


def nxd(nx: float, ny: float, nxy: float) -> float:
    """
    Calculate the x-direction design force (nxd).

    Calculate the design force in the x-direction based on the input forces.
    According to EC2 flowchart for wall design:

    - When ny >= 0: Uses nx + |nxy|
    - When ny < 0: Uses nx + nxy²/|ny|

    The result is clamped to non-negative values (≥ 0) as this represents tension.

    Args:
        nx: Force in x-direction (kN/m)
        ny: Force in y-direction (kN/m)
        nxy: Shear force (kN/m)

    Returns:
        The x-direction design force (kN/m), clamped to non-negative values.

    """
    if ny >= 0:
        # Positive or zero ny: Use linear formula
        return max(nx + abs(nxy), 0.0)
    # Negative ny: Use squared formula
    return max(nx + nxy**2 / abs(ny), 0.0)


def nyd(nx: float, ny: float, nxy: float) -> float:
    """
    Calculate the y-direction design force (nyd).

    Calculate the design force in the y-direction based on the input forces.
    According to EC2 flowchart for wall design:

    - When nx > 0: Uses ny + |nxy| (no clamping)
    - When nx < 0: Uses ny + nxy²/|nx| (clamped to non-positive)
    - When nx = 0: Uses ny (clamped to non-positive)

    Args:
        nx: Force in x-direction (kN/m)
        ny: Force in y-direction (kN/m)
        nxy: Shear force (kN/m)

    Returns:
        The y-direction design force (kN/m). No clamping when nx > 0,
        clamped to non-positive (≤ 0) when nx ≤ 0.

    """
    if nx > 0:
        # Positive nx: Use linear formula, no clamping
        return ny + abs(nxy)
    if nx < 0:
        # Negative nx: Use squared formula, clamp to non-positive
        return min(ny + nxy**2 / abs(nx), 0.0)
    # Zero nx: No shear contribution, clamp to non-positive
    return min(ny, 0.0)
