"""Batch calculation component for OverviewBridgesController."""

import contextlib
import logging
import traceback
from typing import Any

import viktor.api_v1 as api
from viktor.core import Color, Storage, UserMessage, progress_message
from viktor.errors import UserError
from viktor.parametrization import Parametrization
from viktor.views import TableCell, TableResult, TableView

from app.bridge.analysis_cache import STORAGE_WARNING_MARKER_KEY, _get_analysis_cache, get_cached_analysis_results, get_idea_analysis_results
from src.common.constants.technical import AnalysisType

from .utils import (
    calculate_estimated_batch_time,
    check_idea_cache_status,
    deserialize_batch_results,
    extract_uc_summary_from_idea_results,
    generate_bridge_report_url,
    serialize_batch_results,
    validate_bridge_for_calculation,
)

logger = logging.getLogger(__name__)


class BatchCalculationComponent:
    """Component providing batch calculation functionality for multiple bridges."""

    @TableView("Statusoverzicht", duration_guess=1)
    def view_batch_status_and_results(self, params: Parametrization, entity_id: int, **kwargs) -> TableResult:  # noqa: ARG002, C901, PLR0912, PLR0915
        """
        Display unified table showing bridge readiness status and calculation results.

        Shows validation status, missing fields, max UC, UC status, failed checks, and report links.
        Includes storage warning indicator if storage quota is exceeded.

        :param params: Overview Bridges parametrization object
        :type params: Parametrization
        :param entity_id: Entity ID of the Overview Bridges entity
        :type entity_id: int
        :param kwargs: Additional arguments
        :returns: TableResult with combined status and results
        :rtype: TableResult
        """
        storage = Storage()

        # Check for storage warning marker
        storage_warning_message = None
        try:
            warning_file = storage.get(STORAGE_WARNING_MARKER_KEY, scope="workspace")
            if warning_file:
                import json

                warning_data = json.loads(warning_file.getvalue())
                storage_warning_message = warning_data.get("message", "Opslaglimiet bereikt")
        except (FileNotFoundError, Exception):
            pass

        # Get all Bridge child entities
        viktor_api = api.API()
        try:
            parent_entity = viktor_api.get_entity(entity_id)
            bridge_entities = parent_entity.children(entity_type_names=["Bridge"])
        except Exception as e:
            raise UserError(f"Fout bij ophalen van bruggen: {e}")

        # Load batch results from storage
        batch_results = None
        try:
            batch_results_file = storage.get("batch_calculation_results", scope="entity")
            from viktor.core import File

            if isinstance(batch_results_file, bool):
                logger.warning("Found boolean value in storage for 'batch_calculation_results'. Deleting invalid entry.")
                with contextlib.suppress(Exception):
                    storage.delete("batch_calculation_results", scope="entity")
            elif isinstance(batch_results_file, File):
                batch_results = deserialize_batch_results(batch_results_file)
        except (FileNotFoundError, TypeError, AttributeError):
            pass

        # Initialize counters
        total_bridges = len(bridge_entities)
        ready_bridges = 0
        cached_bridges = 0
        non_cached_ready_bridges = 0
        bridge_data_list = []

        # Process each bridge
        for bridge_entity in bridge_entities:
            bridge_name = bridge_entity.name
            bridge_id = bridge_entity.id

            # Fetch fresh entity to get most current saved params
            try:
                from viktor.api_v1 import API

                fresh_entity = API().get_entity(bridge_id)
                bridge_params = fresh_entity.last_saved_params
            except Exception:
                bridge_params = bridge_entity.last_saved_params

            # Validate bridge readiness
            is_ready, missing_fields, _ = validate_bridge_for_calculation(bridge_params, bridge_entity)

            # Check cache status
            is_cached = check_idea_cache_status(bridge_params, bridge_id, batch_results_cache_hash=None)

            if is_ready:
                ready_bridges += 1
                if is_cached:
                    cached_bridges += 1
                else:
                    non_cached_ready_bridges += 1
                missing_fields_str = ""
            elif len(missing_fields) <= 2:
                missing_fields_str = ", ".join(missing_fields)
            else:
                missing_fields_str = f"{', '.join(missing_fields[:2])} (+{len(missing_fields) - 2} meer)"

            # Determine status display
            if is_ready:
                if is_cached:
                    status_display = TableCell("✓ Berekening actueel", background_color=Color(144, 238, 144))
                    sort_priority = 2
                else:
                    status_display = TableCell("✓ Klaar voor berekening", background_color=Color(255, 255, 0))
                    sort_priority = 1
            else:
                status_display = TableCell("✗ Niet klaar voor berekening", background_color=Color(255, 200, 200))
                sort_priority = 3

            # Get results data if available
            max_uc_str = "-"
            uc_status_str = "-"
            failed_checks_str = "-"
            report_url = "-"

            # First try to get from batch_results (preferred source)
            if batch_results and bridge_id in batch_results:
                result = batch_results[bridge_id]
                max_uc = result.get("max_uc")
                uc_status = result.get("uc_status", "N/A")
                failed_checks = result.get("failed_checks", [])

                max_uc_str = f"{max_uc:.2f}" if max_uc is not None else "-"
                uc_status_str = uc_status if uc_status != "N/A" else "-"
                failed_checks_str = str(len(failed_checks)) if failed_checks else "0"
                report_url = generate_bridge_report_url(bridge_id)

            # Fallback: if cache says "actueel" but no batch_results, try reading entity cache
            elif is_cached:
                try:
                    logger.info(f"Bridge {bridge_id}: Cache marked as valid but no batch_results entry - reading from entity cache")
                    cache = _get_analysis_cache()
                    idea_results = cache.get_cached_analysis(
                        params=bridge_params, analysis_type=AnalysisType.IDEA, entity_id=bridge_id, template_path=None
                    )

                    if idea_results is not None:
                        # Extract UC summary from cached IDEA results
                        uc_summary = extract_uc_summary_from_idea_results(idea_results)

                        max_uc = uc_summary.get("max_uc")
                        uc_status = uc_summary.get("status", "N/A")
                        failed_checks = uc_summary.get("failed_checks", [])

                        max_uc_str = f"{max_uc:.2f}" if max_uc is not None else "-"
                        uc_status_str = uc_status if uc_status != "N/A" else "-"
                        failed_checks_str = str(len(failed_checks)) if failed_checks else "0"
                        report_url = generate_bridge_report_url(bridge_id)

                        logger.info(f"Bridge {bridge_id}: Successfully read from entity cache - Max UC: {max_uc_str}")
                    else:
                        logger.warning(f"Bridge {bridge_id}: Cache marked valid but get_cached_analysis returned None - showing '-'")
                except FileNotFoundError:
                    logger.warning(f"Bridge {bridge_id}: Cache file not found despite marker - showing '-'")
                except Exception as e:
                    logger.warning(f"Bridge {bridge_id}: Failed to read entity cache: {type(e).__name__} - showing '-'")

            # Store data with sort priority
            bridge_data_list.append(
                (
                    sort_priority,
                    bridge_name,
                    [status_display, missing_fields_str, max_uc_str, uc_status_str, failed_checks_str, report_url],
                    uc_status_str,
                    max_uc_str if max_uc_str != "-" else "0.0",
                )
            )

        # Sort: ready but not cached first, then cached, then not ready
        # Within each group, sort by max UC descending, then by bridge name
        def sort_key(item: tuple) -> tuple:
            priority, bridge_name, data_row, uc_status, max_uc = item
            max_uc_value = float(max_uc) if max_uc != "-" and max_uc != "0.0" else -1.0
            # Failed first, then by max UC descending
            uc_priority = 0 if uc_status == "FAILED" else 1
            return (priority, uc_priority, -max_uc_value, bridge_name)

        bridge_data_list.sort(key=sort_key)

        # Calculate time estimate
        time_estimate = calculate_estimated_batch_time(non_cached_ready_bridges)

        # Build summary rows
        status_text = f"{ready_bridges} van {total_bridges} gereed • {cached_bridges} berekening actueel"
        summary_data = [
            [
                TableCell(status_text, text_style="bold"),
                "",
                "",
                "",
                "",
                "",
            ],
            [
                TableCell(time_estimate, text_style="bold"),
                "",
                "",
                "",
                "",
                "",
            ],
        ]

        # Add storage warning row if marker exists
        if storage_warning_message:
            summary_data.append(
                [
                    TableCell(
                        f"⚠️ OPSLAGMODUS: Berekeningen lopen zonder cache (langzamer). Fout: {storage_warning_message}",
                        text_style="bold",
                        background_color=Color(255, 200, 100),  # Orange warning
                    ),
                    "",
                    "",
                    "",
                    "",
                    "",
                ]
            )

        summary_row_headers = ["Status", "Geschatte tijd"]
        if storage_warning_message:
            summary_row_headers.append("Opslagwaarschuwing")

        # Extract bridge data
        bridge_row_headers = []
        bridge_table_data = []
        for _, bridge_name, data_row, _, _ in bridge_data_list:
            bridge_row_headers.append(bridge_name)
            bridge_table_data.append(data_row)

        # Combine summary and bridge data
        final_table_data = summary_data + bridge_table_data
        final_row_headers = summary_row_headers + bridge_row_headers

        # Define column headers
        headers = ["Status", "Ontbrekende velden", "Max UC", "UC Status", "Gefaalde controles", "Rapport"]

        return TableResult(final_table_data, column_headers=headers, row_headers=final_row_headers)

    def refresh_batch_status(self, params: Parametrization, entity_id: int, **kwargs) -> None:  # noqa: ARG002
        """
        Refresh the batch status view without recalculation.

        This is a no-op method - VIKTOR will automatically refresh the view when the button is clicked.

        :param params: Overview Bridges parametrization object
        :type params: Parametrization
        :param entity_id: Entity ID of the Overview Bridges entity
        :type entity_id: int
        :param kwargs: Additional arguments
        """
        UserMessage.info("Statusoverzicht ververst")

    def run_batch_calculation(self, params: Parametrization, entity_id: int, **kwargs) -> None:  # noqa: ARG002, C901, PLR0912, PLR0915
        """
        Execute batch calculation for all ready bridges.

        Runs SCIA+IDEA analysis for each bridge with progress tracking.
        Results are cached automatically per bridge and aggregated results
        are stored in parent entity Storage.

        :param params: Overview Bridges parametrization object
        :type params: Parametrization
        :param entity_id: Entity ID of the Overview Bridges entity
        :type entity_id: int
        :param kwargs: Additional arguments
        :raises UserError: If batch calculation fails
        """
        storage = Storage()
        try:
            # Get all Bridge child entities
            viktor_api = api.API()
            try:
                parent_entity = viktor_api.get_entity(entity_id)
                bridge_entities = parent_entity.children(entity_type_names=["Bridge"])
            except Exception as e:
                raise UserError(f"Fout bij ophalen van bruggen: {e}")

            # Filter to ready bridges
            ready_bridges = []
            for bridge_entity in bridge_entities:
                # Fetch fresh entity to get most current saved params
                try:
                    from viktor.api_v1 import API

                    fresh_entity = API().get_entity(bridge_entity.id)
                    bridge_params = fresh_entity.last_saved_params
                except Exception:
                    # Fallback to cached entity if API call fails
                    bridge_params = bridge_entity.last_saved_params

                is_ready, _, _ = validate_bridge_for_calculation(bridge_params, bridge_entity)
                if is_ready:
                    ready_bridges.append((bridge_entity, bridge_params))

            if not ready_bridges:
                raise UserError("Geen geschikte bruggen gevonden voor batchberekening.")

            # Load batch results to get cache hashes if available
            batch_results_cache_hashes: dict[int, str] = {}
            try:
                batch_results_file = storage.get("batch_calculation_results", scope="entity")

                # Validate storage contents before deserializing
                from viktor.core import File

                # Check for boolean first (most common invalid type)
                if isinstance(batch_results_file, bool):
                    logger.warning("Found boolean value in storage for 'batch_calculation_results'. Deleting invalid entry.")
                    with contextlib.suppress(Exception):
                        storage.delete("batch_calculation_results", scope="entity")
                elif isinstance(batch_results_file, File):
                    logger.info("Deserializing batch results file...")
                    loaded_batch_results = deserialize_batch_results(batch_results_file)
                    # Extract cache hashes from batch results
                    if isinstance(loaded_batch_results, dict):
                        for bid, result in loaded_batch_results.items():
                            if "cache_hash" in result:
                                batch_results_cache_hashes[bid] = result["cache_hash"]
                else:
                    logger.warning(
                        "Unexpected type in storage for 'batch_calculation_results' in run_batch_calculation: %s, "
                        "expected File. Skipping cache hash loading.",
                        type(batch_results_file).__name__,
                    )
            except (FileNotFoundError, TypeError, AttributeError) as e:
                # No batch results or error loading - continue without cache hashes
                logger.info("Could not load batch results cache hashes: %s", e)

            # Separate ready bridges into cached and non-cached
            from app.bridge.analysis_cache import AnalysisCache

            cached_bridges_list = []
            non_cached_bridges_list = []
            cache = AnalysisCache()

            for bridge_entity, bridge_params in ready_bridges:
                bridge_id = bridge_entity.id
                # Check cache against CURRENT params to detect any parameter changes
                is_cached = check_idea_cache_status(bridge_params, bridge_id, batch_results_cache_hash=None)

                if is_cached:
                    cached_bridges_list.append((bridge_entity, bridge_params))
                else:
                    non_cached_bridges_list.append((bridge_entity, bridge_params))

            # Initialize results storage
            batch_results: dict[int, dict[str, Any]] = {}
            completed_count = 0
            failed_count = 0
            skipped_cached_count = 0
            total_non_cached_bridges = len(non_cached_bridges_list)
            total_bridges = len(cached_bridges_list) + total_non_cached_bridges
            current_bridge_position = 0

            # Process cached bridges first (load results directly without calculation)
            for i, (bridge_entity, bridge_params) in enumerate(cached_bridges_list):
                bridge_name = bridge_entity.name
                bridge_id = bridge_entity.id
                current_bridge_position = i + 1
                percentage = (current_bridge_position / total_bridges) * 100 if total_bridges > 0 else 0

                # Show progress for cached bridges
                progress_message(
                    message=f"Bridge {current_bridge_position}/{total_bridges}: {bridge_name}\nLaden gecachte resultaten...", percentage=percentage
                )

                try:
                    # Load cached results directly
                    idea_results = cache.get_cached_analysis(bridge_params, AnalysisType.IDEA, bridge_id)

                    if idea_results is None:
                        # Cache check said it exists but retrieval failed - treat as non-cached and calculate
                        logger.warning(
                            "Bridge %s (ID: %s): Cache check passed but retrieval failed, treating as non-cached",
                            bridge_name,
                            bridge_id,
                        )
                        non_cached_bridges_list.append((bridge_entity, bridge_params))
                        total_non_cached_bridges += 1
                        total_bridges = len(cached_bridges_list) + total_non_cached_bridges  # Update total
                        continue

                    # Extract UC summary from cached results
                    uc_summary = extract_uc_summary_from_idea_results(idea_results)

                    # Generate cache hash for this calculation to track cache status
                    # Note: Using private method _generate_input_hash for cache consistency
                    cache_hash = cache._generate_input_hash(bridge_params, AnalysisType.IDEA, None)  # noqa: SLF001

                    # Store success result with cached flag
                    batch_results[bridge_id] = {
                        "bridge_name": bridge_name,
                        "status": "Voltooid",
                        "max_uc": uc_summary.get("max_uc"),
                        "uc_status": uc_summary.get("status"),
                        "failed_checks": uc_summary.get("failed_checks", []),
                        "error": None,
                        "cache_hash": cache_hash,
                        "cached": True,  # Flag indicating this bridge used cached results
                    }
                    skipped_cached_count += 1
                    logger.info("Bridge %s (ID: %s): Loaded from cache. Max UC: %s", bridge_name, bridge_id, uc_summary.get("max_uc"))

                except Exception as e:
                    # Error loading cached results - treat as non-cached and calculate
                    logger.warning("Bridge %s (ID: %s): Error loading cached results: %s, treating as non-cached", bridge_name, bridge_id, e)
                    non_cached_bridges_list.append((bridge_entity, bridge_params))
                    total_non_cached_bridges += 1
                    total_bridges = len(cached_bridges_list) + total_non_cached_bridges  # Update total

            # Process non-cached bridges (run calculations)
            for i, (bridge_entity, bridge_params) in enumerate(non_cached_bridges_list):
                # CRITICAL: Check for cancellation before processing each bridge
                # This allows users to stop batch calculation between bridges
                try:
                    # Test if job is still active by accessing storage
                    # If job is cancelled, storage operations will raise an exception
                    _ = storage.get("batch_calculation_running", scope="entity")
                except FileNotFoundError:
                    # File not found - could be actual cancellation OR first iteration
                    # Only treat as cancellation if we've processed at least one bridge
                    if i > 0:
                        logger.info("Cancellation detected: batch_calculation_running flag deleted")
                        logger.info("Processed %d of %d bridges before cancellation", completed_count + failed_count, total_non_cached_bridges)

                        # Store partial results
                        if batch_results:
                            logger.info("Saving partial batch results before exit...")
                            with contextlib.suppress(Exception):
                                batch_results_file = serialize_batch_results(batch_results)
                                storage.set("batch_calculation_results", batch_results_file, scope="entity")
                                logger.info("Partial results saved successfully")

                        # Clear running flag
                        with contextlib.suppress(Exception):
                            storage.delete("batch_calculation_running", scope="entity")
                            logger.info("Cleared running flag")

                        # Show message to user (nice to have)
                        with contextlib.suppress(Exception):
                            UserMessage.info(
                                f"Batch calculation stopped. Processed {completed_count + failed_count} of {total_non_cached_bridges} bridges."
                            )

                        # Exit loop cleanly - return early with partial results
                        logger.info("Exiting batch calculation due to cancellation")
                        return
                    # First iteration and flag doesn't exist - this is normal, continue
                    logger.info("batch_calculation_running flag not found on first check - continuing (storage may be full or flag not set)")
                except Exception as storage_error:
                    # Storage error (likely full) - log but CONTINUE
                    logger.warning("Storage check failed (%s), continuing calculation in storage-free mode...", type(storage_error).__name__)
                    # Don't exit - keep calculating without storage

                bridge_name = bridge_entity.name
                bridge_id = bridge_entity.id
                # Calculate position relative to non-cached bridges only (for display)
                non_cached_position = i + 1
                # But keep overall percentage based on total bridges for batch progress
                overall_position = len(cached_bridges_list) + i + 1
                percentage = (overall_position / total_bridges) * 100 if total_bridges > 0 else 0

                # Show progress with bridge position (non-cached only) and stage
                progress_message(
                    message=f"Bridge {non_cached_position}/{total_non_cached_bridges}: {bridge_name}\nStarten berekening...", percentage=percentage
                )

                # Run calculation with error handling
                try:
                    # Create analysis context to pass bridge position info through the analysis layers
                    # Use non-cached position for display, but overall percentage for progress bar
                    analysis_context = {
                        "bridge_position": non_cached_position,
                        "total_bridges": total_non_cached_bridges,  # Only count bridges being calculated
                        "bridge_name": bridge_name,
                        "batch_percentage": percentage,  # Overall percentage including cached bridges
                    }

                    # Run IDEA analysis (which automatically runs SCIA first)
                    # Note: get_idea_analysis_results already has internal progress messages for SCIA/IDEA stages
                    idea_results = get_cached_analysis_results(
                        params=bridge_params,
                        analysis_type=AnalysisType.IDEA,
                        entity_id=bridge_id,
                        analysis_function=get_idea_analysis_results,
                        analysis_context=analysis_context,
                    )

                    if idea_results is None:
                        error_msg = "IDEA analyse gefaald of geen gecachte resultaten beschikbaar."
                        logger.error("Bridge %s (ID: %s): %s", bridge_name, bridge_id, error_msg)
                        raise UserError(error_msg)  # noqa: TRY301

                    # Extract UC summary
                    uc_summary = extract_uc_summary_from_idea_results(idea_results)

                    # Generate cache hash for this calculation to track cache status
                    # Note: Using private method _generate_input_hash for cache consistency
                    cache_hash = cache._generate_input_hash(bridge_params, AnalysisType.IDEA, None)  # noqa: SLF001

                    # Store success result with cache hash
                    batch_results[bridge_id] = {
                        "bridge_name": bridge_name,
                        "status": "Voltooid",
                        "max_uc": uc_summary.get("max_uc"),
                        "uc_status": uc_summary.get("status"),
                        "failed_checks": uc_summary.get("failed_checks", []),
                        "error": None,
                        "cache_hash": cache_hash,  # Store hash for cache status checking
                        "cached": False,  # Flag indicating this bridge was calculated (not cached)
                    }
                    completed_count += 1
                    logger.info("Bridge %s (ID: %s): Successfully calculated. Max UC: %s", bridge_name, bridge_id, uc_summary.get("max_uc"))

                    # Show completion progress
                    max_uc_value = uc_summary.get("max_uc", "N/A")
                    uc_display = f"{max_uc_value:.2f}" if isinstance(max_uc_value, (int, float)) else str(max_uc_value)
                    progress_message(
                        message=f"Bridge {current_bridge_position}/{total_bridges}: {bridge_name}\nBerekening voltooid (Max UC: {uc_display})",
                        percentage=percentage,
                    )

                except Exception as e:
                    # Log full error details for debugging
                    error_type = type(e).__name__
                    error_message = str(e)
                    error_traceback = traceback.format_exc()

                    logger.exception("Bridge %s (ID: %s): Calculation failed", bridge_name, bridge_id)

                    # Store error result with detailed error message
                    # Truncate traceback if too long, but keep first line (most important)
                    short_error = f"{error_type}: {error_message}\n(...)" if len(error_traceback) > 500 else f"{error_type}: {error_message}"

                    batch_results[bridge_id] = {
                        "bridge_name": bridge_name,
                        "status": "Gefaald",
                        "max_uc": None,
                        "uc_status": "ERROR",
                        "failed_checks": [],
                        "error": short_error,
                        "cached": False,
                    }
                    failed_count += 1

                    # Show error progress
                    progress_message(
                        message=f"Bridge {current_bridge_position}/{total_bridges}: {bridge_name}\nBerekening gefaald: {error_type}",
                        percentage=percentage,
                    )

            # Store aggregated results in parent entity Storage (storage-free fallback mode)
            try:
                batch_results_file = serialize_batch_results(batch_results)
                storage.set("batch_calculation_results", batch_results_file, scope="entity")
                logger.info("Batch results saved to storage successfully")
            except Exception as storage_error:
                logger.warning("Failed to save batch results to storage (%s) - results available in this session only", type(storage_error).__name__)
                # Continue - results are still in memory for this job
                # User can see them in current view, just won't persist

            # Build completion message with skipped cached bridges information
            total_processed = completed_count + failed_count + skipped_cached_count
            message_parts = []

            if skipped_cached_count > 0:
                message_parts.append(f"{skipped_cached_count} overgeslagen (gecached)")

            if completed_count > 0:
                message_parts.append(f"{completed_count} berekend")

            if failed_count > 0:
                message_parts.append(f"{failed_count} gefaald")

            status_details = ", ".join(message_parts) if message_parts else "geen bruggen"

            # Show completion message with appropriate level based on results
            if failed_count > 0:
                if completed_count == 0 and skipped_cached_count == 0:
                    # All bridges failed - show error message
                    completion_msg = (
                        f"❌ Batchberekening voltooid: Alle {failed_count} bruggen gefaald. "
                        f"Bekijk de foutmeldingen in de 'Batch Berekening Resultaten' tabel voor details."
                    )
                else:
                    # Some bridges failed - show warning message
                    completion_msg = (
                        f"⚠️ Batchberekening voltooid: {status_details} van {total_processed} bruggen. "
                        f"Bekijk de resultaten in de 'Batch Berekening Resultaten' tabel voor details."
                    )
            else:
                # All bridges succeeded (calculated or cached)
                completion_msg = (
                    f"✅ Batchberekening voltooid: {status_details} van {total_processed} bruggen. "
                    f"Bekijk de resultaten in de 'Batch Berekening Resultaten' tabel."
                )

            # Show completion message to user
            UserMessage.success(completion_msg)
            logger.info(
                "Batch calculation completed: %d calculated, %d skipped (cached), %d failed out of %d bridges",
                completed_count,
                skipped_cached_count,
                failed_count,
                total_processed,
            )
        finally:
            # Always try to clear running flag, even if an error occurred
            try:
                storage.delete("batch_calculation_running", scope="entity")
                logger.info("Cleared batch_calculation_running flag")
            except Exception as cleanup_error:
                logger.warning("Failed to clear running flag (%s) - not critical", type(cleanup_error).__name__)
                # Don't fail - this is cleanup, storage might be full
