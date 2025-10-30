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

De tramzone dient te worden geselecteerd wanneer er een gescheiden trambaan is. In deze zone wordt enkel een tram gemodelleerd.
Wanneer er autoverkeer op de trambaan kan komen, dient dit te worden gemodelleerd als rijbaan,
en dienen tussenstukken berm etc. te worden verwaarloosd.
In dit geval krijg je een brede auto zone in het midden van het brugdek, tussen de fiets- en voetpaden.
Er wordt dan geen trambelasting gemodelleerd, maar enkel de verkeersbelasting van de auto zone
omdat dit altijd maatgevend is ten opzichte van de trambelasting.

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

Deze pagina toont een weergave van het aangemaakte SCIA model en biedt download opties voor SCIA Engineer bestanden.
Op het tabblad "Berekening" kun je belastinggevallen toevoegen die mee genomen worden in de SCIA analyse.
Vervolgens kun je de .xml bestanden downloaden om het model zelf te bekijken in SCIA,
of de analyse direct in Viktor laten uitvoeren en de resultaten hier bekijken,
door op de knop "Download ESA Model" of "Download SCIA Output XML" te klikken.
In het eerste geval krijg je meteen het volledige .esa model om zelf te openen in SCIA Engineer,
in het tweede geval krijg je enkel het output .xml bestand.

### Download Opties
Gebruik de onderstaande knoppen om SCIA bestanden te downloaden:"""

# Dimensions segments explanation
DIMENSIONS_SEGMENTS_EXPLANATION = """Definieer hier de dwarsdoorsneden (snedes) van de brug.
Elk item in de lijst hieronder representeert een dwarsdoorsnede.
- Het **eerste item** definieert de geometrie van het begin van de brug (snede D1).
- Elk **volgend item** definieert de geometrie van de *volgende* dwarsdoorsnede (D2, D3, etc.).
- Het veld '**Afstand tot vorige snede**' (`l`) geeft de lengte van het brugsegment *tussen* de voorgaande en de huidige snede.
  Dit veld is niet zichtbaar voor de eerste snede.
- De overige dimensievelden (zoals `bz1`, `bz2`, `dz` voor de dikte van zone 1 en 3, en `dz_2` voor de dikte van zone 2)
  beschrijven de eigenschappen van de *huidige* dwarsdoorsnede.
Standaard zijn twee dwarsdoorsneden (D1 en D2) voorgedefinieerd, wat resulteert in één brugsegment.
Pas de waarden aan, of voeg meer dwarsdoorsneden toe/verwijder ze via de '+' en '-' knoppen.

De brug bestaat altijd uit drie zones (1,2 en 3). Voor een brug met slechts één dikte, vul je dezelfde waarde in voor `dz` en `dz_2`.

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

Deze pagina toont een weergave van de IDEA RCS resultaten en biedt download opties voor de snedetoetsingen in IDEA.

### Model Informatie
Het model is gebaseerd op de opgegeven bruggeometrie en wapening. Het model identificeert op basis van de wapeningsconfiguraties en plaatdiktes,
hoeveel unieke combinaties van plaatdiktes en wapening er zijn, en maakt voor elke unieke combinatie een apart plaat element aan in IDEA.
Vervolgens worden de snedekrachten uit SCIA, hieraan gekoppeld op basis van locatie op het brugdek, en worden de snedetoetsingen uitgevoerd.
Per locatie langs de integratiestroken worden er een of meerdere krachtencombinaties getoetst die mogelijk maatgevend zijn. Deze worden als extremen
toegevoegd aan de doorsnedes.

In het eerste tabblad op de rechterkant van het scherm, is een overzicht te zien van de verschillende plaat elementen die zijn aangemaakt.
In het tweede tabblad is een overzicht te zien van de resultaten van de snedetoetsingen.

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
Dit helpt om de rekentijd te beheren tijdens het testen van specifieke belastingen."""

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
