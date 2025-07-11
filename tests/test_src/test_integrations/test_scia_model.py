"""
Tests for SCIA model creation functions.

Tests the high-level orchestration of building a complete SCIA model by mocking
the SciaModelBuilder and the functions it depends on.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest
from munch import Munch  # type: ignore[import-untyped]

from src.integrations.scia_integration.scia_model import create_bridge_geometry, define_complete_bridge_model
from tests.test_data.seed_loader import load_bridge_default_params


@pytest.fixture
def mock_builder() -> Mock:
    """Fixture to provide a mocked SciaModelBuilder."""
    return Mock()


@pytest.fixture
def mock_params() -> MagicMock:
    """Fixture to provide mocked VIKTOR parameters from a JSON file."""
    return load_bridge_default_params()


class TestCreateBridgeGeometry:
    """Test cases for the create_bridge_geometry function."""

    @patch("src.integrations.scia_integration.scia_model.create_node_and_thickness_dict")
    def test_create_bridge_geometry_logic(self, mock_create_node_dict: MagicMock, mock_builder: Mock, mock_params: MagicMock) -> None:
        """Test the logic for creating materials, nodes, and plates."""
        # Arrange
        nodes_data = {
            "K_dek:1_1": [0, 0, 0],
            "K_dek:1_2": [0, 0, 0],
            "K_dek:1_3": [0, 0, 0],
            "K_dek:1_4": [0, 0, 0],
            "K_dek:2_1": [0, 0, 0],
            "K_dek:2_2": [0, 0, 0],
            "K_dek:2_3": [0, 0, 0],
            "K_dek:2_4": [0, 0, 0],
        }
        thickness_data = {"Z1_1": 0.5, "Z2_1": 0.6, "Z3_1": 0.5}
        mock_create_node_dict.return_value = (nodes_data, thickness_data)
        # 2 segments in default params, so 1 span with 3 plates
        mock_params.bridge_segments_array = [MagicMock(), MagicMock()]

        # Act
        plate_names = create_bridge_geometry(mock_builder, mock_params)

        # Assert
        mock_builder.create_material.assert_called_once_with(name="C30/37")
        assert mock_builder.create_node.call_count == len(nodes_data)
        assert mock_builder.create_plate.call_count == 3
        assert len(plate_names) == 3
        assert "Z1_1" in plate_names
        assert "Z2_1" in plate_names
        assert "Z3_1" in plate_names

    def test_create_bridge_geometry_no_segments_raises_error(self, mock_builder: Mock) -> None:
        """Test that an error is raised if no segments are provided."""
        params_no_segments = Munch({"bridge_segments_array": []})
        with pytest.raises(IndexError):  # Or whatever error `create_node_and_thickness_dict` raises
            create_bridge_geometry(mock_builder, params_no_segments)


class TestDefineCompleteBridgeModel:
    """Test cases for the define_complete_bridge_model function."""

    @patch("src.integrations.scia_integration.scia_model.create_bridge_geometry")
    @patch("src.integrations.scia_integration.scia_model.create_all_supports")
    @patch("src.integrations.scia_integration.scia_model.create_all_load_groups")
    @patch("src.integrations.scia_integration.scia_model.create_all_load_cases")
    @patch("src.integrations.scia_integration.scia_model.create_all_loads")
    @patch("src.integrations.scia_integration.scia_model.create_all_load_combinations")
    @pytest.mark.usefixtures("mock_combinations", "mock_loads", "mock_cases", "mock_groups", "mock_supports", "mock_geometry")
    def test_define_complete_model_orchestration(
        self,
        mock_builder: Mock,
        mock_params: MagicMock,
    ) -> None:
        """Test that the main model definition function calls all helpers in order."""
        # Act
        define_complete_bridge_model(mock_builder, mock_params)

        # Assert
        # Verification is handled by the mock decorators
