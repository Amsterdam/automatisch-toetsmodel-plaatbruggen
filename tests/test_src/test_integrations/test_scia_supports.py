"""
Tests for SCIA support creation functions.

This module tests the creation of SCIA support elements by mocking the SciaModelBuilder.
"""

from unittest.mock import Mock, call

import pytest

from src.integrations.scia_integration.scia_supports import create_all_supports, create_line_supports


@pytest.fixture
def mock_builder() -> Mock:
    """Fixture to provide a mocked SciaModelBuilder."""
    return Mock()


class TestCreateLineSupports:
    """Tests for the create_line_supports function."""

    def test_create_line_supports_basic(self, mock_builder: Mock) -> None:
        """Test basic creation of line supports at start and end of the bridge."""
        plate_names = ["Z1_1", "Z2_1", "Z3_1", "Z1_2", "Z2_2", "Z3_2"]
        create_line_supports(mock_builder, plate_names)

        assert mock_builder.create_line_support.call_count == 6

        # Check calls for start supports (edge 4 on first 3 plates)
        # last_section_number will be 3 (max span number is 2, so 2+1)
        expected_calls_start = [
            call(
                name="SLB_opleg_as_1:1",
                plane_name="Z1_1",
                edge_index=4,
                freedom={"x": "FLEXIBLE", "y": "FLEXIBLE", "z": "RIGID", "rx": "FREE", "ry": "RIGID", "rz": "RIGID"},
                stiffness={"stiffness_x": 1e7, "stiffness_y": 1e6},
            ),
            call(
                name="SLB_opleg_as_1:2",
                plane_name="Z2_1",
                edge_index=4,
                freedom={"x": "FLEXIBLE", "y": "FLEXIBLE", "z": "RIGID", "rx": "FREE", "ry": "RIGID", "rz": "RIGID"},
                stiffness={"stiffness_x": 1e7, "stiffness_y": 1e6},
            ),
            call(
                name="SLB_opleg_as_1:3",
                plane_name="Z3_1",
                edge_index=4,
                freedom={"x": "FLEXIBLE", "y": "FLEXIBLE", "z": "RIGID", "rx": "FREE", "ry": "RIGID", "rz": "RIGID"},
                stiffness={"stiffness_x": 1e7, "stiffness_y": 1e6},
            ),
        ]

        # Check calls for end supports (edge 2 on last 3 plates)
        expected_calls_end = [
            call(
                name="SLB_opleg_as_3:1",
                plane_name="Z1_2",
                edge_index=2,
                freedom={"x": "FLEXIBLE", "y": "FLEXIBLE", "z": "RIGID", "rx": "FREE", "ry": "RIGID", "rz": "RIGID"},
                stiffness={"stiffness_x": 1e7, "stiffness_y": 1e6},
            ),
            call(
                name="SLB_opleg_as_3:2",
                plane_name="Z2_2",
                edge_index=2,
                freedom={"x": "FLEXIBLE", "y": "FLEXIBLE", "z": "RIGID", "rx": "FREE", "ry": "RIGID", "rz": "RIGID"},
                stiffness={"stiffness_x": 1e7, "stiffness_y": 1e6},
            ),
            call(
                name="SLB_opleg_as_3:3",
                plane_name="Z3_2",
                edge_index=2,
                freedom={"x": "FLEXIBLE", "y": "FLEXIBLE", "z": "RIGID", "rx": "FREE", "ry": "RIGID", "rz": "RIGID"},
                stiffness={"stiffness_x": 1e7, "stiffness_y": 1e6},
            ),
        ]

        mock_builder.create_line_support.assert_has_calls(expected_calls_start, any_order=False)
        mock_builder.create_line_support.assert_has_calls(expected_calls_end, any_order=False)

    def test_no_plates_returns_empty_list(self, mock_builder: Mock) -> None:
        """Test that an empty list is returned and no supports are created if no plates are provided."""
        result = create_line_supports(mock_builder, [])
        assert result == []
        mock_builder.create_line_support.assert_not_called()

    def test_single_span_bridge(self, mock_builder: Mock) -> None:
        """Test with a single span bridge (less than 6 plates)."""
        plate_names = ["Z1_1", "Z2_1", "Z3_1"]
        create_line_supports(mock_builder, plate_names)

        # Should still create start and end supports on the same plates
        assert mock_builder.create_line_support.call_count == 6
        mock_builder.create_line_support.assert_any_call(name="SLB_opleg_as_1:1", plane_name="Z1_1", edge_index=4)
        # last_section_number will be 2
        mock_builder.create_line_support.assert_any_call(name="SLB_opleg_as_2:1", plane_name="Z1_1", edge_index=2)


class TestCreateAllSupports:
    """Tests for the create_all_supports function."""

    @pytest.fixture
    def mock_create_line(self) -> Mock:
        """Fixture to provide a mocked create_line_supports function."""
        return Mock()

    @patch("src.integrations.scia_integration.scia_supports.create_line_supports")
    def test_create_all_supports_orchestration(self, mock_create_line: Mock, mock_builder: Mock) -> None:
        """Test that the main support function calls the line support helper."""
        plate_names = ["plate1", "plate2"]
        mock_line_support = Mock()
        mock_create_line.return_value = [mock_line_support]

        all_supports = create_all_supports(mock_builder, plate_names)

        mock_create_line.assert_called_once_with(mock_builder, plate_names)
        assert all_supports == [mock_line_support]
        # Add asserts for other support types when they are added 