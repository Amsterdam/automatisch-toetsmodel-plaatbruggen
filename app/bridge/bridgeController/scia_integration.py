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
from viktor.views import TableResult, TableView

from app.bridge.analysis_cache import get_cached_analysis_results
from app.bridge.parametrization import BridgeParametrization
from app.bridge.scia_model_builder import create_bridge_scia_model, get_scia_analysis_results
from app.constants import RESULT_OBJECT_INTEGRATION_STRIPS, RESULT_OBJECT_SECTIONS_ON_PLANE
from src.common.constants.technical import AnalysisType
from src.integrations.scia_integration.results.scia_integration_strips_views import (
    create_integration_strip_envelope_table_view,
    create_integration_strip_table_view,
)
from src.integrations.scia_integration.results.scia_sections_on_plane_views import (
    create_sections_on_plane_envelopes,
    create_sections_on_plane_slsfreq_x_reg,
    create_sections_on_plane_slsfreq_x_sup,
    create_sections_on_plane_slsfreq_y_reg,
    create_sections_on_plane_slsfreq_y_sup,
    create_sections_on_plane_uls_x_reg,
    create_sections_on_plane_uls_x_sup,
    create_sections_on_plane_uls_y_reg,
    create_sections_on_plane_uls_y_sup,
)


# Visibility conditions reused across all view decorators
def _visible_integration_strips(params: BridgeParametrization, **kwargs) -> bool:  # noqa: ARG001
    return params.calc_page.calc_selection.result_object_type == RESULT_OBJECT_INTEGRATION_STRIPS


def _visible_sections_on_plane(params: BridgeParametrization, **kwargs) -> bool:  # noqa: ARG001
    return params.calc_page.calc_selection.result_object_type == RESULT_OBJECT_SECTIONS_ON_PLANE


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
    # Integration Strip Results Table Views
    # ============================================================================================================

    @TableView("Integratiestroken ULS x reg", duration_guess=600, visible=_visible_integration_strips)
    def get_integration_strip_uls_x_reg(self, params: BridgeParametrization, **kwargs) -> TableResult:
        """
        Display ULS results for x-direction regular integration strips.

        :param params: Bridge parametrization object
        :type params: BridgeParametrization
        :param kwargs: Additional arguments including entity_id
        :returns: TableResult with integration strip results
        :rtype: TableResult
        """
        results = self._get_scia_results_with_cache(params, **kwargs)
        return create_integration_strip_table_view(results, "ULS_x_reg")

    @TableView("Integratiestroken ULS y reg", duration_guess=600, visible=_visible_integration_strips)
    def get_integration_strip_uls_y_reg(self, params: BridgeParametrization, **kwargs) -> TableResult:
        """
        Display ULS results for y-direction regular integration strips.

        :param params: Bridge parametrization object
        :type params: BridgeParametrization
        :param kwargs: Additional arguments including entity_id
        :returns: TableResult with integration strip results
        :rtype: TableResult
        """
        results = self._get_scia_results_with_cache(params, **kwargs)
        return create_integration_strip_table_view(results, "ULS_y_reg")

    @TableView("Integratiestroken ULS x sup", duration_guess=600, visible=_visible_integration_strips)
    def get_integration_strip_uls_x_sup(self, params: BridgeParametrization, **kwargs) -> TableResult:
        """
        Display ULS results for x-direction support integration strips.

        :param params: Bridge parametrization object
        :type params: BridgeParametrization
        :param kwargs: Additional arguments including entity_id
        :returns: TableResult with integration strip results
        :rtype: TableResult
        """
        results = self._get_scia_results_with_cache(params, **kwargs)
        return create_integration_strip_table_view(results, "ULS_x_sup")

    @TableView("Integratiestroken ULS y sup", duration_guess=600, visible=_visible_integration_strips)
    def get_integration_strip_uls_y_sup(self, params: BridgeParametrization, **kwargs) -> TableResult:
        """
        Display ULS results for y-direction support integration strips.

        :param params: Bridge parametrization object
        :type params: BridgeParametrization
        :param kwargs: Additional arguments including entity_id
        :returns: TableResult with integration strip results
        :rtype: TableResult
        """
        results = self._get_scia_results_with_cache(params, **kwargs)
        return create_integration_strip_table_view(results, "ULS_y_sup")

    @TableView("Integratiestroken SLSfreq x reg", duration_guess=600, visible=_visible_integration_strips)
    def get_integration_strip_slsfreq_x_reg(self, params: BridgeParametrization, **kwargs) -> TableResult:
        """
        Display SLS frequent results for x-direction regular integration strips.

        :param params: Bridge parametrization object
        :type params: BridgeParametrization
        :param kwargs: Additional arguments including entity_id
        :returns: TableResult with integration strip results
        :rtype: TableResult
        """
        results = self._get_scia_results_with_cache(params, **kwargs)
        return create_integration_strip_table_view(results, "SLSfreq_x_reg")

    @TableView("Integratiestroken SLSfreq y reg", duration_guess=600, visible=_visible_integration_strips)
    def get_integration_strip_slsfreq_y_reg(self, params: BridgeParametrization, **kwargs) -> TableResult:
        """
        Display SLS frequent results for y-direction regular integration strips.

        :param params: Bridge parametrization object
        :type params: BridgeParametrization
        :param kwargs: Additional arguments including entity_id
        :returns: TableResult with integration strip results
        :rtype: TableResult
        """
        results = self._get_scia_results_with_cache(params, **kwargs)
        return create_integration_strip_table_view(results, "SLSfreq_y_reg")

    @TableView("Integratiestroken SLSfreq x sup", duration_guess=600, visible=_visible_integration_strips)
    def get_integration_strip_slsfreq_x_sup(self, params: BridgeParametrization, **kwargs) -> TableResult:
        """
        Display SLS frequent results for x-direction support integration strips.

        :param params: Bridge parametrization object
        :type params: BridgeParametrization
        :param kwargs: Additional arguments including entity_id
        :returns: TableResult with integration strip results
        :rtype: TableResult
        """
        results = self._get_scia_results_with_cache(params, **kwargs)
        return create_integration_strip_table_view(results, "SLSfreq_x_sup")

    @TableView("Integratiestroken SLSfreq y sup", duration_guess=600, visible=_visible_integration_strips)
    def get_integration_strip_slsfreq_y_sup(self, params: BridgeParametrization, **kwargs) -> TableResult:
        """
        Display SLS frequent results for y-direction support integration strips.

        :param params: Bridge parametrization object
        :type params: BridgeParametrization
        :param kwargs: Additional arguments including entity_id
        :returns: TableResult with integration strip results
        :rtype: TableResult
        """
        results = self._get_scia_results_with_cache(params, **kwargs)
        return create_integration_strip_table_view(results, "SLSfreq_y_sup")

    @TableView("Integratiestroken Enveloppen", duration_guess=600, visible=_visible_integration_strips)
    def get_integration_strip_envelopes(self, params: BridgeParametrization, **kwargs) -> TableResult:
        """
        Display aggregated min/max force envelopes from integration strips.

        Shows minimum and maximum values for all force/moment components per zone,
        direction, and limit state.

        :param params: Bridge parametrization object
        :type params: BridgeParametrization
        :param kwargs: Additional arguments including entity_id
        :returns: TableResult with envelope results
        :rtype: TableResult
        """
        results = self._get_scia_results_with_cache(params, **kwargs)
        return create_integration_strip_envelope_table_view(results)

    # ============================================================================================================
    # Sections on Plane Results Table Views
    # ============================================================================================================

    @TableView("Secties op vlak ULS veld x", duration_guess=600, visible=_visible_sections_on_plane)
    def get_sections_on_plane_uls_x_reg(self, params: BridgeParametrization, **kwargs) -> TableResult:
        """ULS veld x-richting: basis + elementaire ontwerp grootheden."""
        results = self._get_scia_results_with_cache(params, **kwargs)
        return create_sections_on_plane_uls_x_reg(results)

    @TableView("Secties op vlak ULS veld y", duration_guess=600, visible=_visible_sections_on_plane)
    def get_sections_on_plane_uls_y_reg(self, params: BridgeParametrization, **kwargs) -> TableResult:
        """ULS veld y-richting: basis + elementaire ontwerp grootheden."""
        results = self._get_scia_results_with_cache(params, **kwargs)
        return create_sections_on_plane_uls_y_reg(results)

    @TableView("Secties op vlak ULS steunpunt x", duration_guess=600, visible=_visible_sections_on_plane)
    def get_sections_on_plane_uls_x_sup(self, params: BridgeParametrization, **kwargs) -> TableResult:
        """ULS steunpunt x-richting: basis + elementaire ontwerp grootheden."""
        results = self._get_scia_results_with_cache(params, **kwargs)
        return create_sections_on_plane_uls_x_sup(results)

    @TableView("Secties op vlak ULS steunpunt y", duration_guess=600, visible=_visible_sections_on_plane)
    def get_sections_on_plane_uls_y_sup(self, params: BridgeParametrization, **kwargs) -> TableResult:
        """ULS steunpunt y-richting: basis + elementaire ontwerp grootheden."""
        results = self._get_scia_results_with_cache(params, **kwargs)
        return create_sections_on_plane_uls_y_sup(results)

    @TableView("Secties op vlak SLS freq veld x", duration_guess=600, visible=_visible_sections_on_plane)
    def get_sections_on_plane_slsfreq_x_reg(self, params: BridgeParametrization, **kwargs) -> TableResult:
        """SLS frequent veld x-richting: basis + elementaire ontwerp grootheden."""
        results = self._get_scia_results_with_cache(params, **kwargs)
        return create_sections_on_plane_slsfreq_x_reg(results)

    @TableView("Secties op vlak SLS freq veld y", duration_guess=600, visible=_visible_sections_on_plane)
    def get_sections_on_plane_slsfreq_y_reg(self, params: BridgeParametrization, **kwargs) -> TableResult:
        """SLS frequent veld y-richting: basis + elementaire ontwerp grootheden."""
        results = self._get_scia_results_with_cache(params, **kwargs)
        return create_sections_on_plane_slsfreq_y_reg(results)

    @TableView("Secties op vlak SLS freq steunpunt x", duration_guess=600, visible=_visible_sections_on_plane)
    def get_sections_on_plane_slsfreq_x_sup(self, params: BridgeParametrization, **kwargs) -> TableResult:
        """SLS frequent steunpunt x-richting: basis + elementaire ontwerp grootheden."""
        results = self._get_scia_results_with_cache(params, **kwargs)
        return create_sections_on_plane_slsfreq_x_sup(results)

    @TableView("Secties op vlak SLS freq steunpunt y", duration_guess=600, visible=_visible_sections_on_plane)
    def get_sections_on_plane_slsfreq_y_sup(self, params: BridgeParametrization, **kwargs) -> TableResult:
        """SLS frequent steunpunt y-richting: basis + elementaire ontwerp grootheden."""
        results = self._get_scia_results_with_cache(params, **kwargs)
        return create_sections_on_plane_slsfreq_y_sup(results)

    @TableView("Secties Enveloppen", duration_guess=600, visible=_visible_sections_on_plane)
    def get_sections_on_plane_envelopes(self, params: BridgeParametrization, **kwargs) -> TableResult:
        """Maatgevende waarden (abs. max per grootheid) over alle 4 secties-op-vlak tabellen."""
        results = self._get_scia_results_with_cache(params, **kwargs)
        return create_sections_on_plane_envelopes(results)

    def _get_scia_results_with_cache(self, params: BridgeParametrization, **kwargs) -> dict:
        """
        Helper method to get SCIA results with caching.

        :param params: Bridge parametrization object
        :type params: BridgeParametrization
        :param kwargs: Additional arguments including entity_id
        :returns: SCIA results dictionary
        :rtype: dict
        :raises UserError: If analysis fails
        """
        if not params.bridge_segments_array:
            raise UserError("Geen brugsegmenten gedefinieerd. Voeg eerst segmenten toe.")

        template_path = self._get_scia_template_path(params)  # type: ignore[attr-defined]
        entity_id = kwargs.get("entity_id")
        if not isinstance(entity_id, int):
            raise UserError("Entity ID niet gevonden. Cache functionaliteit niet beschikbaar.")

        def _raise_scia_error(error_msg: str = "SCIA resultaten konden niet worden opgehaald.") -> NoReturn:
            raise UserError(error_msg)

        progress_message("Laden van gecachte SCIA analyse of starten nieuwe analyse...")
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
        else:
            return results

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
        """Download SCIA ESA model using cached results, or recalculate if ESA not in cache."""
        try:
            template_path = self._get_scia_template_path(params)  # type: ignore[attr-defined]
            progress_message("Controleren op gecachte SCIA resultaten...")
            results = get_cached_analysis_results(params, AnalysisType.SCIA, entity_id, get_scia_analysis_results, str(template_path))

            if results is not None and results.get("esa_model"):
                # ESA model found in cache - return it directly
                progress_message("✓ ESA model gevonden in cache")
                esa_content = results["esa_model"]
                filename = f"SCIA_model_{bridge_id}.esa"
                file_obj = File.from_data(esa_content)
                return DownloadResult(file_content=file_obj, file_name=filename)

            # ESA model not in cache - check if results exist but ESA was excluded (too large)
            if results is not None:
                summary = results.get("summary", {})
                progress_message(f"⚠ Cache gevonden maar ESA model ontbreekt. Summary: {summary}")
                if summary.get("esa_model_too_large"):
                    # ESA was too large to cache - inform user and recalculate
                    progress_message(
                        f"ESA model te groot voor cache ({summary.get('esa_model_size_mb', 'N/A')} MB). Model wordt opnieuw gegenereerd..."
                    )
                elif not summary.get("esa_model_cached", True):
                    # ESA not cached for other reason - recalculate
                    progress_message("ESA model niet in cache. Model wordt opnieuw gegenereerd...")
                else:
                    # Cache exists but ESA missing - unexpected state
                    progress_message("ESA model niet beschikbaar in cache. Model wordt opnieuw gegenereerd...")

                # Recalculate ESA model directly (don't re-run full analysis)
                return self._download_scia_esa_model_direct(params, bridge_id)

            # No cached results at all - fallback to direct download
            progress_message("Geen cache gevonden - nieuwe berekening wordt gestart...")
            self._raise_analysis_failed_error()  # type: ignore[attr-defined]

        except Exception as e:
            if isinstance(e, UserError):
                raise
            raise UserError(f"Onverwachte fout tijdens SCIA analyse: {e!s}\n\nProbeer in plaats daarvan de XML-bestanden te downloaden.")

    def _download_scia_esa_model_direct(self, params: BridgeParametrization, bridge_id: str) -> DownloadResult:
        """Download SCIA ESA model by creating and running analysis directly."""
        try:
            full_template_path = self._get_scia_full_template_path(params)  # type: ignore[attr-defined]
            xml_file, def_file, analysis = create_bridge_scia_model(params, full_template_path)

            analysis.execute(timeout=10800)
            esa_file = analysis.get_updated_esa_model()
            if not esa_file:
                self._raise_empty_esa_error()  # type: ignore[attr-defined]

            filename = f"{bridge_id}.esa" if bridge_id.endswith("_model") else f"{bridge_id}_model.esa"
            return DownloadResult(file_content=esa_file, file_name=filename)

        except TimeoutError:
            raise UserError(self._get_scia_timeout_message())  # type: ignore[attr-defined]
        except Exception as e:
            if isinstance(e, UserError):
                raise
            raise UserError(self._get_scia_exception_message(e))  # type: ignore[attr-defined]

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
            governing_template_path = self._get_scia_template_path(params)  # type: ignore[attr-defined]
            full_template_path = self._get_scia_full_template_path(params)  # type: ignore[attr-defined]
            xml_file, def_file, _ = create_bridge_scia_model(params, governing_template_path)

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

            # Load both ESA templates to include in ZIP
            governing_esa_content = governing_template_path.read_bytes()
            full_esa_content = full_template_path.read_bytes()

            zip_file_obj = File()
            with zipfile.ZipFile(zip_file_obj.source, "w", zipfile.ZIP_DEFLATED) as z:
                z.writestr(f"SCIA_model_{bridge_id}.xml", xml_content)
                z.writestr("viktor.xml.def", def_content)
                # Add governing template (exports only governing/envelope results — used in Stage 1)
                z.writestr(governing_template_path.name, governing_esa_content)
                # Add full template (exports complete results for all sections — used in Stage 2)
                z.writestr(full_template_path.name, full_esa_content)

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

        def _raise_no_cached_results_error() -> NoReturn:
            raise UserError("Geen gecachte SCIA resultaten gevonden. Voer eerst een SCIA analyse uit via de resultaten tabel.")

        try:
            template_path = self._get_scia_template_path(params)  # type: ignore[attr-defined]
            results = get_cached_analysis_results(params, AnalysisType.SCIA, entity_id, get_scia_analysis_results, str(template_path))

            if results is not None and "xml_output" in results and results["xml_output"]:
                xml_content = results["xml_output"]
                filename = f"scia_output_{params.info.bridge_objectnumm}.xml"
                file_obj = File.from_data(xml_content)
                return DownloadResult(file_content=file_obj, file_name=filename)

            _raise_no_cached_results_error()

        except TimeoutError:
            raise UserError(self._get_scia_timeout_message())  # type: ignore[attr-defined]
        except Exception as e:
            if isinstance(e, UserError):
                raise
            raise UserError(self._get_scia_exception_message(e))  # type: ignore[attr-defined]

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
