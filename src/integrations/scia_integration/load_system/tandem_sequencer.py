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
    Calculate the x-positions of the tandem systems in a notional lane along the length of the bridge deck.
    Default spacing between tandem systems is 0.5 meters. A tandem system exactly mid-span is always included.

    Args:
        length_bridgedeck (float): The length of the bridge deck in meters.
        thickness_bridgedeck (float): The thickness of the bridge deck in meters.
        length_vehicle (float): The length of the vehicle in meters.
        spacing (float): The spacing between tandem systems in meters.

    Returns:
        list[float]: A list containing the positions of the tandem systems along the bridge deck.

    """
    start_of_lanes = calculate_start_of_lanes(thickness_bridgedeck)
    tandem_systems = []

    # Calculate positions based on vehicle length
    mid_span_position = length_bridgedeck / 2 - length_vehicle / 2
    end_span_position = length_bridgedeck - start_of_lanes - length_vehicle

    # Generate positions from start_of_lanes to end_span_position (inclusive), step dx
    pos = start_of_lanes
    while pos < end_span_position - 1e-6:  # Use a small epsilon to avoid floating-point issues
        tandem_systems.append(round(pos, 6))
        pos += spacing
    # Always include end_span_position exactly
    tandem_systems.append(round(end_span_position, 6))

    # Ensure mid-span position is included (within tolerance)
    if not any(abs(p - mid_span_position) < 1e-6 for p in tandem_systems):
        tandem_systems.append(round(mid_span_position, 6))

    return sorted(set(tandem_systems))
