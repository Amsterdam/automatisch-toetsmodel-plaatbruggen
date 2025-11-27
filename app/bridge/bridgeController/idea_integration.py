"""
IDEA StatiCa integration component for BridgeController.

This component provides all IDEA RCS-related functionality including:
- Cross-section analysis views
- Unique cross-section identification
- XML model and analysis downloads
"""

import zipfile
from datetime import datetime, timezone

from viktor.core import File, progress_message
from viktor.errors import UserError
from viktor.result import DownloadResult
from viktor.views import TableResult, TableView

from app.bridge.analysis_cache import get_cached_analysis_results, get_idea_analysis_results, get_idea_model_only
from app.bridge.parametrization import BridgeParametrization
from app.bridge.utils import validate_reinforcement_zone_selections
from src.common.constants.technical import AnalysisType
from src.integrations.idea_integration.idea_data_models import extract_bridge_idea_input_data
from src.integrations.idea_integration.idea_interface import _get_unique_matching_zone_keys
from src.integrations.idea_integration.idea_results_processor import IdeaResultsProcessor


class IdeaIntegration:
    """
    Component providing IDEA StatiCa RCS integration.

    Contains methods for:
    - Unique cross-section identification
    - IDEA RCS capacity analysis views
    - XML model generation and download
    - Complete analysis results download
    """

    @TableView("Unieke dwarsprofielen voor IDEA RCS", duration_guess=2)
    def get_view_unique_idea_cross_sections(self, params: BridgeParametrization, **kwargs) -> TableResult:  # noqa: ARG002
        """
        Display a table with unique matching zone keys for IDEA RCS.

        Shows unique combinations of zone thickness and reinforcement configurations
        that will require separate IDEA RCS analyses.

        :param params: Bridge parametrization object
        :type params: BridgeParametrization
        :param kwargs: Additional arguments
        :returns: TableResult with unique zone keys
        :rtype: TableResult
        """
        validate_reinforcement_zone_selections(params)

        # Extract input data from params for IDEA integration
        input_data = extract_bridge_idea_input_data(params)
        unique_matching_zone_keys, grouped_thickness, grouped_rebar_configs = _get_unique_matching_zone_keys(input_data)

        # Add sequential ID as first column
        data = [[idx, value[0], value[1], str(value[2])] for idx, value in enumerate(unique_matching_zone_keys, start=1)]
        columns = ["Unieke sectie", "Zone_dikte", "Wapeningsconfiguratie", "Zones"]

        return TableResult(data, column_headers=columns)

    @TableView("IDEA RCS resultaten", duration_guess=90)
    def get_view_idea_rcs_results(self, params: BridgeParametrization, **kwargs) -> TableResult:
        """
        Display a table with results from the IDEA RCS analysis.

        Shows cross-section capacity analysis results including utilization ratios
        and capacity checks for all unique cross-sections.

        :param params: Bridge parametrization object
        :type params: BridgeParametrization
        :param kwargs: Additional arguments including entity_id
        :returns: TableResult with IDEA RCS analysis results
        :rtype: TableResult
        :raises UserError: If analysis fails or required data is missing
        """
        validate_reinforcement_zone_selections(params)

        if not hasattr(params, "bridge_segments_array") or not params.bridge_segments_array:
            raise UserError("Geen brugsegmenten gedefinieerd. Voeg eerst segmenten toe.")

        entity_id = kwargs.get("entity_id")
        if entity_id is None:
            raise UserError("Entity ID niet gevonden. Cache functionaliteit niet beschikbaar.")

        progress_message("Laden van gecachte IDEA RCS analyse of starten nieuwe analyse...")
        cached_results = get_cached_analysis_results(params, AnalysisType.IDEA, entity_id, get_idea_analysis_results)
        if cached_results is None:
            raise UserError("IDEA analyse gefaald of geen gecachte resultaten beschikbaar.")

        progress_message("Verwerken IDEA resultaten voor weergave...")
        result = IdeaResultsProcessor.process_idea_results(cached_results)

        if not result["success"] and "error" in result:
            error_msg = result["error"]
            if "geen gecachte resultaten" in error_msg or "Entity ID" in error_msg:
                raise UserError(error_msg)

        return TableResult(result["data"], column_headers=result["headers"])

    def download_idea_xml_file(self, params: BridgeParametrization, **kwargs) -> DownloadResult:
        """
        Download IDEA StatiCa RCS XML input file for cross-section analysis.

        Creates a rectangular beam cross-section model from the bridge segments
        with automatic reinforcement layout and sample loads.

        :param params: Bridge parametrization object
        :type params: BridgeParametrization
        :param kwargs: Additional arguments including entity_id
        :returns: XML file download for IDEA RCS
        :rtype: DownloadResult
        :raises UserError: If model generation fails or entity ID is missing
        """
        validate_reinforcement_zone_selections(params)

        def _raise_entity_id_error() -> None:
            raise UserError("Entity ID not found in kwargs")

        def _raise_model_creation_error() -> None:
            raise UserError("IDEA model creation failed or no cached results available")

        def _raise_incomplete_model_error() -> None:
            raise UserError("Cached IDEA model is incomplete")

        try:
            entity_id = kwargs.get("entity_id")
            if entity_id is None:
                _raise_entity_id_error()

            assert entity_id is not None  # type: ignore[unreachable]
            progress_message("Laden van gecachte IDEA model of genereren nieuw model...")
            cached_results = get_cached_analysis_results(params, AnalysisType.IDEA, entity_id, get_idea_model_only)
            if cached_results is None:
                _raise_model_creation_error()

            assert cached_results is not None  # type: ignore[unreachable]
            idea_xml_input_bytes = cached_results.get("idea_xml_input_bytes")
            if idea_xml_input_bytes is None:
                _raise_incomplete_model_error()

            assert idea_xml_input_bytes is not None  # type: ignore[unreachable]
            xml_content = (
                idea_xml_input_bytes.getvalue()
                if hasattr(idea_xml_input_bytes, "getvalue")
                else idea_xml_input_bytes.read()
                if hasattr(idea_xml_input_bytes, "read")
                else b""
            )

            if not xml_content:
                self._raise_empty_idea_xml_error()  # type: ignore[attr-defined]

            analysis_datetime = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

            return DownloadResult(idea_xml_input_bytes, f"IDEA_rcs_model_input{params.info.bridge_objectnumm}_{analysis_datetime}.xml")

        except Exception as e:
            raise UserError(f"IDEA RCS model input XML generatie gefaald: {e!s}")

    def download_idea_analysis_results(self, params: BridgeParametrization, **kwargs) -> DownloadResult:
        """
        Download IDEA StatiCa RCS analysis results for cross-section capacity assessment.

        Executes the cross-section analysis and returns:
        - Input XML model file
        - Analysis results with capacity calculations
        - Interaction diagrams and stress distributions

        :param params: Bridge parametrization object
        :type params: BridgeParametrization
        :param kwargs: Additional arguments including entity_id
        :returns: ZIP with analysis input and results
        :rtype: DownloadResult
        :raises UserError: If analysis fails or entity ID is missing
        """
        validate_reinforcement_zone_selections(params)

        entity_id = kwargs.get("entity_id")
        if entity_id is None:
            raise UserError("Entity ID not found in kwargs")

        progress_message("Laden van gecachte IDEA analyse resultaten...")
        cached_results = get_cached_analysis_results(params, AnalysisType.IDEA, entity_id, get_idea_analysis_results)
        if cached_results is None:
            raise UserError("IDEA analysis failed or no cached results available")

        assert cached_results is not None  # type: ignore[unreachable]
        model = cached_results.get("model")
        idea_xml_input_bytes = cached_results.get("idea_xml_input_bytes")
        idea_rcs_model = cached_results.get("idea_rcs_model")
        idea_xml_output_bytes = cached_results.get("idea_xml_output_bytes")
        output_content = cached_results.get("output_content")

        if model is None or idea_xml_input_bytes is None or idea_rcs_model is None or idea_xml_output_bytes is None or output_content is None:
            raise UserError("Cached IDEA results are incomplete")

        assert idea_xml_input_bytes is not None  # type: ignore[unreachable]
        idea_input_xml_content = (
            idea_xml_input_bytes.getvalue()
            if hasattr(idea_xml_input_bytes, "getvalue")
            else idea_xml_input_bytes.read()
            if hasattr(idea_xml_input_bytes, "read")
            else b""
        )

        if not idea_input_xml_content:
            self._raise_empty_idea_xml_error()  # type: ignore[attr-defined]

        analysis_datetime = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        zip_file_obj = File()
        with zipfile.ZipFile(zip_file_obj.source, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr(f"IDEA_rcs_model_input_{params.info.bridge_objectnumm}_{analysis_datetime}.xml", idea_input_xml_content)

            z.writestr(
                f"IDEA_rcs_model_{params.info.bridge_objectnumm}_{analysis_datetime}.ideaRcs",
                idea_rcs_model.getvalue()
                if hasattr(idea_rcs_model, "getvalue")
                else idea_rcs_model.read()
                if hasattr(idea_rcs_model, "read")
                else b"",
            )

            z.writestr(
                f"IDEA_rcs_model_output_{params.info.bridge_objectnumm}_{analysis_datetime}.xml",
                idea_xml_output_bytes.getvalue()
                if hasattr(idea_xml_output_bytes, "getvalue")
                else idea_xml_output_bytes.read()
                if hasattr(idea_xml_output_bytes, "read")
                else b"",
            )

        return DownloadResult(zip_file_obj, f"IDEA_rcs_analysis_complete_{params.info.bridge_objectnumm}_{analysis_datetime}.zip")
