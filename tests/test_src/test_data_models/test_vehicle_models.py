"""
Tests for vehicle Pydantic models.

This module tests the vehicle specification models including validation,
property access, and registry functionality.
"""

import pytest
from pydantic import ValidationError

from src.data_models.vehicle_models import (
    STANDARD_VEHICLES,
    AccidentalVehicle,
    AmsterdamAccidentalVehicle,
    ServiceVehicle,
    TandemSystemVehicle,
    TramVehicle,
    VehicleAxleConfig,
    VehicleGeometry,
    VehiclePosition,
    WheelLoad,
)


class TestVehicleGeometry:
    """Tests for VehicleGeometry base model."""

    def test_valid_geometry_creation(self) -> None:
        """Test creation of valid vehicle geometry."""
        geometry = VehicleGeometry(
            length=3.0,
            width=2.0,
            wheel_dim_x=0.3,
            wheel_dim_y=0.35,
            wheel_spacing_longitudinal=2.0,
            wheel_spacing_transverse=1.5,
        )
        assert geometry.length == 3.0
        assert geometry.width == 2.0
        assert geometry.wheel_dim_x == 0.3
        assert geometry.wheel_dim_y == 0.35

    def test_negative_length_rejected(self) -> None:
        """Test that negative length is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            VehicleGeometry(
                length=-1.0,
                width=2.0,
                wheel_dim_x=0.3,
                wheel_dim_y=0.35,
                wheel_spacing_longitudinal=2.0,
                wheel_spacing_transverse=1.5,
            )
        assert "greater than 0" in str(exc_info.value).lower()

    def test_too_large_dimension_rejected(self) -> None:
        """Test that unrealistic dimensions are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            VehicleGeometry(
                length=100.0,
                width=2.0,
                wheel_dim_x=0.3,
                wheel_dim_y=0.35,
                wheel_spacing_longitudinal=2.0,
                wheel_spacing_transverse=1.5,
            )
        assert "less than or equal to" in str(exc_info.value).lower() or "unrealistic" in str(exc_info.value).lower()


class TestVehicleAxleConfig:
    """Tests for VehicleAxleConfig model."""

    def test_valid_axle_config_creation(self) -> None:
        """Test creation of valid axle configuration."""
        config = VehicleAxleConfig(num_axles=2, axle_loads_kn=[80.0, 40.0], axle_spacing_m=1.2)
        assert config.num_axles == 2
        assert config.axle_loads_kn == [80.0, 40.0]
        assert config.axle_spacing_m == 1.2

    def test_axle_loads_count_mismatch(self) -> None:
        """Test that mismatched axle count and loads is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            VehicleAxleConfig(num_axles=2, axle_loads_kn=[80.0, 40.0, 20.0], axle_spacing_m=1.2)
        assert "doesn't match" in str(exc_info.value)

    def test_negative_axle_load_rejected(self) -> None:
        """Test that negative axle loads are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            VehicleAxleConfig(num_axles=2, axle_loads_kn=[80.0, -40.0], axle_spacing_m=1.2)
        assert "must be positive" in str(exc_info.value).lower()


class TestTandemSystemVehicle:
    """Tests for TandemSystemVehicle model."""

    def test_valid_tandem_vehicle_creation(self) -> None:
        """Test creation of valid tandem vehicle."""
        tandem = TandemSystemVehicle()
        assert tandem.vehicle_type == "tandem"
        assert tandem.load_main_lane_kn == 300.0
        assert tandem.load_second_lane_kn == 200.0
        assert tandem.load_third_lane_kn == 100.0
        assert tandem.wheel_spacing_longitudinal == 1.2

    def test_get_load_for_lane(self) -> None:
        """Test the get_load_for_lane method."""
        tandem = TandemSystemVehicle()
        assert tandem.get_load_for_lane(1) == 300.0
        assert tandem.get_load_for_lane(2) == 200.0
        assert tandem.get_load_for_lane(3) == 100.0
        assert tandem.get_load_for_lane(4) == 100.0  # Third+ lanes use third lane load

    def test_get_load_for_lane_invalid(self) -> None:
        """Test get_load_for_lane with invalid lane number."""
        tandem = TandemSystemVehicle()
        with pytest.raises(ValueError, match="Invalid lane number"):
            tandem.get_load_for_lane(0)
        with pytest.raises(ValueError, match="Invalid lane number"):
            tandem.get_load_for_lane(-1)

    def test_custom_tandem_vehicle(self) -> None:
        """Test creation of custom tandem vehicle."""
        tandem = TandemSystemVehicle(load_main_lane_kn=250.0, length=2.0)
        assert tandem.load_main_lane_kn == 250.0
        assert tandem.length == 2.0


class TestServiceVehicle:
    """Tests for ServiceVehicle model."""

    def test_valid_service_vehicle_creation(self) -> None:
        """Test creation of valid service vehicle."""
        service = ServiceVehicle()
        assert service.vehicle_type == "service"
        assert service.force_per_axle_kn == 25.0
        assert service.length == 3.0
        assert service.width == 1.75
        assert service.wheel_dim_x == 0.25
        assert service.wheel_dim_y == 0.25

    def test_custom_service_vehicle(self) -> None:
        """Test creation of custom service vehicle."""
        service = ServiceVehicle(force_per_axle_kn=30.0, width=2.0)
        assert service.force_per_axle_kn == 30.0
        assert service.width == 2.0

    def test_too_large_load_rejected(self) -> None:
        """Test that unrealistic loads are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ServiceVehicle(force_per_axle_kn=1000.0)
        assert "less than or equal to 100" in str(exc_info.value).lower()


class TestAccidentalVehicle:
    """Tests for AccidentalVehicle model."""

    def test_valid_accidental_vehicle_creation(self) -> None:
        """Test creation of valid accidental vehicle."""
        accidental = AccidentalVehicle()
        assert accidental.vehicle_type == "accidental"
        assert accidental.force_axle_1_kn == 80.0
        assert accidental.force_axle_2_kn == 40.0
        assert accidental.width == 1.30
        assert accidental.wheel_dim_x == 0.20
        assert accidental.wheel_dim_y == 0.20
        assert accidental.axle_spacing_m == 1.2


class TestAmsterdamAccidentalVehicle:
    """Tests for AmsterdamAccidentalVehicle model."""

    def test_valid_amsterdam_vehicle_creation(self) -> None:
        """Test creation of valid Amsterdam accidental vehicle."""
        amsterdam = AmsterdamAccidentalVehicle()
        assert amsterdam.vehicle_type == "amsterdam_accidental"
        assert amsterdam.force_single_axle_kn == 240.0
        assert amsterdam.width == 2.0
        assert amsterdam.wheel_dim_x == 0.4
        assert amsterdam.wheel_dim_y == 0.4


class TestTramVehicle:
    """Tests for TramVehicle model."""

    def test_valid_tram_vehicle_creation(self) -> None:
        """Test creation of valid tram vehicle."""
        tram = TramVehicle()
        assert tram.vehicle_type == "tram"
        assert tram.length == 20.0
        assert tram.width == 2.4
        assert tram.track_gauge_m is None

    def test_tram_with_track_gauge(self) -> None:
        """Test tram vehicle with specified track gauge."""
        tram = TramVehicle(track_gauge_m=1.435)
        assert tram.track_gauge_m == 1.435

    def test_invalid_track_gauge_rejected(self) -> None:
        """Test that unrealistic track gauge is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            TramVehicle(track_gauge_m=3.0)
        # Check for validation error message
        assert "less than or equal" in str(exc_info.value).lower() or "too wide" in str(exc_info.value).lower()


class TestVehiclePosition:
    """Tests for VehiclePosition model."""

    def test_valid_position_creation(self) -> None:
        """Test creation of valid vehicle position."""
        position = VehiclePosition(x_coord=10.0, y_coord=5.0)
        assert position.x_coord == 10.0
        assert position.y_coord == 5.0
        assert position.z_coord == 0.0
        assert position.rotation_degrees == 0.0

    def test_position_with_rotation(self) -> None:
        """Test position with rotation."""
        position = VehiclePosition(x_coord=10.0, y_coord=5.0, rotation_degrees=45.0)
        assert position.rotation_degrees == 45.0

    def test_position_with_z_coord(self) -> None:
        """Test position with z coordinate."""
        position = VehiclePosition(x_coord=10.0, y_coord=5.0, z_coord=1.5)
        assert position.z_coord == 1.5

    def test_invalid_coordinate_rejected(self) -> None:
        """Test that unrealistic coordinates are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            VehiclePosition(x_coord=2000.0, y_coord=5.0)
        assert "unrealistic" in str(exc_info.value).lower()


class TestWheelLoad:
    """Tests for WheelLoad model."""

    def test_valid_wheel_load_creation(self) -> None:
        """Test creation of valid wheel load."""
        wheel = WheelLoad(position="front_left", load_kn=50.0, contact_area_m=0.3)
        assert wheel.position == "front_left"
        assert wheel.load_kn == 50.0
        assert wheel.contact_area_m == 0.3

    def test_position_case_insensitive(self) -> None:
        """Test that position identifier is case insensitive."""
        wheel = WheelLoad(position="FRONT_RIGHT", load_kn=50.0, contact_area_m=0.3)
        assert wheel.position == "front_right"

    def test_invalid_position_rejected(self) -> None:
        """Test that invalid position is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            WheelLoad(position="invalid", load_kn=50.0, contact_area_m=0.3)
        assert "not allowed" in str(exc_info.value).lower()


class TestVehicleRegistry:
    """Tests for VehicleRegistry and STANDARD_VEHICLES."""

    def test_standard_vehicles_accessible(self) -> None:
        """Test that STANDARD_VEHICLES is accessible."""
        assert STANDARD_VEHICLES is not None

    def test_tandem_vehicle_access(self) -> None:
        """Test accessing tandem vehicle from registry."""
        tandem = STANDARD_VEHICLES.tandem
        assert isinstance(tandem, TandemSystemVehicle)
        assert tandem.vehicle_type == "tandem"

    def test_service_vehicle_access(self) -> None:
        """Test accessing service vehicle from registry."""
        service = STANDARD_VEHICLES.service
        assert isinstance(service, ServiceVehicle)
        assert service.vehicle_type == "service"

    def test_accidental_vehicle_access(self) -> None:
        """Test accessing accidental vehicle from registry."""
        accidental = STANDARD_VEHICLES.accidental
        assert isinstance(accidental, AccidentalVehicle)
        assert accidental.vehicle_type == "accidental"

    def test_amsterdam_vehicle_access(self) -> None:
        """Test accessing Amsterdam vehicle from registry."""
        amsterdam = STANDARD_VEHICLES.amsterdam_accidental
        assert isinstance(amsterdam, AmsterdamAccidentalVehicle)
        assert amsterdam.vehicle_type == "amsterdam_accidental"

    def test_tram_vehicle_access(self) -> None:
        """Test accessing tram vehicle from registry."""
        tram = STANDARD_VEHICLES.tram
        assert isinstance(tram, TramVehicle)
        assert tram.vehicle_type == "tram"

    def test_registry_values(self) -> None:
        """Test that registry vehicles have correct load values."""
        assert STANDARD_VEHICLES.tandem.load_main_lane_kn == 300.0
        assert STANDARD_VEHICLES.service.force_per_axle_kn == 25.0
        assert STANDARD_VEHICLES.accidental.force_axle_1_kn == 80.0
        assert STANDARD_VEHICLES.amsterdam_accidental.force_single_axle_kn == 240.0


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_zero_load_rejected(self) -> None:
        """Test that zero loads are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            TandemSystemVehicle(load_main_lane_kn=0.0)
        assert "greater than 0" in str(exc_info.value).lower()

    def test_boundary_values_accepted(self) -> None:
        """Test that boundary values are accepted."""
        # Minimum realistic values
        geometry = VehicleGeometry(
            length=0.1,
            width=0.1,
            wheel_dim_x=0.05,
            wheel_dim_y=0.05,
            wheel_spacing_longitudinal=0.1,
            wheel_spacing_transverse=0.1,
        )
        assert geometry.length == 0.1

        # Maximum realistic values
        geometry_max = VehicleGeometry(
            length=10.0,
            width=10.0,
            wheel_dim_x=1.0,
            wheel_dim_y=1.0,
            wheel_spacing_longitudinal=5.0,
            wheel_spacing_transverse=5.0,
        )
        assert geometry_max.length == 10.0

    def test_very_small_contact_area_rejected(self) -> None:
        """Test that very small contact areas are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            VehicleGeometry(
                length=3.0,
                width=2.0,
                wheel_dim_x=0.01,
                wheel_dim_y=0.02,
                wheel_spacing_longitudinal=2.0,
                wheel_spacing_transverse=1.5,
            )
        assert "too small" in str(exc_info.value).lower()

    def test_tram_optional_fields(self) -> None:
        """Test that tram optional fields work correctly."""
        tram_with_load = TramVehicle(load_per_wheel_kn=50.0)
        assert tram_with_load.load_per_wheel_kn == 50.0

        tram_without_load = TramVehicle()
        assert tram_without_load.load_per_wheel_kn is None
