"""
SCIA Engineer utility functions for creating loads, load cases, load combinations, and analysis workflows.

FRAMEWORK USAGE:
================
1. Create Load Group: create_load_group_by_type()
2. Create Load Case: create_load_case_complete()
3. Create Load Combination: create_load_combination_by_type()
4. Apply Loads: create_patch_surface_load()
5. Generate XML: generate_xml_from_model(), generate_bridge_xml_files()
6. Setup Analysis: create_scia_analysis_from_template(), setup_bridge_analysis()

See VIKTOR documentation for detailed parameters:
- LoadGroup: https://docs.viktor.ai/sdk/api/external/scia/#_LoadGroup
- LoadCase: https://docs.viktor.ai/sdk/api/external/scia/#_LoadCase
- LoadCombination: https://docs.viktor.ai/sdk/api/external/scia/#_LoadCombination
- Model methods: https://docs.viktor.ai/sdk/api/external/scia/#Model
"""

import io
from io import BytesIO
from pathlib import Path
from typing import Any, TypeAlias

# Global VIKTOR imports with error handling for CI/testing environments
try:
    from viktor.core import File
    from viktor.external import scia

    VIKTOR_AVAILABLE = True
except ImportError:
    # Mock objects for environments without VIKTOR SDK
    File = None  # type: ignore[misc,assignment]
    scia = None  # type: ignore[misc,assignment]
    VIKTOR_AVAILABLE = False

# Import from other SCIA integration modules
from .scia_model import create_complete_bridge_model

# Type aliases for SCIA objects
SciaModel: TypeAlias = Any
SciaNode: TypeAlias = Any
SciaPlane: TypeAlias = Any
SciaLoadGroup: TypeAlias = Any
SciaLoadCase: TypeAlias = Any
SciaLoadCombination: TypeAlias = Any
SciaFreeSurfaceLoad: TypeAlias = Any


def _check_scia_availability() -> None:
    """Check if VIKTOR SCIA module is available."""
    if not VIKTOR_AVAILABLE or scia is None:
        raise ImportError("VIKTOR SCIA module not available. This function requires VIKTOR SDK.")


def create_load_group_by_type(
    model: SciaModel,
    load_option: str,
    group_name: str,
    relation: str = "STANDARD",
) -> SciaLoadGroup:
    """
    Create SCIA load group with standardized settings.

    :param model: SCIA model instance
    :param load_option: "PERMANENT", "VARIABLE", "ACCIDENTAL", "SEISMIC"
    :param group_name: Name for the load group
    :param relation: "STANDARD", "EXCLUSIVE", "TOGETHER"

    See: https://docs.viktor.ai/sdk/api/external/scia/#Model.create_load_group
    """
    _check_scia_availability()

    load_option_map = {
        "PERMANENT": scia.LoadGroup.LoadOption.PERMANENT,
        "VARIABLE": scia.LoadGroup.LoadOption.VARIABLE,
        "ACCIDENTAL": scia.LoadGroup.LoadOption.ACCIDENTAL,
        "SEISMIC": scia.LoadGroup.LoadOption.SEISMIC,
    }

    relation_map = {
        "STANDARD": scia.LoadGroup.RelationOption.STANDARD,
        "EXCLUSIVE": scia.LoadGroup.RelationOption.EXCLUSIVE,
        "TOGETHER": scia.LoadGroup.RelationOption.TOGETHER,
    }

    return model.create_load_group(group_name, load_option_map[load_option], relation_map[relation], scia.LoadGroup.LoadTypeOption.CAT_A)


# =============================================================================
# XML GENERATION AND ANALYSIS SETUP
# =============================================================================


def generate_xml_from_model(scia_model: Any) -> tuple[BytesIO, BytesIO]:  # noqa: ANN401
    """
    Generate XML and definition files from SCIA model.

    :param scia_model: SCIA model object
    :returns: (xml_file, def_file) for SCIA analysis
    :rtype: tuple[BytesIO, BytesIO]
    :raises ImportError: When VIKTOR SCIA module is not available
    """
    if not VIKTOR_AVAILABLE or scia is None:
        raise ImportError("VIKTOR SCIA module not available. This function requires VIKTOR SDK.")

    return scia_model.generate_xml_input()


def create_scia_analysis_from_template(xml_file: io.BytesIO, def_file: io.BytesIO, template_path: Path) -> Any:  # noqa: ANN401
    """
    Create SCIA analysis using template file.

    :param xml_file: Generated XML input file
    :param def_file: Generated definition file
    :param template_path: Path to ESA template
    :returns: SCIA analysis object
    :rtype: Any
    :raises ImportError: When VIKTOR SCIA module is not available
    :raises FileNotFoundError: When template file is not found
    """
    if not VIKTOR_AVAILABLE or scia is None or File is None:
        raise ImportError("VIKTOR SCIA module not available. This function requires VIKTOR SDK.")

    if not template_path.exists():
        raise FileNotFoundError(f"SCIA template file not found: {template_path}")

    esa_template = File.from_path(template_path)
    return scia.SciaAnalysis(xml_file, def_file, esa_template)


def generate_bridge_xml_files(params: Any) -> tuple[BytesIO, BytesIO]:  # noqa: ANN401
    """
    Generate XML and definition files for SCIA bridge analysis.

    :param params: Bridge parameters
    :returns: (xml_file, def_file) for SCIA analysis
    :rtype: tuple[BytesIO, BytesIO]
    """
    scia_model = create_complete_bridge_model(params)
    return generate_xml_from_model(scia_model)


def setup_bridge_analysis(params: Any, template_path: Path) -> tuple[Any, Any, Any]:  # noqa: ANN401
    """
    Complete bridge analysis setup: model creation → XML generation → analysis setup.

    :param params: Bridge parameters
    :param template_path: Path to ESA template file
    :returns: (xml_file, def_file, scia_analysis)
    :rtype: tuple[Any, Any, Any]
    """
    # Generate XML files from complete bridge model
    xml_file, def_file = generate_bridge_xml_files(params)

    # Setup analysis with template
    scia_analysis = create_scia_analysis_from_template(xml_file, def_file, template_path)

    return xml_file, def_file, scia_analysis


# Backwards compatibility aliases
create_bridge_scia_analysis = setup_bridge_analysis
create_simple_bridge_analysis = generate_bridge_xml_files
