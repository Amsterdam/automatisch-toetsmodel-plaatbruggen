"""Module for the Overview Bridges entity parametrization."""

from viktor.parametrization import (
    ActionButton,
    ChildEntityManager,
    DownloadButton,
    FileField,
    Page,
    Parametrization,
    Text,
)

from app.constants import BATCH_CALCULATION_INTRO_TEXT, BATCH_CALCULATION_BUTTONS_TEXT

class OverviewBridgesParametrization(Parametrization):
    """Parametrization for the Overview Bridges entity."""

    # Define the blank Home page
    home = Page("Startpagina", views=["view_readme_changelog"])

    # Define the Data Upload page
    data_upload = Page("Brug Database Management")
    data_upload.header = Text(
        "## Bruggegevens Uploaden\n\nOp deze pagina kunt u de bruggegevens database bijwerken door een CSV of Excel bestand te uploaden."
    )

    data_upload.download_section = Text(
        "### Stap 1: Download Huidige Data (Optioneel)\n\n"
        "Download de huidige bruggegevens als CSV template. U kunt dit bestand bewerken en weer uploaden."
    )
    data_upload.download_button = DownloadButton(
        "Download Huidige Bruggegevens (CSV)", method="download_current_bridges_csv", description="Download filtered_bridges.json als CSV bestand"
    )

    data_upload.upload_section = Text(
        "### Stap 2: Upload Bestand\n\n"
        "**Vereisten:**\n"
        "- **CSV bestand**: Gebruik puntkomma (;) als scheidingsteken\n"
        "- **Excel bestand**: .xlsx formaat\n"
        "- **Verplichte kolom**: 'Kunstwerk nummer' met unieke brug ID's (bijv. BRU0010)\n"
        "- **Kolomnamen**: Moeten exact overeenkomen met het template (zie gedownload bestand)\n\n"
        "**Let op:** Alle lege rijen worden automatisch overgeslagen tijdens het importeren."
    )
    data_upload.bridge_data_file = FileField(
        "Bruggegevens bestand",
        description="Upload een CSV (.csv) of Excel (.xlsx) bestand",
        file_types=[".csv", ".xlsx"],
    )
    data_upload.process_button = ActionButton(
        "Verwerk en Update Database",
        method="process_bridge_data_upload",
        description="Verwerk het geüploade bestand en update filtered_bridges.json",
    )

    data_upload.next_steps = Text(
        "### Stap 3: Regenereer Bruggen\n\n"
        "Na succesvol uploaden, ga naar de **Overzicht Bruggen** pagina en klik op "
        "**'(Her)genereer Bruggen'** om de bruggen te laden of bij te werken met de nieuwe gegevens."
    )

    # Define the Bridge Overview page
    bridge_overview = Page("Overzicht Bruggen", views=["get_map_view"])
    bridge_overview.introduction = Text(
        "Op deze pagina vind je een overzicht van alle plaatbruggen in het project."
        " Je kunt hier nieuwe bruggen toevoegen of bestaande bruggen bewerken of verwijderen. Klik op een brug in de lijst om naar de brug te gaan."
    )

    # ChildEntityManager linked by passing the registered entity_type_name (alias)
    bridge_overview.bridge_manager = ChildEntityManager("Bridge")

    # Moved regenerate_button below the manager
    bridge_overview.regenerate_button = ActionButton("(Her)genereer Bruggen", method="regenerate_bridges_action")

    # Define the Batch Calculation page
    batch_calculation = Page("Statusoverzicht", views=["view_batch_status_and_results"])
    batch_calculation.introduction_text = Text(BATCH_CALCULATION_INTRO_TEXT)

    batch_calculation.action_buttons_text = Text(BATCH_CALCULATION_BUTTONS_TEXT)

    batch_calculation.action_buttons = Text("### Acties")

    batch_calculation.refresh_button = ActionButton(
        "Ververs Statusoverzicht", method="refresh_batch_status", description="Herlaad de status en resultaten zonder opnieuw te berekenen"
    )
    batch_calculation.calculate_button = ActionButton(
        "Start Berekening", method="run_batch_calculation", description="Start batch berekening voor alle bruggen die klaar zijn"
    )

    batch_calculation.cache_section = Text("### Cache Beheer")
    batch_calculation.clear_cache_button = ActionButton(
        "Wis Workspace Cache", method="clear_workspace_storage", description="Verwijder alle gecachte SCIA en IDEA resultaten uit workspace storage"
    )
