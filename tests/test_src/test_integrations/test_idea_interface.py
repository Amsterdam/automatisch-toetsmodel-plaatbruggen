"""
Test module for IDEA StatiCa integration interface.

This module provides comprehensive testing for the IDEA StatiCa integration,
including model creation, parameter extraction, and analysis functionality.
"""

from unittest.mock import Mock, patch

import pytest

from src.integrations.idea_interface import (
    BridgeCrossSectionData,
    ReinforcementConfig,
    _get_concrete_material_enum,
    _get_reinforcement_material_enum,
    create_bridge_idea_model,
    create_reinforcement_layout,
    create_simple_idea_slab_model,
    extract_cross_section_from_params,
    run_idea_analysis,
)


class TestBridgeCrossSectionData:
    """Tests for BridgeCrossSectionData dataclass."""

    def test_bridge_cross_section_data_creation(self) -> None:
        """Test creating BridgeCrossSectionData with valid parameters."""
        reinforcement_config = {
            "main_diameter_top": 0.012,
            "main_spacing_top": 0.150,
            "main_diameter_bottom": 0.012,
            "main_spacing_bottom": 0.150,
            "concrete_cover": 0.055,
        }

        cross_section = BridgeCrossSectionData(
            width=30.0, height=2.0, concrete_material="C30/37", reinforcement_material="B500B", reinforcement_config=reinforcement_config
        )

        assert cross_section.width == 30.0
        assert cross_section.height == 2.0
        assert cross_section.concrete_material == "C30/37"
        assert cross_section.reinforcement_material == "B500B"
        assert cross_section.reinforcement_config == reinforcement_config


class TestReinforcementConfig:
    """Tests for ReinforcementConfig dataclass."""

    def test_reinforcement_config_creation(self) -> None:
        """Test creating ReinforcementConfig with valid parameters."""
        main_bars_top = [(-0.101, 0.175, 0.012), (0.101, 0.175, 0.012)]
        main_bars_bottom = [(-0.101, -0.175, 0.012), (0.101, -0.175, 0.012)]

        config = ReinforcementConfig(main_bars_top=main_bars_top, main_bars_bottom=main_bars_bottom, concrete_cover=0.055)

        assert config.main_bars_top == main_bars_top
        assert config.main_bars_bottom == main_bars_bottom
        assert config.concrete_cover == 0.055


class TestExtractCrossSectionFromParams:
    """Tests for extract_cross_section_from_params function."""

    def test_extract_cross_section_valid_params(self) -> None:
        """Test extracting cross-section from valid bridge parameters."""
        bridge_segments_params = [{"bz1": 10.0, "bz2": 5.0, "bz3": 15.0, "dz": 2.0, "dz_2": 3.0, "l": 0}]

        result = extract_cross_section_from_params(bridge_segments_params)

        assert result.width == 30.0  # bz1 + bz2 + bz3
        assert result.height == 3.0  # max(dz, dz_2)
        assert result.concrete_material == "C30/37"
        assert result.reinforcement_material == "B500B"
        assert "main_diameter_top" in result.reinforcement_config

    def test_extract_cross_section_empty_params(self) -> None:
        """Test extracting cross-section from empty parameters."""
        with pytest.raises(ValueError, match="No bridge segments provided"):
            extract_cross_section_from_params([])

    def test_extract_cross_section_zero_width(self) -> None:
        """Test extracting cross-section with zero width."""
        bridge_segments_params = [{"bz1": 0.0, "bz2": 0.0, "bz3": 0.0, "dz": 2.0, "dz_2": 3.0, "l": 0}]

        with pytest.raises(ValueError, match="Cross-section width must be positive"):
            extract_cross_section_from_params(bridge_segments_params)

    def test_extract_cross_section_zero_height(self) -> None:
        """Test extracting cross-section with zero height."""
        bridge_segments_params = [{"bz1": 10.0, "bz2": 5.0, "bz3": 15.0, "dz": 0.0, "dz_2": 0.0, "l": 0}]

        with pytest.raises(ValueError, match="Cross-section height must be positive"):
            extract_cross_section_from_params(bridge_segments_params)

    def test_extract_cross_section_missing_fields(self) -> None:
        """Test extracting cross-section with missing fields."""
        bridge_segments_params = [
            {
                "bz1": 10.0,
                # Missing bz2, bz3, etc.
            }
        ]

        result = extract_cross_section_from_params(bridge_segments_params)
        # Should use default values (0.0)
        assert result.width == 10.0  # Only bz1 is provided


class TestCreateReinforcementLayout:
    """Tests for create_reinforcement_layout function."""

    def test_create_reinforcement_layout_valid_data(self) -> None:
        """Test creating reinforcement layout from valid cross-section data."""
        reinforcement_config = {
            "main_diameter_top": 0.012,
            "main_spacing_top": 0.150,
            "main_diameter_bottom": 0.012,
            "main_spacing_bottom": 0.150,
            "concrete_cover": 0.055,
        }

        cross_section = BridgeCrossSectionData(
            width=1.0,  # Small width for predictable bar count
            height=0.5,
            concrete_material="C30/37",
            reinforcement_material="B500B",
            reinforcement_config=reinforcement_config,
        )

        result = create_reinforcement_layout(cross_section)

        assert isinstance(result, ReinforcementConfig)
        assert len(result.main_bars_top) >= 2  # Minimum 2 bars
        assert len(result.main_bars_bottom) >= 2  # Minimum 2 bars
        assert result.concrete_cover == 0.055

    def test_create_reinforcement_layout_wide_section(self) -> None:
        """Test creating reinforcement layout for wide cross-section."""
        reinforcement_config = {
            "main_diameter_top": 0.012,
            "main_spacing_top": 0.150,
            "main_diameter_bottom": 0.016,
            "main_spacing_bottom": 0.200,
            "concrete_cover": 0.055,
        }

        cross_section = BridgeCrossSectionData(
            width=5.0,  # Wide section
            height=0.8,
            concrete_material="C30/37",
            reinforcement_material="B500B",
            reinforcement_config=reinforcement_config,
        )

        result = create_reinforcement_layout(cross_section)

        # Should have more bars for wider section
        assert len(result.main_bars_top) > 2
        assert len(result.main_bars_bottom) > 2

        # Check bar positions are within section boundaries
        for x, y, diameter in result.main_bars_top:
            assert -cross_section.width / 2 <= x <= cross_section.width / 2
            assert abs(y - (cross_section.height / 2 - reinforcement_config["concrete_cover"] - diameter / 2)) < 0.001

        for x, y, diameter in result.main_bars_bottom:
            assert -cross_section.width / 2 <= x <= cross_section.width / 2
            assert abs(y - (-cross_section.height / 2 + reinforcement_config["concrete_cover"] + diameter / 2)) < 0.001


class TestCreateSimpleIdeaSlabModel:
    """Tests for create_simple_idea_slab_model function."""

    @patch("viktor.external.idea_rcs")
    def test_create_simple_idea_slab_model_success(self, mock_idea_rcs: Mock) -> None:
        """Test creating IDEA slab model successfully."""
        # Setup mocks
        mock_model = Mock()
        mock_idea_rcs.Model.return_value = mock_model
        mock_idea_rcs.ConcreteMaterial.C30_37 = "C30_37"
        mock_idea_rcs.ReinforcementMaterial.B_500B = "B_500B"
        mock_idea_rcs.RectSection = Mock()
        mock_idea_rcs.LoadingSLS = Mock()
        mock_idea_rcs.LoadingULS = Mock()
        mock_idea_rcs.ResultOfInternalForces = Mock()

        mock_cs_mat = Mock()
        mock_mat_reinf = Mock()
        mock_slab = Mock()
        mock_cross_section = Mock()

        mock_model.create_concrete_material.return_value = mock_cs_mat
        mock_model.create_reinforcement_material.return_value = mock_mat_reinf
        mock_model.create_one_way_slab.return_value = mock_slab
        mock_idea_rcs.RectSection.return_value = mock_cross_section

        reinforcement_config = {
            "main_diameter_top": 0.012,
            "main_spacing_top": 0.150,
            "main_diameter_bottom": 0.012,
            "main_spacing_bottom": 0.150,
            "concrete_cover": 0.055,
        }

        cross_section_data = BridgeCrossSectionData(
            width=2.0, height=0.6, concrete_material="C30/37", reinforcement_material="B500B", reinforcement_config=reinforcement_config
        )

        result = create_simple_idea_slab_model(cross_section_data)

        # Verify model creation calls
        mock_idea_rcs.Model.assert_called_once()
        mock_model.create_concrete_material.assert_called_once()
        mock_model.create_reinforcement_material.assert_called_once()
        mock_model.create_one_way_slab.assert_called_once()
        mock_slab.create_bar.assert_called()  # Should be called multiple times for bars
        mock_slab.create_extreme.assert_called_once()

        assert result == mock_model

    def test_create_simple_idea_slab_model_import_error(self) -> None:
        """Test creating IDEA slab model with import error."""
        reinforcement_config = {
            "main_diameter_top": 0.012,
            "main_spacing_top": 0.150,
            "main_diameter_bottom": 0.012,
            "main_spacing_bottom": 0.150,
            "concrete_cover": 0.055,
        }

        cross_section_data = BridgeCrossSectionData(
            width=2.0, height=0.6, concrete_material="C30/37", reinforcement_material="B500B", reinforcement_config=reinforcement_config
        )

        with (
            patch("viktor.external.idea_rcs", side_effect=ImportError("VIKTOR module not available")),
            pytest.raises(ImportError, match="VIKTOR IDEA StatiCa module required"),
        ):
            create_simple_idea_slab_model(cross_section_data)


class TestMaterialEnums:
    """Tests for material enum conversion functions."""

    @patch("viktor.external.idea_rcs")
    def test_get_concrete_material_enum_known_material(self, mock_idea_rcs: Mock) -> None:
        """Test getting concrete material enum for known material."""
        mock_idea_rcs.ConcreteMaterial.C30_37 = "C30_37_ENUM"

        result = _get_concrete_material_enum("C30/37")

        assert result == "C30_37_ENUM"

    @patch("viktor.external.idea_rcs")
    def test_get_concrete_material_enum_unknown_material(self, mock_idea_rcs: Mock) -> None:
        """Test getting concrete material enum for unknown material."""
        mock_idea_rcs.ConcreteMaterial.C30_37 = "C30_37_ENUM"

        result = _get_concrete_material_enum("UNKNOWN")

        assert result == "C30_37_ENUM"  # Should return default

    @patch("viktor.external.idea_rcs")
    def test_get_reinforcement_material_enum_known_material(self, mock_idea_rcs: Mock) -> None:
        """Test getting reinforcement material enum for known material."""
        mock_idea_rcs.ReinforcementMaterial.B_500B = "B500B_ENUM"

        result = _get_reinforcement_material_enum("B500B")

        assert result == "B500B_ENUM"

    @patch("viktor.external.idea_rcs")
    def test_get_reinforcement_material_enum_unknown_material(self, mock_idea_rcs: Mock) -> None:
        """Test getting reinforcement material enum for unknown material."""
        mock_idea_rcs.ReinforcementMaterial.B_500B = "B500B_ENUM"

        result = _get_reinforcement_material_enum("UNKNOWN")

        assert result == "B500B_ENUM"  # Should return default

    def test_material_enum_import_error(self) -> None:
        """Test material enum functions with import error."""
        with patch("viktor.external.idea_rcs", side_effect=ImportError("VIKTOR module not available")):
            with pytest.raises(ImportError, match="VIKTOR IDEA StatiCa module required"):
                _get_concrete_material_enum("C30/37")

            with pytest.raises(ImportError, match="VIKTOR IDEA StatiCa module required"):
                _get_reinforcement_material_enum("B500B")


class TestCreateBridgeIdeaModel:
    """Tests for create_bridge_idea_model function."""

    @patch("src.integrations.idea_interface.create_simple_idea_slab_model")
    @patch("src.integrations.idea_interface.extract_cross_section_from_params")
    def test_create_bridge_idea_model_success(self, mock_extract: Mock, mock_create_model: Mock) -> None:
        """Test creating bridge IDEA model successfully."""
        bridge_segments_params = [{"bz1": 10.0, "bz2": 5.0, "bz3": 15.0, "dz": 2.0, "dz_2": 3.0, "l": 0}]

        mock_cross_section_data = Mock()
        mock_model = Mock()
        mock_extract.return_value = mock_cross_section_data
        mock_create_model.return_value = mock_model

        result = create_bridge_idea_model(bridge_segments_params)

        mock_extract.assert_called_once_with(bridge_segments_params)
        mock_create_model.assert_called_once_with(mock_cross_section_data)
        assert result == mock_model

    @patch("src.integrations.idea_interface.extract_cross_section_from_params")
    def test_create_bridge_idea_model_invalid_params(self, mock_extract: Mock) -> None:
        """Test creating bridge IDEA model with invalid parameters."""
        bridge_segments_params: list[dict[str, float]] = []
        mock_extract.side_effect = ValueError("No bridge segments provided")

        with pytest.raises(ValueError, match="No bridge segments provided"):
            create_bridge_idea_model(bridge_segments_params)


class TestRunIdeaAnalysis:
    """Tests for run_idea_analysis function."""

    @patch("viktor.external.idea_rcs")
    def test_run_idea_analysis_success(self, mock_idea_rcs: Mock) -> None:
        """Test running IDEA analysis successfully."""
        # Setup mocks
        mock_model = Mock()
        mock_input_file = Mock()
        mock_analysis = Mock()
        mock_output_file = Mock()

        mock_model.generate_xml_input.return_value = mock_input_file
        mock_idea_rcs.IdeaRcsAnalysis.return_value = mock_analysis
        mock_analysis.get_output_file.return_value = mock_output_file

        result = run_idea_analysis(mock_model, timeout=60)

        mock_model.generate_xml_input.assert_called_once()
        mock_idea_rcs.IdeaRcsAnalysis.assert_called_once_with(mock_input_file)
        mock_analysis.execute.assert_called_once_with(60)
        mock_analysis.get_output_file.assert_called_once()
        assert result == mock_output_file

    def test_run_idea_analysis_import_error(self) -> None:
        """Test running IDEA analysis with import error."""
        with patch("viktor.external.idea_rcs", side_effect=ImportError("VIKTOR module not available")):
            mock_model = Mock()

            with pytest.raises(ImportError, match="VIKTOR IDEA StatiCa module required"):
                run_idea_analysis(mock_model)

    @patch("viktor.external.idea_rcs")
    def test_run_idea_analysis_execution_error(self, mock_idea_rcs: Mock) -> None:
        """Test running IDEA analysis with execution error."""
        # Setup mocks
        mock_model = Mock()
        mock_input_file = Mock()
        mock_analysis = Mock()

        mock_model.generate_xml_input.return_value = mock_input_file
        mock_idea_rcs.IdeaRcsAnalysis.return_value = mock_analysis
        mock_analysis.execute.side_effect = RuntimeError("Analysis failed")

        with pytest.raises(RuntimeError, match="IDEA analysis failed: Analysis failed"):
            run_idea_analysis(mock_model)


class TestIntegrationScenarios:
    """Integration tests for complete scenarios."""

    @patch("viktor.external.idea_rcs")
    def test_full_bridge_to_idea_workflow(self, mock_idea_rcs: Mock) -> None:
        """Test complete workflow from bridge parameters to IDEA analysis."""
        # Setup mocks
        mock_model = Mock()
        mock_idea_rcs.Model.return_value = mock_model
        mock_idea_rcs.ConcreteMaterial.C30_37 = "C30_37"
        mock_idea_rcs.ReinforcementMaterial.B_500B = "B_500B"
        mock_idea_rcs.RectSection = Mock()
        mock_idea_rcs.LoadingSLS = Mock()
        mock_idea_rcs.LoadingULS = Mock()
        mock_idea_rcs.ResultOfInternalForces = Mock()

        mock_cs_mat = Mock()
        mock_mat_reinf = Mock()
        mock_slab = Mock()
        mock_input_file = Mock()
        mock_analysis = Mock()
        mock_output_file = Mock()

        mock_model.create_concrete_material.return_value = mock_cs_mat
        mock_model.create_reinforcement_material.return_value = mock_mat_reinf
        mock_model.create_one_way_slab.return_value = mock_slab
        mock_model.generate_xml_input.return_value = mock_input_file
        mock_idea_rcs.IdeaRcsAnalysis.return_value = mock_analysis
        mock_analysis.get_output_file.return_value = mock_output_file

        # Test data
        bridge_segments_params = [{"bz1": 10.0, "bz2": 5.0, "bz3": 15.0, "dz": 2.0, "dz_2": 3.0, "l": 0}]

        # Execute workflow
        model = create_bridge_idea_model(bridge_segments_params)
        assert model is not None

        output = run_idea_analysis(model, timeout=120)
        assert output == mock_output_file

        # Verify calls
        mock_idea_rcs.Model.assert_called()
        mock_model.generate_xml_input.assert_called()
        mock_analysis.execute.assert_called_with(120)

    def test_environment_awareness(self) -> None:
        """Test that functions handle missing VIKTOR environment gracefully."""
        bridge_segments_params = [{"bz1": 10.0, "bz2": 5.0, "bz3": 15.0, "dz": 2.0, "dz_2": 3.0, "l": 0}]

        # Should work without VIKTOR SDK for parameter extraction
        cross_section_data = extract_cross_section_from_params(bridge_segments_params)
        assert cross_section_data.width == 30.0

        reinforcement = create_reinforcement_layout(cross_section_data)
        assert len(reinforcement.main_bars_top) >= 2

        # IDEA-specific functions should raise ImportError
        with pytest.raises(ImportError):
            create_simple_idea_slab_model(cross_section_data)

        with pytest.raises(ImportError):
            _get_concrete_material_enum("C30/37")

        with pytest.raises(ImportError):
            _get_reinforcement_material_enum("B500B")

        with pytest.raises(ImportError):
            run_idea_analysis(Mock())


if __name__ == "__main__":
    pytest.main([__file__])
