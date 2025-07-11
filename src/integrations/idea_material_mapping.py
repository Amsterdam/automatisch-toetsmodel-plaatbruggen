
"""
Mapping module for IDEA RCS concrete materials.

This module provides mapping functions to convert concrete quality strings
from the betonkwaliteit.csv file to IDEA RCS ConcreteMaterial enum values.
"""

from viktor.external import idea_rcs


def get_idea_concrete_material(concrete_quality: str) -> idea_rcs.ConcreteMaterial:
    """
    Map concrete quality string to IDEA RCS ConcreteMaterial enum value.

    :param concrete_quality: Concrete quality string (e.g., "C30/37")
    :type concrete_quality: str
    :returns: IDEA RCS ConcreteMaterial enum value
    :rtype: idea_rcs.ConcreteMaterial
    :raises ValueError: If concrete quality is not supported
    """
    concrete_material_mapping = {
        "C12/15": idea_rcs.ConcreteMaterial.C12_15,
        "C16/20": idea_rcs.ConcreteMaterial.C16_20,
        "C20/25": idea_rcs.ConcreteMaterial.C20_25,
        "C25/30": idea_rcs.ConcreteMaterial.C25_30,
        "C30/37": idea_rcs.ConcreteMaterial.C30_37,
        "C35/45": idea_rcs.ConcreteMaterial.C35_45,
        "C40/50": idea_rcs.ConcreteMaterial.C40_50,
        "C45/55": idea_rcs.ConcreteMaterial.C45_55,
        "C50/60": idea_rcs.ConcreteMaterial.C50_60,
        "C55/67": idea_rcs.ConcreteMaterial.C55_67,
        "C60/75": idea_rcs.ConcreteMaterial.C60_75,
        "C70/85": idea_rcs.ConcreteMaterial.C70_85,
        "C80/95": idea_rcs.ConcreteMaterial.C80_95,
        "C90/105": idea_rcs.ConcreteMaterial.C90_105,
    }
    
    if concrete_quality not in concrete_material_mapping:
        raise ValueError(f"Concrete quality '{concrete_quality}' is not supported. Available options: {list(concrete_material_mapping.keys())}")
    
    return concrete_material_mapping[concrete_quality]

def get_idea_reinforcement_material(reinforcement_type: str = "B500B") -> idea_rcs.ReinforcementMaterial:
    """
    Map reinforcement type string to IDEA RCS ReinforcementMaterial enum value.

    :param reinforcement_type: Reinforcement type string (e.g., "B500B")
    :type reinforcement_type: str
    :returns: IDEA RCS ReinforcementMaterial enum value
    :rtype: idea_rcs.ReinforcementMaterial
    :raises ValueError: If reinforcement type is not supported
    """
    reinforcement_material_mapping = {
        "B400A": idea_rcs.ReinforcementMaterial.B_400A,
        "B400B": idea_rcs.ReinforcementMaterial.B_400B,
        "B400C": idea_rcs.ReinforcementMaterial.B_400C,
        "B500A": idea_rcs.ReinforcementMaterial.B_500A,
        "B500B": idea_rcs.ReinforcementMaterial.B_500B,
        "B500C": idea_rcs.ReinforcementMaterial.B_500C,
        "B550A": idea_rcs.ReinforcementMaterial.B_550A,
        "B550B": idea_rcs.ReinforcementMaterial.B_550B,
        "B600A": idea_rcs.ReinforcementMaterial.B_600A,
        "B600B": idea_rcs.ReinforcementMaterial.B_600B,
        "B600C": idea_rcs.ReinforcementMaterial.B_600C,
    }
    
    if reinforcement_type not in reinforcement_material_mapping:
        raise ValueError(f"Reinforcement type '{reinforcement_type}' is not supported. Available options: {list(reinforcement_material_mapping.keys())}")
    
    return reinforcement_material_mapping[reinforcement_type]