"""
SCIA Engineer integration for bridge analysis.

This module provides the MAIN INTERFACE used by controllers.
Contains ONLY the function actually called by app/bridge/controller.py.

For specialized functionality, import directly from scia_integration modules.
"""

from pathlib import Path
from typing import Any

# Import only the complete workflow function - NO implementation details
from src.integrations.scia_integration.scia_utils import setup_bridge_analysis


def create_bridge_scia_model(params: Any, template_path: Path) -> tuple[Any, Any, Any]:  # noqa: ANN401
    """
    Main interface function for creating complete SCIA bridge models.

    Pure delegation to the analysis workflow - no implementation details here.

    :param params: Bridge parameters
    :param template_path: Path to ESA template file
    :returns: (xml_file, def_file, scia_analysis)
    :rtype: tuple[Any, Any, Any]
    """
    # Delegate to the complete analysis workflow
    return setup_bridge_analysis(params, template_path)
