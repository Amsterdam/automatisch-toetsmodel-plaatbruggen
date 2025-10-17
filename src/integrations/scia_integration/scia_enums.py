"""
Enum bridge classes for SCIA SDK types.

These enums provide a bridge between the src/ layer and the VIKTOR SDK.
When the SDK is available, enum values are actual SDK enum objects.
When testing without the SDK, enum values fall back to strings.

This approach provides:
- Type safety and IDE autocomplete throughout the codebase
- Zero runtime conversion overhead (values ARE SDK objects)
- Independence from SDK in tests
- Automatic propagation of SDK updates
"""

from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from viktor.external import scia

# Try to import the VIKTOR SDK
try:
    from viktor.external import scia

    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False

# ================================================================================================
# Load Case Enums
# ================================================================================================

if SDK_AVAILABLE:

    class LoadCaseActionType(Enum):
        """Action type for load cases."""

        PERMANENT = scia.LoadCase.ActionType.PERMANENT
        VARIABLE = scia.LoadCase.ActionType.VARIABLE

    class PermanentLoadType(Enum):
        """Types of permanent loads."""

        STANDARD = scia.LoadCase.PermanentLoadType.STANDARD
        SELF_WEIGHT = scia.LoadCase.PermanentLoadType.SELF_WEIGHT
        # Note: PRESTRESS not available in current SDK version

    class VariableLoadType(Enum):
        """Types of variable loads."""

        STATIC = scia.LoadCase.VariableLoadType.STATIC
        # Note: DYNAMIC not available in current SDK version

    class LoadCaseSpecification(Enum):
        """Load specifications."""

        STANDARD = scia.LoadCase.Specification.STANDARD
        TEMPERATURE = scia.LoadCase.Specification.TEMPERATURE
        # Note: WIND, SNOW, CRANE not available in current SDK version

    class LoadCaseDuration(Enum):
        """Load durations."""

        SHORT = scia.LoadCase.Duration.SHORT
        MEDIUM = scia.LoadCase.Duration.MEDIUM
        LONG = scia.LoadCase.Duration.LONG

else:
    # Fallback enums with string values for testing without SDK

    class LoadCaseActionType(Enum):  # type: ignore[no-redef]
        """Action type for load cases."""

        PERMANENT = "PERMANENT"
        VARIABLE = "VARIABLE"

    class PermanentLoadType(Enum):  # type: ignore[no-redef]
        """Types of permanent loads."""

        STANDARD = "STANDARD"
        SELF_WEIGHT = "SELF_WEIGHT"

    class VariableLoadType(Enum):  # type: ignore[no-redef]
        """Types of variable loads."""

        STATIC = "STATIC"

    class LoadCaseSpecification(Enum):  # type: ignore[no-redef]
        """Load specifications."""

        STANDARD = "STANDARD"
        TEMPERATURE = "TEMPERATURE"

    class LoadCaseDuration(Enum):  # type: ignore[no-redef]
        """Load durations."""

        SHORT = "SHORT"
        MEDIUM = "MEDIUM"
        LONG = "LONG"


# ================================================================================================
# Load Group Enums
# ================================================================================================

if SDK_AVAILABLE:

    class LoadGroupOption(Enum):
        """Load group options."""

        PERMANENT = scia.LoadGroup.LoadOption.PERMANENT
        VARIABLE = scia.LoadGroup.LoadOption.VARIABLE
        ACCIDENTAL = scia.LoadGroup.LoadOption.ACCIDENTAL
        SEISMIC = scia.LoadGroup.LoadOption.SEISMIC

    class LoadGroupRelation(Enum):
        """Load group relations."""

        STANDARD = scia.LoadGroup.RelationOption.STANDARD
        EXCLUSIVE = scia.LoadGroup.RelationOption.EXCLUSIVE
        TOGETHER = scia.LoadGroup.RelationOption.TOGETHER

    class LoadGroupLoadType(Enum):
        """Load group load types."""

        CAT_A = scia.LoadGroup.LoadTypeOption.CAT_A
        CAT_B = scia.LoadGroup.LoadTypeOption.CAT_B
        CAT_C = scia.LoadGroup.LoadTypeOption.CAT_C
        CAT_D = scia.LoadGroup.LoadTypeOption.CAT_D
        CAT_E = scia.LoadGroup.LoadTypeOption.CAT_E
        CAT_F = scia.LoadGroup.LoadTypeOption.CAT_F
        CAT_G = scia.LoadGroup.LoadTypeOption.CAT_G
        CAT_H = scia.LoadGroup.LoadTypeOption.CAT_H
        WIND = scia.LoadGroup.LoadTypeOption.WIND
        SNOW = scia.LoadGroup.LoadTypeOption.SNOW
        TEMPERATURE = scia.LoadGroup.LoadTypeOption.TEMPERATURE
        CONSTRUCTION_LOADS = scia.LoadGroup.LoadTypeOption.CONSTRUCTION_LOADS

else:
    # Fallback enums with string values for testing without SDK

    class LoadGroupOption(Enum):  # type: ignore[no-redef]
        """Load group options."""

        PERMANENT = "PERMANENT"
        VARIABLE = "VARIABLE"
        ACCIDENTAL = "ACCIDENTAL"
        SEISMIC = "SEISMIC"

    class LoadGroupRelation(Enum):  # type: ignore[no-redef]
        """Load group relations."""

        STANDARD = "STANDARD"
        EXCLUSIVE = "EXCLUSIVE"
        TOGETHER = "TOGETHER"

    class LoadGroupLoadType(Enum):  # type: ignore[no-redef]
        """Load group load types."""

        CAT_A = "CAT_A"
        CAT_B = "CAT_B"
        CAT_C = "CAT_C"
        CAT_D = "CAT_D"
        CAT_E = "CAT_E"
        CAT_F = "CAT_F"
        CAT_G = "CAT_G"
        CAT_H = "CAT_H"
        WIND = "WIND"
        SNOW = "SNOW"
        TEMPERATURE = "TEMPERATURE"
        CONSTRUCTION_LOADS = "CONSTRUCTION_LOADS"


# ================================================================================================
# Load Combination Enums
# ================================================================================================

if SDK_AVAILABLE:

    class LoadCombinationType(Enum):
        """Load combination types."""

        ENVELOPE_ULTIMATE = scia.LoadCombination.Type.ENVELOPE_ULTIMATE
        ENVELOPE_SERVICEABILITY = scia.LoadCombination.Type.ENVELOPE_SERVICEABILITY
        # Note: Other combination types not available in current SDK version

else:
    # Fallback enums with string values for testing without SDK

    class LoadCombinationType(Enum):  # type: ignore[no-redef]
        """Load combination types."""

        ENVELOPE_ULTIMATE = "ENVELOPE_ULTIMATE"
        ENVELOPE_SERVICEABILITY = "ENVELOPE_SERVICEABILITY"


# ================================================================================================
# Line Load and Support Enums
# ================================================================================================

if SDK_AVAILABLE:

    class LineLoadDirection(Enum):
        """Line load directions."""

        X = scia.FreeLineLoad.Direction.X
        Y = scia.FreeLineLoad.Direction.Y
        Z = scia.FreeLineLoad.Direction.Z

    class LineSupportFreedom(Enum):
        """Line support freedom options."""

        FREE = scia.LineSupport.Freedom.FREE
        RIGID = scia.LineSupport.Freedom.RIGID
        FLEXIBLE = scia.LineSupport.Freedom.FLEXIBLE
        # Note: Compression-only options not available in current SDK version

else:
    # Fallback enums with string values for testing without SDK

    class LineLoadDirection(Enum):  # type: ignore[no-redef]
        """Line load directions."""

        X = "X"
        Y = "Y"
        Z = "Z"

    class LineSupportFreedom(Enum):  # type: ignore[no-redef]
        """Line support freedom options."""

        FREE = "FREE"
        RIGID = "RIGID"
        FLEXIBLE = "FLEXIBLE"
