"""
General analysis caching module.

This module provides caching functionality for analysis results (SCIA, IDEA, etc.) to avoid
recalculating when input parameters haven't changed.
"""

import hashlib
import json
import pickle
from collections.abc import Callable
from enum import Enum
from io import BytesIO
from typing import Any

from src.integrations.idea_interface import create_bridge_idea_model
from viktor.core import Storage
from viktor.external import idea_rcs


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


def get_idea_analysis_results(params: Any) -> dict[str, Any]:  # noqa: ANN401
    """Run IDEA analysis and extract results."""
    model = create_bridge_idea_model(params)
    xml_input = model.generate_xml_input()

    analysis = idea_rcs.IdeaRcsAnalysis(xml_input, return_rcs_file=True)
    analysis.execute(120)

    idea_output_xml_bytes = analysis.get_output_file(as_file=True)
    output_content = _extract_file_content(idea_output_xml_bytes)

    results: dict[str, Any] = {}
    try:
        parser = idea_rcs.RcsOutputFileParser(BytesIO(output_content))
        section_results = []
        for section in parser.section_results():
            section_data = {
                "id": section.id_,
                "capacity": section.capacity()[0] if section.capacity() else {"Result": "N/A"},
                "shear": section.shear()[0] if section.shear() else {"Result": "N/A"},
                "torsion": section.torsion()[0] if section.torsion() else {"Result": "N/A"},
                "interaction": section.interaction()[0] if section.interaction() else {"Result": "N/A"},
                "crack_width": section.crack_width()[0] if section.crack_width() else {"Result": "N/A"},
                "detailing": section.detailing()[0] if section.detailing() else {"Result": "N/A"},
                "stress_limitation": section.stress_limitation()[0] if section.stress_limitation() else {"Result": "N/A"},
            }
            section_results.append(section_data)

        results.update(
            {
                "section_results": section_results,
                "analysis_status": "completed",
                "model": model,
                "xml_input": xml_input,
                "output_content": output_content,
            }
        )
    except Exception as e:
        results.update(
            {
                "analysis_status": "failed",
                "error": str(e),
                "model": model,
                "xml_input": xml_input,
                "output_content": output_content,
            }
        )

    return results


def get_idea_model_only(params: Any) -> dict[str, Any]:  # noqa: ANN401
    """Create IDEA model only (without running analysis)."""
    model = create_bridge_idea_model(params)
    return {
        "model": model,
        "xml_input": model.generate_xml_input(),
        "analysis_status": "model_created",
    }


class AnalysisType(Enum):
    """Enumeration of supported analysis types."""

    SCIA = "scia"
    IDEA = "idea"


class AnalysisCache:
    """General cache for analysis results using VIKTOR Storage."""

    def __init__(self) -> None:
        """Initialize the analysis cache with VIKTOR Storage."""
        self.storage = Storage()

    def _extract_params(self, params: Any, analysis_type: AnalysisType, template_path: str | None = None) -> dict[str, Any]:  # noqa: ANN401
        """Extract relevant parameters for caching based on analysis type."""
        extracted_params: dict[str, Any] = {
            "analysis_type": analysis_type.value,
            "template_path": template_path,
        }

        if analysis_type in {AnalysisType.SCIA, AnalysisType.IDEA}:
            extracted_params.update(
                {
                    "bridge_segments": self._extract_bridge_segments(params),
                    "load_zones": self._extract_load_zones(params),
                    "load_combinations": self._extract_load_combinations(params),
                    "materials": self._extract_materials(params),
                    "reinforcement_zones": self._extract_reinforcement_zones(params),
                    "reinforcement_materials": self._extract_reinforcement_materials(params),
                    "reinforcement_geometry": self._extract_reinforcement_geometry(params),
                }
            )

        return extracted_params

    def _extract_bridge_segments(self, params: Any) -> list[dict[str, Any]]:  # noqa: ANN401
        """Extract bridge segments data from params."""
        segments: list[dict[str, Any]] = []
        if hasattr(params, "bridge_segments_array") and params.bridge_segments_array:
            segments.extend(
                {
                    "bz1": getattr(segment, "bz1", 0.0),
                    "bz2": getattr(segment, "bz2", 0.0),
                    "bz3": getattr(segment, "bz3", 0.0),
                    "dz": getattr(segment, "dz", 0.0),
                    "dz_2": getattr(segment, "dz_2", 0.0),
                    "l": getattr(segment, "l", 0.0),
                    "is_first_segment": getattr(segment, "is_first_segment", False),
                    "is_support": getattr(segment, "is_support", False),
                }
                for segment in params.bridge_segments_array
            )
        return segments

    def _extract_load_zones(self, params: Any) -> list[dict[str, Any]]:  # noqa: ANN401
        """Extract load zones data from params."""
        zones: list[dict[str, Any]] = []
        zones_array = getattr(params, "load_zones_data_array", None)
        if zones_array:
            zones.extend(
                {
                    "zone_number": getattr(zone, "zone_number", []),
                    "hoofdwapening_langs_boven_diameter": getattr(zone, "hoofdwapening_langs_boven_diameter", 0.0),
                    "hoofdwapening_langs_boven_hart_op_hart": getattr(zone, "hoofdwapening_langs_boven_hart_op_hart", 0.0),
                    "hoofdwapening_langs_onder_diameter": getattr(zone, "hoofdwapening_langs_onder_diameter", 0.0),
                    "hoofdwapening_langs_onder_hart_op_hart": getattr(zone, "hoofdwapening_langs_onder_hart_op_hart", 0.0),
                    "hoofdwapening_dwars_boven_diameter": getattr(zone, "hoofdwapening_dwars_boven_diameter", 0.0),
                    "hoofdwapening_dwars_boven_hart_op_hart": getattr(zone, "hoofdwapening_dwars_boven_hart_op_hart", 0.0),
                    "hoofdwapening_dwars_onder_diameter": getattr(zone, "hoofdwapening_dwars_onder_diameter", 0.0),
                    "hoofdwapening_dwars_onder_hart_op_hart": getattr(zone, "hoofdwapening_dwars_onder_hart_op_hart", 0.0),
                    "heeft_bijlegwapening": getattr(zone, "heeft_bijlegwapening", False),
                    "bijlegwapening_langs_boven_diameter": getattr(zone, "bijlegwapening_langs_boven_diameter", 0.0),
                    "bijlegwapening_langs_onder_diameter": getattr(zone, "bijlegwapening_langs_onder_diameter", 0.0),
                    "bijlegwapening_dwars_boven_diameter": getattr(zone, "bijlegwapening_dwars_boven_diameter", 0.0),
                    "bijlegwapening_dwars_onder_diameter": getattr(zone, "bijlegwapening_dwars_onder_diameter", 0.0),
                }
                for zone in zones_array
            )
        return zones

    def _extract_load_combinations(self, params: Any) -> dict[str, Any]:  # noqa: ANN401
        """Extract load combinations data from params."""
        return {
            "load_combinations": getattr(params, "load_combinations", {}),
        }

    def _extract_materials(self, params: Any) -> dict[str, Any]:  # noqa: ANN401
        """Extract materials data from params."""
        return {
            "materials": getattr(params, "materials", {}),
        }

    def _extract_reinforcement_zones(self, params: Any) -> list[dict[str, Any]]:  # noqa: ANN401
        """Extract reinforcement zones data from params."""
        zones = []
        reinforcement_zones = getattr(params, "reinforcement_zones", [])
        if reinforcement_zones:
            for zone in reinforcement_zones:
                zone_data = {
                    "zone_name": getattr(zone, "zone_name", ""),
                    "zone_type": getattr(zone, "zone_type", ""),
                    "zone_length": getattr(zone, "zone_length", 0.0),
                    "zone_width": getattr(zone, "zone_width", 0.0),
                    "zone_height": getattr(zone, "zone_height", 0.0),
                    "zone_position": getattr(zone, "zone_position", {}),
                }
                zones.append(zone_data)
        return zones

    def _extract_reinforcement_materials(self, params: Any) -> dict[str, Any]:  # noqa: ANN401
        """Extract reinforcement materials data from params."""
        return {
            "reinforcement_materials": getattr(params, "reinforcement_materials", {}),
        }

    def _extract_reinforcement_geometry(self, params: Any) -> dict[str, Any]:  # noqa: ANN401
        """Extract reinforcement geometry data from params."""
        return {
            "reinforcement_geometry": getattr(params, "reinforcement_geometry", {}),
        }

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
            cached_data = self.storage.get(cache_key)
            if cached_data:
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
            cached_data = pickle.dumps(results)
            self.storage.set(cache_key, cached_data)
        except Exception:
            pass

    def clear_cache(self, entity_id: int, analysis_type: AnalysisType | None = None) -> None:
        """Clear cache for a specific entity and analysis type."""
        pattern = f"analysis_cache_{entity_id}_{analysis_type.value if analysis_type else ''}_*"

        try:
            keys_to_delete = [key for key in self.storage.list() if key.startswith(pattern)]
            for key in keys_to_delete:
                self.storage.delete(key)
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
            all_keys = self.storage.list()
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
            keys = [key for key in self.storage.list() if key.startswith(pattern)]
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
    cached_results = cache.get_cached_analysis(params, analysis_type, entity_id, template_path)
    if cached_results is not None:
        return cached_results

    # Run analysis if not cached
    results = analysis_function(params, template_path) if template_path else analysis_function(params)

    # Cache the results
    if results is not None:
        cache.cache_analysis_results(params, analysis_type, entity_id, results, template_path)

    return results
