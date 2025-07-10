"""
Tests for SCIA model creation functions.

Tests the creation of SCIA models including geometry, loads, and complete bridge models.
"""

from unittest.mock import MagicMock, patch

import pytest
from munch import Munch  # type: ignore[import-untyped]

from src.integrations.scia_integration.scia_definitions import (
    MaterialDefinition,
    NodeDefinition,
    PlateDefinition,
)
from src.integrations.scia_integration.scia_model import (
    _define_bridge_geometry,
    define_complete_bridge_model,
)
from tests.test_data.seed_loader import load_bridge_default_params


@pytest.fixture
def mock_params() -> MagicMock:
    """Fixture to provide mocked VIKTOR parameters."""
    return load_bridge_default_params()


class TestDefineBridgeGeometry:
    """Test cases for the _define_bridge_geometry function."""

    @patch("src.integrations.scia_integration.scia_model.create_node_and_thickness_dict")
    def test_define_bridge_geometry_structure(self, mock_create_node_and_thickness_dict: MagicMock, mock_params: MagicMock) -> None:
        """Test the basic structure of the returned dictionary."""
        # Arrange
        mock_create_node_and_thickness_dict.return_value = ({}, {})

        # Act
        result = _define_bridge_geometry(mock_params)

        # Assert
        assert isinstance(result, dict)
        assert all(key in result for key in ["nodes", "materials", "plates"])
        assert isinstance(result["nodes"], list)
        assert isinstance(result["materials"], list)
        assert isinstance(result["plates"], list)

    @patch("src.integrations.scia_integration.scia_model.create_node_and_thickness_dict")
    def test_define_bridge_geometry_material_definition(self, mock_create_node_and_thickness_dict: MagicMock, mock_params: MagicMock) -> None:
        """Test that the material is correctly defined."""
        # Arrange
        mock_create_node_and_thickness_dict.return_value = ({}, {})

        # Act
        result = _define_bridge_geometry(mock_params)

        # Assert
        assert len(result["materials"]) == 1
        material = result["materials"][0]
        assert isinstance(material, MaterialDefinition)
        assert material.name == "C30/37"

    @patch("src.integrations.scia_integration.scia_model.create_node_and_thickness_dict")
    def test_define_bridge_geometry_node_definitions(self, mock_create_node_and_thickness_dict: MagicMock, mock_params: MagicMock) -> None:
        """Test the creation of node definitions."""
        # Arrange
        nodes_data = {
            "K_dek:1_1": [0.0, 10.0, 0.0],
            "K_dek:1_2": [0.0, 5.0, 0.0],
            "K_dek:2_1": [20.0, 10.0, 0.0],
            "K_dek:2_2": [20.0, 5.0, 0.0],
        }
        mock_create_node_and_thickness_dict.return_value = (nodes_data, {})

        # Act
        result = _define_bridge_geometry(mock_params)

        # Assert
        assert len(result["nodes"]) == 4
        node_names = {node.name for node in result["nodes"]}
        assert node_names == {"K_dek:1_1", "K_dek:1_2", "K_dek:2_1", "K_dek:2_2"}
        for node in result["nodes"]:
            assert isinstance(node, NodeDefinition)
            assert node.name in nodes_data
            assert [node.x, node.y, node.z] == nodes_data[node.name]

    @patch("src.integrations.scia_integration.scia_model.create_node_and_thickness_dict")
    def test_define_bridge_geometry_plate_definitions(self, mock_create_node_and_thickness_dict: MagicMock, mock_params: MagicMock) -> None:
        """Test the creation of plate definitions."""
        # Arrange
        nodes_data = {f"K_dek:{i}_{j}": [0, 0, 0] for i in range(1, 4) for j in range(1, 5)}
        thickness_data = {"Z1_1": 0.5, "Z2_1": 0.6, "Z3_1": 0.5, "Z1_2": 0.5, "Z2_2": 0.6, "Z3_2": 0.5}
        mock_create_node_and_thickness_dict.return_value = (nodes_data, thickness_data)

        # Make params have 3 segments for this test
        mock_params.bridge_segments_array = [MagicMock(), MagicMock(), MagicMock()]

        # Act
        result = _define_bridge_geometry(mock_params)

        # Assert
        assert len(result["plates"]) == 6  # 3 zones for 2 spans (3 segments)
        for plate in result["plates"]:
            assert isinstance(plate, PlateDefinition)
            assert plate.material_name == "C30/37"
            assert len(plate.corner_node_names) == 4

        plate_names = {p.name for p in result["plates"]}
        assert "Z1_1" in plate_names
        assert "Z2_2" in plate_names

    def test_define_bridge_geometry_no_segments(self) -> None:
        """Test error handling when no bridge segments are provided."""
        # Arrange
        params_no_segments = Munch({"bridge_segments_array": []})
        # Act & Assert
        with pytest.raises(AttributeError):
            _define_bridge_geometry(params_no_segments)


class TestDefineCompleteBridgeModel:
    """Test cases for the define_complete_bridge_model function."""

    @patch("src.integrations.scia_integration.scia_model._define_bridge_geometry")
    def test_define_complete_model_structure(self, mock_define_geometry: MagicMock, mock_params: MagicMock) -> None:
        """Test the structure and placeholder keys for the complete model definition."""
        # Arrange
        mock_define_geometry.return_value = {"nodes": [], "materials": [], "plates": []}

        # Act
        result = define_complete_bridge_model(mock_params)

        # Assert
        assert isinstance(result, dict)
        assert "nodes" in result
        # Check for placeholder keys
        assert "load_groups" in result and result["load_groups"] == []
        assert "load_cases" in result and result["load_cases"] == []
        assert "surface_loads" in result and result["surface_loads"] == []
        assert "load_combinations" in result and result["load_combinations"] == []
        mock_define_geometry.assert_called_once_with(mock_params)


if __name__ == "__main__":
    pytest.main([__file__])
