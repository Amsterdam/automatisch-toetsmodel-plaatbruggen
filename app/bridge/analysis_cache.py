"""
General analysis caching module.

This module provides caching functionality for analysis results (SCIA, IDEA, etc.) to avoid
recalculating when input parameters haven't changed.
"""

import base64
import hashlib
import json
import pickle
from enum import Enum
from io import BytesIO
from pathlib import Path
from typing import Any, Callable, Optional

from src.integrations.idea_interface import create_bridge_idea_model
from viktor.core import File, Storage
from viktor.external import idea_rcs


def _extract_file_content(file_obj: Any) -> bytes:
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
        self.storage = Storage()

    def _extract_params(self, params: Any, analysis_type: AnalysisType, template_path: str | None = None) -> dict[str, Any]:  # noqa: ANN401
        """Extract parameters for caching based on analysis type."""
        base_params = {
            "bridge_segments": self._extract_bridge_segments(params),
            "materials": self._extract_materials(params),
        }

        if analysis_type == AnalysisType.SCIA:
            base_params.update(
                {
                    "load_zones": self._extract_load_zones(params),
                    "load_combinations": self._extract_load_combinations(params),
                    "template_path": template_path,
                }
            )
        elif analysis_type == AnalysisType.IDEA:
            base_params.update(
                {
                    "reinforcement_zones": self._extract_reinforcement_zones(params),
                    "reinforcement_materials": self._extract_reinforcement_materials(params),
                    "reinforcement_geometry": self._extract_reinforcement_geometry(params),
                }
            )
        else:
            raise ValueError(f"Unsupported analysis type: {analysis_type}")

        return base_params

    def _extract_bridge_segments(self, params: Any) -> list[dict[str, Any]]:  # noqa: ANN401
        """Extract bridge segment parameters."""
        segments = []
        if hasattr(params, "bridge_segments_array") and params.bridge_segments_array:
            for segment in params.bridge_segments_array:
                segments.append(
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
                )
        return segments

    def _extract_load_zones(self, params: Any) -> list[dict[str, Any]]:  # noqa: ANN401
        """Extract load zone parameters."""
        zones = []
        if hasattr(params, "load_zones_data_array") and params.load_zones_data_array:
            for zone in params.load_zones_data_array:
                zone_data = {
                    "zone_type": getattr(zone, "zone_type", ""),
                    "pavement_thickness": getattr(zone, "pavement_thickness", 0.0),
                    "pavement_material": getattr(zone, "pavement_material", ""),
                }
                # Add dynamic width fields
                for i in range(1, 16):
                    width_attr = f"d{i}_width"
                    if hasattr(zone, width_attr):
                        zone_data[width_attr] = getattr(zone, width_attr, 0.0)
                zones.append(zone_data)
        return zones

    def _extract_load_combinations(self, params: Any) -> dict[str, Any]:  # noqa: ANN401
        """Extract load combination parameters."""
        belastingcombinaties = getattr(params.input, "belastingcombinaties", None)
        return {
            "cc_class": getattr(belastingcombinaties, "cc_class", "CC2") if belastingcombinaties else "CC2",
            "design_code": getattr(belastingcombinaties, "design_code", "NEN 8700 verbouw") if belastingcombinaties else "NEN 8700 verbouw",
            "shortest_span": getattr(belastingcombinaties, "shortest_span", 20.0) if belastingcombinaties else 20.0,
        }

    def _extract_materials(self, params: Any) -> dict[str, Any]:  # noqa: ANN401
        """Extract material parameters."""
        return {"concrete_strength_class": getattr(params.info, "concrete_strength_class", "")}

    def _extract_reinforcement_zones(self, params: Any) -> list[dict[str, Any]]:  # noqa: ANN401
        """Extract reinforcement zone parameters."""
        zones = []
        geometrie_wapening = getattr(params.input, "geometrie_wapening", None)
        zones_array = getattr(geometrie_wapening, "zones", None) if geometrie_wapening else None

        if zones_array:
            for zone in zones_array:
                zones.append(
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
                )
        return zones

    def _extract_reinforcement_materials(self, params: Any) -> dict[str, Any]:  # noqa: ANN401
        """Extract reinforcement material parameters."""
        return {
            "rebar_grade": getattr(params.info, "rebar_grade", ""),
            "rebar_type": getattr(params.info, "rebar_type", ""),
        }

    def _extract_reinforcement_geometry(self, params: Any) -> dict[str, Any]:  # noqa: ANN401
        """Extract reinforcement geometry parameters."""
        geometrie_wapening = getattr(params.input, "geometrie_wapening", None)
        return {
            "staalsoort": getattr(geometrie_wapening, "staalsoort", "") if geometrie_wapening else "",
            "dekking_boven": getattr(geometrie_wapening, "dekking_boven", 55.0) if geometrie_wapening else 55.0,
            "dekking_onder": getattr(geometrie_wapening, "dekking_onder", 55.0) if geometrie_wapening else 55.0,
            "langswapening_buiten": getattr(geometrie_wapening, "langswapening_buiten", True) if geometrie_wapening else True,
        }

    def _generate_input_hash(self, params: Any, analysis_type: AnalysisType, template_path: str | None = None) -> str:  # noqa: ANN401
        """Generate a hash of the input parameters."""
        try:
            input_data = self._extract_params(params, analysis_type, template_path)
            json_str = json.dumps(input_data, sort_keys=True, default=str)
            return hashlib.sha256(json_str.encode()).hexdigest()
        except Exception:
            fallback_data = {"analysis_type": analysis_type.value, "template_path": template_path or "none"}
            return hashlib.sha256(json.dumps(fallback_data, sort_keys=True, default=str).encode()).hexdigest()

    def get_cached_analysis(
        self,
        params: Any,
        analysis_type: AnalysisType,
        entity_id: int,
        template_path: str | None = None,
    ) -> Optional[dict[str, Any]]:
        """Get cached analysis results if available and valid."""
        try:
            # Get stored input hash
            input_hash_key = f"analysis_input_hash_{analysis_type.value}_{entity_id}"
            stored_input_hash_file = self.storage.get(input_hash_key, scope="entity")

            if stored_input_hash_file is None:
                return None

            stored_input_hash = stored_input_hash_file.getvalue()
            stored_input_hash = stored_input_hash.decode("utf-8") if isinstance(stored_input_hash, bytes) else str(stored_input_hash)

            # Compare hashes
            current_input_hash = self._generate_input_hash(params, analysis_type, template_path)
            if stored_input_hash != current_input_hash:
                return None

            # Get stored results
            results_key = f"analysis_results_{analysis_type.value}_{entity_id}"
            stored_results_file = self.storage.get(results_key, scope="entity")

            if stored_results_file is None:
                return None

            # Deserialize results
            encoded_results = stored_results_file.getvalue()
            serialized_results = base64.b64decode(encoded_results)
            return pickle.loads(serialized_results)

        except Exception:
            return None

    def cache_analysis_results(
        self,
        params: Any,  # noqa: ANN401
        analysis_type: AnalysisType,
        entity_id: int,
        results: dict[str, Any],
        template_path: str | None = None,
    ) -> None:
        """Cache analysis results for the given parameters and entity."""
        try:
            # Generate and store input hash
            input_hash = self._generate_input_hash(params, analysis_type, template_path)
            input_hash_key = f"analysis_input_hash_{analysis_type.value}_{entity_id}"
            self.storage.set(input_hash_key, File.from_data(input_hash), scope="entity")

            # Serialize and store results
            results_key = f"analysis_results_{analysis_type.value}_{entity_id}"
            serialized_results = pickle.dumps(results)
            encoded_results = base64.b64encode(serialized_results).decode("ascii")
            self.storage.set(results_key, File.from_data(encoded_results), scope="entity")

        except Exception:
            pass  # If caching fails, continue without caching

    def clear_cache(self, entity_id: int, analysis_type: AnalysisType | None = None) -> None:
        """Clear cached data for the given entity and analysis type."""
        try:
            types_to_clear = [analysis_type] if analysis_type else list(AnalysisType)
            for at in types_to_clear:
                self.storage.delete(f"analysis_input_hash_{at.value}_{entity_id}", scope="entity")
                self.storage.delete(f"analysis_results_{at.value}_{entity_id}", scope="entity")
        except Exception:
            pass

    def get_cache_info(self, entity_id: int, analysis_type: AnalysisType | None = None) -> dict[str, Any]:
        """Get cache information for the given entity and analysis type."""
        if analysis_type is None:
            cache_info = {"entity_id": entity_id, "analysis_types": {}}
            for at in AnalysisType:
                cache_info["analysis_types"][at.value] = self._get_specific_cache_info(entity_id, at)
            return cache_info
        return self._get_specific_cache_info(entity_id, analysis_type)

    def _get_specific_cache_info(self, entity_id: int, analysis_type: AnalysisType) -> dict[str, Any]:
        """Get cache info for a specific analysis type."""
        input_hash_key = f"analysis_input_hash_{analysis_type.value}_{entity_id}"
        results_key = f"analysis_results_{analysis_type.value}_{entity_id}"

        try:
            has_input_hash = self.storage.get(input_hash_key, scope="entity") is not None
            has_results = self.storage.get(results_key, scope="entity") is not None
        except Exception:
            has_input_hash = has_results = False

        return {
            "analysis_type": analysis_type.value,
            "has_cached_input_hash": has_input_hash,
            "has_cached_results": has_results,
            "cache_valid": has_input_hash and has_results,
        }


# Global cache instance (lazy initialization)
_analysis_cache: Optional[AnalysisCache] = None


def _get_analysis_cache() -> AnalysisCache:
    """Get the global analysis cache instance, creating it if necessary."""
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
) -> Optional[dict[str, Any]]:
    """Get cached analysis results or run analysis if not cached."""
    cache = _get_analysis_cache()

    # Try to get cached results first
    cached_results = cache.get_cached_analysis(params, analysis_type, entity_id, template_path)
    if cached_results is not None:
        return cached_results

    # If not cached, run analysis and cache results
    try:
        if analysis_type == AnalysisType.SCIA and template_path:
            results = analysis_function(params, Path(template_path))
        else:
            results = analysis_function(params)

        if results is not None:
            cache.cache_analysis_results(params, analysis_type, entity_id, results, template_path)
        return results

    except Exception:
        return None
