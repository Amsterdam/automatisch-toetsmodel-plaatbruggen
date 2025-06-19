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


## 2. Installeren van alle requirements

Run setup_dev.py, dit script checkt of de juiste Python versie is gestalleerd en installeerd alle requirements. 

```bash
# In IDE terminal
python setup-dev.py
```

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

#### 2.4.2 Wijzigingen maken en committen

1. **Maak en commit wijzigingen:**
```bash
# Maak wijzigingen...
# Update de Changelog
git add .
git commit -m "Beschrijvende commit message"
```

#### 2.4.3 Run het ruft script

Het ruft script (ruft.py) voert een aantal acties uit om de code kwaliteit te waarborgen:
- Voert een commit uit (mocht dit nog niet zijn gedaan)
- Voert de ruff formating, ruff checks en mypy checks uit
- Voert de unit tests uit
- Voert viktor tests uit 
- Pushed de code naar de feature branch

Indien een check faalt krijg je dit te zien en kun je het oplossen. Run het ruft script vervolgens opnieuw.

#### 2.4.4 Pull Request aanmaken

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