"""Tests for SCIA integration Pydantic models."""

import unittest

import pytest
from pydantic import ValidationError

from src.data_models.scia_models import AmsterdamWheelLoadConfig, BridgeDimensionsData, UdlLoadCaseData, WheelLoadConfig
from src.integrations.scia_integration.model.scia_section_on_plane import Span


class TestWheelLoadConfig(unittest.TestCase):
    """Test cases for WheelLoadConfig Pydantic model."""

    def test_valid_wheel_config_creation(self) -> None:
        """Test creating valid wheel load configuration."""
        config = WheelLoadConfig(
            position="front", side="left", corners_key="front_left_corner", load=50.0, axle_locations={"axle1": [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0)]}
        )

        assert config.position == "front"
        assert config.side == "left"
        assert config.corners_key == "front_left_corner"
        assert config.load == 50.0
        assert config.axle_locations == {"axle1": [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0)]}

    def test_position_validation(self) -> None:
        """Test wheel position validation."""
        # Valid positions
        valid_positions = ["front", "rear", "middle", "front_left", "front_right", "rear_left", "rear_right"]

        for position in valid_positions:
            config = WheelLoadConfig(position=position, side="left", corners_key="test", load=50.0, axle_locations={"axle1": [(0.0, 0.0, 0.0)]})
            assert config.position == position.lower()

        # Invalid position
        with pytest.raises(ValidationError) as exc_info:
            WheelLoadConfig(position="invalid_position", side="left", corners_key="test", load=50.0, axle_locations={"axle1": [(0.0, 0.0, 0.0)]})

        error = exc_info.value
        assert "Position 'invalid_position' not allowed" in str(error)

    def test_side_validation(self) -> None:
        """Test wheel side validation."""
        # Valid sides
        for side in ["left", "right"]:
            config = WheelLoadConfig(position="front", side=side, corners_key="test", load=50.0, axle_locations={"axle1": [(0.0, 0.0, 0.0)]})
            assert config.side == side.lower()

        # Invalid side
        with pytest.raises(ValidationError) as exc_info:
            WheelLoadConfig(position="front", side="center", corners_key="test", load=50.0, axle_locations={"axle1": [(0.0, 0.0, 0.0)]})

        error = exc_info.value
        assert "Side 'center' not allowed" in str(error)

    def test_load_validation(self) -> None:
        """Test load validation."""
        # Valid loads
        config = WheelLoadConfig(
            position="front",
            side="left",
            corners_key="test",
            load=100.0,  # Valid load
            axle_locations={"axle1": [(0.0, 0.0, 0.0)]},
        )
        assert config.load == 100.0

        # Invalid loads
        with pytest.raises(ValidationError) as exc_info:
            WheelLoadConfig(
                position="front",
                side="left",
                corners_key="test",
                load=0.0,  # Too small
                axle_locations={"axle1": [(0.0, 0.0, 0.0)]},
            )

        error = exc_info.value
        assert "load" in str(error)
        assert "greater than 0" in str(error)

        with pytest.raises(ValidationError) as exc_info:
            WheelLoadConfig(
                position="front",
                side="left",
                corners_key="test",
                load=250.0,  # Too large
                axle_locations={"axle1": [(0.0, 0.0, 0.0)]},
            )

        error = exc_info.value
        assert "load" in str(error)
        assert "less than or equal to 200" in str(error)

    def test_axle_locations_validation(self) -> None:
        """Test axle locations validation."""
        # Valid axle locations
        config = WheelLoadConfig(
            position="front",
            side="left",
            corners_key="test",
            load=50.0,
            axle_locations={"axle1": [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0)], "axle2": [(2.0, 0.0, 0.0)]},
        )
        assert len(config.axle_locations) == 2

        # Empty axle locations
        with pytest.raises(ValidationError) as exc_info:
            WheelLoadConfig(
                position="front",
                side="left",
                corners_key="test",
                load=50.0,
                axle_locations={"axle1": []},  # Empty
            )

        error = exc_info.value
        assert "Axle 'axle1' must have at least one coordinate" in str(error)

        # Invalid coordinate dimensions
        with pytest.raises(ValidationError) as exc_info:
            WheelLoadConfig(
                position="front",
                side="left",
                corners_key="test",
                load=50.0,
                axle_locations={"axle1": [(0.0, 0.0)]},  # type: ignore[list-item] # Only 2 coordinates, should be 3
            )

        error = exc_info.value
        assert "Field required" in str(error)

        # Unrealistic coordinates
        with pytest.raises(ValidationError) as exc_info:
            WheelLoadConfig(
                position="front",
                side="left",
                corners_key="test",
                load=50.0,
                axle_locations={"axle1": [(2000.0, 0.0, 0.0)]},  # X too large
            )

        error = exc_info.value
        assert "x-coordinate 2000.0 is unrealistic" in str(error)


class TestAmsterdamWheelLoadConfig(unittest.TestCase):
    """Test cases for AmsterdamWheelLoadConfig Pydantic model."""

    def test_valid_amsterdam_config_creation(self) -> None:
        """Test creating valid Amsterdam wheel load configuration."""
        config = AmsterdamWheelLoadConfig(position="front", corners_key="front_corner", load=75.0)

        assert config.position == "front"
        assert config.corners_key == "front_corner"
        assert config.load == 75.0

    def test_amsterdam_position_validation(self) -> None:
        """Test Amsterdam-specific position validation."""
        # Valid positions (more restrictive than WheelLoadConfig)
        valid_positions = ["front", "rear", "middle"]

        for position in valid_positions:
            config = AmsterdamWheelLoadConfig(position=position, corners_key="test", load=50.0)
            assert config.position == position.lower()

        # Invalid position
        with pytest.raises(ValidationError) as exc_info:
            AmsterdamWheelLoadConfig(
                position="front_left",  # Not allowed in Amsterdam config
                corners_key="test",
                load=50.0,
            )

        error = exc_info.value
        assert "Position 'front_left' not allowed" in str(error)

    def test_amsterdam_load_validation(self) -> None:
        """Test Amsterdam-specific load validation."""
        # Valid loads (Amsterdam has stricter limits)
        config = AmsterdamWheelLoadConfig(
            position="front",
            corners_key="test",
            load=100.0,  # Valid Amsterdam load
        )
        assert config.load == 100.0

        # Load too light
        with pytest.raises(ValidationError) as exc_info:
            AmsterdamWheelLoadConfig(
                position="front",
                corners_key="test",
                load=5.0,  # Too light for Amsterdam traffic
            )

        error = exc_info.value
        assert "Load 5.0kN is too light for Amsterdam traffic" in str(error)

        # Load too heavy
        with pytest.raises(ValidationError) as exc_info:
            AmsterdamWheelLoadConfig(
                position="front",
                corners_key="test",
                load=160.0,  # Exceeds Amsterdam limits
            )

        error = exc_info.value
        assert "Load 160.0kN exceeds Amsterdam traffic limits" in str(error)


class TestBridgeDimensionsData(unittest.TestCase):
    """Test cases for BridgeDimensionsData Pydantic model."""

    def test_valid_bridge_dimensions_creation(self) -> None:
        """Test creating valid bridge dimensions."""
        dimensions = BridgeDimensionsData(
            total_length=50.0,
            total_width=12.0,
            thickness=0.3,
            zone1_width=3.5,
            zone2_width=2.0,
            zone3_width=1.5,
            first_segment_thickness=0.3,
            first_segment_thickness_2=0.3,  # Must equal first_segment_thickness
        )

        assert dimensions.total_length == 50.0
        assert dimensions.total_width == 12.0
        assert dimensions.thickness == 0.3
        assert dimensions.zone1_width == 3.5
        assert dimensions.zone2_width == 2.0
        assert dimensions.zone3_width == 1.5
        assert dimensions.first_segment_thickness == 0.3
        assert dimensions.first_segment_thickness_2 == 0.3

    def test_zone_widths_property(self) -> None:
        """Test zone_widths property for backward compatibility."""
        dimensions = BridgeDimensionsData(
            total_length=50.0,
            total_width=12.0,
            thickness=0.3,
            zone1_width=3.5,
            zone2_width=2.0,
            zone3_width=1.5,
            first_segment_thickness=0.3,
            first_segment_thickness_2=0.3,  # Must equal first_segment_thickness
        )

        zone_widths = dimensions.zone_widths
        assert zone_widths == {"bz1": 3.5, "bz2": 2.0, "bz3": 1.5}

    def test_dimension_validation(self) -> None:
        """Test dimension validation."""
        # Valid dimensions
        dimensions = BridgeDimensionsData(
            total_length=100.0,  # Valid length
            total_width=20.0,  # Valid width
            thickness=0.5,  # Valid thickness
            zone1_width=5.0,  # Valid zone width
            zone2_width=3.0,
            zone3_width=2.0,
            first_segment_thickness=0.5,
            first_segment_thickness_2=0.5,  # Must equal first_segment_thickness
        )
        assert dimensions.total_length == 100.0

        # Invalid dimensions
        with pytest.raises(ValidationError) as exc_info:
            BridgeDimensionsData(
                total_length=-10.0,  # Negative length
                total_width=20.0,
                thickness=0.5,
                zone1_width=5.0,
                zone2_width=3.0,
                zone3_width=2.0,
                first_segment_thickness=0.5,
                first_segment_thickness_2=0.5,
            )

        error = exc_info.value
        assert "total_length" in str(error)
        assert "greater than 0" in str(error)

    def test_thickness_validation(self) -> None:
        """Test thickness validation."""
        # Valid thickness
        dimensions = BridgeDimensionsData(
            total_length=50.0,
            total_width=12.0,
            thickness=0.2,  # Valid thickness
            zone1_width=3.5,
            zone2_width=2.0,
            zone3_width=1.5,
            first_segment_thickness=0.2,
            first_segment_thickness_2=0.2,  # Must equal first_segment_thickness
        )
        assert dimensions.thickness == 0.2

        # Thickness too thin
        with pytest.raises(ValidationError) as exc_info:
            BridgeDimensionsData(
                total_length=50.0,
                total_width=12.0,
                thickness=0.05,  # Too thin
                zone1_width=3.5,
                zone2_width=2.0,
                zone3_width=1.5,
                first_segment_thickness=0.05,
                first_segment_thickness_2=0.05,
            )

        error = exc_info.value
        assert "thickness" in str(error)
        assert "greater than 0.1" in str(error)

    def test_zone_width_validation(self) -> None:
        """Test zone width validation."""
        # Valid zone widths
        dimensions = BridgeDimensionsData(
            total_length=50.0,
            total_width=12.0,
            thickness=0.3,
            zone1_width=0.5,  # Valid minimum width
            zone2_width=1.0,
            zone3_width=0.5,
            first_segment_thickness=0.3,
            first_segment_thickness_2=0.3,  # Must equal first_segment_thickness
        )
        assert dimensions.zone1_width == 0.5

        # Zone width too narrow
        with pytest.raises(ValidationError) as exc_info:
            BridgeDimensionsData(
                total_length=50.0,
                total_width=12.0,
                thickness=0.3,
                zone1_width=0.05,  # Too narrow
                zone2_width=1.0,
                zone3_width=0.5,
                first_segment_thickness=0.3,
                first_segment_thickness_2=0.3,
            )

        error = exc_info.value
        assert "zone1_width" in str(error)
        assert "too narrow (minimum 0.1m)" in str(error)

    def test_thickness_consistency_validation(self) -> None:
        """Test thickness validation - zones can have different thicknesses in cross-section."""
        # Valid: zones have the same thickness
        dimensions = BridgeDimensionsData(
            total_length=50.0,
            total_width=12.0,
            thickness=0.7,
            zone1_width=3.5,
            zone2_width=2.0,
            zone3_width=1.5,
            first_segment_thickness=0.7,  # Zones 1 and 3
            first_segment_thickness_2=0.7,  # Zone 2
        )
        assert dimensions.first_segment_thickness == 0.7
        assert dimensions.first_segment_thickness_2 == 0.7

        # Valid: zone 2 thicker than zones 1 and 3 (allowed in cross-section)
        dimensions_thick_zone2 = BridgeDimensionsData(
            total_length=50.0,
            total_width=12.0,
            thickness=0.7,
            zone1_width=3.5,
            zone2_width=2.0,
            zone3_width=1.5,
            first_segment_thickness=0.7,  # Zones 1 and 3
            first_segment_thickness_2=0.8,  # Zone 2 (thicker) - VALID
        )
        assert dimensions_thick_zone2.first_segment_thickness == 0.7
        assert dimensions_thick_zone2.first_segment_thickness_2 == 0.8

        # Valid: zone 2 thinner than zones 1 and 3 (allowed in cross-section)
        dimensions_thin_zone2 = BridgeDimensionsData(
            total_length=50.0,
            total_width=12.0,
            thickness=0.3,
            zone1_width=3.5,
            zone2_width=2.0,
            zone3_width=1.5,
            first_segment_thickness=0.3,  # Zones 1 and 3
            first_segment_thickness_2=0.2,  # Zone 2 (thinner) - VALID
        )
        assert dimensions_thin_zone2.first_segment_thickness == 0.3
        assert dimensions_thin_zone2.first_segment_thickness_2 == 0.2

    def test_total_width_consistency_validation(self) -> None:
        """Test total width consistency validation."""
        # Valid width relationship
        dimensions = BridgeDimensionsData(
            total_length=50.0,
            total_width=10.0,  # Total width
            thickness=0.3,
            zone1_width=3.0,  # Sum = 3.0 + 2.0 + 1.0 = 6.0 < 10.0 ✓
            zone2_width=2.0,
            zone3_width=1.0,
            first_segment_thickness=0.3,
            first_segment_thickness_2=0.3,  # Must equal first_segment_thickness
        )
        assert dimensions.total_width == 10.0

        # Invalid width relationship
        with pytest.raises(ValidationError) as exc_info:
            BridgeDimensionsData(
                total_length=50.0,
                total_width=5.0,  # Total width
                thickness=0.3,
                zone1_width=3.0,  # Sum = 3.0 + 2.0 + 1.0 = 6.0 > 5.0 ✗
                zone2_width=2.0,
                zone3_width=1.0,
                first_segment_thickness=0.3,
                first_segment_thickness_2=0.3,
            )

        error = exc_info.value
        assert "Sum of zone widths 6.0m exceeds total bridge width 5.0m" in str(error)

    def test_boundary_values_valid(self) -> None:
        """Test that boundary values are valid."""
        # Maximum values (with valid zone width sum)
        dimensions = BridgeDimensionsData(
            total_length=1000.0,  # Maximum length
            total_width=100.0,  # Maximum width
            thickness=5.0,  # Maximum thickness
            zone1_width=30.0,  # Valid zone widths that sum to 90.0 < 100.0
            zone2_width=30.0,
            zone3_width=30.0,
            first_segment_thickness=5.0,
            first_segment_thickness_2=5.0,
        )
        assert dimensions.total_length == 1000.0
        assert dimensions.total_width == 100.0
        assert dimensions.thickness == 5.0


class TestSpan(unittest.TestCase):
    """Test cases for Span Pydantic model."""

    def test_valid_span_creation(self) -> None:
        """Test creating valid span."""
        span = Span(
            start_x=0.0,
            end_x=20.0,
            length=20.0,
            width=10.0,
            bz1=3.0,
            bz2=4.0,
            bz3=3.0,
            min_thickness=0.5,
            span_index=1,
            num_segment_definitions=2,
        )

        assert span.start_x == 0.0
        assert span.end_x == 20.0
        assert span.length == 20.0
        assert span.width == 10.0

    def test_end_x_must_be_greater_than_start_x(self) -> None:
        """Test that end_x must be greater than start_x."""
        with pytest.raises(ValidationError) as exc_info:
            Span(
                start_x=20.0,
                end_x=10.0,  # Less than start_x
                length=10.0,
                width=10.0,
                bz1=3.0,
                bz2=4.0,
                bz3=3.0,
                min_thickness=0.5,
                span_index=1,
                num_segment_definitions=2,
            )

        error = exc_info.value
        assert "end_x" in str(error)
        assert "must be greater than start_x" in str(error)

    def test_length_must_match_end_minus_start(self) -> None:
        """Test that length must match end_x - start_x."""
        with pytest.raises(ValidationError) as exc_info:
            Span(
                start_x=0.0,
                end_x=20.0,
                length=15.0,  # Should be 20.0
                width=10.0,
                bz1=3.0,
                bz2=4.0,
                bz3=3.0,
                min_thickness=0.5,
                span_index=1,
                num_segment_definitions=2,
            )

        error = exc_info.value
        assert "length" in str(error).lower()
        assert "does not match" in str(error)

    def test_width_must_match_sum_of_zones(self) -> None:
        """Test that width must match sum of zone widths."""
        with pytest.raises(ValidationError) as exc_info:
            Span(
                start_x=0.0,
                end_x=20.0,
                length=20.0,
                width=15.0,  # Should be 10.0 (3+4+3)
                bz1=3.0,
                bz2=4.0,
                bz3=3.0,
                min_thickness=0.5,
                span_index=1,
                num_segment_definitions=2,
            )

        error = exc_info.value
        assert "width" in str(error).lower()
        assert "does not match" in str(error)

    def test_positive_dimensions_required(self) -> None:
        """Test that positive dimensions are required."""
        # Negative length
        with pytest.raises(ValidationError):
            Span(
                start_x=0.0,
                end_x=20.0,
                length=-20.0,
                width=10.0,
                bz1=3.0,
                bz2=4.0,
                bz3=3.0,
                min_thickness=0.5,
                span_index=1,
                num_segment_definitions=2,
            )

        # Negative thickness
        with pytest.raises(ValidationError):
            Span(
                start_x=0.0,
                end_x=20.0,
                length=20.0,
                width=10.0,
                bz1=3.0,
                bz2=4.0,
                bz3=3.0,
                min_thickness=-0.5,
                span_index=1,
                num_segment_definitions=2,
            )

    def test_span_index_must_be_at_least_one(self) -> None:
        """Test that span index must be at least 1."""
        with pytest.raises(ValidationError):
            Span(
                start_x=0.0,
                end_x=20.0,
                length=20.0,
                width=10.0,
                bz1=3.0,
                bz2=4.0,
                bz3=3.0,
                min_thickness=0.5,
                span_index=0,
                num_segment_definitions=2,
            )


class TestUdlLoadCaseData(unittest.TestCase):
    """Test cases for UdlLoadCaseData Pydantic model."""

    def test_valid_udl_load_case_creation(self) -> None:
        """Test creating valid UDL load case data."""
        load_case = UdlLoadCaseData(
            polygon=[(0.0, 0.0, 0.0), (10.0, 0.0, 0.0), (10.0, 5.0, 0.0), (0.0, 5.0, 0.0)],
            load=9000.0,
            title="RS 1 - Conf. A - Span 1",
        )

        assert len(load_case.polygon) == 4
        assert load_case.load == 9000.0
        assert load_case.title == "RS 1 - Conf. A - Span 1"

    def test_polygon_must_have_four_corners(self) -> None:
        """Test that polygon must have exactly 4 corners."""
        # Too few corners
        with pytest.raises(ValidationError) as exc_info:
            UdlLoadCaseData(
                polygon=[(0.0, 0.0, 0.0), (10.0, 0.0, 0.0), (10.0, 5.0, 0.0)],
                load=9000.0,
                title="Test",
            )

        error = exc_info.value
        assert "4" in str(error)

        # Too many corners
        with pytest.raises(ValidationError) as exc_info:
            UdlLoadCaseData(
                polygon=[(0.0, 0.0, 0.0), (10.0, 0.0, 0.0), (10.0, 5.0, 0.0), (0.0, 5.0, 0.0), (5.0, 2.5, 0.0)],
                load=9000.0,
                title="Test",
            )

        error = exc_info.value
        assert "4" in str(error)

    def test_load_must_be_positive(self) -> None:
        """Test that load must be positive."""
        with pytest.raises(ValidationError) as exc_info:
            UdlLoadCaseData(
                polygon=[(0.0, 0.0, 0.0), (10.0, 0.0, 0.0), (10.0, 5.0, 0.0), (0.0, 5.0, 0.0)],
                load=-1000.0,
                title="Test",
            )

        error = exc_info.value
        assert "load" in str(error).lower()
        assert "greater than 0" in str(error).lower()

    def test_zero_load_rejected(self) -> None:
        """Test that zero load is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            UdlLoadCaseData(
                polygon=[(0.0, 0.0, 0.0), (10.0, 0.0, 0.0), (10.0, 5.0, 0.0), (0.0, 5.0, 0.0)],
                load=0.0,
                title="Test",
            )

        error = exc_info.value
        assert "load" in str(error).lower()

    def test_title_cannot_be_empty(self) -> None:
        """Test that title cannot be empty."""
        with pytest.raises(ValidationError):
            UdlLoadCaseData(
                polygon=[(0.0, 0.0, 0.0), (10.0, 0.0, 0.0), (10.0, 5.0, 0.0), (0.0, 5.0, 0.0)],
                load=9000.0,
                title="",
            )

    def test_polygon_point_structure_validation(self) -> None:
        """Test that polygon points must be 3-element tuples."""
        # Invalid point structure (2 elements instead of 3)
        with pytest.raises(ValidationError):
            UdlLoadCaseData(
                polygon=[(0.0, 0.0), (10.0, 0.0), (10.0, 5.0), (0.0, 5.0)],  # type: ignore[arg-type,list-item]
                load=9000.0,
                title="Test",
            )
