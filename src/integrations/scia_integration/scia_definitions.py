"""
SCIA definitions module.

This module defines pure Python data structures that act as definitions or blueprints for creating SCIA Engineer objects.
These definitions are used within the src layer to describe SCIA components without having a direct dependency on the VIKTOR SDK.

The app layer's scia_model_builder will then interpret these definitions to construct the actual scia objects.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Literal


class SciaCombinationType(Enum):
    """Enumeration for SCIA Load Combination types, independent of the SDK."""

    ULS = "ULS"
    ULS_SET_B = "ULS_SET_B"
    ULS_SET_C = "ULS_SET_C"
    ENVELOPE_ULS = "ENVELOPE_ULS"
    LINEAR_ULS = "LINEAR_ULS"
    SLS = "SLS"
    SLS_CHAR = "SLS_CHAR"
    SLS_FREQ = "SLS_FREQ"
    SLS_QUASI = "SLS_QUASI"
    ENVELOPE_SLS = "ENVELOPE_SLS"
    LINEAR_SLS = "LINEAR_SLS"
    ACCIDENTAL = "ACCIDENTAL"
    ACCIDENTAL_1 = "ACCIDENTAL_1"
    ACCIDENTAL_2 = "ACCIDENTAL_2"
    SEISMIC = "SEISMIC"


@dataclass
class LoadGroupDefinition:
    """
    Defines the properties for a SCIA Load Group.

    :param name: Name of the load group (e.g., "LG1", "Permanent").
    :param load_option: Type of load, maps to LoadGroup.LoadOption enum.
    :param relation: Relation between load cases, maps to LoadGroup.RelationOption.
    :param load_type: Category of load, maps to LoadGroup.LoadTypeOption.
    """

    name: str
    load_option: Literal["PERMANENT", "VARIABLE", "ACCIDENTAL", "SEISMIC"]
    relation: Literal["STANDARD", "EXCLUSIVE", "TOGETHER"]
    load_type: (
        Literal[
            "CAT_A",
            "CAT_B",
            "CAT_C",
            "CAT_D",
            "CAT_E",
            "CAT_F",
            "CAT_G",
            "CAT_H",
            "WIND",
            "SNOW",
            "TEMPERATURE",
            "RAIN_WATER",
            "CONSTRUCTION_LOADS",
        ]
        | None
    )


@dataclass
class LoadCaseDefinition:
    """
    Defines the properties for a SCIA Load Case.

    :param name: Name of the load case (e.g., "BG01", "Q2_Wind").
    :param description: Description of the load case.
    :param group_name: Name of the load group this case belongs to.
    :param case_type: "PERMANENT" or "VARIABLE".
    :param permanent_type: Type of permanent load (if applicable).
    :param variable_type: Type of variable load (if applicable).
    :param specification: Specification for variable load (if applicable).
    :param duration: Duration for variable load (if applicable).
    """

    name: str
    description: str
    group_name: str
    case_type: Literal["PERMANENT", "VARIABLE"]
    permanent_type: Literal["SELF_WEIGHT", "STANDARD", "PRIMARY_EFFECT"] | None = None
    variable_type: Literal["STATIC", "PRIMARY_EFFECT"] | None = None
    specification: Literal["STANDARD", "STATIC_WIND", "SNOW", "TEMPERATURE", "EARTHQUAKE"] | None = None
    duration: Literal["INSTANTANEOUS", "SHORT", "MEDIUM", "LONG"] | None = None


@dataclass
class NodeDefinition:
    """Defines the properties for a SCIA Node."""

    name: str
    x: float
    y: float
    z: float


@dataclass
class MaterialDefinition:
    """Defines the properties for a SCIA Material."""

    name: str
    material_id: int = 0


@dataclass
class PlateDefinition:
    """
    Defines the properties for a SCIA Plate (Plane).

    :param name: Name of the plate.
    :param corner_node_names: List of four node names that form the plate corners.
    :param thickness: Thickness of the plate.
    :param material_name: Name of the material used for the plate.
    """

    name: str
    corner_node_names: list[str]
    thickness: float
    material_name: str


@dataclass
class SurfaceLoadDefinition:
    """
    Defines the properties for a SCIA Free Surface Load.

    :param name: Name of the load.
    :param load_case_name: Name of the load case this load belongs to.
    :param corner_points: List of 4 corner coordinates for the load patch.
    :param load_value: Load magnitude in [N/m²].
    """

    name: str
    load_case_name: str
    corner_points: list[tuple[float, float, float]]
    load_value: float


@dataclass
class LoadCombinationDefinition:
    """
    Defines the properties for a SCIA Load Combination.

    :param name: Name of the load combination.
    :param combination_type: Type of combination (e.g., "ULS", "SLS_CHAR").
    :param load_case_factors: Dictionary mapping load case names to their factors.
    :param description: Optional description for the combination.
    """

    name: str
    combination_type: SciaCombinationType
    load_case_factors: dict[str, float]
    description: str = ""
