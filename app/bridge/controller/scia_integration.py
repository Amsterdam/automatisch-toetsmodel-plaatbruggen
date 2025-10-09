"""
SCIA Engineer integration mixin for BridgeController.

This mixin provides all SCIA-related functionality including:
- Multiple table views for different analysis types (ULS, SLS kar, SLS freq)
- 1D and 2D result views
- ESA model and XML file downloads
- Force envelope analysis
"""

import traceback
import zipfile
from io import BytesIO
from typing import Any, NoReturn

from app.bridge.analysis_cache import get_cached_analysis_results
from app.bridge.parametrization import BridgeParametrization
from app.bridge.scia_model_builder import create_bridge_scia_model, get_scia_analysis_results
from src.common.constants.technical import AnalysisType
from src.integrations.scia_integration.scia_force_envelopes import extract_force_envelopes, get_force_envelope_summary
from src.integrations.scia_integration.scia_result_views import create_scia_integration_strip_results_table, create_scia_node_results_table
from viktor.core import File, progress_message
from viktor.errors import UserError
from viktor.result import DownloadResult
from viktor.views import TableResult, TableView


class SciaIntegrationMixin:
    """
    Mixin providing SCIA Engineer integration.

    Contains methods for:
    - SCIA analysis table views (ULS, SLS kar, SLS freq) in 2D and 1D
    - Force envelope analysis
    - ESA model and XML file downloads
    - SCIA-specific error handling
    """

    # ============================================================================================================
    # SCIA 2D Node Results Table Views
    # ============================================================================================================

    @TableView("SCIA SLS kar 2D", duration_guess=600)
    def get_scia_results_view_sls_kar(self, params: BridgeParametrization, **kwargs) -> TableResult:
        """
        Display SLS kar results from SCIA analysis in a comprehensive table format.

        Shows maximum and minimum values for each force component (N, Vy, Vz, Mxd+, Mxd-, Myd+, Myd-)
        per bridge section along with complete force state, location and load combination.

        Note: SCIA analysis can take up to 10 minutes for complex models.

        :param params: Bridge parametrization object
        :type params: BridgeParametrization
        :param kwargs: Additional arguments including entity_id
        :returns: TableResult with SLS kar analysis results
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

        progress_message("Laden van gecachte SCIA SLS kar analyse of starten nieuwe analyse...")
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

        return create_scia_node_results_table(results, "SLS kar")

    @TableView("SCIA SLS freq 2D", duration_guess=600)
    def get_scia_results_view_sls_freq(self, params: BridgeParametrization, **kwargs) -> TableResult:
        """
        Display SLS freq results from SCIA analysis in a comprehensive table format.

        Shows force and moment values for each coordinate location from SLS freq analysis.

        Note: SCIA analysis can take up to 10 minutes for complex models.

        :param params: Bridge parametrization object
        :type params: BridgeParametrization
        :param kwargs: Additional arguments including entity_id
        :returns: TableResult with SLS freq analysis results
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

        progress_message("Laden van gecachte SCIA SLS freq analyse of starten nieuwe analyse...")
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

        return create_scia_node_results_table(results, "SLS freq")

    @TableView("SCIA ULS 2D", duration_guess=600)
    def get_scia_results_view_uls(self, params: BridgeParametrization, **kwargs) -> TableResult:
        """
        Display ULS results from SCIA analysis in a comprehensive table format.

        Shows force and moment values for each coordinate location from ULS analysis.

        Note: SCIA analysis can take up to 10 minutes for complex models.

        :param params: Bridge parametrization object
        :type params: BridgeParametrization
        :param kwargs: Additional arguments including entity_id
        :returns: TableResult with ULS analysis results
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

        progress_message("Laden van gecachte SCIA ULS analyse of starten nieuwe analyse...")
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

        return create_scia_node_results_table(results, "ULS")

    # ============================================================================================================
    # SCIA 1D Strip Results Table Views
    # ============================================================================================================

    @TableView("SCIA SLS kar 1D", duration_guess=600)
    def get_scia_1d_results_view_sls_kar(self, params: BridgeParametrization, **kwargs) -> TableResult:
        """
        Display SLS kar 1D results from SCIA analysis in a comprehensive table format.

        Shows 1D beam force and moment values including normal forces, shear forces,
        and bending/torsional moments.

        Note: SCIA analysis can take up to 10 minutes for complex models.

        :param params: Bridge parametrization object
        :type params: BridgeParametrization
        :param kwargs: Additional arguments including entity_id
        :returns: TableResult with SLS kar 1D analysis results
        :rtype: TableResult
        :raises UserError: If analysis fails or bridge segments are missing
        """
        if not params.bridge_segments_array:
            raise UserError("Geen brugsegmenten gedefinieerd. Voeg eerst segmenten toe.")

        template_path = self._get_scia_template_path()  # type: ignore[attr-defined]
        entity_id = kwargs.get("entity_id")
        if not isinstance(entity_id, int):
            raise UserError("Entity ID niet gevonden. Cache functionaliteit niet beschikbaar.")

        def _raise_scia_error(error_msg: str = "SCIA 1D analyse resultaten konden niet worden opgehaald.") -> NoReturn:
            raise UserError(error_msg)

        progress_message("Laden van gecachte SCIA SLS kar 1D analyse of starten nieuwe analyse...")
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
            _raise_scia_error(self._get_scia_1d_timeout_message())  # type: ignore[attr-defined]
        except Exception as e:
            traceback.print_exc()
            _raise_scia_error(self._get_scia_1d_exception_message(e))  # type: ignore[attr-defined]

        return create_scia_integration_strip_results_table(results, "SLS kar")

    @TableView("SCIA SLS freq 1D", duration_guess=600)
    def get_scia_1d_results_view_sls_freq(self, params: BridgeParametrization, **kwargs) -> TableResult:
        """
        Display SLS freq 1D results from SCIA analysis in a comprehensive table format.

        Shows 1D beam force and moment values including normal forces, shear forces,
        and bending/torsional moments.

        Note: SCIA analysis can take up to 10 minutes for complex models.

        :param params: Bridge parametrization object
        :type params: BridgeParametrization
        :param kwargs: Additional arguments including entity_id
        :returns: TableResult with SLS freq 1D analysis results
        :rtype: TableResult
        :raises UserError: If analysis fails or bridge segments are missing
        """
        if not params.bridge_segments_array:
            raise UserError("Geen brugsegmenten gedefinieerd. Voeg eerst segmenten toe.")

        template_path = self._get_scia_template_path()  # type: ignore[attr-defined]
        entity_id = kwargs.get("entity_id")
        if not isinstance(entity_id, int):
            raise UserError("Entity ID niet gevonden. Cache functionaliteit niet beschikbaar.")

        def _raise_scia_error(error_msg: str = "SCIA 1D analyse resultaten konden niet worden opgehaald.") -> NoReturn:
            raise UserError(error_msg)

        progress_message("Laden van gecachte SCIA SLS freq 1D analyse of starten nieuwe analyse...")
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
            _raise_scia_error(self._get_scia_1d_timeout_message())  # type: ignore[attr-defined]
        except Exception as e:
            traceback.print_exc()
            _raise_scia_error(self._get_scia_1d_exception_message(e))  # type: ignore[attr-defined]

        return create_scia_integration_strip_results_table(results, "SLS freq")

    @TableView("SCIA ULS 1D", duration_guess=600)
    def get_scia_1d_results_view_uls(self, params: BridgeParametrization, **kwargs) -> TableResult:
        """
        Display ULS 1D results from SCIA analysis in a comprehensive table format.

        Shows 1D beam force and moment values including normal forces, shear forces,
        and bending/torsional moments.

        Note: SCIA analysis can take up to 10 minutes for complex models.

        :param params: Bridge parametrization object
        :type params: BridgeParametrization
        :param kwargs: Additional arguments including entity_id
        :returns: TableResult with ULS 1D analysis results
        :rtype: TableResult
        :raises UserError: If analysis fails or bridge segments are missing
        """
        if not params.bridge_segments_array:
            raise UserError("Geen brugsegmenten gedefinieerd. Voeg eerst segmenten toe.")

        template_path = self._get_scia_template_path()  # type: ignore[attr-defined]
        entity_id = kwargs.get("entity_id")
        if not isinstance(entity_id, int):
            raise UserError("Entity ID niet gevonden. Cache functionaliteit niet beschikbaar.")

        def _raise_scia_error(error_msg: str = "SCIA 1D analyse resultaten konden niet worden opgehaald.") -> NoReturn:
            raise UserError(error_msg)

        progress_message("Laden van gecachte SCIA ULS 1D analyse of starten nieuwe analyse...")
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
            _raise_scia_error(self._get_scia_1d_timeout_message())  # type: ignore[attr-defined]
        except Exception as e:
            traceback.print_exc()
            _raise_scia_error(self._get_scia_1d_exception_message(e))  # type: ignore[attr-defined]

        return create_scia_integration_strip_results_table(results, "ULS")

    # ============================================================================================================
    # SCIA Force Envelope Analysis
    # ============================================================================================================

    @TableView("SCIA Analyse Resultaten", duration_guess=600)
    def get_scia_results_table(self, params: BridgeParametrization, **kwargs) -> TableResult:  # noqa: C901
        """
        Display force envelopes from SCIA analysis in a comprehensive table format.

        Shows maximum and minimum values for each force component per bridge section
        along with complete force state, location and load combination.

        Note: SCIA analysis can take up to 10 minutes for complex models.

        :param params: Bridge parametrization object
        :type params: BridgeParametrization
        :param kwargs: Additional arguments including entity_id
        :returns: TableResult with force envelope analysis
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

        self._print_scia_results_summary(results)  # type: ignore[arg-type, attr-defined]

        try:
            envelopes = extract_force_envelopes(results)  # type: ignore[arg-type]
        except Exception as e:
            return TableResult(
                [["Fout", f"Kon krachtenveloppen niet extraheren: {str(e)[:100]}...", "", "", "", "", ""]],
                column_headers=["Sectie", "Component", "Type", "Waarde", "Locatie", "Combinatie", "Andere Krachten"],
            )

        if not envelopes:
            return TableResult(
                [["Geen gegevens", "Geen krachtenveloppen beschikbaar - mogelijk geen interne krachten data", "", "", "", "", ""]],
                column_headers=["Sectie", "Component", "Type", "Waarde", "Locatie", "Combinatie", "Andere Krachten"],
            )

        units_mapping = results.get("units", {}).get("internal_forces", {})  # type: ignore[arg-type]
        table_data = []

        for section, section_envelopes in envelopes.items():
            for component, envelope in section_envelopes.items():
                max_data = envelope["max"]
                min_data = envelope["min"]

                component_unit = units_mapping.get(component, "")
                unit_suffix = f" {component_unit}" if component_unit else ""

                if max_data["value"] != float("-inf"):
                    max_forces_str = self._format_complete_force_state(max_data["forces"], units_mapping)  # type: ignore[attr-defined]
                    table_data.append(
                        [
                            section,
                            component,
                            "Maximum",
                            f"{max_data['value']:.1f}{unit_suffix}",
                            max_data["location"],
                            max_data["combination"],
                            max_forces_str,
                        ]
                    )

                if min_data["value"] != float("inf"):
                    min_forces_str = self._format_complete_force_state(min_data["forces"], units_mapping)  # type: ignore[attr-defined]
                    table_data.append(
                        [
                            section,
                            component,
                            "Minimum",
                            f"{min_data['value']:.1f}{unit_suffix}",
                            min_data["location"],
                            min_data["combination"],
                            min_forces_str,
                        ]
                    )

        table_data.sort(key=lambda x: (x[0], x[1], x[2]))
        return TableResult(table_data, column_headers=["Sectie", "Component", "Type", "Waarde", "Locatie", "Combinatie", "Andere Krachten"])

    def get_force_envelopes(self, params: BridgeParametrization, **kwargs) -> dict[str, Any]:
        """
        Extract force envelopes from SCIA analysis results.

        Returns a dictionary containing max/min values for each force component
        along with complete force state and location context.

        :param params: Bridge parametrization
        :type params: BridgeParametrization
        :param kwargs: Additional arguments including entity_id
        :returns: Force envelopes dictionary with summary information
        :rtype: dict[str, Any]
        :raises UserError: If bridge segments are missing or entity ID is invalid
        """
        if not params.bridge_segments_array:
            raise UserError("Geen brugsegmenten gedefinieerd. Voeg eerst segmenten toe.")

        entity_id = kwargs.get("entity_id")
        if not isinstance(entity_id, int):
            raise UserError("Entity ID is vereist voor analyse resultaten")

        template_path = self._get_scia_template_path()  # type: ignore[attr-defined]
        results = get_cached_analysis_results(
            params=params,
            analysis_type=AnalysisType.SCIA,
            entity_id=entity_id,
            analysis_function=get_scia_analysis_results,
            template_path=str(template_path),
        )

        if not results:
            raise UserError("Geen SCIA analyse resultaten beschikbaar. Voer eerst een analyse uit.")

        envelopes = extract_force_envelopes(results)
        summary = get_force_envelope_summary(envelopes)

        return {
            "envelopes": envelopes,
            "summary": summary,
            "analysis_info": {
                "total_components": len(envelopes),
                "has_data": any(env["max"]["value"] != float("-inf") and env["min"]["value"] != float("inf") for env in envelopes.values()),
            },
        }

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
