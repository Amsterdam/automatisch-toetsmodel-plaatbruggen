"""
Common constants used across the src layer.

These constants are shared between different modules in the src layer
and should not depend on the app layer (VIKTOR SDK).
"""

# Maximum number of D-fields (D1 to D15) supported for load zones
MAX_LOAD_ZONE_SEGMENT_FIELDS = 15

# Parametrization options - single source of truth
# These are imported by both app layer (parametrization) and src layer (Pydantic models)
LOAD_ZONE_TYPES = ["Voetgangers", "Fietsers", "Auto", "Berm"]
CC_CLASS_OPTIONS = ["CC1a/b", "CC2", "CC3"]
DESIGN_CODE_OPTIONS = ["NEN 8700 verbouw", "NEN 8700 gebruik", "NEN 8700 afkeur"]
PAVEMENT_MATERIAL_OPTIONS = [
    "Asfalt",
    "Beton (normaal)",
    "Beton (gewapend)",
    "Klinkers",
    "Grind",
    "Tegels",
]
