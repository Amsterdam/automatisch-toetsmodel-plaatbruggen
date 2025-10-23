"""Quick verification of corrected offset."""

from munch import Munch
from src.integrations.scia_integration.scia_section_on_plane import create_section_definitions

class MockParams:
    bridge_segments_array = [
        Munch({"is_first_segment": True, "bz1": 2.0, "bz2": 0.5, "bz3": 4.5, "dz": 0.7, "dz_2": 0.8, "l": 0, "is_support": "Verende oplegging (x,y)"}),
        Munch({"is_first_segment": False, "bz1": 2.0, "bz2": 0.5, "bz3": 4.5, "dz": 0.7, "dz_2": 0.8, "l": 5.0, "is_support": "Verende oplegging (x,y)"}),
    ]

sections = create_section_definitions(MockParams())
x_section = [s for s in sections if "_x_sec_" in s["name"]][0]
y_section = [s for s in sections if "_y_sec_" in s["name"]][0]

print("Corrected offsets:")
print(f"  min_thickness = min(0.7, 0.8) = 0.7 m")
print(f"  X-direction offset = 0.9 * 0.7 = 0.63 m (positive)")
print(f"  Y-direction offset = 0.0 m")
print(f"\nActual values:")
print(f"  X-direction z-coordinate: {x_section['point_1'][2]:.2f} m")
print(f"  Y-direction z-coordinate: {y_section['point_1'][2]:.2f} m")
print(f"\n✓ Offset is now positive: {x_section['point_1'][2] > 0}")
