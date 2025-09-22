"""Module for the Overview Bridges entity parametrization."""

from viktor.parametrization import (
    ActionButton,
    ChildEntityManager,
    Page,
    Parametrization,
    Text,
)


class OverviewBridgesParametrization(Parametrization):
    """Parametrization for the Overview Bridges entity."""

    # Define the blank Home page
    home = Page("Startpagina", views=["view_readme_changelog"])

    # Define the Bridge Overview page
    bridge_overview = Page("Overzicht Bruggen", views=["get_map_view"])
    bridge_overview.introduction = Text("Op deze pagina vind je een overzicht van alle plaatbruggen in het project."
    " Je kunt hier nieuwe bruggen toevoegen of bestaande bruggen bewerken of verwijderen. Klik op een brug in de lijst om naar de brug te gaan.")

    # ChildEntityManager linked by passing the registered entity_type_name (alias)
    bridge_overview.bridge_manager = ChildEntityManager("Bridge")

    # Moved regenerate_button below the manager
    bridge_overview.regenerate_button = ActionButton("(Her)genereer Bruggen", method="regenerate_bridges_action")
