"""
Test module for bridge utility functions.

This module contains comprehensive tests for bridge validation logic,
particularly load zone width validation functionality.
"""

import unittest
from typing import Any

from munch import Munch  # type: ignore[import-untyped]

from app.bridge.utils import ParamsForLoadZones, validate_load_zone_widths
from src.data_models.geometry_data_models import DPointLabelData, LoadZoneGeometryData


class TestValidateLoadZoneWidths(unittest.TestCase):
    """Test cases for validate_load_zone_widths function."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.default_geometry_data = LoadZoneGeometryData(
            num_defined_d_points=3,
            x_coords_d_points=[0.0, 10.0, 20.0],
            total_widths_at_d_points=[6.0, 8.0, 6.0],  # Available bridge widths
            y_top_structural_edge_at_d_points=[3.0, 4.0, 3.0],
            y_bridge_bottom_at_d_points=[-3.0, -4.0, -3.0],
            d_point_label_data=[
                DPointLabelData(text="D1", x=0.0, y=3.0),
                DPointLabelData(text="D2", x=10.0, y=4.0),
                DPointLabelData(text="D3", x=20.0, y=3.0),
            ],
        )

    def _create_load_zone_row(self, **widths: float) -> Munch:
        """Helper to create a load zone row with specified width parameters."""
        zone_row = Munch({"zone_type": "Auto"})
        # Set d1_width through d15_width (up to 15 D-points)
        for i in range(1, 16):
            width_field = f"d{i}_width"
            zone_row[width_field] = widths.get(width_field, 0.0)
        return zone_row

    def _create_params_with_zones(self, load_zones: list[Munch]) -> Munch:
        """Helper to create params object with load zones."""
        return Munch({"load_zones_data_array": load_zones})

    def test_validate_load_zone_widths_no_load_zones(self) -> None:
        """Test validation with no load zones defined."""
        # Arrange
        params = Munch({"load_zones_data_array": []})

        # Act
        warnings = validate_load_zone_widths(params, self.default_geometry_data)

        # Assert
        assert warnings == []

    def test_validate_load_zone_widths_missing_load_zones_attr(self) -> None:
        """Test validation when load_zones_data_array attribute is missing."""
        # Arrange
        params = Munch({})  # Missing load_zones_data_array

        # Act
        warnings = validate_load_zone_widths(params, self.default_geometry_data)

        # Assert
        assert warnings == []

    def test_validate_load_zone_widths_no_d_points(self) -> None:
        """Test validation with geometry that has no D-points."""
        # Arrange
        empty_geometry = LoadZoneGeometryData(
            num_defined_d_points=0,
            x_coords_d_points=[],
            total_widths_at_d_points=[],
            y_top_structural_edge_at_d_points=[],
            y_bridge_bottom_at_d_points=[],
            d_point_label_data=[],
        )
        params = self._create_params_with_zones([self._create_load_zone_row(d1_width=2.0)])

        # Act
        warnings = validate_load_zone_widths(params, empty_geometry)

        # Assert
        assert len(warnings) == 1
        assert "geen D-punten gedefinieerd" in warnings[0]

    def test_validate_load_zone_widths_within_limits(self) -> None:
        """Test validation when all load zone widths are within bridge limits."""
        # Arrange - Total widths: D1=3.0, D2=4.0, D3=3.0 (all within limits)
        zone1 = self._create_load_zone_row(d1_width=1.0, d2_width=1.5, d3_width=1.0)
        zone2 = self._create_load_zone_row(d1_width=1.0, d2_width=1.5, d3_width=1.0)
        # Last zone gets remaining width automatically
        zone3 = self._create_load_zone_row()  # This will be calculated as remaining width

        params = self._create_params_with_zones([zone1, zone2, zone3])

        # Act
        warnings = validate_load_zone_widths(params, self.default_geometry_data)

        # Assert
        assert warnings == []

    def test_validate_load_zone_widths_exceeding_limits(self) -> None:
        """Test validation when load zone widths exceed bridge limits."""
        # Arrange - Use widths that definitely exceed limits at all D-points
        zone1 = self._create_load_zone_row(d1_width=10.0, d2_width=10.0, d3_width=10.0)
        zone2 = self._create_load_zone_row()  # Last zone gets remaining width

        params = self._create_params_with_zones([zone1, zone2])

        # Act
        warnings = validate_load_zone_widths(params, self.default_geometry_data)

        # Assert
        assert len(warnings) == 3  # Should warn for all three D-points
        assert "D1" in warnings[0]
        assert "D2" in warnings[1]
        assert "D3" in warnings[2]
        assert "overschrijdt brugbreedte" in warnings[0]

    def test_validate_load_zone_widths_partial_exceedance(self) -> None:
        """Test validation when only some D-points exceed limits."""
        # Arrange - Only D2 exceeds limit (available width is 8.0m)
        zone1 = self._create_load_zone_row(d1_width=1.0, d2_width=9.0, d3_width=1.0)  # D2 = 9.0 exceeds 8.0 limit
        zone2 = self._create_load_zone_row()  # Last zone

        params = self._create_params_with_zones([zone1, zone2])

        # Act
        warnings = validate_load_zone_widths(params, self.default_geometry_data)

        # Assert
        assert len(warnings) == 1
        assert "D2" in warnings[0]
        assert "D1" not in warnings[0]
        assert "D3" not in warnings[0]

    def test_validate_load_zone_widths_single_zone(self) -> None:
        """Test validation with only one load zone (which gets all remaining width)."""
        # Arrange
        zone1 = self._create_load_zone_row()  # Single zone gets all available width

        params = self._create_params_with_zones([zone1])

        # Act
        warnings = validate_load_zone_widths(params, self.default_geometry_data)

        # Assert
        assert warnings == []  # Single zone should never exceed limits

    def test_validate_load_zone_widths_missing_width_fields(self) -> None:
        """Test validation when width fields are missing from zone rows."""
        # Arrange - Create zone without some width fields
        zone1 = Munch({"zone_type": "Auto"})  # Missing dX_width fields
        zone2 = self._create_load_zone_row(d1_width=1.0, d2_width=1.0, d3_width=1.0)
        zone3 = self._create_load_zone_row()  # Last zone

        params = self._create_params_with_zones([zone1, zone2, zone3])

        # Act
        warnings = validate_load_zone_widths(params, self.default_geometry_data)

        # Assert
        assert warnings == []  # Missing fields should be treated as 0.0

    def test_validate_load_zone_widths_floating_point_tolerance(self) -> None:
        """Test validation with floating point precision near the limit."""
        # Arrange - Set widths very close to but slightly over limits
        zone1 = self._create_load_zone_row(d1_width=3.0001, d2_width=4.0001, d3_width=3.0001)
        zone2 = self._create_load_zone_row(d1_width=2.9999, d2_width=3.9999, d3_width=2.9999)
        zone3 = self._create_load_zone_row()  # Last zone

        params = self._create_params_with_zones([zone1, zone2, zone3])

        # Act
        warnings = validate_load_zone_widths(params, self.default_geometry_data)

        # Assert
        # Small floating point differences should be within tolerance (1e-3)
        # Total at each D: 6.0000, 8.0000, 6.0000 which should be within tolerance
        assert warnings == []

    def test_validate_load_zone_widths_significant_exceedance(self) -> None:
        """Test validation with significant exceedance beyond tolerance."""
        # Arrange - Exceed limits by more than tolerance
        zone1 = self._create_load_zone_row(d1_width=3.5, d2_width=4.5, d3_width=3.5)
        zone2 = self._create_load_zone_row(d1_width=3.0, d2_width=4.0, d3_width=3.0)
        zone3 = self._create_load_zone_row()  # Last zone

        params = self._create_params_with_zones([zone1, zone2, zone3])

        # Act
        warnings = validate_load_zone_widths(params, self.default_geometry_data)

        # Assert
        assert len(warnings) == 3
        # Check for specific overrun amounts in messages
        for warning in warnings:
            assert "overschrijdt brugbreedte" in warning
            assert "met" in warning  # Should include overrun amount
            assert "m." in warning  # Should include unit

    def test_validate_load_zone_widths_last_zone_calculation(self) -> None:
        """Test that the last zone width is calculated correctly."""
        # Arrange - Set up zones where last zone should get specific remaining width
        geometry_data = LoadZoneGeometryData(
            num_defined_d_points=1,
            x_coords_d_points=[0.0],
            total_widths_at_d_points=[10.0],  # Total available
            y_top_structural_edge_at_d_points=[5.0],
            y_bridge_bottom_at_d_points=[-5.0],
            d_point_label_data=[DPointLabelData(text="D1", x=0.0, y=5.0)],
        )

        zone1 = self._create_load_zone_row(d1_width=3.0)  # Uses 3.0m
        zone2 = self._create_load_zone_row(d1_width=4.0)  # Uses 4.0m
        zone3 = self._create_load_zone_row()  # Should get remaining 3.0m

        params = self._create_params_with_zones([zone1, zone2, zone3])

        # Act
        warnings = validate_load_zone_widths(params, geometry_data)

        # Assert
        assert warnings == []  # Total should be exactly 10.0m

    def test_validate_load_zone_widths_zero_width_zones(self) -> None:
        """Test validation with zones having zero width."""
        # Arrange
        zone1 = self._create_load_zone_row(d1_width=0.0, d2_width=0.0, d3_width=0.0)
        zone2 = self._create_load_zone_row(d1_width=2.0, d2_width=3.0, d3_width=2.0)
        zone3 = self._create_load_zone_row()  # Last zone gets remaining

        params = self._create_params_with_zones([zone1, zone2, zone3])

        # Act
        warnings = validate_load_zone_widths(params, self.default_geometry_data)

        # Assert
        assert warnings == []  # Should be within limits

    def test_validate_load_zone_widths_error_message_format(self) -> None:
        """Test that error messages have correct format and information."""
        # Arrange - Create a scenario that will definitely exceed limits
        zone1 = self._create_load_zone_row(d1_width=10.0, d2_width=10.0, d3_width=10.0)
        zone2 = self._create_load_zone_row()  # Last zone

        params = self._create_params_with_zones([zone1, zone2])

        # Act
        warnings = validate_load_zone_widths(params, self.default_geometry_data)

        # Assert
        assert len(warnings) == 3
        for i, warning in enumerate(warnings):
            expected_d_point = f"D{i + 1}"
            assert expected_d_point in warning
            assert "Totale zonebreedte" in warning
            assert "overschrijdt brugbreedte" in warning
            assert "met" in warning
            assert "m)" in warning  # Check for proper formatting with units

    def test_validate_load_zone_widths_edge_case_negative_remaining_width(self) -> None:
        """Test edge case where calculated remaining width for last zone would be negative."""
        # Arrange - Use more width in first zones than total available
        zone1 = self._create_load_zone_row(d1_width=4.0, d2_width=5.0, d3_width=4.0)
        zone2 = self._create_load_zone_row(d1_width=3.0, d2_width=4.0, d3_width=3.0)
        zone3 = self._create_load_zone_row()  # Last zone - remaining would be negative

        params = self._create_params_with_zones([zone1, zone2, zone3])

        # Act
        warnings = validate_load_zone_widths(params, self.default_geometry_data)

        # Assert
        # Should detect exceedance at all D-points
        assert len(warnings) == 3
        for warning in warnings:
            assert "overschrijdt brugbreedte" in warning


class TestParamsForLoadZonesProtocol(unittest.TestCase):
    """Test cases for ParamsForLoadZones protocol."""

    def test_params_protocol_compliance(self) -> None:
        """Test that a valid params object complies with ParamsForLoadZones protocol."""
        # Arrange
        load_zones = [
            Munch({"zone_type": "Auto", "d1_width": 1.0}),
            Munch({"zone_type": "Voetgangers", "d1_width": 2.0}),
        ]
        params = Munch({"load_zones_data_array": load_zones})

        # Act & Assert - This should not raise any type errors
        def use_params_protocol(p: ParamsForLoadZones) -> list[Any]:
            return p.load_zones_data_array

        result = use_params_protocol(params)
        assert result == load_zones

    def test_params_protocol_missing_attribute(self) -> None:
        """Test behavior when params object is missing required attributes."""
        # Arrange
        params = Munch({})  # Missing load_zones_data_array

        # Act & Assert - Should handle gracefully in validate_load_zone_widths
        geometry_data = LoadZoneGeometryData(
            num_defined_d_points=1,
            x_coords_d_points=[0.0],
            total_widths_at_d_points=[10.0],
            y_top_structural_edge_at_d_points=[5.0],
            y_bridge_bottom_at_d_points=[-5.0],
            d_point_label_data=[DPointLabelData(text="D1", x=0.0, y=5.0)],
        )

        warnings = validate_load_zone_widths(params, geometry_data)
        assert warnings == []  # Should return empty list, not crash


if __name__ == "__main__":
    unittest.main()
