"""
Lane calculation utilities for bridge load analysis.

This module provides functions for calculating notional lane configurations
and their properties based on bridge deck dimensions.
"""

from typing import TYPE_CHECKING

from src.integrations.scia_integration.constants.geometry import DEFAULT_LANE_WIDTH

if TYPE_CHECKING:
    from app.bridge.parametrization import BridgeParametrization

# Bridge deck width properties for calculating lane width
min_width = 5.4
max_width = 6.0


def amount_of_notional_lanes(width_bridgedeck: float) -> tuple[int, float]:
    """
    Calculate the number of notional lanes and their width based on the bridge deck width.

    Args:
        width_bridgedeck (float): The width of the bridge deck in meters.

    Returns:
        tuple[int, float]: A tuple containing the number of notional lanes and the width per lane in meters.

    """
    if width_bridgedeck < min_width:
        return 1, 3
    if min_width <= width_bridgedeck < max_width:
        return 2, width_bridgedeck / 2
    return int(width_bridgedeck // 3), 3


def amount_of_notional_lanes_from_center(width_bridgedeck: float) -> tuple[int, int, float]:
    """
    Calculate the number of notional lanes that can fit on either side of the bridge deck center.

    For BG4003 (center load case), we need to determine how many lanes can fit on either side of
    the center lane. The total width available is divided into two parts (left and right of center),
    and we calculate how many 3m lanes can fit in each part.

    Args:
        width_bridgedeck (float): The width of the bridge deck in meters.

    Returns:
        tuple[int, int, float]: A tuple containing:
            - Number of lanes that fit left of center
            - Number of lanes that fit right of center
            - Width per lane (always 3.0m as per standard)

    """
    # Center lane always takes DEFAULT_LANE_WIDTH
    center_lane_width = DEFAULT_LANE_WIDTH
    remaining_width = width_bridgedeck - center_lane_width

    # Calculate space on either side
    width_per_side = remaining_width / 2

    # Calculate number of full DEFAULT_LANE_WIDTH lanes that can fit on each side
    lanes_per_side = int(width_per_side // DEFAULT_LANE_WIDTH)

    return lanes_per_side, lanes_per_side, DEFAULT_LANE_WIDTH


def calculate_possibilities_lane_orientation(width_bridgedeck: float) -> int:
    """
    Calculate the number of possibilities according to which the tandemsystems can be applied.

    Args:
        width_bridgedeck (float): The width of the bridge deck in meters.

    Returns:
        int: An integer containing the amount of lane orientations possible.

    """
    amount_of_lanes = amount_of_notional_lanes(width_bridgedeck)
    if amount_of_lanes[0] == 1 or amount_of_lanes[0] == 2:
        return 2
    return 4


def get_reference_period(params: "BridgeParametrization") -> int:
    """
    Return the reference period (in years) based on the veiligheidsniveau input.

    :param veiligheidsniveau: The value of the veiligheidsniveau field from parametrization.py
    :type veiligheidsniveau: str
    :returns: Reference period in years (30 or 15)
    :rtype: int
    """
    if params["design_code"] == "NEN 8700 afkeur":
        return 15
    return 30
