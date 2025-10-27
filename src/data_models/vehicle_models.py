"""
Pydantic models for vehicle specifications in bridge load analysis.

This module provides validated data structures for all vehicle types used in traffic load
calculations, consolidating scattered constants into reusable, type-safe models.
These models support the current tandem system, service vehicles, accidental vehicles,
and are designed to easily accommodate future vehicles like trams.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class VehicleGeometry(BaseModel):
    """
    Base geometry parameters shared by all vehicle types.

    Provides common dimensional and spatial properties used in load calculations
    and vehicle positioning on bridge decks.

    Note: inset_distance is not included here as it is a bridge-specific parameter,
    not a vehicle characteristic. Different bridges may apply different inset distances
    for the same vehicle type.
    """

    length: float = Field(gt=0, le=10, description="Vehicle length in meters")
    width: float = Field(gt=0, le=10, description="Vehicle width in meters")
    wheel_dim_x: float = Field(gt=0, le=1, description="Wheel contact patch dimension along X-axis (longitudinal) in meters")
    wheel_dim_y: float = Field(gt=0, le=1, description="Wheel contact patch dimension along Y-axis (transverse) in meters")
    wheel_spacing_longitudinal: float = Field(gt=0, le=5.0, description="Distance between axles in meters")
    wheel_spacing_transverse: float = Field(gt=0, le=5.0, description="Distance between left/right wheels in meters")

    @field_validator("length", "width")
    @classmethod
    def validate_dimensions_realistic(cls, v: float) -> float:
        """Validate that vehicle dimensions are realistic."""
        if v < 0.1:
            raise ValueError(f"Vehicle dimension {v}m is too small (minimum 0.1m)")
        if v > 50:
            raise ValueError(f"Vehicle dimension {v}m is unrealistic (maximum 50m)")
        return v

    @field_validator("wheel_dim_x", "wheel_dim_y")
    @classmethod
    def validate_wheel_dimensions(cls, v: float) -> float:
        """Validate wheel dimensions are realistic."""
        if v < 0.05:
            raise ValueError(f"Wheel dimension {v}m is too small (minimum 0.05m)")
        if v > 1.0:
            raise ValueError(f"Wheel dimension {v}m is too large (maximum 1.0m)")
        return v

    model_config = ConfigDict(validate_assignment=True)


class VehicleAxleConfig(BaseModel):
    """
    Axle configuration for multi-axle vehicles.

    Defines the number of axles, load per axle, and spacing between axles
    for vehicles with multiple wheel sets.
    """

    num_axles: int = Field(ge=1, le=4, description="Number of axles (1-4)")
    axle_loads_kn: list[float] = Field(min_length=1, max_length=4, description="Load per axle in kN")
    axle_spacing_m: float | list[float] = Field(gt=0, le=10, description="Spacing between axles in meters")

    @field_validator("axle_loads_kn")
    @classmethod
    def validate_axle_loads(cls, v: list[float]) -> list[float]:
        """Validate that all axle loads are positive and realistic."""
        for i, load in enumerate(v):
            if load <= 0:
                raise ValueError(f"Axle {i + 1} load {load}kN must be positive")
            if load > 500:
                raise ValueError(f"Axle {i + 1} load {load}kN is unrealistic (maximum 500kN)")
        return v

    @model_validator(mode="after")
    def validate_configuration_consistency(self) -> "VehicleAxleConfig":
        """Validate that axle configuration is consistent."""
        # Number of axles must match number of loads
        if len(self.axle_loads_kn) != self.num_axles:
            raise ValueError(f"Number of axle loads ({len(self.axle_loads_kn)}) doesn't match num_axles ({self.num_axles})")

        # If axle spacing is a list, it must have correct length
        if isinstance(self.axle_spacing_m, list):
            # For N axles, we need N-1 spacing values
            expected_spacings = self.num_axles - 1
            if len(self.axle_spacing_m) != expected_spacings:
                raise ValueError(
                    f"Number of axle spacings ({len(self.axle_spacing_m)}) doesn't match expected ({expected_spacings}) for {self.num_axles} axles"
                )

        return self

    model_config = ConfigDict(validate_assignment=True)


class TandemSystemVehicle(BaseModel):
    """
    Complete specification for tandem system load vehicles.

    Defines geometry, contact areas, and lane-specific load values according to
    NEN-EN 1991-2 standards for bridge traffic loading.
    """

    # Geometry (from constants: TANDEM_WHEEL_SPACING_LONGITUDINAL, TANDEM_WHEEL_SPACING_TRANSVERSE, TANDEM_VEHICLE_LENGTH, TANDEM_WHEEL_SIZE)
    length: float = Field(default=1.6, gt=0, le=10, description="Tandem vehicle length in meters")
    width: float = Field(default=2.0, gt=0, le=10, description="Tandem vehicle width in meters")
    wheel_dim_x: float = Field(default=0.4, gt=0, le=1, description="Wheel contact patch dimension along X-axis (longitudinal) in meters")
    wheel_dim_y: float = Field(default=0.4, gt=0, le=1, description="Wheel contact patch dimension along Y-axis (transverse) in meters")
    wheel_spacing_longitudinal: float = Field(default=1.2, gt=0, le=5, description="Distance between axles in meters")
    wheel_spacing_transverse: float = Field(default=2.0, gt=0, le=5, description="Distance between left/right wheels in meters")

    # Load values (from constants: TANDEM_LOAD_BASE_MAIN, TANDEM_LOAD_BASE_SECOND, TANDEM_LOAD_BASE_THIRD)
    load_main_lane_kn: float = Field(default=300.0, gt=0, le=500, description="Load for main lane in kN")
    load_second_lane_kn: float = Field(default=200.0, gt=0, le=500, description="Load for second lane in kN")
    load_third_lane_kn: float = Field(default=100.0, gt=0, le=500, description="Load for third lane in kN")

    vehicle_type: Literal["tandem"] = Field(default="tandem", description="Vehicle type identifier")

    def get_load_for_lane(self, lane_number: int) -> float:
        """
        Get the appropriate load value for a specific lane.

        Args:
            lane_number: Lane number (1 for main, 2 for second, 3+ for third)

        Returns:
            Load value in kN for the specified lane

        Raises:
            ValueError: If lane number is invalid

        """
        if lane_number == 1:
            return self.load_main_lane_kn
        if lane_number == 2:
            return self.load_second_lane_kn
        if lane_number >= 3:
            return self.load_third_lane_kn

        raise ValueError(f"Invalid lane number {lane_number}. Must be 1, 2, or 3+")

    model_config = ConfigDict(validate_assignment=True)


class ServiceVehicle(BaseModel):
    """
    Service vehicle specification (NEN-EN 1991-2 art. 5.3.2.3).

    Defines geometry and load values for service vehicles used in bridge analysis.
    These vehicles are used for maintenance and emergency access load cases.
    """

    # Geometry (from SERVICE_VEHICLE_* constants)
    length: float = Field(default=3.0, gt=0, le=10, description="Service vehicle length in meters")
    width: float = Field(default=1.75, gt=0, le=10, description="Service vehicle width in meters")
    wheel_dim_x: float = Field(default=0.25, gt=0, le=1, description="Wheel contact patch dimension along X-axis (longitudinal) in meters")
    wheel_dim_y: float = Field(default=0.25, gt=0, le=1, description="Wheel contact patch dimension along Y-axis (transverse) in meters")
    wheel_spacing_longitudinal: float = Field(default=2.5, gt=0, le=5, description="Distance between axles in meters")
    wheel_spacing_transverse: float = Field(default=1.25, gt=0, le=5, description="Distance between left/right wheels in meters")

    # Load (from SERVICE_VEHICLE_FORCE_PER_AXLE constant = 25 kN)
    force_per_axle_kn: float = Field(default=25.0, gt=0, le=100, description="Force per axle in kN")

    vehicle_type: Literal["service"] = Field(default="service", description="Vehicle type identifier")

    model_config = ConfigDict(validate_assignment=True)


class AccidentalVehicle(BaseModel):
    """
    Accidental vehicle specification (NEN-EN 1991-2 art. 5.3.2.3(1)P).

    Defines geometry and axle loads for standard accidental vehicle loads used
    in bridge analysis to account for extreme traffic events.
    """

    # Geometry (from ACCIDENTAL_VEHICLE_* constants)
    width: float = Field(default=1.30, gt=0, le=10, description="Vehicle width in meters")
    wheel_dim_x: float = Field(default=0.20, gt=0, le=1, description="Wheel contact patch dimension along X-axis (longitudinal) in meters")
    wheel_dim_y: float = Field(default=0.20, gt=0, le=1, description="Wheel contact patch dimension along Y-axis (transverse) in meters")
    wheel_spacing_transverse: float = Field(default=0.8, gt=0, le=5, description="Distance between left/right wheels in meters")

    # Axle configuration (from ACCIDENTAL_VEHICLE_FORCE_* constants)
    force_axle_1_kn: float = Field(default=80.0, gt=0, le=500, description="Load on first axle in kN")
    force_axle_2_kn: float = Field(default=40.0, gt=0, le=500, description="Load on second axle in kN")
    axle_spacing_m: float = Field(default=1.2, gt=0, le=10, description="Spacing between axles in meters")
    wheel_spacing_longitudinal: float = Field(default=1.2, gt=0, le=5, description="Distance between axles (alias)")

    vehicle_type: Literal["accidental"] = Field(default="accidental", description="Vehicle type identifier")

    model_config = ConfigDict(validate_assignment=True)


class AmsterdamAccidentalVehicle(BaseModel):
    """
    Amsterdam-specific accidental vehicle specification.

    Defines geometry and load values for special heavy vehicle loads used
    in Amsterdam area bridges according to local traffic regulations.
    """

    # Geometry (from ACCIDENTAL_VEHICLE_*_AMSTERDAM constants)
    width: float = Field(default=2.0, gt=0, le=10, description="Vehicle width in meters")
    wheel_dim_x: float = Field(default=0.4, gt=0, le=1, description="Wheel contact patch dimension along X-axis (longitudinal) in meters")
    wheel_dim_y: float = Field(default=0.4, gt=0, le=1, description="Wheel contact patch dimension along Y-axis (transverse) in meters")
    wheel_spacing_transverse: float = Field(default=1.5, gt=0, le=5, description="Distance between left/right wheels in meters")

    # Load (from ACCIDENTAL_VEHICLE_FORCE_AMSTERDAM constant = 240 kN)
    force_single_axle_kn: float = Field(default=240.0, gt=0, le=500, description="Force on single axle in kN")

    vehicle_type: Literal["amsterdam_accidental"] = Field(default="amsterdam_accidental", description="Vehicle type identifier")

    model_config = ConfigDict(validate_assignment=True)


class TramVehicle(BaseModel):
    """
    Tram vehicle specification (placeholder for future implementation).

    Defines basic structure for tram vehicle loads to be used in future
    bridge analyses requiring tram track loading.
    """

    # Geometry (to be defined based on project requirements)
    length: float = Field(default=20.0, gt=0, le=50, description="Tram vehicle length in meters")
    width: float = Field(default=2.4, gt=0, le=10, description="Tram vehicle width in meters")
    wheel_dim_x: float = Field(default=0.6, gt=0, le=1, description="Wheel contact patch dimension along X-axis (longitudinal) in meters")
    wheel_dim_y: float = Field(default=0.6, gt=0, le=1, description="Wheel contact patch dimension along Y-axis (transverse) in meters")
    wheel_spacing_longitudinal: float = Field(default=2.0, gt=0, le=10, description="Distance between axles in meters")
    wheel_spacing_transverse: float = Field(default=1.5, gt=0, le=5, description="Distance between left/right wheels in meters")

    # Load (placeholder - to be defined)
    load_per_wheel_kn: float | None = Field(default=None, gt=0, le=1000, description="Load per wheel in kN")

    # Tram-specific
    track_gauge_m: float | None = Field(default=None, gt=1.0, le=2.0, description="Tram track gauge width in meters")

    vehicle_type: Literal["tram"] = Field(default="tram", description="Vehicle type identifier")

    @field_validator("track_gauge_m")
    @classmethod
    def validate_track_gauge(cls, v: float | None) -> float | None:
        """Validate track gauge is realistic for trams."""
        if v is not None and v < 1.0:
            raise ValueError(f"Track gauge {v}m is too narrow (minimum 1.0m)")
        if v is not None and v > 2.0:
            raise ValueError(f"Track gauge {v}m is too wide (maximum 2.0m)")
        return v

    model_config = ConfigDict(validate_assignment=True)


class VehiclePosition(BaseModel):
    """
    Position specification for vehicle placement on bridge.

    Defines the 3D coordinate position and orientation of a vehicle for
    load application in SCIA analysis.
    """

    x_coord: float = Field(description="Longitudinal position along bridge in meters")
    y_coord: float = Field(description="Transverse position across bridge width in meters")
    z_coord: float = Field(default=0.0, description="Vertical position (typically 0 for bridge deck)")
    rotation_degrees: float = Field(default=0.0, ge=-180, le=180, description="Vehicle rotation in degrees (for future tram tracks)")

    @field_validator("x_coord", "y_coord", "z_coord")
    @classmethod
    def validate_coordinate_ranges(cls, v: float) -> float:
        """Validate coordinate values are within realistic bridge dimensions."""
        if not (-1000 <= v <= 1000):
            raise ValueError(f"Coordinate {v}m is unrealistic (must be between -1000 and 1000m)")
        return v

    model_config = ConfigDict(validate_assignment=True)


class WheelLoad(BaseModel):
    """
    Individual wheel load specification.

    Defines load magnitude, contact area, and position for a single wheel
    in vehicle load calculations.
    """

    position: str = Field(description="Wheel position identifier")
    load_kn: float = Field(gt=0, le=500, description="Wheel load in kN")
    contact_area_m: float = Field(gt=0, le=1.0, description="Contact area dimension in meters")

    @field_validator("position")
    @classmethod
    def validate_position_identifier(cls, v: str) -> str:
        """Validate wheel position is from allowed set."""
        allowed_positions = {
            "front_left",
            "front_right",
            "rear_left",
            "rear_right",
            "front",
            "rear",
            "middle",
        }

        if v.lower() not in allowed_positions:
            valid = ", ".join(sorted(allowed_positions))
            raise ValueError(f"Position '{v}' not allowed. Must be one of: {valid}")
        return v.lower()

    model_config = ConfigDict(validate_assignment=True)


class VehicleRegistry(BaseModel):
    """
    Central registry of standard vehicle specifications.

    Provides singleton access to pre-configured vehicle models for all
    standard load cases (tandem, service, accidental, Amsterdam accidental, tram).
    """

    tandem: TandemSystemVehicle
    service: ServiceVehicle
    accidental: AccidentalVehicle
    amsterdam_accidental: AmsterdamAccidentalVehicle
    tram: TramVehicle | None = Field(default=None, description="Tram vehicle (optional, for future use)")

    model_config = ConfigDict(validate_assignment=True)


# Module-level constant: Standard vehicle registry instance
STANDARD_VEHICLES = VehicleRegistry(
    tandem=TandemSystemVehicle(),
    service=ServiceVehicle(),
    accidental=AccidentalVehicle(),
    amsterdam_accidental=AmsterdamAccidentalVehicle(),
    tram=TramVehicle(),
)
