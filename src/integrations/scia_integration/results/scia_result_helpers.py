"""
Helper functions for SCIA result processing.

This module contains utility functions used across result processing modules
for safer data access and common operations.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def get_nested_result_data(
    results: dict[str, Any],
    table_name: str,
    data_key: str = "p1",
) -> dict[str, Any] | None:
    """
    Safely extract nested data from SCIA results dictionary.

    Provides safer access to deeply nested result structures with better error handling.

    :param results: SCIA analysis results dictionary
    :type results: dict[str, Any]
    :param table_name: Name of the table to extract
    :type table_name: str
    :param data_key: Key within the data dictionary to extract (default: "p1" for sections)
    :type data_key: str
    :returns: Extracted data dictionary, or None if not found
    :rtype: dict[str, Any] | None
    """
    try:
        parsed_tables = results.get("xml_parsing", {}).get("parsed_tables", {})
        table = parsed_tables.get(table_name, {})

        # DEBUG: Log table structure to diagnose extraction issues
        if table:
            table_keys = list(table.keys()) if isinstance(table, dict) else f"Not a dict: {type(table)}"
            logger.info("get_nested_result_data - Table '%s' structure keys: %s", table_name, table_keys)

            data = table.get("data", {}) if isinstance(table, dict) else {}
            if data:
                data_keys = list(data.keys()) if isinstance(data, dict) else f"Not a dict: {type(data)}"
                logger.info("get_nested_result_data - Table '%s' data keys: %s", table_name, data_keys)
            else:
                logger.warning("get_nested_result_data - Table '%s' has no 'data' key!", table_name)
        else:
            logger.warning("get_nested_result_data - Table '%s' not found in parsed_tables", table_name)

        return parsed_tables.get(table_name, {}).get("data", {}).get(data_key, None)
    except (AttributeError, KeyError, TypeError) as e:
        logger.warning("get_nested_result_data - Exception extracting '%s': %s", table_name, e)
        return None
