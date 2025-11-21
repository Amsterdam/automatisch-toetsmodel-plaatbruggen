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
from src.integrations.idea_integration.scia_to_idea_functions import process_scia_cs_results_for_idea
from viktor.external import idea_rcs

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


def _process_scia_cs_results_for_idea_input(
    scia_envelope_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Process SCIA CS (Cross Section) envelope DataFrame for IDEA input.

    The input DataFrame comes from process_scia_cs_results_for_idea and contains
    filtered envelope data with ULS and SLS freq results combined. Each row represents
    a maximum absolute force/moment value for a specific zone and result type.

    Each row will be translated into load cases for both directions (langs/dwars) in IDEA.

    Columns in input:
    - v_x_max, v_y_max, m_xD+_max, m_xD-_max, m_yD+_max, m_yD-_max, n_xD_max, n_yD_max
    - name, zone, coords_xyz, belasting, max_for_column, result_type (ULS or SLS freq)

    :param scia_envelope_df: DataFrame with CS envelope results from process_scia_cs_results_for_idea
    :type scia_envelope_df: pd.DataFrame
    :returns: Processed dataframe ready for IDEA load application (same as input, just validated)
    :rtype: pd.DataFrame
    """
    if scia_envelope_df.empty:
        return pd.DataFrame()

    # Add Mx and My columns - select value with maximum absolute magnitude while preserving sign
    df_processed = scia_envelope_df.copy()

    if all(col in df_processed.columns for col in ["m_xD+_max", "m_xD-_max"]):
        df_processed["Mx"] = df_processed[["m_xD+_max", "m_xD-_max"]].apply(lambda row: row.loc[row.abs().idxmax()], axis=1)

    if all(col in df_processed.columns for col in ["m_yD+_max", "m_yD-_max"]):
        df_processed["My"] = df_processed[["m_yD+_max", "m_yD-_max"]].apply(lambda row: row.loc[row.abs().idxmax()], axis=1)

    # Add normal force columns (Nx, Ny) if present
    if "n_xD_max" in df_processed.columns:
        df_processed["Nx"] = df_processed["n_xD_max"]
    if "n_yD_max" in df_processed.columns:
        df_processed["Ny"] = df_processed["n_yD_max"]

    return df_processed


def _apply_cs_loads_to_slabs(  # noqa: C901
    created_slabs: dict[str, dict],
    df_all: pd.DataFrame,
    builder: Any,  # noqa: ANN401
) -> None:
    """
    Apply load cases from SCIA CS (Cross Section) envelope results to each slab using builder pattern.

    For each unique zone and direction (langs/dwars), creates ONE extreme combining:
    - ULS row for that zone
    - SLS freq row for that zone

    Each extreme has:
    - Shear forces (v_x or v_y depending on direction) → Qz in IDEA
    - Bending moments (Mx or My depending on direction) → My in IDEA
    - Normal forces (Nx or Ny depending on direction) → N in IDEA (if supported)

    :param created_slabs: Dictionary of created slabs with zones and slab objects
    :type created_slabs: dict[str, dict]
    :param df_all: Envelope dataframe with ULS and SLS freq results (individual rows per result_type)
    :type df_all: pd.DataFrame
    :param builder: IDEA model builder instance
    :type builder: Any
    """
    # Early return if dataframe is empty
    if df_all.empty:
        return

    # For langs cs: link IDEA vz to SCIA vy and IDEA My to SCIA My
    # For dwars cs: link IDEA vz to SCIA vx and IDEA My to SCIA Mx
    orient = {
        "langs": {"shear": "v_y_max", "moment": "My", "normal": "Ny"},
        "dwars": {"shear": "v_x_max", "moment": "Mx", "normal": "Nx"},
    }

    def _format_coords(coords: list | tuple | str | float | None) -> str:
        if coords is None:
            return "No_coords"
        if isinstance(coords, (list, tuple)):
            return f"({','.join(str(c) for c in coords)})"
        return str(coords)

    for slab_key, slab_data in created_slabs.items():
        zones = slab_data.get("zones") or []
        if not zones:
            continue

        df_slab = df_all[df_all["zone"].isin(zones)]
        if df_slab.empty:
            continue

        desc_prefix = slab_key.replace(".", "_")

        # Get unique combinations of (zone, max_for_column)
        unique_combinations = df_slab[["zone", "max_for_column"]].drop_duplicates()

        for _, combo_row in unique_combinations.iterrows():
            zone = combo_row["zone"]
            max_for = combo_row["max_for_column"]

            # Filter data for this specific (zone, max_for_column) combination
            df_combo = df_slab[(df_slab["zone"] == zone) & (df_slab["max_for_column"] == max_for)]

            # Split by result_type
            df_uls = df_combo[df_combo["result_type"] == "ULS"]
            df_sls = df_combo[df_combo["result_type"] == "SLS freq"]

            # Get the rows (should be one ULS and one SLS freq for this combination)
            uls_row = df_uls.iloc[0]
            sls_row = df_sls.iloc[0]

            # Create extremes for both directions
            for direction, cfg in orient.items():
                slab = slab_data.get(f"slab_{direction}")
                if slab is None:
                    continue

                shear_col = cfg["shear"]
                moment_col = cfg["moment"]
                normal_col = cfg["normal"]

                # Get ULS values
                qz_uls = uls_row.get(shear_col, 0)
                my_uls = uls_row.get(moment_col, 0)
                n_uls = uls_row.get(normal_col, 0)

                # Get SLS freq values
                qz_freq = sls_row.get(shear_col, 0)
                my_freq = sls_row.get(moment_col, 0)
                n_freq = sls_row.get(normal_col, 0)

                # Build description
                cs_name = uls_row.get("name", "Unknown")
                coords = _format_coords(uls_row.get("coords_xyz"))
                belasting_uls = uls_row.get("belasting", "Unknown")
                belasting_sls = sls_row.get("belasting", "Unknown")

                description = f"{desc_prefix}_{direction}-{zone}-{cs_name}-{coords}-{max_for}-ULS:{belasting_uls}/SLS:{belasting_sls}"

                # Create internal forces for ULS (fundamental)
                try:
                    internal_forces_fund = builder.create_result_of_internal_forces(
                        Qz=qz_uls,
                        My=my_uls,
                        N=n_uls,
                    )
                except TypeError:
                    # Builder doesn't support N parameter
                    internal_forces_fund = builder.create_result_of_internal_forces(
                        Qz=qz_uls,
                        My=my_uls,
                    )
                fund = builder.create_loading_uls(internal_forces_fund)

                # Create internal forces for SLS freq (frequent)
                try:
                    internal_forces_freq = builder.create_result_of_internal_forces(
                        Qz=qz_freq,
                        My=my_freq,
                        N=n_freq,
                    )
                except TypeError:
                    # Builder doesn't support N parameter
                    internal_forces_freq = builder.create_result_of_internal_forces(
                        Qz=qz_freq,
                        My=my_freq,
                    )
                freq = builder.create_loading_sls(internal_forces_freq)

                # Create the extreme combining ULS and SLS freq
                builder.create_extreme_on_slab(
                    slab,
                    description=description,
                    frequent=freq,
                    fundamental=fund,
                )


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

    # Process SCIA CS (Cross Section) envelope results for IDEA input
    # Check if envelope DataFrame is already provided (from cache)
    if "cs_envelope" in scia_results_dict and scia_results_dict["cs_envelope"] is not None:
        df_cs_envelope = scia_results_dict["cs_envelope"]
    else:
        # Process SCIA results to get envelope DataFrame
        # Get the results dict, ensuring it's a dict type
        results_data_raw: pd.DataFrame | dict[str, Any] = scia_results_dict.get("results", {})
        results_data: dict[str, Any] = results_data_raw if isinstance(results_data_raw, dict) else {}
        df_cs_envelope = process_scia_cs_results_for_idea(results_data, input_data.bridge_segments)

    # Process the envelope DataFrame for IDEA input (merges ULS and SLS freq)
    df_cs_all = _process_scia_cs_results_for_idea_input(df_cs_envelope)

    # Apply CS loads to slabs using builder
    _apply_cs_loads_to_slabs(created_slabs, df_cs_all, builder)

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
