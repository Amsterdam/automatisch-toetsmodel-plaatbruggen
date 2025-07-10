"""
Tests for SCIA model creation functions.

Tests the creation of SCIA models including geometry, loads, and complete bridge models.
"""

from typing import Any
from unittest.mock import Mock, patch

import pytest

from src.integrations.scia_integration.scia_model import (
    NodeTracker,
    create_complete_bridge_model,
    create_multi_zone_bridge_model,
)


# Mock test parameters helper
def create_mock_bridge_params(num_segments: int) -> Mock:
    """Create mock bridge parameters for testing."""
    params = Mock()
    params.bridge_segments_array = []

    for i in range(num_segments):
        segment = Mock()
        segment.l = 20.0
        segment.bz1 = 10.0
        segment.bz2 = 5.0
        segment.bz3 = 15.0
        segment.dz = 2.1
        segment.dz_2 = 2.6
        params.bridge_segments_array.append(segment)

    return params


class TestNodeTracker:
    """Test NodeTracker functionality."""

    def test_node_tracker_initialization(self) -> None:
        """Test NodeTracker initialization."""
        mock_model = Mock()
        tracker = NodeTracker(mock_model)

        assert tracker.model is mock_model
        assert tracker._nodes_by_coords == {}  # noqa: SLF001
        assert tracker._nodes_by_name == {}  # noqa: SLF001

    def test_get_or_create_node_new_node(self) -> None:
        """Test creating a new node."""
        mock_model = Mock()
        mock_node = Mock()
        mock_model.create_node.return_value = mock_node

        tracker = NodeTracker(mock_model)
        result = tracker.get_or_create_node("test_node", 1.0, 2.0, 3.0)

        mock_model.create_node.assert_called_once_with("test_node", 1.0, 2.0, 3.0)
        assert result is mock_node
        assert tracker._nodes_by_coords[(1.0, 2.0, 3.0)] is mock_node  # noqa: SLF001
        assert tracker._nodes_by_name["test_node"] is mock_node  # noqa: SLF001

    def test_get_or_create_node_existing_node(self) -> None:
        """Test reusing an existing node at same coordinates."""
        mock_model = Mock()
        mock_node = Mock()
        mock_model.create_node.return_value = mock_node

        tracker = NodeTracker(mock_model)

        # Create first node
        result1 = tracker.get_or_create_node("node1", 1.0, 2.0, 3.0)

        # Create second node at same coordinates
        result2 = tracker.get_or_create_node("node2", 1.0, 2.0, 3.0)

        # Should return same node and only call create_node once
        assert result1 is result2
        assert mock_model.create_node.call_count == 1

    def test_get_node_by_name(self) -> None:
        """Test getting node by name."""
        mock_model = Mock()
        mock_node = Mock()
        mock_model.create_node.return_value = mock_node

        tracker = NodeTracker(mock_model)
        tracker.get_or_create_node("test_node", 1.0, 2.0, 3.0)

        result = tracker.get_node_by_name("test_node")
        assert result is mock_node


class TestCreateMultiZoneBridgeModel:
    """Test multi-zone bridge model creation."""

    @patch("src.integrations.scia_integration.scia_model.scia")
    @patch("src.integrations.scia_integration.scia_model.create_node_and_thickness_dict")
    def test_create_multi_zone_bridge_model_success(self, mock_create_nodes: Mock, mock_scia: Mock) -> None:
        """Test successful multi-zone bridge model creation."""
        # Setup mock SCIA objects
        mock_model = Mock()
        mock_material = Mock()
        mock_node = Mock()

        mock_scia.Model.return_value = mock_model
        mock_scia.Material.return_value = mock_material
        mock_model.create_node.return_value = mock_node

        # Setup mock node and thickness data for 2 segments
        nodes_dict = {
            "K_dek:1_1": [0, 12.5, 0],
            "K_dek:1_2": [0, 2.5, 0],
            "K_dek:1_3": [0, -2.5, 0],
            "K_dek:1_4": [0, -17.5, 0],
            "K_dek:2_1": [20, 12.5, 0],
            "K_dek:2_2": [20, 2.5, 0],
            "K_dek:2_3": [20, -2.5, 0],
            "K_dek:2_4": [20, -17.5, 0],
        }
        thickness_dict = {
            "Z1_1": 2.1,
            "Z2_1": 2.6,
            "Z3_1": 2.1,
        }
        mock_create_nodes.return_value = (nodes_dict, thickness_dict)

        # Create test parameters with 2 segments
        params = Mock()
        params.bridge_segments_array = [Mock(), Mock()]

        result = create_multi_zone_bridge_model(params)

        # Verify SCIA API calls
        mock_scia.Model.assert_called_once()
        mock_scia.Material.assert_called_once_with(0, "C30/37")
        assert mock_model.create_node.call_count >= 8  # At least 8 nodes for 2 cross-sections
        assert mock_model.create_plane.call_count == 3  # 3 zone plates (Z1, Z2, Z3)

        assert result is mock_model

    def test_create_multi_zone_bridge_model_no_viktor(self) -> None:
        """Test multi-zone bridge model creation without VIKTOR SDK."""
        params = Mock()
        params.bridge_segments_array = [Mock()]

        with pytest.raises(ImportError, match="VIKTOR SCIA module not available"):
            create_multi_zone_bridge_model(params)

    @patch("src.integrations.scia_integration.scia_model.scia")
    @patch("src.integrations.scia_integration.scia_model.create_node_and_thickness_dict")
    def test_create_multi_zone_bridge_model_missing_coordinates(self, mock_create_nodes: Mock, mock_scia: Mock) -> None:
        """Test error handling when node coordinates are missing."""
        mock_model = Mock()
        mock_scia.Model.return_value = mock_model
        mock_scia.Material.return_value = Mock()

        # Return incomplete node dictionary (missing required nodes)
        nodes_dict = {"K_dek:1_1": [0, 12.5, 0]}  # Missing other required nodes
        thickness_dict: dict[str, float] = {}
        mock_create_nodes.return_value = (nodes_dict, thickness_dict)

        params = Mock()
        params.bridge_segments_array = [Mock()]

        with pytest.raises(ValueError, match="Coordinates for node .* not found"):
            create_multi_zone_bridge_model(params)

    @patch("src.integrations.scia_integration.scia_model.scia")
    @patch("src.integrations.scia_integration.scia_model.create_node_and_thickness_dict")
    def test_create_multi_zone_bridge_model_single_segment(self, mock_create_nodes: Mock, mock_scia: Mock) -> None:
        """Test bridge model creation with single segment."""
        mock_model = Mock()
        mock_material = Mock()
        mock_node = Mock()

        mock_scia.Model.return_value = mock_model
        mock_scia.Material.return_value = mock_material
        mock_model.create_node.return_value = mock_node

        # Node data for single segment (no plates created)
        nodes_dict = {
            "K_dek:1_1": [0, 12.5, 0],
            "K_dek:1_2": [0, 2.5, 0],
            "K_dek:1_3": [0, -2.5, 0],
            "K_dek:1_4": [0, -17.5, 0],
        }
        thickness_dict: dict[str, float] = {}
        mock_create_nodes.return_value = (nodes_dict, thickness_dict)

        params = create_mock_bridge_params(1)

        result = create_multi_zone_bridge_model(params)

        # Verify model creation
        mock_scia.Model.assert_called_once()
        mock_scia.Material.assert_called_once_with(0, "C30/37")
        assert mock_model.create_node.call_count == 4  # 4 nodes for single cross-section
        assert mock_model.create_plane.call_count == 0  # No plates for single segment

        assert result is mock_model

    @patch("src.integrations.scia_integration.scia_model.scia")
    @patch("src.integrations.scia_integration.scia_model.create_node_and_thickness_dict")
    def test_create_multi_zone_bridge_model_multiple_segments(self, mock_create_nodes: Mock, mock_scia: Mock) -> None:
        """Test bridge model creation with multiple segments."""
        mock_model = Mock()
        mock_material = Mock()
        mock_node = Mock()

        mock_scia.Model.return_value = mock_model
        mock_scia.Material.return_value = mock_material
        mock_model.create_node.return_value = mock_node

        # Node data for 3 segments
        nodes_dict = {}
        thickness_dict = {}
        for cross_section in range(1, 4):  # 3 cross-sections
            for node_suffix in range(1, 5):  # 4 nodes per cross-section
                nodes_dict[f"K_dek:{cross_section}_{node_suffix}"] = [cross_section * 20, 12.5 - node_suffix * 5, 0]

        for span in range(1, 3):  # 2 spans between 3 cross-sections
            thickness_dict[f"Z1_{span}"] = 2.1
            thickness_dict[f"Z2_{span}"] = 2.6
            thickness_dict[f"Z3_{span}"] = 2.1

        mock_create_nodes.return_value = (nodes_dict, thickness_dict)

        params = create_mock_bridge_params(3)

        result = create_multi_zone_bridge_model(params)

        # Verify model creation
        mock_scia.Model.assert_called_once()
        mock_scia.Material.assert_called_once_with(0, "C30/37")
        assert mock_model.create_node.call_count == 12  # 12 nodes for 3 cross-sections
        assert mock_model.create_plane.call_count == 6  # 6 plates (3 zones × 2 spans)

        assert result is mock_model


class TestCreateCompleteBridgeModel:
    """Test complete bridge model creation with loads."""

    @patch("src.integrations.scia_integration.scia_model.create_multi_zone_bridge_model")
    @patch("src.integrations.scia_integration.scia_model.create_load_infrastructure")
    @patch("src.integrations.scia_integration.scia_model.add_theoretical_tandem_loads")
    def test_create_complete_bridge_model_success(self, mock_add_tandems: Mock, mock_create_infrastructure: Mock, mock_create_geometry: Mock) -> None:
        """Test successful complete bridge model creation."""
        # Setup mocks
        mock_model = Mock()
        mock_params = Mock()
        mock_load_groups = {"permanent": Mock(), "traffic": Mock(), "wind": Mock()}
        mock_basic_cases = {"self_weight": Mock(), "wind": Mock()}
        mock_tandem_cases = [Mock(), Mock()]

        mock_create_geometry.return_value = mock_model
        mock_create_infrastructure.return_value = {
            "load_groups": mock_load_groups,
            "basic_load_cases": mock_basic_cases,
        }
        mock_add_tandems.return_value = mock_tandem_cases

        # Execute
        result = create_complete_bridge_model(mock_params)

        # Verify workflow
        mock_create_geometry.assert_called_once_with(mock_params)
        mock_create_infrastructure.assert_called_once_with(mock_model)
        mock_add_tandems.assert_called_once_with(mock_model, mock_params, mock_load_groups["traffic"])

        assert result is mock_model

    @patch("src.integrations.scia_integration.scia_model.create_multi_zone_bridge_model")
    def test_create_complete_bridge_model_geometry_failure(self, mock_create_geometry: Mock) -> None:
        """Test error handling when geometry creation fails."""
        mock_params = Mock()
        mock_create_geometry.side_effect = Exception("Geometry creation failed")

        with pytest.raises(Exception, match="Geometry creation failed"):
            create_complete_bridge_model(mock_params)

    @patch("src.integrations.scia_integration.scia_model.create_multi_zone_bridge_model")
    @patch("src.integrations.scia_integration.scia_model.create_load_infrastructure")
    def test_create_complete_bridge_model_load_infrastructure_failure(self, mock_create_infrastructure: Mock, mock_create_geometry: Mock) -> None:
        """Test error handling when load infrastructure creation fails."""
        mock_model = Mock()
        mock_params = Mock()
        mock_create_geometry.return_value = mock_model
        mock_create_infrastructure.side_effect = Exception("Load infrastructure failed")

        with pytest.raises(Exception, match="Load infrastructure failed"):
            create_complete_bridge_model(mock_params)

    @patch("src.integrations.scia_integration.scia_model.create_multi_zone_bridge_model")
    @patch("src.integrations.scia_integration.scia_model.create_load_infrastructure")
    @patch("src.integrations.scia_integration.scia_model.add_theoretical_tandem_loads")
    def test_create_complete_bridge_model_tandem_loads_failure(
        self, mock_add_tandems: Mock, mock_create_infrastructure: Mock, mock_create_geometry: Mock
    ) -> None:
        """Test error handling when tandem load application fails."""
        mock_model = Mock()
        mock_params = Mock()
        mock_load_groups = {"permanent": Mock(), "traffic": Mock(), "wind": Mock()}
        mock_basic_cases = {"self_weight": Mock(), "wind": Mock()}

        mock_create_geometry.return_value = mock_model
        mock_create_infrastructure.return_value = {
            "load_groups": mock_load_groups,
            "basic_load_cases": mock_basic_cases,
        }
        mock_add_tandems.side_effect = Exception("Tandem load application failed")

        with pytest.raises(Exception, match="Tandem load application failed"):
            create_complete_bridge_model(mock_params)

    @patch("src.integrations.scia_integration.scia_model.create_multi_zone_bridge_model")
    @patch("src.integrations.scia_integration.scia_model.create_load_infrastructure")
    @patch("src.integrations.scia_integration.scia_model.add_theoretical_tandem_loads")
    def test_create_complete_bridge_model_integration_workflow(
        self, mock_add_tandems: Mock, mock_create_infrastructure: Mock, mock_create_geometry: Mock
    ) -> None:
        """Test complete integration workflow with detailed verification."""
        # Setup detailed mocks
        mock_model = Mock()
        mock_params = Mock()

        # Mock load groups
        mock_permanent_group = Mock()
        mock_traffic_group = Mock()
        mock_wind_group = Mock()
        mock_load_groups = {
            "permanent": mock_permanent_group,
            "traffic": mock_traffic_group,
            "wind": mock_wind_group,
        }

        # Mock basic load cases
        mock_self_weight = Mock()
        mock_wind_case = Mock()
        mock_basic_cases = {
            "self_weight": mock_self_weight,
            "wind": mock_wind_case,
        }

        # Mock tandem cases
        mock_tandem_1 = Mock()
        mock_tandem_2 = Mock()
        mock_tandem_cases = [mock_tandem_1, mock_tandem_2]

        # Setup return values
        mock_create_geometry.return_value = mock_model
        mock_create_infrastructure.return_value = {
            "load_groups": mock_load_groups,
            "basic_load_cases": mock_basic_cases,
        }
        mock_add_tandems.return_value = mock_tandem_cases

        # Execute
        result = create_complete_bridge_model(mock_params)

        # Verify detailed workflow
        # Step 1: Geometry creation
        mock_create_geometry.assert_called_once_with(mock_params)

        # Step 2: Load infrastructure creation
        mock_create_infrastructure.assert_called_once_with(mock_model)

        # Step 3: Tandem load application
        mock_add_tandems.assert_called_once_with(mock_model, mock_params, mock_traffic_group)

        # Step 4: Return complete model
        assert result is mock_model

    @patch("src.integrations.scia_integration.scia_model.create_multi_zone_bridge_model")
    @patch("src.integrations.scia_integration.scia_model.create_load_infrastructure")
    @patch("src.integrations.scia_integration.scia_model.add_theoretical_tandem_loads")
    def test_create_complete_bridge_model_load_groups_access(
        self, mock_add_tandems: Mock, mock_create_infrastructure: Mock, mock_create_geometry: Mock
    ) -> None:
        """Test proper access to load groups from infrastructure."""
        mock_model = Mock()
        mock_params = Mock()

        # Create specific load group mocks
        mock_permanent_group = Mock()
        mock_traffic_group = Mock()
        mock_wind_group = Mock()

        mock_load_groups = {
            "permanent": mock_permanent_group,
            "traffic": mock_traffic_group,
            "wind": mock_wind_group,
        }

        mock_create_geometry.return_value = mock_model
        mock_create_infrastructure.return_value = {
            "load_groups": mock_load_groups,
            "basic_load_cases": {"self_weight": Mock(), "wind": Mock()},
        }
        mock_add_tandems.return_value = [Mock()]

        # Execute
        create_complete_bridge_model(mock_params)

        # Verify that specific traffic group was passed to tandem load function
        mock_add_tandems.assert_called_once_with(mock_model, mock_params, mock_traffic_group)


class TestBridgeModelIntegration:
    """Test integration between geometry and load systems."""

    @patch("src.integrations.scia_integration.scia_model.create_multi_zone_bridge_model")
    @patch("src.integrations.scia_integration.scia_model.create_load_infrastructure")
    @patch("src.integrations.scia_integration.scia_model.add_theoretical_tandem_loads")
    def test_model_state_preservation(self, mock_add_tandems: Mock, mock_create_infrastructure: Mock, mock_create_geometry: Mock) -> None:
        """Test that model state is preserved throughout the workflow."""
        # Setup mocks where each function modifies the model
        mock_model = Mock()
        mock_params = Mock()

        # Track model state changes
        geometry_state = {"nodes": 4, "elements": 1}
        load_state = {"load_groups": 3, "load_cases": 2}
        tandem_state = {"tandem_cases": 5}

        def mock_geometry_creation(_params: Any) -> Mock:  # noqa: ANN401
            mock_model.state = geometry_state
            return mock_model

        def mock_infrastructure_creation(model: Any) -> dict[str, Any]:  # noqa: ANN401
            model.state.update(load_state)
            return {
                "load_groups": {"permanent": Mock(), "traffic": Mock(), "wind": Mock()},
                "basic_load_cases": {"self_weight": Mock(), "wind": Mock()},
            }

        def mock_tandem_addition(model: Any, _params: Any, _traffic_group: Any) -> list[Mock]:  # noqa: ANN401
            model.state.update(tandem_state)
            return [Mock(), Mock()]

        mock_create_geometry.side_effect = mock_geometry_creation
        mock_create_infrastructure.side_effect = mock_infrastructure_creation
        mock_add_tandems.side_effect = mock_tandem_addition

        # Execute
        result = create_complete_bridge_model(mock_params)

        # Verify model state accumulation
        expected_state = {**geometry_state, **load_state, **tandem_state}
        assert result.state == expected_state

    def test_backwards_compatibility_alias(self) -> None:
        """Test that old function names still work."""
        # Test that create_simple_scia_plate_model is aliased to create_multi_zone_bridge_model
        from src.integrations.scia_integration.scia_model import create_simple_scia_plate_model

        # They should be the same function
        assert create_simple_scia_plate_model is create_multi_zone_bridge_model


if __name__ == "__main__":
    pytest.main([__file__])
