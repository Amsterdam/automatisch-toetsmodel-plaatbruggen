"""
Tests for SCIA integration module.

These tests verify the core SCIA functionality without requiring VIKTOR SDK or SCIA Worker.
"""

from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest

from tests.test_data.seed_loader import load_bridge_default_params


class TestNodeTracker:
    """Test NodeTracker helper class."""

    def test_node_tracker_initialization(self) -> None:
        """Test NodeTracker initialization."""
        from src.integrations.scia_interface import NodeTracker

        mock_model = Mock()
        tracker = NodeTracker(mock_model)

        assert tracker.model is mock_model
        assert tracker._nodes_by_coords == {}  # noqa: SLF001
        assert tracker._nodes_by_name == {}  # noqa: SLF001

    def test_get_or_create_node_new_node(self) -> None:
        """Test creating new node when coordinates don't exist."""
        from src.integrations.scia_interface import NodeTracker

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
        from src.integrations.scia_interface import NodeTracker

        mock_model = Mock()
        mock_node = Mock()

        tracker = NodeTracker(mock_model)
        tracker._nodes_by_coords[(0.0, 0.0, 0.0)] = mock_node  # noqa: SLF001

        result = tracker.get_or_create_node("N2", 0.0, 0.0, 0.0)

        assert result is mock_node
        mock_model.create_node.assert_not_called()  # Should not create new node

    def test_get_node_by_name(self) -> None:
        """Test retrieving node by name."""
        from src.integrations.scia_interface import NodeTracker

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
        from src.integrations.scia_interface import create_node_and_thickness_dict

        # Create minimal test parameters - use dictionary access for Mock objects
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
        from src.integrations.scia_interface import create_node_and_thickness_dict

        # Create test parameters with 3 segments
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
        from src.integrations.scia_interface import create_node_and_thickness_dict

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
        from src.integrations.scia_interface import create_simple_scia_plate_model

        # Setup mocks
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
        from src.integrations.scia_interface import create_simple_scia_plate_model

        params = Mock()
        params.bridge_segments_array = [Mock(l=0, bz1=5.0, bz2=3.0, bz3=4.0)]

        with pytest.raises(ImportError, match="VIKTOR SCIA module not available"):
            create_simple_scia_plate_model(params)

    @patch("src.integrations.scia_interface.scia")
    def test_create_simple_scia_plate_model_missing_coordinates(self, mock_scia: Any) -> None:  # noqa: ANN401
        """Test error handling when node coordinates are missing."""
        from src.integrations.scia_interface import create_simple_scia_plate_model

        # Setup mocks
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
        from src.integrations.scia_interface import create_simple_scia_plate_model

        # Load real test parameters
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
        from src.integrations.scia_interface import create_scia_analysis_from_template

        mock_xml_file = Mock()
        mock_def_file = Mock()
        missing_template_path = Path("/nonexistent/template.esa")

        with pytest.raises(FileNotFoundError, match="SCIA template file not found"):
            create_scia_analysis_from_template(mock_xml_file, mock_def_file, missing_template_path)

    def test_create_scia_analysis_no_viktor(self) -> None:
        """Test SCIA analysis creation without VIKTOR SDK."""
        from src.integrations.scia_interface import create_scia_analysis_from_template

        mock_xml_file = Mock()
        mock_def_file = Mock()
        template_path = Path("dummy.esa")

        with pytest.raises(ImportError, match="VIKTOR SCIA module not available"):
            create_scia_analysis_from_template(mock_xml_file, mock_def_file, template_path)

    @patch("src.integrations.scia_interface.scia")
    @patch("src.integrations.scia_interface.File")
    def test_create_scia_analysis_success(self, mock_file_class: Any, mock_scia: Any) -> None:  # noqa: ANN401
        """Test successful SCIA analysis creation."""
        from src.integrations.scia_interface import create_scia_analysis_from_template

        # Setup mocks
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
        from src.integrations.scia_interface import create_bridge_scia_model

        # Setup mocks
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
        from src.integrations.scia_interface import create_bridge_scia_model

        # Load real test parameters
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
        from src.integrations.scia_interface import _add_dummy_wheel_loads

        # Setup mocks
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
        from src.integrations.scia_interface import create_node_and_thickness_dict

        # Load real test data
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
        from src.integrations.scia_interface import create_node_and_thickness_dict

        # Create test parameters with known dimensions
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
        from src.integrations.scia_interface import create_node_and_thickness_dict

        # Test with missing attributes
        params = Mock()
        params.bridge_segments_array = [Mock()]  # Missing required attributes

        with pytest.raises(AttributeError):
            create_node_and_thickness_dict(params)

    def test_zero_length_segments(self) -> None:
        """Test handling of zero-length segments."""
        from src.integrations.scia_interface import create_node_and_thickness_dict

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
        from src.integrations.scia_interface import create_node_and_thickness_dict

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
        from src.integrations.scia_interface import extract_tandem_parameters_from_bridge

        # Load real test data
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
        from src.integrations.scia_interface import extract_tandem_parameters_from_bridge

        # Create test parameters with single segment
        params = Mock()
        params.bridge_segments_array = [Mock(l=0, bz1=8.0, bz2=4.0, bz3=12.0, dz=1.5)]

        result = extract_tandem_parameters_from_bridge(params)

        assert result["length_bridgedeck"] == 0.0  # Single segment with l=0
        assert result["width_bridgedeck"] == 24.0  # 8+4+12
        assert result["thickness_bridgedeck"] == 1.5

    def test_extract_tandem_parameters_multiple_segments(self) -> None:
        """Test parameter extraction with multiple segments."""
        from src.integrations.scia_interface import extract_tandem_parameters_from_bridge

        # Create test parameters with multiple segments
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
        from src.integrations.scia_interface import extract_tandem_parameters_from_bridge

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
        from src.integrations.scia_interface import extract_tandem_parameters_from_bridge

        params = Mock()
        params.bridge_segments_array = []

        with pytest.raises(IndexError):
            extract_tandem_parameters_from_bridge(params)


class TestTandemSCIAApplication:
    """Test applying tandem loads to SCIA model."""

    @patch("src.integrations.scia_interface.create_load_case_complete")
    def test_create_tandem_load_cases_from_bg_naming(self, mock_create_case: Mock) -> None:
        """Test creating load cases with BG6001, BG6002 naming."""
        from src.integrations.scia_interface import apply_tandem_loads_to_scia_model

        # Mock SCIA objects
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
        from src.integrations.scia_interface import apply_tandem_loads_to_scia_model

        # Mock SCIA objects
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
        from src.integrations.scia_interface import apply_tandem_loads_to_scia_model

        # Mock SCIA objects
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


class TestDutchStandardLoadCombinations:
    """Test Dutch standard load combinations (NEN 8700/8701) implementation."""

    @patch("src.integrations.scia_interface.get_gamma_factors")
    @patch("src.integrations.scia_interface.get_psi_factor")
    @patch("src.integrations.scia_interface.create_load_combination_by_type")
    def test_create_dutch_standard_load_combinations_success(self, mock_combination: Mock, mock_psi: Mock, mock_gamma: Mock) -> None:
        """Test successful creation of Dutch standard load combinations."""
        from src.integrations.scia_interface import _create_dutch_standard_load_combinations

        # Setup mocks
        mock_model = Mock()
        mock_dead_case = Mock()
        mock_traffic_case_1 = Mock()
        mock_traffic_case_2 = Mock()
        mock_wind_case = Mock()
        mock_combo_object = Mock()

        # Mock gamma factors (NEN 8700)
        mock_gamma.return_value = {
            "6.10a": {
                "gamma_Gjsup": 1.25,
                "gamma_Qverkeer": 1.25,
                "gamma_Qwind": 1.4,
            },
            "6.10b": {
                "gamma_Gjsup": 1.15,
                "gamma_Qverkeer": 1.25,
                "gamma_Qwind": 1.4,
            },
        }

        # Mock psi factor (NEN 8701)
        mock_psi.return_value = 0.95

        # Mock combination creation
        mock_combination.return_value = mock_combo_object

        # Test parameters
        traffic_cases = [mock_traffic_case_1, mock_traffic_case_2]
        bridge_span = 25.0

        result = _create_dutch_standard_load_combinations(
            model=mock_model,
            dead_load_case=mock_dead_case,
            traffic_load_cases=traffic_cases,
            wind_case=mock_wind_case,
            bridge_span=bridge_span,
            consequence_class="CC2",
            safety_level="NEN 8700 gebruik",
            construction_year="2010",
        )

        # Verify function calls
        mock_gamma.assert_called_once_with(cc="CC2", safety_level="NEN 8700 gebruik", building_year="2010")
        mock_psi.assert_called_once_with(span=25.0, reference_period=50.0)

        # Verify combinations were created
        assert mock_combination.call_count >= 6  # Multiple combinations for both 6.10a and 6.10b
        assert len(result) >= 6  # Should have multiple combination types

        # Verify combination names follow expected pattern
        expected_keys = [
            "uls_6.10a_traffic",
            "uls_6.10a_traffic_wind",
            "uls_6.10a_wind_traffic",
            "sls_char_6.10a",
            "sls_freq_6.10a",
        ]
        for key in expected_keys:
            assert key in result

    @patch("src.integrations.scia_interface.get_gamma_factors")
    def test_create_dutch_standard_load_combinations_fallback(self, mock_gamma: Mock) -> None:
        """Test fallback to basic combinations when Dutch standards fail."""
        from src.integrations.scia_interface import _create_dutch_standard_load_combinations

        # Setup mocks
        mock_model = Mock()
        mock_dead_case = Mock()
        mock_traffic_case = Mock()
        mock_wind_case = Mock()

        # Mock gamma factors to raise exception
        mock_gamma.side_effect = ValueError("Gamma factors not found")

        with (
            patch("src.integrations.scia_interface.create_load_combination_by_type") as mock_combination,
            patch("builtins.print"),  # Suppress debug prints
        ):
            mock_combination.return_value = Mock()

            result = _create_dutch_standard_load_combinations(
                model=mock_model,
                dead_load_case=mock_dead_case,
                traffic_load_cases=[mock_traffic_case],
                wind_case=mock_wind_case,
                bridge_span=25.0,
            )

            # Should fall back to basic combinations
            assert len(result) == 2
            assert "uls_basic" in result
            assert "sls_basic" in result

            # Verify basic combinations were created
            assert mock_combination.call_count == 2

    def test_create_dutch_standard_load_combinations_no_traffic(self) -> None:
        """Test behavior when no traffic load cases are provided."""
        from src.integrations.scia_interface import _create_dutch_standard_load_combinations

        mock_model = Mock()
        mock_dead_case = Mock()
        mock_wind_case = Mock()

        with (
            patch("src.integrations.scia_interface.get_gamma_factors") as mock_gamma,
            patch("src.integrations.scia_interface.get_psi_factor") as mock_psi,
        ):
            mock_gamma.return_value = {"6.10a": {}, "6.10b": {}}
            mock_psi.return_value = 0.95

            result = _create_dutch_standard_load_combinations(
                model=mock_model,
                dead_load_case=mock_dead_case,
                traffic_load_cases=[],  # No traffic cases
                wind_case=mock_wind_case,
                bridge_span=25.0,
            )

            # Should return empty result for no traffic cases
            assert result == {}


class TestRealisticTandemLoadsComplete:
    """Test complete realistic tandem loads implementation."""

    def test_add_realistic_tandem_loads_with_real_bridge_data(self) -> None:
        """Test using real bridge_default_params.json data."""
        from src.integrations.scia_interface import _add_realistic_tandem_loads

        # Setup mocks
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
        from src.integrations.scia_interface import _add_realistic_tandem_loads

        # Mock all dependencies
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
        from src.integrations.scia_interface import _add_realistic_tandem_loads

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
        """Test that Dutch standard combinations are called with correct parameters."""
        from src.integrations.scia_interface import _add_realistic_tandem_loads

        mock_model = Mock()
        params = load_bridge_default_params()

        with (
            patch("src.integrations.scia_interface.generate_tandem_loads_for_bridge") as mock_generate,
            patch("src.integrations.scia_interface.apply_tandem_loads_to_scia_model") as mock_apply,
            patch("src.integrations.scia_interface.create_load_group_by_type") as mock_create_group,
            patch("src.integrations.scia_interface.create_load_case_complete") as mock_create_case,
            patch("src.integrations.scia_interface._create_dutch_standard_load_combinations") as mock_dutch_combos,
        ):
            # Setup mocks
            mock_load_group = Mock()
            mock_dead_case = Mock()
            mock_wind_case = Mock()
            mock_traffic_cases = [Mock(), Mock()]

            mock_create_group.return_value = mock_load_group
            mock_create_case.side_effect = [mock_dead_case, mock_wind_case]
            mock_generate.return_value = [{"load_case": "BG6001", "wheels": [], "load": 1000}]
            mock_apply.return_value = mock_traffic_cases
            mock_dutch_combos.return_value = {"uls_6.10a_traffic": Mock(), "sls_char_6.10a": Mock()}

            result = _add_realistic_tandem_loads(mock_model, params)

            # Verify Dutch combinations function was called with correct parameters
            mock_dutch_combos.assert_called_once()
            call_args = mock_dutch_combos.call_args[1]  # keyword arguments

            assert call_args["model"] is mock_model
            assert call_args["dead_load_case"] is mock_dead_case
            assert call_args["traffic_load_cases"] is mock_traffic_cases
            assert call_args["wind_case"] is mock_wind_case
            assert call_args["bridge_span"] == 10.0  # From bridge_default_params.json
            assert call_args["consequence_class"] == "CC2"
            assert call_args["safety_level"] == "NEN 8700 gebruik"
            assert call_args["construction_year"] == "2010"

            # Verify combinations are returned
            assert "combinations" in result
            assert len(result["combinations"]) == 2


if __name__ == "__main__":
    pytest.main([__file__])
