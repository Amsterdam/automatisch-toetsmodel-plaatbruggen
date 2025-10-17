"""Module for processing IDEA RCS analysis results."""

import traceback
from io import BytesIO
from typing import Any


class IdeaResultsProcessor:
    """Class for processing IDEA RCS analysis results."""

    @staticmethod
    def get_table_headers() -> list[str]:
        """
        Get standard IDEA table column headers.

        :returns: List of column headers for IDEA results table including CheckValue columns
        :rtype: list[str]
        """
        return [
            "Sectie",
            "Capaciteit",
            "UC Capaciteit",
            "Schuifkracht",
            "UC Schuifkracht",
            "Torsie",
            "UC Torsie",
            "Interactie",
            "UC Interactie",
            "Scheurwijdte",
            "UC Scheurwijdte",
            "Detailing",
            "UC Detailing",
            "Spanningslimieten",
            "UC Spanningslimieten",
        ]

    @staticmethod
    def create_error_row(error_msg: str) -> list[str]:
        """
        Create table row with error message.

        :param error_msg: Error message to display
        :type error_msg: str
        :returns: Table row with error message and empty cells
        :rtype: list[str]
        """
        return ["Analyse gefaald", error_msg, "", "", "", "", "", "", "", "", "", "", "", "", ""]

    @staticmethod
    def create_processing_error_row(error_msg: str) -> list[str]:
        """
        Create table row for processing errors.

        :param error_msg: Error message to display
        :type error_msg: str
        :returns: Table row with processing error message and empty cells
        :rtype: list[str]
        """
        return ["Fout bij verwerking", f"Kon IDEA resultaten niet verwerken: {error_msg}", "", "", "", "", "", "", "", "", "", "", "", "", ""]

    @staticmethod
    def safe_get_result(section_data: dict[str, Any], key: str) -> tuple[str, str]:
        """
        Safely extract result and check values from pre-parsed data.

        :param section_data: Section data dictionary
        :type section_data: dict[str, Any]
        :param key: Key to extract from section data
        :type key: str
        :returns: Tuple of (Result value, CheckValue) or ("N/A", "N/A") if not found
        :rtype: tuple[str, str]
        """
        value = section_data.get(key)
        if value is None:
            return ("N/A", "N/A")
        if isinstance(value, dict):
            result = value.get("Result", "N/A")
            check_value = value.get("CheckValue", "N/A")
            # Format CheckValue if it's a number
            if isinstance(check_value, (int, float)):
                check_value = f"{check_value:.2f}"
            return (str(result), str(check_value))
        return (str(value), "N/A")

    @staticmethod
    def safe_extract_result(result_list: list[dict[str, Any]] | None) -> tuple[str, str]:
        """
        Safely extract result and check values from parser output.

        :param result_list: List of result dictionaries from parser
        :type result_list: list[dict[str, Any]] | None
        :returns: Tuple of (Result value, CheckValue) or ("N/A", "N/A") if not found
        :rtype: tuple[str, str]
        """
        if not result_list or len(result_list) == 0:
            return ("N/A", "N/A")
        result_dict = result_list[0]
        if result_dict is None or not isinstance(result_dict, dict):
            return ("N/A", "N/A")
        result = result_dict.get("Result", "N/A")
        check_value = result_dict.get("CheckValue", "N/A")
        # Format CheckValue if it's a number
        if isinstance(check_value, (int, float)):
            check_value = f"{check_value:.3f}"
        return (str(result), str(check_value))

    @staticmethod
    def process_preparsed_results(section_results: list[dict[str, Any]]) -> list[list[str]]:
        """
        Process pre-parsed section results into table data.

        :param section_results: List of pre-parsed section results
        :type section_results: list[dict[str, Any]]
        :returns: List of table rows with processed data including CheckValue columns
        :rtype: list[list[str]]
        """
        table_data = []
        for section_data in section_results:
            capacity_result, capacity_check = IdeaResultsProcessor.safe_get_result(section_data, "capacity")
            shear_result, shear_check = IdeaResultsProcessor.safe_get_result(section_data, "shear")
            torsion_result, torsion_check = IdeaResultsProcessor.safe_get_result(section_data, "torsion")
            interaction_result, interaction_check = IdeaResultsProcessor.safe_get_result(section_data, "interaction")
            crack_width_result, crack_width_check = IdeaResultsProcessor.safe_get_result(section_data, "crack_width")
            detailing_result, detailing_check = IdeaResultsProcessor.safe_get_result(section_data, "detailing")
            stress_limitation_result, stress_limitation_check = IdeaResultsProcessor.safe_get_result(section_data, "stress_limitation")

            table_data.append(
                [
                    section_data.get("id", "Onbekend"),
                    capacity_result,
                    capacity_check,
                    shear_result,
                    shear_check,
                    torsion_result,
                    torsion_check,
                    interaction_result,
                    interaction_check,
                    crack_width_result,
                    crack_width_check,
                    detailing_result,
                    detailing_check,
                    stress_limitation_result,
                    stress_limitation_check,
                ]
            )
        return table_data

    @staticmethod
    def process_raw_results(output_content: str | bytes) -> list[list[str]]:
        """
        Process raw IDEA output content into table data.

        :param output_content: Raw output content from IDEA analysis
        :type output_content: str | bytes
        :returns: List of table rows with processed data including CheckValue columns
        :rtype: list[list[str]]
        :raises ValueError: If output content is missing or invalid format
        """
        if output_content is None:
            raise ValueError("Output content is None")

        # Ensure output_content is bytes
        if isinstance(output_content, str):
            output_content = output_content.encode("utf-8")
        elif not isinstance(output_content, bytes):
            raise TypeError(f"Unexpected type for output_content: {type(output_content)}")

        # Import here to avoid circular imports
        try:
            from viktor.external import idea_rcs
        except ImportError as e:
            raise ValueError(f"Cannot import VIKTOR IDEA RCS module: {e}")

        # Parse using IDEA RCS parser
        output_file_obj = BytesIO(output_content)
        parser = idea_rcs.RcsOutputFileParser(output_file_obj)

        table_data = []
        for section in parser.section_results():
            capacity_result, capacity_check = IdeaResultsProcessor.safe_extract_result(section.capacity())
            shear_result, shear_check = IdeaResultsProcessor.safe_extract_result(section.shear())
            torsion_result, torsion_check = IdeaResultsProcessor.safe_extract_result(section.torsion())
            interaction_result, interaction_check = IdeaResultsProcessor.safe_extract_result(section.interaction())
            crack_width_result, crack_width_check = IdeaResultsProcessor.safe_extract_result(section.crack_width())
            detailing_result, detailing_check = IdeaResultsProcessor.safe_extract_result(section.detailing())
            stress_limitation_result, stress_limitation_check = IdeaResultsProcessor.safe_extract_result(section.stress_limitation())

            table_data.append(
                [
                    section.id_ if hasattr(section, "id_") else "Onbekend",
                    capacity_result,
                    capacity_check,
                    shear_result,
                    shear_check,
                    torsion_result,
                    torsion_check,
                    interaction_result,
                    interaction_check,
                    crack_width_result,
                    crack_width_check,
                    detailing_result,
                    detailing_check,
                    stress_limitation_result,
                    stress_limitation_check,
                ]
            )
        return table_data

    @staticmethod
    def process_idea_results(cached_results: dict[str, Any]) -> dict[str, Any]:
        """
        Process IDEA analysis results and return structured data.

        This function handles both pre-parsed and raw results, returning a dictionary
        with the processed data and any error information.

        :param cached_results: Cached analysis results from IDEA
        :type cached_results: dict[str, Any]
        :returns: Dictionary containing 'success', 'data', 'headers', and optional 'error'
        :rtype: dict[str, Any]
        """
        try:
            # Check if analysis failed
            analysis_status = cached_results.get("analysis_status", "unknown")
            if analysis_status == "failed":
                error_msg = cached_results.get("error", "Onbekende fout")
                return {
                    "success": False,
                    "data": [IdeaResultsProcessor.create_error_row(error_msg)],
                    "headers": IdeaResultsProcessor.get_table_headers(),
                    "error": error_msg,
                }

            # Try pre-parsed results first
            section_results = cached_results.get("section_results")
            if section_results is not None:
                data = IdeaResultsProcessor.process_preparsed_results(section_results)
                return {"success": True, "data": data, "headers": IdeaResultsProcessor.get_table_headers()}

            # Fallback to raw parsing
            output_content = cached_results.get("output_content")
            if output_content is None:
                return {
                    "success": False,
                    "data": [IdeaResultsProcessor.create_error_row("Gecachte IDEA resultaten zijn incompleet - geen output content.")],
                    "headers": IdeaResultsProcessor.get_table_headers(),
                    "error": "Missing output content",
                }

            data = IdeaResultsProcessor.process_raw_results(output_content)
            return {"success": True, "data": data, "headers": IdeaResultsProcessor.get_table_headers()}

        except Exception as e:
            # Log the error for debugging
            traceback.print_exc()

            error_msg = str(e)
            return {
                "success": False,
                "data": [IdeaResultsProcessor.create_processing_error_row(error_msg)],
                "headers": IdeaResultsProcessor.get_table_headers(),
                "error": error_msg,
            }
