"""
Theoretical tandem system generators for bridge load analysis.

This module provides functions for generating theoretical tandem load systems
positioned at theoretical traffic lane centers based on geometric bridge division.
"""

from typing import TYPE_CHECKING, Any

from src.combinations.load_factors import get_alpha_q_nen_en_1991_2, get_alpha_trend_nen_8701, get_psi_nen_8701
from src.integrations.scia_integration.constants.geometry import (
    DEFAULT_LANE_WIDTH,
    LANE_CENTER_OFFSET_FACTOR,
    MINIMUM_BRIDGE_WIDTH_FOR_MULTIPLE_LANES,
    TANDEM_START_Y_OFFSET,
    TANDEM_VEHICLE_LENGTH,
)
from src.integrations.scia_integration.constants.loads import (
    NOBS_DEFAULT,
    TANDEM_CONTACT_AREA_SIDE,
    TANDEM_LOAD_BASE_MAIN,
    TANDEM_LOAD_BASE_SECOND,
    TANDEM_LOAD_BASE_THIRD,
)
from src.integrations.scia_integration.load_system.lane_calculations import get_reference_period
from src.integrations.scia_integration.load_system.tandem_sequencer import TANDEM_WHEEL_OFFSETS, tandem_system_sequencer

if TYPE_CHECKING:
    from app.bridge.parametrization import BridgeParametrization


# Helper function to create wheel coordinates for a tandem
def _create_tandem_wheels(x_start: float, y_center: float, wheel_size: float) -> list[list[list[float]]]:
    """Helper function to create a tandem's wheel coordinates."""
    wheels = []
    tandem_start_y = y_center - TANDEM_START_Y_OFFSET
    for dx, dy in TANDEM_WHEEL_OFFSETS:
        x0 = x_start + dx
        y0 = tandem_start_y + dy
        wheel_coords = [
            [x0 + wheel_size, y0],
            [x0 + wheel_size, y0 + wheel_size],
            [x0, y0 + wheel_size],
            [x0, y0],
        ]
        wheels.append(wheel_coords)
    return wheels


def generate_theoretical_lane_positions_bg8000(
    width_bridgedeck: float,
    lane_width: float = DEFAULT_LANE_WIDTH,
    zone3_width: float = 0.0,
    zone2_width: float = 0.0,
) -> list[float]:
    """
    Generate Y-positions for theoretical traffic lanes across bridge width.

    Creates lane center positions based on geometric division of bridge width.
    This provides the foundation for theoretical lane-based tandem loading.

    :param width_bridgedeck: Total bridge width in meters
    :type width_bridgedeck: float
    :param lane_width: Standard lane width in meters (default 3.0m)
    :type lane_width: float
    :param zone3_width: Width of zone 3 to shift all lane centers by (-zone3_width)
    :type zone3_width: float
    :returns: List of Y-coordinates for lane centers (shifted by -zone3_width)
    :rtype: list[float]
    :raises ValueError: If bridge_width or lane_width is not positive

    Examples:
        >>> generate_theoretical_lane_positions(30.0, DEFAULT_LANE_WIDTH, 2.0)
        [-0.5, 2.5, 5.5, 8.5, 11.5, 14.5, 17.5, 20.5, 23.5, 26.5]

    """
    if width_bridgedeck <= 0:
        raise ValueError("Bridge width must be positive")
    if lane_width <= 0:
        raise ValueError("Lane width must be positive")

    # Calculate number of complete lanes
    num_lanes = int(width_bridgedeck // lane_width)

    # Generate lane center positions
    lane_centers = []
    for lane_idx in range(num_lanes):
        lane_start = lane_idx * lane_width
        lane_center = lane_start + (lane_width / 2)  # Center of each lane
        lane_centers.append(lane_center - zone3_width - LANE_CENTER_OFFSET_FACTOR * zone2_width)

    return lane_centers


def tandem_systems_theoretical_lanes_bg8000(  # noqa: PLR0913
    params: "BridgeParametrization",
    length_bridgedeck: float,
    width_bridgedeck: float,
    thickness_bridgedeck: float,
    width_firstsegment_zone3: float,
    width_firstsegment_zone2: float,
    lane_width: float = DEFAULT_LANE_WIDTH,
) -> list[dict[str, Any]]:
    """
    Generate tandem loads positioned at theoretical traffic lane centers.

    This function creates separate load cases for each vehicle (tandem system) positioned at
    theoretical lane centers based on geometric bridge width division.

    :param length_bridgedeck: Bridge length in meters
    :type length_bridgedeck: float
    :param width_bridgedeck: Bridge width in meters
    :type width_bridgedeck: float
    :param thickness_bridgedeck: Bridge thickness in meters
    :type thickness_bridgedeck: float
    :param lane_width: Standard lane width in meters (default 3.0m)
    :type lane_width: float
    :returns: List of tandem load cases. Each dictionary contains:
        - load_case: Identifier string (e.g., "BG8001", "BG8002", "BG8003")
        - title: Title string (e.g., "rs 1 - Conf. A", "rs 2 - Conf. A", "rs 3 - Conf. A")
        - wheels: List of 4 wheel coordinates per tandem
        - load: Load intensity in N/m²
    :rtype: list[dict[str, Any]]
    """
    wheel_size = TANDEM_CONTACT_AREA_SIDE

    # Get longitudinal positions (same as existing system)
    tandem_x_positions = tandem_system_sequencer(length_bridgedeck, thickness_bridgedeck, length_vehicle=TANDEM_VEHICLE_LENGTH)

    # Get theoretical lane positions (NEW: replaces fixed positions)
    lane_y_positions = generate_theoretical_lane_positions_bg8000(width_bridgedeck, lane_width, width_firstsegment_zone3, width_firstsegment_zone2)

    results = []
    # Obtain required factors for vertical traffic loading (LM1 and LM2)
    psi_nen_8701_factor = get_psi_nen_8701(length_bridgedeck, get_reference_period(params))
    alpha_trend_factor = get_alpha_trend_nen_8701(length_bridgedeck, (get_reference_period(params) + 2010))
    alpha_q_factor = get_alpha_q_nen_en_1991_2(length_bridgedeck, nobs=NOBS_DEFAULT)[0]
    # Obtain load values
    contact_area = TANDEM_CONTACT_AREA_SIDE * TANDEM_CONTACT_AREA_SIDE
    load_main = TANDEM_LOAD_BASE_MAIN / contact_area * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factor
    load_second = TANDEM_LOAD_BASE_SECOND / contact_area * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factor
    load_third = TANDEM_LOAD_BASE_THIRD / contact_area * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factor
    # Generate separate load cases for each vehicle
    if lane_y_positions:
        prefix = "BG8"
        load_case_counter = 1

        for x in tandem_x_positions:
            # Vehicle 1: Main vehicle (rs 1) - always exists if there are lanes
            wheels_main = _create_tandem_wheels(x, lane_y_positions[0], wheel_size)

            load_case_main: dict[str, Any] = {
                "load_case": f"{prefix}{load_case_counter:03d}",
                "title": f"rs 1 - Conf. A - x = {x:g} m",
                "wheels": wheels_main,
                "load": load_main,
            }
            results.append(load_case_main)
            load_case_counter += 1

            # Vehicle 2: 200 kN tandem in next lane (rs 2) - if exists
            if len(lane_y_positions) > 1:
                wheels_200 = _create_tandem_wheels(x, lane_y_positions[1], wheel_size)

                load_case_200: dict[str, Any] = {
                    "load_case": f"{prefix}{load_case_counter:03d}",
                    "title": f"rs 2 - Conf. A - x = {x:g} m",
                    "wheels": wheels_200,
                    "load": load_second,
                }
                results.append(load_case_200)
                load_case_counter += 1

            # Vehicle 3: 100 kN tandem in next-next lane (rs 3) - if exists
            if len(lane_y_positions) > 2:
                wheels_100 = _create_tandem_wheels(x, lane_y_positions[2], wheel_size)

                load_case_100: dict[str, Any] = {
                    "load_case": f"{prefix}{load_case_counter:03d}",
                    "title": f"rs 3 - Conf. A - x = {x:g} m",
                    "wheels": wheels_100,
                    "load": load_third,
                }
                results.append(load_case_100)
                load_case_counter += 1

    return results


def generate_theoretical_lane_positions_bg9000(
    width_bridgedeck: float,
    lane_width: float = DEFAULT_LANE_WIDTH,
    zone3_width: float = 0.0,
    zone2_width: float = 0.0,
) -> list[float]:
    """
    Generate Y-positions for theoretical traffic lanes across bridge width, starting from the right edge.

    This mirrors the original lane division, but lanes are counted from the right edge instead of the left.

    :param width_bridgedeck: Total bridge width in meters
    :type width_bridgedeck: float
    :param lane_width: Standard lane width in meters (default 3.0m)
    :type lane_width: float
    :param zone3_width: Width of zone 3 to shift all lane centers by (-zone3_width)
    :type zone3_width: float
    :returns: List of Y-coordinates for lane centers (shifted by -zone3_width), reversed
    :rtype: list[float]
    """
    if width_bridgedeck <= 0:
        raise ValueError("Bridge width must be positive")
    if lane_width <= 0:
        raise ValueError("Lane width must be positive")

    num_lanes = int(width_bridgedeck // lane_width)
    lane_centers = []
    for lane_idx in range(num_lanes):
        # Start from the right edge
        lane_start = width_bridgedeck - lane_idx * lane_width
        lane_center = lane_start - (lane_width / 2)
        lane_centers.append(lane_center - zone3_width - LANE_CENTER_OFFSET_FACTOR * zone2_width)

    return lane_centers


def tandem_systems_theoretical_lanes_bg9000(  # noqa: PLR0913
    params: "BridgeParametrization",
    length_bridgedeck: float,
    width_bridgedeck: float,
    thickness_bridgedeck: float,
    width_firstsegment_zone3: float,
    width_firstsegment_zone2: float,
    lane_width: float = DEFAULT_LANE_WIDTH,
) -> list[dict[str, Any]]:
    """
    Generate tandem loads positioned at theoretical traffic lane centers, starting from the right edge.

    This function creates separate load cases for each vehicle (tandem system) positioned at
    theoretical lane centers, starting from the right edge.

    :param length_bridgedeck: Bridge length in meters
    :type length_bridgedeck: float
    :param width_bridgedeck: Bridge width in meters
    :type width_bridgedeck: float
    :param thickness_bridgedeck: Bridge thickness in meters
    :type thickness_bridgedeck: float
    :param lane_width: Standard lane width in meters (default 3.0m)
    :type lane_width: float
    :returns: List of tandem load cases. Each dictionary contains:
        - load_case: Identifier string (e.g., "BG9001", "BG9002", "BG9003")
        - title: Title string (e.g., "rs 1 - Conf. B", "rs 2 - Conf. B", "rs 3 - Conf. B")
        - wheels: List of wheel coordinates per tandem
        - load: Load intensity in N/m²
    :rtype: list[dict[str, Any]]
    """
    wheel_size = TANDEM_CONTACT_AREA_SIDE
    tandem_x_positions = tandem_system_sequencer(length_bridgedeck, thickness_bridgedeck, length_vehicle=TANDEM_VEHICLE_LENGTH)
    lane_y_positions = generate_theoretical_lane_positions_bg9000(width_bridgedeck, lane_width, width_firstsegment_zone3, width_firstsegment_zone2)

    results = []
    # Obtain required factors for vertical traffic loading (LM1 and LM2)
    psi_nen_8701_factor = get_psi_nen_8701(length_bridgedeck, get_reference_period(params))
    alpha_trend_factor = get_alpha_trend_nen_8701(length_bridgedeck, (get_reference_period(params) + 2010))
    alpha_q_factor = get_alpha_q_nen_en_1991_2(length_bridgedeck, nobs=NOBS_DEFAULT)[0]
    # Obtain load values
    contact_area = TANDEM_CONTACT_AREA_SIDE * TANDEM_CONTACT_AREA_SIDE
    load_main = TANDEM_LOAD_BASE_MAIN / contact_area * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factor
    load_second = TANDEM_LOAD_BASE_SECOND / contact_area * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factor
    load_third = TANDEM_LOAD_BASE_THIRD / contact_area * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factor
    # Generate separate load cases for each vehicle
    if lane_y_positions:
        prefix = "BG9"
        load_case_counter = 1

        for x in tandem_x_positions:
            # Vehicle 1: Main vehicle (rs 1) - always exists if there are lanes
            wheels_main = _create_tandem_wheels(x, lane_y_positions[0], wheel_size)

            load_case_main: dict[str, Any] = {
                "load_case": f"{prefix}{load_case_counter:03d}",
                "title": f"rs 1 - Conf. B - x = {x:g} m",
                "wheels": wheels_main,
                "load": load_main,
            }
            results.append(load_case_main)
            load_case_counter += 1

            # Vehicle 2: 200 kN tandem in next lane (rs 2) - if exists
            if len(lane_y_positions) > 1:
                wheels_200 = _create_tandem_wheels(x, lane_y_positions[1], wheel_size)

                load_case_200: dict[str, Any] = {
                    "load_case": f"{prefix}{load_case_counter:03d}",
                    "title": f"rs 2 - Conf. B - x = {x:g} m",
                    "wheels": wheels_200,
                    "load": load_second,
                }
                results.append(load_case_200)
                load_case_counter += 1

            # Vehicle 3: 100 kN tandem in next-next lane (rs 3) - if exists
            if len(lane_y_positions) > 2:
                wheels_100 = _create_tandem_wheels(x, lane_y_positions[2], wheel_size)

                load_case_100: dict[str, Any] = {
                    "load_case": f"{prefix}{load_case_counter:03d}",
                    "title": f"rs 3 - Conf. B - x = {x:g} m",
                    "wheels": wheels_100,
                    "load": load_third,
                }
                results.append(load_case_100)
                load_case_counter += 1

    return results


def generate_theoretical_lane_positions_bg10000(
    width_bridgedeck: float,
    lane_width: float = DEFAULT_LANE_WIDTH,
    zone3_width: float = 0.0,
    zone2_width: float = 0.0,
) -> list[float]:
    """
    Generate Y-positions for BG10000 load case: 300 kN in center, 200/100 kN adjacent if width permits.

    :param width_bridgedeck: Total bridge width in meters
    :type width_bridgedeck: float
    :param lane_width: Standard lane width in meters (default 3.0m)
    :type lane_width: float
    :param zone3_width: Width of zone 3 to shift all lane centers by (-zone3_width)
    :type zone3_width: float
    :returns: List of Y-coordinates for lane centers. Returns only center lane if width < 9m
    :rtype: list[float]
    """
    if width_bridgedeck <= 0:
        raise ValueError("Bridge width must be positive")
    if lane_width <= 0:
        raise ValueError("Lane width must be positive")

    # Center lane
    y_center = width_bridgedeck / 2 - zone3_width - LANE_CENTER_OFFSET_FACTOR * zone2_width

    # Only add adjacent lanes if we have at least MINIMUM_BRIDGE_WIDTH_FOR_MULTIPLE_LANES width (3 lanes of DEFAULT_LANE_WIDTH each)
    if width_bridgedeck >= MINIMUM_BRIDGE_WIDTH_FOR_MULTIPLE_LANES:
        # Left lane (adjacent to center)
        y_left = y_center - lane_width
        # Right lane (adjacent to center)
        y_right = y_center + lane_width
        return [y_center, y_left, y_right]
    # For narrow bridges, only return center lane
    return [y_center]


def tandem_systems_theoretical_lanes_bg10000(  # noqa: PLR0913
    params: "BridgeParametrization",
    length_bridgedeck: float,
    width_bridgedeck: float,
    thickness_bridgedeck: float,
    width_firstsegment_zone3: float,
    width_firstsegment_zone2: float,
    lane_width: float = DEFAULT_LANE_WIDTH,
) -> list[dict[str, Any]]:
    """
    Generate BG10000 load cases: 300 kN tandem in center always, 200/100 kN adjacent only if width permits.

    This function creates separate load cases for each vehicle (tandem system). Each vehicle gets its own
    load case with lane indicators (rs 1, rs 2, rs 3) and configuration designation (Conf. C).

    :param params: Bridge parametrization for load factors
    :param length_bridgedeck: Bridge length in meters
    :param width_bridgedeck: Bridge width in meters
    :param thickness_bridgedeck: Bridge thickness in meters
    :param width_firstsegment_zone3: Width of zone 3 in first segment
    :param width_firstsegment_zone2: Width of zone 2 in first segment
    :param lane_width: Standard lane width in meters (default 3.0m)
    :returns: List of BG10000 load cases. Each dictionary contains:
        - load_case: Identifier string (e.g., "BG10001", "BG10002", etc.)
        - title: Title string (e.g., "rs 1 - Conf. C", "rs 2 - Conf. C", "rs 3 - Conf. C")
        - wheels: List of wheel coordinates for the tandem system
        - load: Load intensity in N/m²
    :rtype: list[dict[str, Any]]
    """
    wheel_size = TANDEM_CONTACT_AREA_SIDE
    tandem_x_positions = tandem_system_sequencer(length_bridgedeck, thickness_bridgedeck, length_vehicle=TANDEM_VEHICLE_LENGTH)
    lane_y_positions = generate_theoretical_lane_positions_bg10000(width_bridgedeck, lane_width, width_firstsegment_zone3, width_firstsegment_zone2)

    # If no lanes could be positioned (bridge too narrow), return empty results
    if not lane_y_positions:
        return []

    # Obtain required factors for vertical traffic loading (LM1 and LM2)
    psi_nen_8701_factor = get_psi_nen_8701(length_bridgedeck, get_reference_period(params))
    alpha_trend_factor = get_alpha_trend_nen_8701(length_bridgedeck, (get_reference_period(params) + 2010))
    alpha_q_factor = get_alpha_q_nen_en_1991_2(length_bridgedeck, nobs=NOBS_DEFAULT)[0]
    # Obtain load values
    contact_area = TANDEM_CONTACT_AREA_SIDE * TANDEM_CONTACT_AREA_SIDE
    load_main = TANDEM_LOAD_BASE_MAIN / contact_area * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factor
    load_second = TANDEM_LOAD_BASE_SECOND / contact_area * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factor
    load_third = TANDEM_LOAD_BASE_THIRD / contact_area * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factor

    # Determine how many lanes we have
    num_lanes = len(lane_y_positions)
    y_center = lane_y_positions[0]  # Center lane always exists

    prefix = "BG10"
    results = []
    idx = 1

    # Case 1: Only 1 lane - just create central tandem
    if num_lanes == 1:
        for x in tandem_x_positions:
            # Central 300kN tandem (rs 1)
            wheels_300 = _create_tandem_wheels(x, y_center, wheel_size)

            load_case = {
                "load_case": f"{prefix}{idx:03d}",
                "title": f"rs 1 - Conf. C - x = {x:g} m",
                "wheels": wheels_300,
                "load": load_main,
            }
            results.append(load_case)
            idx += 1
        return results

    # Case 2: Exactly 2 lanes - create center (300 kN) + one adjacent (200 kN)
    if num_lanes == 2:
        y_adjacent = lane_y_positions[1]
        for x in tandem_x_positions:
            # Center vehicle (rs 1)
            wheels_300 = _create_tandem_wheels(x, y_center, wheel_size)
            load_case_center = {
                "load_case": f"{prefix}{idx:03d}",
                "title": f"rs 1 - Conf. C - x = {x:g} m",
                "wheels": wheels_300,
                "load": load_main,
            }
            results.append(load_case_center)
            idx += 1

            # Adjacent vehicle (rs 2)
            wheels_200 = _create_tandem_wheels(x, y_adjacent, wheel_size)
            load_case_adjacent = {
                "load_case": f"{prefix}{idx:03d}",
                "title": f"rs 2 - Conf. C - x = {x:g} m",
                "wheels": wheels_200,
                "load": load_second,
            }
            results.append(load_case_adjacent)
            idx += 1
        return results

    # Case 3: 3 or more lanes - create full configurations sequentially
    y_left = lane_y_positions[1]
    y_right = lane_y_positions[2]

    # First, generate ALL Configuration A load cases (300 kN center, 200 kN left, 100 kN right)
    for x in tandem_x_positions:
        # Center vehicle (rs 1)
        wheels_300 = _create_tandem_wheels(x, y_center, wheel_size)
        load_case_center = {
            "load_case": f"{prefix}{idx:03d}",
            "title": "rs 1 - Conf. C",
            "wheels": wheels_300,
            "load": load_main,
        }
        results.append(load_case_center)
        idx += 1

        # Left vehicle (rs 2) - Configuration A: 200 kN
        wheels_200_left = _create_tandem_wheels(x, y_left, wheel_size)
        load_case_left_a = {
            "load_case": f"{prefix}{idx:03d}",
            "title": f"rs 2 - Conf. C - x = {x:g} m",
            "wheels": wheels_200_left,
            "load": load_second,
        }
        results.append(load_case_left_a)
        idx += 1

        # Right vehicle (rs 3) - Configuration A: 100 kN
        wheels_100_right = _create_tandem_wheels(x, y_right, wheel_size)
        load_case_right_a = {
            "load_case": f"{prefix}{idx:03d}",
            "title": f"rs 3 - Conf. C - x = {x:g} m",
            "wheels": wheels_100_right,
            "load": load_third,
        }
        results.append(load_case_right_a)
        idx += 1

    # Then, generate ALL Configuration D load cases (300 kN center, 100 kN left, 200 kN right)
    # Configuration D is the second half of BG10000 where physical positions are switched
    # But lane labels match load magnitudes: rs 2 = 200 kN (middle), rs 3 = 100 kN (lowest)
    for x in tandem_x_positions:
        # Center vehicle (rs 1)
        wheels_300 = _create_tandem_wheels(x, y_center, wheel_size)
        load_case_center = {
            "load_case": f"{prefix}{idx:03d}",
            "title": "rs 1 - Conf. D",
            "wheels": wheels_300,
            "load": load_main,
        }
        results.append(load_case_center)
        idx += 1

        # Left vehicle - Configuration D: 100 kN load at left position, labeled as rs 3
        wheels_100_left = _create_tandem_wheels(x, y_left, wheel_size)
        load_case_left_d = {
            "load_case": f"{prefix}{idx:03d}",
            "title": f"rs 3 - Conf. D - x = {x:g} m",  # rs 3 = 100 kN (consistency)
            "wheels": wheels_100_left,
            "load": load_third,
        }
        results.append(load_case_left_d)
        idx += 1

        # Right vehicle - Configuration D: 200 kN load at right position, labeled as rs 2
        wheels_200_right = _create_tandem_wheels(x, y_right, wheel_size)
        load_case_right_d = {
            "load_case": f"{prefix}{idx:03d}",
            "title": f"rs 2 - Conf. D - x = {x:g} m",  # rs 2 = 200 kN (consistency)
            "wheels": wheels_200_right,
            "load": load_second,
        }
        results.append(load_case_right_d)
        idx += 1

    return results
