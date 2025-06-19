# Testing Uitleg: Automatische Tests voor Brugtoetsingsproject

Dit document legt uit hoe ons automatische testsysteem werkt, hoe je ermee werkt, en hoe je problemen oplost.

## 🚀 Setup voor Nieuwe Developers

### Vereiste Versies
Dit project gebruikt specifieke versies om consistentie tussen lokale en CI omgevingen te garanderen:

- **Ruff** `0.11.7` (code style & formatting)
- **MyPy** `1.15.0` (type checking)
- **Python** `3.12+`

### 1️⃣ Initiële Setup (eenmalig)

**🚀 Quick Setup (Recommended):**
```bash
# 1. Clone het project
git clone <repository-url>
cd automatisch-toetsmodel-plaatbruggen

# 2. Install dependencies
viktor-cli install                    # Main VIKTOR dependencies
pip install -r requirements_dev.txt  # Development tools (Ruff, MyPy, etc.)

# 3. Automated setup verification
python setup_dev.py
```

**🔧 Manual Setup (Step-by-step):**
```bash
# 1-2: Same as above

# 3. Verify installation manually
python ruft.py --dry-run
```

### 2️⃣ Verificatie van Setup

Test of alles werkt:

```bash
# Test alle quality checks (zoals bij git push)
python ruft.py --dry-run

# Of gebruik het volledige script:
python scripts/quality_check_and_push.py --dry-run
```

**Verwachte output:**
```
>> Starting Quality Check and Push Workflow
============================================================
>> Iteration 1
----------------------------------------
[>] Running Ruff Style Check...
    [+] PASSED
[>] Running Ruff Formatter...
    [+] PASSED
[>] Running MyPy Type Check...
    [+] PASSED
[>] Running Unit Tests...
    [+] PASSED

>> Final Status Report
============================================================
  Ruff Style Check: [+] PASSED
  Ruff Formatter: [+] PASSED
  MyPy Type Check: [+] PASSED
  Unit Tests: [+] PASSED

[+] All quality checks passed!
```

### 3️⃣ Dagelijks Gebruik

**Voor elke feature/bugfix:**

```bash
# 1. Maak nieuwe branch
git checkout -b feature/nieuwe-functionaliteit

# 2. Maak je wijzigingen
# ... programmeren ...

# 3. Test je code
python ruft.py --dry-run

# 4. Als alles groen is, commit en push
git add .
git commit -m "feat: voeg nieuwe functionaliteit toe"
git push origin feature/nieuwe-functionaliteit
```

**De quality checks draaien automatisch bij `git push`!**

### 4️⃣ Troubleshooting Setup

**❌ `ModuleNotFoundError: No module named 'ruff'`**
```bash
pip install -r requirements_dev.txt
```

**❌ `viktor-cli command not found`**
```bash
# Install Viktor CLI first
pip install viktor-cli
# Then install dependencies
viktor-cli install
```

**❌ `python scripts/... not found`**
```bash
# Zorg dat je in de root directory bent:
cd automatisch-toetsmodel-plaatbruggen
ls -la  # Je moet 'scripts/' folder zien
```

**❌ Quality checks falen bij clean repository**
```bash
# Forceer clean install:
pip uninstall ruff mypy -y
pip install -r requirements_dev.txt
```

### 5️⃣ IDE Setup (Optioneel maar Aanbevolen)

**VS Code:**
```json
// .vscode/settings.json
{
    "python.linting.enabled": true,
    "python.linting.mypyEnabled": true,
    "ruff.args": ["--config=.ruff.toml"],
    "editor.formatOnSave": true,
    "python.defaultInterpreterPath": "./venv/Scripts/python"
}
```

**PyCharm:**
- External Tools → Add Ruff
- File Watchers → Add MyPy
- Code Style → Import from `.ruff.toml`

## 🎯 Wat Deze Kwaliteitscontroles Doen

Ons project heeft **4 automatische kwaliteitscontroles** bij elke push:

### 🔧 Code Formatting (Ruff Format)
- **Automatisch herformatteren** van code volgens project standaarden
- **Auto-commit** van formatting wijzigingen
- Push gaat door zonder handmatige actie nodig

### ✅ Code Style (Ruff Check)  
- Controleert code style issues (imports, unused variables, etc.)
- **Automatisch repareren** waar mogelijk
- Stopt push alleen bij onoplosbare issues

### 🔍 Type Checking (MyPy)
- Controleert type hints en type safety
- Helpt bugs vroeg te vangen
- Stopt push bij type errors

### 🧪 Unit Tests (~200 tests)
- **Kernberekeningen werken**: Brugberekeningen, belastingen, en toetsen
- **VIKTOR interface functioneert**: Views, controllers, en parametrization  
- **Geen regressies**: Vangt kapotte functionaliteit op voordat het productie bereikt

## 🎯 Push Workflow

### ✅ Succes Scenario
```bash
git push origin feature-branch
```
**Resultaat:**
```
🔧 AUTO-FORMATTING CODE
Reformatted 3 file(s)
✅ Formatting changes committed automatically
✅ CONTINUING WITH PUSH

✅ RUFF CHECK PASSED!
No code style issues found

✅ MYPY CHECK PASSED!
No type checking issues found

✅ Tests completed successfully! 188/188 tests passed.
```
→ Push slaagt automatisch, zelfs als code formatting nodig was!

### ❌ Faal Scenario
```bash
git push origin feature-branch
```
**Resultaat:**
```
❌ RUFF CHECK FAILED
Found 5 code style issues
Run the following command for detailed information:
  -> python scripts/run_ruff_check.py

❌ Tests failed! 3 failures out of 188 tests.

🔥 CONTROLLER TEST FAILURE! 🔥
Test: test_calculate_bridge_loads
Error: AssertionError: Expected load factor 1.35, got 1.0
```
→ Push wordt geweigerd. Los eerst de fouten op.

## 🧪 Test Types

### Core Logic Tests (`tests/test_src/`) - 120 tests
Testen berekeningen onafhankelijk van VIKTOR:

```python
def test_permanent_load_factor(self):
    """Test permanente belasting factor berekening."""
    factor = calculate_permanent_load_factor("unfavorable")
    self.assertEqual(factor, 1.35)  # Eurocode standaard
```

### VIKTOR Interface Tests (`tests/test_app/`) - 68 tests
Testen de VIKTOR interface:

```python
def test_get_3d_view_execution(self):
    """Test 3D view generatie."""
    result = self.controller.get_3d_view(self.default_params)
    self.assertIsInstance(result, GeometryResult)
```

## 🛠️ Wanneer Tests Toevoegen/Wijzigen

### Nieuwe Functionaliteit Toevoegen
1. **Schrijf eerst de test:**
```python
def test_new_calculation_method(self):
    result = new_calculation_method(input_data)
    self.assertEqual(result.factor, expected_value)
```

2. **Implementeer functie:**
```python
def new_calculation_method(input_data):
    return CalculationResult(factor=calculated_value)
```

### Bestaande Code Wijzigen
Update tests wanneer je verwacht gedrag verandert:
```python
# Voor: string output
def test_old_behavior(self):
    result = some_function()
    self.assertEqual(result, "old_format")

# Na: dictionary output  
def test_new_behavior(self):
    result = some_function()
    self.assertEqual(result, {"value": "new_format", "status": "ok"})
```

## 📁 Test Structuur

```
tests/
├── test_app/           # VIKTOR interface tests (68)
│   ├── test_bridge/
│   │   ├── test_controller.py
│   │   └── test_controller_views.py
│   └── test_overview_bridges/
└── test_src/           # Core logic tests (120)
    ├── test_bridge_analysis/
    └── test_common/
```

## 🚀 Tests en Kwaliteitscontroles Draaien

### Alle Kwaliteitscontroles (zoals bij push)
```bash
# Alle checks zoals bij git push
python scripts/run_ruff_check.py    # Code style + auto-fix
python scripts/run_ruff_format.py   # Code formatting + auto-commit
python scripts/run_mypy.py          # Type checking
python run_enhanced_tests.py        # Unit tests
```

### Alleen Tests
```bash
# Alle tests
python run_enhanced_tests.py

# Specifieke test
python -m unittest tests.test_src.test_common.test_gis_utils.TestGISUtils.test_specific_function -v

# Specifieke module
python -m unittest tests.test_app.test_bridge.test_controller_views -v
```

## 📄 Seed Files

Gebruik seed files voor complexe testdata:

```python
# tests/test_data/bridge_default_params.json
{
    "info": {"bridge_name": "Test Brug"},
    "geometry": {"length": 30.0, "width": 12.0}
}

# In tests:
def setUp(self):
    self.default_params = load_bridge_default_params()
```

**⚠️ Belangrijk:** Update seed files wanneer je parametrization wijzigt!

```python
# Parameter toegevoegd in parametrization.py:
input.geometry.height = NumberField("Hoogte", default=5.0)

# Update seed file:
{
    "geometry": {
        "length": 30.0,
        "width": 12.0,
        "height": 5.0  // ← VOEG DIT TOE
    }
}
```

## 🐛 Problemen Debuggen

### Code Style Issues
```bash
# Zie gedetailleerde ruff issues
python scripts/run_ruff_check.py

# Automatisch repareren waar mogelijk
# (gebeurt automatisch bij push, maar je kunt het ook handmatig doen)
```

### Type Checking Issues  
```bash
# Zie gedetailleerde mypy issues
python scripts/run_mypy.py
```

### Falende Tests
1. **Lees de foutmelding:**
```
Test: test_calculate_bridge_loads
Error: AssertionError: Expected load factor 1.35, got 1.0
```

2. **Draai lokaal:**
```bash
python -m unittest tests.test_app.test_bridge.test_controller.TestBridgeController.test_calculate_bridge_loads -v
```

3. **Los het probleem op:**
   - Check of je wijzigingen de verwachte output beïnvloedden
   - Verifieer of test verwachtingen nog kloppen
   - Update test als nieuwe functionaliteit correct is

## 🤖 AI Hulp Krijgen

Wanneer je vastzit, vraag een AI model om hulp met deze template:

```
Ik heb een falende test in mijn Python/VIKTOR project:

**Fout:** AssertionError: Expected load factor 1.35, got 1.0

**Test Code:**
[plak test code]

**Functie die getest wordt:**
[plak functie code]

**Wat ik veranderde:**
[beschrijf je wijzigingen]

**Vraag:** Is mijn test correct, of moet ik de functie repareren?
```

AI kan helpen met:
- Test logica uitleg
- Verwachtingen controleren tegen standaarden
- Mock setup voor VIKTOR tests
- Seed file structuur
- Edge case identificatie

## ✅ Best Practices

**WEL DOEN:**
- Schrijf tests voor nieuwe functies voordat je implementeert
- Gebruik beschrijvende testnamen: `test_bridge_load_calculation_with_traffic_load`
- Test edge cases: lege input, None waarden, extreme getallen
- Update tests bij functionaliteit wijzigingen
- Update seed files bij parameter wijzigingen
- Laat de automatische quality checks hun werk doen (auto-formatting, auto-fixing)
- Vraag AI om hulp wanneer je vastzit

**NIET DOEN:**
- Tests overslaan om push te laten slagen
- Tests verwijderen zonder goede reden
- Complexe logica in tests gebruiken
- Echte files/databases gebruiken in tests
- Seed files vergeten bij parametrization wijzigingen
- Quality checks omzeilen om "sneller" te pushen

## 🆘 Hulp Nodig?

- **Code style issues?** → `python scripts/run_ruff_check.py` voor details
- **Type checking errors?** → `python scripts/run_mypy.py` voor details  
- **Test faalt, weet niet waarom?** → Draai lokaal, check fout, of vraag AI
- **Nieuwe functie, welke test?** → Kijk naar vergelijkbare tests in zelfde module
- **VIKTOR test problemen?** → Check `tests/test_app/test_bridge/test_controller_views.py`
- **Core logic test problemen?** → Check `tests/test_src/` voorbeelden
- **Seed file updates?** → Check alle JSON files in `tests/test_data/`
- **Auto-commit werkt niet?** → Check git status en commit handmatig