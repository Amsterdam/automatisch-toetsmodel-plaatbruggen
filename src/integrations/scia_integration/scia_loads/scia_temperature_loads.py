"""
SCIA temperature loads module.

This module provides functionality to apply temperature loads to bridge deck zones
according to NEN-EN 1991-1-5 using the SCIA model builder interface.

Temperature loads are calculated using the temperature_load module and applied to
each deck zone with appropriate thermal gradients (top_delta and bottom_delta).
"""

from typing import Any

from src.common.constants.technical import (
    TEMP_INITIAL_TEMPERATURE,
    TEMP_OMEGA_M,
    TEMP_OMEGA_N,
    TEMP_UNIT_WIDTH,
)
from src.geometry.bridge_geometry_data import create_node_and_thickness_dict
from src.integrations.scia_integration.model.scia_model_interface import SciaModelBuilder
from src.integrations.scia_integration.types import BridgeParametrization
from src.temperature.temperature_load import calculate_temperature_load_combinations


def _validate_temperature_cases(load_cases: dict[str, Any]) -> dict[str, Any]:
    """Validate that temperature cases exist in load_cases."""
    if "temperature_cases" not in load_cases:
        raise ValueError("Temperature load cases not found in load_cases dictionary")
    return load_cases["temperature_cases"]


def _validate_plates(builder: SciaModelBuilder) -> dict[str, Any]:
    """Validate that plates exist in builder."""
    plates = getattr(builder, "plates", {})
    if not plates:
        raise ValueError("No plates found in builder. Ensure geometry is created before applying temperature loads.")
    return plates


def _validate_plate_thickness(plate_name: str, thickness_dict: dict[str, float]) -> float:
    """Validate that thickness exists for the plate."""
    deck_thickness = thickness_dict.get(plate_name)
    if deck_thickness is None:
        raise ValueError(f"Thickness not found for plate {plate_name}")
    return deck_thickness


def _get_minimum_pavement_thickness(params: BridgeParametrization) -> float:
    """Extract minimum pavement thickness from load zones."""
    load_zones = getattr(params, "load_zones_data_array", [])
    if load_zones:
        pavement_thicknesses = [float(getattr(zone, "pavement_thickness", 0.0)) for zone in load_zones if hasattr(zone, "pavement_thickness")]
        return min(pavement_thicknesses) if pavement_thicknesses else 0.0
    return 0.0


def _apply_temperature_load_to_plate(
    builder: SciaModelBuilder,
    plate_name: str,
    temp_cases: dict[str, Any],
    case_mapping: dict[str, str],
    temp_combinations: dict[str, tuple[float, float]],
) -> None:
    """Apply temperature loads for all combinations to a single plate."""
    for combi_key, temp_key in case_mapping.items():
        load_case = temp_cases.get(combi_key)
        if load_case is None:
            raise KeyError(f"Load case '{combi_key}' not found in temperature_cases")

        top_delta, bottom_delta = temp_combinations[temp_key]
        thermal_load_name = f"temp_{combi_key}_{plate_name}"

        builder.create_thermal_surface_load(
            name=thermal_load_name,
            load_case_name=load_case.name,
            plane_name=plate_name,
            top_delta=top_delta,
            bottom_delta=bottom_delta,
        )


def add_temperature_loads(
    builder: SciaModelBuilder,
    params: BridgeParametrization,
    load_cases: dict[str, Any],
) -> list[Any]:
    """
    Add temperature loads to all deck zones for load cases BG3001-BG3004.

    This function applies thermal surface loads to each deck zone (Z1, Z2, Z3) across
    all spans for the four temperature load combinations according to NEN-EN 1991-1-5:
    - BG3001: Heat with omega_N combination
    - BG3002: Heat with omega_M combination
    - BG3003: Cool with omega_N combination
    - BG3004: Cool with omega_M combination

    For each deck zone, temperature deltas are calculated based on:
    - Total deck height (h): from bridge geometry
    - Surface thickness (t_surface): minimum pavement thickness from all load zones
    - Centroid height (z): h/2 for rectangular sections
    - Width (b): from TEMP_UNIT_WIDTH constant

    Temperature calculation parameters are defined in src.common.constants.technical:
    - TEMP_UNIT_WIDTH: 1.0 m (unit width for analysis)
    - TEMP_INITIAL_TEMPERATURE: 10.0°C (T_0)
    - TEMP_OMEGA_N: 0.35 (combination factor for uniform component)
    - TEMP_OMEGA_M: 0.75 (combination factor for bending component)

    Surface thickness (t_surface) is determined from the load zones data:
    - Collected from all load zones' pavement_thickness values
    - The minimum value is used for conservative temperature calculations

    The temperature gradient is applied linearly through the deck thickness:
    - top_delta: Temperature difference at +Z surface (top of deck)
    - bottom_delta: Temperature difference at -Z surface (bottom of deck)

    :param builder: The SCIA model builder instance
    :type builder: SciaModelBuilder
    :param params: Bridge parameters containing geometry and material properties
    :type params: BridgeParametrization
    :param load_cases: Dictionary of created load cases, must contain "temperature_cases"
    :type load_cases: dict[str, Any]
    :returns: Empty list for compatibility with load creation interface
    :rtype: list[Any]
    :raises ValueError: When temperature load cases are missing or load creation fails
    :raises KeyError: When required temperature case keys are not found

    Example:
        >>> add_temperature_loads(builder, params, load_cases)
        []

    Note:
        - Temperature loads are applied to all plate/plane objects in the model
        - Each plate is identified by name pattern: Z1_span, Z2_span, Z3_span
        - The function automatically extracts deck thickness for each zone
        - Temperature parameters can be adjusted in src.common.constants.technical

    """
    try:
        # Validate and get temperature load cases
        temp_cases = _validate_temperature_cases(load_cases)

        # Map the four temperature combinations to their load cases
        case_mapping = {
            "combi_1": "heat_omega_N",
            "combi_2": "heat_omega_M",
            "combi_3": "cool_omega_N",
            "combi_4": "cool_omega_M",
        }

        # Extract thickness data and minimum pavement thickness
        _, thickness_dict = create_node_and_thickness_dict(params)
        t_surface_min = _get_minimum_pavement_thickness(params)

        # Validate and get plates from builder
        plates = _validate_plates(builder)

        # Iterate through each plate and apply temperature loads
        for plate_name in plates:
            # Validate plate name format: "Z1_1", "Z2_3", "Z3_5", etc.
            try:
                parts = plate_name.split("_")
                if len(parts) != 2:
                    continue  # Skip plates that don't follow expected naming

                # Validate and get deck thickness for this zone
                deck_thickness = _validate_plate_thickness(plate_name, thickness_dict)

                # Calculate centroid height (for rectangular section, z = h/2)
                h = deck_thickness
                z = h / 2.0

                # Calculate temperature load combinations for this zone
                temp_combinations = calculate_temperature_load_combinations(
                    h=h,
                    t_surface=t_surface_min,
                    z=z,
                    b=TEMP_UNIT_WIDTH,
                    T_0=TEMP_INITIAL_TEMPERATURE,
                    omega_N=TEMP_OMEGA_N,
                    omega_M=TEMP_OMEGA_M,
                )

                # Apply temperature loads for all four load cases
                _apply_temperature_load_to_plate(builder, plate_name, temp_cases, case_mapping, temp_combinations)

            except (ValueError, IndexError) as e:
                # Log warning but continue with other plates
                raise ValueError(f"Failed to apply temperature load to plate {plate_name}: {e}") from e

    except Exception as e:
        raise ValueError(f"Failed to add temperature loads: {e}") from e
    else:
        return []
