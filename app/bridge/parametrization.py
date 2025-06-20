"""Module for the Bridge entity parametrization."""

import json
from collections.abc import Callable, Mapping
from typing import Any

from viktor import DynamicArray
from viktor.parametrization import (
    BooleanField,
    DownloadButton,
    DynamicArrayConstraint,
    IsFalse,
    LineBreak,
    Lookup,
    MultiSelectField,
    NumberField,
    OptionField,
    Page,
    Parametrization,
    Tab,
    Text,
    TextAreaField,
    TextField,
)

from app.constants import BRIDGE_DATA_PATH, LOAD_ZONE_TYPES, MAX_LOAD_ZONE_SEGMENT_FIELDS, SCIA_INFO_TEXT

from .geometry_functions import get_steel_qualities

# --- Helper functions for Bridge Data Loading ---


def _load_bridge_data() -> list[dict[str, Any]]:
    """Load bridge data from the filtered_bridges.json file."""
    bridge_data_path = BRIDGE_DATA_PATH
    try:
        with bridge_data_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _get_bridge_by_objectnumm(objectnumm: str) -> dict[str, Any] | None:
    """Get bridge data by OBJECTNUMM."""
    if not objectnumm:
        return None

    bridge_data = _load_bridge_data()
    for bridge in bridge_data:
        if bridge.get("OBJECTNUMM") == objectnumm:
            return bridge
    return None


def _get_bridge_field_value(objectnumm: str, field_name: str, default: str = "") -> str:
    """Get a text field value from bridge data."""
    bridge = _get_bridge_by_objectnumm(objectnumm)
    if bridge and field_name in bridge:
        value = bridge[field_name]
        if value is not None and value != "":
            return str(value)
    return default


def _get_bridge_numeric_field_value(objectnumm: str, field_name: str, default: float = 0.0) -> float:
    """Get a numeric field value from bridge data."""
    bridge = _get_bridge_by_objectnumm(objectnumm)
    if bridge and field_name in bridge:
        value = bridge[field_name]
        if value is not None:
            try:
                return float(value)
            except (ValueError, TypeError):
                pass
    return default


def _bridge_field_has_value(objectnumm: str, field_name: str) -> bool:
    """Check if a bridge field has a meaningful value."""
    bridge = _get_bridge_by_objectnumm(objectnumm)
    if bridge and field_name in bridge:
        value = bridge[field_name]
        return value is not None and value != ""
    return False


def _bridge_field_is_empty(objectnumm: str, field_name: str) -> bool:
    """Check if a bridge field is empty or missing."""
    return not _bridge_field_has_value(objectnumm, field_name)


# --- Helper functions for DynamicArray Default Rows ---


def _create_default_dimension_segment_row(l_value: int, is_first: bool) -> dict[str, Any]:
    """Creates a dictionary for a default bridge dimension segment row."""
    return {
        "bz1": 10.0,
        "bz2": 5.0,
        "bz3": 15.0,
        "dz": 2.0,
        "dz_2": 3.0,
        "col_6": 0.0,
        "l": l_value,
        "is_first_segment": is_first,
    }


def _create_default_load_zone_row(zone_type: str, default_width: float) -> dict[str, Any]:
    """Creates a dictionary for a default load zone row."""
    row: dict[str, Any] = {"zone_type": zone_type}
    for i in range(1, MAX_LOAD_ZONE_SEGMENT_FIELDS + 1):
        row[f"d{i}_width"] = default_width
    return row


# --- Helper functions for Parametrization Logic (e.g., visibility callbacks) ---
def _get_current_num_load_zones(params_obj: Mapping) -> int:
    """Helper to get the current number of load zones from params.load_zones_data_array."""
    try:
        load_zones_array = params_obj.load_zones_data_array
        if load_zones_array is None or not isinstance(load_zones_array, list | tuple):
            return 0
        return len(load_zones_array)
    except AttributeError:
        # Parameters not yet fully defined during app initialization or update – treat as "0" zones
        return 0


def _get_current_num_segments(params_obj: Mapping) -> int:
    """Helper to get the current number of segments from params.bridge_segments_array."""
    try:
        dimension_array = params_obj.bridge_segments_array
        if dimension_array is None or not isinstance(dimension_array, list | tuple):
            return 0
        return len(dimension_array)
    except AttributeError:
        # Parameters not yet fully defined during app initialization or update – treat as "0" segments
        return 0


# Factory function to create visibility callbacks for dX_width fields
def _create_dx_width_visibility_callback(required_segment_count: int) -> Callable[..., list[bool]]:
    """
    Factory function to create visibility callback functions for dX_width fields.

    Args:
        required_segment_count: The minimum number of bridge segments (D-sections)
                                that must exist for the dX_width field to be
                                potentially visible (before considering the last row rule).

    Returns:
        A callback function suitable for the 'visible' attribute of a NumberField.

    """

    def dx_width_visibility_function(params, **kwargs) -> list[bool]:  # noqa: ANN001, ARG001
        """
        Determines visibility for a dX_width field in the load_zones_array.

        A row's field is visible if:
        1. The number of defined bridge segments is >= required_segment_count.
        2. The row is not the last row in the load_zones_array.
        """
        num_segments = _get_current_num_segments(params)
        num_load_zones = _get_current_num_load_zones(params)

        if num_load_zones <= 0:
            return []

        visibility_list = []
        for i in range(num_load_zones):
            is_visible = (num_segments >= required_segment_count) and (i < num_load_zones - 1)
            visibility_list.append(is_visible)

        return visibility_list

    return dx_width_visibility_function


# Generate the visibility callbacks using a dictionary comprehension
DX_WIDTH_VISIBILITY_CALLBACKS = {i: _create_dx_width_visibility_callback(i) for i in range(1, MAX_LOAD_ZONE_SEGMENT_FIELDS + 1)}


# --- Functions for dynamic reinforcement zones ---


def define_options_numbering(params: Mapping, **kwargs) -> list:  # noqa: ARG001
    """
    Define options for zone numbering based on the number of segments.

    Args:
        params: Parameters containing bridge_segments_array
        **kwargs: Additional keyword arguments (unused).

    Returns:
        list: List of zone numbers in format "location-segment" (e.g., ["1-1", "2-1", "3-1", "1-2", "2-2", "3-2"])

    """
    option_list = []
    num_segments = len(params.bridge_segments_array) - 1
    # For each segment
    for segment in range(num_segments):
        # For each zone (left, middle, right)
        for zone in range(3):
            zone_number = f"{zone + 1}-{segment + 1}"
            option_list.append(zone_number)
    return option_list


# --- Helper function to get min and max values of the model ---
def _get_model_xmax(params: Mapping, **kwargs) -> float:  # noqa: ARG001
    max_value = sum(segment.l for segment in params.bridge_segments_array)
    return max_value - 0.01


def _get_model_ymin(params: Mapping, **kwargs) -> float:  # noqa: ARG001
    max_b_z2 = max(segment.bz2 for segment in params.bridge_segments_array)
    max_b_z3 = max(segment.bz3 for segment in params.bridge_segments_array)
    return -max_b_z2 / 2 - max_b_z3


def _get_model_ymax(params: Mapping, **kwargs) -> float:  # noqa: ARG001
    max_b_z1 = max(segment.bz1 for segment in params.bridge_segments_array)
    max_b_z2 = max(segment.bz2 for segment in params.bridge_segments_array)
    max_value = max_b_z2 / 2 + max_b_z1
    return max_value - 0.01


def _get_model_zmin(params: Mapping, **kwargs) -> float:  # noqa: ARG001
    dz = max(segment.dz for segment in params.bridge_segments_array)
    return -dz


def _get_model_zmax(params: Mapping, **kwargs) -> float:  # noqa: ARG001
    dz_max = max(segment.dz_2 - segment.dz for segment in params.bridge_segments_array)
    max_value = dz_max
    return max_value - 0.01


# ----------------------------------
# --- Main Parametrization Class ---
# ----------------------------------
class BridgeParametrization(Parametrization):
    """Parametrization for the individual Bridge entity."""

    # ----------------------------------
    # --- Info Page ---
    # ----------------------------------
    info = Page("Info", views=["get_bridge_map_view", "get_bridge_summary_view"])

    # Bridge identification section
    info.bridge_info_section = Text(
        """# Bridge Details
Below you will find important information about this bridge structure."""
    )

    # Saved bridge identifiers (now visible and with better labels)
    info.bridge_objectnumm = TextField("Brug ID (OBJECTNUMM)", default="", description="Unieke identificatie voor deze brug in het systeem")
    info.bridge_name = TextField("Brugnaam", default="", description="Officiële naam van deze brug")

    # Additional bridge information fields

    info.lb1 = LineBreak()

    info.bridge_location_header = Text("## Locatie Informatie")

    info.stadsdeel = TextField(
        "Stadsdeel",
        default="",
        description="Stadsdeel waar de brug zich bevindt (bijv. Centrum, Noord)",
    )

    info.straat = TextField(
        "Straat",
        default="",
        description="Straat of waterweg waar de brug zich bevindt",
    )

    info.waterway = TextField("Waterweg/Kruising", default="", description="Waterweg of obstakel dat de brug kruist")

    info.lb2 = LineBreak()

    info.bridge_properties_header = Text("## Brugeigenschappen")

    info.bridge_type = TextField(
        "Brugtype",
        default="",
        description="Structurele type classificatie van de brug",
    )

    info.construction_year = TextField(
        "Stichtingsjaar",
        default="",
        description="Jaar waarin de brug is gebouwd",
    )

    info.usage = TextField(
        "Gebruik",
        default="",
        description="Primaire functie van de brug (bijv. wegverkeer, voetgangers)",
    )

    info.concrete_strength_class = TextField("Betonsterkteklasse", default="", description="Beton sterkte classificatie (bijv. B25, B45)")
    info.steel_quality_reinforcement = TextField("Staalkwaliteit (Wapening)", default="", description="Kwaliteitsklasse van betonstaal (bijv. B500)")
    info.deck_layer = TextField("Deklaag", default="", description="Type van het dekoppervlak (bijv. Asfalt, Beton)")

    info.lb2a = LineBreak()

    info.geometric_properties_header = Text("### Geometrische Eigenschappen")
    info.number_of_spans = NumberField("Aantal Velden", default=1, min=1, description="Aantal structurele overspanningen in de brug")
    info.static_system = TextField("Statisch Systeem", default="", description="Statisch systeemtype (bijv. statisch bepaald/onbepaald)")
    info.crossing_angle = NumberField("Kruisingshoek", default=90.0, suffix="°", description="Hoek waaronder de brug het obstakel kruist")
    info.theoretical_length = TextField("Theoretische Lengte", default="", suffix="m", description="Theoretische overspanningslengte")
    info.deck_width = TextField("Brugdekbreedte", default="", suffix="m", description="Totale breedte van het brugdek")
    info.construction_height = NumberField("Constructiehoogte", default=0.0, suffix="mm", description="Hoogte van de dekconstuctie")
    info.slenderness = TextField("Slankheidsverhouding", default="", description="Slankheidsverhouding van de dekoverspanningen")
    info.daily_length = TextField("Ldag", default="", suffix="m", description="Dagelijkse lengte van de brug")

    info.lb2c = LineBreak()

    info.structural_properties_header = Text("### Structurele Eigenschappen")
    info.bearing_type = TextField("Opleggingen", default="", description="Type van de opleggingen/lagers")
    info.orthotropy = TextField("Orthotropie/Isotropie", default="", description="Orthotropisch of isotropisch gedrag van het dek")
    info.beams_in_slab = OptionField(
        "Liggers in plaat", default="Onbekend", options=["Onbekend", "Ja", "Nee"], description="Aanwezigheid van liggers in de plaat"
    )

    info.lb2b = LineBreak()

    info.width_properties_header = Text("### Breedteverdeling")
    info.roadway_width = TextField("Rijwegbreedte", default="", suffix="m", description="Breedte toegewezen aan voertuigverkeer")
    info.tram_width = TextField("Breedte trambaan", default="", suffix="m", description="Breedte van de trambaan")
    info.bicycle_path_width = TextField("Fietspaadbreedte", default="", suffix="m", description="Breedte van fietspaden")
    info.sidewalk_north_east_width = TextField(
        "Trottoirbreedte (Noord/Oost)", default="", suffix="m", description="Breedte van trottoir aan noord/oost zijde"
    )
    info.sidewalk_south_west_width = TextField(
        "Trottoirbreedte (Zuid/West)", default="", suffix="m", description="Breedte van trottoir aan zuid/west zijde"
    )
    info.edge_beam_thickness = TextField("Dikte schampkant", default="", suffix="mm", description="Dikte van de schampkant/randdrager")
    info.edge_loading = OptionField(
        "Randbelasting", default="Onbekend", options=["Onbekend", "Ja", "Nee"], description="Aanwezigheid van randbelasting op de brug"
    )

    info.lb3 = LineBreak()

    info.bridge_status_header = Text("## Beoordelingsstatus")

    info.arb_flag = OptionField(
        "ARB Beoordelingsvlag",
        default="Niet ingesteld",
        options=["Niet ingesteld", "puur groen", "groen/oranje", "oranje/groen", "puur oranje", "oranje/rood", "puur rood"],
        description="Huidige ARB (Assessment of Reliability of Bridges) statusvlag",
    )

    info.basic_test_ghpo = OptionField(
        "Basale Toets GHPO",
        default="Niet ingesteld",
        options=["Niet ingesteld", "groen", "oranje", "rood", "nvt", "Wel"],
        description="Basale toetsresultaat voor GHPO (Richtlijn voor Beoordeling van Bestaande Constructies)",
    )

    info.contractor_iha = TextField(
        "Opdrachtnemer IHA", default="", description="Opdrachtnemer verantwoordelijk voor individuele gezondheidsbeoordeling"
    )
    info.assessment_notes = TextAreaField("Beoordelingsnotities", default="", description="Aanvullende opmerkingen over de brugbeoordeling")

    info.lb4 = LineBreak()

    info.reinforcement_header = Text("## Wapeningsgegevens")
    info.support_reinforcement_diameter = TextField(
        "Steunpuntswapening diameter", default="", suffix="mm", description="Diameter van steunpuntswapening in langsrichting"
    )
    info.support_reinforcement_spacing = TextField(
        "Steunpuntswapening h.o.h.-afstand", default="", suffix="mm", description="Hart-op-hart afstand van steunpuntswapening"
    )
    info.support_reinforcement_layer = TextField("Steunpuntswapening laag", default="", description="Laag nummer van steunpuntswapening")
    info.field_reinforcement_diameter = TextField(
        "Veldwapening diameter", default="", suffix="mm", description="Diameter van veldwapening in langsrichting"
    )
    info.field_reinforcement_spacing = TextField(
        "Veldwapening h.o.h.-afstand", default="", suffix="mm", description="Hart-op-hart afstand van veldwapening"
    )
    info.field_reinforcement_layer = TextField("Veldwapening laag", default="", description="Laag nummer van veldwapening")
    info.field_reinforcement_transverse_diameter = TextField(
        "Veldwapening dwarsrichting diameter", default="", suffix="mm", description="Diameter van veldwapening in dwarsrichting"
    )
    info.field_reinforcement_transverse_spacing = TextField(
        "Veldwapening dwarsrichting h.o.h.-afstand", default="", suffix="mm", description="Hart-op-hart afstand van veldwapening dwarsrichting"
    )
    info.field_reinforcement_transverse_layer = TextField(
        "Veldwapening dwarsrichting laag", default="", description="Laag nummer van veldwapening dwarsrichting"
    )
    info.concrete_cover = TextField(
        "Dekking buitenkant wapening", default="", suffix="mm", description="Betondekking aan de buitenkant van de wapening"
    )

    # ----------------------------------
    # --- Invoer Page ---
    # ----------------------------------

    input = Page(
        "Invoer",
        views=[
            "get_top_view",
            "get_3d_view",
            "get_2d_horizontal_section",
            "get_2d_longitudinal_section",
            "get_2d_cross_section",
            "get_load_zones_view",
            "get_load_combinations_view",
        ],
    )

    # --- Tabs within Invoer Page ---
    input.dimensions = Tab("Dimensies")
    input.geometrie_wapening = Tab("Wapening")
    input.belastingzones = Tab("Belastingzones")
    input.belastingcombinaties = Tab("Belastingcombinaties")

    # --- Load Combinations (in belastingcombinaties tab) ---
    input.belastingcombinaties.cc_class = OptionField("Gevolgklasse", options=["CC1a/b", "CC2", "CC3"], variant="radio")
    input.belastingcombinaties.comb_types = MultiSelectField("Belastingscombinaties", options=["ULS", "SLS", "FAT"])

    # ----------------------------------------
    # --- Invoer Page -> Dimensions tab ---
    # ----------------------------------------

    input.dimensions.segment_explanation = Text(
        """Definieer hier de dwarsdoorsneden (snedes) van de brug.
Elk item in de lijst hieronder representeert een dwarsdoorsnede.
- Het **eerste item** definieert de geometrie van het begin van de brug (snede D1).
- Elk **volgend item** definieert de geometrie van de *volgende* dwarsdoorsnede (D2, D3, etc.).
- Het veld '**Afstand tot vorige snede**' (`l`) geeft de lengte van het brugsegment *tussen* de voorgaande en de huidige snede.
  Dit veld is niet zichtbaar voor de eerste snede.
- De overige dimensievelden (zoals `bz1`, `bz2`, `dz` voor de dikte van zone 1 en 3, en `dz_2` voor de dikte van zone 2)
  beschrijven de eigenschappen van de *huidige* dwarsdoorsnede.
Standaard zijn twee dwarsdoorsneden (D1 en D2) voorgedefinieerd, wat resulteert in één brugsegment.
Pas de waarden aan, of voeg meer dwarsdoorsneden toe/verwijder ze via de '+' en '-' knoppen."""
    )

    input.dimensions.array = DynamicArray(
        "Brug dimensies",
        row_label="D-",
        min=2,
        name="bridge_segments_array",
        default=[
            _create_default_dimension_segment_row(l_value=0, is_first=True),
            _create_default_dimension_segment_row(l_value=10, is_first=False),
        ],
    )
    input.dimensions.array.is_first_segment = BooleanField("Is First Segment Marker", default=False, visible=False)

    input.dimensions.array.bz1 = NumberField("Breedte zone 1", default=10.0, suffix="m")
    input.dimensions.array.bz2 = NumberField("Breedte zone 2", default=5.0, suffix="m")
    input.dimensions.array.bz3 = NumberField("Breedte zone 3", default=15.0, suffix="m")
    input.dimensions.array.dz = NumberField("Dikte zone 1 en 3", default=2.0, suffix="m")
    input.dimensions.array.dz_2 = NumberField("Dikte zone 2", default=3.0, suffix="m")
    input.dimensions.array.col_6 = NumberField("alpha", default=0.0, suffix="Graden", visible=False)

    _l_field_visibility_constraint = DynamicArrayConstraint(
        dynamic_array_name="bridge_segments_array",
        operand=IsFalse(Lookup("$row.is_first_segment")),
    )
    input.dimensions.array.l = NumberField(
        "Afstand tot vorige snede",
        default=10,
        suffix="m",
        visible=_l_field_visibility_constraint,
    )

    # --- Bridge Geometry (moved to geometrie_brug tab) ---
    input.dimensions.lb1 = LineBreak()
    input.dimensions.text_sections = Text("Met onderstaande instellingen kan de locatie van de doorsneden worden ingesteld.")
    input.dimensions.toggle_sections = BooleanField("Toon locaties van de doorsneden in het 3D model", default=False, flex=100)
    input.dimensions.lb2 = LineBreak()
    input.dimensions.horizontal_section_loc = NumberField(
        "Horizontale doorsnede z =",
        default=-1.0,
        suffix="m",
        visible=Lookup("input.dimensions.toggle_sections"),
        min=_get_model_zmin,
        max=_get_model_zmax,
    )
    input.dimensions.lb3 = LineBreak()
    input.dimensions.longitudinal_section_loc = NumberField(
        "Langsdoorsnede y =", default=0.0, suffix="m", visible=Lookup("input.dimensions.toggle_sections"), min=_get_model_ymin, max=_get_model_ymax
    )
    input.dimensions.lb4 = LineBreak()
    input.dimensions.cross_section_loc = NumberField(
        "Dwarsdoorsnede x =", default=0.0, suffix="m", visible=Lookup("input.dimensions.toggle_sections"), min=0, max=_get_model_xmax
    )

    # ----------------------------------------
    # --- Invoer Page -> rebar tab ---
    # ----------------------------------------

    # --- Reinforcement Geometry (in geometrie_wapening tab) ---
    input.geometrie_wapening.explanation = Text(
        """Op deze pagina kan de wapening van de brug worden ingevoerd. Er kunnen oneindig veel wapeningconfiguraties worden toegevoegd.
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
    )

    # General reinforcement parameters
    input.geometrie_wapening.staalsoort = OptionField(
        "Staalsoort",
        options=get_steel_qualities(),
        default="B500B",
        description="De kwaliteit van het betonstaal dat wordt toegepast in de brug.",
    )

    input.geometrie_wapening.langswapening_buiten = BooleanField(
        "Langswapening aan buitenzijde?",
        default=True,
        description=(
            "Indien aangevinkt ligt de langswapening aan de buitenzijde van het beton. Indien uitgevinkt ligt de dwarswapening aan de buitenzijde."
        ),
    )

    input.geometrie_wapening.lb1 = LineBreak()

    input.geometrie_wapening.dekking_boven = NumberField(
        "Betondekking boven",
        default=55.0,
        suffix="mm",
        flex=30,
        description="De betondekking aan de bovenzijde van de plaat.",
    )
    input.geometrie_wapening.dekking_onder = NumberField(
        "Betondekking onder",
        default=55.0,
        suffix="mm",
        flex=30,
        description="De betondekking aan de onderzijde van de plaat.",
    )

    input.geometrie_wapening.zones = DynamicArray(
        "Wapeningsconfiguraties",
        min=1,  # Always require at least one configuration
        name="reinforcement_zones_array",
        default=[
            {
                "zone_number": ["1-1"],  # Default to first zone, but can select multiple
                "hoofdwapening_langs_boven_diameter": 12.0,
                "hoofdwapening_langs_boven_hart_op_hart": 150.0,
                "hoofdwapening_langs_onder_diameter": 12.0,
                "hoofdwapening_langs_onder_hart_op_hart": 150.0,
                "hoofdwapening_dwars_boven_diameter": 12.0,
                "hoofdwapening_dwars_boven_hart_op_hart": 150.0,
                "hoofdwapening_dwars_onder_diameter": 12.0,
                "hoofdwapening_dwars_onder_hart_op_hart": 150.0,
                "heeft_bijlegwapening": False,
            }
        ],
    )

    # Zone number selection
    input.geometrie_wapening.zones.zone_number = MultiSelectField(
        "Zones", options=define_options_numbering, description="Selecteer de zones waar deze wapeningsconfiguratie moet worden toegepast."
    )

    input.geometrie_wapening.zones.lb2 = LineBreak()

    # Main reinforcement - Longitudinal top
    input.geometrie_wapening.zones.hoofdwapening_langs_boven_diameter = NumberField(
        "Diameter hoofdwapening langsrichting boven", default=12.0, suffix="mm", flex=47
    )
    input.geometrie_wapening.zones.hoofdwapening_langs_boven_hart_op_hart = NumberField(
        "H.o.h. afstand hoofdwapening langsrichting boven", default=150.0, suffix="mm", flex=53
    )
    input.geometrie_wapening.zones.lb3 = LineBreak()

    # Main reinforcement - Longitudinal bottom
    input.geometrie_wapening.zones.hoofdwapening_langs_onder_diameter = NumberField(
        "Diameter hoofdwapening langsrichting onder", default=12.0, suffix="mm", flex=47
    )
    input.geometrie_wapening.zones.hoofdwapening_langs_onder_hart_op_hart = NumberField(
        "H.o.h. afstand hoofdwapening langsrichting onder", default=150.0, suffix="mm", flex=53
    )

    input.geometrie_wapening.zones.lb4 = LineBreak()
    # Main reinforcement - Transverse Top
    input.geometrie_wapening.zones.hoofdwapening_dwars_boven_diameter = NumberField(
        "Diameter hoofdwapening dwarsrichting boven", default=12.0, suffix="mm", flex=47
    )

    input.geometrie_wapening.zones.hoofdwapening_dwars_boven_hart_op_hart = NumberField(
        "H.o.h. afstand hoofdwapening dwarsrichting boven", default=150.0, suffix="mm", flex=53
    )

    input.geometrie_wapening.zones.lb4 = LineBreak()

    # Main reinforcement - Transverse Bottom
    input.geometrie_wapening.zones.hoofdwapening_dwars_onder_diameter = NumberField(
        "Diameter hoofdwapening dwarsrichting onder", default=12.0, suffix="mm", flex=47
    )

    input.geometrie_wapening.zones.hoofdwapening_dwars_onder_hart_op_hart = NumberField(
        "H.o.h. afstand hoofdwapening dwarsrichting onder", default=150.0, suffix="mm", flex=53
    )

    # Visual separator for bijlegwapening
    input.geometrie_wapening.zones.lb5 = LineBreak()

    # Additional reinforcement toggle
    input.geometrie_wapening.zones.heeft_bijlegwapening = BooleanField("Bijlegwapening aanwezig?", default=False)

    # Additional reinforcement fields - only visible when heeft_bijlegwapening is True
    _bijleg_visibility = DynamicArrayConstraint(
        dynamic_array_name="reinforcement_zones_array",
        operand=Lookup("$row.heeft_bijlegwapening"),
    )

    input.geometrie_wapening.zones.lb6 = LineBreak()

    input.geometrie_wapening.zones.bijlegwapening_langs_boven_diameter = NumberField(
        "Diameter bijlegwapening langsrichting boven", default=12.0, suffix="mm", flex=47, visible=_bijleg_visibility
    )
    input.geometrie_wapening.zones.bijlegwapening_langs_boven_hart_op_hart = NumberField(
        "H.o.h. afstand bijlegwapening langsrichting boven", default=150.0, suffix="mm", flex=53, visible=_bijleg_visibility
    )

    input.geometrie_wapening.zones.lb7 = LineBreak()

    # Additional reinforcement - Longitudinal bottom
    input.geometrie_wapening.zones.bijlegwapening_langs_onder_diameter = NumberField(
        "Diameter bijlegwapening langsrichting onder", default=12.0, suffix="mm", flex=47, visible=_bijleg_visibility
    )
    input.geometrie_wapening.zones.bijlegwapening_langs_onder_hart_op_hart = NumberField(
        "H.o.h. afstand bijlegwapening langsrichting onder", default=150.0, suffix="mm", flex=53, visible=_bijleg_visibility
    )

    input.geometrie_wapening.zones.lb8 = LineBreak()

    # Additional reinforcement - Transverse top
    input.geometrie_wapening.zones.bijlegwapening_dwars_boven_diameter = NumberField(
        "Diameter bijlegwapening dwarsrichting boven", default=12.0, suffix="mm", flex=47, visible=_bijleg_visibility
    )
    input.geometrie_wapening.zones.bijlegwapening_dwars_boven_hart_op_hart = NumberField(
        "H.o.h. afstand bijlegwapening dwarsrichting boven", default=150.0, suffix="mm", flex=53, visible=_bijleg_visibility
    )
    input.geometrie_wapening.zones.lb9 = LineBreak()
    # Additional reinforcement - Transverse bottom
    input.geometrie_wapening.zones.bijlegwapening_dwars_onder_diameter = NumberField(
        "Diameter bijlegwapening dwarsrichting onder", default=12.0, suffix="mm", flex=47, visible=_bijleg_visibility
    )
    input.geometrie_wapening.zones.bijlegwapening_dwars_onder_hart_op_hart = NumberField(
        "H.o.h. afstand bijlegwapening dwarsrichting onder", default=150.0, suffix="mm", flex=53, visible=_bijleg_visibility
    )

    # ----------------------------------------
    # --- Invoer Page -> loadzones tab ---
    # ----------------------------------------

    # --- Load Zones (in belastingzones tab) ---
    input.belastingzones.info_text = Text(
        "Definieer hier de belastingzones. Elke zone wordt gestapeld vanaf één zijde van de brug. "
        "Vul alleen breedtes in voor de daadwerkelijk gedefinieerde brugsegmenten (D-nummers) "
        "onder de tab 'Dimensies'. De laatste belastingzone loopt automatisch door tot het einde van de brug; "
        "hiervoor hoeven dus geen segmentbreedtes (D-waardes) ingevuld te worden."
    )

    input.belastingzones.load_zones_array = DynamicArray(
        "Belastingzones",
        row_label="Belasting Zone",
        name="load_zones_data_array",
        default=[
            _create_default_load_zone_row(LOAD_ZONE_TYPES[0], 1.5),  # Voetgangers
            _create_default_load_zone_row(LOAD_ZONE_TYPES[1], 3.0),  # Fietsers
            _create_default_load_zone_row(LOAD_ZONE_TYPES[3], 0.5),  # Berm (new)
            _create_default_load_zone_row(LOAD_ZONE_TYPES[2], 10.5),  # Auto (Rijbaan)
        ],
    )
    input.belastingzones.load_zones_array.zone_type = OptionField("Type belastingzone", options=LOAD_ZONE_TYPES, default=LOAD_ZONE_TYPES[0])

    # Dynamically create dX_width fields for the load_zones_array
    for _idx_field in range(1, MAX_LOAD_ZONE_SEGMENT_FIELDS + 1):
        _field = NumberField(
            f"Breedte zone bij D{_idx_field}",
            default=2.0,  # Default set to 2.0m for all fields
            min=0.01,  # Minimum value set to 0.01m (1cm)
            suffix="m",
            description=f"Breedte van deze belastingzone ter hoogte van dwarsdoorsnede D{_idx_field}.",
            visible=DX_WIDTH_VISIBILITY_CALLBACKS[_idx_field],
        )
        setattr(input.belastingzones.load_zones_array, f"d{_idx_field}_width", _field)

    # ----------------------------------------
    # --- Invoer Page -> loadcases tab ---
    # ----------------------------------------

    # ----------------------------------
    # --- SCIA Page ---
    # ----------------------------------

    scia = Page("SCIA", views=["get_scia_model_preview"])

    scia.info_text = Text(SCIA_INFO_TEXT)

    # Download buttons - use DownloadButton instead of ActionButton
    scia.download_xml_button = DownloadButton("Download XML Files", method="download_scia_xml_files")

    scia.download_esa_button = DownloadButton("Download ESA Model", method="download_scia_esa_model")

    # ----------------------------------
    # --- Calculations Page ---
    # ----------------------------------

    berekening = Page("Berekening")

    # ----------------------------------
    # --- Report Page ---
    # ----------------------------------

    rapport = Page("Rapport", views=["get_output_report"])
