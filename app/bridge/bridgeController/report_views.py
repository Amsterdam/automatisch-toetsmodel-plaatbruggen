"""
Report generation component for BridgeController.

This component provides PDF report generation functionality
for bridge design documentation.
"""

from app.bridge.analysis_cache import get_idea_analysis_results
from app.bridge.parametrization import BridgeParametrization
from src.integrations.idea_integration.idea_results_processor import IdeaResultsProcessor
from src.report.report_functions import create_export_report
from viktor.errors import UserError
from viktor.core import progress_message
from viktor.views import PDFResult, PDFView

from ..utils import validate_reinforcement_zone_selections
from ..analysis_cache import AnalysisType, get_cached_analysis_results

class ReportViews:
    """
    Component providing report generation views.

    Contains methods for:
    - PDF report generation
    """

    @PDFView("Rapport", duration_guess=1)
    def get_output_report(self, params: BridgeParametrization, **kwargs) -> PDFResult:
        """
        Generates a PDF report for the bridge design.

        Args:
            params (BridgeParametrization): Input parameters for the bridge dimensions.
            **kwargs: Additional arguments.

        Returns:
            File: A PDF file containing the report.

        """
        # Validate reinforcement zone selections before processing
        validate_reinforcement_zone_selections(params)

        # Validate bridge segments
        if not hasattr(params, "bridge_segments_array") or not params.bridge_segments_array:
            raise UserError("Geen brugsegmenten gedefinieerd. Voeg eerst segmenten toe.")

        # Get entity ID
        entity_id = kwargs.get("entity_id")
        if entity_id is None:
            raise UserError("Entity ID niet gevonden. Cache functionaliteit niet beschikbaar.")

        # Get cached results
        progress_message("Laden van gecachte IDEA RCS analyse of starten nieuwe analyse...")
        cached_results = get_cached_analysis_results(params, AnalysisType.IDEA, entity_id, get_idea_analysis_results)
        if cached_results is None:
            raise UserError("IDEA analyse gefaald of geen gecachte resultaten beschikbaar.")

        # Process results using core logic
        result = IdeaResultsProcessor.process_idea_results(cached_results)
        report_pdf = create_export_report(params, result)  # Call the report generation function
        if not report_pdf:
            raise UserError("Rapport kon niet worden gegenereerd. Controleer de parameters en probeer het opnieuw.")
        return PDFResult(file=report_pdf)
