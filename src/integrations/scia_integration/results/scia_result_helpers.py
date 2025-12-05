"""
Helper functions for SCIA result processing.

This module contains utility functions used across result processing modules
for safer data access and common operations.
"""

from typing import Any


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
        xml_parsing = results.get("xml_parsing", {})
        parsed_tables = xml_parsing.get("parsed_tables", {})

        if table_name not in parsed_tables:
            return None

        table_data = parsed_tables.get(table_name, {})

        data = table_data.get("data", {})
        if not data:
            return None

        return data.get(data_key, None)
    except (AttributeError, KeyError, TypeError):
        return None
