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

# TODO: Load pavement material properties from CSV file according to Eurocode 1
# TODO: Implement material density lookup and kN/m² calculation
# TODO: Create materials.csv with specific masses for different pavement types
PAVEMENT_MATERIAL_OPTIONS = [
    "Asfalt",  # TODO: Add density value (typical: ~23 kN/m³)
    "Beton",  # TODO: Add density value (typical: ~24 kN/m³)
    "Klinkers",  # TODO: Add density value (typical: ~22 kN/m³)
    "Grind",  # TODO: Add density value (typical: ~18 kN/m³)
    "Tegels",  # TODO: Add density value (typical: ~20 kN/m³)
]

LOAD_ZONES_INFO_TEXT = """Definieer hier de werkelijke wegindeling op de brug, de belastingen worden hier automatisch van afgeleid.
De belastingen volgens de theoretische wegindeling worden automatisch gegenereerd op de achtergrond, hier hoef je niets voor in te vullen.

Elke zone wordt gestapeld vanaf één zijde van de brug.
Vul alleen breedtes in voor de daadwerkelijk gedefinieerde brugsegmenten (D-nummers) onder de tab Dimensies.
De laatste belastingzone loopt automatisch door tot het einde van de brug;
hiervoor hoeven dus geen segmentbreedtes (D-waardes) ingevuld te worden.

**Verharding eigenschappen:**
Per belastingzone kan de dikte en het materiaal van de wegverharding worden opgegeven.
Dit wordt gebruikt om het eigengewicht van de verharding te berekenen (dikte * soortelijke massa),
wat vervolgens als extra belasting in kN/m2 wordt toegepast in het SCIA model."""

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

# Combination table according to NEN-EN 1990 table NB.19
#
# Legend:
# X = Leading action     x = Included in combination     0 = Not included in combination
#
COMBINATION_TABLE = {
    "Perm": {
        "Permanente belasting": "X",
        "Voorspaning": "x",
        "Zetting": "",
        "TS": "",
        "UDL": "",
        "Enkele as": "",
        "Horizontale belasting": "",
        "Fiets- en voetpaden": "",
        "Mensenmenigte": "",
        "Bijzonder voertuigen": "",
        "Wind Fwk": "",
        "Wind Fw*": "",
        "Temperatuur": "",
        "Sneeuw": "",
        "Impact op of onder de brug": "",
        "Aardbevingsbelasting": "",
    },
    "Perm zet": {
        "Permanente belasting": "x",
        "Voorspaning": "x",
        "Zetting": "X",
        "TS": "",
        "UDL": "",
        "Enkele as": "",
        "Horizontale belasting": "",
        "Fiets- en voetpaden": "",
        "Mensenmenigte": "",
        "Bijzonder voertuigen": "",
        "Wind Fwk": "",
        "Wind Fw*": "",
        "Temperatuur": "",
        "Sneeuw": "",
        "Impact op of onder de brug": "",
        "Aardbevingsbelasting": "",
    },
    "gr1a": {
        "Permanente belasting": "x",
        "Voorspaning": "x",
        "Zetting": "",
        "TS": "X",
        "UDL": "X",
        "Enkele as": "",
        "Horizontale belasting": "x",
        "Fiets- en voetpaden": "x",
        "Mensenmenigte": "",
        "Bijzonder voertuigen": "",
        "Wind Fwk": "x",
        "Wind Fw*": "x",
        "Temperatuur": "x",
        "Sneeuw": "",
        "Impact op of onder de brug": "",
        "Aardbevingsbelasting": "",
    },
    "gr1b": {
        "Permanente belasting": "x",
        "Voorspaning": "x",
        "Zetting": "",
        "TS": "",
        "UDL": "",
        "Enkele as": "X",
        "Horizontale belasting": "",
        "Fiets- en voetpaden": "",
        "Mensenmenigte": "",
        "Bijzonder voertuigen": "",
        "Wind Fwk": "",
        "Wind Fw*": "",
        "Temperatuur": "",
        "Sneeuw": "",
        "Impact op of onder de brug": "",
        "Aardbevingsbelasting": "",
    },
    "gr2": {
        "Permanente belasting": "x",
        "Voorspaning": "x",
        "Zetting": "",
        "TS": "x",
        "UDL": "x",
        "Enkele as": "",
        "Horizontale belasting": "X",
        "Fiets- en voetpaden": "x",
        "Mensenmenigte": "",
        "Bijzonder voertuigen": "",
        "Wind Fwk": "x",
        "Wind Fw*": "x",
        "Temperatuur": "x",
        "Sneeuw": "",
        "Impact op of onder de brug": "",
        "Aardbevingsbelasting": "",
    },
    "gr3": {
        "Permanente belasting": "x",
        "Voorspaning": "x",
        "Zetting": "",
        "TS": "",
        "UDL": "",
        "Enkele as": "",
        "Horizontale belasting": "",
        "Fiets- en voetpaden": "X",
        "Mensenmenigte": "",
        "Bijzonder voertuigen": "",
        "Wind Fwk": "",
        "Wind Fw*": "",
        "Temperatuur": "",
        "Sneeuw": "",
        "Impact op of onder de brug": "",
        "Aardbevingsbelasting": "",
    },
    "gr4": {
        "Permanente belasting": "x",
        "Voorspaning": "x",
        "Zetting": "",
        "TS": "",
        "UDL": "",
        "Enkele as": "",
        "Horizontale belasting": "",
        "Fiets- en voetpaden": "x",
        "Mensenmenigte": "X",
        "Bijzonder voertuigen": "",
        "Wind Fwk": "",
        "Wind Fw*": "",
        "Temperatuur": "x",
        "Sneeuw": "",
        "Impact op of onder de brug": "",
        "Aardbevingsbelasting": "",
    },
    "gr5": {
        "Permanente belasting": "x",
        "Voorspaning": "x",
        "Zetting": "",
        "TS": "x",
        "UDL": "x",
        "Enkele as": "",
        "Horizontale belasting": "x",
        "Fiets- en voetpaden": "",
        "Mensenmenigte": "",
        "Bijzonder voertuigen": "X",
        "Wind Fwk": "x",
        "Wind Fw*": "x",
        "Temperatuur": "x",
        "Sneeuw": "",
        "Impact op of onder de brug": "",
        "Aardbevingsbelasting": "",
    },
    "Wind gr1a": {
        "Permanente belasting": "x",
        "Voorspaning": "x",
        "Zetting": "",
        "TS": "x",
        "UDL": "x",
        "Enkele as": "",
        "Horizontale belasting": "x",
        "Fiets- en voetpaden": "x",
        "Mensenmenigte": "",
        "Bijzonder voertuigen": "",
        "Wind Fwk": "X",
        "Wind Fw*": "",
        "Temperatuur": "x",
        "Sneeuw": "",
        "Impact op of onder de brug": "",
        "Aardbevingsbelasting": "",
    },
    "Wind gr2": {
        "Permanente belasting": "x",
        "Voorspaning": "x",
        "Zetting": "",
        "TS": "x",
        "UDL": "x",
        "Enkele as": "",
        "Horizontale belasting": "x",
        "Fiets- en voetpaden": "x",
        "Mensenmenigte": "",
        "Bijzonder voertuigen": "",
        "Wind Fwk": "X",
        "Wind Fw*": "",
        "Temperatuur": "x",
        "Sneeuw": "",
        "Impact op of onder de brug": "",
        "Aardbevingsbelasting": "",
    },
    "Temp gr1": {
        "Permanente belasting": "x",
        "Voorspaning": "x",
        "Zetting": "",
        "TS": "x",
        "UDL": "x",
        "Enkele as": "",
        "Horizontale belasting": "x",
        "Fiets- en voetpaden": "x",
        "Mensenmenigte": "",
        "Bijzonder voertuigen": "",
        "Wind Fwk": "x",
        "Wind Fw*": "",
        "Temperatuur": "X",
        "Sneeuw": "",
        "Impact op of onder de brug": "",
        "Aardbevingsbelasting": "",
    },
    "Temp gr2": {
        "Permanente belasting": "x",
        "Voorspaning": "x",
        "Zetting": "",
        "TS": "x",
        "UDL": "x",
        "Enkele as": "",
        "Horizontale belasting": "x",
        "Fiets- en voetpaden": "x",
        "Mensenmenigte": "",
        "Bijzonder voertuigen": "",
        "Wind Fwk": "x",
        "Wind Fw*": "",
        "Temperatuur": "X",
        "Sneeuw": "",
        "Impact op of onder de brug": "",
        "Aardbevingsbelasting": "",
    },
    "Sneeuw": {
        "Permanente belasting": "x",
        "Voorspaning": "x",
        "Zetting": "",
        "TS": "",
        "UDL": "",
        "Enkele as": "",
        "Horizontale belasting": "",
        "Fiets- en voetpaden": "",
        "Mensenmenigte": "",
        "Bijzonder voertuigen": "",
        "Wind Fwk": "",
        "Wind Fw*": "",
        "Temperatuur": "",
        "Sneeuw": "X",
        "Impact op of onder de brug": "",
        "Aardbevingsbelasting": "",
    },
    "Aanrijding gr1a": {
        "Permanente belasting": "x",
        "Voorspaning": "x",
        "Zetting": "",
        "TS": "x",
        "UDL": "x",
        "Enkele as": "",
        "Horizontale belasting": "x",
        "Fiets- en voetpaden": "x",
        "Mensenmenigte": "",
        "Bijzonder voertuigen": "",
        "Wind Fwk": "",
        "Wind Fw*": "",
        "Temperatuur": "",
        "Sneeuw": "",
        "Impact op of onder de brug": "X",
        "Aardbevingsbelasting": "",
    },
    "Aanrijding gr2": {
        "Permanente belasting": "x",
        "Voorspaning": "x",
        "Zetting": "",
        "TS": "x",
        "UDL": "x",
        "Enkele as": "",
        "Horizontale belasting": "x",
        "Fiets- en voetpaden": "x",
        "Mensenmenigte": "",
        "Bijzonder voertuigen": "",
        "Wind Fwk": "",
        "Wind Fw*": "",
        "Temperatuur": "",
        "Sneeuw": "",
        "Impact op of onder de brug": "X",
        "Aardbevingsbelasting": "",
    },
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
