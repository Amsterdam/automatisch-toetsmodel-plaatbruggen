"""
Tests for SCIA integration module.

These tests verify the core SCIA functionality without requiring VIKTOR SDK or SCIA Worker.
"""

import json
from pathlib import Path
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
        assert tracker._nodes_by_coords == {}
        assert tracker._nodes_by_name == {}

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
        assert tracker._nodes_by_coords[(0.0, 0.0, 0.0)] is mock_node
        assert tracker._nodes_by_name["N1"] is mock_node

    def test_get_or_create_node_existing_node(self) -> None:
        """Test reusing existing node at same coordinates."""
        from src.integrations.scia_interface import NodeTracker

        mock_model = Mock()
        mock_node = Mock()
        
        tracker = NodeTracker(mock_model)
        tracker._nodes_by_coords[(0.0, 0.0, 0.0)] = mock_node
        
        result = tracker.get_or_create_node("N2", 0.0, 0.0, 0.0)
        
        assert result is mock_node
        mock_model.create_node.assert_not_called()  # Should not create new node

    def test_get_node_by_name(self) -> None:
        """Test retrieving node by name."""
        from src.integrations.scia_interface import NodeTracker

        mock_model = Mock()
        mock_node = Mock()
        
        tracker = NodeTracker(mock_model)
        tracker._nodes_by_name["N1"] = mock_node
        
        result = tracker.get_node_by_name("N1")
        assert result is mock_node


class TestNodeAndThicknessDictCreation:
    """Test node and thickness dictionary creation from bridge parameters."""

    def test_create_node_and_thickness_dict_single_segment(self) -> None:
        """Test node creation with single bridge segment."""
        from src.integrations.scia_interface import create_node_and_thickness_dict

        # Create minimal test parameters - use dictionary access for Mock objects
        segment = Mock()
        segment.__getitem__ = lambda self, key: {"l": 10.0}[key]
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
            "K_dek:1_1": [10.0, 6.5, 0],    # x=10, y=bz1+bz2/2=5+1.5=6.5
            "K_dek:1_2": [10.0, 1.5, 0],    # x=10, y=bz2/2=1.5
            "K_dek:1_3": [10.0, -1.5, 0],   # x=10, y=-bz2/2=-1.5
            "K_dek:1_4": [10.0, -5.5, 0],   # x=10, y=-bz3-bz2/2=-4-1.5=-5.5
        }
        
        assert nodes_dict == expected_nodes
        assert thickness_dict == {}  # No plates created with single segment

    def test_create_node_and_thickness_dict_multiple_segments(self) -> None:
        """Test node creation with multiple bridge segments."""
        from src.integrations.scia_interface import create_node_and_thickness_dict

        # Create test parameters with 3 segments
        params = Mock()
        params.bridge_segments_array = [
            Mock(l=0, bz1=5.0, bz2=3.0, bz3=4.0, dz=2.0, dz_2=2.5),     # First segment (l=0)
            Mock(l=10, bz1=5.0, bz2=3.0, bz3=4.0, dz=2.1, dz_2=2.6),    # Second segment
            Mock(l=8, bz1=5.0, bz2=3.0, bz3=4.0, dz=2.2, dz_2=2.7),     # Third segment
        ]
        
        nodes_dict, thickness_dict = create_node_and_thickness_dict(params)
        
        # Should create 3 cross-sections
        assert "K_dek:1_1" in nodes_dict
        assert "K_dek:2_1" in nodes_dict  
        assert "K_dek:3_1" in nodes_dict
        
        # Check cumulative lengths
        assert nodes_dict["K_dek:1_1"][0] == 0   # First segment cumulative length
        assert nodes_dict["K_dek:2_1"][0] == 10  # Second segment cumulative length
        assert nodes_dict["K_dek:3_1"][0] == 18  # Third segment cumulative length (10+8)
        
        # Check thickness data for plates between segments
        expected_thickness = {
            "Z1_1": 2.1, "Z2_1": 2.6, "Z3_1": 2.1,  # From segment 1 (index 1)
            "Z1_2": 2.2, "Z2_2": 2.7, "Z3_2": 2.2,  # From segment 2 (index 2)
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

    @patch('src.integrations.scia_interface.scia')
    def test_create_simple_scia_plate_model_mocked(self, mock_scia) -> None:
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

    @patch('src.integrations.scia_interface.scia')
    def test_create_simple_scia_plate_model_missing_coordinates(self, mock_scia) -> None:
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
        except (ImportError, KeyError) as e:
            # Expected outside VIKTOR environment
            expected_errors = ["VIKTOR SCIA module not available", "VIKTOR_DEV"]
            assert any(error in str(e) for error in expected_errors)


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

    @patch('src.integrations.scia_interface.scia')
    @patch('src.integrations.scia_interface.File')
    def test_create_scia_analysis_success(self, mock_file_class, mock_scia) -> None:
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

    @patch('src.integrations.scia_interface.create_simple_scia_plate_model')
    @patch('src.integrations.scia_interface.create_scia_analysis_from_template')
    def test_create_bridge_scia_model_success(self, mock_create_analysis, mock_create_model) -> None:
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
            
        except (ImportError, KeyError, FileNotFoundError) as e:
            # Expected outside VIKTOR environment or missing template
            expected_errors = ["VIKTOR SCIA module not available", "VIKTOR_DEV", "template file not found"]
            assert any(error in str(e) for error in expected_errors)


class TestDummyLoadDemonstration:
    """Test dummy load demonstration function."""

    @patch('src.integrations.scia_interface.create_load_group_by_type')
    @patch('src.integrations.scia_interface.create_load_case_complete')
    @patch('src.integrations.scia_interface.create_load_combination_by_type')
    @patch('src.integrations.scia_interface.create_patch_surface_load')
    def test_add_dummy_wheel_loads(self, mock_patch_load, mock_combination, mock_load_case, mock_load_group) -> None:
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
            assert len([k for k in nodes_dict.keys() if k.startswith("K_dek:1_")]) == 4
            
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
        
        assert nodes_dict["K_dek:1_1"] == [0, 12.5, 0]    # Zone 1 left
        assert nodes_dict["K_dek:1_2"] == [0, 2.5, 0]     # Zone 1 right
        assert nodes_dict["K_dek:1_3"] == [0, -2.5, 0]    # Zone 3 left
        assert nodes_dict["K_dek:1_4"] == [0, -17.5, 0]   # Zone 3 right
        
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


if __name__ == "__main__":
    pytest.main([__file__])
