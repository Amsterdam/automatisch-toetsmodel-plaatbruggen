"""
|
Technical constants specific to the app layer.

These constants define app-specific technical limits and parameters
that are only used within the VIKTOR application layer.
"""

from typing import Any

# Maximum number of bridge segments supported in the model
MAX_DIMENSION_SEGMENTS = 20

# Default content for load case selection table (static values)
LOAD_CASE_SELECTION_DEFAULT: list[dict[str, Any]] = [
    {
        "include": True,
        "load_type": "Eigen gewicht",
        "load_case_range": "BG1001",
        "load_case_count": 1,
    },
    {
        "include": True,
        "load_type": "Permanent",
        "load_case_range": "BG2001-BG2005",
        "load_case_count": 5,
    },
    {
        "include": True,
        "load_type": "Temperatuur",
        "load_case_range": "BG3001-BG3004",
        "load_case_count": 4,
    },
    {
        "include": True,
        "load_type": "UDL",
        "load_case_range": "BG4001-BG4003",
        "load_case_count": 3,
    },
    {
        "include": True,
        "load_type": "Voetgangers",
        "load_case_range": "BG5001",
        "load_case_count": 1,
    },
    {
        "include": True,
        "load_type": "Dienstvoertuig",
        "load_case_range": "BG6001-BG6xxx",
        "load_case_count": 20,  # Estimated default
    },
    {
        "include": True,
        "load_type": "Onbedoeld voertuig",
        "load_case_range": "BG7001-BG7xxx",
        "load_case_count": 50,  # Estimated default
    },
    {
        "include": True,
        "load_type": "TS",
        "load_case_range": "BG8001-BG10xxx",
        "load_case_count": 30,  # Estimated default
    },
]

# Calculation level options for traffic loads
CALCULATION_LEVEL_OPTIONS = [
    "Theoretische wegindeling",
    "Werkelijke wegindeling",
    "Werkelijke wegindeling onderliggend wegennet",
    "Werkelijke wegindeling met bebording",
]

# Signage options for bridge weight limits
SIGNAGE_OPTIONS = [
    "50 ton",
    "45 ton",
    "40 ton",
    "35 ton",
    "30 ton",
    "25 ton",
    "20 ton",
]
