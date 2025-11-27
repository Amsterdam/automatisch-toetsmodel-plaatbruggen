"""Functions for calculating elementary design magnitudes in SCIA.

This module implements the formulas for calculating design magnitudes (mxd+, mxd-, myd+, myd-, nxd, nyd)
based on the input moment and force components.
"""


def mxd_plus(mx: float, my: float, mxy: float) -> float:
    """Calculate the positive x-direction design moment (mxd+).
    
    Args:
        mx: Moment in x-direction
        my: Moment in y-direction
        mxy: Torsional moment
        
    Returns:
        The positive x-direction design moment according to:
        (1) mx + |mxy| if mx ≤ my and mx ≥ -|mxy|
        (2) mx + |mxy| if mx > my and my ≥ -|mxy|
        (3) 0 if mx ≤ my and mx < -|mxy|
        (4) mx + mxy²/|my| if mx > my and my < -|mxy|
    """
    abs_mxy = abs(mxy)
    abs_my = abs(my)
    
    if mx <= my and mx >= -abs_mxy:
        return mx + abs_mxy
    elif mx > my and my >= -abs_mxy:
        return mx + abs_mxy
    elif mx <= my and mx < -abs_mxy:
        return 0.0
    else:  # mx > my and my < -|mxy|
        if abs_my == 0:
            return 0.0
        return mx + (mxy ** 2) / abs_my


def mxd_minus(mx: float, my: float, mxy: float) -> float:
    """Calculate the negative x-direction design moment (mxd-).
    
    Args:
        mx: Moment in x-direction
        my: Moment in y-direction
        mxy: Torsional moment
        
    Returns:
        The negative x-direction design moment according to:
        (1) -mx + |mxy| if mx ≤ my and my ≤ |mxy|
        (2) -mx + |mxy| if mx > my and mx ≤ |mxy|
        (3) -mx + mxy²/|my| if mx ≤ my and my > |mxy|
        (4) 0 if mx > my and mx > |mxy|
    """
    abs_mxy = abs(mxy)
    abs_my = abs(my)
    
    if mx <= my and my <= abs_mxy:
        return -mx + abs_mxy
    elif mx > my and mx <= abs_mxy:
        return -mx + abs_mxy
    elif mx <= my and my > abs_mxy:
        if abs_my == 0:
            return 0.0
        return -mx + (mxy ** 2) / abs_my
    else:  # mx > my and mx > |mxy|
        return 0.0


def myd_plus(mx: float, my: float, mxy: float) -> float:
    """Calculate the positive y-direction design moment (myd+).
    
    Args:
        mx: Moment in x-direction
        my: Moment in y-direction
        mxy: Torsional moment
        
    Returns:
        The positive y-direction design moment according to:
        (1) my + |mxy| if mx ≤ my and mx ≥ -|mxy|
        (2) my + |mxy| if mx > my and my ≥ -|mxy|
        (3) my + mxy²/|mx| if mx ≤ my and mx < -|mxy|
        (4) 0 if mx > my and my < -|mxy|
    """
    abs_mxy = abs(mxy)
    abs_mx = abs(mx)
    
    if mx <= my and mx >= -abs_mxy:
        return my + abs_mxy
    elif mx > my and my >= -abs_mxy:
        return my + abs_mxy
    elif mx <= my and mx < -abs_mxy:
        if abs_mx == 0:
            return 0.0
        return my + (mxy ** 2) / abs_mx
    else:  # mx > my and my < -|mxy|
        return 0.0


def myd_minus(mx: float, my: float, mxy: float) -> float:
    """Calculate the negative y-direction design moment (myd-).
    
    Args:
        mx: Moment in x-direction
        my: Moment in y-direction
        mxy: Torsional moment
        
    Returns:
        The negative y-direction design moment according to:
        (1) -my + |mxy| if mx ≤ my and my ≤ |mxy|
        (2) -my + |mxy| if mx > my and mx ≤ |mxy|
        (3) 0 if mx ≤ my and my > |mxy|
        (4) -my + mxy²/|mx| if mx > my and mx > |mxy|
    """
    abs_mxy = abs(mxy)
    abs_mx = abs(mx)
    
    if mx <= my and my <= abs_mxy:
        return -my + abs_mxy
    elif mx > my and mx <= abs_mxy:
        return -my + abs_mxy
    elif mx <= my and my > abs_mxy:
        return 0.0
    else:  # mx > my and mx > |mxy|
        if abs_mx == 0:
            return 0.0
        return -my + (mxy ** 2) / abs_mx


def nxd(nx: float, ny: float, nxy: float) -> float:
    """Calculate the x-direction design force (nxd).
    
    Args:
        nx: Force in x-direction
        ny: Force in y-direction
        nxy: Shear force
        
    Returns:
        The x-direction design force according to:
        nx + |nxy| for nx ≤ ny and nx ≥ -|nxy|
        nx + |nxy| for nx > ny and ny ≥ -|nxy|
        0 for nx ≤ ny and nx < -|nxy|
        nx + nxy²/|ny| for nx > ny and ny < -|nxy|
    """
    abs_nxy = abs(nxy)
    abs_ny = abs(ny)
    
    if nx <= ny and nx >= -abs_nxy:
        return nx + abs_nxy
    elif nx > ny and ny >= -abs_nxy:
        return nx + abs_nxy
    elif nx <= ny and nx < -abs_nxy:
        return 0.0
    else:  # nx > ny and ny < -|nxy|
        if abs_ny == 0:
            return 0.0
        return nx + (nxy ** 2) / abs_ny


def nyd(nx: float, ny: float, nxy: float) -> float:
    """Calculate the y-direction design force (nyd).
    
    Args:
        nx: Force in x-direction
        ny: Force in y-direction
        nxy: Shear force
        
    Returns:
        The y-direction design force according to:
        ny + |nxy| for nx ≤ ny and nx ≥ -|nxy|
        ny + |nxy| for nx > ny and ny ≥ -|nxy|
        ny + nxy²/|nx| for nx ≤ ny and nx < -|nxy|
        0 for nx > ny and ny < -|nxy|
    """
    abs_nxy = abs(nxy)
    abs_nx = abs(nx)
    
    if nx <= ny and nx >= -abs_nxy:
        return ny + abs_nxy
    elif nx > ny and ny >= -abs_nxy:
        return ny + abs_nxy
    elif nx <= ny and nx < -abs_nxy:
        if abs_nx == 0:
            return 0.0
        return ny + (nxy ** 2) / abs_nx
    else:  # nx > ny and ny < -|nxy|
        return 0.0
