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

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pandas as pd
from viktor.external import idea_rcs

from app.bridge.parametrization import BridgeParametrization
from src.geometry.bridge_geometry_data import create_node_and_thickness_dict
from src.integrations.idea_integration.idea_material_mapping import get_idea_concrete_material, get_idea_reinforcement_material

if TYPE_CHECKING:
    from viktor.core import File
    from viktor.external.idea_rcs import ConcreteMaterial, Material, Model, OneWaySlab, ReinforcementMaterial


@dataclass
class ReinforcementConfig:
    """Configuration for reinforcement parameters."""

    main_reinf_ctc_distances: dict[str, float]
    main_reinf_diameters: dict[str, float]
    reinf_heights: dict[str, float]
    extra_reinf_diameter: dict[str, float]
    extra_reinf_ctc_distances: dict[str, float]
    has_extra_reinforcement: bool
    rebar_config: dict


def _get_unique_matching_zone_keys(
    params: BridgeParametrization,
) -> tuple[
    list[tuple[float, str, list[str]]],
    dict[float, list[str]],
    dict[float, list[str]],
]:
    """
    Extract unique matching zone keys from bridge parameters.

    This function groups reinforcement zones by their zone number and matches them with
    the corresponding thickness zones extracted from the bridge parameters.

    :param params: BridgeParametrization object containing all bridge input parameters
    :type params: BridgeParametrization
    :returns: Tuple containing:
        - List of (thickness, config, zones) tuples for unique matching combinations
        - Dictionary grouping thickness zones by thickness value
        - Dictionary grouping reinforcement zones by configuration number
    :rtype: tuple[list[tuple[float, str, list[str]]], dict[float, list[str]], dict[float, list[str]]]
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
    matching_zone_keys: list[tuple[float, str, str]] = []
    for thickness, thickness_zones in grouped_thickness.items():
        for thickness_zone in thickness_zones:
            for config, rebar_zones in grouped_rebar_configs.items():
                for rebar_zone in rebar_zones:  # ignore PERF401
                    if thickness_zone == rebar_zone:
                        matching_zone_keys.append((thickness, str(config), thickness_zone))  # noqa: PERF401

    # Filter matching_zone_keys to only unique (thickness, config) pairs and collect corresponding zones
    unique_combinations: dict[tuple[float, str], list[str]] = {}
    for match_thickness, match_config, match_zone in matching_zone_keys:
        combination_key = (match_thickness, match_config)
        if combination_key not in unique_combinations:
            unique_combinations[combination_key] = []
        unique_combinations[combination_key].append(match_zone)

    # Create tuples with zones as the third element
    unique_matching_zone_keys = [(thickness, config, zones) for (thickness, config), zones in unique_combinations.items()]
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


def _get_rebar_config(
    rebar_config: dict, params: BridgeParametrization, slab_thickness: float
) -> tuple[dict[str, float], dict[str, float], dict[str, float], dict[str, float], dict[str, float]]:
    """Get reinforcement configuration based on the provided viktor parameters."""
    # reinforcement cover (dekking) is the distance from the concrete surface to the reinforcement
    top_reinf_cover = params.input.geometrie_wapening.dekking_boven
    bottom_reinf_cover = params.input.geometrie_wapening.dekking_onder

    # Get needed reinforcement data in mm
    main_reinf_diameters = {
        "top_langs": rebar_config.get("hoofdwapening_langs_boven_diameter", 0.0),
        "top_dwars": rebar_config.get("hoofdwapening_dwars_boven_diameter", 0.0),
        "bottom_langs": rebar_config.get("hoofdwapening_langs_onder_diameter", 0.0),
        "bottom_dwars": rebar_config.get("hoofdwapening_dwars_onder_diameter", 0.0),
    }

    # Get center to center distances in mm
    main_reinf_ctc_distances = {
        "top_langs": rebar_config.get("hoofdwapening_langs_boven_hart_op_hart", 0.0),
        "top_dwars": rebar_config.get("hoofdwapening_dwars_boven_hart_op_hart", 0.0),
        "bottom_langs": rebar_config.get("hoofdwapening_langs_onder_hart_op_hart", 0.0),
        "bottom_dwars": rebar_config.get("hoofdwapening_dwars_onder_hart_op_hart", 0.0),
    }

    # check if additional reinforcement is used and set the diameters and distances accordingly
    # those values are mm!
    if rebar_config.get("heeft_bijlegwapening"):
        extra_reinf_diameter = {
            "top_langs": rebar_config.get("bijlegwapening_langs_boven_diameter", 0.0),
            "top_dwars": rebar_config.get("bijlegwapening_dwars_boven_diameter", 0.0),
            "bottom_langs": rebar_config.get("bijlegwapening_langs_onder_diameter", 0.0),
            "bottom_dwars": rebar_config.get("bijlegwapening_dwars_onder_diameter", 0.0),
        }
        extra_reinf_ctc_distances = {
            "top_langs": rebar_config.get("bijlegwapening_boven_hart_op_hart", 0.0),
            "top_dwars": rebar_config.get("bijlegwapening_boven_hart_op_hart", 0.0),
            "bottom_langs": rebar_config.get("bijlegwapening_boven_hart_op_hart", 0.0),
            "bottom_dwars": rebar_config.get("bijlegwapening_boven_hart_op_hart", 0.0),
        }
    else:
        # If no additional reinforcement is used, set diameters and distances to zero
        extra_reinf_diameter = {
            "top_langs": 0.0,
            "top_dwars": 0.0,
            "bottom_langs": 0.0,
            "bottom_dwars": 0.0,
        }
        extra_reinf_ctc_distances = {
            "top_langs": 0.0,
            "top_dwars": 0.0,
            "bottom_langs": 0.0,
            "bottom_dwars": 0.0,
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


def _create_idea_model_with_materials(params: BridgeParametrization) -> tuple["Model", "ConcreteMaterial", "ReinforcementMaterial"]:
    """
    Create IDEA model with concrete and reinforcement materials.

    :param params: Bridge parametrization
    :type params: BridgeParametrization
    :returns: Tuple of (model, concrete_material, reinforcement_material)
    :rtype: tuple[Model, ConcreteMaterial, ReinforcementMaterial]
    """
    # Prepare the IDEA model with project information
    project_data = idea_rcs.ProjectData(
        name=f"IDEA Model for {getattr(params.info, 'bridge_objectnumm', None) or 'Unnamed Project'}",
        description="Generated model from VIKTOR",
        author="Ctrl+b",
        national_annex="Dutch",
    )

    # Create the IDEA model with project information
    model = idea_rcs.Model(project_data=project_data)

    # Create concrete material using parameter from user input
    concrete_quality = getattr(params.info, "concrete_strength_class", None) or "C30/37"  # Default fallback
    concrete_material_enum = get_idea_concrete_material(concrete_quality)
    cs_mat = model.create_concrete_material(concrete_material_enum)

    # Create reinforcement material using parameter from user input
    steel_quality = getattr(params.input.geometrie_wapening, "staalsoort", None) or "B500B"  # Default fallback
    reinforcement_material_enum = get_idea_reinforcement_material(steel_quality)
    mat_reinf = model.create_reinforcement_material(reinforcement_material_enum)

    return model, cs_mat, mat_reinf


def _create_reinforcement_bars(
    slab: "OneWaySlab",
    direction: str,
    config: ReinforcementConfig,
    mat_reinf: "ReinforcementMaterial",
) -> None:
    """
    Create reinforcement bars for a slab in a specific direction.

    :param slab: IDEA slab object
    :type slab: OneWaySlab
    :param direction: Direction ("langs" or "dwars")
    :type direction: str
    :param config: Reinforcement configuration containing all parameters
    :type config: ReinforcementConfig
    :param mat_reinf: Reinforcement material
    :type mat_reinf: ReinforcementMaterial
    """
    for location in ["top", "bottom"]:
        # Create main reinforcement bars
        bar_locations_x = [
            x / 1000 for x in calculate_rebar_positions(1000, config.main_reinf_ctc_distances[f"{location}_{direction}"])
        ]  # Convert mm to m
        bar_locations_y = [config.reinf_heights[f"{location}_{direction}"] / 1000] * len(bar_locations_x)  # Convert height from mm to m
        bar_diameters = [config.main_reinf_diameters[f"{location}_{direction}"] / 1000] * len(bar_locations_x)  # Convert diameter from mm to m
        bar_locations = list(zip(bar_locations_x, bar_locations_y))

        for coords, diameter in zip(bar_locations, bar_diameters):
            slab.create_bar(coords, diameter, mat_reinf)

        # Create additional reinforcement if needed
        if config.rebar_config.get("heeft_bijlegwapening"):
            _create_additional_reinforcement(slab, f"{location}_{direction}", bar_locations_x, config, mat_reinf)


def _create_additional_reinforcement(
    slab: "OneWaySlab",
    location_direction: str,  # Combined "top_langs", "bottom_dwars", etc.
    main_bar_locations_x: list[float],
    config: ReinforcementConfig,
    mat_reinf: "ReinforcementMaterial",
) -> None:
    """
    Create additional reinforcement bars (bijlegwapening).

    :param slab: IDEA slab object
    :type slab: OneWaySlab
    :param location_direction: Combined location and direction ("top_langs", "bottom_dwars", etc.)
    :type location_direction: str
    :param main_bar_locations_x: X coordinates of main reinforcement bars
    :type main_bar_locations_x: list[float]
    :param config: Reinforcement configuration containing all parameters
    :type config: ReinforcementConfig
    :param mat_reinf: Reinforcement material
    :type mat_reinf: ReinforcementMaterial
    """
    # Create additional reinforcement bars
    extra_bar_locations_x = calculate_bijleg_positions(main_bar_locations_x)

    # Check if extra bar can fit at the beginning and end of the slab
    loc_max_main_bar = float(max(main_bar_locations_x)) if main_bar_locations_x else 0.0
    loc_min_main_bar = float(min(main_bar_locations_x)) if main_bar_locations_x else 0.0
    ctc_dist_main_bar = float(config.main_reinf_ctc_distances[location_direction]) / 1000 or 0.0  # Convert mm to m
    remaining_space = 0.5 - loc_max_main_bar  # Remaining space at the end of the slab

    # Add extra bars at the beginning and end of the slab if there is enough space
    if remaining_space >= ctc_dist_main_bar:
        extra_bar_locations_x.append(loc_max_main_bar + ctc_dist_main_bar / 2)  # Insert at end
        extra_bar_locations_x.insert(0, loc_min_main_bar - ctc_dist_main_bar / 2)  # Insert at beginning

    extra_bar_locations_y = [config.reinf_heights[location_direction] / 1000] * len(extra_bar_locations_x)
    extra_bar_diameters = [config.extra_reinf_diameter[location_direction] / 1000] * len(extra_bar_locations_x)
    extra_bar_locations = list(zip(extra_bar_locations_x, extra_bar_locations_y))

    for coords, diameter in zip(extra_bar_locations, extra_bar_diameters):
        slab.create_bar(coords, diameter, mat_reinf)


def _create_slabs_with_reinforcement(params: BridgeParametrization, model: "Model", cs_mat: "Material", mat_reinf: "Material") -> dict[str, dict]:
    """
    Create slabs with reinforcement for all unique thickness and reinforcement configurations.

    :param params: Bridge parametrization
    :type params: BridgeParametrization
    :param model: IDEA model
    :type model: Model
    :param cs_mat: Concrete material
    :type cs_mat: ConcreteMaterial
    :param mat_reinf: Reinforcement material
    :type mat_reinf: ReinforcementMaterial
    :returns: Dictionary of created slabs
    :rtype: dict[str, dict]
    """
    # Get unique matching zone keys based on thickness and reinforcement configuration
    unique_matching_zone_keys, _, _ = _get_unique_matching_zone_keys(params)

    # Create a empty dict to store already created slabs to avoid duplicates
    created_slabs = {}

    # Loop through unique thickness and reinforcement configurations
    for slab_thickness, config, zones in unique_matching_zone_keys:
        # store unique slab key to avoid creating duplicate slabs
        slab_key = f"CS_d{slab_thickness}_{config}"
        if slab_key in created_slabs:
            continue  # Skip if slab already created
        created_slabs[slab_key] = {"zones": zones}

        # Get reinforcement configuration
        config_idx = int(config) - 1
        rebar_config = params.reinforcement_zones_array[config_idx]
        main_reinf_ctc_distances, main_reinf_diameters, reinf_heights, extra_reinf_diameter, extra_reinf_ctc_distances = _get_rebar_config(
            rebar_config, params, slab_thickness
        )

        # Create reinforcement configuration object
        reinf_config = ReinforcementConfig(
            main_reinf_ctc_distances=main_reinf_ctc_distances,
            main_reinf_diameters=main_reinf_diameters,
            reinf_heights=reinf_heights,
            extra_reinf_diameter=extra_reinf_diameter,
            extra_reinf_ctc_distances=extra_reinf_ctc_distances,
            has_extra_reinforcement=rebar_config.get("heeft_bijlegwapening", False),
            rebar_config=rebar_config,
        )

        # Create slab for each direction
        for direction in ["langs", "dwars"]:
            # Create rectangular cross-section for the slab
            cs = idea_rcs.RectSection(1.0, slab_thickness)
            slab = model.create_one_way_slab(cs, cs_mat, name=f"CS_d{slab_thickness}_{direction}_{config}", rcs_name=f"rcs_{direction}_{config}")
            created_slabs[slab_key][f"slab_{direction}"] = slab

            # Create reinforcement bars for this slab
            _create_reinforcement_bars(slab, direction, reinf_config, mat_reinf)

    return created_slabs


def _process_scia_results(scia_results_dict: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Process SCIA results into a single merged dataframe.

    :param scia_results_dict: Dictionary containing SCIA results for different load cases
    :returns: Merged dataframe with all load cases
    :rtype: pd.DataFrame
    """
    # Get load cases from SCIA results
    df_uls = scia_results_dict.get("ULS", pd.DataFrame())
    df_sls_kar = scia_results_dict.get("SLS kar", pd.DataFrame())
    df_sls_freq = scia_results_dict.get("SLS freq", pd.DataFrame())

    # Filter the names in the dataframes to match the zones
    for df in [df_uls, df_sls_kar, df_sls_freq]:
        df["name"] = df["name"].str[1:].str.replace("_", "-")

    # Add moment columns
    for df in [df_uls, df_sls_kar, df_sls_freq]:
        df["Mx"] = df[["m_xD+_max", "m_xD-_max"]].abs().max(axis=1)
        df["My"] = df[["m_yD+_max", "m_yD-_max"]].max(axis=1)

    # Rename columns to prevent clashes
    df_uls = df_uls.rename(columns=lambda x: f"ULS_{x}" if x not in ["name", "coords_xyz"] else x)
    df_sls_kar = df_sls_kar.rename(columns=lambda x: f"SLS_kar_{x}" if x not in ["name", "coords_xyz"] else x)
    df_sls_freq = df_sls_freq.rename(columns=lambda x: f"SLS_freq_{x}" if x not in ["name", "coords_xyz"] else x)

    # Merge dataframes
    df_all = df_uls.merge(df_sls_kar, on=["name", "coords_xyz"], how="inner")
    df_all = df_all.merge(df_sls_freq, on=["name", "coords_xyz"], how="inner")

    return df_all


def _apply_loads_to_slabs(created_slabs: dict[str, dict], df_all: pd.DataFrame) -> None:
    """
    Apply load cases from SCIA results to each slab.

    :param created_slabs: Dictionary of created slabs
    :param df_all: Merged dataframe with all load cases
    """
    for slab_key, slab_data in created_slabs.items():
        # Filter SCIA results for the current slab
        zones = slab_data.get("zones", [])
        df_slab = df_all[df_all["name"].isin(zones)]

        # Apply loads for each direction
        for direction in ["langs", "dwars"]:
            slab = slab_data.get(f"slab_{direction}")
            if slab is None:
                continue

            if direction == "langs":
                # Use Y-axis for longitudinal direction
                for _, row in df_slab.iterrows():
                    char = idea_rcs.LoadingSLS(idea_rcs.ResultOfInternalForces(Qz=row.get("SLS_kar_v_y_max", 0), My=row.get("SLS_kar_My", 0)))
                    freq = idea_rcs.LoadingSLS(idea_rcs.ResultOfInternalForces(Qz=row.get("SLS_freq_v_y_max", 0), My=row.get("SLS_freq_My", 0)))
                    fund = idea_rcs.LoadingULS(idea_rcs.ResultOfInternalForces(Qz=row.get("ULS_v_y_max", 0), My=row.get("ULS_My", 0)))

                    # Create a robust description including slab key, name and coords
                    name = row.get("name", "Unknown")
                    coords = row.get("coords_xyz")
                    if coords is not None:
                        coords_str = f"({', '.join(map(str, coords))})" if isinstance(coords, (list, tuple)) else str(coords)
                    else:
                        coords_str = "No coords"

                    description = f"{slab_key.replace('.', '_')} - {name} - {coords_str}"

                    slab.create_extreme(description=description, characteristic=char, frequent=freq, fundamental=fund)
            elif direction == "dwars":
                # Use X-axis for transverse direction
                for _, row in df_slab.iterrows():
                    char = idea_rcs.LoadingSLS(idea_rcs.ResultOfInternalForces(Qz=row.get("SLS_kar_v_x_max", 0), My=row.get("SLS_kar_Mx", 0)))
                    freq = idea_rcs.LoadingSLS(idea_rcs.ResultOfInternalForces(Qz=row.get("SLS_freq_v_x_max", 0), My=row.get("SLS_freq_Mx", 0)))
                    fund = idea_rcs.LoadingULS(idea_rcs.ResultOfInternalForces(Qz=row.get("ULS_v_x_max", 0), My=row.get("ULS_Mx", 0)))

                    # Create a robust description including slab key, name and coords
                    name = row.get("name", "Unknown")
                    coords = row.get("coords_xyz")
                    if coords is not None:
                        coords_str = f"({', '.join(map(str, coords))})" if isinstance(coords, (list, tuple)) else str(coords)
                    else:
                        coords_str = "No coords"

                    description = f"{slab_key.replace('.', '_')} - {name} - {coords_str}"

                    slab.create_extreme(description=description, characteristic=char, frequent=freq, fundamental=fund)


def create_bridge_idea_model(params: BridgeParametrization, entity_id: int, scia_results_dict: dict[str, pd.DataFrame] | None = None) -> "Model":
    """
    Create IDEA StatiCa RCS model from bridge parameters.

    :param params: BridgeParametrization object containing all bridge input parameters
    :type params: BridgeParametrization
    :param entity_id: Entity ID for caching (used if scia_results_dict is None)
    :type entity_id: int
    :param scia_results_dict: Pre-computed SCIA results, if None will fetch from cache
    :type scia_results_dict: dict[str, pd.DataFrame] | None
    :returns: IDEA RCS model object
    :rtype: Model
    :raises ValueError: If parameters are invalid
    :raises ImportError: If VIKTOR IDEA module is not available
    """
    # Get SCIA results - either passed in or fetch from cache
    if scia_results_dict is None:
        # Import here to avoid circular imports only when needed
        from app.bridge.analysis_cache import get_scia_results_for_idea

        scia_results_dict = get_scia_results_for_idea(params, entity_id=entity_id)

    # Create IDEA model with materials
    model, cs_mat, mat_reinf = _create_idea_model_with_materials(params)

    # Create slabs with reinforcement
    created_slabs = _create_slabs_with_reinforcement(params, model, cs_mat, mat_reinf)

    # Process SCIA results
    df_all = _process_scia_results(scia_results_dict)

    # Apply loads to slabs
    _apply_loads_to_slabs(created_slabs, df_all)

    return model


def run_idea_analysis(model: "Model", timeout: int = 300) -> "File":
    """
    Run IDEA StatiCa analysis on the provided model.

    :param model: IDEA RCS model object
    :type model: Model
    :param timeout: Analysis timeout in seconds
    :type timeout: int
    :returns: Analysis output file object
    :rtype: File
    :raises ImportError: If VIKTOR IDEA module is not available
    :raises RuntimeError: If analysis execution fails
    """
    # Generate XML input for analysis
    xml_input = model.generate_xml_input()

    # Create and execute analysis
    analysis = idea_rcs.IdeaRcsAnalysis(xml_input, return_rcs_file=True)
    analysis.execute(timeout)

    return analysis.get_idea_rcs_file()
