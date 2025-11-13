"""
SCIA Engineer integration component for BridgeController.

This component provides all SCIA-related functionality including:
- Multiple table views for different analysis types (ULS, SLS kar, SLS freq)
- 1D and 2D result views
- ESA model and XML file downloads
- Force envelope analysis
"""

import traceback
import zipfile
from io import BytesIO
from typing import NoReturn

from viktor.core import File, progress_message
from viktor.errors import UserError
from viktor.result import DownloadResult
from viktor.views import PlotlyResult, PlotlyView, TableResult, TableView

from app.bridge.analysis_cache import get_cached_analysis_results
from app.bridge.parametrization import BridgeParametrization
from app.bridge.scia_model_builder import create_bridge_scia_model, get_scia_analysis_results
from src.common.constants.technical import AnalysisType
from src.integrations.scia_integration.results.scia_result_views import (
    create_scia_cs_envelope_table,
    create_scia_cs_plotly_visualization,
    create_scia_cs_results_table,
)


class SciaIntegration:
    """
    Component providing SCIA Engineer integration.

    Contains methods for:
    - SCIA CS (Cross Section) analysis table views (ULS, SLS freq)
    - Force envelope analysis combining ULS and SLS freq
    - ESA model and XML file downloads
    - SCIA-specific error handling
    """

    # ============================================================================================================
    # SCIA CS (Cross Section) Results Table Views
    # ============================================================================================================

    def _get_scia_cs_results_table(
        self,
        params: BridgeParametrization,
        analysis_type: str,
        **kwargs,
    ) -> TableResult:
        """
        Internal helper method to get SCIA CS (Cross Section) results table.

        Handles the common logic for fetching and processing CS results for different analysis types.

        :param params: Bridge parametrization object
        :type params: BridgeParametrization
        :param analysis_type: Type of analysis (e.g., "ULS", "SLS kar", "SLS freq")
        :type analysis_type: str
        :param kwargs: Additional arguments including entity_id
        :returns: TableResult with CS analysis results
        :rtype: TableResult
        :raises UserError: If analysis fails or bridge segments are missing
        """
        if not params.bridge_segments_array:
            raise UserError("Geen brugsegmenten gedefinieerd. Voeg eerst segmenten toe.")

        template_path = self._get_scia_template_path()  # type: ignore[attr-defined]
        entity_id = kwargs.get("entity_id")
        if not isinstance(entity_id, int):
            raise UserError("Entity ID niet gevonden. Cache functionaliteit niet beschikbaar.")

        def _raise_scia_error(error_msg: str = f"SCIA CS {analysis_type} resultaten konden niet worden opgehaald.") -> NoReturn:
            raise UserError(error_msg)

        progress_message(f"Laden van gecachte SCIA CS {analysis_type} analyse of starten nieuwe analyse...")
        try:
            results = get_cached_analysis_results(
                params=params,
                analysis_type=AnalysisType.SCIA,
                entity_id=entity_id,
                analysis_function=get_scia_analysis_results,
                template_path=str(template_path),
            )
            if results is None:
                _raise_scia_error()
        except TimeoutError:
            _raise_scia_error(self._get_scia_timeout_message())  # type: ignore[attr-defined]
        except Exception as e:
            traceback.print_exc()
            _raise_scia_error(self._get_scia_exception_message(e))  # type: ignore[attr-defined]

        # Pass bridge_segments to enable zone mapping in CS results
        bridge_segments = params.bridge_segments_array if hasattr(params, "bridge_segments_array") else None
        return create_scia_cs_results_table(results, analysis_type, bridge_segments=bridge_segments)

    @TableView("SCIA CS ULS", duration_guess=600)
    def get_scia_cs_results_view_uls(self, params: BridgeParametrization, **kwargs) -> TableResult:
        """
        Display CS (Cross Section) ULS results from SCIA section on plane objects.

        Shows force and moment values per meter for cross sections at specific locations.

        Note: SCIA analysis can take up to 10 minutes for complex models.

        :param params: Bridge parametrization object
        :type params: BridgeParametrization
        :param kwargs: Additional arguments including entity_id
        :returns: TableResult with CS ULS analysis results
        :rtype: TableResult
        :raises UserError: If analysis fails or bridge segments are missing
        """
        return self._get_scia_cs_results_table(params, "ULS", **kwargs)

    @TableView("SCIA CS SLS freq", duration_guess=600)
    def get_scia_cs_results_view_sls_freq(self, params: BridgeParametrization, **kwargs) -> TableResult:
        """
        Display CS (Cross Section) SLS freq results from SCIA section on plane objects.

        Shows force and moment values per meter for cross sections at specific locations.

        Note: SCIA analysis can take up to 10 minutes for complex models.

        :param params: Bridge parametrization object
        :type params: BridgeParametrization
        :param kwargs: Additional arguments including entity_id
        :returns: TableResult with CS SLS freq analysis results
        :rtype: TableResult
        :raises UserError: If analysis fails or bridge segments are missing
        """
        return self._get_scia_cs_results_table(params, "SLS freq", **kwargs)

    # ============================================================================================================
    # SCIA Force Envelope Analysis
    # ============================================================================================================

    @TableView("SCIA Analyse Resultaten", duration_guess=600)
    def get_scia_results_table(self, params: BridgeParametrization, **kwargs) -> TableResult:
        """
        Display CS force envelopes from SCIA analysis (ULS and SLS freq combined).

        For each unique zone, shows rows with maximum absolute values for each force component
        (v_x, v_y, m_xD+, m_xD-, m_yD+, m_yD-, n_xD, n_yD).

        Combines ULS and SLS freq results and sorts by zone.

        Note: SCIA analysis can take up to 10 minutes for complex models.

        :param params: Bridge parametrization object
        :type params: BridgeParametrization
        :param kwargs: Additional arguments including entity_id
        :returns: TableResult with CS force envelope analysis
        :rtype: TableResult
        :raises UserError: If analysis fails or bridge segments are missing
        """
        if not params.bridge_segments_array:
            raise UserError("Geen brugsegmenten gedefinieerd. Voeg eerst segmenten toe.")

        template_path = self._get_scia_template_path()  # type: ignore[attr-defined]
        entity_id = kwargs.get("entity_id")
        if not isinstance(entity_id, int):
            raise UserError("Entity ID niet gevonden. Cache functionaliteit niet beschikbaar.")

        def _raise_scia_error(error_msg: str = "SCIA analyse resultaten konden niet worden opgehaald.") -> NoReturn:
            raise UserError(error_msg)

        progress_message("Laden van gecachte SCIA CS analyse of starten nieuwe analyse...")
        try:
            results = get_cached_analysis_results(
                params=params,
                analysis_type=AnalysisType.SCIA,
                entity_id=entity_id,
                analysis_function=get_scia_analysis_results,
                template_path=str(template_path),
            )
            if results is None:
                _raise_scia_error()
        except TimeoutError:
            _raise_scia_error(self._get_scia_timeout_message())  # type: ignore[attr-defined]
        except Exception as e:
            traceback.print_exc()
            _raise_scia_error(self._get_scia_exception_message(e))  # type: ignore[attr-defined]

        # Pass bridge_segments to enable zone mapping
        bridge_segments = params.bridge_segments_array if hasattr(params, "bridge_segments_array") else None
        return create_scia_cs_envelope_table(results, bridge_segments=bridge_segments)

    # ============================================================================================================
    # SCIA CS Visualization
    # ============================================================================================================

    @PlotlyView("SCIA CS Visualisatie", duration_guess=600)
    def get_scia_cs_visualization(self, params: BridgeParametrization, **kwargs) -> PlotlyResult:
        """
        Display interactive Plotly visualization of SCIA CS results with 4 subplots.

        Shows force and moment diagrams along cross sections:
        - Subplot 1: Vx and Vy (shear forces)
        - Subplot 2: MxD+ and MxD- (moments in x-direction)
        - Subplot 3: MyD+ and MyD- (moments in y-direction)
        - Subplot 4: NxD and NyD (normal forces)

        Configuration via visualization tab parameters:
        - result_type: "ULS" or "SLS freq"
        - direction: "X-richting" (transverse) or "Y-richting" (longitudinal)
        - max_type: Which force/moment component to maximize for
        - position: Cross section position (X-value for Y-direction, Y-value for X-direction)

        Note: SCIA analysis can take up to 10 minutes for complex models.

        :param params: Bridge parametrization object
        :type params: BridgeParametrization
        :param kwargs: Additional arguments including entity_id
        :returns: PlotlyResult with 4 subplots showing force/moment distributions
        :rtype: PlotlyResult
        :raises UserError: If analysis fails or bridge segments are missing
        """
        if not params.bridge_segments_array:
            raise UserError("Geen brugsegmenten gedefinieerd. Voeg eerst segmenten toe.")

        template_path = self._get_scia_template_path()  # type: ignore[attr-defined]
        entity_id = kwargs.get("entity_id")
        if not isinstance(entity_id, int):
            raise UserError("Entity ID niet gevonden. Cache functionaliteit niet beschikbaar.")

        def _raise_scia_error(error_msg: str = "SCIA CS visualisatie kon niet worden gemaakt.") -> NoReturn:
            raise UserError(error_msg)

        progress_message("Laden van gecachte SCIA CS analyse of starten nieuwe analyse...")
        try:
            results = get_cached_analysis_results(
                params=params,
                analysis_type=AnalysisType.SCIA,
                entity_id=entity_id,
                analysis_function=get_scia_analysis_results,
                template_path=str(template_path),
            )
            if results is None:
                _raise_scia_error()
        except TimeoutError:
            _raise_scia_error(self._get_scia_timeout_message())  # type: ignore[attr-defined]
        except Exception as e:
            traceback.print_exc()
            _raise_scia_error(self._get_scia_exception_message(e))  # type: ignore[attr-defined]

        # Get visualization parameters
        result_type = getattr(params.scia.visualization, "result_type", "ULS")
        direction = getattr(params.scia.visualization, "direction", "X-richting")
        max_type = getattr(params.scia.visualization, "max_type", "m_xD+")
        position_index = int(getattr(params.scia.visualization, "position_index", 0))

        # Pass bridge_segments to enable zone mapping
        bridge_segments = params.bridge_segments_array if hasattr(params, "bridge_segments_array") else None

        return create_scia_cs_plotly_visualization(
            results=results,
            result_type=result_type,
            direction=direction,
            max_type=max_type,
            position_index=position_index,
            bridge_segments=bridge_segments,
        )

    # ============================================================================================================
    # SCIA Downloads
    # ============================================================================================================

    def download_scia_esa_model(self, params: BridgeParametrization, **kwargs) -> DownloadResult:
        """
        Generate and download a complete SCIA ESA model file.

        :param params: Bridge parametrization object
        :type params: BridgeParametrization
        :param kwargs: Additional arguments including entity_id
        :returns: DownloadResult with ESA model file
        :rtype: DownloadResult
        :raises UserError: If bridge segments are missing or generation fails
        """
        if not params.bridge_segments_array:
            self._raise_no_bridge_segments_error()  # type: ignore[attr-defined]

        entity_id = kwargs.get("entity_id")
        bridge_id = getattr(params.info, "bridge_objectnumm", None) or "bridge_model"

        if entity_id is not None and isinstance(entity_id, int):
            return self._download_scia_esa_model_cached(params, entity_id, bridge_id)
        return self._download_scia_esa_model_direct(params, bridge_id)

    def _download_scia_esa_model_cached(self, params: BridgeParametrization, entity_id: int, bridge_id: str) -> DownloadResult:
        """Download SCIA ESA model using cached results."""
        try:
            template_path = self._get_scia_template_path()  # type: ignore[attr-defined]
            results = get_cached_analysis_results(params, AnalysisType.SCIA, entity_id, get_scia_analysis_results, str(template_path))

            if results is not None and results.get("esa_model"):
                esa_content = results["esa_model"]
                filename = f"SCIA_model_{bridge_id}.esa"
                file_obj = File.from_data(esa_content)
                return DownloadResult(file_content=file_obj, file_name=filename)

            if results is not None:
                error_details = results.get("error", "Onbekende fout")
                self._raise_missing_esa_error(error_details)  # type: ignore[attr-defined]

            self._raise_analysis_failed_error()  # type: ignore[attr-defined]

        except Exception as e:
            if isinstance(e, UserError):
                raise
            raise UserError(f"Onverwachte fout tijdens SCIA analyse: {e!s}\n\nProbeer in plaats daarvan de XML-bestanden te downloaden.")

    def _download_scia_esa_model_direct(self, params: BridgeParametrization, bridge_id: str) -> DownloadResult:
        """Download SCIA ESA model by creating and running analysis directly."""
        try:
            template_path = self._get_scia_template_path()  # type: ignore[attr-defined]
            xml_file, def_file, analysis = create_bridge_scia_model(params, template_path)

            analysis.execute(timeout=300)
            esa_file = analysis.get_updated_esa_model()
            if not esa_file:
                self._raise_empty_esa_error()  # type: ignore[attr-defined]

            filename = f"{bridge_id}.esa" if bridge_id.endswith("_model") else f"{bridge_id}_model.esa"
            return DownloadResult(file_content=esa_file, file_name=filename)

        except Exception as e:
            if isinstance(e, UserError):
                raise
            if "SCIA worker" in str(e):
                raise UserError(f"SCIA worker uitvoering gefaald: {e!s}\n\nSCIA worker niet beschikbaar\n\nXML bestanden te downloaden")
            raise UserError(f"Onverwachte fout tijdens SCIA analyse: {e!s}\n\nXML bestanden te downloaden")

    def download_scia_xml_files(self, params: BridgeParametrization, **kwargs) -> DownloadResult:  # noqa: ARG002
        """
        Download SCIA XML and definition files as a ZIP archive.

        :param params: Bridge parametrization object
        :type params: BridgeParametrization
        :param kwargs: Additional arguments
        :returns: DownloadResult with ZIP file containing XML files
        :rtype: DownloadResult
        :raises UserError: If file generation fails
        """
        try:
            template_path = self._get_scia_template_path()  # type: ignore[attr-defined]
            xml_file, def_file, _ = create_bridge_scia_model(params, template_path)

            if not hasattr(xml_file, "getvalue"):
                self._raise_empty_xml_error()  # type: ignore[attr-defined]
            if not hasattr(def_file, "getvalue"):
                self._raise_empty_def_error()  # type: ignore[attr-defined]

            xml_content = xml_file.getvalue()
            if not xml_content:
                self._raise_empty_xml_error()  # type: ignore[attr-defined]

            def_content = def_file.getvalue()
            if not def_content:
                self._raise_empty_def_error()  # type: ignore[attr-defined]

            bridge_id = getattr(params.info, "bridge_objectnumm", None) or "bridge_model"

            zip_file_obj = File()
            with zipfile.ZipFile(zip_file_obj.source, "w", zipfile.ZIP_DEFLATED) as z:
                z.writestr(f"SCIA_model_{bridge_id}.xml", xml_content)
                z.writestr("viktor.xml.def", def_content)

            return DownloadResult(file_content=zip_file_obj, file_name=f"{bridge_id}_Input_Files.zip")

        except Exception as e:
            if isinstance(e, UserError):
                raise
            raise UserError(f"Fout bij genereren SCIA XML bestanden: {e!s}")

    def download_scia_output_xml(self, params: BridgeParametrization, **kwargs) -> DownloadResult:
        """
        Download the SCIA output XML file for investigation.

        :param params: Bridge parametrization object
        :type params: BridgeParametrization
        :param kwargs: Additional arguments including entity_id
        :returns: DownloadResult with output XML file
        :rtype: DownloadResult
        :raises UserError: If bridge segments are missing or no cached results available
        """
        if not params.bridge_segments_array:
            self._raise_no_bridge_segments_error()  # type: ignore[attr-defined]

        entity_id = kwargs.get("entity_id")
        if not isinstance(entity_id, int):
            raise UserError("Entity ID niet gevonden. Cache functionaliteit niet beschikbaar.")

        def _raise_no_cached_results_error() -> None:
            raise UserError("Geen gecachte SCIA resultaten gevonden. Voer eerst een SCIA analyse uit via de resultaten tabel.")

        try:
            template_path = self._get_scia_template_path()  # type: ignore[attr-defined]
            results = get_cached_analysis_results(params, AnalysisType.SCIA, entity_id, get_scia_analysis_results, str(template_path))

            if results is not None and "xml_output" in results and results["xml_output"]:
                xml_content = results["xml_output"]
                filename = f"scia_output_{params.info.bridge_objectnumm}.xml"
                file_obj = File.from_data(xml_content)
                return DownloadResult(file_content=file_obj, file_name=filename)

            _raise_no_cached_results_error()

        except Exception as e:
            raise UserError(f"Onverwachte fout tijdens SCIA analyse: {e!s}\n\nProbeer in plaats daarvan de XML-bestanden te downloaden.")

    def _validate_generated_files(self, xml_file: BytesIO, def_file: BytesIO) -> None:
        """
        Validate that generated files are not empty.

        :param xml_file: XML file BytesIO object
        :param def_file: Definition file BytesIO object
        """
        if not xml_file.getvalue():
            self._raise_empty_xml_error()  # type: ignore[attr-defined]
        if not def_file.getvalue():
            self._raise_empty_def_error()  # type: ignore[attr-defined]
