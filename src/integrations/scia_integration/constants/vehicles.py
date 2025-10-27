"""
Vehicle load constants for SCIA integration.

These constants define vehicle specifications, dimensions, and load values
used in service vehicle and accidental vehicle load calculations.

NOTE: These constants are being migrated to Pydantic models in src.data_models.vehicle_models.
Consider using STANDARD_VEHICLES from src.data_models for new code.
Existing constants are maintained for backward compatibility during transition.
"""

# Service vehicle loads (NEN-EN 1991-2 art. 5.3.2.3)
SERVICE_VEHICLE_FORCE_PER_AXLE = 25 * 1000  # 25 kN converted to N
SERVICE_VEHICLE_LENGTH = 3.0  # Vehicle length in meters
SERVICE_VEHICLE_WIDTH = 1.75  # Vehicle width in meters
SERVICE_VEHICLE_WHEEL_CONTACT_AREA = 0.25  # Square contact area side length in meters
SERVICE_VEHICLE_INSET_DISTANCE = 0.5  # Distance from bridge edge to outer wheel in meters

# Accidental vehicle loads (NEN-EN 1991-2 art. 5.3.2.3(1)P)
ACCIDENTAL_VEHICLE_FORCE_AXLE_1 = 80 * 1000  # Q_sv1 = 80 kN converted to N
ACCIDENTAL_VEHICLE_FORCE_AXLE_2 = 40 * 1000  # Q_sv2 = 40 kN converted to N
ACCIDENTAL_VEHICLE_FORCE_AMSTERDAM = 240 * 1000  # Q_sv = 240 kN converted to N

# Accidental vehicle dimensions
ACCIDENTAL_VEHICLE_WIDTH_STANDARD = 1.30  # Standard vehicle width in meters
ACCIDENTAL_VEHICLE_WIDTH_AMSTERDAM = 2.0  # Amsterdam vehicle width in meters
ACCIDENTAL_VEHICLE_WHEEL_CONTACT_AREA_STANDARD = 0.20  # Standard contact area in meters
ACCIDENTAL_VEHICLE_WHEEL_CONTACT_AREA_AMSTERDAM = 0.4  # Amsterdam contact area in meters
ACCIDENTAL_VEHICLE_AXLE_SPACING = 1.2  # Distance between axles in meters
ACCIDENTAL_VEHICLE_INSET_DISTANCE = 0.5  # Distance from bridge edge in meters

# Vehicle length for sequencing
SERVICE_VEHICLE_LENGTH_FOR_SEQUENCING = 3.25  # Length used in tandem system sequencer
