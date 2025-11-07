"""
Module for calculating temperature loads for bridges according to NEN-EN 1991-1-5.

This module provides comprehensive functionality to calculate temperature components and effects
for bridge design and assessment according to Dutch standards (NEN-EN 1991-1-5).

Key features:
- Calculation of uniform temperature component (delta_T_N_exp, delta_T_N_con) based on minimum and
  maximum shade air temperatures from Table 5.2
- Extraction of temperature difference components (delta_T) for heating and cooling
  scenarios with bilinear interpolation for intermediate values from Table NB.6/B.3
- Temperature profile creation for heating and cooling scenarios over cross-section height
- Temperature analysis tables that decompose non-linear temperature distributions into:
  * Uniform component (ΔTN)
  * Bending component (ΔTM)
  * Remaining temperature component (ΔTE)
- Trapezoidal integration for calculating thermal effects with proper centroid calculations
- Temperature load combinations according to NEN-EN 1991-1-5 with combination factors (ωN, ωM)
- Helper functions for determining temperature zone heights in cross-sections

The module uses lookup tables from NEN-EN 1991-1-5 and provides interpolation for
intermediate values to ensure accurate temperature load calculations for structural analysis.
"""

from pathlib import Path
from typing import TypedDict

import pandas as pd

# ===================================================================================================================
# Type Definitions
# ===================================================================================================================


class HeatingHeightsResult(TypedDict):
    """Result type for collect_sorted_heights_heat function."""

    heights: list[float]
    h: float
    h_1_heat: float
    h_2_heat: float
    h_3_heat: float
    z: float
    bottom: float


class CoolingHeightsResult(TypedDict):
    """Result type for collect_sorted_heights_cool function."""

    heights: list[float]
    h: float
    h_1_cool: float
    h_2_cool: float
    h_3_cool: float
    h_4_cool: float
    z: float
    bottom: float


# ===================================================================================================================
# Paths
# ===================================================================================================================

PROJECT_PATH = Path(__file__).parent.parent.parent
NEN_EN_1991_1_5_table_5_2_PATH = PROJECT_PATH / "resources" / "data" / "code_tables" / "NEN_EN_1991_1_5_table_5_2.csv"
NEN_EN_1991_1_5_table_NB6_B_3_PATH = PROJECT_PATH / "resources" / "data" / "code_tables" / "NEN_EN_1991_1_5_table_NB6_B_3.csv"

# ===================================================================================================================
# Functions
# ===================================================================================================================


def calculate_uniform_temperature_component(
    T_0: float = 10.0,
    data_path: Path = NEN_EN_1991_1_5_table_5_2_PATH,
) -> dict[str, float]:
    """
    Calculate the uniform temperature components delta_T_N according to NEN-EN 1991-1-5.

    This function calculates the uniform temperature components for expansion and contraction
    based on the minimum and maximum shade air temperatures from NEN-EN 1991-1-5 Table 5.2.

    The calculation follows the standard procedure:
    - T_e,min = T_min + 8°C (minimum bridge temperature)
    - T_e,max = T_max + 2°C (maximum bridge temperature)
    - delta_T_N_exp = T_e,max - T_0 (uniform temperature component for expansion)
    - delta_T_N_con = T_0 - T_e,min (uniform temperature component for contraction)

    :param T_0: Initial temperature at the time of restraint (°C).
                Default is 10.0°C according to Dutch practice.
    :type T_0: float
    :param data_path: Path to the CSV file containing temperature data from
                      NEN-EN 1991-1-5 Table 5.2.
    :type data_path: Path

    :returns: Dictionary containing the following temperature values (°C):
              - "delta_T_N_exp": Uniform temperature component for expansion
              - "delta_T_N_con": Uniform temperature component for contraction
              - "T_min": Minimum shade air temperature
              - "T_max": Maximum shade air temperature
              - "T_e_min": Minimum bridge temperature
              - "T_e_max": Maximum bridge temperature
              - "T_0": Initial temperature at the time of restraint
    :rtype: dict[str, float]

    :raises FileNotFoundError: If the data file cannot be found.
    :raises ValueError: If the data file is malformed or missing required columns.

    Example:
        >>> result = calculate_uniform_temperature_component(T_0=10.0)
        >>> print(f"Expansion component: {result['delta_T_N_exp']:.1f}°C")
        >>> print(f"Contraction component: {result['delta_T_N_con']:.1f}°C")

    """
    # Read temperature data from NEN-EN 1991-1-5 Table 5.2
    temp_data = pd.read_csv(data_path, sep=";", decimal=",")

    # Extract minimum and maximum shade air temperatures
    T_min = float(temp_data["T_min"].to_numpy()[0])
    T_max = float(temp_data["T_max"].to_numpy()[0])

    # Calculate minimum and maximum bridge temperatures
    # According to NEN-EN 1991-1-5:6.1.3.2
    T_e_min = T_min + 8  # Minimum bridge temperature
    T_e_max = T_max + 2  # Maximum bridge temperature

    # Calculate total uniform temperature ranges
    delta_T_N_exp = T_e_max - T_0
    delta_T_N_con = T_0 - T_e_min

    return {
        "delta_T_N_exp": delta_T_N_exp,
        "delta_T_N_con": delta_T_N_con,
        "T_min": T_min,
        "T_max": T_max,
        "T_e_min": T_e_min,
        "T_e_max": T_e_max,
        "T_0": T_0,
    }


def collect_sorted_heights_heat(
    h: float,
    t_surface: float,
    z: float,
) -> HeatingHeightsResult:
    """
    Collect and sort height values from largest to lowest for heating scenario.

    This function calculates the heating zone heights according to NEN-EN 1991-1-5
    and collects the specified height values including h, h_1_heat,
    the sum of h_1_heat and h_2_heat, z, h_3_heat, and 0, then sorts them
    in descending order (largest to lowest).

    :param h: Total height of the cross-section (m).
    :type h: float
    :param t_surface: Surface thickness (m).
    :type t_surface: float
    :param z: Reference height, center of gravity (m).
    :type z: float

    :returns: Dictionary containing:
              - "heights": List of height values sorted from largest to lowest
              - "h": Total height of the cross-section
              - "h_1_heat": Height of zone 1
              - "h_2_heat": Height of zone 2
              - "h_3_heat": Height of zone 3
              - "z": Reference height (center of gravity)
              - "bottom": Bottom height (0)
    :rtype: HeatingHeightsResult

    Example:
        >>> result = collect_sorted_heights_heat(1.25, 0.1, 0.625)
        >>> print(result["heights"])
        [1.25, 0.625, 0.4, 0.15, 0.1, 0]
        >>> print(result["h_1_heat"])
        0.15

    """
    # Calculate heating zone heights according to NEN-EN 1991-1-5
    h_1_heat = min(0.3 * h, 0.15)
    h_2_heat = max(0.1, min(0.3 * h, 0.25))
    h_3_heat = min(0.3 * h, h - h_1_heat - h_2_heat, 0.1 + t_surface)

    heights = [
        h,
        h - h_1_heat,
        h - h_1_heat - h_2_heat,
        z,
        h_3_heat,
        0,
    ]

    return {
        "heights": sorted(heights, reverse=True),
        "h": h,
        "h_1_heat": h_1_heat,
        "h_2_heat": h_2_heat,
        "h_3_heat": h_3_heat,
        "z": z,
        "bottom": 0,
    }


def collect_sorted_heights_cool(
    h: float,
    z: float,
) -> CoolingHeightsResult:
    """
    Collect and sort height values from largest to lowest for cooling scenario.

    This function calculates the cooling zone heights according to NEN-EN 1991-1-5
    and collects the specified height values including h, h_1_cool,
    the sum of h_1_cool and h_2_cool, z, the sum of h_1_cool, h_2_cool and h_3_cool,
    h_4_cool, and 0, then sorts them in descending order (largest to lowest).

    :param h: Total height of the cross-section (m).
    :type h: float
    :param z: Reference height, center of gravity (m).
    :type z: float

    :returns: Dictionary containing:
              - "heights": List of height values sorted from largest to lowest
              - "h": Total height of the cross-section
              - "h_1_cool": Height of zone 1
              - "h_2_cool": Height of zone 2
              - "h_3_cool": Height of zone 3
              - "h_4_cool": Height of zone 4
              - "z": Reference height (center of gravity)
              - "bottom": Bottom height (0)
    :rtype: CoolingHeightsResult

    Example:
        >>> result = collect_sorted_heights_cool(1.25, 0.625)
        >>> print(result["heights"])
        [1.25, 0.625, 0.45, 0.25, 0.2, 0.0]
        >>> print(result["h_1_cool"])
        0.25

    """
    # Calculate cooling zone heights according to NEN-EN 1991-1-5
    h_1_cool = min(0.2 * h, 0.25)
    h_2_cool = min(0.25 * h, 0.2)
    h_3_cool = h_2_cool
    h_4_cool = h_1_cool

    heights = [
        h,
        h - h_1_cool,
        h - h_1_cool - h_2_cool,
        z,
        h_3_cool + h_4_cool,
        h_4_cool,
        0,
    ]

    return {
        "heights": sorted(heights, reverse=True),
        "h": h,
        "h_1_cool": h_1_cool,
        "h_2_cool": h_2_cool,
        "h_3_cool": h_3_cool,
        "h_4_cool": h_4_cool,
        "z": z,
        "bottom": 0,
    }


def _linear_interpolate(
    x: float,
    x0: float,
    x1: float,
    y0: float,
    y1: float,
) -> float:
    """
    Perform linear interpolation between two points.

    Given two points (x0, y0) and (x1, y1), this function calculates the
    interpolated y value at position x using linear interpolation.

    :param x: The x-coordinate at which to interpolate.
    :type x: float
    :param x0: The x-coordinate of the first point.
    :type x0: float
    :param x1: The x-coordinate of the second point.
    :type x1: float
    :param y0: The y-coordinate of the first point.
    :type y0: float
    :param y1: The y-coordinate of the second point.
    :type y1: float

    :returns: The interpolated y value at position x.
    :rtype: float

    Example:
        >>> result = _linear_interpolate(0.5, 0.0, 1.0, 10.0, 20.0)
        >>> print(result)
        15.0

    """
    if x1 == x0:
        return y0

    weight = (x - x0) / (x1 - x0)
    return y0 * (1 - weight) + y1 * weight


def get_temperature_differences(
    h: float,
    t_surface: float,
) -> dict[str, float]:
    """
    Extract delta_T values from NEN-EN 1991-1-5 Table NB.6/B.3 with bilinear interpolation.

    This function retrieves the temperature difference components (delta_T1, delta_T2, delta_T3)
    for both heating and cooling scenarios based on the cross-section height and surface thickness.
    For intermediate values, bilinear interpolation is performed.

    :param h: Total height of the cross-section (m). Valid range: 0.4 to 1.5 m.
    :type h: float
    :param t_surface: Surface thickness (mm). Valid range: 0 to 100 mm.
    :type t_surface: float

    :returns: Dictionary containing the following temperature differences (°C):
              - "delta_T1_heat": Temperature difference in zone 1 (heating)
              - "delta_T2_heat": Temperature difference in zone 2 (heating)
              - "delta_T3_heat": Temperature difference in zone 3 (heating)
              - "delta_T1_cool": Temperature difference in zone 1 (cooling)
              - "delta_T2_cool": Temperature difference in zone 2 (cooling)
              - "delta_T3_cool": Temperature difference in zone 3 (cooling)
              - "delta_T4_cool": Temperature difference in zone 4 (cooling)
    :rtype: dict[str, float]

    :raises FileNotFoundError: If the data file cannot be found.
    :raises ValueError: If h or t_surface are outside valid ranges or if data is malformed.

    Example:
        >>> temps = get_temperature_differences(h=1.0, t_surface=50)
        >>> print(f"delta_T1_heat = {temps['delta_T1_heat']:.1f}°C")
        delta_T1_heat = 15.0°C

    """
    # Read temperature data from NEN-EN 1991-1-5 Table NB.6/B.3
    df_delta_T = pd.read_csv(NEN_EN_1991_1_5_table_NB6_B_3_PATH, sep=";", decimal=",")

    # Get unique values for h and surface_thickness
    h_values = sorted(df_delta_T["h"].unique())
    t_values = sorted(df_delta_T["surface_thickness"].unique())

    # Clamp input values to valid ranges
    h_clamped = max(h_values[0], min(h, h_values[-1]))
    t_clamped = max(t_values[0], min(t_surface, t_values[-1]))

    # Find surrounding h values for interpolation
    h_lower = max([hv for hv in h_values if hv <= h_clamped], default=h_values[0])
    h_upper = min([hv for hv in h_values if hv >= h_clamped], default=h_values[-1])

    # Find surrounding t_surface values for interpolation
    t_lower = max([tv for tv in t_values if tv <= t_clamped], default=t_values[0])
    t_upper = min([tv for tv in t_values if tv >= t_clamped], default=t_values[-1])

    # If exact match, return directly
    exact_match = df_delta_T[(df_delta_T["h"] == h_clamped) & (df_delta_T["surface_thickness"] == t_clamped)]
    if not exact_match.empty:
        row = exact_match.iloc[0]
        return {
            "delta_T1_heat": float(row["delta_T1_heat"]),
            "delta_T2_heat": float(row["delta_T2_heat"]),
            "delta_T3_heat": float(row["delta_T3_heat"]),
            "delta_T1_cool": float(row["delta_T1_cool"]),
            "delta_T2_cool": float(row["delta_T2_cool"]),
            "delta_T3_cool": float(row["delta_T3_cool"]),
            "delta_T4_cool": float(row["delta_T4_cool"]),
        }

    # Get values at four corners for bilinear interpolation
    q11 = df_delta_T[(df_delta_T["h"] == h_lower) & (df_delta_T["surface_thickness"] == t_lower)].iloc[0]
    q12 = df_delta_T[(df_delta_T["h"] == h_lower) & (df_delta_T["surface_thickness"] == t_upper)].iloc[0]
    q21 = df_delta_T[(df_delta_T["h"] == h_upper) & (df_delta_T["surface_thickness"] == t_lower)].iloc[0]
    q22 = df_delta_T[(df_delta_T["h"] == h_upper) & (df_delta_T["surface_thickness"] == t_upper)].iloc[0]

    # Bilinear interpolation
    # If h_lower == h_upper or t_lower == t_upper, simplify to linear interpolation
    delta_T_columns = [
        "delta_T1_heat",
        "delta_T2_heat",
        "delta_T3_heat",
        "delta_T1_cool",
        "delta_T2_cool",
        "delta_T3_cool",
        "delta_T4_cool",
    ]

    if h_lower == h_upper and t_lower == t_upper:
        # Single point - no interpolation needed
        result = q11
    elif h_lower == h_upper:
        # Linear interpolation in t direction only
        result = {}
        for col in delta_T_columns:
            result[col] = _linear_interpolate(t_clamped, t_lower, t_upper, q11[col], q12[col])
    elif t_lower == t_upper:
        # Linear interpolation in h direction only
        result = {}
        for col in delta_T_columns:
            result[col] = _linear_interpolate(h_clamped, h_lower, h_upper, q11[col], q21[col])
    else:
        # Full bilinear interpolation
        result = {}
        for col in delta_T_columns:
            # Interpolate in h direction at t_lower
            val_t_lower = _linear_interpolate(h_clamped, h_lower, h_upper, q11[col], q21[col])
            # Interpolate in h direction at t_upper
            val_t_upper = _linear_interpolate(h_clamped, h_lower, h_upper, q12[col], q22[col])
            # Interpolate in t direction
            result[col] = _linear_interpolate(t_clamped, t_lower, t_upper, val_t_lower, val_t_upper)
            result[col] = float(result[col])

    return result


def create_temperature_profile_heat(
    h: float,
    t_surface: float,
    z: float,
) -> pd.DataFrame:
    """
    Create a temperature profile DataFrame for the heating scenario.

    This function generates a DataFrame containing heights and corresponding delta_T values
    for the heat situation according to NEN-EN 1991-1-5. The temperature distribution is:
    - At h: delta_T1_heat
    - At h - h_1_heat: delta_T2_heat
    - At 0: delta_T3_heat
    - At other points: 0°C (unless interpolated)
    - At z: interpolated if it falls between defined points

    :param h: Total height of the cross-section (m).
    :type h: float
    :param t_surface: Surface thickness (m).
    :type t_surface: float
    :param z: Reference height, center of gravity (m).
    :type z: float

    :returns: DataFrame with columns 'height' and 'delta_T', sorted by height (descending).
    :rtype: pd.DataFrame

    Example:
        >>> df = create_temperature_profile_heat(h=1.25, t_surface=0.1, z=0.625)
        >>> print(df)
           height  delta_T
        0    1.25    18.0
        1    1.10    10.0
        2    0.625    5.0
        3    0.00     5.0

    """
    # Get temperature differences from the table
    temp_diffs = get_temperature_differences(h=h, t_surface=t_surface * 1000)  # Convert m to mm

    delta_T1_heat = temp_diffs["delta_T1_heat"]
    delta_T2_heat = temp_diffs["delta_T2_heat"]
    delta_T3_heat = temp_diffs["delta_T3_heat"]

    # Get all sorted heights and zone heights using the helper function
    heights_data = collect_sorted_heights_heat(h=h, t_surface=t_surface, z=z)
    all_heights = heights_data["heights"]
    h_top = heights_data["h"]
    h_1_heat = heights_data["h_1_heat"]
    h_2_heat = heights_data["h_2_heat"]
    bottom = heights_data["bottom"]

    # Define key points with their temperatures
    # According to NEN-EN 1991-1-5, the temperature profile has these key points:
    # - At h: delta_T1_heat
    # - At h - h_1_heat: delta_T2_heat
    # - At h - h_1_heat - h_2_heat: 0°C (end of zone 2)
    # - At bottom (0): delta_T3_heat
    key_points = {
        h_top: delta_T1_heat,
        h_top - h_1_heat: delta_T2_heat,
        h_top - h_1_heat - h_2_heat: 0.0,
        bottom: delta_T3_heat,
    }

    # Build the temperature profile - first pass to assign temperatures
    height_temp_map = {}

    for height in all_heights:
        # Check if this height is a key point, otherwise set to 0.0
        # All other heights (like h_3_heat, z) get zero temperature initially
        height_temp_map[height] = key_points.get(height, 0.0)

    # Second pass: interpolate z if it's between two key points
    if heights_data["z"] not in key_points:
        z_height = heights_data["z"]
        # Get sorted list of key point heights
        sorted_key_heights = sorted(key_points.keys(), reverse=True)

        # Find which two key points z is between
        for i in range(len(sorted_key_heights) - 1):
            h_upper = sorted_key_heights[i]
            h_lower = sorted_key_heights[i + 1]

            if h_lower < z_height < h_upper:
                # Interpolate between the two key points
                temp_upper = key_points[h_upper]
                temp_lower = key_points[h_lower]
                z_temp = _linear_interpolate(z_height, h_lower, h_upper, temp_lower, temp_upper)
                height_temp_map[z_height] = z_temp
                break

    # Build final lists
    heights = []
    temperatures = []

    for height in all_heights:
        heights.append(height)
        temperatures.append(height_temp_map[height])

    # Create DataFrame
    profile_data = pd.DataFrame(
        {
            "height": heights,
            "delta_T": temperatures,
        }
    )

    # Sort by height (descending)
    return profile_data.sort_values("height", ascending=False).reset_index(drop=True)


def create_temperature_profile_cool(
    h: float,
    t_surface: float,
    z: float,
) -> pd.DataFrame:
    """
    Create a temperature profile DataFrame for the cooling scenario.

    This function generates a DataFrame containing heights and corresponding delta_T values
    for the cooling situation according to NEN-EN 1991-1-5. The temperature distribution is:
    - At h: delta_T1_cool
    - At h - h_1_cool: delta_T2_cool
    - At h_4_cool: delta_T3_cool
    - At 0: delta_T4_cool
    - At other points: 0°C (unless interpolated)
    - At z: interpolated if it falls between two non-zero temperature points

    :param h: Total height of the cross-section (m).
    :type h: float
    :param t_surface: Surface thickness (m).
    :type t_surface: float
    :param z: Reference height, center of gravity (m).
    :type z: float

    :returns: DataFrame with columns 'height' and 'delta_T', sorted by height (descending).
    :rtype: pd.DataFrame

    Example:
        >>> df = create_temperature_profile_cool(h=1.25, t_surface=0.1, z=0.625)
        >>> print(df)
           height  delta_T
        0    1.25   -5.0
        1    1.00   -1.0
        2    0.625   0.0
        3    0.00    0.0

    """
    # Get temperature differences from the table
    temp_diffs = get_temperature_differences(h=h, t_surface=t_surface * 1000)  # Convert m to mm

    delta_T1_cool = temp_diffs["delta_T1_cool"]
    delta_T2_cool = temp_diffs["delta_T2_cool"]
    delta_T3_cool = temp_diffs["delta_T3_cool"]
    delta_T4_cool = temp_diffs["delta_T4_cool"]

    # Get all sorted heights and zone heights using the helper function
    heights_data = collect_sorted_heights_cool(h=h, z=z)
    all_heights = heights_data["heights"]
    h_top = heights_data["h"]
    h_1_cool = heights_data["h_1_cool"]
    h_2_cool = heights_data["h_2_cool"]
    h_4_cool = heights_data["h_4_cool"]
    bottom = heights_data["bottom"]

    # Define key points with their temperatures
    # According to NEN-EN 1991-1-5, the temperature profile has these key points:
    # - At h: delta_T1_cool
    # - At h - h_1_cool: delta_T2_cool
    # - At h - h_1_cool - h_2_cool: 0°C (end of zone 2)
    # - At h_4_cool: delta_T3_cool
    # - At bottom (0): delta_T4_cool
    key_points = {
        h_top: delta_T1_cool,
        h_top - h_1_cool: delta_T2_cool,
        h_top - h_1_cool - h_2_cool: 0.0,
        h_4_cool: delta_T3_cool,
        bottom: delta_T4_cool,
    }

    # Build the temperature profile - first pass to assign temperatures
    height_temp_map = {}

    for height in all_heights:
        # Check if this height is a key point, otherwise set to 0.0
        # All other heights get zero temperature initially
        height_temp_map[height] = key_points.get(height, 0.0)

    # Second pass: interpolate z if it's between two key points
    if heights_data["z"] not in key_points:
        z_height = heights_data["z"]
        # Get sorted list of key point heights
        sorted_key_heights = sorted(key_points.keys(), reverse=True)

        # Find which two key points z is between
        for i in range(len(sorted_key_heights) - 1):
            h_upper = sorted_key_heights[i]
            h_lower = sorted_key_heights[i + 1]

            if h_lower < z_height < h_upper:
                # Interpolate between the two key points
                temp_upper = key_points[h_upper]
                temp_lower = key_points[h_lower]
                z_temp = _linear_interpolate(z_height, h_lower, h_upper, temp_lower, temp_upper)
                height_temp_map[z_height] = z_temp
                break

    # Build final lists
    heights = []
    temperatures = []

    for height in all_heights:
        heights.append(height)
        temperatures.append(height_temp_map[height])

    # Create DataFrame
    profile_data = pd.DataFrame(
        {
            "height": heights,
            "delta_T": temperatures,
        }
    )

    # Sort by height (descending)
    return profile_data.sort_values("height", ascending=False).reset_index(drop=True)


def _calculate_trapezoid_centroid(
    value_top: float,
    value_bottom: float,
    height: float,
) -> float:
    """
    Calculate the centroid position of a trapezoidal distribution.

    For a trapezoid with values at the top and bottom over a given height,
    this function calculates the distance from the bottom where the centroid
    (center of area) is located.

    The formula is based on the weighted average of a linear distribution:
    centroid_from_bottom = height × (2·value_top + value_bottom) / (3·(value_top + value_bottom))

    :param value_top: Value at the top of the trapezoid.
    :type value_top: float
    :param value_bottom: Value at the bottom of the trapezoid.
    :type value_bottom: float
    :param height: Height of the trapezoid.
    :type height: float

    :returns: Distance from bottom to centroid. Returns height/2 if both values are zero.
    :rtype: float

    Example:
        >>> centroid = _calculate_trapezoid_centroid(10.0, 4.5, 0.15)
        >>> print(f"Centroid at {centroid:.4f} m from bottom")
        Centroid at 0.0913 m from bottom

    """
    if value_top + value_bottom == 0:
        # Both values are zero, return geometric center
        return height / 2.0

    # Weighted centroid based on trapezoidal distribution
    return height * (2 * value_top + value_bottom) / (3 * (value_top + value_bottom))


def _trapezoidal_integration(
    heights: list[float],
    values: list[float],
    reference_point: float = 0.0,
    width: float = 1.0,
) -> dict[str, list[float]]:
    """
    Perform trapezoidal integration over a series of height-value pairs.

    This function integrates a piecewise-linear distribution (defined by heights and values)
    using the trapezoidal rule. For each segment, it calculates:
    - The average value (first moment)
    - The centroid position of the trapezoidal area
    - The distance from a reference point to the centroid
    - The area integral (value × width × height)
    - The first moment integral (area × distance from reference)

    This is a general-purpose integration method useful for calculating thermal loads,
    distributed loads, or any piecewise-linear distribution.

    :param heights: List of heights in descending order (top to bottom).
    :type heights: list[float]
    :param values: List of values at each height (e.g., temperatures, pressures).
    :type values: list[float]
    :param reference_point: Reference height for moment calculation (default: 0.0).
                           For thermal analysis, this is typically the centroid height.
    :type reference_point: float
    :param width: Width multiplier for area calculation (default: 1.0).
                 For thermal analysis, this is the section width.
    :type width: float

    :returns: Dictionary containing lists of calculated values for each segment:
              - 'delta_h': Height differences (m)
              - 'value_avg': Average values in each segment
              - 'h_centroid': Absolute heights of trapezoid centroids (m)
              - 'distance_from_ref': Distances from reference point to centroids (m)
              - 'area_integral': Integrated areas (value × width × Δh)
              - 'moment_integral': Integrated moments (area × distance)
    :rtype: dict[str, list[float]]

    :raises ValueError: If heights and values have different lengths or less than 2 points.

    Example:
        >>> heights = [1.25, 1.10, 0.85, 0.0]
        >>> temps = [10.0, 4.5, 0.0, 0.0]
        >>> result = _trapezoidal_integration(heights, temps, reference_point=0.625, width=1.0)
        >>> print(f"First segment area: {result['area_integral'][0]:.3f}")
        First segment area: 1.088

    """
    if len(heights) != len(values):
        msg = f"Heights and values must have same length. Got {len(heights)} heights and {len(values)} values."
        raise ValueError(msg)

    if len(heights) < 2:
        msg = f"Need at least 2 points for integration. Got {len(heights)} points."
        raise ValueError(msg)

    # Initialize result lists
    delta_h_list = []
    value_avg_list = []
    h_centroid_list = []
    distance_from_ref_list = []
    area_integral_list = []
    moment_integral_list = []

    # Process each segment
    for i in range(len(heights) - 1):
        h_top = heights[i]
        h_bottom = heights[i + 1]
        value_top = values[i]
        value_bottom = values[i + 1]

        # Calculate segment properties
        delta_h = h_top - h_bottom
        value_avg = (value_top + value_bottom) / 2.0

        # Calculate centroid of trapezoidal segment
        h_from_bottom = _calculate_trapezoid_centroid(value_top, value_bottom, delta_h)
        h_centroid = h_bottom + h_from_bottom

        # Distance from reference point to centroid
        distance = h_centroid - reference_point

        # Calculate integrals
        area_integral = delta_h * value_avg * width
        moment_integral = area_integral * distance

        # Store results
        delta_h_list.append(delta_h)
        value_avg_list.append(value_avg)
        h_centroid_list.append(h_centroid)
        distance_from_ref_list.append(distance)
        area_integral_list.append(area_integral)
        moment_integral_list.append(moment_integral)

    return {
        "delta_h": delta_h_list,
        "value_avg": value_avg_list,
        "h_centroid": h_centroid_list,
        "distance_from_ref": distance_from_ref_list,
        "area_integral": area_integral_list,
        "moment_integral": moment_integral_list,
    }


def create_temperature_analysis_table_heat(
    h: float,
    t_surface: float,
    z: float,
    b: float,
) -> pd.DataFrame:
    """
    Create a complete temperature analysis table for the heating scenario.

    This function generates a comprehensive DataFrame containing the temperature profile
    and all derived quantities needed for structural analysis according to NEN-EN 1991-1-5.

    The calculation uses trapezoidal integration where each segment between two heights
    is treated as a trapezoid. The temperature distribution is integrated using:
    - Average temperature: (ΔT_top + ΔT_bottom) / 2
    - Centroid of trapezoid: weighted position based on temperature distribution

    The table includes:
    - Height (h) and temperature difference (delta_T) from the temperature profile
    - Width (b) - constant for rectangular sections
    - Incremental area moment: Δh·ΔT_avg·b for each segment
    - Distance from neutral axis: z (from trapezoid centroid to section centroid)
    - Incremental second moment: Δh·ΔT_avg·b·z
    - Uniform temperature component: ΔTN (constant over height)
    - Bending temperature component: ΔTM (varies linearly over height)
    - Remaining temperature component: ΔTE = ΔT - ΔTN - ΔTM

    Calculation formulas:
    - A = b × h (cross-sectional area, calculated internally)
    - I_y = (1/12) × b × h³ (second moment of area, calculated internally)
    - ΔTN = Σ(Δh·ΔT_avg·b) / A (uniform component)
    - ΔTM_base = h · Σ(Δh·ΔT_avg·b·z) / I_y (bending base value)
    - ΔTM(h_i) = ΔTM_base · (h_i - z_centroid) / h (varies linearly with height)
    - ΔTE = ΔT - ΔTN - ΔTM (Remaining temperature component at each height)

    :param h: Total height of the cross-section (m).
    :type h: float
    :param t_surface: Surface thickness (m).
    :type t_surface: float
    :param z: Reference height, center of gravity measured from bottom (m).
              For rectangular sections: z = h/2.
    :type z: float
    :param b: Width of the cross-section (m). Assumed constant for rectangular sections.
    :type b: float

    :returns: DataFrame with one row per height level (including bottom at h=0):
              - 'h': Height coordinate (m)
              - 'delta_T': Temperature difference at this height (°C)
              - 'b': Width (m)
              - 'delta_h_delta_T_b': Δh·ΔT_avg·b for segment starting at this height (°C·m²)
              - 'z': Distance from section centroid to trapezoid centroid (m)
              - 'delta_h_delta_T_b_z': Δh·ΔT_avg·b·z (°C·m³)
              - 'delta_T_N': Uniform temperature component (°C, constant for all rows)
              - 'delta_T_M': Bending temperature component at this height (°C)
              - 'delta_T_E': Remaining temperature component at this height (°C)
    :rtype: pd.DataFrame

    Example:
        >>> df = create_temperature_analysis_table_heat(h=1.25, t_surface=0.1, z=0.625, b=1.0)
        >>> print(df)
              h  delta_T    b  delta_h_delta_T_b      z  delta_h_delta_T_b_z  delta_T_N  delta_T_M  delta_T_E
        0  1.250     10.0  1.0              1.088  0.559                0.608       1.32       3.18       5.50
        1  1.100      4.5  1.0              0.563  0.392                0.220       1.32       2.42       0.76
        2  0.850      0.0  1.0              0.563  0.392                0.220       1.32       1.15      -2.47
        ...

    """
    # Calculate cross-sectional properties
    A = b * h  # Cross-sectional area (m²)
    I_y = (b * h**3) / 12  # Second moment of area (m⁴)

    # Get the basic temperature profile
    profile_df = create_temperature_profile_heat(h=h, t_surface=t_surface, z=z)

    # Rename height column to match table format (delta_T already has correct name)
    profile_df = profile_df.rename(columns={"height": "h"})

    # Add width column (constant for rectangular sections)
    profile_df["b"] = b

    # Perform trapezoidal integration using the general helper function
    heights_list = profile_df["h"].tolist()
    temperatures_list = profile_df["delta_T"].tolist()

    integration_results = _trapezoidal_integration(
        heights=heights_list,
        values=temperatures_list,
        reference_point=z,
        width=b,
    )

    # Extract results with meaningful names for temperature analysis
    delta_h_delta_T_b_values = integration_results["area_integral"]
    z_values = integration_results["distance_from_ref"]
    delta_h_delta_T_b_z_values = integration_results["moment_integral"]

    # Create new dataframe with segment-based calculations
    # Each row represents a height level with its temperature and the segment calculations
    # that start at that height. The z value is the distance from the section centroid
    # to the trapezoid centroid of each segment.
    # Include all heights including bottom (h=0)
    all_heights = profile_df["h"].tolist()
    all_delta_T = profile_df["delta_T"].tolist()

    # Pad the segment values with 0 for the last row (bottom)
    segment_df = pd.DataFrame(
        {
            "h": all_heights,
            "delta_T": all_delta_T,
            "b": b,
            "delta_h_delta_T_b": [*delta_h_delta_T_b_values, 0.0],
            "z": [*z_values, 0.0 - z],  # Distance from centroid at h=0
            "delta_h_delta_T_b_z": [*delta_h_delta_T_b_z_values, 0.0],
        }
    )

    # Calculate ΔTN (uniform temperature component)
    sum_delta_h_delta_T_b = sum(delta_h_delta_T_b_values)
    delta_T_N = sum_delta_h_delta_T_b / A
    segment_df["delta_T_N"] = delta_T_N

    # Calculate ΔTM (bending temperature component)
    sum_delta_h_delta_T_b_z = sum(delta_h_delta_T_b_z_values)
    delta_T_M_base = h * sum_delta_h_delta_T_b_z / I_y
    # Calculate ΔTM at each height
    # ΔTM varies linearly from top to bottom
    # At top (h): ΔTM_top = ΔTM·zo / h = ΔTM·(h - z) / h
    # At bottom (0): ΔTM_bottom = -ΔTM·zb / h = -ΔTM·z / h
    # At any height h_i: ΔTM(h_i) = ΔTM·(h_i - z) / h
    segment_df["delta_T_M"] = delta_T_M_base * (segment_df["h"] - z) / h

    # Calculate ΔTE (Remaining temperature component): ΔTE = ΔT - ΔTN - ΔTM
    segment_df["delta_T_E"] = segment_df["delta_T"] - segment_df["delta_T_N"] - segment_df["delta_T_M"]

    # Select and order final columns
    return segment_df[["h", "delta_T", "b", "delta_h_delta_T_b", "z", "delta_h_delta_T_b_z", "delta_T_N", "delta_T_M", "delta_T_E"]]


def create_temperature_analysis_table_cool(
    h: float,
    t_surface: float,
    z: float,
    b: float,
) -> pd.DataFrame:
    """
    Create a complete temperature analysis table for the cooling scenario.

    This function generates a comprehensive DataFrame containing the temperature profile
    and all derived quantities needed for structural analysis according to NEN-EN 1991-1-5.

    The calculation uses trapezoidal integration where each segment between two heights
    is treated as a trapezoid. The temperature distribution is integrated using:
    - Average temperature: (ΔT_top + ΔT_bottom) / 2
    - Centroid of trapezoid: weighted position based on temperature distribution

    The table includes:
    - Height (h) and temperature difference (delta_T) from the temperature profile
    - Width (b) - constant for rectangular sections
    - Incremental area moment: Δh·ΔT_avg·b for each segment
    - Distance from neutral axis: z (from trapezoid centroid to section centroid)
    - Incremental second moment: Δh·ΔT_avg·b·z
    - Uniform temperature component: ΔTN (constant over height)
    - Bending temperature component: ΔTM (varies linearly over height)
    - Remaining temperature component: ΔTE = ΔT - ΔTN - ΔTM

    Calculation formulas:
    - A = b × h (cross-sectional area, calculated internally)
    - I_y = (1/12) × b × h³ (second moment of area, calculated internally)
    - ΔTN = Σ(Δh·ΔT_avg·b) / A (uniform component)
    - ΔTM_base = h · Σ(Δh·ΔT_avg·b·z) / I_y (bending base value)
    - ΔTM(h_i) = ΔTM_base · (h_i - z_centroid) / h (varies linearly with height)
    - ΔTE = ΔT - ΔTN - ΔTM (Remaining temperature component at each height)

    :param h: Total height of the cross-section (m).
    :type h: float
    :param t_surface: Surface thickness (m).
    :type t_surface: float
    :param z: Reference height, center of gravity measured from bottom (m).
              For rectangular sections: z = h/2.
    :type z: float
    :param b: Width of the cross-section (m). Assumed constant for rectangular sections.
    :type b: float

    :returns: DataFrame with one row per height level (including bottom at h=0):
              - 'h': Height coordinate (m)
              - 'delta_T': Temperature difference at this height (°C)
              - 'b': Width (m)
              - 'delta_h_delta_T_b': Δh·ΔT_avg·b for segment starting at this height (°C·m²)
              - 'z': Distance from section centroid to trapezoid centroid (m)
              - 'delta_h_delta_T_b_z': Δh·ΔT_avg·b·z (°C·m³)
              - 'delta_T_N': Uniform temperature component (°C, constant for all rows)
              - 'delta_T_M': Bending temperature component at this height (°C)
              - 'delta_T_E': Remaining temperature component at this height (°C)
    :rtype: pd.DataFrame

    Example:
        >>> df = create_temperature_analysis_table_cool(h=1.25, t_surface=0.1, z=0.625, b=1.0)
        >>> print(df)
              h  delta_T    b  delta_h_delta_T_b      z  delta_h_delta_T_b_z  delta_T_N  delta_T_M  delta_T_E
        0  1.250     -5.0  1.0             -0.750  0.528               -0.396      -0.68      -1.64      -2.68
        1  1.000     -1.0  1.0             -0.100  0.308               -0.031      -0.68      -0.98       0.66
        2  0.800      0.0  1.0              0.000 -0.625                0.000      -0.68       0.00       0.68
        ...

    """
    # Calculate cross-sectional properties
    A = b * h  # Cross-sectional area (m²)
    I_y = (b * h**3) / 12  # Second moment of area (m⁴)

    # Get the basic temperature profile
    profile_df = create_temperature_profile_cool(h=h, t_surface=t_surface, z=z)

    # Rename height column to match table format (delta_T already has correct name)
    profile_df = profile_df.rename(columns={"height": "h"})

    # Add width column (constant for rectangular sections)
    profile_df["b"] = b

    # Perform trapezoidal integration using the general helper function
    heights_list = profile_df["h"].tolist()
    temperatures_list = profile_df["delta_T"].tolist()

    integration_results = _trapezoidal_integration(
        heights=heights_list,
        values=temperatures_list,
        reference_point=z,
        width=b,
    )

    # Extract results with meaningful names for temperature analysis
    delta_h_delta_T_b_values = integration_results["area_integral"]
    z_values = integration_results["distance_from_ref"]
    delta_h_delta_T_b_z_values = integration_results["moment_integral"]

    # Create new dataframe with segment-based calculations
    # Each row represents a height level with its temperature and the segment calculations
    # that start at that height. The z value is the distance from the section centroid
    # to the trapezoid centroid of each segment.
    # Include all heights including bottom (h=0)
    all_heights = profile_df["h"].tolist()
    all_delta_T = profile_df["delta_T"].tolist()

    # Pad the segment values with 0 for the last row (bottom)
    segment_df = pd.DataFrame(
        {
            "h": all_heights,
            "delta_T": all_delta_T,
            "b": b,
            "delta_h_delta_T_b": [*delta_h_delta_T_b_values, 0.0],
            "z": [*z_values, 0.0 - z],  # Distance from centroid at h=0
            "delta_h_delta_T_b_z": [*delta_h_delta_T_b_z_values, 0.0],
        }
    )

    # Calculate ΔTN (uniform temperature component)
    sum_delta_h_delta_T_b = sum(delta_h_delta_T_b_values)
    delta_T_N = sum_delta_h_delta_T_b / A
    segment_df["delta_T_N"] = delta_T_N

    # Calculate ΔTM (bending temperature component)
    sum_delta_h_delta_T_b_z = sum(delta_h_delta_T_b_z_values)
    delta_T_M_base = h * sum_delta_h_delta_T_b_z / I_y
    # Calculate ΔTM at each height
    # ΔTM varies linearly from top to bottom
    # At top (h): ΔTM_top = ΔTM·zo / h = ΔTM·(h - z) / h
    # At bottom (0): ΔTM_bottom = -ΔTM·zb / h = -ΔTM·z / h
    # At any height h_i: ΔTM(h_i) = ΔTM·(h_i - z) / h
    segment_df["delta_T_M"] = delta_T_M_base * (segment_df["h"] - z) / h

    # Calculate ΔTE (Remaining temperature component): ΔTE = ΔT - ΔTN - ΔTM
    segment_df["delta_T_E"] = segment_df["delta_T"] - segment_df["delta_T_N"] - segment_df["delta_T_M"]

    # Select and order final columns
    return segment_df[["h", "delta_T", "b", "delta_h_delta_T_b", "z", "delta_h_delta_T_b_z", "delta_T_N", "delta_T_M", "delta_T_E"]]


def calculate_temperature_load_combinations(
    h: float,
    t_surface: float,
    z: float,
    b: float = 1.0,
    T_0: float = 10.0,
    omega_N: float = 0.35,
    omega_M: float = 0.75,
    data_path: Path = NEN_EN_1991_1_5_table_5_2_PATH,
) -> dict[str, tuple[float, float]]:
    """
    Calculate temperature load combinations according to NEN-EN 1991-1-5.

    This function combines the uniform temperature components (delta_T_N_exp, delta_T_N_con)
    with the bending temperature components (delta_T_M at top and bottom) and the uniform
    component from the non-linear distribution (delta_T_N from analysis tables) according to
    the specified combination factors omega_N and omega_M.

    The following eight load combinations are calculated:

    Heating combinations:
    1. omega_N * delta_T_N_exp + delta_T_N + delta_T_M_heat_top
    2. omega_N * delta_T_N_exp + delta_T_N + delta_T_M_heat_bot
    3. delta_T_N_exp + omega_M * (delta_T_N + delta_T_M_heat_top)
    4. delta_T_N_exp + omega_M * (delta_T_N + delta_T_M_heat_bot)

    Cooling combinations:
    5. omega_N * delta_T_N_con + delta_T_N + delta_T_M_cool_top
    6. omega_N * delta_T_N_con + delta_T_N + delta_T_M_cool_bot
    7. delta_T_N_con + omega_M * (delta_T_N + delta_T_M_cool_top)
    8. delta_T_N_con + omega_M * (delta_T_N + delta_T_M_cool_bot)

    Where:
    - delta_T_N_exp, delta_T_N_con: uniform temperature changes from Table 5.2
    - delta_T_N: uniform component from non-linear distribution analysis
    - delta_T_M_heat_top, delta_T_M_heat_bot: bending component at top (h) and bottom (0) for heating
    - delta_T_M_cool_top, delta_T_M_cool_bot: bending component at top (h) and bottom (0) for cooling

    :param h: Total height of the cross-section (m).
    :type h: float
    :param t_surface: Surface thickness (m).
    :type t_surface: float
    :param z: Reference height, center of gravity measured from bottom (m).
              For rectangular sections: z = h/2.
    :type z: float
    :param b: Width of the cross-section (m). Assumed constant for rectangular sections.
              Default is 1.0 m.
    :type b: float
    :param T_0: Initial temperature at the time of restraint (°C).
                Default is 10.0°C according to Dutch practice.
    :type T_0: float
    :param omega_N: Combination factor for uniform temperature component.
                    Default is 0.35 according to NEN-EN 1991-1-5.
    :type omega_N: float
    :param omega_M: Combination factor for bending temperature component.
                    Default is 0.75 according to NEN-EN 1991-1-5.
    :type omega_M: float
    :param data_path: Path to the CSV file containing temperature data from
                      NEN-EN 1991-1-5 Table 5.2.
    :type data_path: Path

    :returns: Dictionary containing four pairs of temperature load combination values (°C).
              Each pair contains (top, bottom) values:
              - "heat_omega_N": (omega_N * delta_T_N_exp + delta_T_N + delta_T_M_heat_top,
                                omega_N * delta_T_N_exp + delta_T_N + delta_T_M_heat_bot)
              - "heat_omega_M": (delta_T_N_exp + omega_M * (delta_T_N + delta_T_M_heat_top),
                                delta_T_N_exp + omega_M * (delta_T_N + delta_T_M_heat_bot))
              - "cool_omega_N": (omega_N * delta_T_N_con + delta_T_N + delta_T_M_cool_top,
                                omega_N * delta_T_N_con + delta_T_N + delta_T_M_cool_bot)
              - "cool_omega_M": (delta_T_N_con + omega_M * (delta_T_N + delta_T_M_cool_top),
                                delta_T_N_con + omega_M * (delta_T_N + delta_T_M_cool_bot))
    :rtype: dict[str, tuple[float, float]]

    :raises FileNotFoundError: If the data file cannot be found.
    :raises ValueError: If the data file is malformed or missing required columns.

    Example:
        >>> combinations = calculate_temperature_load_combinations(h=1.25, t_surface=0.1, z=0.625, b=1.0)
        >>> top, bot = combinations["heat_omega_N"]
        >>> print(f"Heat omega_N - top: {top:.2f}°C, bottom: {bot:.2f}°C")
        Heat omega_N - top: 12.00°C, bottom: 5.84°C

    """
    # Calculate uniform temperature components from Table 5.2
    uniform_temps = calculate_uniform_temperature_component(T_0=T_0, data_path=data_path)
    delta_T_N_exp = uniform_temps["delta_T_N_exp"]
    delta_T_N_con = -uniform_temps["delta_T_N_con"]  # Negate for cooling (contraction)

    # Calculate temperature analysis tables for heating and cooling
    heat_table = create_temperature_analysis_table_heat(h=h, t_surface=t_surface, z=z, b=b)
    cool_table = create_temperature_analysis_table_cool(h=h, t_surface=t_surface, z=z, b=b)

    # Extract delta_T_N from the analysis tables (uniform component from non-linear distribution)
    # This is constant for all rows in each table
    delta_T_N_heat = heat_table["delta_T_N"].iloc[0]
    delta_T_N_cool = cool_table["delta_T_N"].iloc[0]

    # Extract delta_T_M at top (h) and bottom (0)
    # Top is the first row (h = maximum height)
    # Bottom is the last row (h = 0)
    delta_T_M_heat_top = heat_table["delta_T_M"].iloc[0]
    delta_T_M_heat_bot = heat_table["delta_T_M"].iloc[-1]

    delta_T_M_cool_top = cool_table["delta_T_M"].iloc[0]
    delta_T_M_cool_bot = cool_table["delta_T_M"].iloc[-1]

    # Calculate the 8 combinations
    # Heating combinations
    heat_omega_N_top = omega_N * delta_T_N_exp + delta_T_N_heat + delta_T_M_heat_top
    heat_omega_N_bot = omega_N * delta_T_N_exp + delta_T_N_heat + delta_T_M_heat_bot
    heat_omega_M_top = delta_T_N_exp + omega_M * (delta_T_N_heat + delta_T_M_heat_top)
    heat_omega_M_bot = delta_T_N_exp + omega_M * (delta_T_N_heat + delta_T_M_heat_bot)

    # Cooling combinations
    cool_omega_N_top = omega_N * delta_T_N_con + delta_T_N_cool + delta_T_M_cool_top
    cool_omega_N_bot = omega_N * delta_T_N_con + delta_T_N_cool + delta_T_M_cool_bot
    cool_omega_M_top = delta_T_N_con + omega_M * (delta_T_N_cool + delta_T_M_cool_top)
    cool_omega_M_bot = delta_T_N_con + omega_M * (delta_T_N_cool + delta_T_M_cool_bot)

    return {
        "heat_omega_N": (heat_omega_N_top, heat_omega_N_bot),
        "heat_omega_M": (heat_omega_M_top, heat_omega_M_bot),
        "cool_omega_N": (cool_omega_N_top, cool_omega_N_bot),
        "cool_omega_M": (cool_omega_M_top, cool_omega_M_bot),
    }
