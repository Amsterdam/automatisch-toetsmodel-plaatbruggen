"""
Tests for IDEA model builder (app layer).

This module tests the ViktorIdeaModelBuilder class which implements the
IdeaModelBuilder Protocol using the VIKTOR SDK.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.bridge.idea_model_builder import ViktorIdeaModelBuilder
from src.integrations.idea_integration.idea_enums import ConcreteMaterial, ReinforcementMaterial


class TestViktorIdeaModelBuilder:
    """Test ViktorIdeaModelBuilder class."""

    @pytest.fixture
    def builder(self) -> ViktorIdeaModelBuilder:
        """Create a builder instance for testing."""
        return ViktorIdeaModelBuilder()

    def test_builder_instantiation(self, builder: ViktorIdeaModelBuilder) -> None:
        """Test that builder can be instantiated."""
        assert builder is not None
        assert isinstance(builder, ViktorIdeaModelBuilder)

    def test_get_concrete_material_enum(self, builder: ViktorIdeaModelBuilder) -> None:
        """Test getting concrete material enum from string."""
        # Test valid materials
        result = builder.get_concrete_material_enum("C30/37")
        assert result == ConcreteMaterial.C30_37

        result = builder.get_concrete_material_enum("C40/50")
        assert result == ConcreteMaterial.C40_50

        result = builder.get_concrete_material_enum("C50/60")
        assert result == ConcreteMaterial.C50_60

    def test_get_concrete_material_enum_invalid(self, builder: ViktorIdeaModelBuilder) -> None:
        """Test getting concrete material enum with invalid string."""
        with pytest.raises(ValueError, match="Concrete quality"):
            builder.get_concrete_material_enum("InvalidMaterial")

    def test_get_reinforcement_material_enum(self, builder: ViktorIdeaModelBuilder) -> None:
        """Test getting reinforcement material enum from string."""
        # Test valid materials
        result = builder.get_reinforcement_material_enum("B500B")
        assert result == ReinforcementMaterial.B_500B

        result = builder.get_reinforcement_material_enum("B400A")
        assert result == ReinforcementMaterial.B_400A

        result = builder.get_reinforcement_material_enum("B550A")
        assert result == ReinforcementMaterial.B_550A

    def test_get_reinforcement_material_enum_invalid(self, builder: ViktorIdeaModelBuilder) -> None:
        """Test getting reinforcement material enum with invalid string."""
        with pytest.raises(ValueError, match="Reinforcement quality"):
            builder.get_reinforcement_material_enum("InvalidMaterial")

    def test_is_historical_concrete_material(self, builder: ViktorIdeaModelBuilder) -> None:
        """Test checking if concrete material is historical."""
        # Modern materials
        assert builder.is_historical_concrete_material("C30/37") is False
        assert builder.is_historical_concrete_material("C40/50") is False

        # Historical materials
        assert builder.is_historical_concrete_material("K200") is True
        assert builder.is_historical_concrete_material("K250") is True

    def test_is_historical_reinforcement_material(self, builder: ViktorIdeaModelBuilder) -> None:
        """Test checking if reinforcement material is historical."""
        # Modern materials
        assert builder.is_historical_reinforcement_material("B500B") is False
        assert builder.is_historical_reinforcement_material("B400A") is False

        # Historical materials
        assert builder.is_historical_reinforcement_material("FeB22") is True
        assert builder.is_historical_reinforcement_material("FeB400") is True

    @patch("app.bridge.idea_model_builder.idea_rcs")
    def test_create_project_data(self, mock_idea_rcs: MagicMock, builder: ViktorIdeaModelBuilder) -> None:
        """Test creating project data."""
        mock_project_data = MagicMock()
        mock_idea_rcs.ProjectData.return_value = mock_project_data

        result = builder.create_project_data(
            name="Test Bridge",
            description="Test Description",
            author="Test Author",
            national_annex="Dutch",
        )

        assert result == mock_project_data
        mock_idea_rcs.ProjectData.assert_called_once_with(
            name="Test Bridge",
            description="Test Description",
            author="Test Author",
            national_annex="Dutch",
        )

    @patch("app.bridge.idea_model_builder.idea_rcs")
    def test_create_model(self, mock_idea_rcs: MagicMock, builder: ViktorIdeaModelBuilder) -> None:
        """Test creating IDEA model."""
        mock_project_data = MagicMock()
        mock_model = MagicMock()
        mock_idea_rcs.Model.return_value = mock_model

        result = builder.create_model(mock_project_data)

        assert result == mock_model
        mock_idea_rcs.Model.assert_called_once_with(project_data=mock_project_data)

    @patch("app.bridge.idea_model_builder.idea_rcs")
    def test_create_concrete_material_modern(self, mock_idea_rcs: MagicMock, builder: ViktorIdeaModelBuilder) -> None:  # noqa: ARG002
        """Test creating modern concrete material."""
        mock_model = MagicMock()
        mock_material = MagicMock()
        mock_model.create_concrete_material.return_value = mock_material

        # Use enum
        material_enum = ConcreteMaterial.C30_37

        result = builder.create_concrete_material_modern(mock_model, material_enum)

        assert result == mock_material
        mock_model.create_concrete_material.assert_called_once_with(material_enum.value)

    @patch("app.bridge.idea_model_builder.idea_rcs")
    def test_create_reinforcement_material_modern(self, mock_idea_rcs: MagicMock, builder: ViktorIdeaModelBuilder) -> None:  # noqa: ARG002
        """Test creating modern reinforcement material."""
        mock_model = MagicMock()
        mock_material = MagicMock()
        mock_model.create_reinforcement_material.return_value = mock_material

        # Use enum
        material_enum = ReinforcementMaterial.B_500B

        result = builder.create_reinforcement_material_modern(mock_model, material_enum)

        assert result == mock_material
        mock_model.create_reinforcement_material.assert_called_once_with(material_enum.value)

    @patch("app.bridge.idea_model_builder.idea_rcs")
    def test_create_rect_section(self, mock_idea_rcs: MagicMock, builder: ViktorIdeaModelBuilder) -> None:
        """Test creating rectangular section."""
        mock_section = MagicMock()
        mock_idea_rcs.RectSection.return_value = mock_section

        result = builder.create_rect_section(1.0, 0.3)

        assert result == mock_section
        mock_idea_rcs.RectSection.assert_called_once_with(1.0, 0.3)

    @patch("app.bridge.idea_model_builder.idea_rcs")
    def test_create_one_way_slab(self, mock_idea_rcs: MagicMock, builder: ViktorIdeaModelBuilder) -> None:  # noqa: ARG002
        """Test creating one-way slab."""
        mock_model = MagicMock()
        mock_section = MagicMock()
        mock_material = MagicMock()
        mock_slab = MagicMock()
        mock_model.create_one_way_slab.return_value = mock_slab

        result = builder.create_one_way_slab(
            mock_model,
            mock_section,
            mock_material,
            name="test_slab",
            rcs_name="rcs_test",
        )

        assert result == mock_slab
        mock_model.create_one_way_slab.assert_called_once_with(
            mock_section,
            mock_material,
            name="test_slab",
            rcs_name="rcs_test",
        )

    @patch("app.bridge.idea_model_builder.idea_rcs")
    def test_create_bar_on_slab(self, mock_idea_rcs: MagicMock, builder: ViktorIdeaModelBuilder) -> None:  # noqa: ARG002
        """Test creating bar on slab."""
        mock_slab = MagicMock()
        mock_material = MagicMock()
        coords = (0.5, 0.1)
        diameter = 0.016  # 16mm in meters

        builder.create_bar_on_slab(mock_slab, coords, diameter, mock_material)

        mock_slab.create_bar.assert_called_once_with(coords, diameter, mock_material)

    @patch("app.bridge.idea_model_builder.idea_rcs")
    def test_create_result_of_internal_forces(self, mock_idea_rcs: MagicMock, builder: ViktorIdeaModelBuilder) -> None:
        """Test creating result of internal forces."""
        mock_forces = MagicMock()
        mock_idea_rcs.ResultOfInternalForces.return_value = mock_forces

        result = builder.create_result_of_internal_forces(Qz=100.0, My=50.0)

        assert result == mock_forces
        mock_idea_rcs.ResultOfInternalForces.assert_called_once_with(Qz=100.0, My=50.0)

    @patch("app.bridge.idea_model_builder.idea_rcs")
    def test_create_loading_sls(self, mock_idea_rcs: MagicMock, builder: ViktorIdeaModelBuilder) -> None:
        """Test creating SLS loading."""
        mock_forces = MagicMock()
        mock_loading = MagicMock()
        mock_idea_rcs.LoadingSLS.return_value = mock_loading

        result = builder.create_loading_sls(mock_forces)

        assert result == mock_loading
        mock_idea_rcs.LoadingSLS.assert_called_once_with(mock_forces)

    @patch("app.bridge.idea_model_builder.idea_rcs")
    def test_create_loading_uls(self, mock_idea_rcs: MagicMock, builder: ViktorIdeaModelBuilder) -> None:
        """Test creating ULS loading."""
        mock_forces = MagicMock()
        mock_loading = MagicMock()
        mock_idea_rcs.LoadingULS.return_value = mock_loading

        result = builder.create_loading_uls(mock_forces)

        assert result == mock_loading
        mock_idea_rcs.LoadingULS.assert_called_once_with(mock_forces)

    @patch("app.bridge.idea_model_builder.idea_rcs")
    def test_create_extreme_on_slab(self, mock_idea_rcs: MagicMock, builder: ViktorIdeaModelBuilder) -> None:  # noqa: ARG002
        """Test creating extreme on slab."""
        mock_slab = MagicMock()
        mock_char = MagicMock()
        mock_freq = MagicMock()
        mock_fund = MagicMock()

        builder.create_extreme_on_slab(
            mock_slab,
            description="Test load",
            characteristic=mock_char,
            frequent=mock_freq,
            fundamental=mock_fund,
        )

        mock_slab.create_extreme.assert_called_once_with(
            description="Test load",
            characteristic=mock_char,
            frequent=mock_freq,
            fundamental=mock_fund,
        )

    @patch("app.bridge.idea_model_builder.idea_rcs")
    def test_generate_xml_input(self, mock_idea_rcs: MagicMock, builder: ViktorIdeaModelBuilder) -> None:  # noqa: ARG002
        """Test generating XML input from model."""
        mock_model = MagicMock()
        mock_xml = b"<xml>test</xml>"
        mock_model.generate_xml_input.return_value = mock_xml

        result = builder.generate_xml_input(mock_model)

        assert result == mock_xml
        mock_model.generate_xml_input.assert_called_once()


class TestEnumConversion:
    """Test enum to SDK conversion patterns."""

    @pytest.fixture
    def builder(self) -> ViktorIdeaModelBuilder:
        """Create a builder instance for testing."""
        return ViktorIdeaModelBuilder()

    def test_concrete_material_string_to_enum_mapping(self, builder: ViktorIdeaModelBuilder) -> None:
        """Test mapping of concrete material strings to enums."""
        test_cases = [
            ("C12/15", ConcreteMaterial.C12_15),
            ("C20/25", ConcreteMaterial.C20_25),
            ("C30/37", ConcreteMaterial.C30_37),
            ("C40/50", ConcreteMaterial.C40_50),
            ("C50/60", ConcreteMaterial.C50_60),
        ]

        for material_str, expected_enum in test_cases:
            result = builder.get_concrete_material_enum(material_str)
            assert result == expected_enum, f"Failed for {material_str}"

    def test_reinforcement_material_string_to_enum_mapping(self, builder: ViktorIdeaModelBuilder) -> None:
        """Test mapping of reinforcement material strings to enums."""
        test_cases = [
            ("B400A", ReinforcementMaterial.B_400A),
            ("B400B", ReinforcementMaterial.B_400B),
            ("B500A", ReinforcementMaterial.B_500A),
            ("B500B", ReinforcementMaterial.B_500B),
            ("B500C", ReinforcementMaterial.B_500C),
        ]

        for material_str, expected_enum in test_cases:
            result = builder.get_reinforcement_material_enum(material_str)
            assert result == expected_enum, f"Failed for {material_str}"

    def test_enum_value_attribute(self) -> None:
        """Test that enum values can be accessed."""
        # Enums should have .value attribute that contains SDK object or string
        assert hasattr(ConcreteMaterial.C30_37, "value")
        assert hasattr(ReinforcementMaterial.B_500B, "value")

        # Values should not be None
        assert ConcreteMaterial.C30_37.value is not None
        assert ReinforcementMaterial.B_500B.value is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
