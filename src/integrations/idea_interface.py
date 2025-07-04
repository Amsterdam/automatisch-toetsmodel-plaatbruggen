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
from src.integrations.scia_interface import create_node_and_thickness_dict


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

    # reinforcement cover (dekking) is the distance from the concrete surface to the reinforcement
    top_reinf_cover = params.input.geometrie_wapening.dekking_boven
    bottom_reinf_cover = params.input.geometrie_wapening.dekking_onder

    # Get unique matching zone keys based on thickness and reinforcement configuration
    # We want to create a slab for each unique thickness and reinforcement configuration
    unique_matching_zone_keys, grouped_thickness, grouped_rebar_configs = _get_unique_matching_zone_keys(params)

    # Loop through unique thickness and reinforcement configurations
    for thickness, config in unique_matching_zone_keys:
        # config is a string, but reinforcement_zones_array is indexed by int (1-based)
        # Convert config to int for correct indexing
        config_idx = int(config) - 1
        rebar_config = params.reinforcement_zones_array[config_idx]

        # Get needed reinforcement data in mm
        diameters = {
            "top_langs": rebar_config.get("hoofdwapening_langs_boven_diameter"),
            "top_dwars": rebar_config.get("hoofdwapening_dwars_boven_diameter"),
            "bottom_langs": rebar_config.get("hoofdwapening_langs_onder_diameter"),
            "bottom_dwars": rebar_config.get("hoofdwapening_dwars_onder_diameter"),
        }

        # Get center to center distances in mm
        ctc_distances = {
            "top_langs": rebar_config.get("hoofdwapening_langs_boven_hart_op_hart"),
            "top_dwars": rebar_config.get("hoofdwapening_dwars_boven_hart_op_hart"),
            "bottom_langs": rebar_config.get("hoofdwapening_langs_onder_hart_op_hart"),
            "bottom_dwars": rebar_config.get("hoofdwapening_dwars_onder_hart_op_hart"),
        }

        # This part deals with the reinforcement bar heights based on half slab thickness reduced by the concrete cover and
        # the diameter of the reinforcement bars.
        # It also takes into account the langswapening_buiten parameter to determine the order of reinforcement layers.
        reinf_heights = {}
        thickness_mm = thickness * 1000  # Convert thickness from m to mm
        if params.input.geometrie_wapening.langswapening_buiten:
            # If langswapening_buiten is True, we assume the reinforcement in "langswapening" is placed as first layer
            reinf_heights["top_langs"] = thickness_mm / 2 - top_reinf_cover - diameters["top_langs"] / 2
            reinf_heights["top_dwars"] = thickness_mm / 2 - top_reinf_cover - diameters["top_langs"] - diameters["top_dwars"] / 2
            reinf_heights["bottom_langs"] = -thickness_mm / 2 + bottom_reinf_cover + diameters["bottom_langs"] / 2
            reinf_heights["bottom_dwars"] = -thickness_mm / 2 + bottom_reinf_cover + diameters["bottom_langs"] + diameters["bottom_dwars"] / 2
        else:
            # If langswapening_buiten is False, we assume the reinforcement in "langswapening" is placed as second layer
            reinf_heights["top_langs"] = thickness_mm / 2 - top_reinf_cover - diameters["top_dwars"] - diameters["top_langs"] / 2
            reinf_heights["top_dwars"] = thickness_mm / 2 - top_reinf_cover - diameters["top_dwars"] / 2
            reinf_heights["bottom_langs"] = -thickness_mm / 2 + bottom_reinf_cover + diameters["bottom_dwars"] + diameters["bottom_langs"] / 2
            reinf_heights["bottom_dwars"] = -thickness_mm / 2 + bottom_reinf_cover + diameters["bottom_dwars"] / 2

        # Create slab for each unique thickness and reinforcement configuration for both directions since
        #  we cant create separate sections for each direction
        for direction in ["langs", "dwars"]:
            # Create rectangular cross-section for the slab
            cs = idea_rcs.RectSection(1.0, thickness)
            slab = model.create_one_way_slab(cs, cs_mat, name=f"CS_d{thickness}_{direction}_{config}", rcs_name=f"rcs_{direction}_{config}")

            # Create reinforcement bars for the top and bottom of the slab
            for location in ["top", "bottom"]:
                bar_locations_x = [x / 1000 for x in calculate_rebar_positions(1000, ctc_distances[f"{location}_{direction}"])]  # Convert mm to m
                bar_locations_y = [reinf_heights[f"{location}_{direction}"] / 1000] * len(bar_locations_x)  # Convert height from mm to m
                bar_diameters = [diameters[f"{location}_{direction}"] / 1000] * len(bar_locations_x)  # Convert diameter from mm to m
                bar_locations = list(zip(bar_locations_x, bar_locations_y))

                for coords, diameter in zip(bar_locations, bar_diameters):
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
    try:
        from viktor.external import idea_rcs
    except ImportError as e:
        raise ImportError("VIKTOR IDEA StatiCa module required") from e

    try:
        # Generate XML input for analysis
        xml_input = model.generate_xml_input()

        # Create and execute analysis
        analysis = idea_rcs.IdeaRcsAnalysis(xml_input, return_rcs_file=True)
        analysis.execute(timeout)

        return analysis.get_idea_rcs_file()

    except Exception as e:
        raise RuntimeError(f"IDEA analysis failed: {e}") from e
