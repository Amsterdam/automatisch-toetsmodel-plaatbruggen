"""Batch calculation component for OverviewBridgesController."""

import traceback
from typing import Any

import viktor.api_v1 as api
from app.bridge.analysis_cache import get_cached_analysis_results, get_idea_analysis_results
from src.common.constants.technical import AnalysisType
from viktor.core import Color, Storage, UserMessage, progress_message
from viktor.errors import UserError
from viktor.parametrization import Parametrization
from viktor.views import TableCell, TableResult, TableView

from .utils import (
    calculate_estimated_batch_time,
    check_idea_cache_status,
    deserialize_batch_results,
    extract_uc_summary_from_idea_results,
    generate_bridge_report_url,
    serialize_batch_results,
    validate_bridge_for_calculation,
)


class BatchCalculationComponent:
    """Component providing batch calculation functionality for multiple bridges."""

    @TableView("Statusoverzicht", duration_guess=1)
    def view_batch_readiness(self, params: Parametrization, entity_id: int, **kwargs) -> TableResult:  # noqa: ARG002
        """
        Display table showing which bridges are ready for batch calculation.

        Shows validation status, missing fields, and dynamic time estimate based on
        actual count of ready bridges.

        :param params: Overview Bridges parametrization object
        :type params: Parametrization
        :param entity_id: Entity ID of the Overview Bridges entity
        :type entity_id: int
        :param kwargs: Additional arguments
        :returns: TableResult with bridge readiness information
        :rtype: TableResult
        """
        # Get all Bridge child entities
        viktor_api = api.API()
        try:
            parent_entity = viktor_api.get_entity(entity_id)
            bridge_entities = parent_entity.children(entity_type_names=["Bridge"])
        except Exception as e:
            raise UserError(f"Fout bij ophalen van bruggen: {e}")

        # Initialize counters
        total_bridges = len(bridge_entities)
        ready_bridges = 0
        cached_bridges = 0
        non_cached_ready_bridges = 0
        bridge_data_list = []

        # Load batch results to get cache hashes if available
        storage = Storage()
        batch_results_cache_hashes: dict[int, str] = {}
        try:
            batch_results_file = storage.get("batch_calculation_results", scope="entity")
            
            # Validate storage contents before deserializing
            from viktor.core import File
            
            # Check for boolean first (most common invalid type)
            if isinstance(batch_results_file, bool):
                print(f"WARNING: Found boolean value in storage for 'batch_calculation_results' in view_batch_readiness. Deleting invalid entry.")
                try:
                    storage.delete("batch_calculation_results", scope="entity")
                    print("INFO: Deleted invalid boolean entry from storage")
                except Exception as del_e:
                    print(f"WARNING: Could not delete invalid storage entry: {del_e}")
            elif isinstance(batch_results_file, File):
                batch_results = deserialize_batch_results(batch_results_file)
                # Extract cache hashes from batch results
                if isinstance(batch_results, dict):
                    for bid, result in batch_results.items():
                        if "cache_hash" in result:
                            batch_results_cache_hashes[bid] = result["cache_hash"]
            else:
                print(f"WARNING: Unexpected type in storage for 'batch_calculation_results' in view_batch_readiness: {type(batch_results_file).__name__}, expected File")
        except (FileNotFoundError, TypeError, AttributeError):
            # No batch results or error loading - continue without cache hashes
            pass

        # Validate each bridge and collect data
        for bridge_entity in bridge_entities:
            bridge_params = bridge_entity.last_saved_params
            bridge_name = bridge_entity.name
            bridge_id = bridge_entity.id

            # Validate bridge readiness
            is_ready, missing_fields, _ = validate_bridge_for_calculation(bridge_params, bridge_entity)

            # Check cache status for this bridge (with batch cache hash if available)
            batch_hash = batch_results_cache_hashes.get(bridge_id)
            is_cached = check_idea_cache_status(bridge_params, bridge_id, batch_hash)
            
            if is_ready:
                ready_bridges += 1
                if is_cached:
                    cached_bridges += 1
                else:
                    non_cached_ready_bridges += 1
                missing_fields_str = ""
            else:
                # Format missing fields more cleanly
                if len(missing_fields) <= 2:
                    missing_fields_str = ", ".join(missing_fields)
                else:
                    missing_fields_str = f"{', '.join(missing_fields[:2])} (+{len(missing_fields) - 2} meer)"

            # Determine status display based on readiness and cache status
            if is_ready:
                if is_cached:
                    # Bridge has cached results (green background)
                    status_display = TableCell("✓ Berekening actueel", background_color=Color(144, 238, 144))
                    sort_priority = 2  # Second priority (after ready but not cached)
                else:
                    # Ready but not cached - ready to be calculated (yellow background)
                    status_display = TableCell("✓ Klaar voor berekening", background_color=Color(255, 255, 0))
                    sort_priority = 1  # First priority (top of list)
            else:
                # Not ready - missing fields (red background)
                status_display = TableCell("✗ Niet klaar voor berekening", background_color=Color(255, 200, 200))
                sort_priority = 3  # Third priority (bottom of list)

            # Store data with bridge name for sorting
            # Note: bridge_name will be used as row header, so we don't include it in data
            # Tuple: (sort_priority, bridge_name, [status_display, missing_fields_str])
            bridge_data_list.append((sort_priority, bridge_name, [status_display, missing_fields_str]))

        # Sort: ready but not cached first (priority 1), then cached (priority 2), then not ready (priority 3)
        # Within each group, sort by bridge name
        bridge_data_list.sort(key=lambda x: (x[0], x[1]))

        # Calculate time estimate based on non-cached ready bridges only
        time_estimate = calculate_estimated_batch_time(non_cached_ready_bridges)

        # Build summary rows (cleaner formatting without separator)
        # Use styling for summary rows to make them stand out
        status_text = f"{ready_bridges} van {total_bridges} gereed • {cached_bridges} berekening actueel"

        summary_data = [
            [
                TableCell(status_text, text_style="bold"),
                "",
            ],
            [
                TableCell(time_estimate, text_style="bold"),
                "",
            ],
        ]
        summary_row_headers = ["Status", "Geschatte tijd"]

        # Extract bridge data and row headers separately
        bridge_row_headers = []
        bridge_table_data = []
        for _, bridge_name, data_row in bridge_data_list:
            bridge_row_headers.append(bridge_name)
            bridge_table_data.append(data_row)

        # Combine summary and bridge data
        final_table_data = summary_data + bridge_table_data
        final_row_headers = summary_row_headers + bridge_row_headers

        # Define column headers (removed "Brug" since it's now in row headers)
        headers = ["Status", "Ontbrekende velden"]

        return TableResult(final_table_data, column_headers=headers, row_headers=final_row_headers)

    def run_batch_calculation(self, params: Parametrization, entity_id: int, **kwargs) -> None:  # noqa: ARG002
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
                    print(f"WARNING: Found boolean value in storage for 'batch_calculation_results'. Deleting invalid entry.")
                    try:
                        storage.delete("batch_calculation_results", scope="entity")
                        print("INFO: Deleted invalid boolean entry from storage")
                    except Exception as del_e:
                        print(f"WARNING: Could not delete invalid storage entry: {del_e}")
                elif isinstance(batch_results_file, File):
                    print("INFO: Deserializing batch results file...")
                    batch_results = deserialize_batch_results(batch_results_file)
                    # Extract cache hashes from batch results
                    if isinstance(batch_results, dict):
                        for bid, result in batch_results.items():
                            if "cache_hash" in result:
                                batch_results_cache_hashes[bid] = result["cache_hash"]
                else:
                    print(f"WARNING: Unexpected type in storage for 'batch_calculation_results' in run_batch_calculation: {type(batch_results_file).__name__}, expected File. Skipping cache hash loading.")
            except (FileNotFoundError, TypeError, AttributeError) as e:
                # No batch results or error loading - continue without cache hashes
                print(f"INFO: Could not load batch results cache hashes: {e}")
                pass

            # Separate ready bridges into cached and non-cached
            from app.bridge.analysis_cache import AnalysisCache
            
            cached_bridges_list = []
            non_cached_bridges_list = []
            cache = AnalysisCache()
            
            for bridge_entity, bridge_params in ready_bridges:
                bridge_id = bridge_entity.id
                batch_hash = batch_results_cache_hashes.get(bridge_id)
                is_cached = check_idea_cache_status(bridge_params, bridge_id, batch_hash)
                
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
                    message=f"Bridge {current_bridge_position}/{total_bridges}: {bridge_name}\nLaden gecachte resultaten...",
                    percentage=percentage
                )

                try:
                    # Load cached results directly
                    idea_results = cache.get_cached_analysis(bridge_params, AnalysisType.IDEA, bridge_id)
                    
                    if idea_results is None:
                        # Cache check said it exists but retrieval failed - treat as non-cached and calculate
                        print(f"WARNING: Bridge {bridge_name} (ID: {bridge_id}): Cache check passed but retrieval failed, treating as non-cached")
                        non_cached_bridges_list.append((bridge_entity, bridge_params))
                        total_non_cached_bridges += 1
                        total_bridges = len(cached_bridges_list) + total_non_cached_bridges  # Update total
                        continue

                    # Extract UC summary from cached results
                    uc_summary = extract_uc_summary_from_idea_results(idea_results)

                    # Generate cache hash for this calculation to track cache status
                    cache_hash = cache._generate_input_hash(bridge_params, AnalysisType.IDEA, None)

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
                    print(f"INFO: Bridge {bridge_name} (ID: {bridge_id}): Loaded from cache. Max UC: {uc_summary.get('max_uc')}")

                except Exception as e:
                    # Error loading cached results - treat as non-cached and calculate
                    print(f"WARNING: Bridge {bridge_name} (ID: {bridge_id}): Error loading cached results: {e}, treating as non-cached")
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
                except Exception as cancellation_error:
                    # Job cancelled/context invalid - save partial results and exit
                    print(f"INFO: Cancellation detected: {cancellation_error}")
                    print(f"INFO: Processed {completed_count + failed_count} of {total_non_cached_bridges} bridges before cancellation")
                    
                    # Store partial results
                    if batch_results:
                        print("INFO: Saving partial batch results before exit...")
                        try:
                            batch_results_file = serialize_batch_results(batch_results)
                            storage.set("batch_calculation_results", batch_results_file, scope="entity")
                            print("INFO: Partial results saved successfully")
                        except Exception as save_error:
                            print(f"WARNING: Could not save partial results: {save_error}")
                    
                    # Clear running flag
                    try:
                        storage.delete("batch_calculation_running", scope="entity")
                        print("INFO: Cleared running flag")
                    except Exception:
                        pass  # Storage might be unavailable during cancellation
                    
                    # Show message to user (nice to have)
                    try:
                        UserMessage.info(f"Batch calculation stopped. Processed {completed_count + failed_count} of {total_non_cached_bridges} bridges.")
                    except Exception:
                        pass  # UserMessage might not be available during cancellation
                    
                    # Exit loop cleanly - return early with partial results
                    print("INFO: Exiting batch calculation due to cancellation")
                    return
                
                bridge_name = bridge_entity.name
                bridge_id = bridge_entity.id
                # Calculate position relative to non-cached bridges only (for display)
                non_cached_position = i + 1
                # But keep overall percentage based on total bridges for batch progress
                overall_position = len(cached_bridges_list) + i + 1
                percentage = (overall_position / total_bridges) * 100 if total_bridges > 0 else 0

                # Show progress with bridge position (non-cached only) and stage
                progress_message(
                    message=f"Bridge {non_cached_position}/{total_non_cached_bridges}: {bridge_name}\nStarten berekening...",
                    percentage=percentage
                )

                # Run calculation with error handling
                try:
                    # Create analysis context to pass bridge position info through the analysis layers
                    # Use non-cached position for display, but overall percentage for progress bar
                    analysis_context = {
                        "bridge_position": non_cached_position,
                        "total_bridges": total_non_cached_bridges,  # Only count bridges being calculated
                        "bridge_name": bridge_name,
                        "batch_percentage": percentage  # Overall percentage including cached bridges
                    }
                    
                    # Run IDEA analysis (which automatically runs SCIA first)
                    # Note: get_idea_analysis_results already has internal progress messages for SCIA/IDEA stages
                    idea_results = get_cached_analysis_results(
                        params=bridge_params, 
                        analysis_type=AnalysisType.IDEA, 
                        entity_id=bridge_id, 
                        analysis_function=get_idea_analysis_results,
                        analysis_context=analysis_context
                    )

                    if idea_results is None:
                        error_msg = "IDEA analyse gefaald of geen gecachte resultaten beschikbaar."
                        print(f"ERROR: Bridge {bridge_name} (ID: {bridge_id}): {error_msg}")
                        raise UserError(error_msg)

                    # Extract UC summary
                    uc_summary = extract_uc_summary_from_idea_results(idea_results)

                    # Generate cache hash for this calculation to track cache status
                    cache_hash = cache._generate_input_hash(bridge_params, AnalysisType.IDEA, None)

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
                    print(f"INFO: Bridge {bridge_name} (ID: {bridge_id}): Successfully calculated. Max UC: {uc_summary.get('max_uc')}")
                    
                    # Show completion progress
                    progress_message(
                        message=f"Bridge {current_bridge_position}/{total_bridges}: {bridge_name}\nBerekening voltooid (Max UC: {uc_summary.get('max_uc', 'N/A'):.2f})",
                        percentage=percentage
                    )

                except Exception as e:
                    # Log full error details for debugging
                    error_type = type(e).__name__
                    error_message = str(e)
                    error_traceback = traceback.format_exc()
                    
                    print(f"ERROR: Bridge {bridge_name} (ID: {bridge_id}): Calculation failed with {error_type}: {error_message}")
                    print(f"DEBUG: Full traceback for {bridge_name}:\n{error_traceback}")
                    
                    # Store error result with detailed error message
                    # Truncate traceback if too long, but keep first line (most important)
                    if len(error_traceback) > 500:
                        short_error = f"{error_type}: {error_message}\n(...)"
                    else:
                        short_error = f"{error_type}: {error_message}"
                    
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
                        percentage=percentage
                    )

            # Store aggregated results in parent entity Storage
            batch_results_file = serialize_batch_results(batch_results)
            storage.set("batch_calculation_results", batch_results_file, scope="entity")

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
            print(f"INFO: Batch calculation completed: {completed_count} calculated, {skipped_cached_count} skipped (cached), {failed_count} failed out of {total_processed} bridges")
        finally:
            # Always clear running flag, even if an error occurred
            try:
                storage.delete("batch_calculation_running", scope="entity")
            except Exception:
                pass

    @TableView("Start berekening / Weergeven resultaten", duration_guess=6)
    def view_batch_results(self, params: Parametrization, entity_id: int, **kwargs) -> TableResult:  # noqa: ARG002
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
        # Load results from Storage
        storage = Storage()
        batch_results = None
        try:
            batch_results_file = storage.get("batch_calculation_results", scope="entity")
            
            # Validate storage contents before deserializing
            from viktor.core import File
            

            # Check for boolean first (most common invalid type)
            if isinstance(batch_results_file, bool):
                print(f"WARNING: Found boolean value in storage for 'batch_calculation_results'. Deleting invalid entry.")
                try:
                    storage.delete("batch_calculation_results", scope="entity")
                    print("INFO: Deleted invalid boolean entry from storage")
                except Exception as del_e:
                    print(f"WARNING: Could not delete invalid storage entry: {del_e}")
            elif isinstance(batch_results_file, File):
                batch_results = deserialize_batch_results(batch_results_file)
            else:
                print(f"WARNING: Unexpected type in storage for 'batch_calculation_results': {type(batch_results_file).__name__}, expected File")
        except FileNotFoundError:
            # No batch calculation results stored yet - will trigger calculation below
            pass
        except (TypeError, AttributeError) as e:
            # Error deserializing - log and continue without results
            print(f"WARNING: Error deserializing batch results: {e}")
            batch_results = None

        # Check if we need to trigger a batch calculation
        # This happens if: no results exist, OR there are ready bridges that need calculation
        should_trigger_calculation = False
        
        if not batch_results or len(batch_results) == 0:
            # No results found - need to trigger calculation
            should_trigger_calculation = True
            print("INFO: No batch results found - will trigger batch calculation...")
        else:
            # Check if there are ready bridges that need calculation (not cached)
            try:
                viktor_api = api.API()
                parent_entity = viktor_api.get_entity(entity_id)
                bridge_entities = parent_entity.children(entity_type_names=["Bridge"])
                
                # Get cache hashes from existing batch results
                # Ensure batch_results is a dict (not a File object)
                from viktor.core import File
                
                if isinstance(batch_results, File):
                    # If it's still a File, deserialize it
                    print("INFO: batch_results is still a File, deserializing...")
                    batch_results = deserialize_batch_results(batch_results)
                elif not isinstance(batch_results, dict):
                    # batch_results should be a dict at this point
                    print(f"WARNING: batch_results is not a dict or File: {type(batch_results).__name__}. Cannot extract cache hashes.")
                    batch_results = None
                
                batch_results_cache_hashes: dict[int, str] = {}
                if isinstance(batch_results, dict):
                    for bid, result in batch_results.items():
                        if "cache_hash" in result:
                            batch_results_cache_hashes[bid] = result["cache_hash"]
                
                # Check for ready bridges that are not cached
                ready_bridges_needing_calculation = 0
                for bridge_entity in bridge_entities:
                    bridge_params = bridge_entity.last_saved_params
                    bridge_id = bridge_entity.id
                    
                    # Validate bridge readiness
                    is_ready, _, _ = validate_bridge_for_calculation(bridge_params, bridge_entity)
                    
                    if is_ready:
                        # Check if bridge is cached
                        batch_hash = batch_results_cache_hashes.get(bridge_id)
                        is_cached = check_idea_cache_status(bridge_params, bridge_id, batch_hash)
                        
                        if not is_cached:
                            # Bridge is ready but not cached - needs calculation
                            ready_bridges_needing_calculation += 1
                
                if ready_bridges_needing_calculation > 0:
                    should_trigger_calculation = True
                    print(f"INFO: Found {ready_bridges_needing_calculation} ready bridges needing calculation - will trigger batch calculation...")
            except Exception as e:
                print(f"WARNING: Error checking for ready bridges: {e} - will not auto-trigger calculation")
        
        if should_trigger_calculation:
            # Trigger batch calculation
            try:
                # Check if calculation is already running to prevent multiple simultaneous runs
                # Also handle stale flags from cancelled calculations
                try:
                    running_file = storage.get("batch_calculation_running", scope="entity")
                    from viktor.core import File
                    if isinstance(running_file, File):
                        running_value = running_file.getvalue()
                        if running_value == "running":
                            # Flag exists - could be from a cancelled calculation
                            # Since we can't easily check if job is actually running,
                            # we'll clear the flag and allow new calculation to start
                            # (If calculation was actually running, it would have been caught earlier)
                            print("INFO: Found running flag - clearing to allow new calculation (previous may have been cancelled)")
                            try:
                                storage.delete("batch_calculation_running", scope="entity")
                            except Exception:
                                pass
                            # Continue to start new calculation
                except FileNotFoundError:
                    # No running flag - safe to start calculation
                    pass
                
                # Set running flag as File
                from viktor.core import File
                storage.set("batch_calculation_running", File.from_data("running"), scope="entity")
                
                # Trigger batch calculation automatically
                print("INFO: Triggering batch calculation...", flush=True)
                try:
                    self.run_batch_calculation(params, entity_id, **kwargs)
                except Exception as calc_error:
                    import traceback
                    traceback_str = traceback.format_exc()
                    raise
                
                # Clear running flag
                try:
                    storage.delete("batch_calculation_running", scope="entity")
                except Exception:
                    pass
                
                # Try to load results again after calculation
                try:
                    batch_results_file = storage.get("batch_calculation_results", scope="entity")
                    
                    # Validate storage contents before deserializing
                    from viktor.core import File
                    
                    # Check for boolean first (most common invalid type)
                    if isinstance(batch_results_file, bool):
                        print(f"WARNING: Found boolean value in storage for 'batch_calculation_results' after calculation. Deleting invalid entry.")
                        try:
                            storage.delete("batch_calculation_results", scope="entity")
                            print("INFO: Deleted invalid boolean entry from storage")
                        except Exception as del_e:
                            print(f"WARNING: Could not delete invalid storage entry: {del_e}")
                        batch_results = None
                    elif isinstance(batch_results_file, File):
                        batch_results = deserialize_batch_results(batch_results_file)
                    else:
                        print(f"WARNING: Unexpected type in storage for 'batch_calculation_results' after calculation: {type(batch_results_file).__name__}, expected File")
                        batch_results = None
                except FileNotFoundError:
                    # Still no results after calculation attempt
                    batch_results = None
                except (TypeError, AttributeError) as e:
                    # Error deserializing - log and continue without results
                    print(f"WARNING: Error deserializing batch results after calculation: {e}")
                    batch_results = None
            except Exception as e:
                # Clear running flag on error
                try:
                    storage.delete("batch_calculation_running", scope="entity")
                except Exception:
                    pass
                import traceback
                full_traceback = traceback.format_exc()
                print(f"ERROR: Error triggering batch calculation: {e}", flush=True)
                return TableResult(
                    [["Fout bij starten batchberekening", f"{type(e).__name__}: {str(e)[:100]}", "", "", ""]], 
                    column_headers=["Berekening Status", "Max UC", "UC Status", "Gefaalde controles", "Rapport"], 
                    row_headers=["ERROR"]
                )
        
        # If still no results after attempting calculation, show message
        if not batch_results or len(batch_results) == 0:
            return TableResult(
                [["Geen resultaten beschikbaar", "Ververs deze pagina om opnieuw te proberen", "", "", ""]], 
                column_headers=["Berekening Status", "Max UC", "UC Status", "Gefaalde controles", "Rapport"], 
                row_headers=["INFO"]
            )

        # Build table data with bridge names for row headers
        bridge_data_list = []
        for bridge_id, result in batch_results.items():
            bridge_name = result.get("bridge_name", "Onbekend")
            status = result.get("status", "Onbekend")
            max_uc = result.get("max_uc")
            uc_status = result.get("uc_status", "N/A")
            failed_checks = result.get("failed_checks", [])
            error = result.get("error")

            # Format max_uc
            max_uc_str = f"{max_uc:.2f}" if max_uc is not None else "N/A"

            # Format failed checks count
            failed_checks_str = str(len(failed_checks)) if failed_checks else "0"

            # Generate report URL
            report_url = generate_bridge_report_url(bridge_id)

            # Add status indicator with error message if failed
            # Use TableCell with red background for failed status
            if status == "Gefaald":
                if error:
                    # Show full error message (will be truncated in display if too long)
                    status_display = TableCell(
                        f"{status}: {error[:100]}{'...' if len(error) > 100 else ''}",
                        background_color=Color(255, 200, 200),  # Light red background
                    )
                else:
                    status_display = TableCell(status, background_color=Color(255, 200, 200))
            else:
                status_display = status

            # Store data with bridge name for sorting (bridge_name will be row header)
            bridge_data_list.append((bridge_name, [status_display, max_uc_str, uc_status, failed_checks_str, report_url], uc_status, max_uc_str))

        # Sort results: failed first, then by max UC descending
        def sort_key(item: tuple) -> tuple:
            # item = (bridge_name, data_row, uc_status, max_uc_str)
            bridge_name, data_row, uc_status, max_uc_str = item
            # Convert status to string for comparison (handles both TableCell and string)
            status_text = str(data_row[0])
            status_priority = 0 if "Gefaald" in status_text else 1 if uc_status == "FAILED" else 2
            max_uc_value = float(max_uc_str) if max_uc_str != "N/A" else -1.0
            return (status_priority, -max_uc_value, bridge_name)

        bridge_data_list.sort(key=sort_key)

        # Extract row headers and table data separately
        row_headers = []
        table_data = []
        for bridge_name, data_row, _, _ in bridge_data_list:
            row_headers.append(bridge_name)
            table_data.append(data_row)

        # Define column headers (removed "Brug" since it's now in row headers)
        headers = ["Berekening Status", "Max UC", "UC Status", "Gefaalde controles", "Rapport"]

        return TableResult(table_data, column_headers=headers, row_headers=row_headers)

