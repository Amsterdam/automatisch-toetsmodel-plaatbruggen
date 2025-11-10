"""Batch calculation component for OverviewBridgesController."""

import logging
import traceback
from typing import Any

import viktor.api_v1 as api
from app.bridge.analysis_cache import get_cached_analysis_results, get_idea_analysis_results
from src.common.constants.technical import AnalysisType
from viktor.core import Color, Storage, UserMessage, progress_message
from viktor.errors import UserError
from viktor.parametrization import Parametrization
from viktor.views import TableCell, TableResult, TableView

logger = logging.getLogger(__name__)

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

    @TableView("Gereedheid voor Batch Berekening", duration_guess=1)
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
        bridge_data_list = []

        # Load batch results to get cache hashes if available
        storage = Storage()
        batch_results_cache_hashes: dict[int, str] = {}
        try:
            batch_results_file = storage.get("batch_calculation_results", scope="entity")
            batch_results = deserialize_batch_results(batch_results_file)
            # Extract cache hashes from batch results
            for bid, result in batch_results.items():
                if "cache_hash" in result:
                    batch_results_cache_hashes[bid] = result["cache_hash"]
        except Exception:
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
            if is_cached:
                cached_bridges += 1

            if is_ready:
                ready_bridges += 1
                missing_fields_str = ""
            else:
                # Format missing fields more cleanly
                if len(missing_fields) <= 2:
                    missing_fields_str = ", ".join(missing_fields)
                else:
                    missing_fields_str = f"{', '.join(missing_fields[:2])} (+{len(missing_fields) - 2} meer)"

            # Determine status display based on cache status
            if is_cached:
                # Bridge has cached results (green background)
                status_display = TableCell("✓ Gecached", background_color=Color(144, 238, 144))
            else:
                # No cached results
                status_display = "✗ Niet gecached"

            # Store data with bridge name for sorting (cached first, then by name)
            # Note: bridge_name will be used as row header, so we don't include it in data
            bridge_data_list.append((is_cached, bridge_name, [status_display, missing_fields_str]))

        # Sort: cached bridges first, then by bridge name
        bridge_data_list.sort(key=lambda x: (-x[0], x[1]))

        # Calculate time estimate
        time_estimate = calculate_estimated_batch_time(ready_bridges)

        # Build summary rows (cleaner formatting without separator)
        # Use styling for summary rows to make them stand out
        status_text = f"{ready_bridges} van {total_bridges} gereed • {cached_bridges} gecached"

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

        # Initialize results storage
        batch_results: dict[int, dict[str, Any]] = {}
        completed_count = 0
        failed_count = 0
        total_bridges = len(ready_bridges)

        # Process each ready bridge
        for i, (bridge_entity, bridge_params) in enumerate(ready_bridges):
            bridge_name = bridge_entity.name
            bridge_id = bridge_entity.id

            # Show progress
            progress_message(f"Lopende batchberekening: {i+1}/{total_bridges} bruggen berekend ({bridge_name})...")

            # Run calculation with error handling
            try:
                # Run IDEA analysis (which automatically runs SCIA first)
                idea_results = get_cached_analysis_results(
                    params=bridge_params, analysis_type=AnalysisType.IDEA, entity_id=bridge_id, analysis_function=get_idea_analysis_results
                )

                if idea_results is None:
                    error_msg = "IDEA analyse gefaald of geen gecachte resultaten beschikbaar."
                    logger.error(f"Bridge {bridge_name} (ID: {bridge_id}): {error_msg}")
                    raise UserError(error_msg)

                # Extract UC summary
                uc_summary = extract_uc_summary_from_idea_results(idea_results)

                # Generate cache hash for this calculation to track cache status
                from app.bridge.analysis_cache import AnalysisCache
                cache = AnalysisCache()
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
                }
                completed_count += 1
                logger.info(f"Bridge {bridge_name} (ID: {bridge_id}): Successfully calculated. Max UC: {uc_summary.get('max_uc')}")

            except Exception as e:
                # Log full error details for debugging
                error_type = type(e).__name__
                error_message = str(e)
                error_traceback = traceback.format_exc()
                
                logger.error(f"Bridge {bridge_name} (ID: {bridge_id}): Calculation failed with {error_type}: {error_message}")
                logger.debug(f"Full traceback for {bridge_name}:\n{error_traceback}")
                
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
                }
                failed_count += 1

        # Store aggregated results in parent entity Storage
        storage = Storage()
        batch_results_file = serialize_batch_results(batch_results)
        storage.set("batch_calculation_results", batch_results_file, scope="entity")

        # Show completion message with appropriate level based on results
        if failed_count > 0:
            if completed_count == 0:
                # All bridges failed - show error message
                completion_msg = (
                    f"❌ Batchberekening voltooid: Alle {failed_count} bruggen gefaald. "
                    f"Bekijk de foutmeldingen in de 'Batch Berekening Resultaten' tabel voor details."
                )
            else:
                # Some bridges failed - show warning message
                completion_msg = (
                    f"⚠️ Batchberekening voltooid: {completed_count} geslaagd, {failed_count} gefaald van {total_bridges} bruggen. "
                    f"Bekijk de resultaten in de 'Batch Berekening Resultaten' tabel voor details."
                )
        else:
            # All bridges succeeded
            completion_msg = (
                f"✅ Batchberekening voltooid: Alle {completed_count} bruggen succesvol berekend. "
                f"Bekijk de resultaten in de 'Batch Berekening Resultaten' tabel."
            )
        # Show completion message to user
        UserMessage.success(completion_msg)
        logger.info(f"Batch calculation completed: {completed_count} succeeded, {failed_count} failed out of {total_bridges} bridges")

    @TableView("Batch Berekening Resultaten", duration_guess=2)
    def view_batch_results(self, params: Parametrization, entity_id: int, **kwargs) -> TableResult:  # noqa: ARG002
        """
        Display batch calculation results with UC values and report links.

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
        try:
            batch_results_file = storage.get("batch_calculation_results", scope="entity")
            batch_results = deserialize_batch_results(batch_results_file)
        except FileNotFoundError:
            # No batch calculation results stored yet
            return TableResult(
                [["Geen resultaten beschikbaar", "Start eerst een batchberekening", "", "", ""]], column_headers=["Berekening Status", "Max UC", "UC Status", "Gefaalde controles", "Rapport"], row_headers=["INFO"]
            )

        # Check if results exist (empty dict check)
        if not batch_results:
            return TableResult(
                [["Geen resultaten beschikbaar", "Start eerst een batchberekening", "", "", ""]], column_headers=["Berekening Status", "Max UC", "UC Status", "Gefaalde controles", "Rapport"], row_headers=["INFO"]
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

