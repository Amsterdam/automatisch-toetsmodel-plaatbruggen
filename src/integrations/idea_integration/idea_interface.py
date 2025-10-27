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

import contextlib
from collections import defaultdict
from typing import TYPE_CHECKING, Any

import pandas as pd
from viktor.external import idea_rcs

from src.common.constants.technical import MM_TO_M
from src.geometry.bridge_geometry_data import create_node_and_thickness_dict
from src.integrations.idea_integration.idea_data_models import (
    BridgeGeometryConfig,
    BridgeIdeaInputData,
    ReinforcementConfig,
    ReinforcementZoneConfig,
)
from src.integrations.idea_integration.idea_material_mapping import (
    create_concrete_material_for_idea,
    create_reinforcement_material_for_idea,
)

# SDK import only for TYPE_CHECKING and analysis execution
# Note: run_idea_analysis() still uses direct SDK for analysis execution
# This is acceptable as analysis execution is separate from model building
if TYPE_CHECKING:
    from viktor.core import File
    from viktor.external.idea_rcs import Model, OneWaySlab, ReinforcementMaterial


def _get_unique_matching_zone_keys(
    input_data: BridgeIdeaInputData,
) -> tuple[
    list[tuple[float, str, list[str]]],
    dict[float, list[str]],
    dict[int, list[str]],
]:
    """
    Extract unique matching zone keys from bridge input data.

    This function groups reinforcement zones by their zone number and matches them with
    the corresponding thickness zones extracted from the bridge parameters.

    :param input_data: BridgeIdeaInputData object containing all bridge input data
    :type input_data: BridgeIdeaInputData
    :returns: Tuple containing:
        - List of (thickness, config, zones) tuples for unique matching combinations
        - Dictionary grouping thickness zones by thickness value
        - Dictionary grouping reinforcement zones by configuration number
    :rtype: tuple[list[tuple[float, str, list[str]]], dict[float, list[str]], dict[int, list[str]]]
    """

    # --- 1) Build grouped_thickness: thickness -> [zone] (normalized) -----------------
    # Note: create_node_and_thickness_dict still needs BridgeParametrization
    # This is a temporary workaround - ideally this function should also be refactored
    # TODO: Refactor create_node_and_thickness_dict to work with bridge_segments data
    # Create temporary params object for geometry extraction
    # This is technical debt that should be addressed in future refactoring
    class TempParams:
        def __init__(self, segments: list) -> None:
            self.bridge_segments_array = segments

    temp_params = TempParams(input_data.bridge_segments)
    nodes_dict, thickness_dict = create_node_and_thickness_dict(temp_params)  # type: ignore[arg-type]
    grouped_thickness: dict[float, list[str]] = {}
    for zone_key, thickness in thickness_dict.items():
        # original zone format Z1_1 -> normalized "1-1"
        norm_zone = zone_key[1:].replace("_", "-")
        grouped_thickness.setdefault(thickness, []).append(norm_zone)

    # --- 2) Build grouped_rebar_configs: config_idx -> [zone] (as given) --------------
    grouped_rebar_configs: dict[int, list[str]] = {}
    for i, rebar_config in enumerate(input_data.reinforcement_zones, start=1):
        zones = rebar_config.zone_number or []
        # ensure strings and trim whitespace; keep original semantics
        grouped_rebar_configs[i] = [str(z).strip() for z in zones]

    # --- 3) Match zones via set intersection ------------------------------------------
    # Build (thickness, config) -> set[zones] directly to avoid duplicates while matching
    combo_to_zones: defaultdict[tuple[float, int], set[str]] = defaultdict(set)

    for thickness, t_zones_list in grouped_thickness.items():
        t_zones = set(t_zones_list)  # unique per thickness
        for config, r_zones_list in grouped_rebar_configs.items():
            if not r_zones_list:
                continue
            # intersection is O(n) in smaller set
            for z in t_zones.intersection(r_zones_list):
                combo_to_zones[(thickness, config)].add(z)

    # --- 4) Convert to requested output shape -----------------------------------------
    # (thickness, config:str, zones:list[str])
    unique_matching_zone_keys: list[tuple[float, str, list[str]]] = []
    for (thickness, config), zones_set in combo_to_zones.items():
        zones = sorted(zones_set)  # sort for deterministic output
        unique_matching_zone_keys.append((thickness, str(config), zones))

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
    rebar_config: ReinforcementZoneConfig, geometry_config: BridgeGeometryConfig, slab_thickness: float
) -> tuple[dict[str, float], dict[str, float], dict[str, float], dict[str, float], dict[str, float]]:
    """Get reinforcement configuration based on the provided bridge data."""
    # reinforcement cover (dekking) is the distance from the concrete surface to the reinforcement
    top_reinf_cover = geometry_config.dekking_boven
    bottom_reinf_cover = geometry_config.dekking_onder

    # Get needed reinforcement data in mm
    main_reinf_diameters = {
        "top_langs": rebar_config.hoofdwapening_langs_boven_diameter,
        "top_dwars": rebar_config.hoofdwapening_dwars_boven_diameter,
        "bottom_langs": rebar_config.hoofdwapening_langs_onder_diameter,
        "bottom_dwars": rebar_config.hoofdwapening_dwars_onder_diameter,
    }

    # Get center to center distances in mm
    main_reinf_ctc_distances = {
        "top_langs": rebar_config.hoofdwapening_langs_boven_hart_op_hart,
        "top_dwars": rebar_config.hoofdwapening_dwars_boven_hart_op_hart,
        "bottom_langs": rebar_config.hoofdwapening_langs_onder_hart_op_hart,
        "bottom_dwars": rebar_config.hoofdwapening_dwars_onder_hart_op_hart,
    }

    # check if additional reinforcement is used and set the diameters and distances accordingly
    # those values are mm!
    if rebar_config.heeft_bijlegwapening:
        extra_reinf_diameter = {
            "top_langs": rebar_config.bijlegwapening_langs_boven_diameter,
            "top_dwars": rebar_config.bijlegwapening_dwars_boven_diameter,
            "bottom_langs": rebar_config.bijlegwapening_langs_onder_diameter,
            "bottom_dwars": rebar_config.bijlegwapening_dwars_onder_diameter,
        }
        extra_reinf_ctc_distances = {
            "top_langs": rebar_config.bijlegwapening_boven_hart_op_hart,
            "top_dwars": rebar_config.bijlegwapening_boven_hart_op_hart,
            "bottom_langs": rebar_config.bijlegwapening_boven_hart_op_hart,
            "bottom_dwars": rebar_config.bijlegwapening_boven_hart_op_hart,
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
        if rebar_config.heeft_bijlegwapening
        else main_reinf_diameters["top_langs"],
        "top_dwars": max(main_reinf_diameters["top_dwars"], extra_reinf_diameter["top_dwars"])
        if rebar_config.heeft_bijlegwapening
        else main_reinf_diameters["top_dwars"],
        "bottom_langs": max(main_reinf_diameters["bottom_langs"], extra_reinf_diameter["bottom_langs"])
        if rebar_config.heeft_bijlegwapening
        else main_reinf_diameters["bottom_langs"],
        "bottom_dwars": max(main_reinf_diameters["bottom_dwars"], extra_reinf_diameter["bottom_dwars"])
        if rebar_config.heeft_bijlegwapening
        else main_reinf_diameters["bottom_dwars"],
    }

    # This part deals with the reinforcement bar heights based on half slab thickness reduced by the concrete cover and
    # the diameter of the reinforcement bars.
    # It also takes into account the langswapening_buiten parameter to determine the order of reinforcement layers.
    # It uses max_reinf_diameters to ensure that the cover and heights are calculated correctly if extra reinforcement is used.
    reinf_heights = {}
    thickness_mm = slab_thickness * 1000  # Convert thickness from m to mm
    # check if diameter main > extra to determine cover and reinforcement heights
    if geometry_config.langswapening_buiten:
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


def _create_idea_model_with_concrete_and_reinforcement_materials(
    input_data: BridgeIdeaInputData,
    builder: Any,  # IdeaModelBuilder - using Any to avoid circular import  # noqa: ANN401
) -> tuple[Any, Any, Any]:  # Returns (IdeaModel, IdeaConcreteMaterial, IdeaReinforcementMaterial)
    """
    Create IDEA model with concrete and reinforcement materials using the builder pattern.

    Supports both modern Eurocode materials and historical materials from CSV data.

    :param input_data: Bridge input data extracted from parametrization
    :type input_data: BridgeIdeaInputData
    :param builder: IDEA model builder instance
    :type builder: IdeaModelBuilder
    :returns: Tuple of (model, concrete_material, reinforcement_material)
    :rtype: tuple[Any, Any, Any]
    """
    # Prepare the IDEA model with project information using builder
    project_data = builder.create_project_data(
        name=f"IDEA Model for {input_data.bridge_name}",
        description="Generated model from VIKTOR",
        author="Ctrl+b",
        national_annex="Dutch",
    )

    # Create the IDEA model with project information using builder
    model = builder.create_model(project_data)

    # Create concrete material using builder and material helper functions
    # The helper functions handle both modern and historical materials
    cs_mat = create_concrete_material_for_idea(model, input_data.concrete_strength_class)

    # Create reinforcement material using builder and material helper functions
    mat_reinf = create_reinforcement_material_for_idea(model, input_data.steel_quality)

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
            x / MM_TO_M for x in calculate_rebar_positions(1000, config.main_reinf_ctc_distances[f"{location}_{direction}"])
        ]  # Convert positions from mm to m
        bar_locations_y = [config.reinf_heights[f"{location}_{direction}"] / MM_TO_M] * len(bar_locations_x)  # Convert heights from mm to m
        bar_diameters = [config.main_reinf_diameters[f"{location}_{direction}"] / MM_TO_M] * len(bar_locations_x)  # Convert diameters from mm to m
        bar_locations = list(zip(bar_locations_x, bar_locations_y))

        for coords, diameter in zip(bar_locations, bar_diameters):
            slab.create_bar(coords, diameter, mat_reinf)

        # Create additional reinforcement if needed (using attribute access for Pydantic model)
        if config.rebar_config.heeft_bijlegwapening:
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
    ctc_dist_main_bar = float(config.main_reinf_ctc_distances[location_direction]) / MM_TO_M or 0.0  # Convert mm to m
    remaining_space = 0.5 - loc_max_main_bar  # Remaining space at the end of the slab

    # Add extra bars at the beginning and end of the slab if there is enough space
    if remaining_space >= ctc_dist_main_bar:
        extra_bar_locations_x.append(loc_max_main_bar + ctc_dist_main_bar / 2)  # Insert at end
        extra_bar_locations_x.insert(0, loc_min_main_bar - ctc_dist_main_bar / 2)  # Insert at beginning

    extra_bar_locations_y = [config.reinf_heights[location_direction] / MM_TO_M] * len(extra_bar_locations_x)  # Convert heights from mm to m
    extra_bar_diameters = [config.extra_reinf_diameter[location_direction] / MM_TO_M] * len(extra_bar_locations_x)  # Convert diameters from mm to m
    extra_bar_locations = list(zip(extra_bar_locations_x, extra_bar_locations_y))

    for coords, diameter in zip(extra_bar_locations, extra_bar_diameters):
        slab.create_bar(coords, diameter, mat_reinf)


def _create_slabs_with_reinforcement(
    input_data: BridgeIdeaInputData,
    model: Any,  # IdeaModel  # noqa: ANN401
    cs_mat: Any,  # IdeaConcreteMaterial  # noqa: ANN401
    mat_reinf: Any,  # IdeaReinforcementMaterial  # noqa: ANN401
    builder: Any,  # IdeaModelBuilder  # noqa: ANN401
) -> dict[str, dict]:
    """
    Create slabs with reinforcement for all unique thickness and reinforcement configurations.

    :param input_data: Bridge input data
    :type input_data: BridgeIdeaInputData
    :param model: IDEA model
    :type model: Any
    :param cs_mat: Concrete material
    :type cs_mat: Any
    :param mat_reinf: Reinforcement material
    :type mat_reinf: Any
    :param builder: IDEA model builder instance
    :type builder: Any
    :returns: Dictionary of created slabs
    :rtype: dict[str, dict]
    """
    # Get unique matching zone keys based on thickness and reinforcement configuration
    unique_matching_zone_keys, _, _ = _get_unique_matching_zone_keys(input_data)

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
        rebar_config = input_data.reinforcement_zones[config_idx]
        main_reinf_ctc_distances, main_reinf_diameters, reinf_heights, extra_reinf_diameter, extra_reinf_ctc_distances = _get_rebar_config(
            rebar_config, input_data.geometry_config, slab_thickness
        )

        # Create reinforcement configuration object
        reinf_config = ReinforcementConfig(
            main_reinf_ctc_distances=main_reinf_ctc_distances,
            main_reinf_diameters=main_reinf_diameters,
            reinf_heights=reinf_heights,
            extra_reinf_diameter=extra_reinf_diameter,
            extra_reinf_ctc_distances=extra_reinf_ctc_distances,
            has_extra_reinforcement=rebar_config.heeft_bijlegwapening,
            rebar_config=rebar_config,
        )

        # Create slab for each rebar direction
        for direction in ["langs", "dwars"]:
            # Create rectangular cross-section for the slab using builder
            # cs_dwars should be paired with rebar_langs and vice versa so we use opposite_direction here
            opposite_direction = "dwars" if direction == "langs" else "langs"
            cs = builder.create_rect_section(1.0, slab_thickness)
            slab = builder.create_one_way_slab(
                model, cs, cs_mat, name=f"CS_d{slab_thickness}_{opposite_direction}_{config}", rcs_name=f"rcs_{direction}_{config}"
            )
            created_slabs[slab_key][f"slab_{opposite_direction}"] = slab

            # Create reinforcement bars for this slab
            _create_reinforcement_bars(slab, direction, reinf_config, mat_reinf)

    return created_slabs


def _get_load_case_dataframe(scia_results_dict: dict[str, pd.DataFrame], key: str) -> pd.DataFrame:
    """Get a load case dataframe from SCIA results, returning empty DataFrame if None."""
    load_case_df = scia_results_dict.get(key)
    return load_case_df if load_case_df is not None else pd.DataFrame()


def _process_node_dataframes(dataframes: list[pd.DataFrame]) -> None:
    """Process node dataframes: filter names and add moment columns."""
    for df in dataframes:
        if df is not None and not df.empty and "name" in df.columns:
            df["name"] = df["name"].str[1:].str.replace("_", "-")

        # Add moment columns - select value with maximum absolute magnitude while preserving sign
        if df is not None and not df.empty:
            if all(col in df.columns for col in ["m_xD+_max", "m_xD-_max"]):
                df["Mx"] = df[["m_xD+_max", "m_xD-_max"]].apply(lambda row: row.loc[row.abs().idxmax()], axis=1)
            if all(col in df.columns for col in ["m_yD+_max", "m_yD-_max"]):
                df["My"] = df[["m_yD+_max", "m_yD-_max"]].apply(lambda row: row.loc[row.abs().idxmax()], axis=1)


def _rename_dataframe_columns(df: pd.DataFrame, prefix: str) -> pd.DataFrame:
    """Rename columns in dataframe with prefix, excluding specific columns."""
    if df is not None and not df.empty:
        return df.rename(columns=lambda x: f"{prefix}_{x}" if x not in ["name", "coords_xyz"] else x)
    return df


def _process_scia_node_results_for_idea_input(scia_results_dict: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Process SCIA node results into a single merged dataframe.

    :param scia_results_dict: Dictionary containing SCIA node results for different load cases
    :returns: Merged dataframe with all load cases
    :rtype: pd.DataFrame
    """
    # Get load cases from SCIA results with node prefixes
    df_uls = _get_load_case_dataframe(scia_results_dict, "node_ULS")
    df_sls_kar = _get_load_case_dataframe(scia_results_dict, "node_SLS kar")
    df_sls_freq = _get_load_case_dataframe(scia_results_dict, "node_SLS freq")

    # Process all dataframes
    _process_node_dataframes([df_uls, df_sls_kar, df_sls_freq])

    # Rename columns to prevent clashes
    df_uls = _rename_dataframe_columns(df_uls, "ULS")
    df_sls_kar = _rename_dataframe_columns(df_sls_kar, "SLS_kar")
    df_sls_freq = _rename_dataframe_columns(df_sls_freq, "SLS_freq")

    # Merge dataframes - handle empty cases
    if df_uls.empty or df_sls_kar.empty or df_sls_freq.empty:
        return pd.DataFrame()  # Return empty DataFrame if any component is empty

    df_all = df_uls.merge(df_sls_kar, on=["name", "coords_xyz"], how="inner")
    return df_all.merge(df_sls_freq, on=["name", "coords_xyz"], how="inner")


def _process_scia_cs_results_for_idea_input(scia_results_dict: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Process SCIA CS (Cross Section) results into a single merged dataframe.

    CS results come from SCIA section on plane objects (cross sections) and contain
    force/moment values per meter. After zone mapping and deduplication, they are
    similar in structure to node results.

    :param scia_results_dict: Dictionary containing SCIA CS results for different load cases
    :returns: Merged dataframe with all load cases
    :rtype: pd.DataFrame
    """
    # Get load cases from SCIA results with cs prefixes
    df_uls = _get_load_case_dataframe(scia_results_dict, "cs_ULS")
    df_sls_kar = _get_load_case_dataframe(scia_results_dict, "cs_SLS kar")
    df_sls_freq = _get_load_case_dataframe(scia_results_dict, "cs_SLS freq")

    # Check if zone column exists (it should after zone mapping)
    # If it exists, use it as the 'name' for matching with slabs
    for df in [df_uls, df_sls_kar, df_sls_freq]:
        if df is not None and not df.empty and "zone" in df.columns:
            # For CS results, the zone IS the name we want to use for matching
            # The original 'name' column contains SCIA load case names which we don't need
            df["name"] = df["zone"]

    # Add moment columns - select value with maximum absolute magnitude while preserving sign
    for df in [df_uls, df_sls_kar, df_sls_freq]:
        if df is not None and not df.empty:
            if all(col in df.columns for col in ["m_xD+", "m_xD-"]):
                df["Mx"] = df[["m_xD+", "m_xD-"]].apply(lambda row: row.loc[row.abs().idxmax()], axis=1)
            if all(col in df.columns for col in ["m_yD+", "m_yD-"]):
                df["My"] = df[["m_yD+", "m_yD-"]].apply(lambda row: row.loc[row.abs().idxmax()], axis=1)

    # Rename columns to prevent clashes
    df_uls = _rename_dataframe_columns(df_uls, "ULS")
    df_sls_kar = _rename_dataframe_columns(df_sls_kar, "SLS_kar")
    df_sls_freq = _rename_dataframe_columns(df_sls_freq, "SLS_freq")

    # Merge dataframes - handle empty cases
    if df_uls.empty or df_sls_kar.empty or df_sls_freq.empty:
        return pd.DataFrame()  # Return empty DataFrame if any component is empty

    # For CS results, merge on 'name' (zone) only, since coords_xyz may vary within same zone
    # after deduplication, but we want to use all unique zone results
    df_all = df_uls.merge(df_sls_kar, on="name", how="inner", suffixes=("", "_kar"))
    df_all = df_all.merge(df_sls_freq, on="name", how="inner", suffixes=("", "_freq"))

    # Clean up duplicate coords_xyz columns if they exist
    if "coords_xyz_kar" in df_all.columns:
        df_all = df_all.drop(columns=["coords_xyz_kar"])
    if "coords_xyz_freq" in df_all.columns:
        df_all = df_all.drop(columns=["coords_xyz_freq"])

    return df_all


def _process_scia_integration_strip_results_for_idea_input(scia_results_dict: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Process SCIA integration strip results into a single merged dataframe.

    The individual DataFrames should already be processed (grouped by 'name' and 'dx',
    with 'Belasting' values merged and absolute maximum values for force/moment columns).
    This function just merges the load cases.

    :param scia_results_dict: Dictionary containing SCIA integration strip results for different load cases
    :returns: Merged dataframe with all load cases
    :rtype: pd.DataFrame
    """
    # Get load cases from SCIA results with strip prefixes and add fallback for None values
    df_uls = scia_results_dict.get("strip_ULS")
    if df_uls is None:
        df_uls = pd.DataFrame()

    df_sls_kar = scia_results_dict.get("strip_SLS kar")
    if df_sls_kar is None:
        df_sls_kar = pd.DataFrame()

    df_sls_freq = scia_results_dict.get("strip_SLS freq")
    if df_sls_freq is None:
        df_sls_freq = pd.DataFrame()

    # Check if any dataframes are empty
    if df_uls.empty or df_sls_kar.empty or df_sls_freq.empty:
        return pd.DataFrame()

    # The DataFrames come from SCIA processor with Dutch column names, need to rename them
    # First rename the common columns (Naam -> name) and add load case prefixes

    # Rename common columns and Belasting to avoid conflicts
    df_uls_renamed = df_uls.rename(columns={"Naam": "name", "Belasting": "ULS_Belasting"})
    df_sls_kar_renamed = df_sls_kar.rename(columns={"Naam": "name", "Belasting": "SLS_kar_Belasting"})
    df_sls_freq_renamed = df_sls_freq.rename(columns={"Naam": "name", "Belasting": "SLS_freq_Belasting"})

    # Add load case prefixes to ALL force/moment columns to avoid conflicts during merge
    # The columns are already named like v_y_max, v_z_max, m_x_max, m_y_max, m_z_max
    force_moment_columns = ["v_y_max", "v_z_max", "m_x_max", "m_y_max", "m_z_max"]

    # Also rename coordinate and direction columns to avoid conflicts
    other_columns_to_rename = ["coords_start", "coords_end", "direction_vector"]
    all_columns_to_rename = force_moment_columns + other_columns_to_rename

    for col in all_columns_to_rename:
        if col in df_uls_renamed.columns:
            df_uls_renamed = df_uls_renamed.rename(columns={col: f"ULS_{col}"})
        if col in df_sls_kar_renamed.columns:
            df_sls_kar_renamed = df_sls_kar_renamed.rename(columns={col: f"SLS_kar_{col}"})
        if col in df_sls_freq_renamed.columns:
            df_sls_freq_renamed = df_sls_freq_renamed.rename(columns={col: f"SLS_freq_{col}"})

    # Use 'name' and 'dx' columns for merging (renamed from 'Naam')
    merge_columns = ["name", "dx"]

    df_temp = df_uls_renamed.merge(df_sls_kar_renamed, on=merge_columns, how="inner")
    return df_temp.merge(df_sls_freq_renamed, on=merge_columns, how="inner")


def _apply_integration_strip_loads_to_slabs(created_slabs: dict[str, dict], df_all: pd.DataFrame, builder: Any) -> None:  # noqa: ANN401
    """
    Apply load cases from SCIA integration strip results to each slab.

    :param created_slabs: Dictionary of created slabs with zones and slab objects
    :type created_slabs: dict[str, dict]
    :param df_all: Merged dataframe with all load cases and strip data
    :type df_all: pd.DataFrame
    :param builder: IDEA model builder instance
    :type builder: Any
    """
    if df_all.empty:
        return

    for slab_key, slab_data in created_slabs.items():
        zones = slab_data.get("zones") or []

        if not zones:
            continue

        # Filter df_all to only include strips that belong to this slab's zones
        matching_strips = _find_matching_strips(df_all, zones)

        if not matching_strips:
            continue

        desc_prefix = slab_key.replace(".", "_")

        for direction in ["langs", "dwars"]:
            slab = slab_data.get(f"slab_{direction}")

            if slab is not None:
                _apply_strip_loads_to_slab_direction(slab, matching_strips, desc_prefix, direction, builder)


def _extract_zone_name_from_strip(strip_name: str) -> str:
    """
    Extract zone name from strip name and convert format.

    Example: "strip_Z3_1_(5.0, -1.5, 0)_(5.0, -10.5, 0)" -> "3-1"
    """
    try:
        # Remove "strip_" prefix and extract zone part
        if strip_name.startswith("strip_Z"):
            zone_part = strip_name[7:]  # Remove "strip_Z"
            # Find the first underscore followed by coordinates
            coord_start = zone_part.find("_(")
            if coord_start > 0:
                zone_id = zone_part[:coord_start]  # e.g., "3_1"
                return zone_id.replace("_", "-")  # Convert "3_1" to "3-1"
    except Exception:
        pass
    return ""


def _find_matching_strips(df_all: pd.DataFrame, zones: list[str]) -> list:
    """Find strips that belong to the specified zones."""
    matching_strips = []

    for _, row in df_all.iterrows():
        strip_name = row.get("name", "")
        zone_name = _extract_zone_name_from_strip(strip_name)

        if zone_name in zones:
            matching_strips.append(row)

    return matching_strips


def _create_idea_loading_objects(row: pd.Series, moment_component: str, builder: Any) -> tuple:  # noqa: ANN401
    """
    Create IDEA RCS loading objects from strip result row using builder pattern.

    :param row: DataFrame row with load results
    :type row: pd.Series
    :param moment_component: Moment component name (e.g., "m_y")
    :type moment_component: str
    :param builder: IDEA model builder instance
    :type builder: Any
    :returns: Tuple of (characteristic, frequent, fundamental) loadings
    :rtype: tuple
    """
    # Create characteristic SLS loading
    internal_forces_char = builder.create_result_of_internal_forces(
        Qz=row.get("SLS_kar_v_z_max", 0),
        My=row.get(f"SLS_kar_{moment_component}", 0),
    )
    char = builder.create_loading_sls(internal_forces_char)

    # Create frequent SLS loading
    internal_forces_freq = builder.create_result_of_internal_forces(
        Qz=row.get("SLS_freq_v_z_max", 0),
        My=row.get(f"SLS_freq_{moment_component}", 0),
    )
    freq = builder.create_loading_sls(internal_forces_freq)

    # Create fundamental ULS loading
    internal_forces_fund = builder.create_result_of_internal_forces(
        Qz=row.get("ULS_v_z_max", 0),
        My=row.get(f"ULS_{moment_component}", 0),
    )
    fund = builder.create_loading_uls(internal_forces_fund)

    return char, freq, fund


def _apply_strip_loads_to_slab_direction(slab: Any, matching_strips: list, desc_prefix: str, direction: str, builder: Any) -> None:  # noqa: ANN401
    """
    Apply strip loads to a slab in a specific direction.

    :param slab: Slab object to apply loads to
    :type slab: Any
    :param matching_strips: List of strip results
    :type matching_strips: list
    :param desc_prefix: Description prefix for load cases
    :type desc_prefix: str
    :param direction: Direction ("langs" or "dwars")
    :type direction: str
    :param builder: IDEA model builder instance
    :type builder: Any
    """
    # For integration strips: always use v_z_max as shear (Qz)
    # For moments, determine component based on the strip's direction vector:
    # - if direction vector is (1, 0, 0) or (-1, 0, 0) use m_y_max for langs, m_x_max for dwars
    # - if direction vector is (0, 1, 0) or (0, -1, 0) use m_x_max for langs, m_y_max for dwars
    # This is based on the orientation of the strip and how IDEA RCS expects the moments

    if not matching_strips:
        return

    for row in matching_strips:
        # Debug row data
        strip_name = row.get("name", "Unknown")

        # Get the normalized direction vector from the strip data
        # Try the different possible column names based on load case
        direction_vector = (
            row.get("ULS_direction_vector")
            or row.get("SLS_kar_direction_vector")
            or row.get("SLS_freq_direction_vector")
            or (1.0, 0.0, 0.0)  # Default to x-direction if not found
        )

        # Determine moment component based on strip orientation and slab direction
        if abs(direction_vector[0]) > 0.7:  # Strip is primarily in X-direction (longitudinal)
            moment_component = "m_y_max" if direction == "langs" else "m_x_max"
        elif abs(direction_vector[1]) > 0.7:  # Strip is primarily in Y-direction (transverse)
            moment_component = "m_x_max" if direction == "langs" else "m_y_max"
        else:
            # Error for diagonal or unclear orientations - this indicates a problem with strip geometry
            msg = (
                f"Invalid strip orientation detected for strip '{strip_name}'. "
                f"Direction vector {direction_vector} is not aligned with X or Y axis. "
                f"Integration strips should be aligned with bridge coordinate axes."
            )
            raise ValueError(msg)

        # Create loading objects using builder
        char, freq, fund = _create_idea_loading_objects(row, moment_component, builder)

        zone_name = _extract_zone_name_from_strip(strip_name)
        dx_value = row.get("dx", 0)
        description = f"{desc_prefix} - {zone_name} - {strip_name} - dx={dx_value:.3f}"

        with contextlib.suppress(Exception):
            builder.create_extreme_on_slab(slab, description=description, characteristic=char, frequent=freq, fundamental=fund)


def _apply_node_loads_to_slabs(created_slabs: dict[str, dict], df_all: pd.DataFrame, builder: Any) -> None:  # noqa: ANN401
    """
    Apply load cases from SCIA node results to each slab using builder pattern.

    :param created_slabs: Dictionary of created slabs with zones and slab objects
    :type created_slabs: dict[str, dict]
    :param df_all: Merged dataframe with all load cases
    :type df_all: pd.DataFrame
    :param builder: IDEA model builder instance
    :type builder: Any
    """
    # For langs cs link IDEA vz to scia vy and IDEA My to scia My
    # For dwars cs link IDEA vz to scia vx and IDEA My to scia Mx
    # Direction → axis + corresponding moment component
    orient = {
        "langs": {"axis": "y", "moment": "My"},
        "dwars": {"axis": "x", "moment": "Mx"},
    }

    def _format_coords(coords: list | tuple | str | float | None) -> str:
        if coords is None:
            return "No coords"
        if isinstance(coords, (list, tuple)):
            return f"({', '.join(map(str, coords))})"
        return str(coords)

    for slab_key, slab_data in created_slabs.items():
        zones = slab_data.get("zones") or []
        if not zones:
            continue

        df_slab = df_all[df_all["name"].isin(zones)]
        if df_slab.empty:
            continue

        desc_prefix = slab_key.replace(".", "_")

        for direction, cfg in orient.items():
            slab = slab_data.get(f"slab_{direction}")
            if slab is None:
                continue

            axis = cfg["axis"]  # "x" or "y"

            for _, row in df_slab.iterrows():
                # Build internal forces with dynamic moment component (vx/y and Mx/My) using builder
                internal_forces_char = builder.create_result_of_internal_forces(
                    Qz=row.get(f"SLS_kar_v_{axis}_max", 0),
                    My=row.get(f"SLS_kar_M{axis}", 0),
                )
                char = builder.create_loading_sls(internal_forces_char)

                internal_forces_freq = builder.create_result_of_internal_forces(
                    Qz=row.get(f"SLS_freq_v_{axis}_max", 0),
                    My=row.get(f"SLS_freq_M{axis}", 0),
                )
                freq = builder.create_loading_sls(internal_forces_freq)

                internal_forces_fund = builder.create_result_of_internal_forces(
                    Qz=row.get(f"ULS_v_{axis}_max", 0),
                    My=row.get(f"ULS_M{axis}", 0),
                )
                fund = builder.create_loading_uls(internal_forces_fund)

                name = row.get("name", "Unknown")
                coords_str = _format_coords(row.get("coords_xyz"))
                description = f"{desc_prefix} - {name} - node_{coords_str}"

                builder.create_extreme_on_slab(slab, description=description, characteristic=char, frequent=freq, fundamental=fund)


def _apply_cs_loads_to_slabs(created_slabs: dict[str, dict], df_all: pd.DataFrame, builder: Any) -> None:  # noqa: ANN401
    """
    Apply load cases from SCIA CS (Cross Section) results to each slab using builder pattern.

    CS results are similar to node results but come from section on plane objects.
    Like node results, we map forces based on slab direction.

    :param created_slabs: Dictionary of created slabs with zones and slab objects
    :type created_slabs: dict[str, dict]
    :param df_all: Merged dataframe with all load cases
    :type df_all: pd.DataFrame
    :param builder: IDEA model builder instance
    :type builder: Any
    """
    # For langs cs link IDEA vz to scia vy and IDEA My to scia My
    # For dwars cs link IDEA vz to scia vx and IDEA My to scia Mx
    # Direction → axis + corresponding moment component
    orient = {
        "langs": {"axis": "y", "moment": "My"},
        "dwars": {"axis": "x", "moment": "Mx"},
    }

    def _format_coords(coords: list | tuple | str | float | None) -> str:
        if coords is None:
            return "No coords"
        if isinstance(coords, (list, tuple)):
            return f"({', '.join(map(str, coords))})"
        return str(coords)

    for slab_key, slab_data in created_slabs.items():
        zones = slab_data.get("zones") or []
        if not zones:
            continue

        df_slab = df_all[df_all["name"].isin(zones)]
        if df_slab.empty:
            continue

        desc_prefix = slab_key.replace(".", "_")

        for direction, cfg in orient.items():
            slab = slab_data.get(f"slab_{direction}")
            if slab is None:
                continue

            axis = cfg["axis"]  # "x" or "y"

            for _, row in df_slab.iterrows():
                # Build internal forces with dynamic moment component (vx/y and Mx/My) using builder
                internal_forces_char = builder.create_result_of_internal_forces(
                    Qz=row.get(f"SLS_kar_v_{axis}", 0),
                    My=row.get(f"SLS_kar_M{axis}", 0),
                )
                char = builder.create_loading_sls(internal_forces_char)

                internal_forces_freq = builder.create_result_of_internal_forces(
                    Qz=row.get(f"SLS_freq_v_{axis}", 0),
                    My=row.get(f"SLS_freq_M{axis}", 0),
                )
                freq = builder.create_loading_sls(internal_forces_freq)

                internal_forces_fund = builder.create_result_of_internal_forces(
                    Qz=row.get(f"ULS_v_{axis}", 0),
                    My=row.get(f"ULS_M{axis}", 0),
                )
                fund = builder.create_loading_uls(internal_forces_fund)

                name = row.get("name", "Unknown")
                coords_str = _format_coords(row.get("coords_xyz"))
                description = f"{desc_prefix} - {name} - cs_{coords_str}"

                builder.create_extreme_on_slab(slab, description=description, characteristic=char, frequent=freq, fundamental=fund)


def create_bridge_idea_model(params: Any, entity_id: int, scia_results_dict: dict[str, pd.DataFrame] | None = None) -> "Model":  # noqa: ANN401
    """
    Create IDEA StatiCa RCS model from bridge parameters.

    This is a backward-compatible wrapper that extracts data from BridgeParametrization
    and delegates to the refactored implementation.

    Note: params type is Any to avoid circular import with app layer.

    :param params: BridgeParametrization object containing all bridge input parameters
    :type params: Any
    :param entity_id: Entity ID for caching (used if scia_results_dict is None)
    :type entity_id: int
    :param scia_results_dict: Pre-computed SCIA results, if None will fetch from cache
    :type scia_results_dict: dict[str, pd.DataFrame] | None
    :returns: IDEA RCS model object
    :rtype: Model
    :raises ValueError: If parameters are invalid
    :raises ImportError: If VIKTOR IDEA module is not available
    """
    # Import here to avoid circular import
    from src.integrations.idea_integration.idea_data_models import extract_bridge_idea_input_data

    input_data = extract_bridge_idea_input_data(params)
    input_data = BridgeIdeaInputData(
        entity_id=entity_id,
        bridge_name=input_data.bridge_name,
        concrete_strength_class=input_data.concrete_strength_class,
        steel_quality=input_data.steel_quality,
        reinforcement_zones=input_data.reinforcement_zones,
        bridge_segments=input_data.bridge_segments,
        geometry_config=input_data.geometry_config,
    )

    # Create builder instance (app layer dependency - acceptable at entry point)
    from app.bridge.idea_model_builder import ViktorIdeaModelBuilder

    builder = ViktorIdeaModelBuilder()

    # Get SCIA results - either passed in or fetch from cache
    if scia_results_dict is None:
        # Import here to avoid circular imports only when needed
        from app.bridge.analysis_cache import get_scia_results_for_idea

        scia_results_dict = get_scia_results_for_idea(params, entity_id=entity_id)

    # Create IDEA model with materials using builder
    model, cs_mat, mat_reinf = _create_idea_model_with_concrete_and_reinforcement_materials(input_data, builder)

    # Create slabs with reinforcement using builder
    created_slabs = _create_slabs_with_reinforcement(input_data, model, cs_mat, mat_reinf, builder)

    # Process SCIA node results for idea input
    df_node_all = _process_scia_node_results_for_idea_input(scia_results_dict)
    # Apply node loads to slabs using builder
    _apply_node_loads_to_slabs(created_slabs, df_node_all, builder)

    # Process SCIA CS (Cross Section) results for idea input
    df_cs_all = _process_scia_cs_results_for_idea_input(scia_results_dict)
    # Apply CS loads to slabs using builder
    _apply_cs_loads_to_slabs(created_slabs, df_cs_all, builder)

    # Process SCIA integration strip results for idea input
    df_strip_all = _process_scia_integration_strip_results_for_idea_input(scia_results_dict)
    # Apply integration strip loads to slabs using builder
    _apply_integration_strip_loads_to_slabs(created_slabs, df_strip_all, builder)

    return model


def run_idea_analysis(model: "Model", timeout: int = 300) -> "File":
    """
    Run IDEA StatiCa analysis on the provided model.

    Note: This function uses direct SDK import for analysis execution, which is acceptable
    as analysis execution is separate from model building. The src layer is SDK-independent
    for model building, but analysis execution requires the VIKTOR SDK.

    :param model: IDEA RCS model object
    :type model: Model
    :param timeout: Analysis timeout in seconds
    :type timeout: int
    :returns: Analysis output file object
    :rtype: File
    :raises ImportError: If VIKTOR IDEA module is not available
    :raises RuntimeError: If analysis execution fails
    """
    # Direct SDK import for analysis execution (acceptable technical debt)

    # Generate XML input for analysis
    xml_input = model.generate_xml_input()

    # Create and execute analysis
    analysis = idea_rcs.IdeaRcsAnalysis(xml_input, return_rcs_file=True)
    analysis.execute(timeout)

    return analysis.get_idea_rcs_file()
