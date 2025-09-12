"""Tests for geometry Pydantic models."""

import unittest

import pytest
from pydantic import ValidationError

from src.data_models.geometry_models import TheoreticalLaneResult


class TestTheoreticalLaneResult(unittest.TestCase):
    """Test cases for TheoreticalLaneResult Pydantic model."""

    def test_valid_lane_result_creation(self) -> None:
        """Test creating valid theoretical lane result."""
        result = TheoreticalLaneResult(num_lanes=2, lane_width=3.5, rest_width=1.0, total_lanes_width=7.0)

        assert result.num_lanes == 2
        assert result.lane_width == 3.5
        assert result.rest_width == 1.0
        assert result.total_lanes_width == 7.0

    def test_zero_lanes_valid(self) -> None:
        """Test that zero lanes is valid (very narrow bridges)."""
        result = TheoreticalLaneResult(num_lanes=0, lane_width=3.5, rest_width=5.0, total_lanes_width=0.0)

        assert result.num_lanes == 0
        assert result.total_lanes_width == 0.0

    def test_maximum_lanes_valid(self) -> None:
        """Test that maximum number of lanes (10) is valid."""
        result = TheoreticalLaneResult(num_lanes=10, lane_width=3.5, rest_width=0.0, total_lanes_width=35.0)

        assert result.num_lanes == 10
        assert result.total_lanes_width == 35.0

    def test_negative_lanes_rejected(self) -> None:
        """Test that negative number of lanes is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            TheoreticalLaneResult(
                num_lanes=-1,  # type: ignore[arg-type]
                lane_width=3.5,
                rest_width=1.0,
                total_lanes_width=7.0,
            )

        error = exc_info.value
        assert "num_lanes" in str(error)
        assert "greater than or equal to 0" in str(error)

    def test_too_many_lanes_rejected(self) -> None:
        """Test that more than 10 lanes is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            TheoreticalLaneResult(
                num_lanes=11,  # type: ignore[arg-type]
                lane_width=3.5,
                rest_width=1.0,
                total_lanes_width=38.5,
            )

        error = exc_info.value
        assert "num_lanes" in str(error)
        assert "less than or equal to 10" in str(error)

    def test_lane_width_too_narrow_rejected(self) -> None:
        """Test that lane width below 2.5m is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            TheoreticalLaneResult(
                num_lanes=2,
                lane_width=2.0,  # Too narrow
                rest_width=1.0,
                total_lanes_width=4.0,
            )

        error = exc_info.value
        assert "lane_width" in str(error)
        assert "greater than or equal to 2.5" in str(error)

    def test_lane_width_too_wide_rejected(self) -> None:
        """Test that lane width above 4.0m is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            TheoreticalLaneResult(
                num_lanes=2,
                lane_width=4.5,  # Too wide
                rest_width=1.0,
                total_lanes_width=9.0,
            )

        error = exc_info.value
        assert "lane_width" in str(error)
        assert "less than or equal to 4" in str(error)

    def test_negative_rest_width_rejected(self) -> None:
        """Test that negative rest width is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            TheoreticalLaneResult(
                num_lanes=2,
                lane_width=3.5,
                rest_width=-0.5,  # type: ignore[arg-type]
                total_lanes_width=7.0,
            )

        error = exc_info.value
        assert "rest_width" in str(error)
        assert "greater than or equal to 0" in str(error)

    def test_negative_total_lanes_width_rejected(self) -> None:
        """Test that negative total lanes width is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            TheoreticalLaneResult(
                num_lanes=2,
                lane_width=3.5,
                rest_width=1.0,
                total_lanes_width=-1.0,  # type: ignore[arg-type]
            )

        error = exc_info.value
        assert "total_lanes_width" in str(error)
        assert "greater than or equal to 0" in str(error)

    def test_total_width_consistency_validation(self) -> None:
        """Test that total lanes width must match num_lanes x lane_width."""
        # Correct calculation
        result = TheoreticalLaneResult(
            num_lanes=3,
            lane_width=3.5,
            rest_width=0.5,
            total_lanes_width=10.5,  # 3 * 3.5 = 10.5
        )
        assert result.total_lanes_width == 10.5

        # Incorrect calculation - should be rejected
        with pytest.raises(ValidationError) as exc_info:
            TheoreticalLaneResult(
                num_lanes=3,
                lane_width=3.5,
                rest_width=0.5,
                total_lanes_width=10.0,  # Should be 10.5
            )

        error = exc_info.value
        assert "total_lanes_width" in str(error)
        assert "doesn't match" in str(error)
        assert "num_lanes x lane_width" in str(error)

    def test_floating_point_tolerance(self) -> None:
        """Test that small floating point differences are tolerated."""
        # Should work with small difference (within 0.01 tolerance)
        result = TheoreticalLaneResult(
            num_lanes=2,
            lane_width=3.5,
            rest_width=1.0,
            total_lanes_width=7.005,  # 2 * 3.5 = 7.0, difference = 0.005 < 0.01
        )
        assert result.total_lanes_width == 7.005

        # Should fail with larger difference
        with pytest.raises(ValidationError) as exc_info:
            TheoreticalLaneResult(
                num_lanes=2,
                lane_width=3.5,
                rest_width=1.0,
                total_lanes_width=7.02,  # Difference = 0.02 > 0.01
            )

        error = exc_info.value
        assert "total_lanes_width" in str(error)
        assert "doesn't match" in str(error)

    def test_boundary_values_valid(self) -> None:
        """Test that boundary values are valid."""
        # Minimum lane width
        result = TheoreticalLaneResult(num_lanes=1, lane_width=2.5, rest_width=0.0, total_lanes_width=2.5)
        assert result.lane_width == 2.5

        # Maximum lane width
        result = TheoreticalLaneResult(num_lanes=1, lane_width=4.0, rest_width=0.0, total_lanes_width=4.0)
        assert result.lane_width == 4.0

    def test_realistic_scenarios(self) -> None:
        """Test realistic bridge lane scenarios."""
        # Standard 2-lane highway
        highway_2_lane = TheoreticalLaneResult(num_lanes=2, lane_width=3.5, rest_width=2.0, total_lanes_width=7.0)
        assert highway_2_lane.num_lanes == 2
        assert highway_2_lane.total_lanes_width == 7.0

        # Narrow single lane bridge
        narrow_bridge = TheoreticalLaneResult(num_lanes=1, lane_width=3.0, rest_width=0.5, total_lanes_width=3.0)
        assert narrow_bridge.num_lanes == 1
        assert narrow_bridge.total_lanes_width == 3.0

        # Wide multi-lane bridge
        wide_bridge = TheoreticalLaneResult(num_lanes=4, lane_width=3.5, rest_width=1.0, total_lanes_width=14.0)
        assert wide_bridge.num_lanes == 4
        assert wide_bridge.total_lanes_width == 14.0

    def test_zero_lanes_with_nonzero_width_rejected(self) -> None:
        """Test that zero lanes with nonzero total width is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            TheoreticalLaneResult(
                num_lanes=0,
                lane_width=3.5,
                rest_width=1.0,
                total_lanes_width=1.0,  # Should be 0.0
            )

        error = exc_info.value
        assert "total_lanes_width" in str(error)
        assert "doesn't match" in str(error)
        assert "0 x 3.5 = 0.0" in str(error)

    def test_validation_error_message_format(self) -> None:
        """Test that validation error messages are clear and informative."""
        with pytest.raises(ValidationError) as exc_info:
            TheoreticalLaneResult(
                num_lanes=2,
                lane_width=3.5,
                rest_width=1.0,
                total_lanes_width=8.0,  # Should be 7.0
            )

        error_msg = str(exc_info.value)
        assert "Total lanes width 8.0m doesn't match" in error_msg
        assert "num_lanes x lane_width = 2 x 3.5 = 7.0m" in error_msg
