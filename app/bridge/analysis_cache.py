"""
General analysis caching module.

This module provides caching functionality for analysis results (SCIA, IDEA, etc.) to avoid
recalculating when input parameters haven't changed.
"""

import base64
import contextlib
import hashlib
import json
import pickle
from collections.abc import Callable
from datetime import UTC, datetime
from io import BytesIO
from typing import Any, ClassVar

import viktor.api_v1 as api
from viktor.core import File, Storage, progress_message
from viktor.errors import InternalError, UserError
from viktor.external import idea_rcs

from app.bridge.scia_model_builder import get_scia_analysis_results
from app.constants import SCIA_TEMPLATE_PATH
from src.common.constants.technical import AnalysisType
from src.integrations.idea_integration.idea_interface import create_bridge_idea_model

STORAGE_WARNING_MARKER_KEY = "storage_warning_state"


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


def get_idea_analysis_results(params: Any, entity_id: int, analysis_context: dict[str, Any] | None = None) -> dict[str, Any]:  # noqa: ANN401, C901, PLR0912
    """
    Run IDEA analysis and extract results.

    :param params: Bridge parameters
    :param entity_id: Entity ID
    :param analysis_context: Optional context dict with bridge_position, total_bridges, bridge_name, batch_percentage
    :returns: Dictionary with analysis results
    """
    # Build progress message prefix from context
    if analysis_context:
        prefix = f"Bridge {analysis_context['bridge_position']}/{analysis_context['total_bridges']}: {analysis_context['bridge_name']}\n"
        percentage = analysis_context.get("batch_percentage")
    else:
        prefix = ""
        percentage = None

    # First get SCIA results needed for IDEA
    progress_message(f"{prefix}Ophalen SCIA resultaten voor IDEA analyse...", percentage=percentage)
    scia_results_dict = get_scia_results_for_idea(params, entity_id, analysis_context)

    # Create IDEA model with the SCIA results
    progress_message(f"{prefix}Genereren IDEA model...", percentage=percentage)
    try:
        model = create_bridge_idea_model(params, entity_id, scia_results_dict)
    except UserError:
        # Re-raise UserError as-is (already has helpful message)
        raise
    except Exception as e:
        # Wrap other exceptions with helpful context
        raise UserError(
            f"IDEA model generatie gefaald: {e!s}. "
            "Mogelijk zijn de brugparameters gewijzigd na een eerdere berekening. "
            "Probeer de cache te wissen en opnieuw te berekenen."
        ) from e

    # Generate XML input - this may raise ExecutionError from IDEA SDK
    try:
        _xml_file = model.generate_xml_input()
        # Extract raw bytes so the result dict is picklable (Viktor File objects are not)
        idea_xml_input_bytes = _extract_file_content(_xml_file)
    except Exception as e:
        # IDEA SDK may raise ExecutionError with "Idea model cannot be generated"
        error_msg = str(e)
        if "cannot be generated" in error_msg.lower() or "cannot be generated" in error_msg:
            raise UserError(
                "IDEA model kan niet worden gegenereerd. "
                "Mogelijke oorzaken: geen dwarsdoorsneden gemaakt, geen belastingen toegepast, of ongeldige geometrie. "
                "Controleer of de wapeningszones overeenkomen met de brugsegmenten en of SCIA resultaten beschikbaar zijn. "
                "Als de brugparameters zijn gewijzigd, wis de cache en voer een nieuwe berekening uit."
            ) from e
        raise UserError(f"IDEA model XML generatie gefaald: {e!s}") from e

    # Run IDEA analysis — pass back through BytesIO so the SDK gets a file-like object
    progress_message(f"{prefix}Uitvoeren IDEA RCS analyse...", percentage=percentage)
    analysis = idea_rcs.IdeaRcsAnalysis(BytesIO(idea_xml_input_bytes), return_rcs_file=True)
    try:
        analysis.execute(600)
    except Exception as e:
        error_msg = str(e)
        if "cannot be generated" in error_msg.lower():
            raise UserError(
                "IDEA model kan niet worden gegenereerd. "
                "Mogelijke oorzaken: geen dwarsdoorsneden gemaakt, geen belastingen toegepast, of ongeldige geometrie. "
                "Controleer of de wapeningszones overeenkomen met de brugsegmenten en of SCIA resultaten beschikbaar zijn. "
                "Als de brugparameters zijn gewijzigd, wis de cache en voer een nieuwe berekening uit."
            ) from e
        raise UserError(f"IDEA RCS analyse uitvoering gefaald: {error_msg}") from e

    # Get the IDEA RCS model and output XML
    progress_message(f"{prefix}Verwerken IDEA analyse resultaten...", percentage=percentage)
    idea_rcs_model = analysis.get_idea_rcs_file(as_file=False)
    idea_output_xml_bytes = analysis.get_output_file(as_file=False)

    # Extract output content for parsing
    output_content = _extract_file_content(idea_output_xml_bytes)

    results: dict[str, Any] = {}
    try:
        progress_message(f"{prefix}Parsen IDEA output...", percentage=percentage)
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

        # Extract bytes from any file-like objects so the dict is picklable
        rcs_model_bytes = _extract_file_content(idea_rcs_model) if not isinstance(idea_rcs_model, bytes) else idea_rcs_model
        results.update(
            {
                "section_results": section_results,
                "analysis_status": "completed",
                "idea_xml_input_bytes": idea_xml_input_bytes,  # already bytes
                "idea_rcs_model": rcs_model_bytes,
                "output_content": output_content,
            }
        )
    except Exception as e:
        results.update(
            {
                "analysis_status": "failed",
                "error": str(e),
                "idea_xml_input_bytes": idea_xml_input_bytes,  # already bytes
                "output_content": output_content,
            }
        )
    return results


def get_scia_results_for_idea(params: Any, entity_id: int, analysis_context: dict[str, Any] | None = None) -> dict[str, Any]:  # noqa: ANN401
    """
    Get SCIA results that are needed for IDEA analysis.

    This function processes SCIA analysis results and returns node results (2D forces),
    CS results (cross section forces), and integration strip results (1D forces)
    in a single merged dictionary.

    :param params: Bridge parametrization
    :type params: Any
    :param entity_id: Entity ID for caching
    :type entity_id: int
    :param analysis_context: Optional context dict with bridge_position, total_bridges, bridge_name, batch_percentage
    :type analysis_context: dict[str, Any] | None
    :returns: Dictionary containing processed SCIA node, CS, and integration strip results for IDEA
    :rtype: dict[str, Any]
    :raises UserError: If bridge segments are missing or analysis fails
    """
    # Build progress message prefix from context
    if analysis_context:
        prefix = f"Bridge {analysis_context['bridge_position']}/{analysis_context['total_bridges']}: {analysis_context['bridge_name']}\n"
        percentage = analysis_context.get("batch_percentage")
    else:
        prefix = ""
        percentage = None

    # Get entity ID for caching
    if not isinstance(entity_id, int):
        raise UserError("Entity ID niet gevonden. Cache functionaliteit niet beschikbaar.")

    try:
        from app.constants import SCIA_TEMPLATE_SECTIONS_ON_PLANE_GOVERNING_PATH
        from app.constants.technical import ENABLE_SECTIONS_ON_PLANE, RESULT_OBJECT_SECTIONS_ON_PLANE

        # Build both possible template paths — the SCIA cache key depends on which one was used
        # when the SCIA analysis was originally run.  In the live environment the params attribute
        # may resolve differently from local, causing a key mismatch.  We therefore try EVERY
        # possible template path and take the first cache hit that contains envelope data.
        all_template_paths: list[str | None] = [
            str(SCIA_TEMPLATE_SECTIONS_ON_PLANE_GOVERNING_PATH),
            str(SCIA_TEMPLATE_PATH),
            None,  # legacy: no template path in key
        ]

        # Prefer the path that matches the current parametrization (fewer cache checks)
        try:
            result_type = params.calc_page.calc_selection.result_object_type
        except AttributeError:
            result_type = RESULT_OBJECT_SECTIONS_ON_PLANE if ENABLE_SECTIONS_ON_PLANE else None

        preferred_path = str(SCIA_TEMPLATE_SECTIONS_ON_PLANE_GOVERNING_PATH) if result_type == RESULT_OBJECT_SECTIONS_ON_PLANE else str(SCIA_TEMPLATE_PATH)
        # Re-order so the preferred path is tried first
        all_template_paths = [preferred_path] + [p for p in all_template_paths if p != preferred_path]

        progress_message(f"{prefix}Ophalen SCIA resultaten voor IDEA verwerking...", percentage=percentage)

        cache = _get_analysis_cache()
        results: dict[str, Any] | None = None
        for tpath in all_template_paths:
            candidate = cache.get_cached_analysis(params, AnalysisType.SCIA, entity_id, tpath)
            if candidate is not None and ("integration_strips" in candidate or "sections_on_plane" in candidate):
                results = candidate
                break

        # If no cache hit at all, fall back to running the analysis (will use the preferred path)
        if results is None:
            results = get_cached_analysis_results(params, AnalysisType.SCIA, entity_id, get_scia_analysis_results, preferred_path, analysis_context)

    except UserError:
        raise
    except Exception as e:
        raise UserError(f"Onverwachte fout tijdens ophalen SCIA resultaten voor IDEA analyse: {e!s}")

    # Validate SCIA results
    if results is None:
        raise UserError("Geen SCIA resultaten beschikbaar voor IDEA analyse")

    # Check if at least one supported result type is available for IDEA
    if "integration_strips" not in results and "sections_on_plane" not in results:
        raise UserError(
            "Geen SCIA resultaten beschikbaar voor IDEA analyse. Voer een nieuwe SCIA berekening uit met integratiestroken of secties op vlak."
        )

    # Return results dictionary (IDEA interface selects the correct result type)
    return {
        "results": results,
    }


def get_idea_model_only(params: Any, entity_id: int, analysis_context: dict[str, Any] | None = None) -> dict[str, Any]:  # noqa: ANN401
    """Create IDEA model only (without running analysis)."""
    progress_message("Genereren IDEA model...")
    model = create_bridge_idea_model(params, entity_id)
    # Extract raw bytes — Viktor File/BytesIO objects are not picklable
    xml_bytes = _extract_file_content(model.generate_xml_input())
    return {
        "idea_xml_input_bytes": xml_bytes,
        "analysis_status": "model_created",
    }


class AnalysisCache:
    """General cache for analysis results using VIKTOR Storage."""

    # Class-level cache shared across all instances in the same worker process
    # This ensures that different views in the same request can reuse cached results
    request_cache: ClassVar[dict[str, dict[str, Any]]] = {}

    def __init__(self) -> None:
        """Initialize the analysis cache with VIKTOR Storage."""
        self.storage = Storage()
        self._hash_cache: dict[tuple[int, str, str | None], str] = {}  # Cache for computed hashes
        self._entity_cache: dict[int, Any] = {}  # Cache for entity objects

    def _write_storage_warning(self, message: str) -> None:
        """Persist a workspace-level warning so the UI can notify the user."""
        try:
            payload = json.dumps(
                {
                    "message": message,
                    "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
                }
            )
            self.storage.set(
                STORAGE_WARNING_MARKER_KEY,
                data=File.from_data(payload),
                scope="workspace",
            )
        except Exception:
            # If storage is already inaccessible we cannot do much—ignore.
            pass

    def _clear_storage_warning(self) -> None:
        """Remove the workspace warning marker once storage succeeds again."""
        try:
            self.storage.delete(STORAGE_WARNING_MARKER_KEY, scope="workspace")
        except FileNotFoundError:
            pass
        except Exception:
            pass

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
        """Generate a hash of the input parameters for caching (with memoization)."""
        # Create cache key based on object id and analysis type
        cache_key = (id(params), analysis_type.value, template_path)

        # Return cached hash if available
        if cache_key in self._hash_cache:
            return self._hash_cache[cache_key]

        # Compute hash
        extracted_params = self._extract_params(params, analysis_type, template_path)
        params_json = json.dumps(extracted_params, sort_keys=True, default=str)
        computed_hash = hashlib.md5(params_json.encode()).hexdigest()

        # Cache the result
        self._hash_cache[cache_key] = computed_hash
        return computed_hash

    def _get_entity(self, entity_id: int) -> Any:  # noqa: ANN401
        """
        Get entity object for the given entity ID with memoization.

        This retrieves the entity so it can be passed to Storage methods
        for cross-entity storage access per VIKTOR SDK documentation.

        :param entity_id: Entity ID
        :type entity_id: int
        :returns: Entity object or None if unavailable
        :rtype: Any
        """
        if entity_id not in self._entity_cache:
            try:
                entity_obj = api.API().get_entity(entity_id)
                self._entity_cache[entity_id] = entity_obj
            except Exception:
                self._entity_cache[entity_id] = None
        return self._entity_cache[entity_id]

    def get_cached_analysis(  # noqa: C901
        self,
        params: Any,  # noqa: ANN401
        analysis_type: AnalysisType,
        entity_id: int,
        template_path: str | None = None,
    ) -> dict[str, Any] | None:
        """Get cached analysis results if available."""
        cache_key = ""
        try:
            # Generate hash (with memoization - this should be fast on subsequent calls)
            input_hash = self._generate_input_hash(params, analysis_type, template_path)
            cache_key = f"analysis_cache_{entity_id}_{analysis_type.value}_{input_hash}"

            # Check request-level cache first (fastest - in-memory)
            # Note: request_cache is a class variable, shared across all AnalysisCache instances
            # within the same worker process for optimal performance
            if cache_key in AnalysisCache.request_cache:
                return AnalysisCache.request_cache[cache_key]

            # Get entity object for cross-entity storage access
            entity = self._get_entity(entity_id)

            # Storage retrieval from entity scope
            if entity is not None:
                cached_file = self.storage.get(cache_key, scope="entity", entity=entity)
            else:
                # Fallback: use current entity scope if API unavailable
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
                results = pickle.loads(cached_data)

                # Store in request-level cache for subsequent views in same request
                AnalysisCache.request_cache[cache_key] = results

                # Limit request cache size to prevent memory issues
                # Keep only the most recent 10 entries per entity
                if len(AnalysisCache.request_cache) > 10:
                    # Remove oldest entries (simple FIFO)
                    keys_to_remove = list(AnalysisCache.request_cache.keys())[:-10]
                    for key_to_remove in keys_to_remove:
                        del AnalysisCache.request_cache[key_to_remove]

                return results
        except Exception as e:
            if isinstance(e, InternalError):
                self._write_storage_warning(f"Opslag lezen mislukt voor {cache_key or 'onbekende sleutel'} ({analysis_type.value})")

        return None

    def _attempt_storage_cleanup_and_retry(
        self,
        _entity_id: int,
        cache_key: str,
        cached_file: File,
    ) -> bool:
        """
        Attempt to free up storage space and retry cache save.

        When storage is full (5 GB limit), this method:
        1. Clears ALL cache files from current entity
        2. Clears workspace markers
        3. Retries the cache save once
        4. Returns success/failure

        :param entity_id: Entity ID for logging
        :type entity_id: int
        :param cache_key: Cache key to save
        :type cache_key: str
        :param cached_file: File object to save
        :type cached_file: File
        :returns: True if retry succeeded, False otherwise
        :rtype: bool
        """
        try:
            # 1. Clear ALL cache files from current entity's storage
            try:
                entity_keys = self.storage.list(scope="entity")
                for key in entity_keys:
                    if key.startswith("analysis_cache_"):
                        with contextlib.suppress(Exception):
                            self.storage.delete(key, scope="entity")
            except Exception:
                pass

            # 2. Clear workspace markers and batch results
            try:
                workspace_keys = self.storage.list(scope="workspace")
                for key in workspace_keys:
                    if key.startswith(("bridge_", "batch_calculation_", "analysis_cache_")):
                        with contextlib.suppress(Exception):
                            self.storage.delete(key, scope="workspace")
            except Exception:
                pass

            # 3. Retry the cache save
            self.storage.set(cache_key, data=cached_file, scope="entity")
            return True  # noqa: TRY300
        except Exception:
            return False

    def cache_analysis_results(  # noqa: C901, PLR0912
        self,
        params: Any,  # noqa: ANN401
        analysis_type: AnalysisType,
        entity_id: int,
        results: dict[str, Any],
        template_path: str | None = None,
    ) -> bool:
        """
        Cache analysis results.

        :returns: True if caching succeeded, False if it failed
        :rtype: bool
        """
        input_hash = self._generate_input_hash(params, analysis_type, template_path)
        cache_key = f"analysis_cache_{entity_id}_{analysis_type.value}_{input_hash}"

        try:
            # Filter results to exclude large binary files (ESA, XML output)
            if analysis_type == AnalysisType.SCIA:
                cacheable_results = extract_cacheable_scia_results(results)
            elif analysis_type == AnalysisType.IDEA:
                cacheable_results = extract_cacheable_idea_results(results)
            else:
                cacheable_results = results  # Fallback

            # Pickle the filtered results and encode as base64 to avoid binary data issues
            cached_data = pickle.dumps(cacheable_results)
            encoded_data = base64.b64encode(cached_data).decode("utf-8")
            size_mb = len(encoded_data) / (1024 * 1024)

            # Size check: Skip caching if data is too large (> 250 MB)
            max_cache_size_mb = 250
            if size_mb > max_cache_size_mb:
                # Cache is too large for storage, but store in request-level cache anyway
                # This helps with multiple views in the same request/session
                import logging

                logging.warning(
                    f"Cache too large for Storage ({size_mb:.2f} MB > {max_cache_size_mb} MB). Storing in request cache only for entity {entity_id}"
                )
                AnalysisCache.request_cache[cache_key] = cacheable_results
                return False

            # Log size for monitoring
            import logging

            logging.info(f"Caching {analysis_type.value.upper()} results for entity {entity_id}: {size_mb:.2f} MB")

            cached_file = File.from_data(encoded_data)

            # CRITICAL: Delete old cache files for this entity + analysis type BEFORE saving new one.
            # In practice the entire Storage() API (list/get/set/delete) starts throwing InternalError once
            # the workspace quota is saturated. We therefore avoid Storage.list() and rely on the workspace
            # marker to know exactly which cache key to delete. If even Storage.get(marker_key) fails we
            # simply log it and continue – the next calculation will have to recalc until someone purges
            # storage manually (cache button, viktor-cli clear, or platform support).
            try:
                import json

                # Read workspace marker to get old hash
                marker_key = f"bridge_{entity_id}_{analysis_type.value}_cache_status"
                marker_file = self.storage.get(marker_key, scope="workspace")
                marker_data = json.loads(marker_file.getvalue())
                old_hash = marker_data.get("cached_hash")

                if old_hash and old_hash != input_hash:
                    # Construct old cache key from marker and delete it
                    old_cache_key = f"analysis_cache_{entity_id}_{analysis_type.value}_{old_hash}"
                    try:
                        self.storage.delete(old_cache_key, scope="entity")
                    except Exception as delete_error:
                        if isinstance(delete_error, InternalError):
                            self._write_storage_warning(f"Opslag verwijderen mislukt voor {old_cache_key}")
            except FileNotFoundError:
                pass
            except Exception as marker_error:
                if isinstance(marker_error, InternalError):
                    self._write_storage_warning(f"Opslag lezen van cache marker mislukt ({analysis_type.value})")

            # Get entity object for cross-entity storage access
            entity = self._get_entity(entity_id)

            # Write to local entity storage
            try:
                if entity is not None:
                    self.storage.set(cache_key, data=cached_file, scope="entity", entity=entity)
                else:
                    # Fallback: use current entity scope if API unavailable
                    self.storage.set(cache_key, data=cached_file, scope="entity")
                self._clear_storage_warning()

                # Store in request-level cache as well
                AnalysisCache.request_cache[cache_key] = cacheable_results

                # Notify parent entity of cache status
                notify_parent_of_cache_status(entity_id, analysis_type, input_hash)
                return True  # noqa: TRY300

            except Exception as storage_error:
                # Storage write failed - store in request-level cache anyway for this session
                AnalysisCache.request_cache[cache_key] = cacheable_results

                if isinstance(storage_error, InternalError):
                    self._write_storage_warning(f"Opslag schrijven mislukt voor {cache_key}")

                    # Attempt automatic cleanup and retry
                    cleanup_success = self._attempt_storage_cleanup_and_retry(entity_id, cache_key, cached_file)

                    if cleanup_success:
                        # Cleanup worked! Notify parent and return success
                        with contextlib.suppress(Exception):
                            notify_parent_of_cache_status(entity_id, analysis_type, input_hash)

                        self._clear_storage_warning()
                        return True
                    # Cleanup failed - but request cache is populated, so partial success
                    return False
                # Not a storage error, just fail gracefully (but request cache is still populated)
                return False

        except Exception:
            # General error during caching setup
            # Still try to populate request cache if we got this far (cacheable_results should exist)
            with contextlib.suppress(Exception):
                AnalysisCache.request_cache[cache_key] = cacheable_results
            return False

    def clear_cache(self, entity_id: int, analysis_type: AnalysisType | None = None) -> None:
        """Clear cache for a specific entity and analysis type."""
        # Clear hash cache
        self._hash_cache.clear()

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


def notify_parent_of_cache_status(
    entity_id: int,
    analysis_type: AnalysisType,
    cache_hash: str,
) -> None:
    """
    Notify parent entity that this bridge has cached results.

    Writes a lightweight marker file to parent's storage so the overview
    can check cache status without cross-entity storage access.

    :param entity_id: Bridge entity ID
    :type entity_id: int
    :param analysis_type: Analysis type (SCIA or IDEA)
    :type analysis_type: AnalysisType
    :param cache_hash: Hash of cached parameters
    :type cache_hash: str
    :returns: None
    :rtype: None
    """
    try:
        # Get parent entity
        current_entity = api.API().get_entity(entity_id)
        parent_entity = current_entity.parent()

        if parent_entity is None:
            return

        # Create marker data
        marker_data = {
            "entity_id": entity_id,
            "analysis_type": analysis_type.value,
            "cache_hash": cache_hash,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        # Write to parent storage
        marker_key = f"bridge_{entity_id}_{analysis_type.value}_cache_status"
        marker_json = json.dumps(marker_data)
        marker_file = File.from_data(marker_json)

        # Write to workspace storage (accessible by all entities)
        parent_storage = Storage()
        parent_storage.set(marker_key, data=marker_file, scope="workspace")
    except Exception:
        # Don't fail the analysis if parent notification fails
        pass


def _process_esa_model_for_cache(esa_model: bytes | None, cacheable: dict[str, Any]) -> None:
    """
    Process ESA model for caching based on size threshold.

    Only caches ESA models under 250 MB to prevent storage overflow.
    Updates the cacheable dict in-place with ESA model and metadata.

    :param esa_model: ESA model bytes or None
    :type esa_model: bytes | None
    :param cacheable: Dictionary to update with ESA model and metadata
    :type cacheable: dict[str, Any]
    :returns: None (updates cacheable in-place)
    :rtype: None
    """
    if esa_model is None:
        return

    # Check size in bytes
    esa_size_bytes = len(esa_model) if isinstance(esa_model, bytes) else 0
    esa_size_mb = esa_size_bytes / (1024 * 1024)

    # Only cache if under 250 MB threshold
    if esa_size_mb < 250:
        cacheable["esa_model"] = esa_model
        # Update summary to indicate ESA was cached
        if "summary" in cacheable and isinstance(cacheable["summary"], dict):
            cacheable["summary"]["esa_model_cached"] = True
            cacheable["summary"]["esa_model_size_mb"] = round(esa_size_mb, 2)
    # ESA too large - don't cache it
    elif "summary" in cacheable and isinstance(cacheable["summary"], dict):
        cacheable["summary"]["esa_model_cached"] = False
        cacheable["summary"]["esa_model_size_mb"] = round(esa_size_mb, 2)
        cacheable["summary"]["esa_model_too_large"] = True


def extract_cacheable_scia_results(full_results: dict[str, Any]) -> dict[str, Any]:  # noqa: PLR0912, C901
    """
    Extract cacheable data from SCIA results with smart ESA filtering.

    ESA model caching logic:
    - If ESA > 250MB: Never cached
    - If ESA < 250MB but total cache > 250MB: ESA excluded to keep cache under limit
    - If ESA < 250MB and total cache < 250MB: ESA included

    Includes:
    - xml_output (needed for downloads)
    - Parsed DataFrames (cs_envelope_df, integration_strips, etc.)
    - Summary dict
    - Analysis status
    - Other processed data

    :param full_results: Complete SCIA analysis results
    :type full_results: dict[str, Any]
    :returns: Filtered results suitable for caching
    :rtype: dict[str, Any]
    """
    cacheable = {
        "analysis_status": full_results.get("analysis_status"),
        "summary": full_results.get("summary"),
    }

    # Include df_cs_envelope if present (parsed, relatively small)
    if "df_cs_envelope" in full_results:
        cacheable["df_cs_envelope"] = full_results["df_cs_envelope"]

    # Include CS dataframes if present (needed for CS ULS/SLS freq views)
    if "df_cs_uls" in full_results:
        cacheable["df_cs_uls"] = full_results["df_cs_uls"]
    if "df_cs_sls_freq" in full_results:
        cacheable["df_cs_sls_freq"] = full_results["df_cs_sls_freq"]

    # Include integration strips if present (needed for integration strip views)
    if "integration_strips" in full_results:
        cacheable["integration_strips"] = full_results["integration_strips"]

    # Include sections-on-plane if present (needed for sections-on-plane views)
    if "sections_on_plane" in full_results:
        cacheable["sections_on_plane"] = full_results["sections_on_plane"]

    # Include other DataFrames/parsed results (small)
    for key in ["displacements", "internal_forces", "reactions", "stresses"]:
        if key in full_results:
            cacheable[key] = full_results[key]

    # Include xml_output for downloads (moderate size, but needed)
    if "xml_output" in full_results:
        cacheable["xml_output"] = full_results["xml_output"]

    # Smart ESA model caching:
    # First, check cache size without ESA. If adding ESA would exceed 250MB, exclude it.
    if "esa_model" in full_results:
        esa_model = full_results["esa_model"]
        esa_size_bytes = len(esa_model) if esa_model else 0
        esa_size_mb = esa_size_bytes / (1024 * 1024)

        # Calculate current cache size without ESA
        import pickle

        test_data = pickle.dumps(cacheable)
        current_size_mb = len(test_data) / (1024 * 1024)
        projected_size_mb = current_size_mb + esa_size_mb

        if "summary" not in cacheable:
            cacheable["summary"] = {}
        if not isinstance(cacheable["summary"], dict):
            cacheable["summary"] = {}

        # Use typed variable to help MyPy
        summary: dict[str, Any] = cacheable["summary"]  # type: ignore[assignment]
        summary["esa_model_size_mb"] = round(esa_size_mb, 2)

        # Only cache ESA if: 1) ESA < 250MB AND 2) Total cache would be < 250MB
        if esa_size_mb >= 250:
            # ESA too large - never cache it
            summary["esa_model_cached"] = False
            summary["esa_model_too_large"] = True
        elif projected_size_mb > 250:
            # ESA would push cache over 250MB limit - exclude it
            summary["esa_model_cached"] = False
            summary["esa_excluded_due_to_size"] = True
            summary["projected_cache_size_mb"] = round(projected_size_mb, 2)
        else:
            # ESA fits within limits - cache it
            cacheable["esa_model"] = esa_model
            summary["esa_model_cached"] = True

    return cacheable


def extract_cacheable_idea_results(full_results: dict[str, Any]) -> dict[str, Any]:
    """
    Extract only cacheable data from IDEA results (exclude large binary files).

    This function stores the complete IDEA results including model and binary files
    needed for downloads. While these files are large, they are necessary for:
    - XML download (needs idea_xml_input_bytes)
    - Results download (needs all files for ZIP creation)

    The alternative would be to regenerate these files on-demand, but that would
    require running the IDEA analysis again, which is slower than caching.

    Includes:
    - model (IDEA model object, needed for XML generation)
    - idea_xml_input_bytes (XML input file)
    - idea_rcs_model (RCS model file)
    - idea_xml_output_bytes (XML output file)
    - output_content (raw output for parsing)
    - Parsed section results
    - Analysis status

    :param full_results: Complete IDEA analysis results
    :type full_results: dict[str, Any]
    :returns: Filtered results suitable for caching
    :rtype: dict[str, Any]
    """
    cacheable = {
        "analysis_status": full_results.get("analysis_status"),
    }

    # Include section_results (parsed, small)
    if "section_results" in full_results:
        cacheable["section_results"] = full_results["section_results"]

    # Include error if present
    if "error" in full_results:
        cacheable["error"] = full_results["error"]

    # Include model and binary files for downloads
    # Note: These are large but necessary for download functionality
    if "model" in full_results:
        cacheable["model"] = full_results["model"]
    if "idea_xml_input_bytes" in full_results:
        cacheable["idea_xml_input_bytes"] = full_results["idea_xml_input_bytes"]
    if "idea_rcs_model" in full_results:
        cacheable["idea_rcs_model"] = full_results["idea_rcs_model"]
    if "idea_xml_output_bytes" in full_results:
        cacheable["idea_xml_output_bytes"] = full_results["idea_xml_output_bytes"]
    if "output_content" in full_results:
        cacheable["output_content"] = full_results["output_content"]

    return cacheable


def has_valid_scia_cache_for_idea(params: Any, entity_id: int) -> bool:  # noqa: ANN401
    """
    Check if valid SCIA cache exists that can be used for IDEA analysis.

    This validates the cache by attempting to process it the same way IDEA does,
    ensuring the cache contains the required CS table data.

    :param params: Bridge parametrization
    :type params: Any
    :param entity_id: Bridge entity ID
    :type entity_id: int
    :returns: True if SCIA cache exists and can be processed for IDEA, False otherwise
    :rtype: bool
    """
    cache = _get_analysis_cache()
    template_path = str(SCIA_TEMPLATE_PATH)

    # Check if SCIA cache exists using the same method as get_cached_analysis_results
    scia_results = cache.get_cached_analysis(params, AnalysisType.SCIA, entity_id, template_path)
    if scia_results is None:
        return False

    # Validate cache by checking if integration strips are available
    # Integration strips are mandatory for IDEA analysis
    try:
        # Check if integration strips exist in the results
        if "integration_strips" not in scia_results:
            return False

        # Verify integration strips have data
        integration_strips = scia_results.get("integration_strips")
    except Exception:
        # Error accessing results - cache is invalid
        return False
    else:
        # Cache is valid if integration strips are present and non-empty
        return not (integration_strips is None or not integration_strips)


def has_valid_idea_cache(params: Any, entity_id: int, expected_hash: str | None = None) -> bool:  # noqa: ANN401
    """
    Check if valid IDEA cache exists for the given parameters.

    If expected_hash is provided, compares it with current parameters hash.
    Only returns True if hashes match AND cache exists (ensures parameters haven't changed).
    Otherwise, checks if cache exists for current parameters.

    :param params: Bridge parametrization (used to generate hash for comparison)
    :type params: Any
    :param entity_id: Bridge entity ID
    :type entity_id: int
    :param expected_hash: Optional cache hash from batch results to validate against current params
    :type expected_hash: str | None
    :returns: True if IDEA cache exists and parameters match, False otherwise
    :rtype: bool
    """
    cache = _get_analysis_cache()

    # Generate hash for current parameters
    # Note: Using private method _generate_input_hash for cache consistency
    current_hash = cache._generate_input_hash(params, AnalysisType.IDEA, None)  # noqa: SLF001

    # If expected_hash is provided, it must match current hash exactly
    # This ensures that if parameters changed, cache is considered invalid
    if expected_hash is not None:
        if current_hash != expected_hash:
            # Hash mismatch - parameters changed, cache is invalid
            return False
        # Hashes match - check if cache exists for this hash
        cache_key = f"analysis_cache_{entity_id}_{AnalysisType.IDEA.value}_{expected_hash}"
        try:
            cached_file = cache.storage.get(cache_key, scope="entity")
        except Exception:
            return False
        else:
            return cached_file is not None

    # Otherwise, check cache for current parameters
    idea_results = cache.get_cached_analysis(params, AnalysisType.IDEA, entity_id)
    return idea_results is not None


def get_cached_analysis_results(  # noqa: PLR0913
    params: Any,  # noqa: ANN401
    analysis_type: AnalysisType,
    entity_id: int,
    analysis_function: Callable[..., dict[str, Any]],
    template_path: str | None = None,
    analysis_context: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """
    Get cached analysis results or run analysis if not cached.

    :param params: Bridge parameters
    :param analysis_type: Type of analysis (SCIA or IDEA)
    :param entity_id: Entity ID
    :param analysis_function: Function to run if cache miss
    :param template_path: Optional template path for SCIA
    :param analysis_context: Optional context dict with bridge_position, total_bridges, bridge_name, batch_percentage
    :returns: Analysis results dictionary or None
    """
    cache = _get_analysis_cache()

    # Build progress message prefix from context
    if analysis_context:
        prefix = f"Bridge {analysis_context['bridge_position']}/{analysis_context['total_bridges']}: {analysis_context['bridge_name']}\n"
        percentage = analysis_context.get("batch_percentage")
    else:
        prefix = ""
        percentage = None

    # Try to get cached results (hash computation is fast with memoization)
    progress_message(f"{prefix}Controleren op gecachte resultaten...", percentage=percentage)
    cached_results = cache.get_cached_analysis(params, analysis_type, entity_id, template_path)
    if cached_results is not None:
        progress_message(f"{prefix}✓ Cache gevonden - resultaten worden geladen...")
        # Store in request-level cache for reuse within this request
        input_hash = cache._generate_input_hash(params, analysis_type, template_path)  # noqa: SLF001
        cache_key = f"analysis_cache_{entity_id}_{analysis_type.value}_{input_hash}"
        AnalysisCache.request_cache[cache_key] = cached_results
        return cached_results

    # Run analysis if not cached
    progress_message(f"{prefix}⚠ Geen cache gevonden - nieuwe {analysis_type.value.upper()} analyse wordt gestart...")
    # Call the analysis function based on analysis type
    if analysis_type == AnalysisType.SCIA:
        results = analysis_function(params, template_path, analysis_context)
    elif analysis_type == AnalysisType.IDEA:
        results = analysis_function(params, entity_id, analysis_context)
    else:
        # Fallback: try calling with just params
        raise UserError("Unsupported analysis type for caching.")

    # Cache the results and log if caching fails
    if results is not None:
        progress_message(f"Opslaan {analysis_type.value.upper()} resultaten in cache...")
        cache_success = cache.cache_analysis_results(params, analysis_type, entity_id, results, template_path)
        if not cache_success:
            # Caching failed - log warning but continue (analysis completed successfully)
            import logging

            logging.warning(
                f"Failed to cache {analysis_type.value.upper()} results for entity {entity_id}. Results will need to be recalculated on next request."
            )

    return results
