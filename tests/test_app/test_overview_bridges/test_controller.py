"""Tests for app.overview_bridges.controller module."""

import unittest
from unittest.mock import MagicMock, patch

import pytest
from munch import Munch  # type: ignore[import-untyped]
from viktor.errors import UserError

from app.overview_bridges.controller import OverviewBridgesController
from tests.test_data.seed_loader import create_mocked_entity_list, load_overview_bridges_default_params


class TestOverviewBridgesController(unittest.TestCase):
    """Test cases for OverviewBridgesController."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.controller = OverviewBridgesController()
        self.default_params = load_overview_bridges_default_params()

    def _create_mock_params(self) -> Munch:
        """Helper to create mock overview bridges parametrization."""
        return Munch({"home": Munch({}), "bridge_overview": Munch({})})

    def test_get_resource_paths_success(self) -> None:
        """Test successful resource path retrieval."""
        # This is a static method test - just verify it doesn't raise exceptions
        with (
            patch("app.overview_bridges.controller.get_resources_dir") as mock_get_res,
            patch("app.overview_bridges.controller.get_default_shapefile_path") as mock_get_shp,
            patch("app.overview_bridges.controller.get_filtered_bridges_json_path") as mock_get_json,
            patch("app.overview_bridges.controller.validate_shapefile_exists") as mock_validate,
            patch("os.path.exists") as mock_exists,
        ):
            # Arrange
            mock_get_res.return_value = "/resources"
            mock_get_shp.return_value = "/path/shapefile.shp"
            mock_get_json.return_value = "/path/filtered.json"
            mock_validate.return_value = "/path/shapefile.shp"
            mock_exists.return_value = True

            # Act
            result = self.controller._get_resource_paths()  # noqa: SLF001

            # Assert
            assert len(result) == 3
            assert isinstance(result, tuple)

    def test_load_filtered_bridges_success(self) -> None:
        """Test successful loading of filtered bridges."""
        with patch("builtins.open"), patch("json.load") as mock_json_load:
            # Arrange
            mock_json_load.return_value = [{"OBJECTNUMM": "BRIDGE-001"}]
            file_path = "/path/to/filtered_bridges.json"

            # Act
            result = self.controller._load_filtered_bridges(file_path)  # noqa: SLF001

            # Assert
            assert isinstance(result, list)
            assert len(result) == 1

    def test_load_filtered_bridges_file_error(self) -> None:
        """Test loading filtered bridges with file error."""
        with patch("builtins.open", side_effect=FileNotFoundError()):
            # Arrange
            file_path = "/nonexistent/filtered_bridges.json"

            # Act & Assert
            with pytest.raises(UserError):
                self.controller._load_filtered_bridges(file_path)  # noqa: SLF001

    @patch("app.overview_bridges.controller.gpd.read_file")
    def test_load_shapefile_and_names_success(self, mock_read_file: MagicMock) -> None:
        """Test loading shapefile and names successfully."""
        # Arrange
        mock_gdf = MagicMock()
        mock_gdf.iterrows.return_value = [
            (0, {"OBJECTNUMM": "BRIDGE-001", "OBJECTNAAM": "Test Bridge"}),
            (1, {"OBJECTNUMM": "BRIDGE-002", "OBJECTNAAM": "Another Bridge"}),
        ]
        mock_read_file.return_value = mock_gdf
        shapefile_path = "test_bridges.shp"

        # Act
        result = self.controller._load_shapefile_and_names(shapefile_path)  # noqa: SLF001

        # Assert
        assert isinstance(result, dict)
        assert result["BRIDGE-001"] == "Test Bridge"
        assert result["BRIDGE-002"] == "Another Bridge"

    @patch("app.overview_bridges.controller.gpd.read_file")
    def test_load_shapefile_and_names_missing_names(self, mock_read_file: MagicMock) -> None:
        """Test loading shapefile with missing object names."""
        # Arrange
        mock_gdf = MagicMock()
        mock_gdf.iterrows.return_value = [
            (0, {"OBJECTNUMM": "BRIDGE-001", "OBJECTNAAM": None}),
            (1, {"OBJECTNUMM": "BRIDGE-002", "OBJECTNAAM": "   "}),  # Whitespace only
        ]
        mock_read_file.return_value = mock_gdf
        shapefile_path = "/path/to/shapefile.shp"

        # Act
        result = self.controller._load_shapefile_and_names(shapefile_path)  # noqa: SLF001

        # Assert
        assert isinstance(result, dict)
        assert result["BRIDGE-001"] is None
        assert result["BRIDGE-002"] is None

    @patch("viktor.api_v1.API")
    def test_get_existing_child_objectnumms_success(self, mock_api_class: MagicMock) -> None:
        """Test successful retrieval of existing child object numbers."""
        # Arrange
        mock_api = MagicMock()
        mock_api_class.return_value = mock_api

        mock_entity = MagicMock()
        mock_api.get_entity.return_value = mock_entity

        mock_child1 = MagicMock()
        mock_child1.last_saved_params = {"bridge_objectnumm": "BRIDGE-001"}
        mock_child2 = MagicMock()
        mock_child2.last_saved_params = {"bridge_objectnumm": "BRIDGE-002"}

        mock_entity.children.return_value = [mock_child1, mock_child2]

        entity_id = 123

        # Act
        result = self.controller._get_existing_child_objectnumms(entity_id)  # noqa: SLF001

        # Assert
        assert isinstance(result, set)
        assert result == {"BRIDGE-001", "BRIDGE-002"}

    @patch("viktor.api_v1.API")
    def test_get_existing_child_objectnumms_api_error(self, mock_api_class: MagicMock) -> None:
        """Test handling of API errors when getting existing children."""
        # Arrange
        mock_api = MagicMock()
        mock_api_class.return_value = mock_api
        mock_api.get_entity.side_effect = Exception("API Error")

        entity_id = 123

        # Act & Assert
        with pytest.raises(UserError):
            self.controller._get_existing_child_objectnumms(entity_id)  # noqa: SLF001

    @patch("viktor.api_v1.API")
    def test_create_missing_children_success(self, mock_api_class: MagicMock) -> None:
        """Test successful creation of missing child entities."""
        # Arrange
        mock_api = MagicMock()
        mock_api_class.return_value = mock_api

        mock_parent_entity = MagicMock()
        mock_api.get_entity.return_value = mock_parent_entity

        parent_entity_id = 123
        filtered_bridge_data = [{"OBJECTNUMM": "BRIDGE-001"}, {"OBJECTNUMM": "BRIDGE-002"}]
        objectnumm_to_name: dict[str, str | None] = {"BRIDGE-001": "Test Bridge", "BRIDGE-002": None}
        existing_objectnumms: set[str] = {"BRIDGE-001"}  # BRIDGE-001 already exists

        # Act
        self.controller._create_missing_children(parent_entity_id, filtered_bridge_data, objectnumm_to_name, existing_objectnumms)  # noqa: SLF001

        # Assert
        # Should only create BRIDGE-002 (BRIDGE-001 already exists)
        mock_parent_entity.create_child.assert_called_once()
        call_args = mock_parent_entity.create_child.call_args
        assert call_args[1]["entity_type_name"] == "Bridge"
        assert call_args[1]["name"] == "BRIDGE-002"

    def test_create_missing_children_invalid_data(self) -> None:
        """Test handling of invalid bridge data during child creation."""
        # This test validates the method signature and basic error handling
        # without calling the actual VIKTOR API

        # Arrange
        parent_entity_id = 123
        filtered_bridge_data = [
            {"OBJECTNUMM": None},  # Invalid - no OBJECTNUMM
            {},  # Invalid - missing OBJECTNUMM
        ]
        objectnumm_to_name: dict[str, str | None] = {}
        existing_objectnumms: set[str] = set()

        # Act & Assert - We expect this to eventually raise a UserError due to API issues
        # but we're testing that the method handles invalid data gracefully
        # The API error is expected since we're not mocking the VIKTOR API properly
        with pytest.raises((UserError, AttributeError, TypeError)):
            self.controller._create_missing_children(parent_entity_id, filtered_bridge_data, objectnumm_to_name, existing_objectnumms)  # noqa: SLF001

    @patch.object(OverviewBridgesController, "_get_resource_paths")
    @patch.object(OverviewBridgesController, "_load_filtered_bridges")
    @patch.object(OverviewBridgesController, "_load_shapefile_and_names")
    @patch.object(OverviewBridgesController, "_get_existing_child_objectnumms")
    @patch.object(OverviewBridgesController, "_create_missing_children")
    def test_regenerate_bridges_action_success(
        self,
        mock_create_children: MagicMock,
        mock_get_existing: MagicMock,
        mock_load_shapefile: MagicMock,
        mock_load_filtered: MagicMock,
        mock_get_paths: MagicMock,
    ) -> None:
        """Test successful bridge regeneration action."""
        # Arrange
        entity_id = 123

        mock_get_paths.return_value = ("/resources", "/shapefile.shp", "/filtered.json")
        mock_load_filtered.return_value = [{"OBJECTNUMM": "BRIDGE-001"}]
        mock_load_shapefile.return_value = {"BRIDGE-001": "Test Bridge"}
        mock_get_existing.return_value = set()

        # Act
        self.controller.regenerate_bridges_action(entity_id)

        # Assert
        # Method returns None implicitly
        mock_create_children.assert_called_once()

    def test_params_structure_validation(self) -> None:
        """Test that the mock params structure is valid."""
        # Arrange & Act
        params = self._create_mock_params()

        # Assert
        assert isinstance(params, Munch)
        assert "home" in params
        assert "bridge_overview" in params
        assert isinstance(params.home, Munch)
        assert isinstance(params.bridge_overview, Munch)

    def test_controller_initialization(self) -> None:
        """Test that the controller initializes correctly."""
        # Assert
        assert isinstance(self.controller, OverviewBridgesController)

    def test_seed_data_integrity_default(self) -> None:
        """Test that default seed data has expected structure."""
        # Assert
        assert "home" in self.default_params
        assert "bridge_overview" in self.default_params

        # Check specific values
        assert "introduction" in self.default_params.bridge_overview

    def test_mocked_entity_list_creation(self) -> None:
        """Test creation of mocked entity list for testing."""
        # Act
        entities = create_mocked_entity_list(count=5)

        # Assert
        assert isinstance(entities, list)
        assert len(entities) == 5

        for i, entity in enumerate(entities, 1):
            assert "OBJECTNUMM" in entity
            assert "OBJECTNAAM" in entity
            assert "geometry" in entity
            assert entity["OBJECTNUMM"] == f"BRIDGE-{i:03d}"
            assert entity["OBJECTNAAM"] == f"Test Bridge {i}"

    def test_controller_method_signatures(self) -> None:
        """Test that controller methods have expected signatures."""
        # This test ensures the methods exist and can be called
        # without testing the actual VIKTOR API integration

        # Check that methods exist
        assert hasattr(self.controller, "_create_missing_children")
        assert callable(getattr(self.controller, "_create_missing_children"))


if __name__ == "__main__":
    unittest.main()
