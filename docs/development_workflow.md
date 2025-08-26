# Development Workflow

Deze workflow beschrijft hoe we samen ontwikkelen in de GitHub repository.

## 1. Branching Strategie

We gebruiken de volgende branches:

- **`main`**: Production
  - Stabiele, gepubliceerde versie
  - Hier mag alleen volledig werkende code staan
- **`development`**: Development 
  - Speeltuin voor ontwikkelaars
  - Code hier kan (tijdelijk) kapot zijn
  - Dit is de basis voor nieuwe features
- **Feature Branches**:
  - Vernoemd naar user story nummer en korte beschrijving
  - Bijvoorbeeld: `73822_korte_taak_beschrijving`
  - Aangemaakt *vanuit* `development`
  - Gemerged *terug naar* `development` via Pull Request


## 2. Development Environment Setup

Run `setup_dev.py` om automatisch de development environment in te stellen. Dit script:
- Controleert of Python 3.12+ is geïnstalleerd
- Maakt een RUFT virtual environment aan (`.ruft_venv/`)
- Installeert alle runtime en development dependencies
- Installeert VIKTOR CLI dependencies (optioneel)
- Geeft exacte instructies voor IDE setup

```bash
# In project root directory
python setup_dev.py
```

**IDE Setup (VS Code/Cursor):**
1. Open Command Palette (Ctrl+Shift+P)
2. Select "Python: Select Interpreter"
3. Choose: `.ruft_venv\Scripts\python.exe` (pad wordt getoond door setup script)
4. Dit zorgt voor correcte test discovery en linting

**Eerste keer testen:**
```bash
python ruft.py --dry-run    # Duurt 2-5 minuten eerste keer, daarna snel
```

**Testing:**
- Unit tests draaien automatisch via `ruft.py`
- Resource file access tests controleren dat alle bestanden correct toegankelijk zijn
- Tests gebruiken absolute paths om productie-problemen te voorkomen

## 3. Workflow

### 3.1 Issues aanmaken

- Issues worden aangemaakt voor elke nieuwe taak, bug of feature request
- Issues kunnen voortkomen uit:
  - De sprint
  - Reviews
  - Gebruik van de applicatie
- Zorg voor:
  - Een duidelijke titel en beschrijving
  - Relevante labels (e.g., `task`, `bug`, `feature`)

### 3.2 Starten met een Issue

- Wijs de issue toe aan een persoon die het oppakt

### 3.3 Feature Branch aanmaken

> **Note:** Dit kan alleen door @amsterdam.nl accounts

1. Navigeer naar de issue op GitHub
2. In de rechterkolom, onder "Development", klik op "Create a branch"
3. GitHub stelt een branch naam voor
   - Pas deze eventueel aan indien nodig
4. Zorg dat de branch wordt aangemaakt vanuit de `development` branch
5. Kies "Create Branch"

### 3.4 Werken in de Feature Branch

#### 3.4.1 Branch lokaal ophalen

Om in de feature branch te kunnen werken:

1. **Haal de nieuwe feature branch op:**
```bash
git fetch origin
```

2. **Checkout de feature branch lokaal:**
```bash
# Vervang <naam-van-de-feature-branch> door de daadwerkelijke naam
git checkout <naam-van-de-feature-branch>
# Bijvoorbeeld: git checkout 73822_korte_taak_beschrijving
```

#### 3.4.2 Wijzigingen maken en committen

1. **Maak en commit wijzigingen:**
```bash
# Maak wijzigingen...
# Update de Changelog
git add .
git commit -m "Beschrijvende commit message"
```

#### 3.4.3 Quality Checks en Push

Het `ruft.py` script voert automatisch alle quality checks uit en pushed naar GitHub:

```bash
python ruft.py              # Volledige workflow: checks + commit + push
python ruft.py --dry-run    # Alleen checks, geen commits/push
python ruft.py --no-push    # Checks + commit, maar geen push
```

**Het script doet automatisch:**
1. **Uncommitted changes**: Vraagt of je wilt committen
2. **Quality checks**: Ruff style check, Ruff formatter, MyPy, unit tests, VIKTOR tests
3. **Auto-fixes**: Ruff kan automatisch style issues oplossen
4. **Auto-commit**: Commits auto-fixes met duidelijke messages
5. **Iteratie**: Herhaalt tot geen fixes meer mogelijk zijn
6. **Final report**: Toont status van alle checks
7. **Push**: Pushed naar GitHub als alles slaagt

**Bij gefaalde checks:**
- Script toont exacte commando's om issues op te lossen
- Los handmatig op en run `python ruft.py` opnieuw
- Script blijft itereren tot alles werkt

#### 3.4.4 Pull Request aanmaken

Als alle wijzigingen uitgewerkt zijn, kan de feature branch samengevoegd worden in de development branch. Hiervoor moet een Pull Request (PR) aangemaakt worden.

1. Ga naar de repository op GitHub
2. Klik op "Pull requests" → "New Pull request"
3. Selecteer:
   - Base: `development`
   - Compare: je feature branch
4. Vul in:
   - Duidelijke beschrijving van wijzigingen
   - Link naar de issue
5. Maak de Pull Request aan

### 3.5 Code Review en Merge

1. Een beheerder controleert de Pull Request
2. Bij akkoord:
   - PR wordt gemerged in `development`
   - Issue wordt gesloten
   - Feature branch wordt automatisch verwijderd

### 3.6 Nieuwe Release

1. Beheerder:
   - Merged `development` naar `main`
   - Maakt een nieuwe release aan
2. Via CI/CD wordt de release automatisch:
   - Op de productie omgeving in VIKTOR geplaatst