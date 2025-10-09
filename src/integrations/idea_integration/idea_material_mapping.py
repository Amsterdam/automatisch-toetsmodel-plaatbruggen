"""
Mapping module for IDEA RCS concrete and reinforcement materials.

This module provides mapping functions to convert material quality strings
to enum values and create custom materials from CSV data.

This module is now SDK-independent, using the enum bridge pattern.
"""

from src.integrations.idea_integration.idea_enums import ConcreteMaterial, ReinforcementMaterial


def get_idea_concrete_material(concrete_quality: str) -> ConcreteMaterial:
    """
    Map concrete quality string to IDEA RCS ConcreteMaterial enum value.

    This function only handles modern Eurocode materials (C-class).
    For historical materials (K-class, B-class), use create_historical_concrete_material() instead.

    :param concrete_quality: Concrete quality string (e.g., "C30/37")
    :type concrete_quality: str
    :returns: ConcreteMaterial enum value
    :rtype: ConcreteMaterial
    :raises ValueError: If concrete quality is not supported or is a historical material
    """
    concrete_material_mapping = {
        # Modern Eurocode materials (C-class)
        "C12/15": ConcreteMaterial.C12_15,
        "C16/20": ConcreteMaterial.C16_20,
        "C20/25": ConcreteMaterial.C20_25,
        "C25/30": ConcreteMaterial.C25_30,
        "C30/37": ConcreteMaterial.C30_37,
        "C35/45": ConcreteMaterial.C35_45,
        "C40/50": ConcreteMaterial.C40_50,
        "C45/55": ConcreteMaterial.C45_55,
        "C50/60": ConcreteMaterial.C50_60,
        "C55/67": ConcreteMaterial.C55_67,
        "C60/75": ConcreteMaterial.C60_75,
        "C70/85": ConcreteMaterial.C70_85,
        "C80/95": ConcreteMaterial.C80_95,
        "C90/105": ConcreteMaterial.C90_105,
    }

    if concrete_quality not in concrete_material_mapping:
        # Check if it's a historical material
        if is_historical_material(concrete_quality):
            raise ValueError(
                f"Historical material '{concrete_quality}' detected. "
                f"Use create_historical_concrete_material() instead of get_idea_concrete_material()."
            )
        raise ValueError(
            f"Concrete quality '{concrete_quality}' is not supported. Available modern materials: {list(concrete_material_mapping.keys())}"
        )

    return concrete_material_mapping[concrete_quality]


# ===================================================================================
# Material Creation Functions - Use IdeaModelBuilder Instead
# ===================================================================================
#
# Material creation with SDK has been moved to app/bridge/idea_model_builder.py
#
# For creating materials, use the IdeaModelBuilder Protocol methods:
# - builder.create_concrete_material_modern(model, material_enum)
# - builder.create_concrete_material_historical(model, quality, cement_class, aggregate_type, diagram_type)
# - builder.create_reinforcement_material_modern(model, material_enum)
# - builder.create_reinforcement_material_historical(model, quality, ...)
#
# This module now only provides enum mappings and material type checking.
# ===================================================================================


def is_historical_material(concrete_quality: str) -> bool:
    """
    Check if a concrete quality is a historical material that requires CSV data.

    :param concrete_quality: Concrete quality string
    :type concrete_quality: str
    :returns: True if historical material, False otherwise
    :rtype: bool
    """
    historical_materials = {
        # Historical materials from GBV 1940/1950/1962
        "K150",
        "K200",
        "K250",
        "K160",
        "K225",
        "K300",
        "K400",
        "K450",
        # NEN 6720 materials (B-class)
        "B25",
        "B35",
        "B45",
        "B55",
        "B65",
        # VB 74+84 materials (B-class with decimals)
        "B12,5",
        "B17,5",
        "B22,5",
        "B30",
        "B37,5",
        "B52,5",
        "B60",
    }
    return concrete_quality in historical_materials


def get_all_supported_materials() -> dict[str, str]:
    """
    Get all supported concrete materials with their types.

    :returns: Dictionary mapping material names to types ('modern' or 'historical')
    :rtype: dict[str, str]
    """
    materials = {}

    # Modern materials
    modern_materials = [
        "C12/15",
        "C16/20",
        "C20/25",
        "C25/30",
        "C30/37",
        "C35/45",
        "C40/50",
        "C45/55",
        "C50/60",
        "C55/67",
        "C60/75",
        "C70/85",
        "C80/95",
        "C90/105",
    ]
    for material in modern_materials:
        materials[material] = "modern"

    # Historical materials
    historical_materials = [
        "K150",
        "K200",
        "K250",
        "K160",
        "K225",
        "K300",
        "K400",
        "K450",
        "B25",
        "B35",
        "B45",
        "B55",
        "B65",
        "B12,5",
        "B17,5",
        "B22,5",
        "B30",
        "B37,5",
        "B52,5",
        "B60",
    ]
    for material in historical_materials:
        materials[material] = "historical"

    return materials


def get_idea_reinforcement_material(reinforcement_type: str = "B500B") -> ReinforcementMaterial:
    """
    Map modern reinforcement type string to ReinforcementMaterial enum value.

    This function only handles modern Eurocode materials (B-class with letter suffix).
    For historical materials (FeB, HK, St.), use builder.create_reinforcement_material_historical() instead.

    :param reinforcement_type: Reinforcement type string (e.g., "B500B")
    :type reinforcement_type: str
    :returns: ReinforcementMaterial enum value
    :rtype: ReinforcementMaterial
    :raises ValueError: If reinforcement type is not supported or is a historical material
    """
    reinforcement_material_mapping = {
        "B400A": ReinforcementMaterial.B_400A,
        "B400B": ReinforcementMaterial.B_400B,
        "B400C": ReinforcementMaterial.B_400C,
        "B500A": ReinforcementMaterial.B_500A,
        "B500B": ReinforcementMaterial.B_500B,
        "B500C": ReinforcementMaterial.B_500C,
        "B550A": ReinforcementMaterial.B_550A,
        "B550B": ReinforcementMaterial.B_550B,
        "B600A": ReinforcementMaterial.B_600A,
        "B600B": ReinforcementMaterial.B_600B,
        "B600C": ReinforcementMaterial.B_600C,
    }

    if reinforcement_type not in reinforcement_material_mapping:
        # Check if it's a historical material
        if is_historical_reinforcement_material(reinforcement_type):
            raise ValueError(
                f"Historical material '{reinforcement_type}' detected. "
                f"Use create_historical_reinforcement_material() instead of get_idea_reinforcement_material()."
            )
        raise ValueError(
            f"Reinforcement type '{reinforcement_type}' is not supported. Available modern materials: {list(reinforcement_material_mapping.keys())}"
        )

    return reinforcement_material_mapping[reinforcement_type]


# Note: Material creation functions have been removed - use IdeaModelBuilder instead
# See comment block above for details on the new pattern


def is_historical_reinforcement_material(reinforcement_type: str) -> bool:
    """
    Check if a reinforcement type is a historical material that requires CSV data.

    :param reinforcement_type: Reinforcement type string
    :type reinforcement_type: str
    :returns: True if historical material, False otherwise
    :rtype: bool
    """
    historical_materials = {
        # GBV 1940 materials
        "HK",
        "St. 37",
        # GBV 1950 materials
        "QR22",
        "QR24",
        "QR30",
        "QR36",
        "QR42",
        # GBV 1962 materials
        "QR32",
        "QR40",
        "QR48",
        # NEN 6720 materials
        "FeB500 HWL, HK",
        "FeB400 HWL, HK",
        "FeB220 HWL",
        # VB 74+84 materials
        "FeB500 HW",
        "FeB400 HW",
        "FeB220 HW",
    }
    return reinforcement_type in historical_materials


def get_all_supported_reinforcement_materials() -> dict[str, str]:
    """
    Get all supported reinforcement materials with their types.

    :returns: Dictionary mapping material names to types ('modern' or 'historical')
    :rtype: dict[str, str]
    """
    materials = {}

    # Modern materials
    modern_materials = ["B400A", "B400B", "B400C", "B500A", "B500B", "B500C", "B550A", "B550B", "B600A", "B600B", "B600C"]
    for material in modern_materials:
        materials[material] = "modern"

    # Historical materials
    historical_materials = [
        "HK",
        "St. 37",
        "QR22",
        "QR24",
        "QR30",
        "QR36",
        "QR42",
        "QR32",
        "QR40",
        "QR48",
        "FeB500 HWL, HK",
        "FeB400 HWL, HK",
        "FeB220 HWL",
        "FeB500 HW",
        "FeB400 HW",
        "FeB220 HW",
    ]
    for material in historical_materials:
        materials[material] = "historical"

    return materials
