"""Tests for bridge Pydantic models."""

import unittest

import pytest
from pydantic import ValidationError

from src.data_models.bridge_models import BridgeSegmentDimensions


class TestBridgeSegmentDimensions(unittest.TestCase):
    """Test cases for BridgeSegmentDimensions Pydantic model."""

    def test_valid_dimensions_creation(self) -> None:
        """Test creating valid bridge segment dimensions."""
        dimensions = BridgeSegmentDimensions(bz1=3.5, bz2=2.0, bz3=1.5, segment_length=25.0)

        assert dimensions.bz1 == 3.5
        assert dimensions.bz2 == 2.0
        assert dimensions.bz3 == 1.5
        assert dimensions.segment_length == 25.0

    def test_zero_segment_length_valid(self) -> None:
        """Test that zero segment length is valid (first segment)."""
        dimensions = BridgeSegmentDimensions(bz1=3.5, bz2=2.0, bz3=1.5, segment_length=0.0)

        assert dimensions.segment_length == 0.0

    def test_negative_zone_widths_rejected(self) -> None:
        """Test that negative zone widths are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            BridgeSegmentDimensions(
                bz1=-1.0,  # type: ignore[arg-type]
                bz2=2.0,
                bz3=1.5,
                segment_length=25.0,
            )

        error = exc_info.value
        assert "bz1" in str(error)
        assert "greater than 0" in str(error)

    def test_zero_zone_widths_rejected(self) -> None:
        """Test that zero zone widths are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            BridgeSegmentDimensions(
                bz1=0.0,  # type: ignore[arg-type]
                bz2=2.0,
                bz3=1.5,
                segment_length=25.0,
            )

        error = exc_info.value
        assert "bz1" in str(error)
        assert "greater than 0" in str(error)

    def test_negative_segment_length_rejected(self) -> None:
        """Test that negative segment length is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            BridgeSegmentDimensions(
                bz1=3.5,
                bz2=2.0,
                bz3=1.5,
                segment_length=-5.0,  # type: ignore[arg-type]
            )

        error = exc_info.value
        assert "segment_length" in str(error)
        assert "greater than or equal to 0" in str(error)

    def test_zone_width_too_small_rejected(self) -> None:
        """Test that zone widths below 0.1m are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            BridgeSegmentDimensions(
                bz1=0.05,  # Too small
                bz2=2.0,
                bz3=1.5,
                segment_length=25.0,
            )

        error = exc_info.value
        assert "bz1" in str(error)
        assert "unrealistic" in str(error)
        assert "0.1m and 50m" in str(error)

    def test_zone_width_too_large_rejected(self) -> None:
        """Test that zone widths above 50m are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            BridgeSegmentDimensions(
                bz1=60.0,  # Too large
                bz2=2.0,
                bz3=1.5,
                segment_length=25.0,
            )

        error = exc_info.value
        assert "bz1" in str(error)
        assert "unrealistic" in str(error)
        assert "0.1m and 50m" in str(error)

    def test_segment_length_too_large_rejected(self) -> None:
        """Test that segment lengths above 200m are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            BridgeSegmentDimensions(
                bz1=3.5,
                bz2=2.0,
                bz3=1.5,
                segment_length=250.0,  # Too large
            )

        error = exc_info.value
        assert "segment_length" in str(error)
        assert "unrealistic" in str(error)
        assert "≤ 200m" in str(error)

    def test_boundary_values_valid(self) -> None:
        """Test that boundary values (0.1m, 50m, 200m) are valid."""
        # Minimum zone width
        dimensions = BridgeSegmentDimensions(bz1=0.1, bz2=0.1, bz3=0.1, segment_length=0.0)
        assert dimensions.bz1 == 0.1

        # Maximum zone width
        dimensions = BridgeSegmentDimensions(bz1=50.0, bz2=50.0, bz3=50.0, segment_length=200.0)
        assert dimensions.bz1 == 50.0
        assert dimensions.segment_length == 200.0

    def test_all_zone_widths_validated(self) -> None:
        """Test that all zone widths (bz1, bz2, bz3) are validated."""
        # Test bz2 validation
        with pytest.raises(ValidationError) as exc_info:
            BridgeSegmentDimensions(
                bz1=3.5,
                bz2=0.05,  # Too small
                bz3=1.5,
                segment_length=25.0,
            )

        error = exc_info.value
        assert "bz2" in str(error)

        # Test bz3 validation
        with pytest.raises(ValidationError) as exc_info:
            BridgeSegmentDimensions(
                bz1=3.5,
                bz2=2.0,
                bz3=60.0,  # Too large
                segment_length=25.0,
            )

        error = exc_info.value
        assert "bz3" in str(error)

    def test_validate_assignment_enabled(self) -> None:
        """Test that validation is enabled on assignment."""
        dimensions = BridgeSegmentDimensions(bz1=3.5, bz2=2.0, bz3=1.5, segment_length=25.0)

        # This should work
        dimensions.bz1 = 4.0
        assert dimensions.bz1 == 4.0

        # This should raise validation error
        with pytest.raises(ValidationError):
            dimensions.bz1 = 0.05  # Too small

    def test_model_config_settings(self) -> None:
        """Test that model configuration is properly set."""
        dimensions = BridgeSegmentDimensions(bz1=3.5, bz2=2.0, bz3=1.5, segment_length=25.0)

        # Check that validate_assignment is enabled
        with pytest.raises(ValidationError):
            dimensions.bz1 = 0.05

        # Check that model config values are set correctly
        assert dimensions.model_config["validate_assignment"] is True
        # use_enum_values removed - model doesn't use enums

    def test_realistic_bridge_scenarios(self) -> None:
        """Test realistic bridge dimension scenarios."""
        # Typical highway bridge
        highway_bridge = BridgeSegmentDimensions(
            bz1=3.5,  # Lane
            bz2=2.0,  # Shoulder
            bz3=1.0,  # Barrier
            segment_length=30.0,
        )
        assert highway_bridge.bz1 == 3.5

        # Narrow pedestrian bridge
        pedestrian_bridge = BridgeSegmentDimensions(
            bz1=2.0,  # Walkway
            bz2=0.5,  # Railing
            bz3=0.5,  # Railing
            segment_length=15.0,
        )
        assert pedestrian_bridge.bz1 == 2.0

        # Wide bridge with multiple lanes
        wide_bridge = BridgeSegmentDimensions(
            bz1=12.0,  # Multiple lanes
            bz2=3.0,  # Shoulder
            bz3=2.0,  # Barrier
            segment_length=50.0,
        )
        assert wide_bridge.bz1 == 12.0
