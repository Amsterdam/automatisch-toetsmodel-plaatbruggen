"""Module for the Overview Bridges entity parametrization."""

from viktor.parametrization import (
    ActionButton,
    ChildEntityManager,
    DownloadButton,
    FileField,
    OutputField,
    Page,
    Parametrization,
    Text,
)

from app.constants import BATCH_CALCULATION_BUTTONS_TEXT, BATCH_CALCULATION_INTRO_TEXT

try:  # pragma: no cover - fallback for environments without Chat field support
    from viktor.parametrization import Chat
except ImportError:  # pragma: no cover
    Chat = None  # type: ignore[assignment, misc]


def _get_storage_status_text(params, **kwargs) -> str:  # noqa: ANN001, ARG001
    """
    Get formatted storage status text for OutputField.

    Returns technical storage operation status for developers.
    Shows last storage operation timestamp, success/failure, and details.

    :param params: Parametrization (unused, required by VIKTOR)
    :type params: Any
    :param kwargs: Additional keyword arguments
    :type kwargs: Any
    :returns: Formatted status text
    :rtype: str
    """
    from datetime import datetime

    from viktor.core import Storage

    from app.overview_bridges.batch_calculation.utils import load_storage_status

    storage = Storage()
    status = load_storage_status(storage)

    if status is None:
        return "**Geen opslag status beschikbaar.**\n\nVoer een batch berekening uit om status te zien."

    # Format timestamp
    timestamp_str = status.get("timestamp", "Onbekend")
    try:
        dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        timestamp_str = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except Exception:
        pass

    success = status.get("success", False)
    message = status.get("message", "Geen bericht")
    details = status.get("details", {})

    status_icon = "✓" if success else "✗"
    status_text = "SUCCES" if success else "GEFAALD"

    # Format details
    detail_lines = []
    if details:
        for key, value in details.items():
            detail_lines.append(f"  • {key}: {value}")

    detail_text = "\n".join(detail_lines) if detail_lines else "  (geen details)"

    return (
        f"**Status:** {status_icon} {status_text}\n"
        f"**Tijdstip:** {timestamp_str}\n"
        f"**Bericht:** {message}\n\n"
        f"**Details:**\n{detail_text}"
    )


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
    batch_calculation.introduction_text = Text(BATCH_CALCULATION_INTRO_TEXT)

    # Chat section for querying batch results (moved to top for better visibility)
    batch_calculation.chat_section = Text("### Resultaten Chat")
    batch_calculation.chat_guidance = Text(
        "Stel hier gerichte vragen over reeds berekende bruggen. De chat leest alleen bestaande batchresultaten "
        "en start nooit automatisch een nieuwe berekening."
    )
    if Chat is not None:
        batch_calculation.batch_results_chat = Chat(
            "Resultaten chat",
            method="chat_batch_results",
            placeholder="Bijv. 'Welke bruggen uit 1950-1980 hebben UC > 1?'",
            first_message="Vraag bijvoorbeeld: 'Welke bruggen hebben UC boven de 1,2?'",
            flex=100,
        )

    batch_calculation.action_buttons_text = Text(BATCH_CALCULATION_BUTTONS_TEXT)

    # Action buttons section
    batch_calculation.action_buttons = Text("### Acties")

    batch_calculation.refresh_button = ActionButton(
        "Ververs Statusoverzicht", method="refresh_batch_status", description="Herlaad de status en resultaten zonder opnieuw te berekenen"
    )
    batch_calculation.calculate_button = ActionButton(
        "Start Berekening", method="run_batch_calculation", description="Start batch berekening voor alle bruggen die klaar zijn"
    )

    # Technical/developer info section at the bottom
    batch_calculation.nerd_info_section = Text("### Tools en Info voor nerds")
    batch_calculation.cache_section = Text("#### Cache Beheer")
    batch_calculation.clear_cache_button = ActionButton(
        "Wis Workspace Cache", method="clear_workspace_storage", description="Verwijder alle gecachte SCIA en IDEA resultaten uit workspace storage"
    )
    batch_calculation.storage_status_section = Text("#### Opslag Status")
    batch_calculation.storage_status = OutputField(
        "Laatste opslag operatie",
        value=_get_storage_status_text,
        flex=100,
    )
