"""
IDEA RCS Model Builder - VIKTOR SDK Implementation.

This module provides the concrete implementation of the IdeaModelBuilder Protocol
using the VIKTOR SDK. It acts as the bridge between the src layer and the SDK.

This implementation:
- Imports and uses viktor.external.idea_rcs
- Extracts .value from enum bridge objects to get SDK enums
- Handles all SDK-specific logic and error handling
- Provides material creation with support for both modern and historical materials
"""

from typing import Any

from viktor.external import idea_rcs

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


class ViktorIdeaModelBuilder:
    """
    Concrete implementation of IdeaModelBuilder using VIKTOR SDK.

    This class provides all functionality needed to create and configure IDEA RCS models
    using the VIKTOR external integration for IDEA StatiCa.
    """

    def create_model(self, project_data: idea_rcs.ProjectData) -> idea_rcs.Model:
        """
        Create a new IDEA RCS model with project information.

        :param project_data: Project metadata
        :type project_data: idea_rcs.ProjectData
        :returns: Created IDEA model
        :rtype: idea_rcs.Model
        """
        return idea_rcs.Model(project_data=project_data)

    def create_project_data(self, name: str, description: str, author: str, national_annex: str) -> idea_rcs.ProjectData:
        """
        Create project data object for model initialization.

        :param name: Project name
        :type name: str
        :param description: Project description
        :type description: str
        :param author: Project author
        :type author: str
        :param national_annex: National annex
        :type national_annex: str
        :returns: Project data object
        :rtype: idea_rcs.ProjectData
        """
        return idea_rcs.ProjectData(
            name=name,
            description=description,
            author=author,
            national_annex=national_annex,
        )

    def create_rect_section(self, width: float, height: float) -> idea_rcs.RectSection:
        """
        Create a rectangular cross-section.

        :param width: Section width in meters
        :type width: float
        :param height: Section height in meters
        :type height: float
        :returns: Rectangular section object
        :rtype: idea_rcs.RectSection
        """
        return idea_rcs.RectSection(width, height)

    def create_one_way_slab(
        self,
        model: idea_rcs.Model,
        section: idea_rcs.RectSection,
        concrete_material: Any,  # noqa: ANN401
        name: str,
        rcs_name: str,
    ) -> idea_rcs.OneWaySlab:
        """
        Create a one-way slab in the model.

        :param model: IDEA model object
        :type model: idea_rcs.Model
        :param section: Cross-section geometry
        :type section: idea_rcs.RectSection
        :param concrete_material: Concrete material
        :type concrete_material: Any
        :param name: Slab name
        :type name: str
        :param rcs_name: RCS calculation name
        :type rcs_name: str
        :returns: Created slab object
        :rtype: idea_rcs.OneWaySlab
        """
        return model.create_one_way_slab(section, concrete_material, name=name, rcs_name=rcs_name)

    def create_bar_on_slab(
        self,
        slab: idea_rcs.OneWaySlab,
        coords: tuple[float, float],
        diameter: float,
        reinforcement_material: Any,  # noqa: ANN401
    ) -> None:
        """
        Create a reinforcement bar on a slab.

        :param slab: Slab object to add bar to
        :type slab: idea_rcs.OneWaySlab
        :param coords: Bar coordinates (x, y) in meters
        :type coords: tuple[float, float]
        :param diameter: Bar diameter in meters
        :type diameter: float
        :param reinforcement_material: Reinforcement material
        :type reinforcement_material: Any
        """
        slab.create_bar(coords, diameter, reinforcement_material)

    def create_extreme_on_slab(
        self,
        slab: idea_rcs.OneWaySlab,
        description: str,
        frequent: idea_rcs.LoadingSLS,
        fundamental: idea_rcs.LoadingULS,
    ) -> None:
        """
        Create an extreme load case on a slab.

        :param slab: Slab object to add load case to
        :type slab: idea_rcs.OneWaySlab
        :param description: Load case description
        :type description: str
        :param frequent: Frequent SLS loading
        :type frequent: idea_rcs.LoadingSLS
        :param fundamental: Fundamental ULS loading
        :type fundamental: idea_rcs.LoadingULS
        """
        slab.create_extreme(description=description, frequent=frequent, fundamental=fundamental)

    def create_loading_sls(self, internal_forces: idea_rcs.ResultOfInternalForces) -> idea_rcs.LoadingSLS:
        """
        Create an SLS loading object from internal forces.

        :param internal_forces: Internal forces result
        :type internal_forces: idea_rcs.ResultOfInternalForces
        :returns: SLS loading object
        :rtype: idea_rcs.LoadingSLS
        """
        return idea_rcs.LoadingSLS(internal_forces)

    def create_loading_uls(self, internal_forces: idea_rcs.ResultOfInternalForces) -> idea_rcs.LoadingULS:
        """
        Create a ULS loading object from internal forces.

        :param internal_forces: Internal forces result
        :type internal_forces: idea_rcs.ResultOfInternalForces
        :returns: ULS loading object
        :rtype: idea_rcs.LoadingULS
        """
        return idea_rcs.LoadingULS(internal_forces)

    def create_result_of_internal_forces(self, Qz: float = 0.0, My: float = 0.0) -> idea_rcs.ResultOfInternalForces:  # noqa: N803
        """
        Create an internal forces result object.

        :param Qz: Shear force Qz in kN
        :type Qz: float
        :param My: Bending moment My in kNm
        :type My: float
        :returns: Internal forces result object
        :rtype: idea_rcs.ResultOfInternalForces
        """
        return idea_rcs.ResultOfInternalForces(Qz=Qz, My=My)

    def get_concrete_material_enum(self, quality: str) -> ConcreteMaterial:
        """
        Get concrete material enum from quality string.

        :param quality: Concrete quality string (e.g., "C30/37")
        :type quality: str
        :returns: Concrete material enum
        :rtype: ConcreteMaterial
        :raises ValueError: If quality is not supported
        """
        material_map = {
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

        if quality not in material_map:
            raise ValueError(f"Concrete quality '{quality}' is not supported. Available modern materials: {list(material_map.keys())}")

        return material_map[quality]

    def get_reinforcement_material_enum(self, quality: str) -> ReinforcementMaterial:
        """
        Get reinforcement material enum from quality string.

        :param quality: Reinforcement quality string (e.g., "B500B")
        :type quality: str
        :returns: Reinforcement material enum
        :rtype: ReinforcementMaterial
        :raises ValueError: If quality is not supported
        """
        material_map = {
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

        if quality not in material_map:
            raise ValueError(f"Reinforcement quality '{quality}' is not supported. Available modern materials: {list(material_map.keys())}")

        return material_map[quality]

    def create_concrete_material_modern(
        self,
        model: idea_rcs.Model,
        material_enum: ConcreteMaterial,
    ) -> idea_rcs.MatConcreteEc2:
        """
        Create a modern (Eurocode) concrete material.

        :param model: IDEA model object
        :type model: idea_rcs.Model
        :param material_enum: Concrete material enum
        :type material_enum: ConcreteMaterial
        :returns: Created concrete material
        :rtype: idea_rcs.MatConcreteEc2
        """
        # Extract SDK enum from bridge enum
        sdk_material = material_enum.value
        return model.create_concrete_material(sdk_material)

    def create_concrete_material_historical(
        self,
        model: idea_rcs.Model,
        quality: str,
        cement_class: ConcCementClass,  # noqa: ARG002
        aggregate_type: ConcAggregateType,  # noqa: ARG002
        diagram_type: ConcDiagramType,  # noqa: ARG002
    ) -> idea_rcs.MatConcreteEc2:
        """
        Create a historical concrete material from CSV data.

        :param model: IDEA model object
        :type model: idea_rcs.Model
        :param quality: Concrete quality string (e.g., "K150", "B25")
        :type quality: str
        :param cement_class: Cement class enum
        :type cement_class: ConcCementClass
        :param aggregate_type: Aggregate type enum
        :type aggregate_type: ConcAggregateType
        :param diagram_type: Diagram type enum
        :type diagram_type: ConcDiagramType
        :returns: Created concrete material
        :rtype: idea_rcs.MatConcreteEc2
        :raises ValueError: If material CSV file not found or data invalid
        """
        # Import generator function
        from src.integrations.idea_integration.idea_material_generator import create_idea_concrete_material

        # Create material using generator (only quality parameter is used, others are deprecated)
        return create_idea_concrete_material(
            model,
            material_name=quality,
            custom_name=None,
        )

    def create_reinforcement_material_modern(
        self,
        model: idea_rcs.Model,
        material_enum: ReinforcementMaterial,
    ) -> idea_rcs.MatReinforcementEc2:
        """
        Create a modern (Eurocode) reinforcement material.

        :param model: IDEA model object
        :type model: idea_rcs.Model
        :param material_enum: Reinforcement material enum
        :type material_enum: ReinforcementMaterial
        :returns: Created reinforcement material
        :rtype: idea_rcs.MatReinforcementEc2
        """
        # Extract SDK enum from bridge enum
        sdk_material = material_enum.value
        return model.create_reinforcement_material(sdk_material)

    def create_reinforcement_material_historical(  # noqa: PLR0913
        self,
        model: idea_rcs.Model,
        quality: str,
        reinforcement_class: ReinforcementClass,  # noqa: ARG002
        bar_surface: BarSurface,  # noqa: ARG002
        diagram_type: ReinfDiagramType,  # noqa: ARG002
        reinf_type: ReinfType,  # noqa: ARG002
        fabrication: ReinfFabrication,  # noqa: ARG002
    ) -> idea_rcs.MatReinforcementEc2:
        """
        Create a historical reinforcement material from CSV data.

        :param model: IDEA model object
        :type model: idea_rcs.Model
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
        :rtype: idea_rcs.MatReinforcementEc2
        :raises ValueError: If material CSV file not found or data invalid
        """
        # Import generator function
        from src.integrations.idea_integration.idea_material_generator import create_idea_reinforcement_material

        # Create material using generator (only quality parameter is used)
        return create_idea_reinforcement_material(
            model,
            material_name=quality,
            custom_name=None,
        )

    def generate_xml_input(self, model: idea_rcs.Model) -> bytes:
        """
        Generate XML input file from model.

        :param model: IDEA model object
        :type model: idea_rcs.Model
        :returns: XML content as bytes
        :rtype: bytes
        """
        xml_file = model.generate_xml_input()
        # If it's a File object, get the content
        if hasattr(xml_file, "getvalue"):
            return xml_file.getvalue()
        if hasattr(xml_file, "read"):
            return xml_file.read()
        return xml_file

    def is_historical_concrete_material(self, quality: str) -> bool:
        """
        Check if concrete quality string represents a historical material.

        :param quality: Concrete quality string
        :type quality: str
        :returns: True if historical material
        :rtype: bool
        """
        historical_materials = {
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
        }
        return quality in historical_materials

    def is_historical_reinforcement_material(self, quality: str) -> bool:
        """
        Check if reinforcement quality string represents a historical material.

        :param quality: Reinforcement quality string
        :type quality: str
        :returns: True if historical material
        :rtype: bool
        """
        # Check if quality is NOT in the modern materials list
        modern_materials = {
            "B400A",
            "B400B",
            "B400C",
            "B500A",
            "B500B",
            "B500C",
            "B550A",
            "B550B",
            "B600A",
            "B600B",
            "B600C",
        }
        return quality not in modern_materials
