"""
SCIA Engineer integration for bridge analysis.

Creates SCIA models from bridge parameters with:
- Multi-zone plates (Zone 1, 2, 3) with variable thickness
- Proper node positioning from bridge_segments_array
- Realistic tandem load application from src.loads.loadcase_helper_functions

========================================================================
COLLEAGUE INTEGRATION POINTS SUMMARY
========================================================================

This file contains 10 clearly marked integration points where your colleague
needs to integrate load combinations, load cases, and results classes:

INTEGRATION POINT 1: Load Groups (Line ~550)
- Location: _add_realistic_tandem_loads function
- Purpose: Replace basic load groups with comprehensive EN 1990 load groups
- Needs: Traffic, pedestrian, wind, thermal load groups with proper relationships

INTEGRATION POINT 2: Basic Load Cases (Line ~565)
- Location: _add_realistic_tandem_loads function
- Purpose: Expand basic load cases beyond dead/wind
- Needs: Self-weight, UDL, pedestrian, environmental loads

INTEGRATION POINT 3: Tandem Load Cases (Line ~580)
- Location: _add_realistic_tandem_loads function
- Purpose: Enhance tandem load case metadata
- Needs: Position descriptions, DAF, filtering, fatigue variants

INTEGRATION POINT 4: Load Combinations - CRITICAL (Line ~590)
- Location: _add_realistic_tandem_loads function
- Purpose: Replace basic ULS/SLS with comprehensive EN 1990 combinations
- Needs: All combination types, envelope strategies, proper factors

INTEGRATION POINT 5: Results Classes (Line ~650)
- Location: _add_realistic_tandem_loads function
- Purpose: Future results processing integration
- Needs: BridgeAnalysisResults, ResultsProcessor, code checkers

INTEGRATION POINT 6: Return Structure (Line ~670)
- Location: _add_realistic_tandem_loads function
- Purpose: Enhance return data with metadata
- Needs: Combination metadata, critical combinations, analysis settings

INTEGRATION POINT 7: Load Zone Data (Line ~690)
- Location: create_bridge_scia_model function
- Purpose: Integrate params.input.belastingzones data
- Needs: Zone-specific load processing and mapping

INTEGRATION POINT 8: Results Processing (Line ~710)
- Location: create_bridge_scia_model function
- Purpose: Add complete results processing pipeline
- Needs: Analysis execution, code checks, report generation

INTEGRATION POINT 9: Load Case Metadata (Line ~340)
- Location: apply_tandem_loads_to_scia_model function
- Purpose: Enhance load case creation with metadata
- Needs: Priorities, DAF, filtering, position descriptions

INTEGRATION POINT 10: Enhanced Descriptions (Line ~360)
- Location: apply_tandem_loads_to_scia_model function
- Purpose: Add detailed load case descriptions
- Needs: Position info, magnitudes, analysis purpose

========================================================================
INTEGRATION PRIORITY & CHECKLIST
========================================================================

HIGH PRIORITY (Core Functionality):
[✅] Point 4: Load Combinations - IMPLEMENTED Dutch standard NEN 8700/8701 system
[ ] Point 1: Load Groups - Add comprehensive load group management
[ ] Point 2: Basic Load Cases - Expand beyond dead/wind loads

MEDIUM PRIORITY (Enhanced Functionality):
[ ] Point 7: Load Zone Data - Integrate params.input.belastingzones
[ ] Point 3: Tandem Load Cases - Add metadata and optimization
[ ] Point 9: Load Case Metadata - Enhance with priorities and DAF

LOW PRIORITY (Future Enhancements):
[ ] Point 8: Results Processing - Complete analysis pipeline
[ ] Point 5: Results Classes - Post-processing and code checks
[ ] Point 6: Return Structure - Enhanced metadata
[ ] Point 10: Enhanced Descriptions - Detailed load case info

SUGGESTED IMPLEMENTATION ORDER:
1. Start with Point 4 (Load Combinations) - This is the most critical
2. Implement Point 1 (Load Groups) to support combinations
3. Add Point 2 (Basic Load Cases) for comprehensive load modeling
4. Continue with medium priority items based on project needs

========================================================================
"""

import io
from io import BytesIO
from pathlib import Path
from typing import Any, TypeAlias

from src.combinations.load_factors import get_gamma_factors, get_psi_factor
from src.integrations.scia_utils import (
    create_load_case_complete,
    create_load_combination_by_type,
    create_load_group_by_type,
    create_patch_surface_load,
)
from src.loads.loadcase_helper_functions import (
    amount_of_notional_lanes,
    tandem_systems_axes_double_lane,
    tandem_systems_axes_more_lanes,
    tandem_systems_axes_single_lane,
)

# Type aliases
SciaNode: TypeAlias = object
SciaModel: TypeAlias = "SciaModelProtocol"


class SciaModelProtocol:
    """Protocol for SCIA model objects."""

    def create_node(self, name: str, x: float, y: float, z: float) -> "SciaNode":
        """Create a node in the SCIA model."""


class NodeTracker:
    """Helper to track and reuse nodes in SCIA model."""

    def __init__(self, scia_model: SciaModel) -> None:
        """Initialize the node tracker."""
        self.model = scia_model
        self._nodes_by_coords: dict[tuple[float, float, float], SciaNode] = {}
        self._nodes_by_name: dict[str, SciaNode] = {}

    def get_or_create_node(self, name: str, x: float, y: float, z: float) -> SciaNode:
        """Get existing node at coordinates or create new one."""
        coords = (x, y, z)

        if coords in self._nodes_by_coords:
            return self._nodes_by_coords[coords]

        node = self.model.create_node(name, x, y, z)
        self._nodes_by_coords[coords] = node
        self._nodes_by_name[name] = node
        return node

    def get_node_by_name(self, name: str) -> SciaNode:
        """Get node by name."""
        return self._nodes_by_name[name]


def create_node_and_thickness_dict(params: Any) -> tuple[dict[str, list[float]], dict[str, float]]:  # noqa: ANN401
    """
    Create node positions and thickness data from bridge parameters.

    :param params: Bridge parameters
    :returns: (nodes_dict, thickness_dict)
    """
    dynamic_arrays = len(params.bridge_segments_array)
    nodes_dict = {}
    thickness_dict = {}

    def calculate_cross_section_positions(segment_idx: int) -> dict[str, float]:
        """Calculate node positions for cross section."""
        l_sum = sum(item["l"] for item in params.bridge_segments_array[: segment_idx + 1])
        segment = params.bridge_segments_array[segment_idx]

        return {
            "x": l_sum,
            "z1_left": segment.bz1 + segment.bz2 / 2,
            "z1_right": segment.bz2 / 2,
            "z3_left": -segment.bz2 / 2,
            "z3_right": -segment.bz3 - segment.bz2 / 2,
        }

    # Create first cross section
    if dynamic_arrays > 0:
        pos = calculate_cross_section_positions(0)
        nodes_dict.update(
            {
                "K_dek:1_1": [pos["x"], pos["z1_left"], 0],
                "K_dek:1_2": [pos["x"], pos["z1_right"], 0],
                "K_dek:1_3": [pos["x"], pos["z3_left"], 0],
                "K_dek:1_4": [pos["x"], pos["z3_right"], 0],
            }
        )

    # Create remaining cross sections and thickness data
    for dynamic_array in range(1, dynamic_arrays):
        pos = calculate_cross_section_positions(dynamic_array)
        d_num = dynamic_array + 1

        nodes_dict.update(
            {
                f"K_dek:{d_num}_1": [pos["x"], pos["z1_left"], 0],
                f"K_dek:{d_num}_2": [pos["x"], pos["z1_right"], 0],
                f"K_dek:{d_num}_3": [pos["x"], pos["z3_left"], 0],
                f"K_dek:{d_num}_4": [pos["x"], pos["z3_right"], 0],
            }
        )

        thickness_dict.update(
            {
                f"Z1_{dynamic_array}": params.bridge_segments_array[dynamic_array].dz,
                f"Z2_{dynamic_array}": params.bridge_segments_array[dynamic_array].dz_2,
                f"Z3_{dynamic_array}": params.bridge_segments_array[dynamic_array].dz,
            }
        )

    return nodes_dict, thickness_dict


def extract_tandem_parameters_from_bridge(params: Any) -> dict[str, float]:  # noqa: ANN401
    """
    Extract parameters needed for src.loads.loadcase_helper_functions from bridge data.

    :param params: Bridge parameters
    :returns: Dictionary with length_bridgedeck, width_bridgedeck, thickness_bridgedeck
    :rtype: dict[str, float]
    :raises IndexError: When no bridge segments are provided
    """
    if not params.bridge_segments_array:
        raise IndexError("No bridge segments provided")

    # Calculate total bridge length (cumulative sum of segment lengths)
    length_bridgedeck = sum(segment.l for segment in params.bridge_segments_array)

    # Calculate total bridge width from first segment (bz1 + bz2 + bz3)
    first_segment = params.bridge_segments_array[0]
    width_bridgedeck = first_segment.bz1 + first_segment.bz2 + first_segment.bz3

    # Use thickness from first segment (dz)
    thickness_bridgedeck = first_segment.dz

    return {
        "length_bridgedeck": length_bridgedeck,
        "width_bridgedeck": width_bridgedeck,
        "thickness_bridgedeck": thickness_bridgedeck,
    }


def determine_tandem_function_for_bridge(bridge_dims: dict[str, float]) -> dict[str, Any]:
    """
    Determine which tandem function to use based on bridge width.

    :param bridge_dims: Bridge dimensions dictionary
    :returns: Dictionary with function_name and lane_count
    :rtype: dict[str, Any]
    :raises ValueError: When bridge width is invalid
    """
    width = bridge_dims["width_bridgedeck"]

    if width <= 0:
        raise ValueError("Invalid bridge width")

    lane_count, _ = amount_of_notional_lanes(width)

    if lane_count == 1:
        function_name = "tandem_systems_axes_single_lane"
    elif lane_count == 2:
        function_name = "tandem_systems_axes_double_lane"
    else:
        function_name = "tandem_systems_axes_more_lanes"

    return {
        "function_name": function_name,
        "lane_count": lane_count,
    }


def generate_tandem_loads_for_bridge(bridge_params: dict[str, float]) -> list[dict[str, Any]]:
    """
    Generate tandem loads using appropriate loadcase_helper function.

    :param bridge_params: Bridge parameters dictionary with length, width, thickness
    :returns: List of tandem load data
    :rtype: list[dict[str, Any]]
    :raises KeyError: When required bridge parameters are missing
    """
    required_keys = ["length_bridgedeck", "width_bridgedeck", "thickness_bridgedeck"]
    for key in required_keys:
        if key not in bridge_params:
            raise KeyError(f"Missing required parameter: {key}")

    length = bridge_params["length_bridgedeck"]
    width = bridge_params["width_bridgedeck"]
    thickness = bridge_params["thickness_bridgedeck"]

    # Determine which function to use
    tandem_config = determine_tandem_function_for_bridge(bridge_params)
    function_name = tandem_config["function_name"]

    # Call appropriate tandem function
    if function_name == "tandem_systems_axes_single_lane":
        return tandem_systems_axes_single_lane(length, width, thickness)
    if function_name == "tandem_systems_axes_double_lane":
        return tandem_systems_axes_double_lane(length, width, thickness)
    # tandem_systems_axes_more_lanes
    return tandem_systems_axes_more_lanes(length, width, thickness)


def convert_wheel_coordinates_to_3d(wheel_2d: list[list[float]]) -> list[tuple[float, float, float]]:
    """
    Convert 2D wheel coordinates to 3D SCIA coordinates.

    :param wheel_2d: List of [x, y] coordinates
    :returns: List of (x, y, z) tuples with z=0
    :rtype: list[tuple[float, float, float]]
    """
    return [(x, y, 0.0) for x, y in wheel_2d]


def align_bridge_coordinates_to_scia(
    bridge_coords: list[tuple[float, float, float]], _bridge_dims: dict[str, float]
) -> list[tuple[float, float, float]]:
    """
    Align bridge coordinate system to SCIA model coordinate system.

    Currently maintains coordinates as-is. Future enhancement could map
    bridge edge coordinates to SCIA zone boundaries.

    :param bridge_coords: Bridge coordinates
    :param _bridge_dims: Bridge dimensions for reference (unused)
    :returns: SCIA-aligned coordinates
    :rtype: list[tuple[float, float, float]]
    """
    # For now, maintain coordinates as-is
    # Future: map Y coordinates from bridge edge system to SCIA zone system
    return bridge_coords


def convert_tandem_data_to_scia_format(tandem_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Convert tandem data to SCIA patch load format.

    Handles both single lane and multi-lane tandem data formats.

    :param tandem_data: Tandem load data from src.loads.loadcase_helper_functions
    :returns: SCIA-formatted load case data
    :rtype: list[dict[str, Any]]
    :raises KeyError: When tandem data structure is invalid
    """
    scia_load_cases = []

    for tandem in tandem_data:
        if "load_case" not in tandem:
            raise KeyError("Missing 'load_case' in tandem data")

        load_case_name = tandem["load_case"]
        patch_loads = []

        # Handle single lane format: {load_case, wheels, load}
        if "wheels" in tandem and "load" in tandem:
            wheels = tandem["wheels"]
            load_value = tandem["load"]

            for wheel_coords in wheels:
                corners_3d = convert_wheel_coordinates_to_3d(wheel_coords)
                patch_loads.append(
                    {
                        "corners": corners_3d,
                        "load_value": load_value,
                    }
                )

        # Handle multi-lane format: {load_case, tandems}
        elif "tandems" in tandem:
            for lane_tandem in tandem["tandems"]:
                if "wheels" not in lane_tandem or "load" not in lane_tandem:
                    raise KeyError("Missing 'wheels' or 'load' in lane tandem data")

                wheels = lane_tandem["wheels"]
                load_value = lane_tandem["load"]

                for wheel_coords in wheels:
                    corners_3d = convert_wheel_coordinates_to_3d(wheel_coords)
                    patch_loads.append(
                        {
                            "corners": corners_3d,
                            "load_value": load_value,
                        }
                    )
        else:
            raise KeyError("Invalid tandem data structure: missing 'wheels' or 'tandems'")

        scia_load_cases.append(
            {
                "load_case": load_case_name,
                "patch_loads": patch_loads,
            }
        )

    return scia_load_cases


def apply_tandem_loads_to_scia_model(
    model: SciaModel,
    scia_tandem_data: list[dict[str, Any]],
    load_group: Any,  # noqa: ANN401
) -> list[Any]:
    """
    Apply tandem loads to SCIA model using existing framework.

    :param model: SCIA model instance
    :param scia_tandem_data: SCIA-formatted tandem load data
    :param load_group: SCIA load group for the load cases
    :returns: List of created SCIA load cases
    :rtype: list[Any]
    """
    # ========================================================================
    # COLLEAGUE INTEGRATION POINT 9: LOAD CASE METADATA ENHANCEMENT
    # ========================================================================
    # TODO: Enhance load case creation with metadata and optimization
    # CURRENT: Basic load case creation with simple naming
    # READY FOR ENHANCEMENT: Your colleague can extend to add:
    # - Load case priorities (critical vs. non-critical positions)
    # - Position descriptions ("Mid-span critical", "Support region", etc.)
    # - Dynamic amplification factors (DAF) based on bridge natural frequency
    # - Load case filtering (only create most critical cases for optimization)
    # - Fatigue load case variants with cycle counting
    # - Integration with influence line analysis for critical positioning

    load_cases = []

    for load_case_data in scia_tandem_data:
        load_case_name = load_case_data["load_case"]
        patch_loads = load_case_data["patch_loads"]

        # ========================================================================
        # COLLEAGUE INTEGRATION POINT 10: ENHANCED LOAD CASE DESCRIPTIONS
        # ========================================================================
        # CURRENT: Simple description with load case name
        # ENHANCEMENT OPPORTUNITY: Add detailed descriptions:
        # - Position information (x-coordinate, critical section)
        # - Load magnitude and configuration
        # - Analysis purpose (ULS, SLS, fatigue)
        # - Load case dependencies or relationships

        # Create load case for this tandem configuration
        description = f"Load Model 1 - Tandem system {load_case_name}"
        load_case = create_load_case_complete(model, load_group, load_case_name, description, "VARIABLE", variable_type="STATIC", duration="SHORT")

        # Apply all patch loads for this load case
        for i, patch_load in enumerate(patch_loads):
            corners = patch_load["corners"]
            load_value = patch_load["load_value"]
            load_name = f"{load_case_name}_Wheel_{i + 1}"

            # Apply loads as negative values to point downward (correct direction for bridge loads)
            create_patch_surface_load(model, load_case, corners, -load_value, load_name)

        load_cases.append(load_case)

    return load_cases


def create_simple_scia_plate_model(params: Any) -> tuple[BytesIO, BytesIO]:  # noqa: ANN401
    """
    Create SCIA bridge model with multi-zone plates.

    Creates:
    - Cross-sections at each bridge segment
    - Three zone plates (Zone 1, 2, 3) with variable thickness
    - Demonstration loads using scia_utils framework

    Coordinate system:
    - X: Longitudinal (cumulative segment lengths)
    - Y: Transverse (zone boundaries from bz1, bz2, bz3)
    - Z: Vertical (0 at top surface)

    Zone layout: Zone 3 | Zone 2 | Zone 1
                |--bz3--|--bz2--|--bz1--|

    :param params: Bridge parameters
    :returns: (xml_file, def_file) for SCIA analysis
    """
    try:
        from viktor.external import scia
    except ImportError as e:
        raise ImportError("VIKTOR SCIA module not available. This function requires VIKTOR SDK.") from e

    # Create model and material
    model = scia.Model()
    node_tracker = NodeTracker(model)
    material = scia.Material(0, "C30/37")

    # Get geometry data
    nodes_dict, thickness_dict = create_node_and_thickness_dict(params)
    dynamic_arrays = len(params.bridge_segments_array)
    scia_nodes = {}

    # Create initial cross section nodes
    for node_suffix in range(1, 5):
        node_name = f"K_dek:1_{node_suffix}"
        coords = nodes_dict.get(node_name)
        if coords is None:
            raise ValueError(f"Coordinates for node '{node_name}' not found.")
        scia_nodes[node_name] = node_tracker.get_or_create_node(node_name, coords[0], coords[1], coords[2])

    # Create plates between cross sections
    for span in range(1, dynamic_arrays):
        next_span = span + 1

        # Create next cross section nodes
        for node_suffix in range(1, 5):
            node_name = f"K_dek:{next_span}_{node_suffix}"
            if node_name not in scia_nodes:
                coords = nodes_dict.get(node_name)
                if coords is None:
                    raise ValueError(f"Coordinates for node '{node_name}' not found.")
                scia_nodes[node_name] = node_tracker.get_or_create_node(node_name, coords[0], coords[1], coords[2])

        # Create zone plates
        # Zone 1 plate
        corner_nodes_z1 = [
            scia_nodes[f"K_dek:{span}_1"],
            scia_nodes[f"K_dek:{next_span}_1"],
            scia_nodes[f"K_dek:{next_span}_2"],
            scia_nodes[f"K_dek:{span}_2"],
        ]
        model.create_plane(corner_nodes_z1, thickness_dict.get(f"Z1_{span}"), name=f"Z1_{span}", material=material)

        # Zone 3 plate
        corner_nodes_z3 = [
            scia_nodes[f"K_dek:{span}_3"],
            scia_nodes[f"K_dek:{next_span}_3"],
            scia_nodes[f"K_dek:{next_span}_4"],
            scia_nodes[f"K_dek:{span}_4"],
        ]
        model.create_plane(corner_nodes_z3, thickness_dict.get(f"Z3_{span}"), name=f"Z3_{span}", material=material)

        # Zone 2 plate
        corner_nodes_z2 = [
            scia_nodes[f"K_dek:{span}_2"],
            scia_nodes[f"K_dek:{next_span}_2"],
            scia_nodes[f"K_dek:{next_span}_3"],
            scia_nodes[f"K_dek:{span}_3"],
        ]
        model.create_plane(corner_nodes_z2, thickness_dict.get(f"Z2_{span}"), name=f"Z2_{span}", material=material)

    # Add realistic tandem loads based on bridge parameters
    _add_realistic_tandem_loads(model, params)

    return model.generate_xml_input()


def _create_dutch_standard_load_combinations(
    model: SciaModel,
    dead_load_case: Any,  # noqa: ANN401
    traffic_load_cases: list[Any],
    wind_case: Any,  # noqa: ANN401
    bridge_span: float,
    consequence_class: str = "CC2",
    safety_level: str = "NEN 8700 gebruik",
    construction_year: str = "2010",
) -> dict[str, Any]:
    """
    Create Dutch standard load combinations according to NEN 8700/8701.

    Generates load combinations using proper gamma factors (NEN 8700) and psi factors
    (NEN 8701) for bridge analysis. Replaces basic EN 1990 combinations with Dutch
    standards compliant combinations.

    :param model: SCIA model instance
    :param dead_load_case: Dead load case object
    :param traffic_load_cases: List of traffic load case objects
    :param wind_case: Wind load case object
    :param bridge_span: Bridge span length for psi factor calculation
    :param consequence_class: Consequence class (CC1a/b, CC2, CC3)
    :param safety_level: Safety assessment level
    :param construction_year: Year of construction for material factors
    :returns: Dictionary with created load combinations
    :rtype: dict[str, Any]
    """
    try:
        # Get gamma factors from NEN 8700 based on project parameters
        gamma_factors = get_gamma_factors(cc=consequence_class, safety_level=safety_level, building_year=construction_year)

        # Get psi factor from NEN 8701 based on bridge span (assuming 50 year reference period)
        psi_traffic = get_psi_factor(span=bridge_span, reference_period=50.0)

        combinations = {}

        # Create combination sets for both 6.10a and 6.10b
        for combo_type in ["6.10a", "6.10b"]:
            gamma_set = gamma_factors[combo_type]

            # ULS Combination 1: Dead + Leading Traffic
            if traffic_load_cases:
                primary_traffic = traffic_load_cases[0]
                uls_1_factors = {
                    dead_load_case: gamma_set["gamma_Gjsup"],
                    primary_traffic: gamma_set["gamma_Qverkeer"],
                }

                # Add accompanying traffic loads with psi factor
                for traffic_case in traffic_load_cases[1:]:
                    uls_1_factors[traffic_case] = gamma_set["gamma_Qverkeer"] * psi_traffic

                uls_1 = create_load_combination_by_type(
                    model, "ULS", f"ULS_{combo_type}_G+Q_Traffic", uls_1_factors, f"ULS {combo_type}: Dead + Traffic (NEN 8700/8701)"
                )
                combinations[f"uls_{combo_type}_traffic"] = uls_1

            # ULS Combination 2: Dead + Leading Traffic + Accompanying Wind
            if traffic_load_cases and wind_case:
                primary_traffic = traffic_load_cases[0]
                uls_2_factors = {
                    dead_load_case: gamma_set["gamma_Gjsup"],
                    primary_traffic: gamma_set["gamma_Qverkeer"],
                    wind_case: gamma_set["gamma_Qwind"] * 0.6,  # psi_0 for wind = 0.6
                }

                uls_2 = create_load_combination_by_type(
                    model, "ULS", f"ULS_{combo_type}_G+Q_Traffic+Wind", uls_2_factors, f"ULS {combo_type}: Dead + Traffic + Wind (NEN 8700/8701)"
                )
                combinations[f"uls_{combo_type}_traffic_wind"] = uls_2

            # ULS Combination 3: Dead + Leading Wind + Accompanying Traffic
            if traffic_load_cases and wind_case:
                primary_traffic = traffic_load_cases[0]
                uls_3_factors = {
                    dead_load_case: gamma_set["gamma_Gjsup"],
                    wind_case: gamma_set["gamma_Qwind"],
                    primary_traffic: gamma_set["gamma_Qverkeer"] * psi_traffic,
                }

                uls_3 = create_load_combination_by_type(
                    model, "ULS", f"ULS_{combo_type}_G+Wind+Q_Traffic", uls_3_factors, f"ULS {combo_type}: Dead + Wind + Traffic (NEN 8700/8701)"
                )
                combinations[f"uls_{combo_type}_wind_traffic"] = uls_3

            # SLS Characteristic Combination: Dead + Traffic
            if traffic_load_cases:
                primary_traffic = traffic_load_cases[0]
                sls_char_factors = {
                    dead_load_case: 1.0,  # No factor for dead loads in SLS
                    primary_traffic: 1.0,  # Characteristic value
                }

                # Add accompanying traffic loads with psi factor
                for traffic_case in traffic_load_cases[1:]:
                    sls_char_factors[traffic_case] = psi_traffic

                sls_char = create_load_combination_by_type(
                    model,
                    "SLS_CHAR",
                    f"SLS_CHAR_{combo_type}_G+Q_Traffic",
                    sls_char_factors,
                    f"SLS Characteristic {combo_type}: Dead + Traffic (NEN 8700/8701)",
                )
                combinations[f"sls_char_{combo_type}"] = sls_char

            # SLS Frequent Combination: Dead + Frequent Traffic
            if traffic_load_cases:
                primary_traffic = traffic_load_cases[0]
                psi1_traffic = 0.75  # ψ₁ for traffic from EN 1991-2

                sls_freq_factors = {
                    dead_load_case: 1.0,
                    primary_traffic: psi1_traffic,
                }

                sls_freq = create_load_combination_by_type(
                    model,
                    "SLS_FREQ",
                    f"SLS_FREQ_{combo_type}_G+Psi1_Q",
                    sls_freq_factors,
                    f"SLS Frequent {combo_type}: Dead + ψ₁×Traffic (NEN 8700/8701)",
                )
                combinations[f"sls_freq_{combo_type}"] = sls_freq

        return combinations

    except Exception as e:
        # Fallback to basic combinations if Dutch standard combinations fail
        print(f"DEBUG: Dutch standard combinations failed: {e}")
        print("DEBUG: Falling back to basic combinations")

        # Create basic fallback combinations
        if traffic_load_cases:
            primary_traffic = traffic_load_cases[0]
            uls_basic = create_load_combination_by_type(
                model, "ULS", "ULS_Basic_G+Q", {dead_load_case: 1.35, primary_traffic: 1.5}, "Basic ULS: Dead + Traffic (Fallback)"
            )
            sls_basic = create_load_combination_by_type(
                model, "SLS_CHAR", "SLS_Basic_G+Q", {dead_load_case: 1.0, primary_traffic: 1.0}, "Basic SLS: Dead + Traffic (Fallback)"
            )
            return {"uls_basic": uls_basic, "sls_basic": sls_basic}

        return {}


def _add_dummy_wheel_loads(model: SciaModel) -> dict[str, Any]:
    """
    DEPRECATED: Replaced by _add_realistic_tandem_loads.

    Legacy demonstration load framework from scia_utils.
    Shows 4-step workflow for reference but no longer used in production.

    Use _add_realistic_tandem_loads instead for actual bridge analysis.
    """
    # Create load groups
    permanent_group = create_load_group_by_type(model, "PERMANENT", "LG_Permanent")
    traffic_group = create_load_group_by_type(model, "VARIABLE", "LG_Traffic")
    wind_group = create_load_group_by_type(model, "VARIABLE", "LG_Wind")

    # Create load cases
    dead_load_case = create_load_case_complete(
        model, permanent_group, "G1_DeadLoad", "Superimposed dead load", "PERMANENT", permanent_type="STANDARD"
    )

    lm1_case = create_load_case_complete(
        model, traffic_group, "Q1_LM1", "Load Model 1 - Tandem + UDL", "VARIABLE", variable_type="STATIC", duration="SHORT"
    )

    wind_case = create_load_case_complete(
        model, wind_group, "Q2_Wind", "Wind Load", "VARIABLE", variable_type="STATIC", specification="STATIC_WIND", duration="SHORT"
    )

    # Create load combinations (EN 1990 factors)
    uls_basic = create_load_combination_by_type(model, "ULS", "ULS_1_G+LM1", {dead_load_case: 1.35, lm1_case: 1.5})

    uls_wind = create_load_combination_by_type(model, "ULS", "ULS_2_G+LM1+W", {dead_load_case: 1.35, lm1_case: 1.5, wind_case: 1.5 * 0.6})

    sls_char = create_load_combination_by_type(model, "SLS_CHAR", "SLS_Char_G+LM1", {dead_load_case: 1.0, lm1_case: 1.0})

    # Apply LM1 tandem loads (dummy positions)
    wheel_1_corners = [(10.0, 1.8, 0.0), (10.4, 1.8, 0.0), (10.4, 2.2, 0.0), (10.0, 2.2, 0.0)]
    wheel_2_corners = [(10.0, -0.2, 0.0), (10.4, -0.2, 0.0), (10.4, 0.2, 0.0), (10.0, 0.2, 0.0)]
    wheel_3_corners = [(11.2, 1.8, 0.0), (11.6, 1.8, 0.0), (11.6, 2.2, 0.0), (11.2, 2.2, 0.0)]
    wheel_4_corners = [(11.2, -0.2, 0.0), (11.6, -0.2, 0.0), (11.6, 0.2, 0.0), (11.2, 0.2, 0.0)]

    # 300kN/0.16m² = 1,875,000 N/m², 200kN/0.16m² = 1,250,000 N/m²
    create_patch_surface_load(model, lm1_case, wheel_1_corners, -1875000.0, "LM1_Axle1_Wheel1")
    create_patch_surface_load(model, lm1_case, wheel_2_corners, -1875000.0, "LM1_Axle1_Wheel2")
    create_patch_surface_load(model, lm1_case, wheel_3_corners, -1250000.0, "LM1_Axle2_Wheel1")
    create_patch_surface_load(model, lm1_case, wheel_4_corners, -1250000.0, "LM1_Axle2_Wheel2")

    return {
        "load_groups": {"permanent": permanent_group, "traffic": traffic_group, "wind": wind_group},
        "load_cases": {"dead_load": dead_load_case, "lm1": lm1_case, "wind": wind_case},
        "combinations": {"uls_basic": uls_basic, "uls_wind": uls_wind, "sls_char": sls_char},
    }


def _add_realistic_tandem_loads(model: SciaModel, params: Any) -> dict[str, Any]:  # noqa: ANN401
    """
    Apply realistic tandem loads to SCIA model from bridge parameters.

    Replaces _add_dummy_wheel_loads with loads generated from src.loads.loadcase_helper_functions
    using actual bridge geometry and dimensions.

    :param model: SCIA model instance
    :param params: Bridge parameters
    :returns: Dictionary with load_groups, load_cases, combinations (compatible with dummy loads)
    :rtype: dict[str, Any]
    """
    # Extract bridge parameters for tandem load generation
    bridge_params = extract_tandem_parameters_from_bridge(params)

    # Generate tandem loads using src.loads.loadcase_helper_functions
    raw_tandem_data = generate_tandem_loads_for_bridge(bridge_params)

    # Convert to SCIA format
    scia_tandem_data = convert_tandem_data_to_scia_format(raw_tandem_data)

    # ========================================================================
    # COLLEAGUE INTEGRATION POINT 1: LOAD GROUPS
    # ========================================================================
    # TODO: Replace basic load groups with comprehensive EN 1990 load groups
    # CURRENT: Simple permanent/traffic/wind groups
    # NEEDED: Your colleague should integrate sophisticated load group management
    # - Multiple variable load groups (traffic, pedestrian, wind, thermal, etc.)
    # - Proper load group relationships (exclusive, standard, together)
    # - Load group categorization (Cat A, B, C, D, E)
    # - Integration with params.input.belastingzones if available

    # Create load groups (maintain compatibility with existing structure)
    permanent_group = create_load_group_by_type(model, "PERMANENT", "LG_Permanent")
    traffic_group = create_load_group_by_type(model, "VARIABLE", "LG_Traffic")
    wind_group = create_load_group_by_type(model, "VARIABLE", "LG_Wind")

    # ========================================================================
    # COLLEAGUE INTEGRATION POINT 2: BASIC LOAD CASES
    # ========================================================================
    # TODO: Expand basic load case creation with comprehensive load case management
    # CURRENT: Simple dead load and wind load cases
    # NEEDED: Your colleague should add:
    # - Dead load variants (self-weight, superimposed dead loads, equipment)
    # - Live load cases beyond tandem (UDL, pedestrian, special vehicles)
    # - Environmental loads (wind profiles, thermal gradients, settlement)
    # - Load case metadata (duration, dynamic factors, partial factors)
    # - Integration with bridge-specific load requirements

    # Create basic load cases (maintain compatibility)
    dead_load_case = create_load_case_complete(
        model, permanent_group, "G1_DeadLoad", "Superimposed dead load", "PERMANENT", permanent_type="STANDARD"
    )

    wind_case = create_load_case_complete(
        model, wind_group, "Q2_Wind", "Wind Load", "VARIABLE", variable_type="STATIC", specification="STATIC_WIND", duration="SHORT"
    )

    # ========================================================================
    # COLLEAGUE INTEGRATION POINT 3: TANDEM LOAD CASES
    # ========================================================================
    # CURRENT: All tandem load cases applied with basic settings
    # READY FOR ENHANCEMENT: Your colleague can extend this section to:
    # - Add load case metadata (position descriptions, critical sections)
    # - Implement load case filtering/optimization (critical cases only)
    # - Add dynamic amplification factors
    # - Integrate with fatigue load models
    # - Add special tandem configurations (emergency vehicles, permit loads)

    # Apply realistic tandem loads
    tandem_load_cases = apply_tandem_loads_to_scia_model(model, scia_tandem_data, traffic_group)

    # ========================================================================
    # INTEGRATION POINT 4: DUTCH STANDARD LOAD COMBINATIONS (NEN 8700/8701)
    # ========================================================================
    # ✅ IMPLEMENTED: Dutch standard load combinations with proper factors
    # REPLACED: Basic EN 1990 combinations with NEN 8700/8701 compliant system
    # FEATURES:
    # - Gamma factors from NEN 8700 based on consequence class and safety level
    # - Psi factors from NEN 8701 based on bridge span and reference period
    # - Both 6.10a and 6.10b combination equations
    # - ULS combinations (dead+traffic, dead+traffic+wind, dead+wind+traffic)
    # - SLS combinations (characteristic, frequent)
    # - Proper accompanying load factors with psi values
    # - Fallback to basic combinations if Dutch standards fail

    # Calculate bridge span for psi factor determination
    bridge_span = bridge_params["length_bridgedeck"]

    # Create Dutch standard load combinations
    # TODO: FUTURE ENHANCEMENT - Make these parameters configurable from bridge params:
    # - consequence_class: Extract from params.bridge.consequence_class or params.input.cc_class
    # - safety_level: Extract from params.bridge.design_code or params.input.design_code
    # - construction_year: Extract from params.bridge.construction_year or params.info.construction_year
    combinations = _create_dutch_standard_load_combinations(
        model=model,
        dead_load_case=dead_load_case,
        traffic_load_cases=tandem_load_cases,
        wind_case=wind_case,
        bridge_span=bridge_span,
        consequence_class="CC2",  # Default consequence class
        safety_level="NEN 8700 gebruik",  # Default safety level
        construction_year="2010",  # Default construction year
    )

    # ========================================================================
    # COLLEAGUE INTEGRATION POINT 5: RESULTS CLASSES (FUTURE)
    # ========================================================================
    # TODO: When colleague implements results processing, add results integration here
    # SUGGESTED INTERFACE:
    # - BridgeAnalysisResults class to store/process SCIA output
    # - ResultsProcessor class for post-processing (code checks, utilization)
    # - ReportGenerator class for automated report generation
    # INTEGRATION LOCATION: After model.generate_xml_input() in main function
    # RETURN EXTENSION: Add "results_config" to return dictionary

    # Build load cases dictionary
    load_cases = {
        "dead_load": dead_load_case,
        "wind": wind_case,
    }

    # Add all tandem load cases
    for i, tandem_case in enumerate(tandem_load_cases):
        load_cases[f"tandem_{i + 1}"] = tandem_case

    # ========================================================================
    # COLLEAGUE INTEGRATION POINT 6: RETURN STRUCTURE ENHANCEMENT
    # ========================================================================
    # CURRENT: Basic compatibility structure
    # READY FOR EXTENSION: Your colleague can add:
    # - "combination_metadata": {...} - Combination descriptions and factors
    # - "critical_combinations": [...] - Pre-identified critical combinations
    # - "load_case_mapping": {...} - BG6001 → description mapping
    # - "analysis_settings": {...} - Analysis parameters and options
    # - "results_config": {...} - Results processing configuration

    return {
        "load_groups": {"permanent": permanent_group, "traffic": traffic_group, "wind": wind_group},
        "load_cases": load_cases,
        "combinations": combinations,
    }


def create_scia_analysis_from_template(xml_file: io.BytesIO, def_file: io.BytesIO, template_path: Path) -> Any:  # noqa: ANN401
    """
    Create SCIA analysis using template file.

    :param xml_file: Generated XML input file
    :param def_file: Generated definition file
    :param template_path: Path to ESA template
    :returns: SCIA analysis object
    """
    try:
        from viktor.core import File
        from viktor.external import scia
    except ImportError as e:
        raise ImportError("VIKTOR SCIA module not available. This function requires VIKTOR SDK.") from e

    if not template_path.exists():
        raise FileNotFoundError(f"SCIA template file not found: {template_path}")

    esa_template = File.from_path(template_path)
    return scia.SciaAnalysis(xml_file, def_file, esa_template)


def create_bridge_scia_model(params: Any, template_path: Path) -> tuple[Any, Any, Any]:  # noqa: ANN401
    """
    Main function to create complete SCIA model from bridge parameters.

    Creates geometry from bridge_segments_array and sets up analysis with template.

    :param params: Bridge parameters
    :param template_path: Path to ESA template file
    :returns: (xml_file, def_file, scia_analysis)
    """
    # ========================================================================
    # COLLEAGUE INTEGRATION POINT 7: LOAD ZONE DATA INTEGRATION
    # ========================================================================
    # TODO: Integrate with load zone data from params.input.belastingzones for realistic loads.
    # CURRENT: Only using tandem loads from src.loads.loadcase_helper_functions
    # NEEDED: Your colleague should add integration for:
    # - params.input.belastingzones data processing
    # - Zone-specific load application (different loads per bridge zone)
    # - Load distribution algorithms across bridge segments
    # - Zone-to-SCIA coordinate mapping
    # - Multi-zone load combination strategies
    # INTEGRATION LOCATION: In _add_realistic_tandem_loads function - Point 1

    xml_file, def_file = create_simple_scia_plate_model(params)
    scia_analysis = create_scia_analysis_from_template(xml_file, def_file, template_path)

    # ========================================================================
    # COLLEAGUE INTEGRATION POINT 8: RESULTS PROCESSING INTEGRATION
    # ========================================================================
    # TODO: Add results processing pipeline after SCIA analysis creation
    # SUGGESTED IMPLEMENTATION:
    #
    # from src.results.bridge_results import BridgeAnalysisResults, ResultsProcessor  # noqa: ERA001
    # from src.results.code_checks import EurocodeChecker, UtilizationCalculator  # noqa: ERA001
    # from src.results.report_generator import AutomatedReportGenerator  # noqa: ERA001
    #
    # # Execute analysis and get results
    # if enable_analysis_execution:
    #     try:  # noqa: ERA001
    #         scia_analysis.execute(timeout=600)  # 10 minutes max  # noqa: ERA001
    #         results_data = scia_analysis.get_results()  # noqa: ERA001
    #
    #         # Process results
    #         bridge_results = BridgeAnalysisResults(results_data, bridge_geometry=params)  # noqa: ERA001
    #         processor = ResultsProcessor(bridge_results)  # noqa: ERA001
    #
    #         # Perform code checks
    #         checker = EurocodeChecker(processor)  # noqa: ERA001
    #         code_check_results = checker.perform_checks()  # noqa: ERA001
    #
    #         # Calculate utilization ratios
    #         utilization = UtilizationCalculator(processor)  # noqa: ERA001
    #         utilization_results = utilization.calculate_all()  # noqa: ERA001
    #
    #         # Generate automated report
    #         report_gen = AutomatedReportGenerator(bridge_results, code_check_results, utilization_results)  # noqa: ERA001
    #         report_file = report_gen.generate_report()  # noqa: ERA001
    #
    #         return xml_file, def_file, scia_analysis, bridge_results, report_file  # noqa: ERA001
    #     except Exception as e:  # noqa: ERA001
    #         # Analysis failed - return model files only
    #         return xml_file, def_file, scia_analysis, None, None  # noqa: ERA001
    #
    # CLASSES TO IMPLEMENT:
    # - BridgeAnalysisResults: Parse and store SCIA results (forces, moments, displacements)
    # - ResultsProcessor: Post-process results (max/min values, critical sections)
    # - EurocodeChecker: Automated code compliance checks (EN 1992-2, EN 1991-2)
    # - UtilizationCalculator: Capacity/demand ratios for all critical sections
    # - AutomatedReportGenerator: PDF report generation with plots and tables
    #
    # RETURN STRUCTURE EXTENSION:
    # Current: (xml_file, def_file, scia_analysis)  # noqa: ERA001
    # Enhanced: (xml_file, def_file, scia_analysis, bridge_results, report_file)  # noqa: ERA001

    return xml_file, def_file, scia_analysis
