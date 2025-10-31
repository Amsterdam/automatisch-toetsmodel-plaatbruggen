"""
General analysis caching module.

This module provides caching functionality for analysis results (SCIA, IDEA, etc.) to avoid
recalculating when input parameters haven't changed.
"""

import base64
import hashlib
import json
import pickle
from collections.abc import Callable
from io import BytesIO
from typing import Any

from viktor.core import File, Storage, progress_message
from viktor.errors import UserError
from viktor.external import idea_rcs

from app.bridge.scia_model_builder import get_scia_analysis_results
from app.constants import SCIA_TEMPLATE_PATH
from src.common.constants.technical import AnalysisType
from src.integrations.idea_integration.idea_interface import create_bridge_idea_model
from src.integrations.idea_integration.scia_to_idea_functions import (
    process_scia_integration_strip_results_for_idea,
    process_scia_node_results_for_idea,
)


def _extract_file_content(file_obj: Any) -> bytes:  # noqa: ANN401
    """Extract content from file object."""
    if hasattr(file_obj, "getvalue"):
        content = file_obj.getvalue()
    elif hasattr(file_obj, "read"):
        content = file_obj.read()
        if hasattr(file_obj, "seek"):
            file_obj.seek(0)
    else:
        content = b""

    return content.encode("utf-8") if isinstance(content, str) else content


def get_idea_analysis_results(params: Any, entity_id: int) -> dict[str, Any]:  # noqa: ANN401
    """Run IDEA analysis and extract results."""
    # First get SCIA results needed for IDEA
    progress_message("Ophalen SCIA resultaten voor IDEA analyse...")
    scia_results_dict = get_scia_results_for_idea(params, entity_id)

    # Create IDEA model with the SCIA results
    progress_message("Genereren IDEA model...")
    model = create_bridge_idea_model(params, entity_id, scia_results_dict)
    idea_xml_input_bytes = model.generate_xml_input()

    # Run IDEA analysis
    progress_message("Uitvoeren IDEA RCS analyse...")
    analysis = idea_rcs.IdeaRcsAnalysis(idea_xml_input_bytes, return_rcs_file=True)
    analysis.execute(600)

    # Get the IDEA RCS model and output XML
    progress_message("Verwerken IDEA analyse resultaten...")
    idea_rcs_model = analysis.get_idea_rcs_file(as_file=False)
    idea_output_xml_bytes = analysis.get_output_file(as_file=False)

    # Extract output content for parsing
    output_content = _extract_file_content(idea_output_xml_bytes)

    results: dict[str, Any] = {}
    try:
        progress_message("Parsen IDEA output...")
        parser = idea_rcs.RcsOutputFileParser(BytesIO(output_content))
        section_results = []
        for section in parser.section_results():
            # Extract crack_width data - it has nested 'short' and 'long' keys
            crack_width_data = section.crack_width()[0] if section.crack_width() else None
            # Extract the overall Result and CheckValue from the crack_width data
            # IDEA returns crack_width with nested structure: {'short': {...}, 'long': {...}}
            # We need to check both short and long term and use the worst case (highest CheckValue)
            crack_width_result = {"Result": "N/A", "CheckValue": "N/A"}
            if crack_width_data:
                short_term = crack_width_data.get("short")
                long_term = crack_width_data.get("long")

                # Collect valid check values
                check_values = []
                crack_width_results_list = []

                if short_term and isinstance(short_term, dict):
                    if "CheckValue" in short_term and short_term["CheckValue"] is not None:
                        check_values.append(short_term["CheckValue"])
                    if "Result" in short_term:
                        crack_width_results_list.append(short_term["Result"])

                if long_term and isinstance(long_term, dict):
                    if "CheckValue" in long_term and long_term["CheckValue"] is not None:
                        check_values.append(long_term["CheckValue"])
                    if "Result" in long_term:
                        crack_width_results_list.append(long_term["Result"])

                # Use the maximum CheckValue (worst case)
                if check_values:
                    crack_width_result["CheckValue"] = max(check_values)

                # Use the worst result (prioritize "FAILED" over "PASSED")
                if crack_width_results_list:
                    if any(r == "FAILED" for r in crack_width_results_list if r):
                        crack_width_result["Result"] = "FAILED"
                    elif any(r == "PASSED" for r in crack_width_results_list if r):
                        crack_width_result["Result"] = "PASSED"
                    else:
                        crack_width_result["Result"] = crack_width_results_list[0] if crack_width_results_list[0] else "N/A"

            section_data = {
                "id": section.id_,
                "capacity": section.capacity()[0] if section.capacity() else {"Result": "N/A"},
                "shear": section.shear()[0] if section.shear() else {"Result": "N/A"},
                "torsion": section.torsion()[0] if section.torsion() else {"Result": "N/A"},
                "interaction": section.interaction()[0] if section.interaction() else {"Result": "N/A"},
                "crack_width": crack_width_result,
                "detailing": section.detailing()[0] if section.detailing() else {"Result": "N/A"},
                "stress_limitation": section.stress_limitation()[0] if section.stress_limitation() else {"Result": "N/A"},
            }
            section_results.append(section_data)

        results.update(
            {
                "section_results": section_results,
                "analysis_status": "completed",
                "model": model,
                "idea_xml_input_bytes": idea_xml_input_bytes,
                "idea_rcs_model": idea_rcs_model,
                "idea_xml_output_bytes": idea_output_xml_bytes,
                "output_content": output_content,
            }
        )
    except Exception as e:
        results.update(
            {
                "analysis_status": "failed",
                "error": str(e),
                "model": model,
                "idea_xml_input_bytes": idea_xml_input_bytes,
                "idea_rcs_model": idea_rcs_model,
                "idea_xml_output_bytes": idea_output_xml_bytes,
                "output_content": output_content,
            }
        )
    return results


def get_scia_results_for_idea(params: Any, entity_id: int) -> dict[str, Any]:  # noqa: ANN401
    """
    Get SCIA results that are needed for IDEA analysis.

    This function processes SCIA analysis results and returns both node results (2D forces)
    and integration strip results (1D forces) in a single merged dictionary.

    :param params: Bridge parametrization
    :type params: Any
    :param entity_id: Entity ID for caching
    :type entity_id: int
    :returns: Dictionary containing processed SCIA node and integration strip results for IDEA
    :rtype: dict[str, Any]
    :raises UserError: If bridge segments are missing or analysis fails
    """
    # Get entity ID for caching
    if not isinstance(entity_id, int):
        raise UserError("Entity ID niet gevonden. Cache functionaliteit niet beschikbaar.")

    try:
        # Get the ESA template path
        template_path = SCIA_TEMPLATE_PATH

        # Use cached SCIA analysis results instead of calling directly
        progress_message("Ophalen SCIA resultaten voor IDEA verwerking...")
        results = get_cached_analysis_results(params, AnalysisType.SCIA, entity_id, get_scia_analysis_results, str(template_path))

    except Exception as e:
        raise UserError(f"Onverwachte fout tijdens ophalen SCIA resultaten voor IDEA analyse: {e!s}")

    # Process SCIA results using the dedicated functions for both node and integration strip results
    if results is None:
        raise UserError("Geen SCIA resultaten beschikbaar voor IDEA analyse")

    # Get both node results (2D forces) and integration strip results (1D forces)
    progress_message("Verwerken SCIA resultaten voor IDEA...")
    node_results = process_scia_node_results_for_idea(results)
    integration_strip_results = process_scia_integration_strip_results_for_idea(results)

    # Merge both result dictionaries
    merged_results = {}
    merged_results.update(node_results)
    merged_results.update(integration_strip_results)

    return merged_results


def get_idea_model_only(params: Any, entity_id: int) -> dict[str, Any]:  # noqa: ANN401
    """Create IDEA model only (without running analysis)."""
    progress_message("Genereren IDEA model...")
    model = create_bridge_idea_model(params, entity_id)
    return {
        "model": model,
        "idea_xml_input_bytes": model.generate_xml_input(),
        "analysis_status": "model_created",
    }


class AnalysisCache:
    """General cache for analysis results using VIKTOR Storage."""

    def __init__(self) -> None:
        """Initialize the analysis cache with VIKTOR Storage."""
        self.storage = Storage()

    def _extract_params(self, params: Any, analysis_type: AnalysisType, template_path: str | None = None) -> dict[str, Any]:  # noqa: ANN401
        """
        Extract relevant parameters for caching based on analysis type.

        Uses the centralized parameter system from cache_parameters module.

        :param params: Bridge parameters object
        :type params: Any
        :param analysis_type: Type of analysis (SCIA or IDEA)
        :type analysis_type: AnalysisType
        :param template_path: Optional template path for SCIA analyses
        :type template_path: str | None
        :returns: Dictionary of extracted parameters for caching
        :rtype: dict[str, Any]
        """
        from app.bridge.cache_parameters import extract_parameters_for_analysis

        extracted_params: dict[str, Any] = {
            "analysis_type": analysis_type.value,
            "template_path": template_path,
        }

        # Use the centralized extraction system
        extracted_params.update(extract_parameters_for_analysis(params, analysis_type))

        return extracted_params

    def _generate_input_hash(self, params: Any, analysis_type: AnalysisType, template_path: str | None = None) -> str:  # noqa: ANN401
        """Generate a hash of the input parameters for caching."""
        extracted_params = self._extract_params(params, analysis_type, template_path)
        params_json = json.dumps(extracted_params, sort_keys=True, default=str)
        return hashlib.md5(params_json.encode()).hexdigest()

    def get_cached_analysis(
        self,
        params: Any,  # noqa: ANN401
        analysis_type: AnalysisType,
        entity_id: int,
        template_path: str | None = None,
    ) -> dict[str, Any] | None:
        """Get cached analysis results if available."""
        input_hash = self._generate_input_hash(params, analysis_type, template_path)
        cache_key = f"analysis_cache_{entity_id}_{analysis_type.value}_{input_hash}"

        try:
            cached_file = self.storage.get(cache_key, scope="entity")
            if cached_file:
                # Read the base64-encoded data
                if hasattr(cached_file, "getvalue"):
                    encoded_data = cached_file.getvalue()
                elif hasattr(cached_file, "read"):
                    cached_file.seek(0)
                    encoded_data = cached_file.read()
                else:
                    encoded_data = cached_file

                # Ensure we have string data for base64 decoding
                if isinstance(encoded_data, bytes):
                    encoded_data = encoded_data.decode("utf-8")

                # Decode from base64 and unpickle
                cached_data = base64.b64decode(encoded_data)
                return pickle.loads(cached_data)
        except Exception:
            pass

        return None

    def cache_analysis_results(
        self,
        params: Any,  # noqa: ANN401
        analysis_type: AnalysisType,
        entity_id: int,
        results: dict[str, Any],
        template_path: str | None = None,
    ) -> None:
        """Cache analysis results."""
        input_hash = self._generate_input_hash(params, analysis_type, template_path)
        cache_key = f"analysis_cache_{entity_id}_{analysis_type.value}_{input_hash}"

        try:
            # Pickle the results and encode as base64 to avoid binary data issues
            cached_data = pickle.dumps(results)
            encoded_data = base64.b64encode(cached_data).decode("utf-8")
            cached_file = File.from_data(encoded_data)
            self.storage.set(cache_key, data=cached_file, scope="entity")
        except Exception:
            pass

    def clear_cache(self, entity_id: int, analysis_type: AnalysisType | None = None) -> None:
        """Clear cache for a specific entity and analysis type."""
        pattern = f"analysis_cache_{entity_id}_{analysis_type.value if analysis_type else ''}_*"

        try:
            keys_to_delete = [key for key in self.storage.list(scope="entity") if key.startswith(pattern)]
            for key in keys_to_delete:
                self.storage.delete(key, scope="entity")
        except Exception:
            pass

    def get_cache_info(self, entity_id: int, analysis_type: AnalysisType | None = None) -> dict[str, Any]:
        """Get cache information for debugging."""
        cache_info: dict[str, Any] = {
            "entity_id": entity_id,
            "analysis_types": {},
            "total_cache_entries": 0,
        }

        try:
            all_keys = self.storage.list(scope="entity")
            entity_keys = [key for key in all_keys if key.startswith(f"analysis_cache_{entity_id}_")]
            cache_info["total_cache_entries"] = len(entity_keys)

            if analysis_type:
                cache_info["analysis_types"][analysis_type.value] = self._get_specific_cache_info(entity_id, analysis_type)
            else:
                for at in AnalysisType:
                    cache_info["analysis_types"][at.value] = self._get_specific_cache_info(entity_id, at)
        except Exception:
            pass

        return cache_info

    def _get_specific_cache_info(self, entity_id: int, analysis_type: AnalysisType) -> dict[str, Any]:
        """Get cache information for a specific analysis type."""
        pattern = f"analysis_cache_{entity_id}_{analysis_type.value}_*"
        try:
            keys = [key for key in self.storage.list(scope="entity") if key.startswith(pattern)]
            return {
                "cache_entries": len(keys),
                "cache_keys": keys,
            }
        except Exception:
            return {
                "cache_entries": 0,
                "cache_keys": [],
            }


# Global cache instance (lazy initialization)
_analysis_cache: AnalysisCache | None = None


def _get_analysis_cache() -> AnalysisCache:
    """Get the global analysis cache instance."""
    global _analysis_cache  # noqa: PLW0603
    if _analysis_cache is None:
        _analysis_cache = AnalysisCache()
    return _analysis_cache


def get_cached_analysis_results(
    params: Any,  # noqa: ANN401
    analysis_type: AnalysisType,
    entity_id: int,
    analysis_function: Callable[..., dict[str, Any]],
    template_path: str | None = None,
) -> dict[str, Any] | None:
    """Get cached analysis results or run analysis if not cached."""
    cache = _get_analysis_cache()

    # Try to get cached results
    progress_message("Controleren op gecachte resultaten...")
    cached_results = cache.get_cached_analysis(params, analysis_type, entity_id, template_path)
    if cached_results is not None:
        progress_message("Gecachte resultaten gevonden - laden...")
        return cached_results

    # Run analysis if not cached
    progress_message("Geen gecachte resultaten gevonden - starten nieuwe analyse...")
    # Call the analysis function based on analysis type
    if analysis_type == AnalysisType.SCIA:
        results = analysis_function(params, template_path)
    elif analysis_type == AnalysisType.IDEA:
        results = analysis_function(params, entity_id)
    else:
        # Fallback: try calling with just params
        raise UserError("Unsupported analysis type for caching.")

    # Cache the results
    if results is not None:
        progress_message("Opslaan resultaten in cache...")
        cache.cache_analysis_results(params, analysis_type, entity_id, results, template_path)

    return results
