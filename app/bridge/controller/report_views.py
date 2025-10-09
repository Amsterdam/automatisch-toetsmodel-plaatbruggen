"""
Report generation mixin for BridgeController.

This mixin provides PDF report generation functionality
for bridge design documentation.
"""

from app.bridge.parametrization import BridgeParametrization
from src.report.report_functions import create_export_report
from viktor.errors import UserError
from viktor.views import PDFResult, PDFView


class ReportViewsMixin:
    """
    Mixin providing report generation views.

    Contains methods for:
    - PDF report generation
    """

    @PDFView("Rapport", duration_guess=1)
    def get_output_report(self, params: BridgeParametrization, **kwargs) -> PDFResult:  # noqa: ARG002
        """
        Generate a PDF report for the bridge design.

        :param params: Input parameters for the bridge dimensions
        :type params: BridgeParametrization
        :param kwargs: Additional arguments
        :returns: A PDF file containing the report
        :rtype: PDFResult
        :raises UserError: If report generation fails
        """
        report_pdf = create_export_report(params)
        if not report_pdf:
            raise UserError("Rapport kon niet worden gegenereerd. Controleer de parameters en probeer het opnieuw.")
        return PDFResult(file=report_pdf)
