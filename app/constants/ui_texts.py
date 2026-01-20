"""
UI text constants for help texts, explanations, and content.

These constants contain all the text content displayed in the VIKTOR
application interface, including help texts, explanations, and documentation.
"""

# README content for the application
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

# Load zones explanation text
LOAD_ZONES_INFO_TEXT = """Definieer hier de werkelijke wegindeling op de brug, de belastingen worden hier automatisch van afgeleid.
De belastingen volgens de theoretische wegindeling worden automatisch gegenereerd op de achtergrond, hier hoef je niets voor in te vullen.

Elke zone wordt gestapeld vanaf één zijde van de brug.
Vul alleen breedtes in voor de daadwerkelijk gedefinieerde brugsegmenten (D-nummers) onder het tabblad dimensies.
De laatste belastingzone loopt automatisch door tot het einde van de brug;
hiervoor hoeft geen breedte ingevuld te worden.

De tramzone dient te worden geselecteerd wanneer er een gescheiden trambaan is. In het geval van een tramzone moet een breedte
van 1,5 m worden aangehouden. Ieder tramspoor wordt afzonderlijk ingevoerd. De overige delen tussen- en naast de trambaan worden als berm
gedefinieerd. De breedte van 1,5 m is praktisch gekozen om overige belastingzones in te passen. De voertuigbreedte van de tram is 1,435 m,
gelijk aan de spoorbreedte.

Wanneer er autoverkeer op de trambaan kan komen, dient dit te worden gemodelleerd als rijbaan en dienen tussenstukken zoals berm etc.
te worden verwaarloosd. In dit geval krijg je een brede auto zone in het midden van het dek, tussen de fiets- en voetpaden. Er wordt dan
geen trambelasting gemodelleerd, maar enkel de verkeersbelasting van de auto zone omdat dit altijd maatgevend is ten opzichte van de
trambelasting.

**Verharding eigenschappen:**
Per belastingzone kan de dikte en het materiaal van de wegverharding worden opgegeven.
Dit wordt gebruikt om het eigengewicht van de verharding te berekenen (dikte * soortelijke massa),
wat vervolgens als extra belasting in kN/m2 wordt toegepast in het SCIA model.

De lijnlast van de leuningbelasting kan hieronder worden opgegeven, deze staat standaard op 1 kN/m."""

# SCIA ZIP readme content
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

# SCIA integration info text
SCIA_INFO_TEXT = """## SCIA Engineer Integratie

Deze pagina toont het SCIA model en de analyseresultaten. De krachten worden uitgelezen via
"section on 2D members" en vormen de input voor IDEA toetsingen.

### Tabbladen

- **3D Model**: Interactieve 3D-weergave van het brugmodel.
- **SCIA Analyse Resultaten**: Maximale snedekrachten per zone voor IDEA toetsingen.

### Download Opties
- **Download input files** → XML + DEF + ESA template in ZIP voor handmatige import in SCIA.
- **Download ESA Model** → ESA inclusief berekeningsresultaten (doorgerekend).
  - Kleine modellen (< 250 MB): Direct uit cache (instant download bij tweede keer).
  - Grote modellen (≥ 250 MB): Wordt elke keer opnieuw berekend (10+ minuten).
- **Download SCIA Output XML** → Output resultaten in XML format (doorgerekend).
"""

# Dimensions segments explanation
DIMENSIONS_SEGMENTS_EXPLANATION = """Definieer hier de dwarsdoorsneden (snedes) van de brug.

### Globale dimensies (bovenaan)
Gebruik de invoervelden **bovenaan** om snel dimensies toe te passen op alle segmenten tegelijk:
- Vul de gewenste waarden in voor breedte zone 1, 2, 3 en dikte zone 1+3 en zone 2.
- Klik op de knop **"Pas dimensies toe op alle segmenten"** om deze waarden naar alle segmenten te kopiëren.

### Individuele segmenten (tabel)
Elk item in de tabel hieronder representeert een dwarsdoorsnede:
- Het **eerste item** definieert de geometrie van het begin van de brug (snede D1).
- Elk **volgend item** definieert de geometrie van de *volgende* dwarsdoorsnede (D2, D3, etc.).
- Het veld '**Afstand tot vorige snede**' geeft de lengte van het brugsegment *tussen* de voorgaande en de huidige snede.
  Dit veld is niet zichtbaar voor de eerste snede.
- Het veld '**Oplegging**' geeft aan of de snede een oplegging bevat.

Standaard zijn vier dwarsdoorsneden (D1 t/m D4) voorgedefinieerd, wat resulteert in drie brugsegmenten.
Voeg meer dwarsdoorsneden toe/verwijder ze via de '+' en '-' knoppen.

**Let op:** De brug bestaat altijd uit drie zones (1, 2 en 3). Voor een brug met slechts één dikte,
vul je dezelfde waarde in voor 'Dikte zone 1 en 3' en 'Dikte zone 2'.

"""

# Reinforcement explanation text
REINFORCEMENT_INFO_TEXT = """Op deze pagina kan de wapening van de brug worden ingevoerd.
Er kunnen oneindig veel wapeningconfiguraties worden toegevoegd.
Er kan per configuratie worden aangegeven in welke zones deze moet worden toegepast.
De zones corresponderen met de plaatzones die worden gegenereerd op basis van de geometrie:
- Bij de minimale geometrie (2 doorsnedes) ontstaan er 3 zones: "1-1", "2-1" en "3-1"
- Voor elke extra doorsnede komen er 3 nieuwe zones bij: "1-2", "2-2", "3-2", etc.
- Het getal voor het streepje correspondeert met de zone (1=links, 2=midden, 3=rechts)
- Het getal na het streepje geeft aan bij welk segment de zone hoort

Eerst wordt er gevraagd naar de eigenschappen van de hoofdwapening in langs- en dwarsrichting.
Vervolgens kan er aangeklikt worden, of er extra bijlegwapening aanwezig is in de configuratie.
Wanneer dit wordt aangevinkt, verschijnen dezelfde invoervelden nogmaals, om deze bijlegwapening te definiëren.
In het model, wordt deze bijlegwapening automatisch tussen het bestaande hoofdwapeningsnet gelegd, met dezelfde hart op hart afstand.

Zorg ervoor dat elke zone altijd precies 1 keer is aangevinkt, anders kan het model niet correct worden gegenereerd.
Houdt rekening met laadtijd van het model, wanneer er veel zones en wapeningsconfiguraties worden gedefinieerd."""

# IDEA StatiCa integration info text
IDEA_INFO_TEXT = """## IDEA StatiCa RCS Integratie

Deze pagina toont de IDEA RCS snedetoetsingen en IDEA download opties.

### Modelopbouw in 5 stappen
Het proces werkt als volgt:
1. Uit het SCIA model worden met "2D sections on members" de snedekrachten (ULS & SLS freq) uitgelezen via integratie strips.
2. Deze krachten worden automatisch uit de SCIA-resultaten gehaald.
3. Per zone worden de maximale absolute waarden bepaald (envelope).
4. De resultaten worden van SCIA omgezet naar het IDEA-formaat:
   - **X-richting strips (dwars/transversaal):**
     - N → N (normaalkracht)
     - V_z → Qz (dwarskracht)
     - M_x → My (buigend moment)
   - **Y-richting strips (langs/longitudinaal):**
     - N → N (normaalkracht)
     - V_z → Qz (dwarskracht)
     - M_y → My (buigend moment)
   - **Gecorrigeerd kolom:** Geeft aan of de waarden gecorrigeerd zijn omdat de integratie strip een breedte < 1 m heeft.
     De krachten worden automatisch omgerekend naar krachten per meter breedte.
5. **Belangrijk:** Voor elke unieke plaat (combinatie van plaatdikte en wapeningsconfiguratie)
    worden altijd **2 extremen** aangemaakt (langs- en dwarsrichting).
    Dit is nodig om zowel de langs- als de dwarswapening te kunnen toetsen in IDEA.

Voor elke unieke combinatie van plaatdikte en wapening worden alle relevante krachtencombinaties als extremen toegevoegd.


### Tabbladen
- **Tabblad 1**: Unieke plaatelementen (combinatie van plaatdikte en wapeningsconfiguratie)
- **Tabblad 2**: Snedetoetsing resultaten

### Download Opties
Gebruik de onderstaande knoppen om IDEA RCS bestanden te downloaden:"""

CALCULATION_SETTINGS_INFO_TEXT = """Hier kunnen de berekeningsinstellingen voor het model worden opgegeven.
Eerst wordt gevraagd om de gevolgklasse en het veiligheidsniveau te selecteren. Deze bepalen de factoren in de belastingcombinaties.
De factoren worden automatisch geupdate in de belastingcombinatie tabel aan de rechterkant van het scherm."""

CALCULATION_SETTINGS_INFO_TEXT_CALCULATION_LEVEL = """Hieronder kan het gewenste berekeningsniveau worden geselecteerd.
Ten eerste moet een keuze worden gemaakt tussen de theoretische wegindeling of de werkelijke wegindeling.
Bij de theoretische wegindeling worden de standaard verkeersbelastingen uit de norm toegepast over de volledige breedte van de brug.
Bij de werkelijke wegindeling worden de verkeersbelastingen verdeeld over de verschillende zones zoals opgegeven in het tabblad 'Belastingzones'.
Wanneer de brug hierop niet voldoet, kan er gekozen worden om de brug te berekenen op het onderliggend wegennet, of met een lastbeperking.
Hierbij wordt de grootte van de verkeersbelasting aangepast.
De aanpassingen van de verkeersbelastingen zijn niet te zien in de Viktor app, maar worden direct doorgestuurd naar het SCIA model.
Vergeet de pagina niet op te slaan na het maken van wijzigingen, voordat je het SCIA model aanmaakt."""

# Load case selection header text
LOAD_CASE_SELECTION_HEADER_TEXT = """## Belastingselectie
Selecteer welke belastingen worden gegenereerd in het SCIA model.
Dit helpt om de rekentijd te beheren tijdens het testen van specifieke belastingen.
**Let op:** Trambelastingen kunnen alleen worden ingeschakeld wanneer:
1. De verkeersbelasting is ingesteld op 'Werkelijke wegindeling' (een van de drie opties).
2. Er minimaal één tram belastingzone is gedefinieerd op het tabblad 'Belastingzones'.

De onderstaande radio button bestuurt op welke zijde van het brugdek de belastingen voor het dienstvoertuig en onbedoeld voertuig worden geplaatst.
Door deze maar aan 1 kant te plaatsen, bijvoorbeeld de maatgevende zijde waar de rijstroken het dichtste bij de rand liggen,
kan het aantal belastinggevallen worden beperkt."""

# Load case selection note text
LOAD_CASE_SELECTION_NOTE_TEXT = """**Let op:** Het uitschakelen van belastingen kan de rekentijd aanzienlijk verkorten,
maar kan ook leiden tot onvolledige resultaten. Gebruik dit alleen voor testdoeleinden."""

# OPTIMIZATION_EXPLANATION_TEXT
OPTIMIZATION_EXPLANATION_TEXT = """Op deze pagina kan een optimalisatie berekening worden uitgevoerd.
Tijdens de optimalisatie worden de volgende berekeningsniveaus doorlopen:
1.  Theoretische wegindeling
2.  Werkelijke wegindeling
3.  Werkelijke wegindeling onderliggend wegennet
4.  Werkelijke wegindeling met bebording - 50 ton
5.  Werkelijke wegindeling met bebording - 45 ton
6.  Werkelijke wegindeling met bebording - 40 ton
7.  Werkelijke wegindeling met bebording - 35 ton
8.  Werkelijke wegindeling met bebording - 30 ton
9.  Werkelijke wegindeling met bebording - 25 ton
10.  Werkelijke wegindeling met bebording - 20 ton

Tijdens elke stap worden de resultaten gecontroleerd op slagingscriteria (IDEA capaciteit en schuifsterkte toetsing).
Als de resultaten voldoen aan de slagingscriteria, wordt de optimalisatie gestopt en worden de resultaten weergegeven.

Door op "Start Optimalisatie" te klikken, wordt de optimalisatie gestart.
Na voltooiing worden de resultaten van de optimalisatieberekeningen weergegeven.
Het is mogelijk in de resultaten lijst te klikken op een specifieke rij om alle invoergegevens behorende bij die berekening in te laden.
Omdat de berekeningen worden gecahched, kunnen de resultaten snel worden bekeken zonder opnieuw te hoeven rekenen.

**Let op:** Deze optimalisatie kan enige tijd duren, afhankelijk van de complexiteit van het model en berekening selectie.
"""
BATCH_CALCULATION_INTRO_TEXT = """Dit is de berekeningspagina voor de batch berekeningen.
Hier kan je de berekeningen voor alle bruggen tegelijk uitvoeren. Rechts in de tabel is het statusoverzicht te zien.
De geschatte tijd geeft een indicatie van de tijd die nodig is om alle bruggen te berekenen, die klaar staan.
Een brug is klaar voor berekening wanneer alle benodigde invoervelden zijn ingevuld. Deze brug wordt dan geel gekleurd.
Bruggen die nog informatie missen, worden rood gemarkeerd. In de tweede kolom staan de ontbrekende velden aangegeven, die nog ingevuld moeten worden.
Wanneer de berekeningen klaar zijn, wordt de tabel aangevuld met beknopte resultaten.
Je kunt vervolgens per brug de resultaten bekijken in de entiteit van de brug zelf.

Let op: Het kan erg lang duren voordat de berekeningen klaar zijn.
"""
