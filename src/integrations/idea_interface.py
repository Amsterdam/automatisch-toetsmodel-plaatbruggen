"""
IDEA StatiCa Concrete integration module for bridge cross-section analysis.

This module provides functionality to create IDEA StatiCa models from bridge parameters.
Currently implements a simple rectangular beam model as a starting point.

Future enhancements needed:
- Support for complex bridge cross-sections (T-beams, box girders)
- Variable reinforcement configurations per zone
- Multiple load cases and combinations
- Different member types (slabs, compression members)
- Integration with bridge geometry for automatic cross-section selection
"""

from typing import Any

from viktor.external import idea_rcs

from app.bridge.parametrization import (
    BridgeParametrization,
)
from src.integrations.scia_integration.scia_bridge_geometry import create_node_and_thickness_dict


def _get_unique_matching_zone_keys(
    params: BridgeParametrization,
) -> tuple[
    list[tuple[float, str]],
    dict[float, list[str]],
    dict[float, list[str]],
]:
    """
    Extract unique matching zone keys from bridge parameters.

    This function groups reinforcement zones by their zone number and matches them with
    the corresponding thickness zones extracted from the bridge parameters.

    :param params: BridgeParametrization object containing all bridge input parameters
    :type params: BridgeParametrization
    :returns: List of unique (thickness, config) tuples for matching zones
    :rtype: list[tuple[float, str]]
    """
    # Extract zone thickness data from bridge parameters
    nodes_dict, thickness_dict = create_node_and_thickness_dict(params)

    # Group thickness_dict keys [zones] by their value [thickness] -> dict[thickness, list[zones]]
    grouped_thickness: dict[float, list[str]] = {}
    for key, value in thickness_dict.items():
        grouped_thickness.setdefault(value, []).append(key[1:].replace("_", "-"))  # to get zone format from Z1_1 to 1-1

    # Group reinforcement zones by their zone number
    grouped_rebar_configs: dict[float, list[str]] = {}
    i = 1
    for rebar_config in params.reinforcement_zones_array:
        grouped_rebar_configs[i] = rebar_config.get("zone_number")
        i += 1

    # Find matching thickness and reinforcement zone numbers
    matching_zone_keys: list[tuple[float, str]] = []
    for thickness, thickness_zones in grouped_thickness.items():
        for thickness_zone in thickness_zones:
            for config, rebar_zones in grouped_rebar_configs.items():
                for rebar_zone in rebar_zones:  # ignore PERF401
                    if thickness_zone == rebar_zone:
                        matching_zone_keys.append((thickness, str(config)))  # noqa: PERF401
    # Filter matching_zone_keys to only unique (thickness, config) pairs
    unique_matching_zone_keys = list({(thickness, config) for thickness, config in matching_zone_keys})
    return unique_matching_zone_keys, grouped_thickness, grouped_rebar_configs


def calculate_rebar_positions(width: float, hoh: float, y_offset: float = 0) -> list[float]:
    """Calculate positions for longitudinal reinforcement."""
    n_rebars = int(width / hoh)  # Round down to ensure minimum hoh is maintained
    if n_rebars < 1:
        return []

    actual_hoh = width / n_rebars
    positions = []

    if n_rebars % 2 == 0:  # Even number of rebars
        for i in range(n_rebars // 2):
            offset = (i + 0.5) * actual_hoh
            positions.extend([-offset, offset])
    else:  # Odd number of rebars
        positions = [0]  # Center rebar
        for i in range(1, (n_rebars + 1) // 2):
            offset = i * actual_hoh
            positions.extend([-offset, offset])

    positions.sort()
    return [pos + y_offset for pos in positions]


def calculate_bijleg_positions(positions: list[float], y_offset: float = 0) -> list[float]:
    """Calculate positions for bijlegwapening (additional reinforcement) by finding midpoints between main reinforcement."""
    if len(positions) < 2:
        return []

    # Calculate midpoint between each pair of consecutive positions
    bijleg_positions = []
    for i in range(len(positions) - 1):
        midpoint = (positions[i] + positions[i + 1]) / 2.0
        bijleg_positions.append(midpoint)

    # Add y_offset to all positions
    return [pos + y_offset for pos in bijleg_positions]


def _get_rebar_config(rebar_config: dict, params: BridgeParametrization, slab_thickness: float):
    """Get reinforcement configuration based on the provided viktor parameters."""
    # reinforcement cover (dekking) is the distance from the concrete surface to the reinforcement
    top_reinf_cover = params.input.geometrie_wapening.dekking_boven
    bottom_reinf_cover = params.input.geometrie_wapening.dekking_onder

    # Get needed reinforcement data in mm
    main_reinf_diameters = {
        "top_langs": rebar_config.get("hoofdwapening_langs_boven_diameter"),
        "top_dwars": rebar_config.get("hoofdwapening_dwars_boven_diameter"),
        "bottom_langs": rebar_config.get("hoofdwapening_langs_onder_diameter"),
        "bottom_dwars": rebar_config.get("hoofdwapening_dwars_onder_diameter"),
    }

    # Get center to center distances in mm
    main_reinf_ctc_distances = {
        "top_langs": rebar_config.get("hoofdwapening_langs_boven_hart_op_hart"),
        "top_dwars": rebar_config.get("hoofdwapening_dwars_boven_hart_op_hart"),
        "bottom_langs": rebar_config.get("hoofdwapening_langs_onder_hart_op_hart"),
        "bottom_dwars": rebar_config.get("hoofdwapening_dwars_onder_hart_op_hart"),
    }

    # check if additional reinforcement is used and set the diameters and distances accordingly
    # those values are mm!
    if rebar_config.get("heeft_bijlegwapening"):
        extra_reinf_diameter = {
            "top_langs": rebar_config.get("bijlegwapening_langs_boven_diameter"),
            "top_dwars": rebar_config.get("bijlegwapening_dwars_boven_diameter"),
            "bottom_langs": rebar_config.get("bijlegwapening_langs_onder_diameter"),
            "bottom_dwars": rebar_config.get("bijlegwapening_dwars_onder_diameter"),
        }
        extra_reinf_ctc_distances = {
            "top_langs": rebar_config.get("bijlegwapening_boven_hart_op_hart"),
            "top_dwars": rebar_config.get("bijlegwapening_boven_hart_op_hart"),
            "bottom_langs": rebar_config.get("bijlegwapening_boven_hart_op_hart"),
            "bottom_dwars": rebar_config.get("bijlegwapening_boven_hart_op_hart"),
        }
    else:
        # If no additional reinforcement is used, set diameters and distances to zero
        extra_reinf_diameter = {
            "top_langs": 0,
            "top_dwars": 0,
            "bottom_langs": 0,
            "bottom_dwars": 0,
        }
        extra_reinf_ctc_distances = {
            "top_langs": 0,
            "top_dwars": 0,
            "bottom_langs": 0,
            "bottom_dwars": 0,
        }

    # create new dict with max diameters to calculate reinforcement heights
    # This is needed to ensure that we use the maximum diameter for each direction to calculate cover and reinforcement heights
    max_reinf_diameters = {
        "top_langs": max(main_reinf_diameters["top_langs"], extra_reinf_diameter["top_langs"])
        if rebar_config.get("heeft_bijlegwapening")
        else main_reinf_diameters["top_langs"],
        "top_dwars": max(main_reinf_diameters["top_dwars"], extra_reinf_diameter["top_dwars"])
        if rebar_config.get("heeft_bijlegwapening")
        else main_reinf_diameters["top_dwars"],
        "bottom_langs": max(main_reinf_diameters["bottom_langs"], extra_reinf_diameter["bottom_langs"])
        if rebar_config.get("heeft_bijlegwapening")
        else main_reinf_diameters["bottom_langs"],
        "bottom_dwars": max(main_reinf_diameters["bottom_dwars"], extra_reinf_diameter["bottom_dwars"])
        if rebar_config.get("heeft_bijlegwapening")
        else main_reinf_diameters["bottom_dwars"],
    }

    # This part deals with the reinforcement bar heights based on half slab thickness reduced by the concrete cover and
    # the diameter of the reinforcement bars.
    # It also takes into account the langswapening_buiten parameter to determine the order of reinforcement layers.
    # It uses max_reinf_diameters to ensure that the cover and heights are calculated correctly if extra reinforcement is used.
    reinf_heights = {}
    thickness_mm = slab_thickness * 1000  # Convert thickness from m to mm
    # check if diameter main > extra to determine cover and reinforcement heights
    if params.input.geometrie_wapening.langswapening_buiten:
        # If langswapening_buiten is True, we assume the reinforcement in "langswapening" is placed as first layer
        reinf_heights["top_langs"] = thickness_mm / 2 - top_reinf_cover - max_reinf_diameters["top_langs"] / 2
        reinf_heights["top_dwars"] = thickness_mm / 2 - top_reinf_cover - max_reinf_diameters["top_langs"] - max_reinf_diameters["top_dwars"] / 2
        reinf_heights["bottom_langs"] = -thickness_mm / 2 + bottom_reinf_cover + max_reinf_diameters["bottom_langs"] / 2
        reinf_heights["bottom_dwars"] = (
            -thickness_mm / 2 + bottom_reinf_cover + max_reinf_diameters["bottom_langs"] + max_reinf_diameters["bottom_dwars"] / 2
        )
    else:
        # If langswapening_buiten is False, we assume the reinforcement in "langswapening" is placed as second layer
        reinf_heights["top_langs"] = thickness_mm / 2 - top_reinf_cover - max_reinf_diameters["top_dwars"] - max_reinf_diameters["top_langs"] / 2
        reinf_heights["top_dwars"] = thickness_mm / 2 - top_reinf_cover - max_reinf_diameters["top_dwars"] / 2
        reinf_heights["bottom_langs"] = (
            -thickness_mm / 2 + bottom_reinf_cover + max_reinf_diameters["bottom_dwars"] + max_reinf_diameters["bottom_langs"] / 2
        )
        reinf_heights["bottom_dwars"] = -thickness_mm / 2 + bottom_reinf_cover + max_reinf_diameters["bottom_dwars"] / 2

    return main_reinf_ctc_distances, main_reinf_diameters, reinf_heights, extra_reinf_diameter, extra_reinf_ctc_distances


def create_bridge_idea_model(params: BridgeParametrization) -> Any:  # noqa: ANN401
    """
    Create IDEA StatiCa RCS model from bridge parameters.

    :param params: BridgeParametrization object containing all bridge input parameters
    :type params: BridgeParametrization
    :returns: IDEA RCS model object
    :rtype: Any
    :raises ValueError: If parameters are invalid
    :raises ImportError: If VIKTOR IDEA module is not available
    """
    # Create the IDEA model
    model = idea_rcs.Model()

    # Create concrete material TODO link to centralized material system
    cs_mat = model.create_concrete_material(idea_rcs.ConcreteMaterial.C30_37)

    # Create reinforcement material TODO link to centralized material system
    mat_reinf = model.create_reinforcement_material(idea_rcs.ReinforcementMaterial.B_500B)

    # Get unique matching zone keys based on thickness and reinforcement configuration
    # We want to create a slab for each unique thickness and reinforcement configuration
    unique_matching_zone_keys, grouped_thickness, grouped_rebar_configs = _get_unique_matching_zone_keys(params)

    # Loop through unique thickness and reinforcement configurations
    for slab_thickness, config in unique_matching_zone_keys:
        # config is a string, but reinforcement_zones_array is indexed by int (1-based)
        # Convert config to int for correct indexing
        config_idx = int(config) - 1
        rebar_config = params.reinforcement_zones_array[config_idx]

        # Get reinforcement configuration based on the provided parameters for idea model
        # This function gets the main reinforcement diameters, center-to-center distances, and reinforcement heights
        main_reinf_ctc_distances, main_reinf_diameters, reinf_heights, extra_reinf_diameter, extra_reinf_ctc_distances = _get_rebar_config(
            rebar_config, params, slab_thickness
        )

        # Create slab for each unique thickness and reinforcement configuration for both directions since
        #  we cant create separate sections for each direction
        for direction in ["langs", "dwars"]:
            # Create rectangular cross-section for the slab
            cs = idea_rcs.RectSection(1.0, slab_thickness)
            slab = model.create_one_way_slab(cs, cs_mat, name=f"CS_d{slab_thickness}_{direction}_{config}", rcs_name=f"rcs_{direction}_{config}")

            # Create reinforcement bars for the top and bottom of the slab
            for location in ["top", "bottom"]:
                bar_locations_x = [
                    x / 1000 for x in calculate_rebar_positions(1000, main_reinf_ctc_distances[f"{location}_{direction}"])
                ]  # Convert mm to m
                bar_locations_y = [reinf_heights[f"{location}_{direction}"] / 1000] * len(bar_locations_x)  # Convert height from mm to m
                bar_diameters = [main_reinf_diameters[f"{location}_{direction}"] / 1000] * len(bar_locations_x)  # Convert diameter from mm to m
                bar_locations = list(zip(bar_locations_x, bar_locations_y))

                for coords, diameter in zip(bar_locations, bar_diameters):
                    slab.create_bar(coords, diameter, mat_reinf)

                # If additional reinforcement is used, create it as well
                if rebar_config.get("heeft_bijlegwapening"):
                    # Create additional reinforcement bars
                    extra_bar_locations_x = calculate_bijleg_positions(bar_locations_x)

                    # check if extra bar can fit at the beginning and end of the slab
                    loc_max_main_bar = float(max(bar_locations_x)) or 0.0  # Handle empty list case
                    loc_min_main_bar = float(min(bar_locations_x)) or 0.0  # Handle empty list case
                    ctc_dist_main_bar = float(main_reinf_ctc_distances[f"{location}_{direction}"]) / 1000 or 0.0  # Convert mm to m
                    remaining_space = 0.5 - loc_max_main_bar  # Remaining space at the end of the slab

                    # add extra bars at the beginning and end of the slab if there is enough space
                    if remaining_space >= ctc_dist_main_bar:
                        extra_bar_locations_x.append(loc_max_main_bar + ctc_dist_main_bar / 2)  # Insert at end
                        extra_bar_locations_x.insert(0, loc_min_main_bar - ctc_dist_main_bar / 2)  # Insert at beginning

                    extra_bar_locations_y = [reinf_heights[f"{location}_{direction}"] / 1000] * len(
                        extra_bar_locations_x
                    )  # Convert height from mm to m
                    extra_bar_diameters = [extra_reinf_diameter[f"{location}_{direction}"] / 1000] * len(
                        extra_bar_locations_x
                    )  # Convert diameter from mm to m
                    extra_bar_locations = list(zip(extra_bar_locations_x, extra_bar_locations_y))

                    for coords, diameter in zip(extra_bar_locations, extra_bar_diameters):
                        slab.create_bar(coords, diameter, mat_reinf)

            # Add extreme(s) TODO for now we use hardcoded values
            freq = idea_rcs.LoadingSLS(idea_rcs.ResultOfInternalForces(N=-100000, My=210000))
            fund = idea_rcs.LoadingULS(idea_rcs.ResultOfInternalForces(N=-99999, My=200000))
            slab.create_extreme(frequent=freq, fundamental=fund)

    # returns the IDEA model object
    return model


def run_idea_analysis(model: Any, timeout: int = 300) -> Any:  # noqa: ANN401
    """
    Run IDEA StatiCa analysis on the provided model.

    :param model: IDEA RCS model object
    :type model: Any
    :param timeout: Analysis timeout in seconds
    :type timeout: int
    :returns: Analysis output file object
    :rtype: Any
    :raises ImportError: If VIKTOR IDEA module is not available
    :raises RuntimeError: If analysis execution fails
    """
    # try:
    # Generate XML input for analysis
    xml_input = model.generate_xml_input()

    # Create and execute analysis
    analysis = idea_rcs.IdeaRcsAnalysis(xml_input, return_rcs_file=True)
    analysis.execute(timeout)

    return analysis.get_idea_rcs_file()
