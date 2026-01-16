"""Module for the Overview Bridges entity parametrization."""

from datetime import datetime

from viktor.core import Storage
from viktor.parametrization import (
    ActionButton,
    ChildEntityManager,
    DownloadButton,
    FileField,
    LineBreak,
    OutputField,
    Page,
    Parametrization,
    Text,
)

try:  # pragma: no cover - fallback for environments without Chat field support
    from viktor.parametrization import Chat
except ImportError:  # pragma: no cover
    Chat = None  # type: ignore[assignment, misc]

from app.overview_bridges.batch_calculation.utils import load_storage_status


def _get_storage_status(params, **kwargs) -> str:  # noqa: ANN001, ARG001
    """Get storage status (success/fail) for OutputField."""
    storage = Storage()
    status = load_storage_status(storage)
    if status is None:
        return "Geen data"
    success = status.get("success", False)
    return "✓ SUCCES" if success else "✗ GEFAALD"


def _get_storage_timestamp(params, **kwargs) -> str:  # noqa: ANN001, ARG001
    """Get storage timestamp for OutputField."""
    storage = Storage()
    status = load_storage_status(storage)
    if status is None:
        return "-"
    timestamp_str = status.get("timestamp", "Onbekend")
    try:
        dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return timestamp_str


def _get_storage_details(params, **kwargs) -> str:  # noqa: ANN001, ARG001
    """Get storage details summary for OutputField."""
    storage = Storage()
    status = load_storage_status(storage)
    if status is None:
        return "Voer eerst een batch berekening uit"
    details = status.get("details", {})
    if not details:
        return "(geen details)"
    # Compact format: "calculated: 0, failed: 0, skipped: 1, total: 1"
    parts = [f"{k.replace('bridges_', '')}: {v}" for k, v in details.items()]
    return ", ".join(parts)


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

    # Define the Batch Calculation page - combined view with status and results
    batch_calculation = Page("Statusoverzicht", views=["view_batch_status_and_results"])

    # Short introduction
    batch_calculation.introduction_text = Text(
        "Op deze pagina kun je batch berekeningen uitvoeren voor alle bruggen tegelijk. "
        "Rechts in de tabel zie je het statusoverzicht met de berekeningsstatus per brug."
    )

    if Chat is not None:
        batch_calculation.batch_results_chat = Chat(
            "Stel vragen over berekende bruggen. Chat leest alleen bestaande resultaten en start geen nieuwe berekening.",
            method="chat_batch_results",
            placeholder="Bijv. 'Wat is de relatie tussen het bouwjaar en de UC'",
            first_message="Vraag bijvoorbeeld: 'Welke bruggen tussen 1950 en 1980 hebben UC boven de 1?'",
            flex=100,
        )

    # Information about calculations and buttons
    batch_calculation.calculation_details = Text(
        "### Over de berekening\n\n"
        "Een brug is klaar voor berekening wanneer alle benodigde invoervelden zijn ingevuld (geel gemarkeerd). "
        "Bruggen die nog informatie missen worden rood gemarkeerd met de ontbrekende velden. "
        "Wanneer de berekeningen klaar zijn, wordt de tabel aangevuld met beknopte resultaten.\n\n"
        "**Let op:** Het kan erg lang duren voordat de berekeningen klaar zijn.\n"
        "### Acties\n\n"
    )

    batch_calculation.refresh_button = ActionButton(
        "Ververs Statusoverzicht", method="refresh_batch_status", description="Herlaad de status en resultaten zonder opnieuw te berekenen"
    )
    batch_calculation.calculate_button = ActionButton(
        "Start Berekening", method="run_batch_calculation", description="Start batch berekening voor alle bruggen die klaar zijn"
    )

    # Technical/developer info section at the bottom
    batch_calculation.cache_section = Text("#### Cache Beheer & Opslag Status")
    batch_calculation.clear_cache_button = ActionButton(
        "Wis Workspace Cache", method="clear_workspace_storage", description="Verwijder alle gecachte SCIA en IDEA resultaten uit workspace storage"
    )
    batch_calculation.lb_storage_status_separator = LineBreak()
    batch_calculation.storage_status = OutputField("#### Berekening status", value=_get_storage_status, flex=50)
    batch_calculation.storage_timestamp = OutputField("#### Tijdstip van laatste batch berekening", value=_get_storage_timestamp, flex=50)
    batch_calculation.lb_storage_details_separator = LineBreak()
    batch_calculation.storage_details = OutputField("#### Opslag details", value=_get_storage_details, flex=100)
