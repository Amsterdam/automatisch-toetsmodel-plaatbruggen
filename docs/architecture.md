# Project Architectuur: automatisch-toetsmodel-plaatbruggen

Dit document beschrijft de voorgestelde architectuur voor de VIKTOR-applicatie gericht op geautomatiseerde brugberekeningen, met inzichten uit de conceptdocumentatie (v1, jan 2025).

## Doelstellingen

*   Scheiden van de kernberekeningslogica van de VIKTOR-interfacelaag.
*   Zorgen voor hoge testbaarheid van de kernlogica.
*   Bevorderen van onderhoudbaarheid en schaalbaarheid voor een complexe applicatie.
*   Potentieel hergebruik van de kernlogica met andere interfaces in de toekomst mogelijk maken.
*   Faciliteren van bulktesten van meerdere bruggen middels een parent/child-structuur.

## Voorgestelde Mapstructuur

```
automatisch-toetsmodel-plaatbruggen/
├── app/                     # VIKTOR applicatiepakket (Interface Laag), georganiseerd per feature/entiteit
│   ├── overview_bridges/   # Logica voor de batch calculatie entiteit
│   │   ├── controller.py      # Controller & Views
│   │   ├── parametrization.py
│   │   └── utils.py (optioneel)
│   ├── bridge/              # Logica voor de individuele brug entiteit
│   │   ├── controller.py      # Controller & Views
│   │   ├── parametrization.py
│   │   └── utils.py (optioneel)
├── src/                     # Kern berekening/logica pakket (Backend/Domein Laag) - GEEN VIKTOR IMPORTS
│   ├── bridge_analysis/     # Hoofdlogica voor brugberekeningen
│   │   ├── calculators/     # Modules voor specifieke berekeningstypen
│   │   │   ├── load_calculator.py   # Behandelt permanente, verkeers- (LM1, UDL/TS), temp lasten (H5.4)
│   │   │   ├── check_calculator.py  # Behandelt wapenings- & dwarskrachttoetsen (H6)
│   │   │   └── ...                # Andere specifieke calculators indien nodig
│   │   ├── models/          # Datastructuren (Pydantic aanbevolen)
│   │   │   ├── bridge_model.py    # Representeert bruggeometrie, materialen, zones
│   │   │   ├── load_model.py      # Representeert belastinggevallen, combinaties
│   │   │   └── result_model.py    # Representeert berekenings-/toetsingsresultaten
│   │   ├── types/           # Logica specifiek voor verschillende brugtypen (Type 0-3, H2)
│   │   │   ├── plate_bridge_base.py # Basis klasse/logica?
│   │   │   └── ...                # Type-specifieke implementaties
│   │   └── utils.py         # Utility functies voor analyse (bv. geometrie helpers)
│   ├── common/              # Gedeelde utilities/modellen over verschillende src/ modules
│   │   └── ...                # Gedeelde code
│   ├── integrations/        # Logica voor interactie met externe software
│   │   └── scia_interface.py  # Behandelt SCIA interactie
│   ├── constants/           # Gedeelde configuratie data
│   │   └── materials.json     # Standaard materiaaleigenschappen (Tabel 1-3)
│   └── ...
├── tests/                   # Unit- en integratietests
│   ├── test_app/            # Tests voor de app-laag (VIKTOR layer)
│   └── test_src/            # Unit tests voor de kernlogica (hoge prioriteit)
│       ├── test_bridge_analysis/
│       │   ├── test_calculators/
│       │   │   └── ...
│       │   ├── test_models/
│       │   │   └── ...
│       │   └── test_integrations/
│       │       └── test_scia_interface.py
│       └── ...
├── doc/                     # Documentatie map
│   └── architecture.md      # Dit bestand
├── viktor.config.toml       # VIKTOR app configuratie
├── requirements.txt         # Productie dependencies (viktor, numpy, scipy, pandas, etc.)
├── requirements_dev.txt     # Ontwikkeling dependencies (pytest, ruff, mypy, etc.)
├── pyproject.toml           # Build systeem en tool configuratie
├── .pre-commit-config.yaml  # Pre-commit hooks configuratie
├── .ruff.toml               # Ruff linter/formatter configuratie
├── .gitignore               # Git ignore regels
└── README.md                # Project beschrijving, setup instructies
```

## Laag Beschrijvingen en Werkwijze

1.  **`app/` (VIKTOR Laag):**
    *   Bevat alle VIKTOR SDK gerelateerde code, georganiseerd in submappen per feature of entiteit type (bv. `app/overview_bridges/`, `app/bridge/`).
    *   Elke submap bevat typisch:
        *   `parametrization.py`: Definieert de gebruikersinterface voor die feature/entiteit.
        *   `controller.py`: Orkestreert de workflow, definieert VIKTOR views en roept `src/` logica aan.
        *   Optioneel `utils.py` voor UI-specifieke helpers.
    *   Controllers (`app/.../controller.py`) beheren de interactie:
        *   Beheren VIKTOR entiteiten (bv. parent/child voor batch/bridge).
        *   Halen gebruikersinvoer op via `params` (gedefinieerd in `parametrization.py`).
        *   Halen configuraties op uit `src/constants/`.
        *   Roepen de kernlogica in `src/` aan.
        *   Verwerken resultaten uit `src/`.
        *   Genereren VIKTOR views (gedefinieerd binnen de controller zelf).
        *   Genereren potentieel PDF-rapporten (m.b.v. `utils.py` of direct in controller).

2.  **`src/` (Kern Logica Laag):**
    *   **Geen VIKTOR SDK imports toegestaan.** Bevat pure, herbruikbare Python logica.
    *   `bridge_analysis/`: Kern domeinlogica voor constructieve analyse en toetsen, volgens Eurocodes en specifieke richtlijnen (NEN 8700 serie, RBK, TAB).
        *   `calculators/`: Implementeert specifieke berekeningsstappen (lasten, toetsen).
        *   `models/`: Definieert duidelijke datacontracten voor intern gebruik en communicatie tussen lagen (Pydantic aanbevolen).
        *   `types/`: Behandelt variaties tussen verschillende brugtypen (Type 0-3).
    *   `integrations/`: Interfaces met externe tools.
        *   `scia_interface.py`: Beheert het gedetailleerde proces van het genereren van SCIA input XML, gebruik van template bestanden, uitvoeren van SCIA (mogelijk via `ESA_XML.exe`), en parsen van resultaten.
        *   *(Toekomst)* `idea_interface.py` kan hier worden toegevoegd als gedetailleerde doorsnedetoetsen met IDEA StatiCa later nodig zijn.
    *   `constants/`: Biedt toegang tot gedeelde, niet-gebruikersspecifieke data zoals standaard materialen geladen uit JSON/YAML bestanden.
    *   `common/`: Algemene utility functies.

3.  **`tests/` (Test Laag):**
    *   `test_src/`: Hoge prioriteit unit tests die de correctheid verifiëren van calculators, modellen, type-specifieke logica, en integratiecomponenten (bv. SCIA input generatie).
    *   `test_app/`: Lagere prioriteit tests voor UI helpers (`app/.../utils.py`) of potentieel integratietests voor de VIKTOR controllers (`app/.../controller.py`).

## Voordelen

*   **Duidelijke Scheiding:** Isoleert VIKTOR-specifieke zaken, maakt kernlogica herbruikbaar en onafhankelijk testbaar.
*   **Testbaarheid:** `src/` is gemakkelijk unit-testbaar.
*   **Onderhoudbaarheid:** Structuur sluit aan bij het domein, vereenvoudigt updates en debuggen.
*   **Schaalbaarheid:** Modulair ontwerp ondersteunt toevoegen van nieuwe brugtypen, berekeningen of externe tool integraties.

## Belangrijke Overwegingen

*   **Data Overdracht:** Gebruik goed-gedefinieerde Pydantic modellen (`src/models/`) voor robuuste data-uitwisseling tussen `app` en `src`.
*   **Configuratie Beheer:** Gebruik `src/constants/` voor gedeelde data, onderscheiden van gebruikersinvoer beheerd door VIKTOR.
*   **Interactie Externe Tool:** Encapsuleer alle SCIA-specifieke logica binnen `src/integrations/scia_interface.py`. Behandel potentiële fouten tijdens bestandsgeneratie, executie of parsen.
*   **Rapportage:** Plan hoe de `app` laag (specifiek controllers/utils) data verzamelt van `src` resultaten en de vereiste PDF rapporten genereert.
*   **Bulk Verwerking:** Ontwerp de controller in `app/overview_bridges/controller.py` om efficiënt child (`app/bridge/`) entiteiten te beheren en resultaten te aggregeren.
*   **Foutafhandeling:** Implementeer robuuste foutafhandeling door de gehele applicatie, speciaal voor interacties met externe tools en bestandsoperaties.

## SCIA ESA Model Caching en Download Gedrag

### Overzicht

De applicatie implementeert een slim caching mechanisme voor SCIA ESA model bestanden om onnodige herberekeningen te vermijden en de gebruikerservaring te verbeteren. Het systeem balanceert tussen snelheid (caching) en opslagbeperkingen (250 MB limiet per bestand).

### Cache Gedrag

#### ESA Model Caching

Het ESA model wordt **conditioneel gecached** op basis van bestandsgrootte:

- **Kleine modellen (< 250 MB)**: Worden volledig gecached bij eerste berekening
  - Volgende downloads zijn instant (direct vanuit cache)
  - Geen herberekening nodig
  
- **Grote modellen (≥ 250 MB)**: Worden **niet gecached**
  - Bij elke download wordt het model opnieuw gegenereerd
  - Voorkomt opslagproblemen en quota overschrijding
  - Gebruiker krijgt melding: *"ESA model te groot voor cache (X MB). Model wordt opnieuw gegenereerd..."*

#### Download Button Functionaliteit

Wanneer de gebruiker op "Download ESA Model" klikt:

1. **Check cache**: Systeem controleert of een gecached ESA model beschikbaar is
2. **Cache hit** (model < 250 MB, eerder gecached):
   - ESA model wordt direct uit cache gehaald
   - Download start onmiddellijk
3. **Cache miss** (model ≥ 250 MB of nog niet berekend):
   - Progress message toont: *"ESA model niet in cache. Model wordt opnieuw gegenereerd..."*
   - Volledige SCIA analyse wordt opnieuw uitgevoerd
   - ESA model wordt gegenereerd en gedownload
   - Model wordt **niet** gecached als het ≥ 250 MB is

### Technische Details

#### Implementatie Locaties

- **Cache logica**: `app/bridge/analysis_cache.py`
  - `extract_cacheable_scia_results()`: Bepaalt of ESA model gecached wordt
  - Voegt metadata toe aan cache summary: `esa_model_cached`, `esa_model_size_mb`, `esa_model_too_large`

- **Download logica**: `app/bridge/bridgeController/scia_integration.py`
  - `download_scia_esa_model()`: Entry point voor download
  - `_download_scia_esa_model_cached()`: Probeert cache eerst, valt terug naar herberekening
  - `_download_scia_esa_model_direct()`: Genereert ESA model on-demand

#### Size Check Implementatie

```python
esa_size_bytes = len(esa_model) if isinstance(esa_model, bytes) else 0
esa_size_mb = esa_size_bytes / (1024 * 1024)

if esa_size_mb < 250:
    cacheable["esa_model"] = esa_model
    cacheable["summary"]["esa_model_cached"] = True
else:
    cacheable["summary"]["esa_model_cached"] = False
    cacheable["summary"]["esa_model_too_large"] = True
```

### Cache Summary Metadata

De cache bevat metadata over ESA model status:

```python
{
    "summary": {
        "esa_model_cached": bool,      # True als ESA in cache zit
        "esa_model_size_mb": float,    # Grootte in MB
        "esa_model_too_large": bool,   # True als > 250 MB (niet gecached)
    }
}
```

### Gebruikerscommunicatie

Het systeem geeft duidelijke feedback tijdens download:

- Cache hit: *"✓ Cache gevonden - resultaten worden geladen..."*
- Te groot voor cache: *"ESA model te groot voor cache (X MB). Model wordt opnieuw gegenereerd..."*
- Niet gecached: *"ESA model niet in cache. Model wordt opnieuw gegenereerd..."*
- Fout: *"Onverwachte fout tijdens SCIA analyse: [details]. Probeer in plaats daarvan de XML-bestanden te downloaden."*

### Waarom 250 MB Limiet?

1. **VIKTOR Storage Quota**: Workspace heeft 5 GB totale opslag limiet
2. **Multiple Bridges**: Applicatie kan tientallen bruggen bevatten
3. **Safety Margin**: 250 MB per model zorgt voor ruimte voor ~20 grote modellen + overige data
4. **Performance**: Kleinere cache files zijn sneller om te schrijven/lezen
5. **Fallback**: Grote modellen kunnen altijd on-demand gegenereerd worden

### Best Practices voor Gebruikers

- **Kleine tot middelgrote bruggen**: Profiteer van instant downloads via cache
- **Grote/complexe bruggen**: Verwacht herberekening bij elke download (1-5 minuten)
- **Storage Management**: Gebruik "Cache Wissen" functie als storage vol is
- **Alternative Downloads**: XML bestanden zijn altijd gecached en klein (< 5 MB)

### Toekomstige Verbeteringen

Mogelijke optimalisaties:

1. **Compressie**: ESA files comprimeren voor kleinere storage footprint
2. **Smart Eviction**: Automatisch oude/grote cache entries verwijderen
3. **User Choice**: Optie om grote modellen wel/niet te cachen
4. **Incremental Updates**: Alleen gewijzigde delen opnieuw berekenen
 