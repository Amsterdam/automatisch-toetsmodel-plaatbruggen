"""Batch calculation component for OverviewBridgesController."""

import contextlib
import traceback
from typing import Any

try:
    from viktor import ChatResult
except ImportError:  # pragma: no cover - fallback for local test environments
    ChatResult = None  # type: ignore[assignment, misc]


import viktor.api_v1 as api
from viktor.core import Color, Storage, UserMessage, progress_message
from viktor.errors import UserError
from viktor.parametrization import Parametrization
from viktor.views import TableCell, TableResult, TableView

from app.bridge.analysis_cache import STORAGE_WARNING_MARKER_KEY, _get_analysis_cache, get_cached_analysis_results, get_idea_analysis_results
from src.common.constants.technical import AnalysisType

from .llm import generate_batch_chat_response
from .utils import (
    calculate_estimated_batch_time,
    check_idea_cache_status,
    deserialize_batch_results,
    extract_uc_summary_from_idea_results,
    generate_bridge_report_url,
    record_batch_last_run_timestamp,
    serialize_batch_results,
    validate_bridge_for_calculation,
)


def _load_batch_results_from_storage(storage: Storage) -> dict[int, dict[str, Any]] | None:
    """
    Load batch results from storage, handling various error cases.

    :param storage: Storage instance
    :type storage: Storage
    :returns: Batch results dictionary or None if not available
    :rtype: dict[int, dict[str, Any]] | None
    """
    from viktor.core import File

    try:
        batch_results_file = storage.get("batch_calculation_results", scope="entity")

        if isinstance(batch_results_file, bool):
            print("Warning: Found boolean value in storage for 'batch_calculation_results'. Deleting invalid entry.")
            with contextlib.suppress(Exception):
                storage.delete("batch_calculation_results", scope="entity")
            return None
        if isinstance(batch_results_file, File):
            return deserialize_batch_results(batch_results_file)
        print(f"Warning: Unexpected type in storage for 'batch_calculation_results': {type(batch_results_file).__name__}, expected File")
        return None  # noqa: TRY300
    except FileNotFoundError:
        return None
    except (TypeError, AttributeError) as e:
        print(f"Warning: Error deserializing batch results: {e}")
        return None


def _check_should_trigger_calculation(batch_results: dict[int, dict[str, Any]] | None, entity_id: int) -> bool:  # noqa: C901
    """
    Check if batch calculation should be triggered.

    :param batch_results: Existing batch results or None
    :type batch_results: dict[int, dict[str, Any]] | None
    :param entity_id: Overview Bridges entity ID
    :type entity_id: int
    :returns: True if calculation should be triggered
    :rtype: bool
    """
    if not batch_results or len(batch_results) == 0:
        print("Info: No batch results found - will trigger batch calculation...")
        return True

    try:
        viktor_api = api.API()
        parent_entity = viktor_api.get_entity(entity_id)
        bridge_entities = parent_entity.children(entity_type_names=["Bridge"])

        from viktor.core import File

        if isinstance(batch_results, File):
            print("Info: batch_results is still a File, deserializing...")
            batch_results = deserialize_batch_results(batch_results)
        elif not isinstance(batch_results, dict):
            print(f"Warning: batch_results is not a dict or File: {type(batch_results).__name__}. Cannot extract cache hashes.")
            return True

        batch_results_cache_hashes: dict[int, str] = {}
        if isinstance(batch_results, dict):
            for bid, result in batch_results.items():
                if "cache_hash" in result:
                    batch_results_cache_hashes[bid] = result["cache_hash"]

        ready_bridges_needing_calculation = 0
        for bridge_entity in bridge_entities:
            bridge_params = bridge_entity.last_saved_params
            bridge_id = bridge_entity.id

            is_ready, _, _ = validate_bridge_for_calculation(bridge_params, bridge_entity)

            if is_ready:
                batch_hash = batch_results_cache_hashes.get(bridge_id)
                is_cached = check_idea_cache_status(bridge_params, bridge_id, batch_hash)

                if not is_cached:
                    ready_bridges_needing_calculation += 1

        if ready_bridges_needing_calculation > 0:
            print(f"Info: Found {ready_bridges_needing_calculation} ready bridges needing calculation - will trigger batch calculation...")
            return True
    except Exception as e:
        print(f"Warning: Error checking for ready bridges: {e} - will not auto-trigger calculation")

    return False


def _trigger_batch_calculation_with_cleanup(
    component: "BatchCalculationComponent",
    storage: Storage,
    params: Parametrization,
    entity_id: int,
    **kwargs: Any,  # noqa: ANN401
) -> dict[int, dict[str, Any]] | None:
    """
    Trigger batch calculation with proper cleanup and result reloading.

    :param component: BatchCalculationComponent instance
    :type component: BatchCalculationComponent
    :param storage: Storage instance
    :type storage: Storage
    :param params: Overview Bridges parametrization object
    :type params: Parametrization
    :param entity_id: Overview Bridges entity ID
    :type entity_id: int
    :param kwargs: Additional arguments
    :returns: Batch results after calculation or None
    :rtype: dict[int, dict[str, Any]] | None
    """
    from viktor.core import File

    try:
        try:
            running_file = storage.get("batch_calculation_running", scope="entity")
            if isinstance(running_file, File):
                running_value = running_file.getvalue()
                if running_value == "running":
                    print("Info: Found running flag - clearing to allow new calculation (previous may have been cancelled)")
                    with contextlib.suppress(Exception):
                        storage.delete("batch_calculation_running", scope="entity")
        except FileNotFoundError:
            pass

        storage.set("batch_calculation_running", File.from_data("running"), scope="entity")

        print("Info: Triggering batch calculation...")
        component.run_batch_calculation(params, entity_id, **kwargs)

        with contextlib.suppress(Exception):
            storage.delete("batch_calculation_running", scope="entity")

        return _load_batch_results_from_storage(storage)
    except Exception as e:
        with contextlib.suppress(Exception):
            storage.delete("batch_calculation_running", scope="entity")
        print(f"Error: Error triggering batch calculation: {e}")
        print(traceback.format_exc())
        raise


def _build_table_result_from_batch_results(batch_results: dict[int, dict[str, Any]]) -> TableResult:
    """
    Build TableResult from batch results dictionary.

    :param batch_results: Batch results dictionary
    :type batch_results: dict[int, dict[str, Any]]
    :returns: TableResult with formatted data
    :rtype: TableResult
    """
    bridge_data_list = []
    for bridge_id, result in batch_results.items():
        bridge_name = result.get("bridge_name", "Onbekend")
        status = result.get("status", "Onbekend")
        max_uc = result.get("max_uc")
        uc_status = result.get("uc_status", "N/A")
        failed_checks = result.get("failed_checks", [])
        error = result.get("error")

        max_uc_str = f"{max_uc:.2f}" if max_uc is not None else "N/A"
        failed_checks_str = str(len(failed_checks)) if failed_checks else "0"
        report_url = generate_bridge_report_url(bridge_id)

        if status == "Gefaald":
            if error:
                status_display = TableCell(
                    f"{status}: {error[:100]}{'...' if len(error) > 100 else ''}",
                    background_color=Color(255, 200, 200),
                )
            else:
                status_display = TableCell(status, background_color=Color(255, 200, 200))
        else:
            status_display = status

        bridge_data_list.append((bridge_name, [status_display, max_uc_str, uc_status, failed_checks_str, report_url], uc_status, max_uc_str))

    def sort_key(item: tuple) -> tuple:
        bridge_name, data_row, uc_status, max_uc_str = item
        status_text = str(data_row[0])
        status_priority = 0 if "Gefaald" in status_text else 1 if uc_status == "FAILED" else 2
        max_uc_value = float(max_uc_str) if max_uc_str != "N/A" else -1.0
        return (status_priority, -max_uc_value, bridge_name)

    bridge_data_list.sort(key=sort_key)

    row_headers = []
    table_data = []
    for bridge_name, data_row, _, _ in bridge_data_list:
        row_headers.append(bridge_name)
        table_data.append(data_row)

    headers = ["Berekening Status", "Max UC", "UC Status", "Gefaalde controles", "Rapport"]
    return TableResult(table_data, column_headers=headers, row_headers=row_headers)


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
                print("Warning: Found boolean value in storage for 'batch_calculation_results'. Deleting invalid entry.")
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

            # First try to get from batch_results (preferred source)
            if batch_results and bridge_id in batch_results:
                result = batch_results[bridge_id]
                max_uc = result.get("max_uc")
                uc_status = result.get("uc_status", "N/A")
                failed_checks = result.get("failed_checks", [])

                max_uc_str = f"{max_uc:.2f}" if max_uc is not None else "-"
                uc_status_str = uc_status if uc_status != "N/A" else "-"
                failed_checks_str = str(len(failed_checks)) if failed_checks else "0"

            # Fallback: if cache says "actueel" but no batch_results, try reading entity cache
            elif is_cached:
                try:
                    print(f"Info: Bridge {bridge_id}: Cache marked as valid but no batch_results entry - reading from entity cache")
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

                        print(f"Info: Bridge {bridge_id}: Successfully read from entity cache - Max UC: {max_uc_str}")
                    else:
                        print(f"Warning: Bridge {bridge_id}: Cache marked valid but get_cached_analysis returned None - showing '-'")
                except FileNotFoundError:
                    print(f"Warning: Bridge {bridge_id}: Cache file not found despite marker - showing '-'")
                except Exception as e:
                    print(f"Warning: Bridge {bridge_id}: Failed to read entity cache: {type(e).__name__} - showing '-'")

            # Store data with sort priority
            bridge_data_list.append(
                (
                    sort_priority,
                    bridge_name,
                    bridge_id,
                    [status_display, missing_fields_str, max_uc_str, uc_status_str, failed_checks_str],
                    uc_status_str,
                    max_uc_str if max_uc_str != "-" else "0.0",
                )
            )

        # Sort: ready but not cached first, then cached, then not ready
        # Within each group, sort by max UC descending, then by bridge name
        def sort_key(item: tuple) -> tuple:
            priority, bridge_name, bridge_id, data_row, uc_status, max_uc = item
            max_uc_value = float(max_uc) if max_uc not in {"-", "0.0"} else -1.0
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
            ],
            [
                TableCell(time_estimate, text_style="bold"),
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
                ]
            )

        summary_row_headers = ["Status", "Geschatte tijd"]
        if storage_warning_message:
            summary_row_headers.append("Opslagwaarschuwing")

        # Extract bridge data
        bridge_row_headers = []
        bridge_table_data = []
        for _, bridge_name, _bridge_id, data_row, _, _ in bridge_data_list:
            # Keep bridge name as string in row header
            bridge_row_headers.append(bridge_name)
            # Use data row directly (VIKTOR TableCell doesn't support HTML links or sticky rows)
            # NOTE: For improved UX, consider using WebView instead of TableView:
            # - Clickable entity links to navigate to bridges or reports
            # - Sticky/frozen summary rows (always visible when scrolling)
            # See: https://docs.viktor.ai/docs/create-apps/results-and-visualizations/data-and-tables/
            # and: https://docs.viktor.ai/sdk/api/views/#_TableResult
            bridge_table_data.append(data_row)

        # Combine summary and bridge data
        final_table_data = summary_data + bridge_table_data
        final_row_headers = summary_row_headers + bridge_row_headers

        # Define column headers
        headers = ["Status", "Ontbrekende velden", "Max UC", "UC Status", "Gefaalde controles"]

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
                    print("Warning: Found boolean value in storage for 'batch_calculation_results'. Deleting invalid entry.")
                    with contextlib.suppress(Exception):
                        storage.delete("batch_calculation_results", scope="entity")
                elif isinstance(batch_results_file, File):
                    print("Info: Deserializing batch results file...")
                    loaded_batch_results = deserialize_batch_results(batch_results_file)
                    # Extract cache hashes from batch results
                    if isinstance(loaded_batch_results, dict):
                        for bid, result in loaded_batch_results.items():
                            if "cache_hash" in result:
                                batch_results_cache_hashes[bid] = result["cache_hash"]
                else:
                    print(
                        f"Warning: Unexpected type in storage for 'batch_calculation_results' in run_batch_calculation: {type(batch_results_file).__name__}, "
                        "expected File. Skipping cache hash loading."
                    )
            except (FileNotFoundError, TypeError, AttributeError) as e:
                # No batch results or error loading - continue without cache hashes
                print(f"Info: Could not load batch results cache hashes: {e}")

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
                        print(f"Warning: Bridge {bridge_name} (ID: {bridge_id}): Cache check passed but retrieval failed, treating as non-cached")
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
                        "uc_breakdown": uc_summary.get("uc_breakdown"),
                        "error": None,
                        "cache_hash": cache_hash,
                        "cached": True,  # Flag indicating this bridge used cached results
                    }
                    skipped_cached_count += 1
                    print(f"Info: Bridge {bridge_name} (ID: {bridge_id}): Loaded from cache. Max UC: {uc_summary.get('max_uc')}")

                except Exception as e:
                    # Error loading cached results - treat as non-cached and calculate
                    print(f"Warning: Bridge {bridge_name} (ID: {bridge_id}): Error loading cached results: {e}, treating as non-cached")
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
                        print("Info: Cancellation detected: batch_calculation_running flag deleted")
                        print(f"Info: Processed {completed_count + failed_count} of {total_non_cached_bridges} bridges before cancellation")

                        # Store partial results
                        if batch_results:
                            print("Info: Saving partial batch results before exit...")
                            try:
                                batch_results_file = serialize_batch_results(batch_results)
                                storage.set("batch_calculation_results", batch_results_file, scope="entity")
                                record_batch_last_run_timestamp(storage)
                                print("Info: Partial results saved successfully")
                                # Record successful partial save
                                from app.overview_bridges.batch_calculation.utils import record_storage_status

                                record_storage_status(
                                    storage,
                                    success=True,
                                    message="Partial batch results saved (interrupted calculation)",
                                    details={"partial": True, "bridges_processed": len(batch_results)},
                                )
                            except Exception as partial_save_error:
                                # Record failed partial save
                                from app.overview_bridges.batch_calculation.utils import record_storage_status

                                record_storage_status(
                                    storage,
                                    success=False,
                                    message=f"Failed to save partial results: {type(partial_save_error).__name__}",
                                    details={"partial": True, "error_type": type(partial_save_error).__name__},
                                )

                        # Clear running flag
                        with contextlib.suppress(Exception):
                            storage.delete("batch_calculation_running", scope="entity")
                            print("Info: Cleared running flag")

                        # Show message to user (nice to have)
                        with contextlib.suppress(Exception):
                            UserMessage.info(
                                f"Batch calculation stopped. Processed {completed_count + failed_count} of {total_non_cached_bridges} bridges."
                            )

                        # Exit loop cleanly - return early with partial results
                        print("Info: Exiting batch calculation due to cancellation")
                        return
                    # First iteration and flag doesn't exist - this is normal, continue
                    print("Info: batch_calculation_running flag not found on first check - continuing (storage may be full or flag not set)")
                except Exception as storage_error:
                    # Storage error (likely full) - log but CONTINUE
                    print(f"Warning: Storage check failed ({type(storage_error).__name__}), continuing calculation in storage-free mode...")
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
                        print(f"Error: Bridge {bridge_name} (ID: {bridge_id}): {error_msg}")
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
                        "uc_breakdown": uc_summary.get("uc_breakdown"),
                        "error": None,
                        "cache_hash": cache_hash,  # Store hash for cache status checking
                        "cached": False,  # Flag indicating this bridge was calculated (not cached)
                    }
                    completed_count += 1
                    print(f"Info: Bridge {bridge_name} (ID: {bridge_id}): Successfully calculated. Max UC: {uc_summary.get('max_uc')}")

                    # Show completion progress
                    max_uc_value = uc_summary.get("max_uc", "N/A")
                    uc_display = f"{max_uc_value:.2f}" if isinstance(max_uc_value, int | float) else str(max_uc_value)
                    progress_message(
                        message=f"Bridge {current_bridge_position}/{total_bridges}: {bridge_name}\nBerekening voltooid (Max UC: {uc_display})",
                        percentage=percentage,
                    )

                except Exception as e:
                    # Log full error details for debugging
                    error_type = type(e).__name__
                    error_message = str(e)
                    error_traceback = traceback.format_exc()

                    print(f"Error: Bridge {bridge_name} (ID: {bridge_id}): Calculation failed")
                    print(error_traceback)

                    # Store error result with detailed error message
                    # Truncate traceback if too long, but keep first line (most important)
                    short_error = f"{error_type}: {error_message}\n(...)" if len(error_traceback) > 500 else f"{error_type}: {error_message}"

                    batch_results[bridge_id] = {
                        "bridge_name": bridge_name,
                        "status": "Gefaald",
                        "max_uc": None,
                        "uc_status": "ERROR",
                        "failed_checks": [],
                        "uc_breakdown": None,
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
            # Calculate total_processed before try block (needed for storage status recording)
            total_processed = completed_count + failed_count + skipped_cached_count
            try:
                batch_results_file = serialize_batch_results(batch_results)
                storage.set("batch_calculation_results", batch_results_file, scope="entity")
                record_batch_last_run_timestamp(storage)
                print("Info: Batch results saved to storage successfully")
                # Record successful storage operation
                from app.overview_bridges.batch_calculation.utils import record_storage_status

                record_storage_status(
                    storage,
                    success=True,
                    message="Batch results saved successfully",
                    details={
                        "bridges_calculated": completed_count,
                        "bridges_failed": failed_count,
                        "bridges_skipped": skipped_cached_count,
                        "total_bridges": total_processed,
                    },
                )
            except Exception as storage_error:
                error_type = type(storage_error).__name__
                error_message = str(storage_error)
                print(f"Warning: Failed to save batch results to storage ({error_type}) - results available in this session only")
                # Record failed storage operation
                from app.overview_bridges.batch_calculation.utils import record_storage_status

                record_storage_status(
                    storage,
                    success=False,
                    message=f"Storage operation failed: {error_type}",
                    details={
                        "error_type": error_type,
                        "error_message": error_message,
                        "bridges_calculated": completed_count,
                        "bridges_failed": failed_count,
                        "bridges_skipped": skipped_cached_count,
                    },
                )
                # Continue - results are still in memory for this job
                # User can see them in current view, just won't persist

            # Build completion message with skipped cached bridges information
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
            print(
                f"Info: Batch calculation completed: {completed_count} calculated, {skipped_cached_count} skipped (cached), {failed_count} failed out of {total_processed} bridges"
            )
        finally:
            # Always try to clear running flag, even if an error occurred
            try:
                storage.delete("batch_calculation_running", scope="entity")
                print("Info: Cleared batch_calculation_running flag")
            except Exception as cleanup_error:
                print(f"Warning: Failed to clear running flag ({type(cleanup_error).__name__}) - not critical")
                # Don't fail - this is cleanup, storage might be full

    @TableView("Start berekening / Weergeven resultaten", duration_guess=6)
    def view_batch_results(self, params: Parametrization, entity_id: int, **kwargs) -> TableResult:
        """
        Display batch calculation results with UC values and report links.

        Automatically triggers batch calculation if:
        - No results exist, OR
        - There are ready bridges that need calculation (not cached).

        Shows status, max UC, pass/fail, and clickable links to individual bridge reports.
        Results are sorted by status (failed first) then by max UC (descending).

        :param params: Overview Bridges parametrization object
        :type params: Parametrization
        :param entity_id: Entity ID of the Overview Bridges entity
        :type entity_id: int
        :param kwargs: Additional arguments
        :returns: TableResult with batch calculation results
        :rtype: TableResult
        """
        storage = Storage()
        batch_results = _load_batch_results_from_storage(storage)

        should_trigger_calculation = _check_should_trigger_calculation(batch_results, entity_id)

        if should_trigger_calculation:
            try:
                batch_results = _trigger_batch_calculation_with_cleanup(self, storage, params, entity_id, **kwargs)
            except Exception as e:
                return TableResult(
                    [["Fout bij starten batchberekening", f"{type(e).__name__}: {str(e)[:100]}", "", "", ""]],
                    column_headers=["Berekening Status", "Max UC", "UC Status", "Gefaalde controles", "Rapport"],
                    row_headers=["ERROR"],
                )

        if not batch_results or len(batch_results) == 0:
            return TableResult(
                [["Geen resultaten beschikbaar", "Ververs deze pagina om opnieuw te proberen", "", "", ""]],
                column_headers=["Berekening Status", "Max UC", "UC Status", "Gefaalde controles", "Rapport"],
                row_headers=["INFO"],
            )

        return _build_table_result_from_batch_results(batch_results)

    def chat_batch_results(self, params: Parametrization, entity_id: int, **kwargs) -> ChatResult:  # noqa: ARG002
        """
        Provide a chat response summarizing batch calculation insights via OpenAI GPT-5 Nano.

        :param params: Overview Bridges parametrization object
        :type params: Parametrization
        :param entity_id: Entity ID of the Overview Bridges entity
        :type entity_id: int
        :returns: ChatResult with assistant reply
        :rtype: ChatResult
        """
        conversation = getattr(getattr(params, "batch_calculation", None), "batch_results_chat", None)
        if conversation is None:
            raise UserError("Chatveld niet beschikbaar op deze entiteit.")

        messages = conversation.get_messages() if conversation else []

        if ChatResult is None:
            raise UserError("ChatResult is niet beschikbaar in deze omgeving.")

        try:
            answer = generate_batch_chat_response(entity_id, messages)
        except UserError:
            # Re-raise UserError as-is (it already has appropriate messages)
            raise
        except Exception as e:
            print(f"Error: Chat response generation failed: {e}")
            print(traceback.format_exc())
            return ChatResult(
                conversation,
                "Het is niet gelukt om een antwoord op te halen van de AI-service. Probeer het later nog eens.",
            )

        return ChatResult(conversation, answer)
