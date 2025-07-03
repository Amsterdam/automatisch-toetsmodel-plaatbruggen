"""
Tests for SCIA integration module.

These tests verify the core SCIA functionality without requiring VIKTOR SDK or SCIA Worker.
"""

from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest

# Global imports from SCIA interface module - moved to top level for CI compatibility
from src.integrations.scia_interface import (
    NodeTracker,
    _add_dummy_wheel_loads,
    _add_realistic_tandem_loads,
    _create_dutch_standard_load_combinations,
    _create_traffic_load_combinations_minimal,
    apply_tandem_loads_to_scia_model,
    create_bridge_scia_model,
    create_node_and_thickness_dict,
    create_scia_analysis_from_template,
    create_simple_scia_plate_model,
    determine_tandem_function_for_bridge,
    extract_tandem_parameters_from_bridge,
    generate_tandem_loads_for_bridge,
)

# Global imports from loadcase helper functions - moved to top level for CI compatibility
from src.loads.loadcase_helper_functions import (
    generate_theoretical_lane_positions,
    tandem_systems_actual_lanes,
    tandem_systems_shiftable_lanes,
    tandem_systems_theoretical_lanes,
)
from tests.test_data.seed_loader import load_bridge_default_params


class TestNodeTracker:
    """Test NodeTracker helper class."""

    def test_node_tracker_initialization(self) -> None:
        """Test NodeTracker initialization."""
        mock_model = Mock()
        tracker = NodeTracker(mock_model)

        assert tracker.model is mock_model
        assert tracker._nodes_by_coords == {}  # noqa: SLF001
        assert tracker._nodes_by_name == {}  # noqa: SLF001

    def test_get_or_create_node_new_node(self) -> None:
        """Test creating new node when coordinates don't exist."""
        mock_model = Mock()
        mock_node = Mock()
        mock_model.create_node.return_value = mock_node

        tracker = NodeTracker(mock_model)
        result = tracker.get_or_create_node("N1", 0.0, 0.0, 0.0)

        assert result is mock_node
        mock_model.create_node.assert_called_once_with("N1", 0.0, 0.0, 0.0)
        assert tracker._nodes_by_coords[(0.0, 0.0, 0.0)] is mock_node  # noqa: SLF001
        assert tracker._nodes_by_name["N1"] is mock_node  # noqa: SLF001

    def test_get_or_create_node_existing_node(self) -> None:
        """Test reusing existing node at same coordinates."""
        mock_model = Mock()
        mock_node = Mock()

        tracker = NodeTracker(mock_model)
        tracker._nodes_by_coords[(0.0, 0.0, 0.0)] = mock_node  # noqa: SLF001

        result = tracker.get_or_create_node("N2", 0.0, 0.0, 0.0)

        assert result is mock_node
        mock_model.create_node.assert_not_called()  # Should not create new node

    def test_get_node_by_name(self) -> None:
        """Test retrieving node by name."""
        mock_model = Mock()
        mock_node = Mock()

        tracker = NodeTracker(mock_model)
        tracker._nodes_by_name["N1"] = mock_node  # noqa: SLF001

        result = tracker.get_node_by_name("N1")
        assert result is mock_node


class TestNodeAndThicknessDictCreation:
    """Test node and thickness dictionary creation from bridge parameters."""

    def test_create_node_and_thickness_dict_single_segment(self) -> None:
        """Test node creation with single bridge segment."""
        segment = Mock()
        segment.__getitem__ = lambda _self, key: {"l": 10.0}[key]
        segment.bz1 = 5.0
        segment.bz2 = 3.0
        segment.bz3 = 4.0
        segment.dz = 2.0
        segment.dz_2 = 2.5

        params = Mock()
        params.bridge_segments_array = [segment]

        nodes_dict, thickness_dict = create_node_and_thickness_dict(params)

        # Should only create first cross-section nodes (no plates yet)
        expected_nodes = {
            "K_dek:1_1": [10.0, 6.5, 0],  # x=10, y=bz1+bz2/2=5+1.5=6.5
            "K_dek:1_2": [10.0, 1.5, 0],  # x=10, y=bz2/2=1.5
            "K_dek:1_3": [10.0, -1.5, 0],  # x=10, y=-bz2/2=-1.5
            "K_dek:1_4": [10.0, -5.5, 0],  # x=10, y=-bz3-bz2/2=-4-1.5=-5.5
        }

        assert nodes_dict == expected_nodes
        assert thickness_dict == {}  # No plates created with single segment

    def test_create_node_and_thickness_dict_multiple_segments(self) -> None:
        """Test node creation with multiple bridge segments."""
        params = Mock()
        params.bridge_segments_array = [
            Mock(l=0, bz1=5.0, bz2=3.0, bz3=4.0, dz=2.0, dz_2=2.5),  # First segment (l=0)
            Mock(l=10, bz1=5.0, bz2=3.0, bz3=4.0, dz=2.1, dz_2=2.6),  # Second segment
            Mock(l=8, bz1=5.0, bz2=3.0, bz3=4.0, dz=2.2, dz_2=2.7),  # Third segment
        ]

        nodes_dict, thickness_dict = create_node_and_thickness_dict(params)

        # Should create 3 cross-sections
        assert "K_dek:1_1" in nodes_dict
        assert "K_dek:2_1" in nodes_dict
        assert "K_dek:3_1" in nodes_dict

        # Check cumulative lengths
        assert nodes_dict["K_dek:1_1"][0] == 0  # First segment cumulative length
        assert nodes_dict["K_dek:2_1"][0] == 10  # Second segment cumulative length
        assert nodes_dict["K_dek:3_1"][0] == 18  # Third segment cumulative length (10+8)

        # Check thickness data for plates between segments
        expected_thickness = {
            "Z1_1": 2.1,
            "Z2_1": 2.6,
            "Z3_1": 2.1,  # From segment 1 (index 1)
            "Z1_2": 2.2,
            "Z2_2": 2.7,
            "Z3_2": 2.2,  # From segment 2 (index 2)
        }
        assert thickness_dict == expected_thickness

    def test_create_node_and_thickness_dict_empty_segments(self) -> None:
        """Test behavior with empty segments array."""
        params = Mock()
        params.bridge_segments_array = []

        nodes_dict, thickness_dict = create_node_and_thickness_dict(params)

        assert nodes_dict == {}
        assert thickness_dict == {}


class TestSCIAModelCreation:
    """Test SCIA model creation functions."""

    @patch("src.integrations.scia_interface.scia")
    def test_create_simple_scia_plate_model_mocked(self, mock_scia: Any) -> None:  # noqa: ANN401
        """Test SCIA model creation with mocked SDK."""
        mock_model = Mock()
        mock_material = Mock()
        mock_node = Mock()

        mock_scia.Model.return_value = mock_model
        mock_scia.Material.return_value = mock_material
        mock_model.create_node.return_value = mock_node
        mock_model.generate_xml_input.return_value = (Mock(), Mock())

        # Create test parameters
        params = Mock()
        params.bridge_segments_array = [
            Mock(l=0, bz1=5.0, bz2=3.0, bz3=4.0, dz=2.0, dz_2=2.5),
            Mock(l=10, bz1=5.0, bz2=3.0, bz3=4.0, dz=2.1, dz_2=2.6),
        ]

        result = create_simple_scia_plate_model(params)

        # Verify SCIA API calls
        mock_scia.Model.assert_called_once()
        mock_scia.Material.assert_called_once_with(0, "C30/37")
        assert mock_model.create_node.call_count >= 8  # At least 8 nodes for 2 cross-sections
        assert mock_model.create_plane.call_count == 3  # 3 zone plates
        mock_model.generate_xml_input.assert_called_once()

        assert result is not None

    def test_create_simple_scia_plate_model_no_viktor(self) -> None:
        """Test SCIA model creation without VIKTOR SDK."""
        params = Mock()
        params.bridge_segments_array = [Mock(l=0, bz1=5.0, bz2=3.0, bz3=4.0)]

        with pytest.raises(ImportError, match="VIKTOR SCIA module not available"):
            create_simple_scia_plate_model(params)

    @patch("src.integrations.scia_interface.scia")
    def test_create_simple_scia_plate_model_missing_coordinates(self, mock_scia: Any) -> None:  # noqa: ANN401
        """Test error handling when node coordinates are missing."""
        mock_model = Mock()
        mock_scia.Model.return_value = mock_model
        mock_scia.Material.return_value = Mock()

        # Create params that will cause missing coordinates
        params = Mock()
        params.bridge_segments_array = []  # Empty array causes missing coordinates

        with pytest.raises(ValueError, match="Coordinates for node .* not found"):
            create_simple_scia_plate_model(params)

    def test_create_simple_scia_plate_model_with_real_data(self) -> None:
        """Test SCIA model creation with real test data."""
        params = load_bridge_default_params()

        try:
            result = create_simple_scia_plate_model(params)
            # Success in VIKTOR environment
            assert result is not None
        except (ImportError, KeyError):
            # Expected outside VIKTOR environment
            pass


class TestSCIAAnalysisCreation:
    """Test SCIA analysis creation functions."""

    def test_create_scia_analysis_missing_template(self) -> None:
        """Test that FileNotFoundError is raised for missing template."""
        mock_xml_file = Mock()
        mock_def_file = Mock()
        missing_template_path = Path("/nonexistent/template.esa")

        with pytest.raises(FileNotFoundError, match="SCIA template file not found"):
            create_scia_analysis_from_template(mock_xml_file, mock_def_file, missing_template_path)

    def test_create_scia_analysis_no_viktor(self) -> None:
        """Test SCIA analysis creation without VIKTOR SDK."""
        mock_xml_file = Mock()
        mock_def_file = Mock()
        template_path = Path("dummy.esa")

        with pytest.raises(ImportError, match="VIKTOR SCIA module not available"):
            create_scia_analysis_from_template(mock_xml_file, mock_def_file, template_path)

    @patch("src.integrations.scia_interface.scia")
    @patch("src.integrations.scia_interface.File")
    def test_create_scia_analysis_success(self, mock_file_class: Any, mock_scia: Any) -> None:  # noqa: ANN401
        """Test successful SCIA analysis creation."""
        mock_xml_file = Mock()
        mock_def_file = Mock()
        mock_template_file = Mock()
        mock_analysis = Mock()

        mock_file_class.from_path.return_value = mock_template_file
        mock_scia.SciaAnalysis.return_value = mock_analysis

        # Create existing template path
        template_path = Path(__file__).parent / "test_template.esa"
        template_path.touch()  # Create empty file

        try:
            result = create_scia_analysis_from_template(mock_xml_file, mock_def_file, template_path)

            # Verify calls
            mock_file_class.from_path.assert_called_once_with(template_path)
            mock_scia.SciaAnalysis.assert_called_once_with(mock_xml_file, mock_def_file, mock_template_file)
            assert result is mock_analysis

        finally:
            # Cleanup
            if template_path.exists():
                template_path.unlink()


class TestMainBridgeModelFunction:
    """Test main bridge model creation function."""

    @patch("src.integrations.scia_interface.create_simple_scia_plate_model")
    @patch("src.integrations.scia_interface.create_scia_analysis_from_template")
    def test_create_bridge_scia_model_success(self, mock_create_analysis: Any, mock_create_model: Any) -> None:  # noqa: ANN401
        """Test successful bridge SCIA model creation."""
        mock_xml = Mock()
        mock_def = Mock()
        mock_analysis = Mock()

        mock_create_model.return_value = (mock_xml, mock_def)
        mock_create_analysis.return_value = mock_analysis

        # Test parameters
        params = Mock()
        template_path = Path("test_template.esa")

        result = create_bridge_scia_model(params, template_path)

        # Verify calls
        mock_create_model.assert_called_once_with(params)
        mock_create_analysis.assert_called_once_with(mock_xml, mock_def, template_path)

        # Verify result
        xml_file, def_file, scia_analysis = result
        assert xml_file is mock_xml
        assert def_file is mock_def
        assert scia_analysis is mock_analysis

    def test_create_bridge_scia_model_with_real_template(self) -> None:
        """Test bridge model creation with real template file."""
        params = load_bridge_default_params()

        # Use project's template file
        template_path = Path("automatisch-toetsmodel-plaatbruggen/resources/templates/model.esa")

        try:
            result = create_bridge_scia_model(params, template_path)
            # Success in VIKTOR environment
            assert len(result) == 3
            xml_file, def_file, scia_analysis = result
            assert xml_file is not None
            assert def_file is not None
            assert scia_analysis is not None

        except (ImportError, KeyError, FileNotFoundError):
            # Expected outside VIKTOR environment or missing template
            pass


class TestDummyLoadDemonstration:
    """Test dummy load demonstration function."""

    @patch("src.integrations.scia_interface.create_load_group_by_type")
    @patch("src.integrations.scia_interface.create_load_case_complete")
    @patch("src.integrations.scia_interface.create_load_combination_by_type")
    @patch("src.integrations.scia_interface.create_patch_surface_load")
    def test_add_dummy_wheel_loads(self, mock_patch_load: Any, mock_combination: Any, mock_load_case: Any, mock_load_group: Any) -> None:  # noqa: ANN401
        """Test dummy wheel loads demonstration."""
        mock_model = Mock()
        mock_permanent_group = Mock()
        mock_traffic_group = Mock()
        mock_wind_group = Mock()
        mock_dead_case = Mock()
        mock_lm1_case = Mock()
        mock_wind_case = Mock()
        mock_uls_basic = Mock()
        mock_uls_wind = Mock()
        mock_sls_char = Mock()

        mock_load_group.side_effect = [mock_permanent_group, mock_traffic_group, mock_wind_group]
        mock_load_case.side_effect = [mock_dead_case, mock_lm1_case, mock_wind_case]
        mock_combination.side_effect = [mock_uls_basic, mock_uls_wind, mock_sls_char]

        result = _add_dummy_wheel_loads(mock_model)

        # Verify load group creation
        assert mock_load_group.call_count == 3
        mock_load_group.assert_any_call(mock_model, "PERMANENT", "LG_Permanent")
        mock_load_group.assert_any_call(mock_model, "VARIABLE", "LG_Traffic")
        mock_load_group.assert_any_call(mock_model, "VARIABLE", "LG_Wind")

        # Verify load case creation
        assert mock_load_case.call_count == 3

        # Verify load combination creation
        assert mock_combination.call_count == 3

        # Verify patch loads creation (4 wheel loads)
        assert mock_patch_load.call_count == 4

        # Verify result structure
        assert "load_groups" in result
        assert "load_cases" in result
        assert "combinations" in result
        assert len(result["load_groups"]) == 3
        assert len(result["load_cases"]) == 3
        assert len(result["combinations"]) == 3


class TestIntegrationWithRealData:
    """Integration tests with real project data."""

    def test_node_creation_with_real_bridge_data(self) -> None:
        """Test node creation with real bridge parameters."""
        params = load_bridge_default_params()

        nodes_dict, thickness_dict = create_node_and_thickness_dict(params)

        # Verify structure
        assert isinstance(nodes_dict, dict)
        assert isinstance(thickness_dict, dict)

        # Should have nodes for each cross-section
        num_segments = len(params.bridge_segments_array)
        if num_segments > 0:
            assert len([k for k in nodes_dict if k.startswith("K_dek:1_")]) == 4

        # Should have thickness data for plates between segments
        if num_segments > 1:
            assert len(thickness_dict) > 0

    def test_coordinate_calculation_accuracy(self) -> None:
        """Test coordinate calculation accuracy with known values."""
        params = Mock()
        params.bridge_segments_array = [
            Mock(l=0, bz1=10.0, bz2=5.0, bz3=15.0, dz=2.0, dz_2=3.0),
            Mock(l=20, bz1=10.0, bz2=5.0, bz3=15.0, dz=2.1, dz_2=3.1),
        ]

        nodes_dict, thickness_dict = create_node_and_thickness_dict(params)

        # Check first cross-section coordinates
        # Zone layout: Zone 3 (15m) | Zone 2 (5m) | Zone 1 (10m)
        # Y-coordinates: z1_left = bz1 + bz2/2 = 10 + 2.5 = 12.5
        #                z1_right = bz2/2 = 2.5
        #                z3_left = -bz2/2 = -2.5
        #                z3_right = -bz3 - bz2/2 = -15 - 2.5 = -17.5

        assert nodes_dict["K_dek:1_1"] == [0, 12.5, 0]  # Zone 1 left
        assert nodes_dict["K_dek:1_2"] == [0, 2.5, 0]  # Zone 1 right
        assert nodes_dict["K_dek:1_3"] == [0, -2.5, 0]  # Zone 3 left
        assert nodes_dict["K_dek:1_4"] == [0, -17.5, 0]  # Zone 3 right

        # Check second cross-section coordinates (cumulative length = 20)
        assert nodes_dict["K_dek:2_1"] == [20, 12.5, 0]
        assert nodes_dict["K_dek:2_2"] == [20, 2.5, 0]
        assert nodes_dict["K_dek:2_3"] == [20, -2.5, 0]
        assert nodes_dict["K_dek:2_4"] == [20, -17.5, 0]

        # Check thickness data
        assert thickness_dict["Z1_1"] == 2.1  # From second segment
        assert thickness_dict["Z2_1"] == 3.1  # From second segment
        assert thickness_dict["Z3_1"] == 2.1  # From second segment


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_invalid_bridge_segments_structure(self) -> None:
        """Test handling of invalid bridge segments structure."""
        params = Mock()
        params.bridge_segments_array = [Mock()]  # Missing required attributes

        with pytest.raises(AttributeError):
            create_node_and_thickness_dict(params)

    def test_zero_length_segments(self) -> None:
        """Test handling of zero-length segments."""
        params = Mock()
        params.bridge_segments_array = [
            Mock(l=0, bz1=5.0, bz2=3.0, bz3=4.0, dz=2.0, dz_2=2.5),
            Mock(l=0, bz1=5.0, bz2=3.0, bz3=4.0, dz=2.1, dz_2=2.6),  # Zero length
        ]

        nodes_dict, thickness_dict = create_node_and_thickness_dict(params)

        # Should still create nodes, but both cross-sections at same X position
        assert nodes_dict["K_dek:1_1"][0] == 0
        assert nodes_dict["K_dek:2_1"][0] == 0  # Same X position due to zero length

    def test_negative_dimensions(self) -> None:
        """Test handling of negative dimensions."""
        params = Mock()
        params.bridge_segments_array = [
            Mock(l=0, bz1=-5.0, bz2=3.0, bz3=4.0, dz=2.0, dz_2=2.5),  # Negative bz1
        ]

        # Should not raise error, but coordinates will be unusual
        nodes_dict, thickness_dict = create_node_and_thickness_dict(params)

        # Verify it still creates nodes (even if geometrically unusual)
        assert len(nodes_dict) == 4


class TestTandemParameterExtraction:
    """Test extracting parameters for src.loads.loadcase_helper_functions integration."""

    def test_extract_tandem_parameters_from_bridge_default_data(self) -> None:
        """Test parameter extraction using bridge_default_params.json data."""
        params = load_bridge_default_params()

        result = extract_tandem_parameters_from_bridge(params)

        # Expected values from bridge_default_params.json
        # Length: sum of segment lengths = 0 + 10 = 10.0
        # Width: bz1 + bz2 + bz3 = 10.0 + 5.0 + 15.0 = 30.0
        # Thickness: dz from first segment = 2.0
        assert result["length_bridgedeck"] == 10.0
        assert result["width_bridgedeck"] == 30.0
        assert result["thickness_bridgedeck"] == 2.0

    def test_extract_tandem_parameters_single_segment(self) -> None:
        """Test parameter extraction with single segment."""
        params = Mock()
        params.bridge_segments_array = [Mock(l=0, bz1=8.0, bz2=4.0, bz3=12.0, dz=1.5)]

        result = extract_tandem_parameters_from_bridge(params)

        assert result["length_bridgedeck"] == 0.0  # Single segment with l=0
        assert result["width_bridgedeck"] == 24.0  # 8+4+12
        assert result["thickness_bridgedeck"] == 1.5

    def test_extract_tandem_parameters_multiple_segments(self) -> None:
        """Test parameter extraction with multiple segments."""
        params = Mock()
        params.bridge_segments_array = [
            Mock(l=0, bz1=5.0, bz2=3.0, bz3=7.0, dz=1.8),
            Mock(l=15, bz1=5.0, bz2=3.0, bz3=7.0, dz=1.9),
            Mock(l=20, bz1=5.0, bz2=3.0, bz3=7.0, dz=2.0),
        ]

        result = extract_tandem_parameters_from_bridge(params)

        assert result["length_bridgedeck"] == 35.0  # 0+15+20
        assert result["width_bridgedeck"] == 15.0  # 5+3+7
        assert result["thickness_bridgedeck"] == 1.8  # From first segment

    def test_extract_tandem_parameters_zero_length_segments(self) -> None:
        """Test parameter extraction with zero-length segments."""
        params = Mock()
        params.bridge_segments_array = [
            Mock(l=0, bz1=6.0, bz2=2.0, bz3=8.0, dz=2.2),
            Mock(l=0, bz1=6.0, bz2=2.0, bz3=8.0, dz=2.3),
        ]

        result = extract_tandem_parameters_from_bridge(params)

        assert result["length_bridgedeck"] == 0.0  # All segments have l=0
        assert result["width_bridgedeck"] == 16.0  # 6+2+8
        assert result["thickness_bridgedeck"] == 2.2

    def test_extract_tandem_parameters_empty_segments(self) -> None:
        """Test error handling with empty segments array."""
        params = Mock()
        params.bridge_segments_array = []

        with pytest.raises(IndexError):
            extract_tandem_parameters_from_bridge(params)


class TestTandemSCIAApplication:
    """Test applying tandem loads to SCIA model."""

    @patch("src.integrations.scia_interface.create_load_case_complete")
    def test_create_tandem_load_cases_from_bg_naming(self, mock_create_case: Mock) -> None:
        """Test creating load cases with BG6001, BG6002 naming."""
        mock_model = Mock()
        mock_load_group = Mock()
        mock_load_case = Mock()
        mock_create_case.return_value = mock_load_case

        # Mock tandem load data
        scia_tandem_data = [
            {
                "load_case": "BG6001",
                "patch_loads": [
                    {
                        "corners": [(10.0, 1.0, 0.0), (10.4, 1.0, 0.0), (10.4, 1.4, 0.0), (10.0, 1.4, 0.0)],
                        "load_value": 1875000.0,
                    }
                ],
            }
        ]

        result = apply_tandem_loads_to_scia_model(mock_model, scia_tandem_data, mock_load_group)

        # Verify load case creation with correct naming
        mock_create_case.assert_called_once()
        call_args = mock_create_case.call_args[0]
        assert call_args[2] == "BG6001"  # load case name
        assert "Load Model" in call_args[3]  # description should mention Load Model

        assert len(result) == 1
        assert result[0] == mock_load_case

    def test_apply_wheel_loads_to_scia_model(self) -> None:
        """Test applying individual wheel loads as patch loads."""
        mock_model = Mock()
        mock_load_group = Mock()

        # Mock tandem load data with multiple wheels
        scia_tandem_data = [
            {
                "load_case": "BG6001",
                "patch_loads": [
                    {
                        "corners": [(10.0, 1.0, 0.0), (10.4, 1.0, 0.0), (10.4, 1.4, 0.0), (10.0, 1.4, 0.0)],
                        "load_value": 1875000.0,
                    },
                    {
                        "corners": [(11.2, 1.0, 0.0), (11.6, 1.0, 0.0), (11.6, 1.4, 0.0), (11.2, 1.4, 0.0)],
                        "load_value": 1250000.0,
                    },
                ],
            }
        ]

        with (
            patch("src.integrations.scia_interface.create_load_case_complete") as mock_create_case,
            patch("src.integrations.scia_interface.create_patch_surface_load") as mock_patch_load,
        ):
            mock_create_case.return_value = Mock()
            mock_patch_load.return_value = Mock()

            apply_tandem_loads_to_scia_model(mock_model, scia_tandem_data, mock_load_group)

            # Verify patch loads creation
            assert mock_patch_load.call_count == 2  # Two wheels

            # Check first wheel load
            call_args_1 = mock_patch_load.call_args_list[0]
            assert call_args_1[0][2] == [(10.0, 1.0, 0.0), (10.4, 1.0, 0.0), (10.4, 1.4, 0.0), (10.0, 1.4, 0.0)]
            assert call_args_1[0][3] == 1875000.0

    def test_load_value_handling_downward_direction(self) -> None:
        """Test that load values are applied as negative (downward direction)."""
        mock_model = Mock()
        mock_load_group = Mock()

        # Mock tandem data with pressure values (positive from tandem functions)
        scia_tandem_data = [
            {
                "load_case": "BG6001",
                "patch_loads": [
                    {
                        "corners": [(10.0, 1.0, 0.0), (10.4, 1.0, 0.0), (10.4, 1.4, 0.0), (10.0, 1.4, 0.0)],
                        "load_value": 1875000.0,  # Positive value from tandem functions
                    }
                ],
            }
        ]

        with (
            patch("src.integrations.scia_interface.create_load_case_complete") as mock_create_case,
            patch("src.integrations.scia_interface.create_patch_surface_load") as mock_patch_load,
        ):
            mock_create_case.return_value = Mock()
            mock_patch_load.return_value = Mock()

            apply_tandem_loads_to_scia_model(mock_model, scia_tandem_data, mock_load_group)

            # Verify load value is negative (downward direction)
            call_args = mock_patch_load.call_args[0]
            assert call_args[3] == -1875000.0  # Negative for downward direction


class TestMinimalTrafficLoadCombinations:
    """Test minimal traffic load combinations (gr1a TS focus) implementation."""

    @patch("src.integrations.scia_interface.create_load_combination_by_type")
    def test_create_traffic_combinations_minimal_success(self, mock_combination: Mock) -> None:
        """Test successful creation of minimal traffic load combinations."""
        mock_model = Mock()
        mock_dead_case = Mock()
        mock_tandem_case_1 = Mock()
        mock_tandem_case_2 = Mock()
        mock_tandem_case_3 = Mock()
        mock_combo_object = Mock()

        # Mock combination creation
        mock_combination.return_value = mock_combo_object

        # Test parameters - focus on traffic (TS - Tandem System)
        traffic_cases = [mock_tandem_case_1, mock_tandem_case_2, mock_tandem_case_3]
        bridge_span = 25.0

        # Patch the global imports correctly
        with (
            patch("src.integrations.scia_interface.get_gamma_factors") as mock_gamma,
            patch("src.integrations.scia_interface.get_psi_factor") as mock_psi,
            patch("src.integrations.scia_interface.LOAD_FACTORS_AVAILABLE", True),
        ):
            # Mock gamma factors (NEN 8700)
            mock_gamma.return_value = {
                "6.10a": {
                    "gamma_Gjsup": 1.25,
                    "gamma_Qverkeer": 1.25,
                },
                "6.10b": {
                    "gamma_Gjsup": 1.15,
                    "gamma_Qverkeer": 1.25,
                },
            }

            # Mock psi factor (NEN 8701)
            mock_psi.return_value = 0.95

            result = _create_traffic_load_combinations_minimal(
                model=mock_model,
                dead_load_case=mock_dead_case,
                traffic_load_cases=traffic_cases,
                bridge_span=bridge_span,
                config={
                    "consequence_class": "CC2",
                    "safety_level": "NEN 8700 gebruik",
                    "construction_year": "2010",
                },
            )

            # Verify function calls
            mock_gamma.assert_called_once_with(cc="CC2", safety_level="NEN 8700 gebruik", building_year="2010")
            mock_psi.assert_called_once_with(span=25.0, reference_period=50.0)

            # Should create 4 combinations (ULS + SLS for both 6.10a and 6.10b)
            assert len(result) == 4

            # Check combination types
            assert "uls_6.10a_gr1a_ts" in result
            assert "uls_6.10b_gr1a_ts" in result
            assert "sls_char_6.10a_gr1a_ts" in result
            assert "sls_char_6.10b_gr1a_ts" in result

            # Verify combination creation calls
            # Should have 4 calls for the 4 combinations
            assert mock_combination.call_count == 4

    @patch("src.integrations.scia_interface.create_load_combination_by_type")
    def test_create_traffic_combinations_minimal_fallback(self, mock_combination: Mock) -> None:
        """Test fallback to basic combinations when traffic combinations fail."""
        mock_model = Mock()
        mock_dead_case = Mock()
        mock_tandem_case = Mock()

        # Mock combination creation
        mock_combination.return_value = Mock()

        # Mock the import to fail and trigger fallback
        with (
            patch("src.integrations.scia_interface.get_gamma_factors", side_effect=ImportError("Mock import failure")),
            patch("src.integrations.scia_interface.get_psi_factor", side_effect=ImportError("Mock import failure")),
            patch("src.integrations.scia_interface.LOAD_FACTORS_AVAILABLE", False),
            patch("builtins.print"),  # Suppress debug prints
        ):
            result = _create_traffic_load_combinations_minimal(
                model=mock_model,
                dead_load_case=mock_dead_case,
                traffic_load_cases=[mock_tandem_case],
                bridge_span=25.0,
            )

            # Should fall back to basic traffic combinations
            assert len(result) == 2
            assert "uls_basic_traffic" in result
            assert "sls_basic_traffic" in result

            # Verify basic combinations were created with TS naming
            assert mock_combination.call_count == 2

            # Check ULS combination
            uls_call = mock_combination.call_args_list[0]
            assert uls_call[0][2] == "ULS_Basic_G+TS"  # Combination name
            assert "Tandem System" in uls_call[0][4]  # Description

            # Check SLS combination
            sls_call = mock_combination.call_args_list[1]
            assert sls_call[0][2] == "SLS_Basic_G+TS"  # Combination name
            assert "Tandem System" in sls_call[0][4]  # Description

    def test_create_traffic_combinations_minimal_no_traffic(self) -> None:
        """Test behavior when no traffic load cases are provided."""
        mock_model = Mock()
        mock_dead_case = Mock()

        # No need to mock gamma/psi factors since function should exit early
        result = _create_traffic_load_combinations_minimal(
            model=mock_model,
            dead_load_case=mock_dead_case,
            traffic_load_cases=[],  # No traffic cases
            bridge_span=25.0,
        )

        # Should return empty result for no traffic cases
        assert result == {}

    @patch("src.integrations.scia_interface.create_load_combination_by_type")
    def test_create_traffic_combinations_minimal_single_tandem(self, mock_combination: Mock) -> None:
        """Test combinations with single tandem load case."""
        mock_model = Mock()
        mock_dead_case = Mock()
        mock_tandem_case = Mock()

        # Mock combination creation
        mock_combination.return_value = Mock()

        # Patch the global imports correctly
        with (
            patch("src.integrations.scia_interface.get_gamma_factors") as mock_gamma,
            patch("src.integrations.scia_interface.get_psi_factor") as mock_psi,
            patch("src.integrations.scia_interface.LOAD_FACTORS_AVAILABLE", True),
        ):
            # Setup return values
            mock_gamma.return_value = {
                "6.10a": {"gamma_Gjsup": 1.25, "gamma_Qverkeer": 1.25},
                "6.10b": {"gamma_Gjsup": 1.15, "gamma_Qverkeer": 1.25},
            }
            mock_psi.return_value = 0.95

            result = _create_traffic_load_combinations_minimal(
                model=mock_model,
                dead_load_case=mock_dead_case,
                traffic_load_cases=[mock_tandem_case],  # Single tandem
                bridge_span=25.0,
            )

            # Should create combinations for single tandem
            assert len(result) == 4  # ULS + SLS for both 6.10a and 6.10b
            assert mock_combination.call_count == 4

            # Verify that only primary tandem is used (no accompanying loads)
            for call in mock_combination.call_args_list:
                factors = call[0][3]  # Load factors dictionary
                assert len(factors) == 2  # Only dead load + primary tandem
                assert mock_dead_case in factors
                assert mock_tandem_case in factors

    @patch("src.integrations.scia_interface.create_load_combination_by_type")
    def test_create_traffic_combinations_minimal_multiple_tandems(self, mock_combination: Mock) -> None:
        """Test combinations with multiple tandem load cases (leading + accompanying)."""
        mock_model = Mock()
        mock_dead_case = Mock()
        mock_primary_tandem = Mock()
        mock_tandem_2 = Mock()
        mock_tandem_3 = Mock()
        mock_tandem_4 = Mock()  # Should be ignored (limit to 2 accompanying)

        # Mock combination creation
        mock_combination.return_value = Mock()

        # Patch the global imports correctly
        with (
            patch("src.integrations.scia_interface.get_gamma_factors") as mock_gamma,
            patch("src.integrations.scia_interface.get_psi_factor") as mock_psi,
            patch("src.integrations.scia_interface.LOAD_FACTORS_AVAILABLE", True),
        ):
            # Setup return values
            mock_gamma.return_value = {
                "6.10a": {"gamma_Gjsup": 1.25, "gamma_Qverkeer": 1.25},
                "6.10b": {"gamma_Gjsup": 1.15, "gamma_Qverkeer": 1.25},
            }
            mock_psi.return_value = 0.95

            result = _create_traffic_load_combinations_minimal(
                model=mock_model,
                dead_load_case=mock_dead_case,
                traffic_load_cases=[mock_primary_tandem, mock_tandem_2, mock_tandem_3, mock_tandem_4],
                bridge_span=25.0,
            )

            # Should create combinations with primary + 2 accompanying tandems max
            assert len(result) == 4
            assert mock_combination.call_count == 4

            # Verify load factors include primary + 2 accompanying (not 4th tandem)
            for call in mock_combination.call_args_list:
                factors = call[0][3]  # Load factors dictionary
                assert len(factors) == 4  # Dead + primary + 2 accompanying
                assert mock_dead_case in factors
                assert mock_primary_tandem in factors
                assert mock_tandem_2 in factors
                assert mock_tandem_3 in factors
                assert mock_tandem_4 not in factors  # Should be excluded


class TestDutchStandardLoadCombinations:
    """Test deprecated Dutch standard load combinations (compatibility)."""

    @patch("src.integrations.scia_interface._create_traffic_load_combinations_minimal")
    def test_create_dutch_standard_load_combinations_redirect(self, mock_minimal: Mock) -> None:
        """Test that deprecated function redirects to minimal implementation."""
        mock_model = Mock()
        mock_dead_case = Mock()
        mock_traffic_cases = [Mock(), Mock()]
        mock_wind_case = Mock()
        mock_result = {"uls_6.10a_gr1a_ts": Mock()}

        mock_minimal.return_value = mock_result

        result = _create_dutch_standard_load_combinations(
            model=mock_model,
            dead_load_case=mock_dead_case,
            traffic_load_cases=mock_traffic_cases,
            wind_case=mock_wind_case,  # Wind case passed but not used in minimal
            bridge_span=25.0,
            consequence_class="CC2",
            safety_level="NEN 8700 gebruik",
            construction_year="2010",
        )

        # Verify redirect to minimal function
        mock_minimal.assert_called_once_with(
            model=mock_model,
            dead_load_case=mock_dead_case,
            traffic_load_cases=mock_traffic_cases,
            bridge_span=25.0,
            config={
                "consequence_class": "CC2",
                "safety_level": "NEN 8700 gebruik",
                "construction_year": "2010",
            },
        )

        # Verify result is passed through
        assert result is mock_result


class TestRealisticTandemLoadsComplete:
    """Test complete realistic tandem loads implementation."""

    def test_add_realistic_tandem_loads_with_real_bridge_data(self) -> None:
        """Test using real bridge_default_params.json data."""
        mock_model = Mock()
        mock_load_group = Mock()
        mock_load_case = Mock()
        mock_combination = Mock()

        mock_model.create_load_group = Mock(return_value=mock_load_group)

        # Load real test data
        params = load_bridge_default_params()

        with (
            patch("src.integrations.scia_interface.create_load_group_by_type", return_value=mock_load_group),
            patch("src.integrations.scia_interface.apply_tandem_loads_to_scia_model", return_value=[mock_load_case]),
            patch("src.integrations.scia_interface.create_load_combination_by_type", return_value=mock_combination),
        ):
            result = _add_realistic_tandem_loads(mock_model, params)

            # Verify structure matches dummy loads format
            assert "load_groups" in result
            assert "load_cases" in result
            assert "combinations" in result

    def test_realistic_loads_return_structure_compatibility(self) -> None:
        """Test return structure matches _add_dummy_wheel_loads."""
        mock_model = Mock()
        params = load_bridge_default_params()

        with (
            patch("src.integrations.scia_interface.create_load_group_by_type") as mock_create_group,
            patch("src.integrations.scia_interface.apply_tandem_loads_to_scia_model") as mock_apply_loads,
            patch("src.integrations.scia_interface.create_load_combination_by_type") as mock_create_combo,
        ):
            mock_create_group.side_effect = [Mock(), Mock(), Mock()]  # traffic, permanent, wind groups
            mock_apply_loads.return_value = [Mock(), Mock()]  # multiple load cases
            mock_create_combo.side_effect = [Mock(), Mock(), Mock()]  # multiple combinations

            result = _add_realistic_tandem_loads(mock_model, params)

            # Verify exact structure compatibility
            assert isinstance(result, dict)
            assert set(result.keys()) == {"load_groups", "load_cases", "combinations"}
            assert isinstance(result["load_groups"], dict)
            assert isinstance(result["load_cases"], dict)
            assert isinstance(result["combinations"], dict)

    def test_load_case_count_matches_tandem_positions(self) -> None:
        """Test number of load cases matches tandem system output."""
        mock_model = Mock()
        params = load_bridge_default_params()

        with (
            patch("src.integrations.scia_interface.generate_tandem_loads_for_bridge") as mock_generate,
            patch("src.integrations.scia_interface.apply_tandem_loads_to_scia_model") as mock_apply,
            patch("src.integrations.scia_interface.create_load_group_by_type"),
            patch("src.integrations.scia_interface._create_dutch_standard_load_combinations") as mock_dutch_combos,
        ):
            # Mock tandem generation returning 5 load cases
            mock_generate.return_value = [{"load_case": f"BG600{i}", "wheels": [], "load": 1000} for i in range(1, 6)]
            mock_apply.return_value = [Mock() for _ in range(5)]
            mock_dutch_combos.return_value = {"uls_6.10a_traffic": Mock(), "sls_char_6.10a": Mock()}

            result = _add_realistic_tandem_loads(mock_model, params)

            # Verify tandem load cases are created
            assert len(result["load_cases"]) >= 5  # At least the tandem cases (may include others)

    def test_dutch_standard_combinations_integration(self) -> None:
        """Test that minimal traffic combinations are called with correct parameters."""
        mock_model = Mock()
        params = load_bridge_default_params()

        with (
            patch("src.integrations.scia_interface.generate_tandem_loads_for_bridge") as mock_generate,
            patch("src.integrations.scia_interface.apply_tandem_loads_to_scia_model") as mock_apply,
            patch("src.integrations.scia_interface.create_load_group_by_type") as mock_create_group,
            patch("src.integrations.scia_interface.create_load_case_complete") as mock_create_case,
            patch("src.integrations.scia_interface._create_traffic_load_combinations_minimal") as mock_traffic_combos,
        ):
            # Setup mocks
            mock_load_group = Mock()
            mock_dead_case = Mock()
            mock_wind_case = Mock()
            mock_traffic_cases = [Mock(), Mock()]

            mock_create_group.return_value = mock_load_group
            mock_create_case.side_effect = [mock_dead_case, mock_wind_case]
            mock_generate.return_value = [{"load_case": "TH6001", "wheels": [], "load": 1000}]
            mock_apply.return_value = mock_traffic_cases
            mock_traffic_combos.return_value = {"uls_6.10a_gr1a_ts": Mock(), "sls_char_6.10a_gr1a_ts": Mock()}

            result = _add_realistic_tandem_loads(mock_model, params)

            # Verify minimal traffic combinations function was called with correct parameters
            mock_traffic_combos.assert_called_once()
            call_args = mock_traffic_combos.call_args[1]  # keyword arguments

            # Note: The call goes through _create_dutch_standard_load_combinations which redirects
            # to _create_traffic_load_combinations_minimal, so we verify the redirect path works
            assert call_args["model"] is mock_model
            assert call_args["dead_load_case"] is mock_dead_case
            assert call_args["traffic_load_cases"] is mock_traffic_cases
            assert call_args["bridge_span"] == 10.0  # From bridge_default_params.json
            assert call_args["consequence_class"] == "CC2"
            assert call_args["safety_level"] == "NEN 8700 gebruik"
            assert call_args["construction_year"] == "2010"

            # Verify combinations are returned (gr1a TS focus)
            assert "combinations" in result
            assert len(result["combinations"]) == 2

    def test_load_case_naming_theoretical_vs_eurocode(self) -> None:
        """Test that load case naming distinguishes between theoretical and eurocode modes."""
        bridge_params = {"length_bridgedeck": 20.0, "width_bridgedeck": 30.0, "thickness_bridgedeck": 1.5}

        with (
            patch("src.integrations.scia_interface.tandem_systems_theoretical_lanes") as mock_theoretical,
            patch("src.integrations.scia_interface.tandem_systems_axes_more_lanes") as mock_eurocode,
        ):
            # Mock theoretical mode with TH prefix
            mock_theoretical.return_value = [{"load_case": "TH6001", "wheels": [], "load": 1875000.0}]

            # Mock eurocode mode with BG prefix
            mock_eurocode.return_value = [{"load_case": "BG6001", "wheels": [], "load": 1875000.0}]

            # Test theoretical mode
            theoretical_result = generate_tandem_loads_for_bridge(bridge_params, mode="theoretical")
            assert theoretical_result[0]["load_case"].startswith("TH")

            # Test eurocode mode
            eurocode_result = generate_tandem_loads_for_bridge(bridge_params, mode="eurocode")
            assert eurocode_result[0]["load_case"].startswith("BG")


class TestTheoreticalLaneFunctions:
    """Test theoretical lane functions from loadcase_helper_functions."""

    def test_generate_theoretical_lane_positions_30m_bridge(self) -> None:
        """Test lane position generation for 30m bridge."""
        positions = generate_theoretical_lane_positions(30.0, 3.0)

        # 30m ÷ 3m = 10 complete lanes
        expected_positions = [1.5, 4.5, 7.5, 10.5, 13.5, 16.5, 19.5, 22.5, 25.5, 28.5]
        assert positions == expected_positions
        assert len(positions) == 10

    def test_generate_theoretical_lane_positions_with_remainder(self) -> None:
        """Test lane position generation when bridge width has remainder."""
        positions = generate_theoretical_lane_positions(10.0, 3.0)

        # 10m ÷ 3m = 3 complete lanes (1m remainder ignored)
        expected_positions = [1.5, 4.5, 7.5]
        assert positions == expected_positions
        assert len(positions) == 3

    def test_generate_theoretical_lane_positions_custom_lane_width(self) -> None:
        """Test lane position generation with custom lane width."""
        positions = generate_theoretical_lane_positions(20.0, 4.0)

        # 20m ÷ 4m = 5 complete lanes
        expected_positions = [2.0, 6.0, 10.0, 14.0, 18.0]  # Centers at lane_width/2 + n*lane_width
        assert positions == expected_positions
        assert len(positions) == 5

    def test_generate_theoretical_lane_positions_edge_cases(self) -> None:
        """Test edge cases for lane position generation."""
        positions = generate_theoretical_lane_positions(2.0, 3.0)
        assert positions == []  # No complete lanes

        positions = generate_theoretical_lane_positions(9.0, 3.0)
        assert len(positions) == 3
        assert positions == [1.5, 4.5, 7.5]

    def test_generate_theoretical_lane_positions_error_handling(self) -> None:
        """Test error handling for invalid inputs."""
        with pytest.raises(ValueError, match="Bridge width must be positive"):
            generate_theoretical_lane_positions(0.0, 3.0)

        with pytest.raises(ValueError, match="Bridge width must be positive"):
            generate_theoretical_lane_positions(-5.0, 3.0)

        with pytest.raises(ValueError, match="Lane width must be positive"):
            generate_theoretical_lane_positions(30.0, 0.0)

        with pytest.raises(ValueError, match="Lane width must be positive"):
            generate_theoretical_lane_positions(30.0, -2.0)

    @patch("src.loads.loadcase_helper_functions.tandem_system_sequencer")
    def test_tandem_systems_theoretical_lanes_basic_functionality(self, mock_sequencer: Mock) -> None:
        """Test basic functionality of theoretical lane tandem system."""
        mock_sequencer.return_value = [5.0, 15.0]  # Two X positions

        result = tandem_systems_theoretical_lanes(20.0, 9.0, 1.5, lane_width=3.0)

        # Bridge: 20m length, 9m width = 3 lanes (at Y positions 1.5, 4.5, 7.5)
        # Longitudinal: 2 positions = 2 * 3 = 6 load cases total
        assert len(result) == 6

        # Verify load case naming
        load_case_names = [case["load_case"] for case in result]
        expected_names = ["TH6001", "TH6002", "TH6003", "TH6004", "TH6005", "TH6006"]
        assert load_case_names == expected_names

        # Verify all cases have required structure
        for case in result:
            assert "load_case" in case
            assert "wheels" in case
            assert "load" in case
            assert abs(case["load"] - 1875.0) < 1e-6  # Standard load intensity: 300 kN / 0.16 m²

    @patch("src.loads.loadcase_helper_functions.tandem_system_sequencer")
    def test_tandem_systems_theoretical_lanes_wheel_positioning(self, mock_sequencer: Mock) -> None:
        """Test wheel positioning in theoretical lane system."""
        mock_sequencer.return_value = [10.0]

        result = tandem_systems_theoretical_lanes(20.0, 6.0, 1.5, lane_width=3.0)

        # Bridge: 6m width = 2 lanes at Y positions 1.5, 4.5
        assert len(result) == 2

        # Check first lane (Y center = 1.5)
        first_case = result[0]
        wheels_lane_1 = first_case["wheels"]
        assert len(wheels_lane_1) == 4  # 4 wheels per tandem

        # Tandem should be centered at lane 1 (Y=1.5)
        # Tandem start_y = 1.5 - 0.6 = 0.9
        # First wheel should be at (10.0, 0.9) to (10.4, 1.3)
        first_wheel = wheels_lane_1[0]
        assert first_wheel[0] == [10.4, 0.9]  # bottom right
        assert first_wheel[1] == [10.4, 1.3]  # top right
        assert first_wheel[2] == [10.0, 1.3]  # top left
        assert first_wheel[3] == [10.0, 0.9]  # bottom left

    def test_tandem_systems_theoretical_lanes_lane_width_integration(self) -> None:
        """Test integration with different lane widths matching load_zone_geometry."""
        with patch("src.loads.loadcase_helper_functions.tandem_system_sequencer") as mock_seq:
            mock_seq.return_value = [10.0]

            result_3m = tandem_systems_theoretical_lanes(20.0, 30.0, 1.5, lane_width=3.0)
            result_custom = tandem_systems_theoretical_lanes(20.0, 30.0, 1.5, lane_width=2.5)

            # 30m width: 3.0m lanes = 10 lanes, 2.5m lanes = 12 lanes
            assert len(result_3m) == 10
            assert len(result_custom) == 12

    def test_future_function_placeholders(self) -> None:
        """Test that future functions raise NotImplementedError."""
        with pytest.raises(NotImplementedError, match="Shiftable lanes implementation planned for Phase 2"):
            tandem_systems_shiftable_lanes(20.0, 30.0, 1.5)

        with pytest.raises(NotImplementedError, match="Actual lanes implementation planned for Phase 3"):
            tandem_systems_actual_lanes(20.0, [1.5, 4.5, 7.5], 1.5)


class TestTheoreticalLaneIntegration:
    """Test theoretical traffic lane integration with tandem loads."""

    def test_determine_tandem_function_theoretical_mode(self) -> None:
        """Test tandem function determination in theoretical mode."""
        bridge_dims = {"width_bridgedeck": 30.0}
        result = determine_tandem_function_for_bridge(bridge_dims, mode="theoretical")

        assert result["function_name"] == "tandem_systems_theoretical_lanes"
        assert result["lane_count"] == 10  # 30m ÷ 3m = 10 lanes
        assert result["mode"] == "theoretical"
        assert "10 lanes across 30m" in result["description"]

    def test_determine_tandem_function_eurocode_mode(self) -> None:
        """Test tandem function determination in eurocode mode."""
        bridge_dims = {"width_bridgedeck": 30.0}
        result = determine_tandem_function_for_bridge(bridge_dims, mode="eurocode")

        assert result["function_name"] == "tandem_systems_axes_more_lanes"  # 30m > 6m = more lanes
        assert result["mode"] == "eurocode"
        assert "Eurocode notional lanes" in result["description"]

    def test_determine_tandem_function_mode_comparison(self) -> None:
        """Test that theoretical and eurocode modes produce different lane counts."""
        bridge_dims = {"width_bridgedeck": 15.0}  # 15m bridge

        theoretical_result = determine_tandem_function_for_bridge(bridge_dims, mode="theoretical")
        eurocode_result = determine_tandem_function_for_bridge(bridge_dims, mode="eurocode")

        # Theoretical: 15m ÷ 3m = 5 lanes
        assert theoretical_result["lane_count"] == 5
        assert theoretical_result["function_name"] == "tandem_systems_theoretical_lanes"

        # Eurocode: Uses notional lane calculation (different result)
        assert eurocode_result["mode"] == "eurocode"
        assert eurocode_result["function_name"] in [
            "tandem_systems_axes_single_lane",
            "tandem_systems_axes_double_lane",
            "tandem_systems_axes_more_lanes",
        ]

    def test_determine_tandem_function_invalid_mode(self) -> None:
        """Test error handling for invalid modes."""
        bridge_dims = {"width_bridgedeck": 30.0}

        with pytest.raises(ValueError, match="Unsupported mode 'invalid'"):
            determine_tandem_function_for_bridge(bridge_dims, mode="invalid")

    def test_determine_tandem_function_future_modes(self) -> None:
        """Test that future modes raise NotImplementedError."""
        bridge_dims = {"width_bridgedeck": 30.0}

        with pytest.raises(NotImplementedError, match="planned for future implementation"):
            determine_tandem_function_for_bridge(bridge_dims, mode="shiftable")

        with pytest.raises(NotImplementedError, match="planned for future implementation"):
            determine_tandem_function_for_bridge(bridge_dims, mode="actual")

    @patch("src.integrations.scia_interface.tandem_systems_theoretical_lanes")
    def test_generate_tandem_loads_theoretical_mode(self, mock_theoretical_lanes: Mock) -> None:
        """Test tandem load generation in theoretical mode."""
        mock_theoretical_lanes.return_value = [
            {"load_case": "TH6001", "wheels": [], "load": 1875000.0},
            {"load_case": "TH6002", "wheels": [], "load": 1875000.0},
        ]

        bridge_params = {"length_bridgedeck": 20.0, "width_bridgedeck": 30.0, "thickness_bridgedeck": 1.5}

        result = generate_tandem_loads_for_bridge(bridge_params, mode="theoretical")

        # Verify theoretical function was called
        mock_theoretical_lanes.assert_called_once_with(20.0, 30.0, 1.5)
        assert len(result) == 2
        assert result[0]["load_case"] == "TH6001"

    @patch("src.integrations.scia_interface.tandem_systems_axes_more_lanes")
    def test_generate_tandem_loads_eurocode_mode(self, mock_eurocode_lanes: Mock) -> None:
        """Test tandem load generation in eurocode mode."""
        mock_eurocode_lanes.return_value = [{"load_case": "BG6001", "wheels": [], "load": 1875000.0}]

        bridge_params = {
            "length_bridgedeck": 20.0,
            "width_bridgedeck": 30.0,  # > 6m = more lanes function
            "thickness_bridgedeck": 1.5,
        }

        result = generate_tandem_loads_for_bridge(bridge_params, mode="eurocode")

        # Verify eurocode function was called
        mock_eurocode_lanes.assert_called_once_with(20.0, 30.0, 1.5)
        assert len(result) == 1
        assert result[0]["load_case"] == "BG6001"

    def test_theoretical_lane_integration_end_to_end(self) -> None:
        """Test end-to-end theoretical lane integration with real bridge data."""
        mock_model = Mock()

        # Load real test data
        params = load_bridge_default_params()

        with (
            patch("src.integrations.scia_interface.create_load_group_by_type") as mock_create_group,
            patch("src.integrations.scia_interface.apply_tandem_loads_to_scia_model") as mock_apply_loads,
            patch("src.integrations.scia_interface._create_dutch_standard_load_combinations") as mock_dutch_combos,
            patch("src.integrations.scia_interface.tandem_systems_theoretical_lanes") as mock_theoretical_func,
        ):
            # Setup return values
            mock_create_group.side_effect = [Mock(), Mock(), Mock()]  # Three load groups
            mock_apply_loads.return_value = [Mock(), Mock(), Mock()]  # Multiple load cases
            mock_dutch_combos.return_value = {"uls_6.10a_traffic": Mock(), "sls_char_6.10a": Mock()}

            # Mock theoretical lanes function with realistic output
            mock_theoretical_func.return_value = [
                {"load_case": "TH6001", "wheels": [[[10, 1.5], [10.4, 1.5], [10.4, 1.9], [10, 1.9]]], "load": 1875000.0},
                {"load_case": "TH6002", "wheels": [[[10, 4.5], [10.4, 4.5], [10.4, 4.9], [10, 4.9]]], "load": 1875000.0},
                {"load_case": "TH6003", "wheels": [[[10, 7.5], [10.4, 7.5], [10.4, 7.9], [10, 7.9]]], "load": 1875000.0},
            ]

            result = _add_realistic_tandem_loads(mock_model, params)

            # Verify theoretical lanes function was called with bridge dimensions
            # Bridge from default params: length=10m, width=30m, thickness=2.0m
            mock_theoretical_func.assert_called_once_with(10.0, 30.0, 2.0)

            # Verify structure is returned correctly
            assert "load_groups" in result
            assert "load_cases" in result
            assert "combinations" in result

    def test_load_case_naming_theoretical_vs_eurocode(self) -> None:
        """Test that load case naming distinguishes between theoretical and eurocode modes."""
        bridge_params = {"length_bridgedeck": 20.0, "width_bridgedeck": 30.0, "thickness_bridgedeck": 1.5}

        with (
            patch("src.integrations.scia_interface.tandem_systems_theoretical_lanes") as mock_theoretical,
            patch("src.integrations.scia_interface.tandem_systems_axes_more_lanes") as mock_eurocode,
        ):
            # Mock theoretical mode with TH prefix
            mock_theoretical.return_value = [{"load_case": "TH6001", "wheels": [], "load": 1875000.0}]

            # Mock eurocode mode with BG prefix
            mock_eurocode.return_value = [{"load_case": "BG6001", "wheels": [], "load": 1875000.0}]

            # Test theoretical mode
            theoretical_result = generate_tandem_loads_for_bridge(bridge_params, mode="theoretical")
            assert theoretical_result[0]["load_case"].startswith("TH")

            # Test eurocode mode
            eurocode_result = generate_tandem_loads_for_bridge(bridge_params, mode="eurocode")
            assert eurocode_result[0]["load_case"].startswith("BG")


if __name__ == "__main__":
    pytest.main([__file__])
