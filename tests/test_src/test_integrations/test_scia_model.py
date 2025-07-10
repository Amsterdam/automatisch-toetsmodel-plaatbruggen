"""
Tests for SCIA model creation functions.

Tests the creation of SCIA models including geometry, loads, and complete bridge models.
"""

from unittest.mock import Mock, patch

import pytest

from src.integrations.scia_integration.scia_definitions import (
    MaterialDefinition,
    NodeDefinition,
    PlateDefinition,
)
from src.integrations.scia_integration.scia_model import (
    create_multi_zone_bridge_model,
)


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


class TestCreateMultiZoneBridgeModel:
    """Test multi-zone bridge model definition creation."""

    @patch("src.integrations.scia_integration.scia_model.create_node_and_thickness_dict")
    def test_create_multi_zone_bridge_model_success(self, mock_create_nodes: Mock) -> None:
        """Test successful multi-zone bridge model definition creation."""
        # Setup mock node and thickness data for 2 segments (1 span)
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
        thickness_dict = {"Z1_1": 2.1, "Z2_1": 2.6, "Z3_1": 2.1}
        mock_create_nodes.return_value = (nodes_dict, thickness_dict)

        params = create_mock_bridge_params(2)
        definitions = create_multi_zone_bridge_model(params)

        # Verify definitions
        assert "nodes" in definitions
        assert "materials" in definitions
        assert "plates" in definitions

        assert len(definitions["nodes"]) == 8
        assert all(isinstance(n, NodeDefinition) for n in definitions["nodes"])
        assert len(definitions["materials"]) == 1
        assert isinstance(definitions["materials"][0], MaterialDefinition)
        assert len(definitions["plates"]) == 3
        assert all(isinstance(p, PlateDefinition) for p in definitions["plates"])

    @patch("src.integrations.scia_integration.scia_model.create_node_and_thickness_dict")
    def test_create_multi_zone_bridge_model_single_segment(self, mock_create_nodes: Mock) -> None:
        """Test with a single segment (no plates should be created)."""
        nodes_dict = {
            "K_dek:1_1": [0, 12.5, 0],
            "K_dek:1_2": [0, 2.5, 0],
            "K_dek:1_3": [0, -2.5, 0],
            "K_dek:1_4": [0, -17.5, 0],
        }
        thickness_dict: dict[str, float] = {}
        mock_create_nodes.return_value = (nodes_dict, thickness_dict)

        params = create_mock_bridge_params(1)
        definitions = create_multi_zone_bridge_model(params)

        assert len(definitions["nodes"]) == 4
        assert len(definitions["plates"]) == 0  # No spans, so no plates
        assert len(definitions["materials"]) == 1

    @patch("src.integrations.scia_integration.scia_model.create_node_and_thickness_dict")
    def test_create_multi_zone_bridge_model_missing_thickness(self, mock_create_nodes: Mock) -> None:
        """Test error handling when thickness data is missing for a plate."""
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
        # Missing thickness for Z1_1
        thickness_dict = {"Z2_1": 2.6, "Z3_1": 2.1}
        mock_create_nodes.return_value = (nodes_dict, thickness_dict)

        params = create_mock_bridge_params(2)
        with pytest.raises(ValueError, match="Thickness for plate Z1_1 not found."):
            create_multi_zone_bridge_model(params)


if __name__ == "__main__":
    pytest.main([__file__])
