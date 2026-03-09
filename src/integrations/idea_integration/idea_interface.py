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

from collections import defaultdict
from typing import TYPE_CHECKING, Any

import pandas as pd
from viktor.external import idea_rcs

from src.common.constants.technical import MM_TO_M
from src.data_models.idea_models import ReinforcementConfigData
from src.geometry.bridge_geometry_data import create_node_and_thickness_dict
from src.integrations.idea_integration.constants.geometry import (
    MIDPOINT_DIVISOR,
    REBAR_POSITION_HALF_OFFSET,
    SLAB_EDGE_SPACE_BOUNDARY,
    SLAB_WIDTH,
)
from src.integrations.idea_integration.constants.materials import DEFAULT_REBAR_POSITION_BASE
from src.integrations.idea_integration.constants.units import M_TO_MM_IDEA
from src.integrations.idea_integration.idea_data_models import (
    BridgeGeometryConfig,
    BridgeIdeaInputData,
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


def _get_unique_matching_zone_keys(  # noqa: C901
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
    class SegmentWrapper:
        """Wrapper to provide attribute access to segment dictionaries."""

        def __init__(self, segment_dict: dict) -> None:
            self._data = segment_dict

        def __getattr__(self, name: str) -> Any:  # noqa: ANN401
            """Allow attribute-style access to dictionary keys."""
            if name.startswith("_"):
                raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
            return self._data.get(name)

    class TempParams:
        def __init__(self, segments: list) -> None:
            # Wrap dictionaries to provide attribute access
            self.bridge_segments_array = [SegmentWrapper(seg) if isinstance(seg, dict) else seg for seg in segments]

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
    """Calculate positions for longitudinal reinforcement using exact spacing."""
    n_rebars = width / hoh  # Use exact fractional value
    if n_rebars < 1:
        return []

    # Use exact requested hoh spacing
    actual_hoh = hoh
    positions = []

    # Round to nearest integer for determining layout pattern
    n_rebars_int = round(n_rebars)

    if n_rebars_int % 2 == 0:  # Even number of rebars
        for i in range(n_rebars_int // 2):
            offset = (i + REBAR_POSITION_HALF_OFFSET) * actual_hoh
            positions.extend([-offset, offset])
    else:  # Odd number of rebars
        positions = [0]  # Center rebar
        for i in range(1, (n_rebars_int + 1) // 2):
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
        midpoint = (positions[i] + positions[i + 1]) / MIDPOINT_DIVISOR
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
    thickness_mm = slab_thickness * M_TO_MM_IDEA  # Convert thickness from m to mm
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
    config: ReinforcementConfigData,
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
            x / MM_TO_M for x in calculate_rebar_positions(DEFAULT_REBAR_POSITION_BASE, config.main_reinf_ctc_distances[f"{location}_{direction}"])
        ]  # Convert positions from mm to m
        bar_locations_y = [config.reinf_heights[f"{location}_{direction}"] / MM_TO_M] * len(bar_locations_x)  # Convert heights from mm to m
        bar_diameters = [config.main_reinf_diameters[f"{location}_{direction}"] / MM_TO_M] * len(bar_locations_x)  # Convert diameters from mm to m
        bar_locations = list(zip(bar_locations_x, bar_locations_y))

        for coords, diameter in zip(bar_locations, bar_diameters):
            slab.create_bar(coords, diameter, mat_reinf)

        # Create additional reinforcement if needed (rebar_config is now a dict)
        if config.rebar_config.get("heeft_bijlegwapening", False):
            _create_additional_reinforcement(slab, f"{location}_{direction}", bar_locations_x, config, mat_reinf)


def _create_additional_reinforcement(
    slab: "OneWaySlab",
    location_direction: str,  # Combined "top_langs", "bottom_dwars", etc.
    main_bar_locations_x: list[float],
    config: ReinforcementConfigData,
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
    remaining_space = SLAB_EDGE_SPACE_BOUNDARY - loc_max_main_bar  # Remaining space at the end of the slab

    # Add extra bars at the beginning and end of the slab if there is enough space
    if remaining_space >= ctc_dist_main_bar:
        extra_bar_locations_x.append(loc_max_main_bar + ctc_dist_main_bar / MIDPOINT_DIVISOR)  # Insert at end
        extra_bar_locations_x.insert(0, loc_min_main_bar - ctc_dist_main_bar / MIDPOINT_DIVISOR)  # Insert at beginning

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

        # Create reinforcement configuration object using Pydantic model
        # Convert ReinforcementZoneConfig to dict for rebar_config field
        rebar_config_dict = {
            "heeft_bijlegwapening": rebar_config.heeft_bijlegwapening,
            "zone_number": rebar_config.zone_number,
        }
        reinf_config = ReinforcementConfigData(
            main_reinf_ctc_distances=main_reinf_ctc_distances,
            main_reinf_diameters=main_reinf_diameters,
            reinf_heights=reinf_heights,
            extra_reinf_diameter=extra_reinf_diameter,
            extra_reinf_ctc_distances=extra_reinf_ctc_distances,
            has_extra_reinforcement=rebar_config.heeft_bijlegwapening,
            rebar_config=rebar_config_dict,
        )

        # Create slab for each rebar direction
        for direction in ["langs", "dwars"]:
            # Create rectangular cross-section for the slab using builder
            # cs_dwars should be paired with rebar_langs and vice versa so we use opposite_direction here
            opposite_direction = "dwars" if direction == "langs" else "langs"
            cs = builder.create_rect_section(SLAB_WIDTH, slab_thickness)
            slab = builder.create_one_way_slab(
                model, cs, cs_mat, name=f"CS_d{slab_thickness}_{opposite_direction}_{config}", rcs_name=f"rcs_{direction}_{config}"
            )
            created_slabs[slab_key][f"slab_{opposite_direction}"] = slab

            # Create reinforcement bars for this slab
            _create_reinforcement_bars(slab, direction, reinf_config, mat_reinf)

    return created_slabs


def _apply_integration_strip_loads_to_slabs(  # noqa: C901
    created_slabs: dict[str, dict],
    df_strips: pd.DataFrame,
    builder: Any,  # noqa: ANN401
) -> int:
    """
    Apply load cases from integration strip envelope results to each slab using builder pattern.

    For each unique zone, direction, and filtered_for value, creates ONE extreme combining:
    - ULS row for that combination
    - SLS freq row for that combination

    Direction mapping:
    - X-direction strips (x_reg/x_sup) → dwars (transverse) cross-section in IDEA
    - Y-direction strips (y_reg/y_sup) → langs (longitudinal) cross-section in IDEA

    Force mapping (already done in process_integration_strips_for_idea):
    For X-direction strips (transverse/dwars):
    - N → N (normal force)
    - V_z → Qz (shear force)
    - M_x → My (bending moment)

    For Y-direction strips (longitudinal/langs):
    - N → N (normal force)
    - V_z → Qz (shear force)
    - M_y → My (bending moment)

    :param created_slabs: Dictionary of created slabs with zones and slab objects
    :type created_slabs: dict[str, dict]
    :param df_strips: DataFrame with integration strip results mapped to IDEA format (N, Qz, My)
    :type df_strips: pd.DataFrame
    :param builder: IDEA model builder instance
    :type builder: Any
    :returns: Number of extremes created
    :rtype: int
    """
    # Early return if dataframe is empty
    if df_strips.empty:
        return 0

    loads_applied = 0

    # Map strip direction to IDEA slab direction
    # X-strips (transverse) → dwars cross-section
    # Y-strips (longitudinal) → langs cross-section
    strip_to_slab_direction = {
        "x": "dwars",
        "y": "langs",
    }

    def _format_position(dx: float | None) -> str:
        """Format position value for description."""
        if dx is None or pd.isna(dx):
            return "NoPos"
        return f"{float(dx):.2f}m"

    for slab_key, slab_data in created_slabs.items():
        zones = slab_data.get("zones") or []
        if not zones:
            continue

        # Filter strips for zones in this slab
        df_slab = df_strips[df_strips["zone"].isin(zones)]
        if df_slab.empty:
            continue

        desc_prefix = slab_key.replace(".", "_")

        # Get unique combinations of (zone, direction, filtered_for)
        unique_combinations = df_slab[["zone", "direction", "filtered_for"]].drop_duplicates()

        for _, combo_row in unique_combinations.iterrows():
            zone = combo_row["zone"]
            strip_direction = combo_row["direction"]
            filtered_for = combo_row["filtered_for"]

            # Determine which slab to use based on strip direction
            slab_direction = strip_to_slab_direction.get(strip_direction)
            if slab_direction is None:
                continue

            slab = slab_data.get(f"slab_{slab_direction}")
            if slab is None:
                continue

            # Filter data for this specific combination
            df_combo = df_slab[(df_slab["zone"] == zone) & (df_slab["direction"] == strip_direction) & (df_slab["filtered_for"] == filtered_for)]

            # Split by limit_state
            df_uls = df_combo[df_combo["limit_state"] == "ULS"]
            df_sls = df_combo[df_combo["limit_state"] == "SLSfreq"]

            # Check if we have both ULS and SLS freq data
            if df_uls.empty or df_sls.empty:
                continue

            # Get the rows (should be one ULS and one SLS freq for this combination)
            uls_row = df_uls.iloc[0]
            sls_row = df_sls.iloc[0]

            # Extract forces (already mapped to IDEA format)
            # Convert numpy types to native Python floats for JSON serialization
            qz_uls = float(uls_row.get("Qz", 0))
            my_uls = float(uls_row.get("My", 0))
            n_uls = float(uls_row.get("N", 0))

            qz_sls = float(sls_row.get("Qz", 0))
            my_sls = float(sls_row.get("My", 0))
            n_sls = float(sls_row.get("N", 0))

            # Build description
            strip_name = uls_row.get("name", "Unknown")
            position_uls = _format_position(uls_row.get("dx"))
            position_sls = _format_position(sls_row.get("dx"))
            load_case_uls = uls_row.get("load_case", "Unknown")
            load_case_sls = sls_row.get("load_case", "Unknown")

            description = (
                f"{desc_prefix}_{slab_direction}-{zone}-{strip_name}-"
                f"{filtered_for}-ULS:{load_case_uls}@{position_uls}/SLS:{load_case_sls}@{position_sls}"
            )

            # Create internal forces for ULS (fundamental)
            internal_forces_fund = builder.create_result_of_internal_forces(
                Qz=qz_uls,
                My=my_uls,
                N=n_uls,
            )
            fund = builder.create_loading_uls(internal_forces_fund)

            # Create internal forces for SLS freq (frequent)
            internal_forces_freq = builder.create_result_of_internal_forces(
                Qz=qz_sls,
                My=my_sls,
                N=n_sls,
            )
            freq = builder.create_loading_sls(internal_forces_freq)

            # Create the extreme combining ULS and SLS freq
            builder.create_extreme_on_slab(
                slab,
                description=description,
                frequent=freq,
                fundamental=fund,
            )
            loads_applied += 1

    return loads_applied


def _apply_sections_on_plane_loads_to_slabs(
    created_slabs: dict[str, dict],
    df_sections: pd.DataFrame,
    builder: Any,  # noqa: ANN401
) -> int:
    """
    Apply load cases from sections-on-plane envelope results to each slab.

    For each unique (zone, direction, filtered_for) combination, creates ONE
    extreme combining ULS (fundamental) and SLS freq (frequent) data.

    Direction mapping — identical to the integration-strip convention:

    - X-direction sections → *dwars* (transverse) cross-section in IDEA
    - Y-direction sections → *langs* (longitudinal) cross-section in IDEA

    The ``df_sections`` DataFrame is expected to have already been processed by
    :func:`~scia_sections_on_plane_to_idea.process_sections_on_plane_for_idea`
    so that ``N``, ``Qz`` and ``My`` columns are present.

    :param created_slabs: Dictionary of created slabs with zones and slab objects
    :type created_slabs: dict[str, dict]
    :param df_sections: DataFrame with sections-on-plane results mapped to
                        IDEA format (N, Qz, My columns)
    :type df_sections: pd.DataFrame
    :param builder: IDEA model builder instance
    :type builder: Any
    :returns: Number of extremes created
    :rtype: int
    """
    if df_sections.empty:
        return 0

    loads_applied = 0

    # X-direction sections (transverse) → dwars slab
    # Y-direction sections (longitudinal) → langs slab
    section_to_slab_direction = {
        "x": "dwars",
        "y": "langs",
    }

    for slab_key, slab_data in created_slabs.items():
        zones = slab_data.get("zones") or []
        if not zones:
            continue

        df_slab = df_sections[df_sections["zone"].isin(zones)]
        if df_slab.empty:
            continue

        unique_combinations = df_slab[["zone", "direction", "filtered_for"]].drop_duplicates()

        for _, combo_row in unique_combinations.iterrows():
            zone = combo_row["zone"]
            section_direction = combo_row["direction"]
            filtered_for = combo_row["filtered_for"]

            slab_direction = section_to_slab_direction.get(section_direction)
            if slab_direction is None:
                continue

            slab = slab_data.get(f"slab_{slab_direction}")
            if slab is None:
                continue

            df_combo = df_slab[
                (df_slab["zone"] == zone)
                & (df_slab["direction"] == section_direction)
                & (df_slab["filtered_for"] == filtered_for)
            ]

            df_uls = df_combo[df_combo["limit_state"] == "ULS"]
            df_sls = df_combo[df_combo["limit_state"] == "SLSfreq"]

            if df_uls.empty or df_sls.empty:
                continue

            uls_row = df_uls.iloc[0]
            sls_row = df_sls.iloc[0]

            qz_uls = float(uls_row.get("Qz", 0.0))
            my_uls = float(uls_row.get("My", 0.0))
            n_uls = float(uls_row.get("N", 0.0))

            qz_sls = float(sls_row.get("Qz", 0.0))
            my_sls = float(sls_row.get("My", 0.0))
            n_sls = float(sls_row.get("N", 0.0))

            load_case_uls = uls_row.get("load_case", "Unknown")
            load_case_sls = sls_row.get("load_case", "Unknown")

            description = f"{zone}_{slab_direction}_{filtered_for}_ULS:{load_case_uls}_SLS:{load_case_sls}"

            internal_forces_fund = builder.create_result_of_internal_forces(
                Qz=qz_uls,
                My=my_uls,
                N=n_uls,
            )
            fund = builder.create_loading_uls(internal_forces_fund)

            internal_forces_freq = builder.create_result_of_internal_forces(
                Qz=qz_sls,
                My=my_sls,
                N=n_sls,
            )
            freq = builder.create_loading_sls(internal_forces_freq)

            builder.create_extreme_on_slab(
                slab,
                description=description,
                frequent=freq,
                fundamental=fund,
            )
            loads_applied += 1

    return loads_applied


def create_bridge_idea_model(params: Any, entity_id: int, scia_results_dict: dict[str, pd.DataFrame] | None = None) -> "Model":  # noqa: ANN401, C901, PLR0912
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

    # Validate that slabs were created
    if not created_slabs:
        from viktor.errors import UserError

        raise UserError(
            "Geen dwarsdoorsneden kunnen worden gemaakt voor IDEA model. "
            "Controleer of de wapeningszones overeenkomen met de brugsegmenten. "
            "Mogelijk zijn de parameters gewijzigd na een eerdere berekening - probeer de cache te wissen en opnieuw te berekenen."
        )

    # Determine which SCIA result type is available and prepare the IDEA force DataFrame
    results_data_raw: Any = scia_results_dict.get("results", {})
    results_data: dict[str, Any] = results_data_raw if isinstance(results_data_raw, dict) else {}

    use_integration_strips = False
    use_sections_on_plane = False
    df_strips_all = pd.DataFrame()
    df_sections_all = pd.DataFrame()

    # --- Try integration strips (integratiestroken) ---
    if "integration_strips" in scia_results_dict or "integration_strips" in results_data:
        try:
            from src.integrations.scia_integration.results.scia_integration_strips_to_idea import (
                process_integration_strips_for_idea,
            )

            df_strips_all = process_integration_strips_for_idea(results_data)
            if not df_strips_all.empty:
                use_integration_strips = True
        except (ValueError, KeyError) as e:
            import warnings

            warnings.warn(f"Integration strips verwerking mislukt: {e}.", stacklevel=2)

    # --- Try sections on plane (secties op vlak) if integration strips unavailable ---
    if not use_integration_strips and (
        "sections_on_plane" in scia_results_dict or "sections_on_plane" in results_data
    ):
        try:
            from src.integrations.scia_integration.results.scia_sections_on_plane_to_idea import (
                process_sections_on_plane_for_idea,
            )

            df_sections_all = process_sections_on_plane_for_idea(results_data)
            if not df_sections_all.empty:
                use_sections_on_plane = True
        except (ValueError, KeyError) as e:
            import warnings

            warnings.warn(f"Secties-op-vlak verwerking mislukt: {e}.", stacklevel=2)

    if not use_integration_strips and not use_sections_on_plane:
        from viktor.errors import UserError

        raise UserError(
            "Geen integratiestroken of secties-op-vlak resultaten beschikbaar in SCIA resultaten. "
            "IDEA model kan niet worden gegenereerd. "
            "Voer een nieuwe SCIA berekening uit met integratiestroken of secties op vlak."
        )

    # Apply loads to slabs
    if use_integration_strips:
        loads_applied = _apply_integration_strip_loads_to_slabs(created_slabs, df_strips_all, builder)
    else:
        loads_applied = _apply_sections_on_plane_loads_to_slabs(created_slabs, df_sections_all, builder)

    # Validate that loads were applied
    if loads_applied == 0:
        from viktor.errors import UserError

        slab_zones: set[str] = set()
        for slab_data in created_slabs.values():
            slab_zones.update(slab_data.get("zones", []))

        source_name = "integratiestroken" if use_integration_strips else "secties-op-vlak"
        source_df = df_strips_all if use_integration_strips else df_sections_all
        source_zones: set[str] = set(source_df["zone"].unique()) if "zone" in source_df.columns else set()

        raise UserError(
            f"Geen belastingen kunnen worden toegepast vanuit {source_name}. "
            f"Zones in brugsegmenten: {sorted(slab_zones)}, "
            f"Zones in {source_name}: {sorted(source_zones)}. "
            "De zones komen niet overeen - mogelijk zijn de brugsegmenten gewijzigd na een eerdere SCIA berekening. "
            "Wis de cache en voer een nieuwe SCIA berekening uit."
        )

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
