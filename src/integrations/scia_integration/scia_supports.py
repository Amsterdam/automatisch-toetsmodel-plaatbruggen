"""Scia support calculation and helper functions."""

from collections.abc import Sequence
from typing import Any

from viktor.external.scia import LineSupport

# Type aliases for SCIA objects
SciaModel = Any


def get_line_support_edges_for_bridge(
    planes: Sequence[Any],
) -> list[tuple[Any, int]]:
    """
    Return all plate edges where line supports should be placed for the bridge.

    This function selects:
    - The first three edges (edge 4) of the first three planes (crosswise, i.e., planes 0, 1, 2)
    - The last three edges (edge 2) of the last three planes (planes -3, -2, -1)

    The result is a list of (plane, edge_index) tuples, suitable for SCIA's create_line_support_on_plane.

    :param planes: Sequence of SCIA Plane objects (ordered along the bridge)
    :type planes: Sequence[Any]
    :returns: List of (plane, edge_index) tuples for line supports
    :rtype: list[tuple[Any, int]]
    """
    return [(plane, 4) for plane in planes[:3]] + [(plane, 2) for plane in planes[-3:]]


def create_scia_line_supports(
    model: SciaModel,
    planes: Sequence[Any],
) -> list[Any]:
    """
    Create line supports on the first and last three edges of the bridge planes.

    This function places line supports on the specified edges of the bridge planes.

    :param model: SCIA model instance
    :param planes: Sequence of SCIA Plane objects (ordered along the bridge)
    :returns: List of created SCIA line support objects
    :rtype: list[Any]
    """
    edges = get_line_support_edges_for_bridge(planes)
    line_supports = []
    # To generate names, we need to know which plane and which zone (cross direction) each support is on.
    # The planes list is sorted as [(span, zone), ...] in scia_model.py, so we can reconstruct the mapping.
    # We'll build a lookup: plane -> (zone, span)
    plane_to_zone_span = {}
    n_planes = len(planes)
    n_zones = 3  # Always 3 zones per cross section
    n_spans = n_planes // n_zones
    for idx, plane in enumerate(planes):
        # The planes are sorted by (span, zone), so we can recover span and zone from the order
        # There are always 3 zones per span, so:
        span = idx // n_zones + 1
        zone = idx % n_zones + 1
        # For the last three planes (end of bridge), set span to n_spans + 1 (last cross section)
        # These are always the last three planes in the list
        if idx >= n_planes - n_zones:
            span = n_spans + 1
        plane_to_zone_span[plane] = (zone, span)

    for plane, edge_index in edges:
        zone, span = plane_to_zone_span.get(plane, (1, 1))  # Default to zone 1, span 1 if not found
        # Generate a unique name for the line support based on span and zone
        name = f"Slb_opleg_as_{span}:{zone}"
        line_support = model.create_line_support_on_plane(
            (plane, edge_index),
            name=name,
            x=LineSupport.Freedom.FLEXIBLE,
            stiffness_x=1e7,
            y=LineSupport.Freedom.FLEXIBLE,
            stiffness_y=1e6,
            z=LineSupport.Freedom.RIGID,
            rx=LineSupport.Freedom.FREE,
            ry=LineSupport.Freedom.RIGID,
            rz=LineSupport.Freedom.RIGID,
        )
        line_supports.append(line_support)
    return line_supports
