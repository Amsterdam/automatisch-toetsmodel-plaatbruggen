"""
IDEA RCS SDK Enum Bridge.

This module provides Python Enum classes whose values are actual IDEA RCS SDK enum objects
when the SDK is available, with string fallback for testing environments.

This approach provides:
- Type safety with IDE autocomplete
- Zero runtime conversion overhead (enum values ARE SDK objects)
- SDK independence for testing (falls back to strings)
- Single source of truth for all IDEA enum types
"""

from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from viktor.external import idea_rcs

try:
    from viktor.external import idea_rcs

    SDK_AVAILABLE = True
except ImportError:
    idea_rcs = None  # type: ignore[assignment]
    SDK_AVAILABLE = False


# ============================================================================================================
# Reinforcement Enums
# ============================================================================================================

if SDK_AVAILABLE:

    class ReinforcementClass(Enum):
        """Reinforcement class options."""

        A = idea_rcs.ReinfClass.A
        B = idea_rcs.ReinfClass.B
        C = idea_rcs.ReinfClass.C

    class BarSurface(Enum):
        """Bar surface options."""

        SMOOTH = idea_rcs.BarSurface.SMOOTH
        RIBBED = idea_rcs.BarSurface.RIBBED

    class ReinfDiagramType(Enum):
        """Reinforcement diagram type options."""

        BILINEAR_NOT_INCLINED = idea_rcs.ReinfDiagramType.BILINEAR_NOT_INCLINED
        BILINEAR_INCLINED = idea_rcs.ReinfDiagramType.BILINEAR_INCLINED

    class ReinfType(Enum):
        """Reinforcement type options."""

        BARS = idea_rcs.ReinfType.BARS

    class ReinfFabrication(Enum):
        """Reinforcement fabrication options."""

        HOT_ROLLED = idea_rcs.ReinfFabrication.HOT_ROLLED

    class ReinforcementMaterial(Enum):
        """Reinforcement material options."""

        B_400A = idea_rcs.ReinforcementMaterial.B_400A
        B_400B = idea_rcs.ReinforcementMaterial.B_400B
        B_400C = idea_rcs.ReinforcementMaterial.B_400C
        B_500A = idea_rcs.ReinforcementMaterial.B_500A
        B_500B = idea_rcs.ReinforcementMaterial.B_500B
        B_500C = idea_rcs.ReinforcementMaterial.B_500C
        B_550A = idea_rcs.ReinforcementMaterial.B_550A
        B_550B = idea_rcs.ReinforcementMaterial.B_550B
        B_600A = idea_rcs.ReinforcementMaterial.B_600A
        B_600B = idea_rcs.ReinforcementMaterial.B_600B
        B_600C = idea_rcs.ReinforcementMaterial.B_600C

else:
    # Fallback to string values for testing without SDK

    class ReinforcementClass(Enum):  # type: ignore[no-redef]
        """Reinforcement class options."""

        A = "A"
        B = "B"
        C = "C"

    class BarSurface(Enum):  # type: ignore[no-redef]
        """Bar surface options."""

        SMOOTH = "SMOOTH"
        RIBBED = "RIBBED"

    class ReinfDiagramType(Enum):  # type: ignore[no-redef]
        """Reinforcement diagram type options."""

        BILINEAR_NOT_INCLINED = "BILINEAR_NOT_INCLINED"
        BILINEAR_INCLINED = "BILINEAR_INCLINED"

    class ReinfType(Enum):  # type: ignore[no-redef]
        """Reinforcement type options."""

        BARS = "BARS"

    class ReinfFabrication(Enum):  # type: ignore[no-redef]
        """Reinforcement fabrication options."""

        HOT_ROLLED = "HOT_ROLLED"

    class ReinforcementMaterial(Enum):  # type: ignore[no-redef]
        """Reinforcement material options."""

        B_400A = "B_400A"
        B_400B = "B_400B"
        B_400C = "B_400C"
        B_500A = "B_500A"
        B_500B = "B_500B"
        B_500C = "B_500C"
        B_550A = "B_550A"
        B_550B = "B_550B"
        B_600A = "B_600A"
        B_600B = "B_600B"
        B_600C = "B_600C"


# ============================================================================================================
# Concrete Enums
# ============================================================================================================

if SDK_AVAILABLE:

    class ConcCementClass(Enum):
        """Concrete cement class options."""

        S = idea_rcs.ConcCementClass.S
        R = idea_rcs.ConcCementClass.R
        N = idea_rcs.ConcCementClass.N

    class ConcAggregateType(Enum):
        """Concrete aggregate type options."""

        QUARTZITE = idea_rcs.ConcAggregateType.QUARTZITE
        LIMESTONE = idea_rcs.ConcAggregateType.LIMESTONE
        SANDSTONE = idea_rcs.ConcAggregateType.SANDSTONE
        BASALT = idea_rcs.ConcAggregateType.BASALT

    class ConcDiagramType(Enum):
        """Concrete diagram type options."""

        PARABOLIC = idea_rcs.ConcDiagramType.PARABOLIC

    class ConcreteMaterial(Enum):
        """Concrete material options."""

        C12_15 = idea_rcs.ConcreteMaterial.C12_15
        C16_20 = idea_rcs.ConcreteMaterial.C16_20
        C20_25 = idea_rcs.ConcreteMaterial.C20_25
        C25_30 = idea_rcs.ConcreteMaterial.C25_30
        C30_37 = idea_rcs.ConcreteMaterial.C30_37
        C35_45 = idea_rcs.ConcreteMaterial.C35_45
        C40_50 = idea_rcs.ConcreteMaterial.C40_50
        C45_55 = idea_rcs.ConcreteMaterial.C45_55
        C50_60 = idea_rcs.ConcreteMaterial.C50_60
        C55_67 = idea_rcs.ConcreteMaterial.C55_67
        C60_75 = idea_rcs.ConcreteMaterial.C60_75
        C70_85 = idea_rcs.ConcreteMaterial.C70_85
        C80_95 = idea_rcs.ConcreteMaterial.C80_95
        C90_105 = idea_rcs.ConcreteMaterial.C90_105

else:
    # Fallback to string values for testing without SDK

    class ConcCementClass(Enum):  # type: ignore[no-redef]
        """Concrete cement class options."""

        S = "S"
        R = "R"
        N = "N"

    class ConcAggregateType(Enum):  # type: ignore[no-redef]
        """Concrete aggregate type options."""

        QUARTZITE = "QUARTZITE"
        LIMESTONE = "LIMESTONE"
        SANDSTONE = "SANDSTONE"
        BASALT = "BASALT"

    class ConcDiagramType(Enum):  # type: ignore[no-redef]
        """Concrete diagram type options."""

        PARABOLIC = "PARABOLIC"

    class ConcreteMaterial(Enum):  # type: ignore[no-redef]
        """Concrete material options."""

        C12_15 = "C12_15"
        C16_20 = "C16_20"
        C20_25 = "C20_25"
        C25_30 = "C25_30"
        C30_37 = "C30_37"
        C35_45 = "C35_45"
        C40_50 = "C40_50"
        C45_55 = "C45_55"
        C50_60 = "C50_60"
        C55_67 = "C55_67"
        C60_75 = "C60_75"
        C70_85 = "C70_85"
        C80_95 = "C80_95"
        C90_105 = "C90_105"
