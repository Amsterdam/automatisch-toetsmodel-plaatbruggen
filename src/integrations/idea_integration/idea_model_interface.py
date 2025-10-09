"""
IDEA RCS Model Builder Protocol Interface.

This module defines the Protocol interface for building IDEA RCS models,
enabling the src layer to work with IDEA models without depending on the VIKTOR SDK.

The Protocol pattern allows:
- SDK independence in src layer
- Easy mocking for testing
- Clear contract for model building operations
- Flexibility to swap implementations
"""

from typing import Any, Protocol

from src.integrations.idea_integration.idea_enums import (
    BarSurface,
    ConcAggregateType,
    ConcCementClass,
    ConcDiagramType,
    ConcreteMaterial,
    ReinfDiagramType,
    ReinfFabrication,
    ReinforcementClass,
    ReinforcementMaterial,
    ReinfType,
)

# Type aliases for IDEA SDK objects (actual types unknown to src layer)
IdeaModel = Any
IdeaSlab = Any
IdeaConcreteMaterial = Any
IdeaReinforcementMaterial = Any
IdeaMatConcreteEc2 = Any
IdeaMatReinforcementEc2 = Any
IdeaRectSection = Any
IdeaProjectData = Any
IdeaLoadingSLS = Any
IdeaLoadingULS = Any
IdeaResultOfInternalForces = Any


class IdeaModelBuilder(Protocol):
    """
    Protocol for building IDEA RCS models.

    This interface defines all operations needed to create and configure IDEA RCS models
    without depending on the VIKTOR SDK. The app layer provides a concrete implementation.
    """

    def create_model(self, project_data: IdeaProjectData) -> IdeaModel:
        """
        Create a new IDEA RCS model with project information.

        :param project_data: Project metadata (name, description, author, etc.)
        :type project_data: IdeaProjectData
        :returns: Created IDEA model object
        :rtype: IdeaModel
        """
        ...

    def create_project_data(self, name: str, description: str, author: str, national_annex: str) -> IdeaProjectData:
        """
        Create project data object for model initialization.

        :param name: Project name
        :type name: str
        :param description: Project description
        :type description: str
        :param author: Project author
        :type author: str
        :param national_annex: National annex (e.g., "Dutch")
        :type national_annex: str
        :returns: Project data object
        :rtype: IdeaProjectData
        """
        ...

    def create_rect_section(self, width: float, height: float) -> IdeaRectSection:
        """
        Create a rectangular cross-section.

        :param width: Section width in meters
        :type width: float
        :param height: Section height in meters
        :type height: float
        :returns: Rectangular section object
        :rtype: IdeaRectSection
        """
        ...

    def create_one_way_slab(
        self,
        model: IdeaModel,
        section: IdeaRectSection,
        concrete_material: IdeaConcreteMaterial,
        name: str,
        rcs_name: str,
    ) -> IdeaSlab:
        """
        Create a one-way slab in the model.

        :param model: IDEA model object
        :type model: IdeaModel
        :param section: Cross-section geometry
        :type section: IdeaRectSection
        :param concrete_material: Concrete material
        :type concrete_material: IdeaConcreteMaterial
        :param name: Slab name
        :type name: str
        :param rcs_name: RCS calculation name
        :type rcs_name: str
        :returns: Created slab object
        :rtype: IdeaSlab
        """
        ...

    def create_bar_on_slab(
        self,
        slab: IdeaSlab,
        coords: tuple[float, float],
        diameter: float,
        reinforcement_material: IdeaReinforcementMaterial,
    ) -> None:
        """
        Create a reinforcement bar on a slab.

        :param slab: Slab object to add bar to
        :type slab: IdeaSlab
        :param coords: Bar coordinates (x, y) in meters
        :type coords: tuple[float, float]
        :param diameter: Bar diameter in meters
        :type diameter: float
        :param reinforcement_material: Reinforcement material
        :type reinforcement_material: IdeaReinforcementMaterial
        """
        ...

    def create_extreme_on_slab(
        self,
        slab: IdeaSlab,
        description: str,
        characteristic: IdeaLoadingSLS,
        frequent: IdeaLoadingSLS,
        fundamental: IdeaLoadingULS,
    ) -> None:
        """
        Create an extreme load case on a slab.

        :param slab: Slab object to add load case to
        :type slab: IdeaSlab
        :param description: Load case description
        :type description: str
        :param characteristic: Characteristic SLS loading
        :type characteristic: IdeaLoadingSLS
        :param frequent: Frequent SLS loading
        :type frequent: IdeaLoadingSLS
        :param fundamental: Fundamental ULS loading
        :type fundamental: IdeaLoadingULS
        """
        ...

    def create_loading_sls(self, internal_forces: IdeaResultOfInternalForces) -> IdeaLoadingSLS:
        """
        Create an SLS loading object from internal forces.

        :param internal_forces: Internal forces result
        :type internal_forces: IdeaResultOfInternalForces
        :returns: SLS loading object
        :rtype: IdeaLoadingSLS
        """
        ...

    def create_loading_uls(self, internal_forces: IdeaResultOfInternalForces) -> IdeaLoadingULS:
        """
        Create a ULS loading object from internal forces.

        :param internal_forces: Internal forces result
        :type internal_forces: IdeaResultOfInternalForces
        :returns: ULS loading object
        :rtype: IdeaLoadingULS
        """
        ...

    def create_result_of_internal_forces(self, Qz: float = 0.0, My: float = 0.0) -> IdeaResultOfInternalForces:  # noqa: N803
        """
        Create an internal forces result object.

        :param Qz: Shear force Qz in kN
        :type Qz: float
        :param My: Bending moment My in kNm
        :type My: float
        :returns: Internal forces result object
        :rtype: IdeaResultOfInternalForces
        """
        ...

    def get_concrete_material_enum(self, quality: str) -> ConcreteMaterial:
        """
        Get concrete material enum from quality string.

        :param quality: Concrete quality string (e.g., "C30/37")
        :type quality: str
        :returns: Concrete material enum
        :rtype: ConcreteMaterial
        :raises ValueError: If quality is not supported
        """
        ...

    def get_reinforcement_material_enum(self, quality: str) -> ReinforcementMaterial:
        """
        Get reinforcement material enum from quality string.

        :param quality: Reinforcement quality string (e.g., "B500B")
        :type quality: str
        :returns: Reinforcement material enum
        :rtype: ReinforcementMaterial
        :raises ValueError: If quality is not supported
        """
        ...

    def create_concrete_material_modern(
        self,
        model: IdeaModel,
        material_enum: ConcreteMaterial,
    ) -> IdeaConcreteMaterial:
        """
        Create a modern (Eurocode) concrete material.

        :param model: IDEA model object
        :type model: IdeaModel
        :param material_enum: Concrete material enum
        :type material_enum: ConcreteMaterial
        :returns: Created concrete material
        :rtype: IdeaConcreteMaterial
        """
        ...

    def create_concrete_material_historical(
        self,
        model: IdeaModel,
        quality: str,
        cement_class: ConcCementClass,
        aggregate_type: ConcAggregateType,
        diagram_type: ConcDiagramType,
    ) -> IdeaMatConcreteEc2:
        """
        Create a historical concrete material from CSV data.

        :param model: IDEA model object
        :type model: IdeaModel
        :param quality: Concrete quality string (e.g., "K150", "B25")
        :type quality: str
        :param cement_class: Cement class enum
        :type cement_class: ConcCementClass
        :param aggregate_type: Aggregate type enum
        :type aggregate_type: ConcAggregateType
        :param diagram_type: Diagram type enum
        :type diagram_type: ConcDiagramType
        :returns: Created concrete material
        :rtype: IdeaMatConcreteEc2
        """
        ...

    def create_reinforcement_material_modern(
        self,
        model: IdeaModel,
        material_enum: ReinforcementMaterial,
    ) -> IdeaReinforcementMaterial:
        """
        Create a modern (Eurocode) reinforcement material.

        :param model: IDEA model object
        :type model: IdeaModel
        :param material_enum: Reinforcement material enum
        :type material_enum: ReinforcementMaterial
        :returns: Created reinforcement material
        :rtype: IdeaReinforcementMaterial
        """
        ...

    def create_reinforcement_material_historical(
        self,
        model: IdeaModel,
        quality: str,
        reinforcement_class: ReinforcementClass,
        bar_surface: BarSurface,
        diagram_type: ReinfDiagramType,
        reinf_type: ReinfType,
        fabrication: ReinfFabrication,
    ) -> IdeaMatReinforcementEc2:
        """
        Create a historical reinforcement material from CSV data.

        :param model: IDEA model object
        :type model: IdeaModel
        :param quality: Reinforcement quality string
        :type quality: str
        :param reinforcement_class: Reinforcement class enum
        :type reinforcement_class: ReinforcementClass
        :param bar_surface: Bar surface enum
        :type bar_surface: BarSurface
        :param diagram_type: Diagram type enum
        :type diagram_type: ReinfDiagramType
        :param reinf_type: Reinforcement type enum
        :type reinf_type: ReinfType
        :param fabrication: Fabrication method enum
        :type fabrication: ReinfFabrication
        :returns: Created reinforcement material
        :rtype: IdeaMatReinforcementEc2
        """
        ...

    def generate_xml_input(self, model: IdeaModel) -> bytes:
        """
        Generate XML input file from model.

        :param model: IDEA model object
        :type model: IdeaModel
        :returns: XML content as bytes
        :rtype: bytes
        """
        ...

    def is_historical_concrete_material(self, quality: str) -> bool:
        """
        Check if concrete quality string represents a historical material.

        :param quality: Concrete quality string
        :type quality: str
        :returns: True if historical material
        :rtype: bool
        """
        ...

    def is_historical_reinforcement_material(self, quality: str) -> bool:
        """
        Check if reinforcement quality string represents a historical material.

        :param quality: str
        :type quality: str
        :returns: True if historical material
        :rtype: bool
        """
        ...
