"""
Functions for calculating elementary design magnitudes in SCIA.

This module implements the formulas for calculating design magnitudes (mxd+, mxd-, myd+, myd-, nxd, nyd)
based on the input moment and force components.

Formulas according to ČSN P ENV 1992–1–1 (731201), Appendix 2:
- Bending moments: par. A2.8
- Normal forces: par. A2.9
"""


def mxd_plus(mx: float, my: float, mxy: float) -> float:
    """
    Calculate the positive x-direction design moment (mxd+).

    Bottom layer (tension) design moment in x-direction.
    Based on ČSN P ENV 1992–1–1 (731201), Appendix 2, par. A2.8.

    Args:
        mx: Moment in x-direction (kNm/m)
        my: Moment in y-direction (kNm/m)
        mxy: Torsional moment (kNm/m)

    Returns:
        mxd+: Design moment for bottom reinforcement in x-direction (kNm/m)

    """
    # Flowchart for m+:
    # if my >= mx and my <= |mxy|: return -mx + |mxy|
    # elif my < mx and mx <= |mxy|: return -mx + |mxy|
    # else: use alternative formula
    if my >= mx and my <= abs(mxy):
        return -mx + abs(mxy)
    elif my < mx and mx <= abs(mxy):
        return -mx + abs(mxy)
    elif my >= mx and my > abs(mxy):
        # my > |mxy|, so use formula with non-dominant axis
        return -mx + mxy**2 / abs(my)
    elif my < mx and mx > abs(mxy):
        # mx > |mxy|, so use formula with non-dominant axis
        return 0.0
    else:
        raise ValueError("Unexpected condition in mxd_plus")


def mxd_minus(mx: float, my: float, mxy: float) -> float:
    """
    Calculate the negative x-direction design moment (mxd-).

    Top layer (compression/tension) design moment in x-direction.
    Based on ČSN P ENV 1992–1–1 (731201), Appendix 2, par. A2.8.

    Args:
        mx: Moment in x-direction (kNm/m)
        my: Moment in y-direction (kNm/m)
        mxy: Torsional moment (kNm/m)

    Returns:
        mxd-: Design moment for top reinforcement in x-direction (kNm/m)

    """
    # Flowchart for m-:
    # if my >= mx and mx >= -|mxy|: return mx + |mxy|
    # elif my < mx and my >= -|mxy|: return mx + |mxy|
    # else: use alternative formula
    if my >= mx and mx >= -abs(mxy):
        return mx + abs(mxy)
    elif my < mx and my >= -abs(mxy):
        return mx + abs(mxy)
    elif my >= mx and mx < -abs(mxy):
        # mx < -|mxy|, so x is too small (too negative)
        return 0.0
    elif my < mx and my < -abs(mxy):
        # my < -|mxy|, so y is too small (too negative)
        return mx + mxy**2 / abs(my)
    else:
        raise ValueError("Unexpected condition in mxd_minus")


def myd_plus(mx: float, my: float, mxy: float) -> float:
    """
    Calculate the positive y-direction design moment (myd+).

    Bottom layer (tension) design moment in y-direction.
    Based on ČSN P ENV 1992–1–1 (731201), Appendix 2, par. A2.8.

    Args:
        mx: Moment in x-direction (kNm/m)
        my: Moment in y-direction (kNm/m)
        mxy: Torsional moment (kNm/m)

    Returns:
        myd+: Design moment for bottom reinforcement in y-direction (kNm/m)

    """
    # Flowchart for m+:
    # if my >= mx and my <= |mxy|: return -my + |mxy|
    # elif my < mx and mx <= |mxy|: return -my + |mxy|
    # else: use alternative formula
    if my >= mx and my <= abs(mxy):
        return -my + abs(mxy)
    elif my < mx and mx <= abs(mxy):
        return -my + abs(mxy)
    elif my >= mx and my > abs(mxy):
        # my > |mxy|, so use formula with non-dominant axis
        return 0.0
    elif my < mx and mx > abs(mxy):
        # mx > |mxy|, so use formula with non-dominant axis
        return -my + mxy**2 / abs(mx)
    else:
        raise ValueError("Unexpected condition in myd_plus")


def myd_minus(mx: float, my: float, mxy: float) -> float:
    """
    Calculate the negative y-direction design moment (myd-).

    Top layer (compression/tension) design moment in y-direction.
    Based on ČSN P ENV 1992–1–1 (731201), Appendix 2, par. A2.8.

    Args:
        mx: Moment in x-direction (kNm/m)
        my: Moment in y-direction (kNm/m)
        mxy: Torsional moment (kNm/m)

    Returns:
        myd-: Design moment for top reinforcement in y-direction (kNm/m)

    """
    # Flowchart for m-:
    # if my >= mx and mx >= -|mxy|: return my + |mxy|
    # elif my < mx and my >= -|mxy|: return my + |mxy|
    # else: use alternative formula
    if my >= mx and mx >= -abs(mxy):
        return my + abs(mxy)
    elif my < mx and my >= -abs(mxy):
        return my + abs(mxy)
    elif my >= mx and mx < -abs(mxy):
        # mx < -|mxy|, so x is too small (too negative)
        return my + mxy**2 / abs(mx)
    elif my < mx and my < -abs(mxy):
        # my < -|mxy|, so y is too small (too negative)
        return 0.0
    else:
        raise ValueError("Unexpected condition in myd_minus")


def nxd(nx: float, ny: float, nxy: float) -> float:
    """
    Calculate the x-direction design force (nxd).

    Calculate the design force in the x-direction based on the input forces.
    Based on ČSN P ENV 1992–1–1 (731201), Appendix 2, par. A2.9.

    Args:
        nx: Force in x-direction (kN/m)
        ny: Force in y-direction (kN/m)
        nxy: Shear force (kN/m)

    Returns:
        The x-direction design force (kN/m).

    """
    # Flowchart for normal forces:
    # if ny >= nx and nx >= -|nxy|: return nx + |nxy|
    # elif ny < nx and ny >= -|nxy|: return nx + |nxy|
    # else: use alternative formula
    if ny >= nx and nx >= -abs(nxy):
        return nx + abs(nxy)
    elif ny < nx and ny >= -abs(nxy):
        return nx + abs(nxy)
    elif ny >= nx and nx < -abs(nxy):
        # nx < -|nxy|, so x is too small (too negative)
        return 0.0
    elif ny < nx and ny < -abs(nxy):
        # ny < -|nxy|, so y is too small (too negative)
        return nx + nxy**2 / abs(ny)
    else:
        raise ValueError("Unexpected condition in nxd")


def nyd(nx: float, ny: float, nxy: float) -> float:
    """
    Calculate the y-direction design force (nyd).

    Calculate the design force in the y-direction based on the input forces.
    Based on ČSN P ENV 1992–1–1 (731201), Appendix 2, par. A2.9.

    Args:
        nx: Force in x-direction (kN/m)
        ny: Force in y-direction (kN/m)
        nxy: Shear force (kN/m)

    Returns:
        The y-direction design force (kN/m).

    """
    # Flowchart for normal forces:
    # if ny >= nx and nx >= -|nxy|: return ny + |nxy|
    # elif ny < nx and ny >= -|nxy|: return ny + |nxy|
    # else: use alternative formula
    if ny >= nx and nx >= -abs(nxy):
        return ny + abs(nxy)
    elif ny < nx and ny >= -abs(nxy):
        return ny + abs(nxy)
    elif ny >= nx and nx < -abs(nxy):
        # nx < -|nxy|, so x is too small (too negative)
        return ny + nxy**2 / abs(nx)
    elif ny < nx and ny < -abs(nxy):
        # ny < -|nxy|, so y is too small (too negative)
        return 0.0
    else:
        raise ValueError("Unexpected condition in nyd")
