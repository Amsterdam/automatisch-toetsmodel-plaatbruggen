"""Controller for the Overview Bridges entity."""

# ============================================================================================================
# Imports
# ============================================================================================================

import csv  # Import csv module
import json  # Import json module
import os  # Import os to construct path
import typing  # Import typing for ClassVar
from io import StringIO

# Add GeoPandas import (ensure it's installed in your venv)
import geopandas as gpd
import markdown
import viktor.api_v1 as api  # Import VIKTOR API
from viktor.core import (  # Import Color, ViktorController
    File,
    UserMessage,
    ViktorController,  # Import Color, ViktorController
)
from viktor.core import File, UserMessage, ViktorController  # Import Color, ViktorController
from viktor.errors import UserError  # Import UserError
from viktor.parametrization import Parametrization  # Import for type hint
from viktor.result import DownloadResult  # Import DownloadResult
from viktor.views import MapPoint, MapResult, MapView, WebResult, WebView  # Use MapPolygon instead of MapPolyline

from app.common.map_utils import (  # Import shared utilities
    get_default_shapefile_path,
    get_filtered_bridges_json_path,
    get_resources_dir,
    load_and_prepare_shapefile,
    process_all_bridges_geometries,
    validate_shapefile_exists,
)
from app.constants import (  # Replace relative imports with absolute imports
    CHANGELOG_PATH,
    CSS_PATH,
    README_PATH,
)
from viktor.core import File, UserMessage, ViktorController  # Import Color, ViktorController
from viktor.errors import UserError  # Import UserError
from viktor.parametrization import Parametrization  # Import for type hint
from viktor.result import DownloadResult  # Import DownloadResult
from viktor.views import MapPoint, MapResult, MapView, WebResult, WebView  # Use MapPolygon instead of MapPolyline

# Import the parametrization from the separate file
from .parametrization import OverviewBridgesParametrization


class OverviewBridgesController(ViktorController):
    """Controller for the Overview Bridges entity."""

    label = "Overzicht Bruggen"  # Updated label
    parametrization = OverviewBridgesParametrization  # type: ignore[assignment] # Ignore potential complex assignment MyPy error
    children: typing.ClassVar[list[str]] = ["Bridge"]  # Use the alias defined in app/__init__.py
    show_children_as: typing.ClassVar[str] = "Table"  # Optional: How to display children (Table or Cards)

    # --- Map View Helper Methods ---

    @MapView("Overzicht Kaart", duration_guess=1)
    def get_map_view(self, params: Parametrization, **kwargs) -> MapResult:  # noqa: ARG002
        """Displays bridge polygons from the shapefile in the resources folder."""
        # 1. Define Paths
        try:
            shapefile_path = get_default_shapefile_path()
            allowed_bridges_path = get_filtered_bridges_json_path()

            # Using shared utility function to validate shapefile existence
            # validate_shapefile_exists now returns the path, so we use it directly
            shapefile_path = validate_shapefile_exists(shapefile_path)

            if not os.path.exists(allowed_bridges_path):
                raise UserError(f"Filter bestand niet gevonden op verwachtte locatie: {allowed_bridges_path}")  # noqa: TRY301

        except UserError as ue:
            raise UserError(str(ue))
        except Exception as e:
            raise UserError(f"Fout bij het bepalen van bestandspaden: {e}")

        # 2. Load allowed bridges list
        try:
            with open(allowed_bridges_path) as f:
                filtered_bridge_data = json.load(f)
                allowed_objectnumm = {bridge_obj.get("OBJECTNUMM") for bridge_obj in filtered_bridge_data if bridge_obj.get("OBJECTNUMM")}
        except Exception as e:
            raise UserError(f"Fout bij laden van {allowed_bridges_path}: {e}")

        # 3. Load and prepare shapefile data using the shared utility
        gdf = load_and_prepare_shapefile(shapefile_path, allowed_objectnumm)

        # 4. Process geometries if data exists using utility function
        features = []
        if gdf is not None and not gdf.empty:
            features = process_all_bridges_geometries(gdf)

        # 5. Handle case where no features were generated
        if not features:
            default_point = MapPoint(52.37, 4.89, description="Geen geldige brugpolygonen gevonden/gefilterd.")
            return MapResult([default_point])

        # 6. Return map result
        return MapResult(features)

    # --- Helper methods for regenerate_bridges_action ---

    @staticmethod
    def _get_resource_paths() -> tuple[str, str, str]:
        """Constructs and returns paths to resource files."""
        # Helper function to raise consistent error for missing filter file
        from typing import Never

        def _raise_filter_file_missing(path: str) -> Never:
            """Raises UserError with a consistent message format for missing filter file."""
            raise UserError(f"Filter bestand niet gevonden: {path}")

        try:
            resources_dir = get_resources_dir()  # Use new helper
            shapefile_path = get_default_shapefile_path()  # Use new helper
            filtered_bridges_path = get_filtered_bridges_json_path()  # Use new helper

            # Basic file existence check using shared utility
            # validate_shapefile_exists now returns the path
            try:
                shapefile_path = validate_shapefile_exists(shapefile_path)
            except UserError as ue:
                raise UserError(f"Shapefile validatie fout: {ue}")

            if not os.path.exists(filtered_bridges_path):
                _raise_filter_file_missing(filtered_bridges_path)
            else:
                return resources_dir, shapefile_path, filtered_bridges_path

        except Exception as e:
            raise UserError(f"Fout bij het bepalen van bestandspaden: {e}")

    @WebView("Readme and Changelog", duration_guess=3)
    def view_readme_changelog(self, **kwargs) -> WebResult:  # noqa: ARG002
        """
        Converts the docs files (README.md, CHANGELOG.md) to HTML and presents them in the viewer.

        :return: WebResult.
        """
        with open(README_PATH, encoding="utf-8") as f:
            html_text_readme = markdown.markdown(f.read())
        with open(CHANGELOG_PATH, encoding="utf-8") as f:
            html_text_changelog = markdown.markdown(f.read())
        with open(CSS_PATH, encoding="utf-8") as f:
            html_css = f.read()

        # Create complete HTML documents for each iframe
        readme_doc = f"""<!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>{html_css}</style>
        </head>
        <body>
            {html_text_readme}
        </body>
        </html>"""

        changelog_doc = f"""<!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>{html_css}</style>
        </head>
        <body class="changelog">
            {html_text_changelog}
        </body>
        </html>"""

        # Main HTML structure with responsive layout
        html_content = f"""<!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                /* Minimal styling for the container page only */
                html, body {{
                    margin: 0;
                    padding: 0;
                    height: 100%;
                    overflow: hidden;
                }}
                .container {{
                    display: flex;
                    height: 100vh;
                    width: 100%;
                }}
                .iframe-wrapper {{
                    flex: 1;
                    /* Use lighter border */
                    border-right: 1px solid #eaecef;
                    height: 100%;
                }}
                /* Remove border from the last wrapper */
                .iframe-wrapper:last-child {{
                    border-right: none;
                }}
                .iframe {{
                    width: 100%;
                    height: 100%;
                    border: none;
                }}
                @media (max-width: 768px) {{
                    .container {{
                        flex-direction: column;
                    }}
                    .iframe-wrapper {{
                        height: 50%;
                        border-right: none;
                        /* Use lighter border */
                        border-bottom: 1px solid #eaecef;
                    }}
                    /* Remove border from the last wrapper on mobile */
                    .iframe-wrapper:last-child {{
                        border-bottom: none;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="iframe-wrapper">
                    <iframe class="iframe" srcdoc="{readme_doc.replace('"', "&quot;")}" frameborder="0"></iframe>
                </div>
                <div class="iframe-wrapper">
                    <iframe class="iframe" srcdoc="{changelog_doc.replace('"', "&quot;")}" frameborder="0"></iframe>
                </div>
            </div>
        </body>
        </html>"""

        return WebResult(html=StringIO(html_content))

    @staticmethod
    def _load_filtered_bridges(filtered_bridges_path: str) -> list[dict]:
        """Loads filtered bridge data from the JSON file."""
        try:
            with open(filtered_bridges_path) as f:
                return json.load(f)
        except Exception as e:
            raise UserError(f"Fout bij het laden van {filtered_bridges_path}: {e}")

    @staticmethod
    def _load_shapefile_and_names(shapefile_path: str) -> dict[str, str | None]:
        """Loads the shapefile and creates a mapping from OBJECTNUMM to OBJECTNAAM."""
        try:
            gdf = gpd.read_file(shapefile_path)
            objectnumm_to_name: dict[str, str | None] = {}
            for _, row in gdf.iterrows():
                numm = row.get("OBJECTNUMM")
                if numm:
                    name = row.get("OBJECTNAAM")
                    # Format ID as integer if possible - This part seems unused for map/child generation, removing F841/SIM105 issues

                    # Store None if OBJECTNAAM is missing, None, or empty/whitespace
                    objectnumm_to_name[str(numm)] = name if name and isinstance(name, str) and name.strip() else None
            # If loop completes without error, return the dictionary
            return objectnumm_to_name  # noqa: TRY300
        except Exception as e:
            raise UserError(f"Fout bij het lezen van shapefile {shapefile_path}: {e}")

    @staticmethod
    def _get_existing_child_objectnumms(entity_id: int) -> set[str]:
        """Retrieves the OBJECTNUMM of existing child entities."""
        try:
            viktor_api = api.API()
            parent_entity = viktor_api.get_entity(entity_id)
            existing_children = parent_entity.children(entity_type_names=["Bridge"])
            # Store OBJECTNUMM in child params under 'bridge_objectnumm' key
            return {
                child.last_saved_params.get("bridge_objectnumm") for child in existing_children if child.last_saved_params.get("bridge_objectnumm")
            }
        except Exception as e:
            raise UserError(f"Fout bij het ophalen van bestaande kind-entiteiten: {e}")

    def _create_and_update_children(
        self,
        parent_entity_id: int,
        filtered_bridge_data: list[dict],
        objectnumm_to_name: dict[str, str | None],
    ) -> tuple[int, int]:
        """
        Creates new child entities and updates existing ones with data from filtered_bridges.json.

        :param parent_entity_id: ID of the parent entity.
        :type parent_entity_id: int
        :param filtered_bridge_data: Bridge data from JSON.
        :type filtered_bridge_data: list[dict]
        :param objectnumm_to_name: Mapping of OBJECTNUMM to bridge names.
        :type objectnumm_to_name: dict[str, str | None]
        :returns: Tuple of (updated_count, created_count).
        :rtype: tuple[int, int]
        :raises UserError: If creation/update fails.
        """
        try:
            viktor_api = api.API()
            parent_entity = viktor_api.get_entity(parent_entity_id)
            existing_children = parent_entity.children(entity_type_names=["Bridge"])

            # Create mapping of OBJECTNUMM -> entity
            existing_entities_map = {}
            for child in existing_children:
                obj_numm = child.last_saved_params.get("bridge_objectnumm")
                if obj_numm:
                    existing_entities_map[str(obj_numm)] = child

            updated_count = 0
            created_count = 0

            for bridge_data in filtered_bridge_data:
                objectnumm = bridge_data.get("OBJECTNUMM")
                if not objectnumm:
                    continue

                objectnumm_str = str(objectnumm)
                bridge_name = objectnumm_to_name.get(objectnumm_str)
                child_name = f"{objectnumm_str} - {bridge_name}" if bridge_name else objectnumm_str
                child_params = self._build_child_params(bridge_data, objectnumm_str, bridge_name)

                if objectnumm_str in existing_entities_map:
                    # Update existing entity
                    existing_entity = existing_entities_map[objectnumm_str]
                    existing_entity.set_params(child_params)
                    updated_count += 1
                else:
                    # Create new entity
                    parent_entity.create_child(entity_type_name="Bridge", name=child_name, params=child_params)
                    created_count += 1

            return updated_count, created_count  # noqa: TRY300

        except Exception as e:
            raise UserError(f"Fout tijdens het aanmaken/bijwerken van bruggen: {e}")

    def _create_missing_children(
        self,
        parent_entity_id: int,
        filtered_bridge_data: list[dict],
        objectnumm_to_name: dict[str, str | None],
        existing_objectnumms: set[str],
    ) -> None:
        """Creates child entities for bridges that do not already exist."""
        try:
            parent_entity = api.API().get_entity(parent_entity_id)

            for bridge_data in filtered_bridge_data:
                if self._should_skip_bridge(bridge_data, existing_objectnumms):
                    continue

                objectnumm_str = str(bridge_data["OBJECTNUMM"])
                bridge_name = objectnumm_to_name.get(objectnumm_str)
                child_name = f"{objectnumm_str} - {bridge_name}" if bridge_name else objectnumm_str

                child_params = self._build_child_params(bridge_data, objectnumm_str, bridge_name)
                parent_entity.create_child(entity_type_name="Bridge", name=child_name, params=child_params)
                existing_objectnumms.add(objectnumm_str)

        except Exception as e:
            raise UserError(f"Fout tijdens het aanmaken van kind-entiteiten: {e}")

    def _should_skip_bridge(self, bridge_data: dict, existing_objectnumms: set[str]) -> bool:
        """Check if a bridge should be skipped during creation."""
        objectnumm = bridge_data.get("OBJECTNUMM")
        if not objectnumm:
            return True

        objectnumm_str = str(objectnumm)
        return objectnumm_str in existing_objectnumms

    def _build_child_params(self, bridge_data: dict, objectnumm_str: str, bridge_name: str | None) -> dict:
        """Build parameters for a child bridge entity."""
        basic_info = self._extract_basic_bridge_info(bridge_data)
        geometric_info = self._extract_geometric_info(bridge_data)
        structural_info = self._extract_structural_info(bridge_data)
        width_info = self._extract_width_info(bridge_data)
        reinforcement_info = self._extract_reinforcement_info(bridge_data)

        return {
            "info": {
                "bridge_objectnumm": objectnumm_str,
                "bridge_name": bridge_name,
                **basic_info,
                **geometric_info,
                **structural_info,
                **width_info,
                **reinforcement_info,
            }
        }

    def _extract_basic_bridge_info(self, bridge_data: dict) -> dict:
        """Extract basic bridge information from bridge data."""
        arb_flag = bridge_data.get("vlag_arb", "Niet ingesteld")
        basic_test_ghpo = bridge_data.get("basale_toets_ghpo", "Niet ingesteld")

        return {
            "stadsdeel": bridge_data.get("stadsdeel", ""),
            "straat": bridge_data.get("straat", ""),
            "bridge_type": bridge_data.get("type", ""),
            "construction_year": str(bridge_data.get("stichtingsjaar", "")),
            "usage": bridge_data.get("gebruik", ""),
            "arb_flag": (
                arb_flag
                if arb_flag in ["puur groen", "groen/oranje", "oranje/groen", "puur oranje", "oranje/rood", "puur rood"]
                else "Niet ingesteld"
            ),
            "basic_test_ghpo": (basic_test_ghpo if basic_test_ghpo in ["groen", "oranje", "rood", "nvt", "Wel"] else "Niet ingesteld"),
            "concrete_strength_class": bridge_data.get("betonsterkteklasse", ""),
            "steel_quality_reinforcement": bridge_data.get("staalkwaliteit_wapening", ""),
            "deck_layer": bridge_data.get("deklaag", ""),
            "contractor_iha": bridge_data.get("opdrachtnemer_iha", ""),
        }

    def _extract_geometric_info(self, bridge_data: dict) -> dict:
        """Extract geometric information from bridge data."""
        number_of_spans = bridge_data.get("aantal_velden", 1)
        crossing_angle = bridge_data.get("kruisingshoek", 90.0)
        construction_height = bridge_data.get("constructiehoogte_dek", 0.0)

        # Note: Multi-span bridges may contain semicolon-separated values for some fields
        theoretical_length = self._convert_mm_to_m_if_numeric(bridge_data.get("lth", ""))
        deck_width = self._convert_mm_to_m_if_numeric(bridge_data.get("bbrugdek", ""))

        return {
            "number_of_spans": number_of_spans if isinstance(number_of_spans, int) else 1,
            "static_system": bridge_data.get("statisch_systeem", ""),
            "crossing_angle": crossing_angle if isinstance(crossing_angle, int | float) else 90.0,
            "theoretical_length": theoretical_length,
            "deck_width": deck_width,
            "construction_height": construction_height if isinstance(construction_height, int | float) else 0.0,
            "slenderness": bridge_data.get("slankheid_dek", ""),
            "daily_length": bridge_data.get("ldag", ""),
        }

    def _extract_structural_info(self, bridge_data: dict) -> dict:
        """Extract structural information from bridge data."""
        beams_in_slab = bridge_data.get("liggers_in_plaat", "")
        edge_loading = bridge_data.get("randbelasting", "")

        return {
            "bearing_type": bridge_data.get("opleggingen", ""),
            "orthotropy": bridge_data.get("orthotropie_isotropie", ""),
            "beams_in_slab": self._normalize_boolean_field(beams_in_slab),
            "edge_loading": self._normalize_boolean_field(edge_loading),
        }

    def _extract_width_info(self, bridge_data: dict) -> dict:
        """Extract width distribution information from bridge data."""
        # Note: Multi-span bridges may contain ranges like "1418-1724" for sidewalk widths
        sidewalk_north_east_width = self._convert_mm_to_m_if_numeric(bridge_data.get("breedte_voetpad_noord_oost", ""))
        sidewalk_south_west_width = self._convert_mm_to_m_if_numeric(bridge_data.get("breedte_voetpad_zuid_west", ""))
        roadway_width = self._convert_mm_to_m_if_numeric(bridge_data.get("breedte_rijwegen", ""))
        tram_width = self._convert_mm_to_m_if_numeric(bridge_data.get("breedte_trambaan", ""))
        bicycle_path_width = self._convert_mm_to_m_if_numeric(bridge_data.get("breedte_fietspad", ""))

        return {
            "roadway_width": roadway_width,
            "tram_width": tram_width,
            "bicycle_path_width": bicycle_path_width,
            "sidewalk_north_east_width": sidewalk_north_east_width,
            "sidewalk_south_west_width": sidewalk_south_west_width,
            "edge_beam_thickness": bridge_data.get("dikte_schampkant", ""),
        }

    def _extract_reinforcement_info(self, bridge_data: dict) -> dict:
        """Extract reinforcement information from bridge data."""
        return {
            "support_reinforcement_diameter": bridge_data.get("steunpuntswapening_langsrichting_diameter", ""),
            "support_reinforcement_spacing": bridge_data.get("steunpuntswapening_langsrichting_hoh_afstand", ""),
            "support_reinforcement_layer": bridge_data.get("steunpuntswapening_laag", ""),
            "field_reinforcement_diameter": bridge_data.get("veldwapening_langsrichting_diameter", ""),
            "field_reinforcement_spacing": bridge_data.get("veldwapening_langsrichting_hoh_afstand", ""),
            "field_reinforcement_layer": bridge_data.get("veldwapening_langsrichting_laag", ""),
            "field_reinforcement_transverse_diameter": bridge_data.get("veldwapening_dwarsrichting_diameter", ""),
            "field_reinforcement_transverse_spacing": bridge_data.get("veldwapening_dwarsrichting_hoh_afstand", ""),
            "field_reinforcement_transverse_layer": bridge_data.get("veldwapening_dwarsrichting_laag", ""),
            "concrete_cover": bridge_data.get("dekking_buitenkant_wapening", ""),
        }

    def _convert_mm_to_m_if_numeric(self, value: str) -> str:
        """Convert numeric string from mm to m, otherwise return as-is."""
        if value and str(value).isdigit():
            return str(float(value) / 1000)
        return str(value) if value else ""

    def _normalize_boolean_field(self, value: str) -> str:
        """Normalize boolean-like field values to standard options."""
        if not value:
            return "Onbekend"

        value_lower = str(value).lower()
        if value_lower in ["ja", "yes", "true", "1"]:
            return "Ja"
        if value_lower in ["nee", "no", "false", "0"]:
            return "Nee"
        return "Onbekend"

    # --- Data Download Method ---

    def download_current_bridges_csv(self, **kwargs) -> DownloadResult:  # noqa: ARG002
        """
        Download the current filtered_bridges.json as a CSV file.

        This provides a template that users can edit and re-upload.

        :returns: DownloadResult with CSV file.
        :rtype: DownloadResult
        :raises UserError: If download fails.
        """
        try:
            # Load current bridge data
            json_path = get_filtered_bridges_json_path()

            if not os.path.exists(json_path):
                raise UserError("Geen bruggegevens gevonden. Upload eerst een CSV bestand.")  # noqa: TRY301

            with open(json_path, encoding="utf-8") as f:
                bridges_data = json.load(f)

            if not bridges_data:
                raise UserError("Geen bruggegevens beschikbaar om te downloaden.")  # noqa: TRY301

            # Create reverse mapping: JSON field -> CSV column
            from src.common.csv_parser import COLUMN_MAPPINGS

            reverse_mapping = {v: k for k, v in COLUMN_MAPPINGS.items()}

            # Get all possible CSV columns
            csv_columns = list(COLUMN_MAPPINGS.keys())

            # Create CSV in memory
            output = StringIO()
            writer = csv.DictWriter(output, fieldnames=csv_columns, delimiter=";", lineterminator="\n")
            writer.writeheader()

            # Convert each bridge record back to CSV format
            for bridge in bridges_data:
                csv_row = {}
                for json_field, value in bridge.items():
                    csv_column = reverse_mapping.get(json_field)
                    if csv_column:
                        # Convert boolean back to ja/nee
                        if isinstance(value, bool):
                            csv_row[csv_column] = "ja" if value else "nee"
                        else:
                            csv_row[csv_column] = str(value) if value is not None else ""
                writer.writerow(csv_row)

            # Convert to bytes
            csv_content = output.getvalue().encode("utf-8-sig")  # Add BOM for Excel compatibility

            # Create File object
            csv_file = File.from_data(csv_content)

            return DownloadResult(csv_file, "bruggegevens.csv")

        except UserError:
            raise
        except Exception as e:
            raise UserError(f"Fout bij downloaden van bruggegevens: {e}")

    # --- Data Upload Helper Methods ---

    @staticmethod
    def _clean_bridge_data(bridges_data: list[dict]) -> list[dict]:
        """
        Clean bridge data by removing problematic Unicode characters.

        :param bridges_data: List of bridge data dictionaries.
        :type bridges_data: list[dict]
        :returns: Cleaned bridge data.
        :rtype: list[dict]
        """

        def clean_value(value: dict | list | str | float | bool | None) -> dict | list | str | int | float | bool | None:
            """Recursively clean values in the data structure."""
            if isinstance(value, str):
                # Remove Unicode replacement character and other problematic characters
                cleaned = value.replace("\ufffd", "")
                # Remove other control characters except newlines and tabs
                return "".join(char for char in cleaned if char >= " " or char in "\n\t")
            if isinstance(value, dict):
                return {k: clean_value(v) for k, v in value.items()}
            if isinstance(value, list):
                return [clean_value(item) for item in value]
            return value

        return [clean_value(bridge) for bridge in bridges_data]  # type: ignore[misc]

    # --- Data Upload Action Method ---

    def process_bridge_data_upload(self, params: Parametrization, **kwargs) -> None:  # noqa: ARG002
        """
        Process uploaded CSV or Excel file and update filtered_bridges.json.

        :param params: The parametrization containing the uploaded file.
        :type params: Parametrization
        :raises UserError: If file processing fails.
        """
        from src.common.csv_parser import parse_bridge_csv, parse_bridge_excel

        # Get uploaded file
        uploaded_file = params.data_upload.bridge_data_file
        if not uploaded_file:
            raise UserError("Geen bestand geüpload. Upload eerst een CSV of Excel bestand.")

        try:
            # Get filename from FileResource
            file_name = uploaded_file.filename if hasattr(uploaded_file, "filename") else "unknown"
            file_extension = os.path.splitext(file_name.lower())[1]

            # Validate file type
            if file_extension not in [".csv", ".xlsx", ".xls"]:
                raise UserError(f"Ongeldig bestandstype: {file_extension}. Alleen .csv en .xlsx zijn toegestaan.")  # noqa: TRY301

            # Read file content using VIKTOR's File API
            with uploaded_file.file.open_binary() as f:
                file_content = f.read()

            # Parse based on file type
            if file_extension == ".csv":
                bridges_data = parse_bridge_csv(file_content)
            elif file_extension in [".xlsx", ".xls"]:
                bridges_data = parse_bridge_excel(file_content)
            else:
                raise UserError(f"Ongeldig bestandstype: {file_extension}. Alleen .csv en .xlsx zijn toegestaan.")  # noqa: TRY301

            # Clean data: remove Unicode replacement characters and other problematic characters
            bridges_data = self._clean_bridge_data(bridges_data)

            # Get path to filtered_bridges.json
            json_path = get_filtered_bridges_json_path()

            # Write to JSON file
            # Use ensure_ascii=True to avoid any encoding issues - characters will be escaped
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(bridges_data, f, indent=2, ensure_ascii=True)

            # Show success message to user
            bridge_count = len(bridges_data)
            UserMessage.success(
                f"Upload succesvol! {bridge_count} bruggen verwerkt en opgeslagen. "
                f"Gebruik nu de '(Her)genereer Bruggen' knop op de 'Overzicht Bruggen' pagina om de bruggen te laden."
            )

        except ValueError as e:
            # Clean error message to avoid encoding issues
            error_msg = str(e).replace("\ufffd", "?").encode("ascii", errors="replace").decode("ascii")
            raise UserError(f"Fout bij verwerken van bestand: {error_msg}")
        except Exception as e:
            # Clean error message to avoid encoding issues
            error_msg = str(e).replace("\ufffd", "?").encode("ascii", errors="replace").decode("ascii")
            raise UserError(f"Onverwachte fout bij verwerken van bestand: {error_msg}")

    # --- Main Action Method ---

    def regenerate_bridges_action(self, entity_id: int, **kwargs) -> None:  # noqa: ARG002
        """
        Loads bridges from filtered_bridges.json and creates/updates child entities.

        Creates new entities for bridges that don't exist yet.
        Updates existing entities with new data from the JSON file.
        """
        # 1. Get paths
        _resources_dir, shapefile_path, filtered_bridges_path = self._get_resource_paths()

        # 2. Load data
        filtered_bridge_data = self._load_filtered_bridges(filtered_bridges_path)
        objectnumm_to_name = self._load_shapefile_and_names(shapefile_path)

        # 3. Get existing children and update them
        updated_count, created_count = self._create_and_update_children(
            parent_entity_id=entity_id,
            filtered_bridge_data=filtered_bridge_data,
            objectnumm_to_name=objectnumm_to_name,
        )

        # 4. Show success message
        UserMessage.success(f"Bruggen (her)gegenereerd: {created_count} nieuwe bruggen aangemaakt, {updated_count} bestaande bruggen bijgewerkt.")
