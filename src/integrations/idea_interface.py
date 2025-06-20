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
from typing import Any

from src.common.materials import get_default_materials


@dataclass
class BridgeCrossSectionData:
    """
    Data structure for bridge cross-section information extracted from bridge parameters.

    :param width: Width of the cross-section in meters
    :type width: float
    :param height: Height of the cross-section in meters
    :type height: float
    :param concrete_material: Concrete material grade
    :type concrete_material: str
    :param reinforcement_material: Reinforcement material grade
    :type reinforcement_material: str
    :param reinforcement_config: Dictionary containing reinforcement configuration
    :type reinforcement_config: dict[str, Any]
    """

    width: float
    height: float
    concrete_material: str
    reinforcement_material: str
    reinforcement_config: dict[str, Any]


@dataclass
class ReinforcementConfig:
    """
    Data structure for reinforcement configuration.

    :param main_bars_top: Top main reinforcement bars [(x, y, diameter), ...]
    :type main_bars_top: list[tuple[float, float, float]]
    :param main_bars_bottom: Bottom main reinforcement bars [(x, y, diameter), ...]
    :type main_bars_bottom: list[tuple[float, float, float]]
    :param concrete_cover: Concrete cover in meters
    :type concrete_cover: float
    """

    main_bars_top: list[tuple[float, float, float]]
    main_bars_bottom: list[tuple[float, float, float]]
    concrete_cover: float


def extract_cross_section_from_params(
    bridge_segments_params: list[dict[str, Any]], concrete_material: str | None = None, reinforcement_material: str | None = None
) -> BridgeCrossSectionData:
    """
    Extract bridge cross-section data from bridge segment parameters.

    Currently creates a simple rectangular cross-section:
    - Width: Uses width of first segment (bz1 + bz2 + bz3)
    - Height: Uses thickness of first segment (dz or dz_2)
    - Materials: Hardcoded defaults

    TODO: Future improvements:
    - Support multiple cross-sections along bridge length
    - Support for T-beam and box girder sections
    - Extract actual material grades from params.info
    - Handle different zone thicknesses properly

    :param bridge_segments_params: List of bridge segment parameter dictionaries
    :type bridge_segments_params: list[dict[str, Any]]
    :returns: Bridge cross-section data for IDEA model creation
    :rtype: BridgeCrossSectionData
    :raises ValueError: If bridge_segments_params is empty or invalid
    """
    if not bridge_segments_params:
        raise ValueError("No bridge segments provided")

    # Use first segment for cross-section definition
    first_segment = bridge_segments_params[0]
    bz1 = float(first_segment.get("bz1", 0))
    bz2 = float(first_segment.get("bz2", 0))
    bz3 = float(first_segment.get("bz3", 0))
    width = bz1 + bz2 + bz3

    if width <= 0:
        raise ValueError("Cross-section width must be positive")

    # Bridge deck thickness should be much smaller than structural height
    # For IDEA RCS analysis, we need the actual concrete deck thickness, not the full structural height
    # Extract actual deck thickness from construction height or use segment dimensions
    dz = float(first_segment.get("dz", 0.5))
    dz_2 = float(first_segment.get("dz_2", 0.5))

    # Use the maximum thickness from zones 1-3 vs zone 2
    # Limit to reasonable deck thickness (max 0.8m for slab analysis)
    thickness = min(max(dz, dz_2), 0.8)

    # Use provided materials or defaults from the centralized material system
    if concrete_material is None or reinforcement_material is None:
        defaults = get_default_materials()
        concrete_material = concrete_material or defaults["concrete"]
        reinforcement_material = reinforcement_material or defaults["reinforcement"]

    # Basic reinforcement configuration
    # Extract from actual reinforcement parameters from wapening zones
    # Use hoofdwapening_langs_boven/onder_diameter and hart_op_hart fields
    # For now using defaults: 12mm diameter with 150mm spacing
    bar_diameter_mm = 12.0
    spacing_mm = 150.0
    cover_mm = 55.0

    return BridgeCrossSectionData(
        width=width,
        height=thickness,
        concrete_material=concrete_material,
        reinforcement_material=reinforcement_material,
        reinforcement_config={
            "main_diameter_top": bar_diameter_mm,
            "main_spacing_top": spacing_mm,
            "main_diameter_bottom": bar_diameter_mm,
            "main_spacing_bottom": spacing_mm,
            "concrete_cover": cover_mm / 1000,
        },
    )


def create_reinforcement_layout(cross_section: BridgeCrossSectionData) -> ReinforcementConfig:
    """
    Create reinforcement layout from cross-section data.

    :param cross_section: Bridge cross-section data
    :type cross_section: BridgeCrossSectionData
    :returns: Reinforcement configuration
    :rtype: ReinforcementConfig
    """
    config = cross_section.reinforcement_config
    cover = config["concrete_cover"]

    # Calculate bar positions for top reinforcement
    main_bars_top = []
    spacing_top = config["main_spacing_top"]
    diameter_top = config["main_diameter_top"]

    # Position bars across the width with specified spacing
    y_top = cross_section.height / 2 - cover - diameter_top / 2
    num_bars_top = max(2, int(cross_section.width / spacing_top) + 1)

    for i in range(num_bars_top):
        x_pos = -cross_section.width / 2 + cover + i * spacing_top
        if x_pos <= cross_section.width / 2 - cover:
            main_bars_top.append((x_pos, y_top, diameter_top))

    # Calculate bar positions for bottom reinforcement
    main_bars_bottom = []
    spacing_bottom = config["main_spacing_bottom"]
    diameter_bottom = config["main_diameter_bottom"]

    y_bottom = -cross_section.height / 2 + cover + diameter_bottom / 2
    num_bars_bottom = max(2, int(cross_section.width / spacing_bottom) + 1)

    for i in range(num_bars_bottom):
        x_pos = -cross_section.width / 2 + cover + i * spacing_bottom
        if x_pos <= cross_section.width / 2 - cover:
            main_bars_bottom.append((x_pos, y_bottom, diameter_bottom))

    return ReinforcementConfig(main_bars_top=main_bars_top, main_bars_bottom=main_bars_bottom, concrete_cover=cover)


def create_simple_idea_slab_model(cross_section_data: BridgeCrossSectionData) -> Any:  # noqa: ANN401
    """
    Create a simple rectangular slab IDEA model from cross-section data.

    Creates a basic IDEA StatiCa model with:
    - Rectangular slab cross-section
    - Concrete and reinforcement materials
    - Basic reinforcement layout
    - Sample loading extremes

    TODO: Future enhancements for complete cross-section modeling:

    1. SUPPORT FOR DIFFERENT SLAB SECTION TYPES:
       - Variable thickness slab sections per zone
       - Rectangular sections with zone-specific thickness (dz, dz_2)
       - Extract geometry from params.input.dimensions.bridge_segments_array

    2. ADVANCED REINFORCEMENT PATTERNS:
       - Support for stirrups/shear reinforcement
       - Variable reinforcement along length
       - Prestressing tendons
       - Extract from params.input.geometrie_wapening for realistic reinforcement layouts
       - Use zone-specific reinforcement configurations from reinforcement_zones_array
       - Support hoofdwapening (main) and bijlegwapening (additional) reinforcement

        3. SLAB-FOCUSED ANALYSIS:
       - One-way slab analysis (current implementation using create_one_way_slab)
       - Focus on bridge deck analysis only (no girders/beams modeled)
       - Extract slab properties from params.info.bridge_type and params.info.static_system

    4. ENHANCED LOAD CASES:
       - Dead load from bridge geometry
       - Live load from traffic models (params.input.belastingzones.load_zones_array)
       - Load combinations per Eurocode (params.input.belastingcombinaties)
       - Extract material properties from params.info section

    5. INTEGRATION WITH BRIDGE PARAMETRIZATION:
       - Use params.info.construction_height for realistic deck thickness
       - Use params.info.concrete_strength_class and steel_quality_reinforcement for materials
       - Extract reinforcement from params.input.geometrie_wapening zones
       - Map load zones from params.input.belastingzones for proper loading

    :param cross_section_data: Bridge cross-section data
    :type cross_section_data: BridgeCrossSectionData
    :returns: IDEA StatiCa model object
    :rtype: Any
    :raises ImportError: When VIKTOR IDEA module is not available
    """
    try:
        from viktor.external import idea_rcs
    except ImportError as e:
        raise ImportError("VIKTOR IDEA StatiCa module required for IDEA integration") from e

    # Create the IDEA model
    model = idea_rcs.Model()

    # Create concrete material
    # Convert material name to IDEA enum
    concrete_material_enum = _get_concrete_material_enum(cross_section_data.concrete_material)
    cs_mat = model.create_concrete_material(concrete_material_enum)

    # Create reinforcement material
    reinforcement_material_enum = _get_reinforcement_material_enum(cross_section_data.reinforcement_material)
    mat_reinf = model.create_reinforcement_material(reinforcement_material_enum)

    # Create rectangular cross-section
    cross_section = idea_rcs.RectSection(cross_section_data.width, cross_section_data.height)

    # Create one-way slab member (correct for bridge deck analysis)
    slab = model.create_one_way_slab(cross_section, cs_mat)

    # Add reinforcement bars
    reinforcement = create_reinforcement_layout(cross_section_data)

    # Add top reinforcement
    for x, y, diameter in reinforcement.main_bars_top:
        slab.create_bar((x, y), diameter, mat_reinf)

    # Add bottom reinforcement
    for x, y, diameter in reinforcement.main_bars_bottom:
        slab.create_bar((x, y), diameter, mat_reinf)

    # Add sample load extremes
    # Calculate realistic loads from bridge geometry and traffic patterns
    frequent = idea_rcs.LoadingSLS(idea_rcs.ResultOfInternalForces(N=-100000, My=210000))
    fundamental = idea_rcs.LoadingULS(idea_rcs.ResultOfInternalForces(N=-99999, My=200000))
    slab.create_extreme(frequent=frequent, fundamental=fundamental)

    return model


def _get_concrete_material_enum(material_name: str) -> Any:  # noqa: ANN401
    """
    Convert concrete material name to IDEA enum using centralized material system.

    Validates against the project's material database (betonkwaliteit.csv) and maps
    to IDEA StatiCa enums only for materials that exist in both systems.

    :param material_name: Concrete material name (e.g., "C30/37")
    :type material_name: str
    :returns: IDEA concrete material enum
    :rtype: Any
    :raises ImportError: When VIKTOR IDEA module is not available
    :raises ValueError: When material not found in project database
    """
    try:
        from viktor.external import idea_rcs
    except ImportError as e:
        raise ImportError("VIKTOR IDEA StatiCa module required") from e

    # Validate that material exists in our project database
    from src.common.materials import get_supported_idea_materials, normalize_material_name, validate_material_exists

    if not validate_material_exists(material_name, "concrete"):
        available_materials = get_supported_idea_materials()["concrete"]
        raise ValueError(f"Concrete material '{material_name}' not found in project database. IDEA-supported materials: {available_materials}")

    # Normalize material name to handle decimal separator differences
    normalized_material = normalize_material_name(material_name)

    # Build mapping for materials supported by both our database and IDEA StatiCa
    supported_materials = get_supported_idea_materials()["concrete"]
    idea_mapping = {}

    # Create enum mapping for supported materials
    enum_name_mapping = {
        "C12/15": "C12_15",
        "C16/20": "C16_20",
        "C20/25": "C20_25",
        "C25/30": "C25_30",
        "C30/37": "C30_37",
        "C35/45": "C35_45",
        "C40/50": "C40_50",
        "C45/55": "C45_55",
        "C50/60": "C50_60",
    }

    # Build mapping only for materials available in both systems
    for csv_name in supported_materials:
        if csv_name in enum_name_mapping and hasattr(idea_rcs.ConcreteMaterial, enum_name_mapping[csv_name]):
            idea_mapping[csv_name] = getattr(idea_rcs.ConcreteMaterial, enum_name_mapping[csv_name])

    # Return mapped material or fallback to default if not supported by IDEA
    # Try normalized material name first, then original
    if normalized_material in idea_mapping:
        return idea_mapping[normalized_material]
    if material_name in idea_mapping:
        return idea_mapping[material_name]
    # Material exists in our database but not supported by IDEA - use closest equivalent
    default_material = "C30/37"
    if default_material in idea_mapping:
        return idea_mapping[default_material]
    # Last resort fallback
    return idea_rcs.ConcreteMaterial.C30_37


def _get_reinforcement_material_enum(material_name: str) -> Any:  # noqa: ANN401
    """
    Convert reinforcement material name to IDEA enum using centralized material system.

    :param material_name: Material name (e.g., "B500B", "QR40")
    :type material_name: str
    :returns: IDEA reinforcement material enum
    :rtype: Any
    :raises ImportError: If VIKTOR IDEA module not available
    """
    try:
        from viktor.external import idea_rcs
    except ImportError as e:
        raise ImportError("VIKTOR IDEA StatiCa module required") from e

    # Mapping of material names to IDEA enums
    material_mapping = {
        "B500A": idea_rcs.ReinforcementMaterial.B_500A,
        "B500B": idea_rcs.ReinforcementMaterial.B_500B,
        "B500C": idea_rcs.ReinforcementMaterial.B_500C,
        "QR22": idea_rcs.ReinforcementMaterial.B_500A,  # Legacy mapping
        "QR24": idea_rcs.ReinforcementMaterial.B_500A,
        "QR30": idea_rcs.ReinforcementMaterial.B_500B,
        "QR40": idea_rcs.ReinforcementMaterial.B_500B,
        "FeB 400": idea_rcs.ReinforcementMaterial.B_500B,
        "QR48": idea_rcs.ReinforcementMaterial.B_500C,
        "FeB 500": idea_rcs.ReinforcementMaterial.B_500C,
    }

    return material_mapping.get(material_name, idea_rcs.ReinforcementMaterial.B_500B)


def create_bridge_idea_model(bridge_segments_params: list[dict[str, Any]]) -> Any:  # noqa: ANN401
    """
    Create IDEA StatiCa RCS model from bridge parameters.

    :param bridge_segments_params: List of bridge segment parameters
    :type bridge_segments_params: list[dict[str, Any]]
    :returns: IDEA RCS model object
    :rtype: Any
    :raises ValueError: If parameters are invalid
    :raises ImportError: If VIKTOR IDEA module is not available
    """
    # Extract cross-section geometry
    cross_section_data = extract_cross_section_from_params(bridge_segments_params)

    return create_simple_idea_slab_model(cross_section_data)


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
        analysis = idea_rcs.IdeaRcsAnalysis(xml_input)
        analysis.execute(timeout)

        return analysis.get_output_file()

    except Exception as e:
        raise RuntimeError(f"IDEA analysis failed: {e}") from e
