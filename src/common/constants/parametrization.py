"""
Parametrization constants for UI field options and validation.

These constants define the available options for dropdown fields, radio buttons,
and other UI elements. They are used by both the app layer (parametrization)
and src layer (Pydantic model validation) to ensure consistency.

Single source of truth for all parametrization options.
"""

# Load zone types for bridge analysis
LOAD_ZONE_TYPES = ["Voetgangers", "Fietsers", "Auto", "Berm"]

# Consequence classes according to NEN 8700
CC_CLASS_OPTIONS = ["CC1a/b", "CC2", "CC3"]

# Design codes and safety levels
DESIGN_CODE_OPTIONS = ["NEN 8700 verbouw", "NEN 8700 gebruik", "NEN 8700 afkeur"]

# Pavement material options for load zones
PAVEMENT_MATERIAL_OPTIONS = [
    "Asfalt",
    "Beton (normaal)",
    "Beton (gewapend)",
    "Klinkers",
    "Grind",
    "Tegels",
]
