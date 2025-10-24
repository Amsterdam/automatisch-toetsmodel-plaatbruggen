"""Module for the Bridge entity parametrization."""

import csv
import json
from collections.abc import Callable, Mapping
from typing import Any

from viktor.parametrization import (
    BooleanField,
    DownloadButton,
    DynamicArray,
    DynamicArrayConstraint,
    IsFalse,
    LineBreak,
    Lookup,
    MultiSelectField,
    NumberField,
    OptimizationButton,
    OptionField,
    OutputField,
    Page,
    Parametrization,
    RowLookup,
    Tab,
    Table,
    Text,
    TextAreaField,
    TextField,
)

from app.constants import (
    BRIDGE_DATA_PATH,
    CALCULATION_LEVEL_OPTIONS,
    CALCULATION_SETTINGS_INFO_TEXT,
    CALCULATION_SETTINGS_INFO_TEXT_CALCULATION_LEVEL,
    CONCRETEQUALITY_CSV_PATH,
    DIMENSIONS_SEGMENTS_EXPLANATION,
    IDEA_INFO_TEXT,
    LOAD_CASE_SELECTION_DEFAULT,
    LOAD_CASE_SELECTION_HEADER_TEXT,
    LOAD_CASE_SELECTION_NOTE_TEXT,
    LOAD_ZONE_TYPES,
    LOAD_ZONES_INFO_TEXT,
    MAX_LOAD_ZONE_SEGMENT_FIELDS,
    OPTIMIZATION_EXPLANATION_TEXT,
    PAVEMENT_MATERIAL_OPTIONS,
    REINFORCEMENT_INFO_TEXT,
    SCIA_INFO_TEXT,
    SIGNAGE_OPTIONS,
)
from src.common.materials import get_reinforcement_qualities

from .utils import validate_reinforcement_zone_selections


def _calculate_load_case_counts(params: Any) -> dict[str, int]:  # noqa: ANN401
    """
    Calculate the number of load cases that would be generated for each load type.

    :param params: Bridge parameters for dynamic calculations.
    :return: Dictionary mapping load type names to their load case counts.
    :rtype: dict[str, int]
    """
    counts = {
        "Eigen gewicht": 1,  # BG1001
        "Permanente belastingen": 5,  # BG2001-BG2005
        "Temperatuurbelastingen": 4,  # BG3001-BG3004
        "Verkeersbelastingen UDL": 3,  # BG4001-BG4003
        "Voetgangersbelastingen": 1,  # BG5001
    }

    try:
        # For dynamic load cases, we need to calculate based on bridge geometry
        from src.integrations.scia_integration.scia_load_generators import extract_bridge_dimensions
        from src.integrations.scia_integration.scia_loads_helper import (
            generate_theoretical_lane_positions_bg8000,
            tandem_system_sequencer,
            tandem_system_sequencer_single_axis,
            tandem_system_sequencer_single_axis_rotated,
        )

        dims = extract_bridge_dimensions(params)
        length = dims.total_length
        thickness = dims.thickness
        width = dims.total_width

        # Service vehicle load cases: 2 × number of positions (y_plus and y_minus)
        service_positions = tandem_system_sequencer(length, thickness, length_vehicle=3.25)
        counts["Dienstvoertuig belastingen"] = len(service_positions) * 2

        # Unintended vehicle load cases: complex calculation
        unintended_positions = tandem_system_sequencer(length, thickness, length_vehicle=1.2)
        amsterdam_positions = tandem_system_sequencer_single_axis(length, thickness)
        amsterdam_rotated_positions = tandem_system_sequencer_single_axis_rotated(length, thickness, length_vehicle=2.0)

        # Standard vehicle: 2 edges × 2 directions × positions
        standard_cases = len(unintended_positions) * 2 * 2  # RS1 and RS3, forward and reverse
        # Amsterdam vehicle: 2 edges × positions
        amsterdam_cases = len(amsterdam_positions) * 2
        # Amsterdam rotated: 2 edges × positions
        amsterdam_rotated_cases = len(amsterdam_rotated_positions) * 2

        counts["Onbedoeld voertuig belastingen"] = standard_cases + amsterdam_cases + amsterdam_rotated_cases

        # Tandem system load cases: depends on number of theoretical lanes
        num_lanes = len(generate_theoretical_lane_positions_bg8000(width))
        num_lanes = min(num_lanes, 3)  # Maximum 3 lanes

        tandem_positions = tandem_system_sequencer(length, thickness, length_vehicle=1.6)
        tandem_cases = 0

        for rs in range(1, num_lanes + 1):
            if rs == 3:
                # RS3 has double the cases (2 configurations)
                tandem_cases += len(tandem_positions) * 2
            else:
                tandem_cases += len(tandem_positions)

        counts["Tandem systeem belastingen"] = tandem_cases

    except Exception:
        # Fallback to estimated values if calculation fails
        counts["Dienstvoertuig belastingen"] = 20  # Estimated
        counts["Onbedoeld voertuig belastingen"] = 50  # Estimated
        counts["Tandem systeem belastingen"] = 30  # Estimated

    return counts


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


# --- Helper functions for visibility callbacks ---


def _show_signage_field(params, **kwargs) -> bool:  # noqa: ANN001, ARG001
    """
    Determine if the signage field should be visible based on berekeningsniveau.
    Only show when "Werkelijke wegindeling met bebording" is selected.

    :param params: Parameters containing berekeningsniveau setting
    :returns: True if signage field should be visible, False otherwise
    :rtype: bool
    """
    return params.berekeningsniveau == "Werkelijke wegindeling met bebording"


# --- Helper functions for DynamicArray Default Rows ---


def _create_default_dimension_segment_row(
    *,  # Force keyword arguments for clarity
    l_value: float = 0,
    is_first: bool = False,
    support_type: str = "Nee",
) -> dict[str, Any]:
    """
    Create a dictionary for a default bridge dimension segment row with customizable values.

    :param l_value: Distance to previous section. Defaults to 0.
    :type l_value: float
    :param is_first: Whether this is the first segment. Defaults to False.
    :type is_first: bool
    :param support_type: Type of support at this location. Defaults to "Nee".
    :type support_type: str

    :returns: Dictionary containing the segment row parameters with the following keys:
        - "bz1" (float): Width of zone 1 (default: 10.0 m)
        - "bz2" (float): Width of zone 2 (default: 3.0 m)
        - "bz3" (float): Width of zone 3 (default: 15.0 m)
        - "dz" (float): Thickness of zones 1 and 3 (default: 0.7 m)
        - "dz_2" (float): Thickness of zone 2 (default: 0.8 m)
        - "col_6" (float): Alpha angle (default: 0.0 degrees)
        - "l" (float): Distance to previous section (default: value of l_value)
        - "is_first_segment" (bool): Whether this is the first segment (default: value of is_first)
        - "is_support" (str): Type of support at this location
    :rtype: dict[str, Any]
    """
    bz1 = 10.0
    bz2 = 3.0
    bz3 = 15.0
    dz = 0.7
    dz_2 = 0.8
    col_6 = 0.0

    return {
        "bz1": bz1,
        "bz2": bz2,
        "bz3": bz3,
        "dz": dz,
        "dz_2": dz_2,
        "col_6": col_6,
        "l": l_value,
        "is_first_segment": is_first,
        "is_support": support_type,
    }


def _create_default_load_zone_row(zone_type: str, default_width: float) -> dict[str, Any]:
    """Creates a dictionary for a default load zone row."""
    row: dict[str, Any] = {
        "zone_type": zone_type,
        "pavement_thickness": 0.05,  # Default 5cm thickness
        "pavement_material": "Asfalt",  # Default material
    }
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


def _validate_reinforcement_zones_callback(params, **kwargs) -> None:  # noqa: ANN001, ARG001
    """
    Validation callback for reinforcement zone selections.

    Validates that each zone is selected in only one configuration.
    Raises UserError if duplicates are found.

    Args:
        params: Parameters containing reinforcement_zones_array
        **kwargs: Additional keyword arguments (unused)

    Raises:
        UserError: If duplicate zone selections are found

    """
    validate_reinforcement_zone_selections(params)


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


# -- helper function to get bridge type based on supports
def _get_bridge_type_based_on_supports(params: Mapping, **kwargs) -> str:  # noqa: ARG001
    """
    Determine the bridge type based on the support configuration.
    Statically determinate: exactly 2 supports (Scharnieroplegging and Roloplegging) at begin and end positions.
    Statically indeterminate: all other cases.

    Args:
        params: Parameters containing bridge_segments_array
        **kwargs: Additional keyword arguments (unused).

    Returns:
        str: Bridge type ("Statisch bepaald" or "Statisch onbepaald")

    """
    support_types = [segment.is_support for segment in params.bridge_segments_array]

    # Count supports that are not "Nee" (no support)
    supports_with_position = []
    for i, support_type in enumerate(support_types):
        if support_type != "Nee":
            supports_with_position.append((i, support_type))

    num_supports = len(supports_with_position)

    # Statically determinate: exactly 2 supports at begin and end with one Scharnieroplegging and one Roloplegging
    if num_supports == 2:
        first_support_pos = supports_with_position[0][0]
        last_support_pos = supports_with_position[1][0]
        first_support_type = supports_with_position[0][1]
        last_support_type = supports_with_position[1][1]

        # Check if supports are at begin and end positions
        if first_support_pos == 0 and last_support_pos == len(support_types) - 1:
            # Check if we have exactly one Scharnieroplegging and two Verende oplegging (x,y) (order doesn't matter)
            support_type_set = {first_support_type, last_support_type}
            if support_type_set == {"Verende oplegging (x,y)", "Verende oplegging (x,y)"}:
                return "Statisch bepaald"

    # All other cases: statically indeterminate
    return "Statisch onbepaald"


# ----------------------------------
# --- Main Parametrization Class ---
# ----------------------------------
class BridgeParametrization(Parametrization):
    """Parametrization for the individual Bridge entity."""

    # ----------------------------------
    # --- Info Page ---
    # ----------------------------------
    info = Page("Paspoortinformatie", views=["get_bridge_map_view"])

    # Bridge identification section
    info.bridge_info_section = Text(
        """# Paspoortinformatie
Op deze pagina vind je de paspoortgegevens van deze brug."""
    )

    # Saved bridge identifiers (now visible and with better labels)
    info.bridge_objectnumm = TextField("Brug ID (OBJECTNUMM)", default="", description="Unieke identificatie voor deze brug in het systeem")
    info.bridge_name = TextField("Brugnaam", default="", description="Officiële naam van deze brug")

    # Additional bridge information fields

    info.lb1 = LineBreak()

    info.bridge_location_header = Text("## Locatie")

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

    info.waterway = TextField("Water/kruising", default="", description="Water of obstakel waar de brug overheen gaat")

    info.lb2 = LineBreak()

    info.bridge_properties_header = Text("## Brugeigenschappen")

    info.bridge_type = TextField(
        "Brugtype",
        default="",
        description="Constructie type classificatie van de brug",
    )

    info.construction_year = TextField(
        "Stichtingsjaar",
        default="",
        description="Jaar waarin de brug is gebouwd",
    )

    info.usage = OptionField(
        "Gebruik",
        default="Wegverkeer",
        options=["Wegverkeer", "Wegverkeer en tram", "Voetpad", "Trambaan", "Fietspad/voetpad"],
        description="Primaire functie van de brug (bijv. wegverkeer, voetgangers)",
    )

    @staticmethod
    def _get_steel_quality_options() -> list[str]:
        """
        Get comprehensive list of steel qualities including modern and historical materials.

        :returns: Complete list of supported steel qualities
        :rtype: list[str]
        """
        # Get modern materials from CSV (if available)
        try:
            modern_materials = get_reinforcement_qualities()
        except Exception:
            # Fallback to basic modern materials if CSV reading fails
            modern_materials = ["B400A", "B400B", "B400C", "B500A", "B500B", "B500C"]

        # Add historical materials from IDEA integration
        # Import here to avoid circular imports between app and src layers
        try:
            from src.integrations.idea_integration.idea_material_mapping import get_all_supported_reinforcement_materials

            all_supported = get_all_supported_reinforcement_materials()
            historical_materials = [material for material, material_type in all_supported.items() if material_type == "historical"]
        except ImportError:
            # Fallback to hardcoded list if import fails
            historical_materials = [
                # GBV 1940 materials
                "HK",
                "St. 37",
                # GBV 1950 materials
                "QR22",
                "QR24",
                "QR30",
                "QR36",
                "QR42",
                # GBV 1962 materials
                "QR32",
                "QR40",
                "QR48",
                # NEN 6720 materials
                "FeB500 HWL, HK",
                "FeB400 HWL, HK",
                "FeB220 HWL",
                # VB 74+84 materials
                "FeB500 HW",
                "FeB400 HW",
                "FeB220 HW",
            ]

        # Combine: modern materials first, then historical materials
        all_materials = modern_materials + historical_materials

        # Remove duplicates while preserving order
        seen = set()
        unique_materials = []
        for material in all_materials:
            if material not in seen:
                seen.add(material)
                unique_materials.append(material)

        return unique_materials

    @staticmethod
    def _get_steel_quality_options_dynamic(params, **kwargs) -> list[str]:  # noqa: ANN001, ARG004
        """
        Dynamic options provider for Staalsoort.

        Ensures legacy/default values already stored in older entities are included
        so loading does not fail when value is not in the standard modern material list.

        :param params: Current parameters (may contain a stored value)
        :returns: Options list including any stored legacy value
        :rtype: list[str]
        """
        options = BridgeParametrization._get_steel_quality_options()

        try:
            current_value = getattr(getattr(params, "input", None), "geometrie_wapening", None)
            if current_value:
                steel_value = getattr(current_value, "staalsoort", None)
                if isinstance(steel_value, str) and steel_value and steel_value not in options:
                    options.append(steel_value)
        except Exception:
            # If params is not fully initialized yet, just return base options
            pass

        return options

    @staticmethod
    def _get_concrete_quality_options() -> list[str]:
        """
        Load concrete quality options from resources/data/materials/betonkwaliteit.csv
        and include historical materials from IDEA integration.

        :returns: List of concrete quality keys (modern + historical)
        :rtype: list[str]
        """
        # Load modern materials from CSV
        modern_materials = []
        csv_path = CONCRETEQUALITY_CSV_PATH
        try:
            with csv_path.open(encoding="utf-8") as f:
                reader = csv.DictReader(f, delimiter=";")
                modern_materials = [row["Betonkwaliteit"].strip('"') for row in reader]
        except (FileNotFoundError, KeyError):
            # Fallback to standard Eurocode materials if CSV is not available
            modern_materials = [
                "C12/15",
                "C16/20",
                "C20/25",
                "C25/30",
                "C30/37",
                "C35/45",
                "C40/50",
                "C45/55",
                "C50/60",
                "C55/67",
                "C60/75",
                "C70/85",
                "C80/95",
                "C90/105",
            ]

        # Add historical materials from IDEA integration
        # Import here to avoid circular imports between app and src layers
        try:
            from src.integrations.idea_integration.idea_material_mapping import get_all_supported_materials

            all_supported = get_all_supported_materials()
            historical_materials = [material for material, material_type in all_supported.items() if material_type == "historical"]
        except ImportError:
            # Fallback to hardcoded list if import fails
            historical_materials = [
                # Historical materials from GBV 1940/1950/1962
                "K150",
                "K200",
                "K250",
                "K160",
                "K225",
                "K300",
                "K400",
                "K450",
                # NEN 6720 materials (B-class)
                "B25",
                "B35",
                "B45",
                "B55",
                "B65",
                # VB 74+84 materials (B-class with decimals)
                "B12,5",
                "B17,5",
                "B22,5",
                "B30",
                "B37,5",
                "B52,5",
                "B60",
            ]

        # Combine: modern materials first, then historical materials
        all_materials = modern_materials + historical_materials

        # Remove duplicates while preserving order
        seen = set()
        unique_materials = []
        for material in all_materials:
            if material not in seen:
                seen.add(material)
                unique_materials.append(material)

        return unique_materials

    @staticmethod
    def _get_concrete_quality_options_dynamic(params, **kwargs) -> list[str]:  # noqa: ANN001, ARG004
        """
        Dynamic options provider for Betonsterkteklasse.

        Ensures legacy/default values (e.g., "B55") already stored in older
        entities are included so loading does not fail when value is not in
        the standard C12/15..C90/105 list.

        :param params: Current parameters (may contain a stored value)
        :returns: Options list including any stored legacy value
        :rtype: list[str]
        """
        options = BridgeParametrization._get_concrete_quality_options()

        try:
            current_value = getattr(getattr(params, "info", None), "concrete_strength_class", None)
            if isinstance(current_value, str) and current_value and current_value not in options:
                options.append(current_value)
        except Exception:
            # If params is not fully initialized yet, just return base options
            pass

        return options

    info.concrete_strength_class = OptionField(
        "Betonsterkteklasse",
        options=_get_concrete_quality_options_dynamic,
        default="",
        name="concrete_strength_class",
        description="Beton sterkte classificatie (bijv. C12/15 .. C90/105)",
    )
    info.concrete_strength_class_source = OptionField(
        "Bron Betonsterkteklasse",
        options=["Onbekend", "Aanname", "Tekening"],
        default="Onbekend",
    )
    info.concrete_strength_class_source_text = TextAreaField(
        "Toelichting Bron Betonsterkteklasse", default="", description="Toelichting op de bron van de betonsterkteklasse"
    )

    info.lb2a = LineBreak()

    info.geometric_properties_header = Text("### Geometrische eigenschappen")
    info.number_of_spans = NumberField("Aantal Velden", default=1, min=1, description="Aantal structurele overspanningen in de brug", visible=False)
    info.static_system = TextField(
        "Statisch Systeem", default="", description="Statisch systeemtype (bijv. statisch bepaald/onbepaald)", visible=False
    )
    info.crossing_angle = NumberField(
        "Kruisingshoek", default=90.0, suffix="°", description="Hoek waaronder de brug het obstakel kruist", visible=False
    )
    info.theoretical_length = TextField(
        "Theoretische lengte",
        default="",
        suffix="m",
        description="Theoretische overspanningslengte, dit is de afstand tussen de assen van de opleggingen",
    )
    info.deck_width = TextField("Brugdekbreedte", default="", suffix="m", description="Totale breedte van het brugdek")
    info.construction_height = NumberField("Constructiehoogte", default=0.0, suffix="mm", description="Hoogte van de dekconstructie", visible=False)
    info.slenderness = NumberField("Slankheidsverhouding", default=0.0, description="Slankheidsverhouding van de dekoverspanningen", visible=False)
    info.daily_length = TextField(
        "Ldag", default="", suffix="m", description="Lengte van de brug tussen de steunpunten, waar krachten worden afgelezen", visible=False
    )

    info.lb2c = LineBreak()

    info.width_properties_header = Text("### Breedteverdeling", visible=False)
    info.roadway_width = TextField("Rijwegbreedte", default="", suffix="m", description="Breedte toegewezen aan voertuigverkeer", visible=False)
    info.tram_width = TextField("Breedte trambaan", default="", suffix="m", description="Breedte van de trambaan", visible=False)
    info.bicycle_path_width = TextField("Fietspadbreedte", default="", suffix="m", description="Breedte van fietspaden", visible=False)
    info.sidewalk_north_east_width = TextField(
        "Trottoirbreedte (Noord/Oost)", default="", suffix="m", description="Breedte van trottoir aan noord/oost zijde", visible=False
    )
    info.sidewalk_south_west_width = TextField(
        "Trottoirbreedte (Zuid/West)", default="", suffix="m", description="Breedte van trottoir aan zuid/west zijde", visible=False
    )
    info.edge_beam_thickness = TextField("Dikte schampkant", default="", suffix="mm", description="Dikte van de schampkant/randdrager", visible=False)
    info.edge_loading = OptionField(
        "Randbelasting", default="Onbekend", options=["Onbekend", "Ja", "Nee"], description="Aanwezigheid van randbelasting op de brug", visible=False
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
    info.last_calculation = TextField("Datum laatste berekening", default="", description="Datum van de laatste berekening van deze brug in Viktor")
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
        ],
    )

    # --- Tabs within Invoer Page ---
    input.dimensions = Tab("Dimensies")
    input.geometrie_wapening = Tab("Wapening")
    input.belastingzones = Tab("Belastingzones")

    # ----------------------------------------
    # --- Invoer Page -> Dimensions tab ---
    # ----------------------------------------

    input.dimensions.segment_explanation = Text(DIMENSIONS_SEGMENTS_EXPLANATION)

    input.dimensions.array = DynamicArray(
        "Brug dimensies",
        row_label="D-",
        min=2,
        name="bridge_segments_array",
        default=[
            _create_default_dimension_segment_row(l_value=0, is_first=True, support_type="Verende oplegging (x,y)"),
            _create_default_dimension_segment_row(l_value=25, is_first=False, support_type="Nee"),
            _create_default_dimension_segment_row(l_value=15, is_first=False, support_type="Nee"),
            _create_default_dimension_segment_row(l_value=10, is_first=False, support_type="Verende oplegging (x,y)"),
        ],
    )
    input.dimensions.array.is_first_segment = BooleanField("Is First Segment Marker", default=False, visible=False)

    input.dimensions.array.bz1 = NumberField("Breedte zone 1", default=10.0, suffix="m", min=0.1)
    input.dimensions.array.bz2 = NumberField("Breedte zone 2", default=3.0, suffix="m", min=0.1)
    input.dimensions.array.bz3 = NumberField("Breedte zone 3", default=15.0, suffix="m", min=0.1)
    input.dimensions.array.dz = NumberField("Dikte zone 1 en 3", default=0.7, suffix="m", min=0.05)
    input.dimensions.array.dz_2 = NumberField("Dikte zone 2", default=0.8, suffix="m", min=0.05)
    input.dimensions.array.col_6 = NumberField("alpha", default=0.0, suffix="Graden", visible=False)

    _l_field_visibility_constraint = DynamicArrayConstraint(
        dynamic_array_name="bridge_segments_array",
        operand=IsFalse(Lookup("$row.is_first_segment")),
    )
    input.dimensions.array.l = NumberField(
        "Afstand tot vorige snede",
        default=10,
        suffix="m",
        min=0.1,
        visible=_l_field_visibility_constraint,
    )

    input.dimensions.array.is_support = OptionField(
        "Oplegging", options=["Nee", "Verende oplegging (x,y)", "Inklemming"], default="Nee", description="Type oplegging op deze locatie"
    )

    input.dimensions.bridge_type_output = OutputField(
        "### Op basis van de invoer is de brugtype:",
        value=_get_bridge_type_based_on_supports,
        description="De automatisch bepaalde brugtype op basis van de geselecteerde opleggingen",
        flex=100,
    )

    # --- Bridge Geometry (moved to geometrie_brug tab) ---
    input.dimensions.lb1 = LineBreak()
    input.dimensions.text_sections = Text("### Met onderstaande instellingen kan de locatie van de doorsneden worden ingesteld.")
    input.dimensions.toggle_sections = BooleanField("Toon locaties van de doorsneden in het 3D model", default=False, flex=100)
    input.dimensions.lb2 = LineBreak()
    input.dimensions.horizontal_section_loc = NumberField(
        "Horizontale doorsnede z =",
        default=-0.1,
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
    input.geometrie_wapening.explanation = Text(REINFORCEMENT_INFO_TEXT)

    # General reinforcement parameters
    input.geometrie_wapening.staalsoort = OptionField(
        "Staalsoort",
        options=_get_steel_quality_options_dynamic,
        default="B500B",
        description=(
            "Kwaliteit van het betonstaal. SCIA: alle materialen. IDEA: moderne en historische materialen. "
            "Oude staalsoorten worden automatisch ondersteund."
        ),
    )

    input.geometrie_wapening.steel_quality_source = OptionField(
        "Staalsoort bron",
        options=["Onbekend", "Aanname", "Tekening"],
        default="Onbekend",
        description=("Bron van de staalsoort, bijvoorbeeld een aanname of afgeleid uit tekeningen."),
    )

    input.geometrie_wapening.steel_quality_source_text = TextAreaField(
        "Toelichting staalsoort bron", default="", description="Toelichting op de bron van de staalsoort"
    )

    input.geometrie_wapening.lb0 = LineBreak()

    input.geometrie_wapening.langswapening_buiten = BooleanField(
        "Langswapening in eerste laag?",
        default=True,
        description=(
            "Indien aangevinkt ligt de langswapening in de eerste laag. "
            "Indien uitgevinkt ligt de dwarswapening in de eerste laag en de langswapening in de tweede laag."
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
        row_label="Wapeningsconfiguratie",
        default=[
            {
                "zone_number": ["1-1", "2-1", "3-1"],  # Default to all zones for the first configuration
                "hoofdwapening_langs_boven_diameter": 12.0,
                "hoofdwapening_langs_boven_hart_op_hart": 150.0,
                "hoofdwapening_dwars_boven_diameter": 12.0,
                "hoofdwapening_dwars_boven_hart_op_hart": 150.0,
                "hoofdwapening_langs_onder_diameter": 12.0,
                "hoofdwapening_langs_onder_hart_op_hart": 150.0,
                "hoofdwapening_dwars_onder_diameter": 12.0,
                "hoofdwapening_dwars_onder_hart_op_hart": 150.0,
                "heeft_bijlegwapening": False,
                "bijlegwapening_langs_boven_diameter": 12.0,
                "bijlegwapening_dwars_boven_diameter": 12.0,
                "bijlegwapening_langs_onder_diameter": 12.0,
                "bijlegwapening_dwars_onder_diameter": 12.0,
            },
        ],
    )
    # Zone number selection
    input.geometrie_wapening.zones.zone_number = MultiSelectField(
        "Zones",
        options=define_options_numbering,  # Use dynamic options based on number of segments
        default=["1-1", "2-1", "3-1"],  # Default to all zones for the first configuration
        description="Selecteer de zones waar deze wapeningsconfiguratie moet worden toegepast.",
    )

    input.geometrie_wapening.zones.lb2 = LineBreak()

    # Main reinforcement - Longitudinal top
    input.geometrie_wapening.zones.hoofdwapening_langs_boven_diameter = NumberField(
        "Ø hoofdwapening langsrichting boven", default=12.0, min=6.0, suffix="mm", flex=47
    )
    input.geometrie_wapening.zones.hoofdwapening_langs_boven_hart_op_hart = NumberField(
        "H.o.h. afstand hoofdwapening langsrichting boven", default=150.0, min=50, suffix="mm", flex=53
    )

    input.geometrie_wapening.zones.lb3 = LineBreak()

    # Main reinforcement - Transverse Top
    input.geometrie_wapening.zones.hoofdwapening_dwars_boven_diameter = NumberField(
        "Ø hoofdwapening dwarsrichting boven", default=12.0, min=6, suffix="mm", flex=47
    )

    input.geometrie_wapening.zones.hoofdwapening_dwars_boven_hart_op_hart = NumberField(
        "H.o.h. afstand hoofdwapening dwarsrichting boven", default=150.0, min=50, suffix="mm", flex=53
    )

    input.geometrie_wapening.zones.lb4 = LineBreak()

    # Main reinforcement - Longitudinal bottom
    input.geometrie_wapening.zones.hoofdwapening_langs_onder_diameter = NumberField(
        "Ø hoofdwapening langsrichting onder", default=12.0, min=6, suffix="mm", flex=47
    )
    input.geometrie_wapening.zones.hoofdwapening_langs_onder_hart_op_hart = NumberField(
        "H.o.h. afstand hoofdwapening langsrichting onder", default=150.0, min=50, suffix="mm", flex=53
    )

    input.geometrie_wapening.zones.lb5 = LineBreak()

    # Main reinforcement - Transverse Bottom
    input.geometrie_wapening.zones.hoofdwapening_dwars_onder_diameter = NumberField(
        "Ø hoofdwapening dwarsrichting onder", default=12.0, min=6, suffix="mm", flex=47
    )

    input.geometrie_wapening.zones.hoofdwapening_dwars_onder_hart_op_hart = NumberField(
        "H.o.h. afstand hoofdwapening dwarsrichting onder", default=150.0, min=50, suffix="mm", flex=53
    )

    # Visual separator for bijlegwapening
    input.geometrie_wapening.zones.lb6 = LineBreak()

    # Additional reinforcement toggle
    input.geometrie_wapening.zones.heeft_bijlegwapening = BooleanField("Bijlegwapening aanwezig?", default=False)

    # Additional reinforcement fields - only visible when heeft_bijlegwapening is True
    input.geometrie_wapening.zones.lb7 = LineBreak()

    # Additional reinforcement - Longitudinal top
    input.geometrie_wapening.zones.bijlegwapening_langs_boven_diameter = NumberField(
        "Ø bijlegwapening langsrichting boven", default=12.0, min=6, suffix="mm", flex=47, visible=RowLookup("heeft_bijlegwapening")
    )
    input.geometrie_wapening.zones.bijlegwapening_langs_boven_hart_op_hart = OutputField(
        "H.o.h. afstand bijlegwapening langsrichting boven",
        value=RowLookup("hoofdwapening_langs_boven_hart_op_hart"),
        visible=RowLookup("heeft_bijlegwapening"),
        suffix="mm",
        flex=53,
    )

    input.geometrie_wapening.zones.lb8 = LineBreak()

    # Additional reinforcement - Transverse top
    input.geometrie_wapening.zones.bijlegwapening_dwars_boven_diameter = NumberField(
        "Ø bijlegwapening dwarsrichting boven", default=12.0, min=6, suffix="mm", flex=47, visible=RowLookup("heeft_bijlegwapening")
    )
    input.geometrie_wapening.zones.bijlegwapening_dwars_boven_hart_op_hart = OutputField(
        "H.o.h. afstand bijlegwapening dwarsrichting boven",
        value=RowLookup("hoofdwapening_dwars_boven_hart_op_hart"),
        visible=RowLookup("heeft_bijlegwapening"),
        suffix="mm",
        flex=53,
    )

    input.geometrie_wapening.zones.lb9 = LineBreak()

    # Additional reinforcement - Longitudinal bottom
    input.geometrie_wapening.zones.bijlegwapening_langs_onder_diameter = NumberField(
        "Ø bijlegwapening langsrichting onder", default=12.0, min=6, suffix="mm", flex=47, visible=RowLookup("heeft_bijlegwapening")
    )
    input.geometrie_wapening.zones.bijlegwapening_langs_onder_hart_op_hart = OutputField(
        "H.o.h. afstand bijlegwapening langsrichting onder",
        value=RowLookup("hoofdwapening_langs_onder_hart_op_hart"),
        visible=RowLookup("heeft_bijlegwapening"),
        suffix="mm",
        flex=53,
    )

    input.geometrie_wapening.zones.lb10 = LineBreak()

    # Additional reinforcement - Transverse bottom
    input.geometrie_wapening.zones.bijlegwapening_dwars_onder_diameter = NumberField(
        "Ø bijlegwapening dwarsrichting onder", default=12.0, min=6, suffix="mm", flex=47, visible=RowLookup("heeft_bijlegwapening")
    )
    input.geometrie_wapening.zones.bijlegwapening_dwars_onder_hart_op_hart = OutputField(
        "H.o.h. afstand bijlegwapening dwarsrichting onder",
        value=RowLookup("hoofdwapening_dwars_onder_hart_op_hart"),
        visible=RowLookup("heeft_bijlegwapening"),
        suffix="mm",
        flex=53,
    )

    # ----------------------------------------
    # --- Invoer Page -> loadzones tab ---
    # ----------------------------------------

    # --- Load Zones (in belastingzones tab) ---
    input.belastingzones.info_text = Text(LOAD_ZONES_INFO_TEXT)

    input.belastingzones.lijnlast_leuning = NumberField(
        "Lijnlast leuning",
        default=1.0,
        min=0.0,
        suffix="kN/m",
        description="Lijnlast van de leuning op het brugdek",
    )

    input.belastingzones.load_zones_array = DynamicArray(
        "Belastingzones",
        row_label="Belasting Zone",
        name="load_zones_data_array",
        default=[
            _create_default_load_zone_row(LOAD_ZONE_TYPES[0], 1.5),  # Voetgangers
            _create_default_load_zone_row(LOAD_ZONE_TYPES[1], 3.0),  # Fietsers
            _create_default_load_zone_row(LOAD_ZONE_TYPES[2], 10.5),  # Auto (Rijbaan)
            _create_default_load_zone_row(LOAD_ZONE_TYPES[3], 3.0),  # Tram
            _create_default_load_zone_row(LOAD_ZONE_TYPES[4], 0.5),  # Berm
        ],
    )
    input.belastingzones.load_zones_array.zone_type = OptionField("Type belastingzone", options=LOAD_ZONE_TYPES, default=LOAD_ZONE_TYPES[0])

    # Pavement properties for load calculation
    input.belastingzones.load_zones_array.pavement_thickness = NumberField(
        "Dikte verharding",
        default=0.05,  # 5cm default
        min=0.001,  # Minimum 1mm
        max=1.0,  # Maximum 1m
        suffix="m",
        step=0.001,  # 1mm steps
        description="Dikte van de wegverharding/ophoging voor deze belastingzone. Wordt gebruikt voor berekening eigengewicht.",
    )

    input.belastingzones.load_zones_array.pavement_material = OptionField(
        "Materiaal verharding",
        options=PAVEMENT_MATERIAL_OPTIONS,
        default="Asfalt",
        description="Type materiaal van de verharding. Bepaalt de soortelijke massa voor eigengewichtberekening.",
    )

    # TODO: Add calculated field showing resulting load in kN/m² based on thickness × material density
    # TODO: This calculation should be implemented in the controller/backend logic

    input.belastingzones.load_zones_array.lb_pavement = LineBreak()

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

    # ----------------------------------
    # --- Berekening Page ---
    # ----------------------------------
    calc_page = Page("Berekening", views="get_load_combinations_view")

    # ----------------------------------
    # --- Berekening Page -> Berekening opties tab ---
    # ----------------------------------

    calc_page.calc_level = Tab("Berekening niveau")

    calc_page.calc_level.info_load_combinations = Text(CALCULATION_SETTINGS_INFO_TEXT)

    # --- Load Combinations (in berekening niveau tab) ---
    calc_page.calc_level.cc_class = OptionField("Gevolgklasse", options=["CC1a/b", "CC2", "CC3"], variant="radio", name="cc_class", default="CC2")

    calc_page.calc_level.design_code = OptionField(
        "Veiligheidsniveau",
        options=[
            "NEN 8700 verbouw",
            "NEN 8700 gebruik",
            "NEN 8700 afkeur",
        ],
        variant="radio",
        name="design_code",
        default="NEN 8700 gebruik",
    )

    calc_page.calc_level.info_calculation_level = Text(CALCULATION_SETTINGS_INFO_TEXT_CALCULATION_LEVEL)

    calc_page.calc_level.calculation_level = OptionField(
        "Verkeersbelasting",
        options=CALCULATION_LEVEL_OPTIONS,
        variant="radio",
        name="berekeningsniveau",
        default="Theoretische wegindeling",
    )

    calc_page.calc_level.signage = OptionField(
        "Bebording",
        options=SIGNAGE_OPTIONS,
        name="signage",
        default="50 ton",
        visible=_show_signage_field,
    )

    calc_page.calc_level.lb1 = LineBreak()

    calc_page.calc_level.spreiding = BooleanField(
        "Spreiding van verkeersbelasting",
        default=True,
        name="spreiding",
        description="Indien aangevinkt, wordt de verticale verkeersbelasting van BG6000 tot en met BG10000, uitgespreid over een breder vlak",
    )

    # ----------------------------------
    # --- Berekening Page -> Berekening selectie tab ---
    # ----------------------------------
    calc_page.calc_selection = Tab("Berekening selectie")

    # Load case selection for controlling calculation time
    calc_page.calc_selection.load_case_selection_header = Text(LOAD_CASE_SELECTION_HEADER_TEXT)

    calc_page.calc_selection.lb_load_case_selection = LineBreak()

    calc_page.calc_selection.load_case_selection_table = Table(
        "Belastingselectie",
        name="load_case_selection_table",
        default=LOAD_CASE_SELECTION_DEFAULT,
    )

    # Define table columns (order determines display order)
    calc_page.calc_selection.load_case_selection_table.include = BooleanField(" ", description="Schakel deze belastingen in/uit voor het SCIA model")
    calc_page.calc_selection.load_case_selection_table.load_type = TextField(
        "Belastingtype", description="Type van de belasting (bijv. Eigen gewicht, Verkeersbelastingen)"
    )
    calc_page.calc_selection.load_case_selection_table.load_case_range = TextField(
        "Belastinggevallen", description="Range van belastinggevallen die worden gegenereerd (bijv. BG1001, BG2001-BG2005)"
    )
    calc_page.calc_selection.load_case_selection_table.load_case_count = NumberField(
        "Aantal belastinggevallen",
        suffix="",
        visible=True,
        description="Aantal belastinggevallen dat wordt gegenereerd - indicator voor rekentijd impact",
    )

    calc_page.calc_selection.lb_traffic_loads = LineBreak()

    calc_page.calc_selection.load_case_selection_note = Text(LOAD_CASE_SELECTION_NOTE_TEXT)

    # ----------------------------------
    # --- Berekening Page -> Berekening selectie tab ---
    # ----------------------------------
    calc_page.calc_optimization = Tab("Berekening optimalisatie")

    calc_page.calc_optimization.optimization_header = Text("## Berekening optimalisatie")

    calc_page.calc_optimization.lb1 = LineBreak()

    calc_page.calc_optimization.optimization_explanation = Text(OPTIMIZATION_EXPLANATION_TEXT)

    calc_page.calc_optimization.optimization_btn = OptimizationButton("OptimizationButton", method="perform_optimization", flex=100, longpoll=True)

    # ----------------------------------
    # --- SCIA Page ---
    # ----------------------------------

    scia = Page(
        "SCIA",
        views=[
            "get_3d_view",
            "get_scia_results_view_sls_kar",
            "get_scia_results_view_sls_freq",
            "get_scia_results_view_uls",
            "get_scia_1d_results_view_sls_kar",
            "get_scia_1d_results_view_sls_freq",
            "get_scia_1d_results_view_uls",
            "get_scia_cs_results_view_uls",
            "get_scia_cs_results_view_sls_kar",
            "get_scia_cs_results_view_sls_freq",
            "get_scia_results_table",
        ],
    )

    # Downloads tab
    scia.downloads = Tab("Downloads")

    scia.downloads.info_text = Text(SCIA_INFO_TEXT)

    # Download buttons - use DownloadButton instead of ActionButton
    scia.downloads.download_xml_button = DownloadButton("Download XML Files", method="download_scia_xml_files", longpoll=True)

    scia.downloads.download_esa_button = DownloadButton("Download ESA Model", method="download_scia_esa_model", longpoll=True)

    # Analysis button
    scia.downloads.run_analysis_button = DownloadButton("Download SCIA Output XML", method="download_scia_output_xml", longpoll=True)

    # ----------------------------------
    # --- IDEA StatiCa Page ---
    # ----------------------------------

    idea = Page("IDEA StatiCa", views=["get_view_unique_idea_cross_sections", "get_view_idea_rcs_results"])

    idea.explanation = Text(IDEA_INFO_TEXT)

    # Add download buttons as page attributes below the explanation
    idea.download_xml = DownloadButton("Download RCS Model (XML)", method="download_idea_xml_file", longpoll=True)
    idea.download_results = DownloadButton("Download Capaciteitsanalyse", method="download_idea_analysis_results", longpoll=True)

    # ----------------------------------
    # --- Report Page ---
    # ----------------------------------

    rapport = Page("Rapport", views=["get_output_report"])
