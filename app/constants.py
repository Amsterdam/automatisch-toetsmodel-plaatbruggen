"""Constants used throughout the application."""
# ===================================================================================================================
# Imports
# ===================================================================================================================

from pathlib import Path

# ===================================================================================================================
# Paths
# ===================================================================================================================

PROJECT_PATH = Path(__file__).parent.parent
README_PATH = PROJECT_PATH / "README.md"
CHANGELOG_PATH = PROJECT_PATH / "CHANGELOG.md"
CSS_PATH = PROJECT_PATH / "resources" / "styles" / "style.css"
OUTPUT_REPORT_PATH = PROJECT_PATH / "resources" / "templates" / "template_eindrapport.docx"
REINFORCEMENT_PATH = PROJECT_PATH / "resources" / "data" / "materials" / "betonstaalkwaliteit.csv"
BRIDGE_DATA_PATH = PROJECT_PATH / "resources" / "data" / "bridges" / "filtered_bridges.json"

# ===================================================================================================================
# Docs - Readme
# ===================================================================================================================

README_CONTENT = """
    html, body {
        height: 100%;
        margin: 0;
        padding: 0;
    }

    .container {
        display: flex;
        height: 100%;
    }

    .iframe-wrapper {
        flex: 1;
        margin: 10px;
        border: none;
    }

    .iframe {
        width: 100%;
        height: 100%;
        border: none;
    }

        </style>
    </head>
    <body>
        <div class="container">
        <div class="iframe-wrapper">
"""

# ===================================================================================================================
# Parametrization Constants
# ===================================================================================================================

MAX_LOAD_ZONE_SEGMENT_FIELDS = 15  # Define how many D-fields (D1 to D15) we'll support for load zones
LOAD_ZONE_TYPES = ["Voetgangers", "Fietsers", "Auto", "Berm"]


# ===================================================================================================================
# Tables from codes
# ===================================================================================================================

# Psi factors according to NEN 8701 table 1
PSI_FACTORS_NEN8701: dict[float, dict[int, float]] = {
    100: {20: 1.00, 50: 1.00, 100: 1.00, 200: 1.00},
    50: {20: 0.99, 50: 0.99, 100: 0.99, 200: 0.99},
    30: {20: 0.99, 50: 0.99, 100: 0.98, 200: 0.97},
    15: {20: 0.98, 50: 0.98, 100: 0.96, 200: 0.96},
    1: {20: 0.95, 50: 0.94, 100: 0.89, 200: 0.88},
    1 / 12: {20: 0.91, 50: 0.91, 100: 0.81, 200: 0.81},
}

# ===================================================================================================================
# SCIA zip readme content
# ===================================================================================================================

SCIA_ZIP_README_CONTENT = """SCIA Engineer XML Files - Bridge Model

This ZIP contains the generated SCIA model files:

1. bridge_model.xml - Main model definition with geometry, materials, and mesh
2. bridge_model.def - Definition file with additional model parameters

To use these files:
1. Open SCIA Engineer (version 24.0.3015.64 or compatible)
2. Create a new project or open existing template
3. Import the XML files: File > Import > XML files
4. Review the imported model geometry and settings
5. Define load cases and run analysis as needed

Note: This is a simplified rectangular plate model. Future versions will support:
- Complex bridge geometry matching actual shape
- Variable thickness per zone
- Load cases and combinations
- Advanced material properties

Generated from VIKTOR Bridge Assessment Tool
"""

# ===================================================================================================================
# SCIA info text
# ===================================================================================================================

SCIA_INFO_TEXT = """## SCIA Engineer Integration

Deze pagina toont een preview van het SCIA model en biedt download opties voor SCIA Engineer bestanden.

### Model Informatie
Het huidige model is een **vereenvoudigde rechthoekige plaat** gebaseerd op:
- **Lengte**: Som van alle segment lengtes (Afstand tot vorige snede)
- **Breedte**: Breedte van het eerste segment (bz1 + bz2 + bz3)
- **Dikte**: Vast op 0.5m (moet nog uitgebreid worden met variabele dikte per zone)
- **Materiaal**: Standaard beton C30/37

### Download Opties
Gebruik de onderstaande knoppen om SCIA bestanden te downloaden:

### Toekomstige Uitbreidingen
- Complexe bruggeometrie (1:1 met werkelijke brugvorm)
- Variabele dikte per zone (dz, dz_2 parameters)
- Belastinggevallen en combinaties
- Geavanceerde materiaal eigenschappen
        """
