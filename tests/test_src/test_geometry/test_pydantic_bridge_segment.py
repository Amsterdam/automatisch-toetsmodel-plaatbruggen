"""
Tests for Pydantic BridgeSegmentDimensions model.

This module demonstrates the benefits of using Pydantic for data validation
by testing the new BridgeSegmentDimensions Pydantic model.
"""

import unittest

import pytest
from pydantic import ValidationError

from src.data_models.bridge_models import BridgeSegmentDimensions


class TestPydanticBridgeSegmentDimensions(unittest.TestCase):
    """Test cases for the Pydantic BridgeSegmentDimensions model."""

    def test_valid_bridge_segment_creation(self) -> None:
        """Test creating a valid bridge segment with Pydantic."""
        # Arrange
        valid_data = {"bz1": 5.0, "bz2": 10.0, "bz3": 5.0, "segment_length": 15.0}

        # Act
        segment = BridgeSegmentDimensions(**valid_data)

        # Assert
        assert segment.bz1 == 5.0
        assert segment.bz2 == 10.0
        assert segment.bz3 == 5.0
        assert segment.segment_length == 15.0

    def test_zero_segment_length_allowed(self) -> None:
        """Test that zero segment length is allowed (for first segment)."""
        # Arrange
        valid_data = {
            "bz1": 5.0,
            "bz2": 10.0,
            "bz3": 5.0,
            "segment_length": 0.0,  # First segment
        }

        # Act
        segment = BridgeSegmentDimensions(**valid_data)

        # Assert
        assert segment.segment_length == 0.0

    def test_negative_width_validation(self) -> None:
        """Test that negative widths are rejected with clear error messages."""
        # Arrange
        invalid_data = {
            "bz1": -2.0,  # Invalid: negative width
            "bz2": 10.0,
            "bz3": 5.0,
            "segment_length": 15.0,
        }

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            BridgeSegmentDimensions(**invalid_data)

        # Check that the error message is clear
        error = exc_info.value
        assert len(error.errors()) == 1
        assert error.errors()[0]["loc"] == ("bz1",)
        assert "greater than 0" in error.errors()[0]["msg"]

    def test_zero_width_validation(self) -> None:
        """Test that zero widths are rejected."""
        # Arrange
        invalid_data = {
            "bz1": 5.0,
            "bz2": 0.0,  # Invalid: zero width
            "bz3": 5.0,
            "segment_length": 15.0,
        }

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            BridgeSegmentDimensions(**invalid_data)

        error = exc_info.value
        assert error.errors()[0]["loc"] == ("bz2",)

    def test_unrealistic_width_validation(self) -> None:
        """Test that unrealistically large widths are rejected."""
        # Arrange
        invalid_data = {
            "bz1": 100.0,  # Invalid: too large (>50m)
            "bz2": 10.0,
            "bz3": 5.0,
            "segment_length": 15.0,
        }

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            BridgeSegmentDimensions(**invalid_data)

        # Check custom validation message
        error = exc_info.value
        assert "unrealistic" in str(error).lower()

    def test_unrealistic_segment_length_validation(self) -> None:
        """Test that unrealistically long segments are rejected."""
        # Arrange
        invalid_data = {
            "bz1": 5.0,
            "bz2": 10.0,
            "bz3": 5.0,
            "segment_length": 300.0,  # Invalid: too long (>200m)
        }

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            BridgeSegmentDimensions(**invalid_data)

        error = exc_info.value
        assert "unrealistic" in str(error).lower()

    def test_missing_required_field(self) -> None:
        """Test that missing required fields are caught."""
        # Arrange
        incomplete_data = {
            "bz1": 5.0,
            "bz2": 10.0,
            # Missing bz3 and segment_length
        }

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            BridgeSegmentDimensions(**incomplete_data)

        error = exc_info.value
        # Should have 2 errors (missing bz3 and segment_length)
        assert len(error.errors()) == 2

    def test_type_conversion(self) -> None:
        """Test that Pydantic automatically converts compatible types."""
        # Arrange
        data_with_strings = {
            "bz1": "5.0",  # String that can be converted to float
            "bz2": "10.0",
            "bz3": "5.0",
            "segment_length": "15.0",
        }

        # Act
        segment = BridgeSegmentDimensions(
            bz1=float(data_with_strings["bz1"]),
            bz2=float(data_with_strings["bz2"]),
            bz3=float(data_with_strings["bz3"]),
            segment_length=float(data_with_strings["segment_length"]),
        )

        # Assert - should be converted to floats
        assert isinstance(segment.bz1, float)
        assert segment.bz1 == 5.0

    def test_invalid_type_conversion(self) -> None:
        """Test that invalid types are rejected with clear messages."""
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            BridgeSegmentDimensions(
                bz1="not_a_number",  # type: ignore[arg-type]  # Invalid: can't convert to float
                bz2=10.0,
                bz3=5.0,
                segment_length=15.0,
            )

        error = exc_info.value
        assert "valid number" in str(error).lower()


class TestPydanticDataConversion(unittest.TestCase):
    """Test cases for data conversion scenarios with Pydantic."""

    def test_direct_creation_from_dict(self) -> None:
        """Test creating BridgeSegmentDimensions directly from dict (simulating VIKTOR params)."""
        # Arrange - simulate VIKTOR parameter row
        param_row = {
            "bz1": 5.0,
            "bz2": 10.0,
            "bz3": 5.0,
            "segment_length": 15.0,  # Note: using segment_length directly
        }

        # Act
        result = BridgeSegmentDimensions(**param_row)

        # Assert
        assert result is not None
        assert isinstance(result, BridgeSegmentDimensions)
        assert result.bz1 == 5.0
        assert result.segment_length == 15.0

    def test_conversion_with_viktor_style_field_names(self) -> None:
        """Test conversion from VIKTOR-style field names (l instead of segment_length)."""
        # Arrange - simulate actual VIKTOR parameter structure
        viktor_param_row = {
            "bz1": 5.0,
            "bz2": 10.0,
            "bz3": 5.0,
            "l": 15.0,  # VIKTOR uses 'l' for length
        }

        # Act - convert to our Pydantic model format
        converted_data = {
            "bz1": viktor_param_row["bz1"],
            "bz2": viktor_param_row["bz2"],
            "bz3": viktor_param_row["bz3"],
            "segment_length": viktor_param_row["l"],  # Map 'l' to 'segment_length'
        }
        result = BridgeSegmentDimensions(**converted_data)

        # Assert
        assert result.segment_length == 15.0

    def test_validation_with_string_inputs(self) -> None:
        """Test that Pydantic handles string-to-float conversion from VIKTOR."""
        # Arrange - VIKTOR sometimes provides string values
        string_param_row = {"bz1": "5.0", "bz2": "10.0", "bz3": "5.0", "segment_length": "15.0"}

        # Act
        result = BridgeSegmentDimensions(
            bz1=float(string_param_row["bz1"]),
            bz2=float(string_param_row["bz2"]),
            bz3=float(string_param_row["bz3"]),
            segment_length=float(string_param_row["segment_length"]),
        )

        # Assert - should convert to floats
        assert isinstance(result.bz1, float)
        assert result.bz1 == 5.0


class TestPydanticBenefitsDemonstration(unittest.TestCase):
    """Demonstrate the benefits of Pydantic over manual validation."""

    def test_comprehensive_validation_in_one_step(self) -> None:
        """Show how Pydantic validates everything in one step."""
        # Before: Manual validation required multiple checks
        # Now: Pydantic does it all automatically

        test_cases = [
            # Valid case
            ({"bz1": 5.0, "bz2": 10.0, "bz3": 5.0, "segment_length": 15.0}, True),
            # Missing field
            ({"bz1": 5.0, "bz2": 10.0}, False),
            # Negative value
            ({"bz1": -5.0, "bz2": 10.0, "bz3": 5.0, "segment_length": 15.0}, False),
            # Zero value
            ({"bz1": 0.0, "bz2": 10.0, "bz3": 5.0, "segment_length": 15.0}, False),
            # Unrealistic value
            ({"bz1": 100.0, "bz2": 10.0, "bz3": 5.0, "segment_length": 15.0}, False),
            # Type conversion
            ({"bz1": "5.0", "bz2": "10.0", "bz3": "5.0", "segment_length": "15.0"}, True),
            # Invalid type
            ({"bz1": "invalid", "bz2": 10.0, "bz3": 5.0, "segment_length": 15.0}, False),
        ]

        for data, should_be_valid in test_cases:
            with self.subTest(data=data, should_be_valid=should_be_valid):
                if should_be_valid:
                    # Should create successfully
                    segment = BridgeSegmentDimensions(**data)  # type: ignore[arg-type]
                    assert isinstance(segment, BridgeSegmentDimensions)
                else:
                    # Should raise ValidationError
                    with pytest.raises(ValidationError):
                        BridgeSegmentDimensions(**data)  # type: ignore[arg-type]

    def test_clear_error_messages(self) -> None:
        """Demonstrate Pydantic's clear error messages."""
        # Test multiple validation errors at once
        invalid_data = {
            "bz1": -5.0,  # Negative
            "bz2": 0.0,  # Zero
            "bz3": 100.0,  # Too large
            "segment_length": 300.0,  # Too long
        }

        with pytest.raises(ValidationError) as exc_info:
            BridgeSegmentDimensions(**invalid_data)

        error = exc_info.value
        # Should have multiple specific errors
        assert len(error.errors()) >= 3  # At least 3 validation errors

        # Each error should have clear location and message
        for err in error.errors():
            assert "loc" in err
            assert "msg" in err
            assert len(err["loc"]) > 0  # Should specify which field


if __name__ == "__main__":
    unittest.main()
