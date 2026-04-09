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
        "load_case_count": "1",
    },
    {
        "include": True,
        "load_type": "Permanent",
        "load_case_range": "BG2001-BG2005",
        "load_case_count": "5",
    },
    {
        "include": True,
        "load_type": "Temperatuur",
        "load_case_range": "BG3001-BG3004",
        "load_case_count": "4",
    },
    {
        "include": True,
        "load_type": "UDL",
        "load_case_range": "BG4000 serie",
        "load_case_count": "dynamisch",  # Estimated default
    },
    {
        "include": True,
        "load_type": "Voetgangers",
        "load_case_range": "BG5001",
        "load_case_count": "1",
    },
    {
        "include": True,
        "load_type": "Dienstvoertuig",
        "load_case_range": "BG6000 serie",
        "load_case_count": "dynamisch",  # Estimated default
    },
    {
        "include": True,
        "load_type": "Onbedoeld voertuig",
        "load_case_range": "BG7000 serie",
        "load_case_count": "dynamisch",  # Estimated default
    },
    {
        "include": True,
        "load_type": "TS",
        "load_case_range": "BG8000-BG10000 serie",
        "load_case_count": "dynamisch",  # Estimated default
    },
    {
        "include": True,  # Default to True - gating logic enforces conditions in load case creation
        "load_type": "Tram",
        "load_case_range": "BG11000-BG12000 serie",
        "load_case_count": "dynamisch",  # Estimated default
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

# Maximum number of bridges to include in chat context
MAX_BRIDGES_IN_CHAT_CONTEXT = 60

# Field descriptions for LLM chat context
CHAT_FIELD_DESCRIPTIONS = {
    "construction_year": "Stichtingsjaar van de brug (filtered_bridges.json of parametrisatie).",
    "total_length_m": "Totale lengte in meters; voorkeur uit parametrisatie, anders filtered_bridges.json.",
    "total_width_m": "Totale brugbreedte in meters (voor zover bekend).",
    "max_uc": "Hoogste unity check (UC) uit IDEA; UC ≥ 1 betekent afkeur.",
    "uc_status": "IDEA-status: PASSED of FAILED op basis van max UC.",
    "classification": (
        "Verwerkingsstatus: calculated (berekend), failed (berekend maar UC ≥ 1 of fout), "
        "pending (wel compleet, nog niet berekend) of not_ready (ontbrekende invoer)."
    ),
    "cached": "Geeft aan of resultaten rechtstreeks uit de analyse-cache komen.",
    "missing_fields": "Lijst van ontbrekende verplichte invoervelden indien de brug nog niet berekend kan worden.",
}

# Storage keys for batch calculation
LAST_BATCH_RUN_KEY = "batch_calculation_last_run"
STORAGE_STATUS_KEY = "batch_calculation_storage_status"

# ---------------------------------------------------------------------------
# Result object type options for SCIA calculation
# ---------------------------------------------------------------------------
# These string constants match the OptionField options in the parametrization.
# Only one type can be active at a time.
RESULT_OBJECT_INTEGRATION_STRIPS: str = "Integratiestroken"
RESULT_OBJECT_SECTIONS_ON_PLANE: str = "Secties op vlak"

# ---------------------------------------------------------------------------
# Feature toggle fallbacks for SCIA result objects
# ---------------------------------------------------------------------------
# Used when the parametrization OptionField is not yet present (backward compat).
# ENABLE_SECTIONS_ON_PLANE is False so the safe default is integration strips.
ENABLE_INTEGRATION_STRIPS: bool = False
ENABLE_SECTIONS_ON_PLANE: bool = True
