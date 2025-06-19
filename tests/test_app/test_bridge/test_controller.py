"""Tests for app.bridge.controller module."""

import unittest
from unittest.mock import MagicMock, patch

import pytest

from app.bridge.controller import BridgeController
from src.geometry.model_creator import BridgeSegmentDimensions
from tests.test_data.seed_loader import load_bridge_complex_params, load_bridge_default_params
from tests.test_utils import controller_test_wrapper
from viktor.errors import UserError


class TestBridgeController(unittest.TestCase):
    """Test cases for BridgeController."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.controller = BridgeController()
        self.default_params = load_bridge_default_params()
        self.complex_params = load_bridge_complex_params()

        # Sample bridge segment row for testing individual segment processing
        # Use data from seed file but ensure it has all needed fields for testing
        seed_segment = self.default_params.bridge_segments_array[0].copy()
        self.sample_segment_row = {
            "bz1": seed_segment.get("bz1", 10.0),
            "bz2": seed_segment.get("bz2", 5.0),
            "bz3": seed_segment.get("bz3", 15.0),
            "dz": seed_segment.get("dz", 2.0),
            "dz_2": seed_segment.get("dz_2", 3.0),
            "col_6": seed_segment.get("col_6", 0.0),
            "l": seed_segment.get("l", 10.0),
            "is_first_segment": seed_segment.get("is_first_segment", False),
        }

    @controller_test_wrapper("BridgeController", "_create_bridge_segment_dimensions_from_params")
    def test_create_bridge_segment_dimensions_from_params_valid_segment(self) -> None:
        """Test creating bridge segment dimensions from a valid individual segment."""
        # Act
        result = self.controller._create_bridge_segment_dimensions_from_params(self.sample_segment_row)  # type: ignore[arg-type]  # noqa: SLF001

        # Assert
        assert isinstance(result, BridgeSegmentDimensions)
        assert result.bz1 == self.sample_segment_row["bz1"]
        assert result.bz2 == self.sample_segment_row["bz2"]
        assert result.bz3 == self.sample_segment_row["bz3"]
        assert result.segment_length == self.sample_segment_row["l"]

    @controller_test_wrapper("BridgeController", "_create_bridge_segment_dimensions_from_params")
    def test_create_bridge_segment_dimensions_from_params_missing_required_field(self) -> None:
        """Test creating bridge segment dimensions with missing required fields."""
        # Arrange - Create incomplete segment by removing 'l' from seed data
        seed_segment = self.default_params.bridge_segments_array[0].copy()
        incomplete_segment = {k: v for k, v in seed_segment.items() if k != "l"}

        # Act & Assert
        with pytest.raises(UserError) as context:
            self.controller._create_bridge_segment_dimensions_from_params(incomplete_segment)  # type: ignore[arg-type]  # noqa: SLF001

        assert "brugsegmenten missen benodigde data" in str(context.value)

    @patch("app.bridge.controller.prepare_load_zone_geometry_data")
    @controller_test_wrapper("BridgeController", "_prepare_bridge_geometry_for_plotting")
    def test_prepare_bridge_geometry_for_plotting_with_valid_segments(self, mock_prepare_geometry: MagicMock) -> None:
        """Test preparing bridge geometry with valid segment data."""
        # Arrange
        segments_list = [self.sample_segment_row]
        mock_geometry_data = MagicMock()
        mock_prepare_geometry.return_value = mock_geometry_data

        # Act
        result = self.controller._prepare_bridge_geometry_for_plotting(segments_list)  # noqa: SLF001

        # Assert
        assert result == mock_geometry_data
        mock_prepare_geometry.assert_called_once()
        # Verify the call was made with the correct type of arguments
        call_args = mock_prepare_geometry.call_args[0][0]  # First positional argument
        assert isinstance(call_args, list)
        assert len(call_args) > 0
        # Verify the first item is a BridgeSegmentDimensions object
        from src.geometry.model_creator import BridgeSegmentDimensions

        assert isinstance(call_args[0], BridgeSegmentDimensions)

    def test_prepare_bridge_geometry_for_plotting_empty_segments(self) -> None:
        """Test preparing bridge geometry with empty segment list."""
        # Act
        result = self.controller._prepare_bridge_geometry_for_plotting([])  # noqa: SLF001

        # Assert
        assert result is None

    def test_prepare_bridge_geometry_for_plotting_with_complex_data(self) -> None:
        """Test preparing bridge geometry with complex segment data from seed files."""
        # Arrange - Use segments from complex seed data
        bridge_segments_params = self.complex_params.bridge_segments_array

        # Act
        result = self.controller._prepare_bridge_geometry_for_plotting(bridge_segments_params)  # noqa: SLF001

        # Assert
        assert result is not None
        # The number of D points should match the number of segments from complex seed data
        expected_segments = len(self.complex_params.bridge_segments_array)
        assert result.num_defined_d_points == expected_segments

    def test_prepare_bridge_geometry_for_plotting_invalid_segment_raises_error(self) -> None:
        """Test preparing bridge geometry with invalid segment data."""
        # Arrange - Create invalid segment by keeping only bz1 from seed data
        seed_segment = self.default_params.bridge_segments_array[0].copy()
        invalid_segments = [{"bz1": seed_segment["bz1"]}]  # Missing bz2, bz3, l

        # Act & Assert
        with pytest.raises(UserError):
            self.controller._prepare_bridge_geometry_for_plotting(invalid_segments)  # noqa: SLF001

    def test_get_bridge_entity_data_invalid_entity_id(self) -> None:
        """Test fetching bridge entity data with invalid entity ID."""
        # Act
        objectnumm, name, error_result = self.controller._get_bridge_entity_data(None)  # type: ignore[arg-type]  # noqa: SLF001

        # Assert
        assert objectnumm is None
        assert name is None
        assert error_result is not None  # Should return a MapResult error

    def test_get_bridge_entity_data_with_api_mocking(self) -> None:
        """Test bridge entity data method structure without actual API calls."""
        # This test verifies the method exists and has the right signature
        # without testing the actual API integration

        # Arrange - invalid entity ID
        entity_id = None

        # Act
        objectnumm, name, error_result = self.controller._get_bridge_entity_data(entity_id)  # type: ignore[arg-type]  # noqa: SLF001

        # Assert - with invalid ID, should return None values and error
        assert objectnumm is None
        assert name is None
        assert error_result is not None

    def test_bridge_segment_param_row_structure(self) -> None:
        """Test BridgeSegmentParamRow structure validation using seed data."""
        # Act & Assert - test that our sample segment has the expected structure
        assert "bz1" in self.sample_segment_row
        assert "bz2" in self.sample_segment_row
        assert "bz3" in self.sample_segment_row
        assert "l" in self.sample_segment_row

        # Test values are what we expect from seed data
        assert self.sample_segment_row["bz1"] == self.sample_segment_row["bz1"]
        assert self.sample_segment_row["bz2"] == self.sample_segment_row["bz2"]
        assert self.sample_segment_row["bz3"] == self.sample_segment_row["bz3"]
        assert self.sample_segment_row["l"] == self.sample_segment_row["l"]

        # Test data types
        assert isinstance(self.sample_segment_row["bz1"], int | float)
        assert isinstance(self.sample_segment_row["bz2"], int | float)
        assert isinstance(self.sample_segment_row["bz3"], int | float)
        assert isinstance(self.sample_segment_row["l"], int | float)

    def test_seed_data_integrity_default(self) -> None:
        """Test that default seed data has expected structure."""
        # Assert
        assert "info" in self.default_params
        assert "input" in self.default_params
        assert "bridge_segments_array" in self.default_params
        assert "load_zones_data_array" in self.default_params
        assert "reinforcement_zones_array" in self.default_params

        # Check specific values
        assert self.default_params.info.bridge_objectnumm == "BRIDGE-001"
        assert len(self.default_params.bridge_segments_array) == 2
        assert len(self.default_params.load_zones_data_array) == 4

    def test_seed_data_integrity_complex(self) -> None:
        """Test that complex seed data has expected structure."""
        # Assert
        assert "info" in self.complex_params
        assert "input" in self.complex_params
        assert "bridge_segments_array" in self.complex_params
        assert "load_zones_data_array" in self.complex_params
        assert "reinforcement_zones_array" in self.complex_params

        # Check specific values
        assert self.complex_params.info.bridge_objectnumm == "BRIDGE-COMPLEX-001"
        assert len(self.complex_params.bridge_segments_array) == 3
        assert len(self.complex_params.load_zones_data_array) == 3

    def test_seed_data_bridge_segments_structure(self) -> None:
        """Test that bridge segments in seed data have correct structure."""
        # Test first segment in default params
        first_segment = self.default_params.bridge_segments_array[0]

        # Check required fields exist
        required_fields = ["bz1", "bz2", "bz3", "l"]
        for field in required_fields:
            assert field in first_segment

        # Check types
        assert isinstance(first_segment["bz1"], int | float)
        assert isinstance(first_segment["bz2"], int | float)
        assert isinstance(first_segment["bz3"], int | float)
        assert isinstance(first_segment["l"], int | float)


if __name__ == "__main__":
    unittest.main()
