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

# Note: Material paths are now managed by src.common.materials module

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

MAX_DIMENSION_SEGMENTS = 20  # Define how many segments we can have in the model
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
wat vervolgens als extra belasting in kN/m2 wordt toegepast in het SCIA model.

De lijnlast van de leuningbelasting kan hieronder worden opgegeven, deze staat standaard op 1 kN/m."""

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

SCIA_ZIP_README_CONTENT = """SCIA Engineer XML Bestanden - Brugmodel

Deze ZIP bevat de gegenereerde SCIA model bestanden:

1. [BrugID].xml - Hoofdmodel definitie met geometrie, materialen en mesh
2. viktor.xml.def - Definitie bestand met aanvullende model parameters
3. model.esa - Leeg template bestand met juiste project instellingen

BELANGRIJK - Hoe deze bestanden te gebruiken:

1. Pak ALLE 3 bestanden uit naar DEZELFDE MAP
   (Het is cruciaal dat de XML, DEF en ESA bestanden op dezelfde locatie staan)

2. Open SCIA Engineer (versie 24.0.3015.64 of compatibel)

3. Open het LEGE model.esa bestand uit de uitgepakte map
   (Dit dient als template met de juiste instellingen)

4. Klik in SCIA Engineer op "Bijwerken vanuit"

5. Klik op "XML bestand"

6. Selecteer het [BrugID].xml bestand uit dezelfde map

Dit zorgt ervoor dat de juiste instellingen en template configuratie worden gebruikt.



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

### Materiaal Compatibiliteit
SCIA Engineer ondersteunt een brede range aan materialen via string-gebaseerde namen:

**Volledig ondersteund:**
- **Alle moderne Eurocode materialen** (C12/15 tot C90/105, B500A/B/C)
- **Oudere Nederlandse materialen** (K150-K600, B12,5-B65)
- **Oude wapeningsstaal** (QR22-QR54, QRn32-QRn54, FeB 220/400/500)
- **Historische staalsoorten** (St. 37, St. 52, Speciaal st. 36/48)

**Voordeel:** SCIA accepteert materialen direct zoals ze in de project database staan.

### Download Opties
Gebruik de onderstaande knoppen om SCIA bestanden te downloaden:

### Toekomstige Uitbreidingen
- Complexe bruggeometrie (1:1 met werkelijke brugvorm)
- Variabele dikte per zone (dz, dz_2 parameters)
- Belastinggevallen en combinaties
- Geavanceerde materiaal eigenschappen
        """

# ===================================================================================================================
# Invoer Page dimensions segments explanation
# ===================================================================================================================

DIMENSIONS_SEGMENTS_EXPLANATION = """Definieer hier de dwarsdoorsneden (snedes) van de brug.
Elk item in de lijst hieronder representeert een dwarsdoorsnede.
- Het **eerste item** definieert de geometrie van het begin van de brug (snede D1).
- Elk **volgend item** definieert de geometrie van de *volgende* dwarsdoorsnede (D2, D3, etc.).
- Het veld '**Afstand tot vorige snede**' (`l`) geeft de lengte van het brugsegment *tussen* de voorgaande en de huidige snede.
  Dit veld is niet zichtbaar voor de eerste snede.
- De overige dimensievelden (zoals `bz1`, `bz2`, `dz` voor de dikte van zone 1 en 3, en `dz_2` voor de dikte van zone 2)
  beschrijven de eigenschappen van de *huidige* dwarsdoorsnede.
Standaard zijn twee dwarsdoorsneden (D1 en D2) voorgedefinieerd, wat resulteert in één brugsegment.
Pas de waarden aan, of voeg meer dwarsdoorsneden toe/verwijder ze via de '+' en '-' knoppen."""

# ===================================================================================================================
# IDEA StatiCa info text
# ===================================================================================================================

IDEA_INFO_TEXT = """## IDEA StatiCa RCS Integration

Deze pagina toont een preview van het IDEA RCS model en biedt download opties voor dwarsdoorsnede analyse.

### Model Informatie
Het huidige model is een **vereenvoudigde rechthoekige plaat** met wapening gebaseerd op:
- **Breedte**: Breedte van het eerste segment (bz1 + bz2 + bz3)
- **Dikte**: Realistische dekdikte (maximum 0.8m voor plaatanalyse)
- **Materiaal**: Standaard beton C30/37
- **Wapening**: Betonstaal B500B met diameter 12mm en onderlinge afstand 150mm
- **Bovenwapening**: Hart-op-hart afstand 150mm, betondekking 55mm
- **Onderwapening**: Hart-op-hart afstand 150mm, betondekking 55mm

### Materiaal Compatibiliteit
IDEA StatiCa ondersteunt alleen moderne Eurocode materialen:

**Direct ondersteund:**
- **B500A, B500B, B500C** (moderne Eurocode wapeningsstaal)
- **C12/15 tot C50/60** (standaard betonklassen)

**Automatische omzetting oude materialen:**
- **QR24, QR22** naar B500A (lage sterkte: 220-240 N/mm²)
- **QR30, QR40, FeB 400** naar B500B (medium sterkte: 300-400 N/mm²)
- **QR48, FeB 500** naar B500C (hoge sterkte: 400+ N/mm²)

**Aanbeveling:** Voor exacte materiaalcontrole, selecteer direct B500A/B/C in wapeningsinstellingen.

### Download Opties
Gebruik de onderstaande knoppen om IDEA RCS bestanden te downloaden:

### Toekomstige Uitbreidingen
- T-balken en kokerprofielen
- Variabele wapeningsconfiguraties per zone
- Realistische belastinggevallen uit bruggeometrie
- Uitbreiding van materiaalintegratie met Info pagina parameters
        """
