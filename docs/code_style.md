# Code Style en Linting

Dit project gebruikt **Ruff** voor het handhaven van code style (volgens PEP 8) en voor linting (het opsporen van potentiële fouten). Er wordt ook gebruik gemaakt van **Mypy** voor statische type checking en **pre-commit** voor automatische checks bij het committen.

## Installatie

### VIKTOR Applicatie

De hoofd-dependency voor het draaien van de VIKTOR applicatie zelf wordt geïnstalleerd via:


```bash
pip install viktor
```
(Normaal gesproken wordt dit afgehandeld door de VIKTOR CLI of `requirements.txt`)

### Ontwikkel-Dependencies (Ruff, Mypy, Pre-commit, etc.)

Ruff, pre-commit, Mypy, en andere ontwikkel-dependencies staan gedefinieerd in `../requirements_dev.txt`.

Om deze dependencies te installeren, activeer eerst de virtual environment van het project en voer dan het volgende commando uit vanuit de hoofdmap (`automatisch-toetsmodel-plaatbruggen/`):

```bash
pip install -r requirements_dev.txt
```

## Pre-commit Hooks (Automatische Checks)

Dit project maakt gebruik van `pre-commit` om automatisch checks (zoals Ruff) uit te voeren voordat je code commit naar Git. Dit helpt om te zorgen dat code die gecommit wordt voldoet aan de standaarden.

Nadat je de ontwikkel-dependencies hebt geïnstalleerd (zie Installatie), moet je de Git hooks installeren met het volgende commando (uitgevoerd vanuit de hoofdmap):

```bash
pre-commit migrate-config
pre-commit install --hook-type pre-push
```

Nu zullen de geconfigureerde checks automatisch draaien elke keer dat je `git commit` probeert uit te voeren. Als een check faalt (bijvoorbeeld Ruff vindt fouten), zal de commit worden afgebroken. Je moet dan de fouten oplossen (vaak kan Ruff dit automatisch met `ruff check . --fix`) en de gewijzigde bestanden opnieuw toevoegen (`git add ...`) voordat je opnieuw probeert te committen.

## Handmatige Checks

Je kunt de checks ook handmatig uitvoeren.

### Ruff (Style & Linting)

Controleren:
```bash
ruff check .
```

Automatisch corrigeren (voor zover mogelijk):
```bash
ruff check . --fix
```

### Mypy (Type Checking)

Voer statische type checks uit:
```bash
mypy .
```
Dit controleert of de type hints in de code consistent zijn.

