"""
Tandem system sequencer for generating load positions.

This module provides utilities for calculating tandem system positions along bridge decks.
"""

from src.integrations.scia_integration.constants.geometry import (
    TANDEM_SPACING_LONGITUDINAL,
    TANDEM_START_Y_OFFSET_FACTOR,
    TANDEM_WHEEL_SPACING_LONGITUDINAL,
    TANDEM_WHEEL_SPACING_TRANSVERSE,
)

# Standard tandem wheel offsets from bottom left corner
TANDEM_WHEEL_OFFSETS = [
    (0, 0),
    (TANDEM_WHEEL_SPACING_LONGITUDINAL, 0),
    (0, TANDEM_WHEEL_SPACING_TRANSVERSE),
    (TANDEM_WHEEL_SPACING_LONGITUDINAL, TANDEM_WHEEL_SPACING_TRANSVERSE),
]


def calculate_start_of_lanes(thickness_bridgedeck: float) -> float:
    """
    Calculate the distance from the edge of the bridge deck, from where the tandem systems start.
    Assuming a spread under 45 degrees, the distance is equal to 0.9 times the thickness of the bridge deck.

    Args:
        thickness_bridgedeck (float): The thickness of the bridge deck in meters.

    Returns:
        distance(float): The distance in meters from the edge of the bridge deck to the start of the tandem systems.

    """
    return TANDEM_START_Y_OFFSET_FACTOR * thickness_bridgedeck


def tandem_system_sequencer(
    length_bridgedeck: float, thickness_bridgedeck: float, length_vehicle: float = 0.0, spacing: float = TANDEM_SPACING_LONGITUDINAL
) -> list[float]:
    """
    Calculate the longitudinal x-positions of tandem systems along the bridge deck.

    The tandem systems are positioned starting from an offset based on the bridge deck thickness
    (accounting for load spread), and distributed at regular intervals along the deck length.
    The starting offset is calculated as TANDEM_START_Y_OFFSET_FACTOR * thickness_bridgedeck,
    then adjusted by the vehicle length. The function ensures that both the end position and
    mid-span position are always included in the returned positions.

    Args:
        length_bridgedeck (float): The total length of the bridge deck in meters.
        thickness_bridgedeck (float): The thickness of the bridge deck in meters, used to calculate
            the starting offset based on load spread assumption (45-degree angle).
        length_vehicle (float): The length of the vehicle in meters. Defaults to 0.0.
        spacing (float): The longitudinal spacing between consecutive tandem systems in meters.
            Defaults to TANDEM_SPACING_LONGITUDINAL (0.5 meters).

    Returns:
        list[float]: A sorted list of unique x-positions (in meters) where tandem systems should be
            placed along the bridge deck, always including mid-span and end positions.

    """
    start_of_lanes = calculate_start_of_lanes(thickness_bridgedeck) - length_vehicle
    tandem_systems = []

    # Calculate critical positions: mid-span for maximum bending moment and end position
    mid_span_position = length_bridgedeck / 2 - length_vehicle / 2
    end_span_position = length_bridgedeck - start_of_lanes - length_vehicle

    # Generate positions at regular intervals from start to end
    pos = start_of_lanes
    while pos < end_span_position - 1e-6:  # Use epsilon to avoid floating-point precision issues
        tandem_systems.append(round(pos, 6))
        pos += spacing

    # Always include the end position for complete coverage
    tandem_systems.append(round(end_span_position, 6))

    # Ensure mid-span position is included (critical for structural analysis)
    if not any(abs(p - mid_span_position) < 1e-6 for p in tandem_systems):
        tandem_systems.append(round(mid_span_position, 6))

    return sorted(set(tandem_systems))
