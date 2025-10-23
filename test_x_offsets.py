"""Test X-direction offsets at span boundaries."""

from munch import Munch
from src.integrations.scia_integration.scia_section_on_plane import create_section_definitions

# Create a test bridge with a 5m span
# min_thickness = 0.7, so offset = 0.9 * 0.7 = 0.63
class MockParams:
    bridge_segments_array = [
        Munch({"is_first_segment": True, "bz1": 2.0, "bz2": 0.5, "bz3": 4.5, "dz": 0.7, "dz_2": 0.8, "l": 0, "is_support": "Verende oplegging (x,y)"}),
        Munch({"is_first_segment": False, "bz1": 2.0, "bz2": 0.5, "bz3": 4.5, "dz": 0.7, "dz_2": 0.8, "l": 5.0, "is_support": "Verende oplegging (x,y)"}),
    ]

sections = create_section_definitions(MockParams())
x_sections = [s for s in sections if "_x_sec_" in s["name"]]

print("=" * 80)
print("X-Direction Section Offset Test")
print("=" * 80)
print(f"\nSpan: x from 0.0 to 5.0 m")
print(f"min_thickness = 0.7 m")
print(f"Expected offset at start: +0.9 * 0.7 = +0.63 m")
print(f"Expected offset at end: -0.9 * 0.7 = -0.63 m")
print(f"Expected range: 0.63 to 4.37 m")

# Get unique x-positions for sections at same y
x_positions_set = set()
for section in x_sections:
    x_positions_set.add(section["point_1"][0])
    x_positions_set.add(section["point_2"][0])

x_positions_sorted = sorted(x_positions_set)

print(f"\nFirst section x-coordinates:")
first_section = x_sections[0]
print(f"  Start: {first_section['point_1'][0]:.2f} m (expected: 0.63)")
print(f"  End: {first_section['point_2'][0]:.2f} m (expected: 1.63)")

print(f"\nMinimum x-coordinate in all sections: {min(x_positions_sorted):.2f} m (expected: 0.63)")
print(f"Maximum x-coordinate in all sections: {max(x_positions_sorted):.2f} m (expected: 4.37)")

print(f"\nZ-offset for x-direction sections: {first_section['point_1'][2]:.2f} m (expected: 0.63)")

# Verify
start_correct = abs(min(x_positions_sorted) - 0.63) < 0.01
end_correct = abs(max(x_positions_sorted) - 4.37) < 0.01
z_correct = abs(first_section['point_1'][2] - 0.63) < 0.01

print(f"\nValidation:")
print(f"  ✓ Start offset correct: {start_correct}")
print(f"  ✓ End offset correct: {end_correct}")
print(f"  ✓ Z-offset correct: {z_correct}")

print("\n" + "=" * 80)
