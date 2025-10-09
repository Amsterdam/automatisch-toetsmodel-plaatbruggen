"""
Utility methods and error handlers for BridgeController.

This mixin provides common helper methods, error handling,
validation functions, and data processing utilities used
across different controller mixins.
"""

from pathlib import Path
from typing import Any

import viktor.api_v1 as api_sdk
import viktor.errors
from app.constants import SCIA_TEMPLATE_PATH
from src.integrations.scia_integration.scia_force_envelopes import get_force_envelope_summary
from viktor.errors import UserError
from viktor.views import MapPoint, MapResult


class ControllerUtilsMixin:
    """
    Mixin providing utility methods for BridgeController.

    Contains helper methods for:
    - Entity data retrieval
    - Template path management
    - Error handling and raising
    - Data processing and validation
    - Force state formatting
    """

    # ============================================================================================================
    # Entity and Template Management
    # ============================================================================================================

    def _get_bridge_entity_data(self, entity_id: int) -> tuple[str | None, str | None, MapResult | None]:
        """
        Fetch bridge entity data (OBJECTNUMM and name) using the VIKTOR API.

        :param entity_id: VIKTOR entity ID
        :type entity_id: int
        :returns: Tuple of (objectnumm, name, error_result)
        :rtype: tuple[str | None, str | None, MapResult | None]
        """
        if not entity_id:
            return None, None, MapResult([MapPoint(52.37, 4.89, description="Entity ID niet gevonden.")])
        try:
            viktor_api = api_sdk.API()
            current_entity = viktor_api.get_entity(entity_id)
            last_params = current_entity.last_saved_params
            info_page_params = last_params.get("info")

            objectnumm = info_page_params.bridge_objectnumm if info_page_params and hasattr(info_page_params, "bridge_objectnumm") else None
            name = info_page_params.bridge_name if info_page_params and hasattr(info_page_params, "bridge_name") else ""
            if objectnumm is None:
                return None, None, MapResult([MapPoint(52.37, 4.89, description="OBJECTNUMM van brug niet gevonden in opgeslagen parameters.")])
            return objectnumm, name, None  # noqa: TRY300
        except Exception as e:
            return None, None, MapResult([MapPoint(52.37, 4.89, description=f"Fout bij ophalen entity data: {e}")])

    def _get_scia_template_path(self) -> Path:
        """
        Get the path to the SCIA template file.

        :returns: Path to the model.esa template file
        :rtype: Path
        :raises UserError: If template file is not found
        """
        template_path = SCIA_TEMPLATE_PATH

        if not template_path.exists():
            raise UserError(f"SCIA template file niet gevonden: {template_path}")

        return template_path

    # ============================================================================================================
    # Error Handlers
    # ============================================================================================================

    def _raise_no_bridge_segments_error(self) -> None:
        """Raise UserError for missing bridge segments."""
        raise UserError("Geen brugsegmenten gedefinieerd. Ga naar de 'Invoer' pagina om de brug dimensies in te stellen.")

    def _raise_empty_xml_error(self) -> None:
        """Raise UserError for empty XML file."""
        raise UserError("XML bestand is leeg - SCIA model generatie gefaald")

    def _raise_empty_def_error(self) -> None:
        """Raise UserError for empty definition file."""
        raise UserError("Definition bestand is leeg - SCIA model generatie gefaald")

    def _raise_empty_esa_error(self) -> None:
        """Raise UserError for empty ESA file."""
        raise UserError("ESA bestand is leeg - SCIA worker uitvoering gefaald")

    def _raise_no_idea_segments_error(self) -> None:
        """Raise UserError for missing bridge segments in IDEA RCS model."""
        raise UserError("Geen brugsegmenten gevonden voor IDEA RCS model")

    def _raise_no_idea_analysis_segments_error(self) -> None:
        """Raise UserError for missing bridge segments in IDEA RCS analysis."""
        raise UserError("Geen brugsegmenten gevonden voor IDEA RCS analyse")

    def _raise_empty_idea_xml_error(self) -> None:
        """Raise UserError for empty IDEA XML file."""
        raise UserError("XML bestand is leeg - IDEA RCS model generatie gefaald")

    def _raise_missing_esa_error(self, error_details: str) -> None:
        """
        Raise UserError for missing ESA model.

        :param error_details: Details about the error
        :type error_details: str
        """
        raise UserError(f"SCIA analyse uitgevoerd maar ESA model ontbreekt: {error_details}")

    def _raise_analysis_failed_error(self) -> None:
        """Raise UserError for failed analysis."""
        raise UserError("SCIA analyse kon niet worden uitgevoerd. Controleer de brug parameters en probeer opnieuw.")

    def _raise_no_xml_output_error(self) -> None:
        """Raise error when no XML output file is available."""
        raise UserError("No XML output file available from SCIA analysis")

    def _raise_unexpected_type_error(self, fresh_xml_output_file: object) -> None:
        """
        Raise error for unexpected type of fresh_xml_output_file.

        :param fresh_xml_output_file: The object with unexpected type
        :type fresh_xml_output_file: object
        """
        raise UserError(f"Unexpected type for fresh_xml_output_file: {type(fresh_xml_output_file)}")

    def _handle_scia_exception(self, e: Exception) -> None:
        """
        Handle SCIA-related exceptions and raise appropriate UserError.

        :param e: Exception to handle
        :type e: Exception
        """
        if isinstance(e, ImportError):
            raise UserError(f"VIKTOR SCIA module niet beschikbaar: {e!s}\n\nDeze functie vereist de VIKTOR SDK met SCIA integratie.")
        if isinstance(e, viktor.errors.LicenseError):
            raise UserError(
                f"SCIA Engineer licentie fout: {e!s}\n\nControleer uw SCIA Engineer licentie en zorg ervoor dat deze correct is geconfigureerd."
            )
        if isinstance(e, viktor.errors.ExecutionError):
            raise UserError(
                f"SCIA analyse uitvoering gefaald: {e!s}\n\n"
                "De externe SCIA analyse is niet succesvol voltooid. "
                "Controleer of SCIA Engineer correct is geïnstalleerd en toegankelijk is."
            )
        if isinstance(e, viktor.errors.ModelError):
            raise UserError(
                f"SCIA model fout: {e!s}\n\n"
                "Er was een probleem met de SCIA model generatie of analyse. "
                "Controleer uw brug parameters en probeer opnieuw."
            )
        if isinstance(e, FileNotFoundError):
            raise UserError(
                f"Template bestand niet gevonden: {e!s}\n\n"
                "Het SCIA template bestand ontbreekt of is niet toegankelijk. "
                "Controleer de template configuratie."
            )
        if isinstance(e, PermissionError):
            raise UserError(
                f"Toestemmings fout: {e!s}\n\n"
                "Onvoldoende toestemmingen om SCIA bestanden te openen of de analyse uit te voeren. "
                "Controleer bestandsrechten en gebruikers toegangsrechten."
            )
        raise UserError(f"Onverwachte fout tijdens SCIA analyse: {e!s}\n\nProbeer in plaats daarvan de XML-bestanden te downloaden.")

    def _get_scia_timeout_message(self) -> str:
        """Get standardized SCIA timeout error message."""
        return (
            "⏱️ SCIA analyse time-out na 10 minuten.\n\n"
            "Mogelijke oplossingen:\n"
            "• Verminder het aantal brugsegmenten\n"
            "• Vereenvoudig de belastingzones\n"
            "• Download de XML bestanden en analyseer handmatig in SCIA\n"
            "• Probeer het later opnieuw als de server minder belast is\n\n"
            "Als het probleem aanhoudt, neem contact op met support."
        )

    def _get_scia_1d_timeout_message(self) -> str:
        """Get standardized SCIA 1D timeout error message."""
        return (
            "⏱️ SCIA 1D analyse time-out na 10 minuten.\n\n"
            "Mogelijke oplossingen:\n"
            "• Verminder het aantal brugsegmenten\n"
            "• Vereenvoudig de belastingzones\n"
            "• Download de XML bestanden en analyseer handmatig in SCIA\n"
            "• Probeer het later opnieuw als de server minder belast is\n\n"
            "Als het probleem aanhoudt, neem contact op met support."
        )

    def _get_scia_exception_message(self, e: Exception) -> str:
        """Get appropriate error message based on exception type."""
        if "timeout" in str(e).lower():
            return "SCIA analyse time-out. Het model duurt te lang om te berekenen. Probeer minder segmenten of eenvoudigere belastingen."
        if "license" in str(e).lower():
            return "SCIA licentie probleem. Controleer of SCIA Engineer correct is geïnstalleerd en een geldige licentie heeft."
        if "worker" in str(e).lower():
            return "SCIA worker niet beschikbaar. De externe SCIA service is niet actief. Probeer later opnieuw of download de XML bestanden."
        return f"SCIA analyse fout: {str(e)[:200]}..."

    def _get_scia_1d_exception_message(self, e: Exception) -> str:
        """Get appropriate error message for 1D analysis based on exception type."""
        if "timeout" in str(e).lower():
            return "SCIA 1D analyse time-out. Het model duurt te lang om te berekenen. Probeer minder segmenten of eenvoudigere belastingen."
        if "license" in str(e).lower():
            return "SCIA licentie probleem. Controleer of SCIA Engineer correct is geïnstalleerd en een geldige licentie heeft."
        if "worker" in str(e).lower():
            return "SCIA worker niet beschikbaar. De externe SCIA service is niet actief. Probeer later opnieuw of download de XML bestanden."
        return f"SCIA 1D analyse fout: {str(e)[:200]}..."

    # ============================================================================================================
    # Data Processing Helpers
    # ============================================================================================================

    def _process_single_force_value(self, m_x: float, m_y: float, v_x: float, v_y: float, plate_name: str) -> tuple[float, float, float, str]:
        """
        Process a single set of force values and return calculated results.

        :param m_x: Moment in x direction
        :param m_y: Moment in y direction
        :param v_x: Shear in x direction
        :param v_y: Shear in y direction
        :param plate_name: Name of the plate
        :returns: Tuple of (moment, shear, max_normal_comp, plate_name)
        """
        moment = (m_x**2 + m_y**2) ** 0.5
        shear = (v_x**2 + v_y**2) ** 0.5
        max_normal_comp = max(abs(m_x), abs(m_y))
        return moment, shear, max_normal_comp, plate_name

    def _process_internal_forces_data(self, forces_data: dict[str, Any]) -> tuple[float | None, float | None, float | None, str]:
        """
        Process internal forces data and return maximum values and plate name.

        :param forces_data: Dictionary containing force data
        :returns: Tuple of (max_moment, max_shear, max_normal, plate_with_max_moment)
        """
        max_moment = None
        max_shear = None
        max_normal = None
        plate_with_max_moment = "Onbekend"

        if not isinstance(forces_data, dict) or "Basis grootheden" not in forces_data:
            return max_moment, max_shear, max_normal, plate_with_max_moment

        data = forces_data["Basis grootheden"]
        required_columns = ["m_x", "m_y", "v_x", "v_y"]
        if not all(col in data for col in required_columns):
            return max_moment, max_shear, max_normal, plate_with_max_moment

        m_x_values = data["m_x"]
        m_y_values = data["m_y"]
        v_x_values = data["v_x"]
        v_y_values = data["v_y"]
        plate_names = data.get("Naam", [])

        valid_results = []
        for i in range(len(m_x_values)):
            try:
                m_x = float(m_x_values[i])
                m_y = float(m_y_values[i])
                v_x = float(v_x_values[i])
                v_y = float(v_y_values[i])
            except (ValueError, TypeError, IndexError):
                continue

            plate_name = plate_names[i] if i < len(plate_names) else f"Plate_{i + 1}"
            valid_results.append((m_x, m_y, v_x, v_y, plate_name))

        for m_x, m_y, v_x, v_y, plate_name in valid_results:
            moment, shear, max_normal_comp, _ = self._process_single_force_value(m_x, m_y, v_x, v_y, plate_name)

            if max_moment is None or abs(moment) > abs(max_moment):
                max_moment = moment
                plate_with_max_moment = plate_name
            if max_shear is None or abs(shear) > abs(max_shear):
                max_shear = shear
            if max_normal is None or max_normal_comp > max_normal:
                max_normal = max_normal_comp

        return max_moment, max_shear, max_normal, plate_with_max_moment

    def _find_displacement_columns(self, data: object) -> tuple[str | None, str | None]:
        """
        Find displacement and rotation columns in the data.

        :param data: Data object to search
        :returns: Tuple of (disp_col, rot_col)
        """
        if not hasattr(data, "columns"):
            return None, None

        columns = list(data.columns)
        disp_col = None
        rot_col = None

        for col in columns:
            if "displacement" in col.lower() or "verplaatsing" in col.lower():
                disp_col = col
            elif "rotation" in col.lower() or "rotatie" in col.lower():
                rot_col = col

        return disp_col, rot_col

    def _process_displacement_data(self, displacement_data: dict[str, Any]) -> tuple[float | None, float | None]:
        """
        Process displacement data and return maximum values.

        :param displacement_data: Dictionary containing displacement data
        :returns: Tuple of (max_displacement, max_rotation)
        """
        max_displacement = None
        max_rotation = None

        if not isinstance(displacement_data, dict) or "Table0" not in displacement_data:
            return max_displacement, max_rotation

        data = displacement_data["Table0"]
        disp_col, rot_col = self._find_displacement_columns(data)
        if not disp_col or not rot_col:
            return max_displacement, max_rotation

        try:
            disp_values = data[disp_col].values
            rot_values = data[rot_col].values
        except (AttributeError, KeyError):
            return max_displacement, max_rotation

        valid_results = []
        for i in range(len(disp_values)):
            try:
                displacement = float(disp_values[i])
                rotation = float(rot_values[i])
            except (ValueError, TypeError):
                continue

            valid_results.append((displacement, rotation))

        for displacement, rotation in valid_results:
            if max_displacement is None or abs(displacement) > abs(max_displacement):
                max_displacement = displacement
            if max_rotation is None or abs(rotation) > abs(max_rotation):
                max_rotation = rotation

        return max_displacement, max_rotation

    def _get_engineering_assessment(self, max_moment: float | None) -> str:
        """
        Get engineering assessment based on moment magnitude.

        :param max_moment: Maximum moment value
        :returns: Assessment string
        """
        if max_moment is None:
            return "❓ Onbekend"

        if max_moment < 1000000:  # 1000 kNm
            return "✅ Laag"
        if max_moment < 5000000:  # 5000 kNm
            return "⚠️ Gemiddeld"
        return "❌ Hoog"

    def _format_complete_force_state(self, forces: dict[str, float], units_mapping: dict[str, str] | None = None) -> str:
        """
        Format the complete force state as a compact readable string.

        :param forces: Dictionary of force components
        :param units_mapping: Optional mapping of units for each component
        :returns: Formatted force state string
        """
        force_parts = []
        units_mapping = units_mapping or {}

        # Normal force
        if "N" in forces and abs(forces["N"]) > 0.1:
            unit = units_mapping.get("N", "")
            unit_suffix = f" {unit}" if unit else ""
            force_parts.append(f"N={forces['N']:.0f}{unit_suffix}")

        # Shear forces
        if "Vy" in forces and abs(forces["Vy"]) > 0.1:
            unit = units_mapping.get("Vy", "")
            unit_suffix = f" {unit}" if unit else ""
            force_parts.append(f"Vy={forces['Vy']:.0f}{unit_suffix}")
        if "Vz" in forces and abs(forces["Vz"]) > 0.1:
            unit = units_mapping.get("Vz", "")
            unit_suffix = f" {unit}" if unit else ""
            force_parts.append(f"Vz={forces['Vz']:.0f}{unit_suffix}")

        # Moments
        if "Mxd+" in forces and abs(forces["Mxd+"]) > 0.1:
            unit = units_mapping.get("Mxd+", "")
            unit_suffix = f" {unit}" if unit else ""
            force_parts.append(f"Mx+={forces['Mxd+']:.0f}{unit_suffix}")
        if "Mxd-" in forces and abs(forces["Mxd-"]) > 0.1:
            unit = units_mapping.get("Mxd-", "")
            unit_suffix = f" {unit}" if unit else ""
            force_parts.append(f"Mx-={forces['Mxd-']:.0f}{unit_suffix}")
        if "Myd+" in forces and abs(forces["Myd+"]) > 0.1:
            unit = units_mapping.get("Myd+", "")
            unit_suffix = f" {unit}" if unit else ""
            force_parts.append(f"My+={forces['Myd+']:.0f}{unit_suffix}")
        if "Myd-" in forces and abs(forces["Myd-"]) > 0.1:
            unit = units_mapping.get("Myd-", "")
            unit_suffix = f" {unit}" if unit else ""
            force_parts.append(f"My-={forces['Myd-']:.0f}{unit_suffix}")

        if not force_parts:
            return "All ≈ 0"

        return " | ".join(force_parts)

    def _print_scia_results_summary(self, results: dict[str, Any]) -> None:
        """
        Print a summary of SCIA results to console for debugging/development.

        :param results: Dictionary containing SCIA analysis results
        """
        results.get("analysis_status", {})

        xml_parsing = results.get("xml_parsing", {})
        if isinstance(xml_parsing, dict):
            parsed_tables = xml_parsing.get("parsed_tables", {})
            [name for name in parsed_tables if "Resultaatklasses" in name]

        results.get("displacements", {})
        results.get("internal_forces", {})

        if isinstance(xml_parsing, dict):
            table_details = xml_parsing.get("table_details", [])
            [t for t in table_details if t.get("has_data", False)]

        self._print_force_envelopes(results)

    def _print_sample_engineering_values(self, results: dict[str, Any]) -> None:  # noqa: C901
        """
        Print sample engineering values from SCIA results.

        :param results: Dictionary containing SCIA analysis results
        """
        internal_forces = results.get("internal_forces", {})
        if internal_forces.get("status") == "success":
            force_data = internal_forces.get("data", {})
            if force_data and hasattr(force_data, "rows"):
                try:
                    for i, row in enumerate(force_data.rows[:3]):
                        if hasattr(row, "m_x") and hasattr(row, "v_x"):
                            getattr(row, "element_name", f"Element {i + 1}")
                            float(row.m_x) / 1000000  # Convert to kNm
                            float(row.v_x) / 1000  # Convert to kN
                            getattr(row, "load_case", "Unknown")
                except Exception:
                    pass

        displacements = results.get("displacements", {})
        if displacements.get("status") == "success":
            disp_data = displacements.get("data", {})
            if disp_data and hasattr(disp_data, "rows"):
                try:
                    for i, row in enumerate(disp_data.rows[:3]):
                        if hasattr(row, "u_z"):
                            getattr(row, "element_name", f"Point {i + 1}")
                            float(row.u_z) * 1000  # Convert to mm
                            getattr(row, "load_case", "Unknown")
                except Exception:
                    pass

    def _print_force_envelopes(self, results: dict[str, Any]) -> None:
        """
        Extract and print force envelopes from SCIA results.

        :param results: Dictionary containing SCIA analysis results
        """
        try:
            from src.integrations.scia_integration.scia_force_envelopes import extract_force_envelopes

            envelopes = extract_force_envelopes(results)

            if not envelopes:
                return

            for section_envelopes in envelopes.values():
                for envelope in section_envelopes.values():
                    max_data = envelope["max"]
                    min_data = envelope["min"]

                    if max_data["value"] == float("-inf") or min_data["value"] == float("inf"):
                        continue

                    max_data["forces"]
                    min_data["forces"]

            get_force_envelope_summary(envelopes)

        except Exception:
            pass
