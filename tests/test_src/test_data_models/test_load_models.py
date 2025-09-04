"""Tests for load zone Pydantic models."""

import unittest

import pytest
from pydantic import ValidationError

from src.data_models.load_models import LoadZoneData


class TestLoadZoneData(unittest.TestCase):
    """Test cases for LoadZoneData Pydantic model."""

    def test_valid_auto_zone_creation(self) -> None:
        """Test creating a valid auto zone."""
        zone = LoadZoneData(
            zone_type="Auto",
            pavement_thickness=0.1,
            pavement_material="Asfalt",
            d1_width=3.5,
            d2_width=3.5,
            d3_width=3.5,
        )
        assert zone.zone_type == "Auto"
        assert zone.pavement_thickness == 0.1
        assert zone.d1_width == 3.5

    def test_invalid_zone_type_rejected(self) -> None:
        """Test that invalid zone types are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            LoadZoneData(
                zone_type="InvalidType",  # type: ignore[arg-type]
                pavement_thickness=0.1,
                pavement_material="Asfalt",
            )

        error = exc_info.value
        assert "zone_type" in str(error)

    def test_pavement_thickness_validation_by_zone_type(self) -> None:
        """Test pavement thickness validation based on zone type."""
        # Auto zone with too thin pavement
        with pytest.raises(ValidationError) as exc_info:
            LoadZoneData(
                zone_type="Auto",
                pavement_thickness=0.01,  # Too thin for Auto
                pavement_material="Asfalt",
            )

        assert "minimum 5cm pavement thickness" in str(exc_info.value)

    def test_valid_pedestrian_zone_creation(self) -> None:
        """Test creating a valid pedestrian zone."""
        zone = LoadZoneData(
            zone_type="Voetgangers",
            pavement_thickness=0.03,
            pavement_material="Tegels",
            d1_width=2.0,
            d2_width=2.0,
        )
        assert zone.zone_type == "Voetgangers"
        assert zone.pavement_material == "Tegels"

    def test_invalid_pavement_material_rejected(self) -> None:
        """Test that invalid pavement materials are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            LoadZoneData(
                zone_type="Auto",
                pavement_thickness=0.1,
                pavement_material="InvalidMaterial",  # type: ignore[arg-type]
            )

        error = exc_info.value
        assert "pavement_material" in str(error)

    def test_negative_pavement_thickness_rejected(self) -> None:
        """Test that negative pavement thickness is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            LoadZoneData(
                zone_type="Auto",
                pavement_thickness=-0.1,  # Negative thickness
                pavement_material="Asfalt",
            )

        error = exc_info.value
        assert "greater than 0" in str(error)

    def test_excessive_pavement_thickness_rejected(self) -> None:
        """Test that excessive pavement thickness is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            LoadZoneData(
                zone_type="Auto",
                pavement_thickness=1.0,  # Too thick (>0.5m)
                pavement_material="Asfalt",
            )

        error = exc_info.value
        assert "less than or equal to 0.5" in str(error)

    def test_d_width_validation(self) -> None:
        """Test D-width field validation."""
        # Valid case with multiple D-widths
        zone = LoadZoneData(
            zone_type="Auto",
            pavement_thickness=0.1,
            pavement_material="Asfalt",
            d1_width=3.5,
            d5_width=4.0,
            d10_width=3.0,
        )
        assert zone.d1_width == 3.5
        assert zone.d5_width == 4.0
        assert zone.d10_width == 3.0
        assert zone.d2_width is None  # Not specified, should be None

    def test_invalid_d_width_rejected(self) -> None:
        """Test that invalid D-width values are rejected."""
        # Negative width
        with pytest.raises(ValidationError):
            LoadZoneData(
                zone_type="Auto",
                pavement_thickness=0.1,
                pavement_material="Asfalt",
                d1_width=-1.0,  # Negative width
            )

        # Excessive width
        with pytest.raises(ValidationError):
            LoadZoneData(
                zone_type="Auto",
                pavement_thickness=0.1,
                pavement_material="Asfalt",
                d1_width=100.0,  # Too wide (>50m)
            )

    def test_calculated_fields_default_empty(self) -> None:
        """Test that calculated fields default to empty lists."""
        zone = LoadZoneData(zone_type="Auto", pavement_thickness=0.1, pavement_material="Asfalt")

        assert zone.zone_widths_per_d == []
        assert zone.y_coords_top_current_zone == []


if __name__ == "__main__":
    unittest.main()
