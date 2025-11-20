"""
Diagnostic script to inspect cached SCIA and IDEA analysis results.

This script retrieves and analyzes cached results for a specific entity to diagnose
issues with SCIA timeout and IDEA generation failures.
"""

import base64
import json
import pickle
from pathlib import Path
from typing import Any

import pandas as pd

# VIKTOR imports
import viktor.api_v1 as api
from app.bridge.analysis_cache import _get_analysis_cache
from src.common.constants.technical import AnalysisType
from viktor.core import Storage


def inspect_cache_for_entity(entity_id: int, output_dir: Path = Path("C:/temp")) -> None:
    """
    Inspect cached SCIA and IDEA results for a specific entity.

    :param entity_id: Bridge entity ID to inspect
    :type entity_id: int
    :param output_dir: Directory to save diagnostic output files
    :type output_dir: Path
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Inspecting cache for entity {entity_id}...")
    print(f"Output directory: {output_dir}")

    # Get entity and parameters
    viktor_api = api.API()
    try:
        entity = viktor_api.get_entity(entity_id)
        entity_name = entity.name
        print(f"Entity name: {entity_name}")

        # Get last saved parameters
        params = entity.last_saved_params
        print(f"Parameters retrieved: {type(params)}")

        # Get bridge segments count
        bridge_segments = getattr(params, "bridge_segments_array", None)
        num_segments = len(bridge_segments) if bridge_segments else 0
        print(f"Number of bridge segments: {num_segments}")

    except Exception as e:
        print(f"ERROR: Failed to get entity or parameters: {e}")
        return

    # Get cache instance
    cache = _get_analysis_cache()

    # Get cache info
    cache_info = cache.get_cache_info(entity_id)
    print(f"\nCache info: {json.dumps(cache_info, indent=2, default=str)}")

    # Inspect SCIA cache
    print("\n" + "=" * 80)
    print("INSPECTING SCIA CACHE")
    print("=" * 80)

    scia_results = cache.get_cached_analysis(params, AnalysisType.SCIA, entity_id, str("template_path"))
    if scia_results:
        print("SCIA cache found!")
        print(f"SCIA results type: {type(scia_results)}")
        print(f"SCIA results keys: {list(scia_results.keys()) if isinstance(scia_results, dict) else 'N/A'}")

        # Save SCIA results summary
        scia_summary = {
            "entity_id": entity_id,
            "entity_name": entity_name,
            "num_segments": num_segments,
            "cache_keys": list(scia_results.keys()) if isinstance(scia_results, dict) else [],
        }

        # Check for internal_forces key
        if isinstance(scia_results, dict):
            if "internal_forces" in scia_results:
                internal_forces = scia_results["internal_forces"]
                scia_summary["internal_forces_type"] = str(type(internal_forces))
                if isinstance(internal_forces, dict):
                    scia_summary["internal_forces_keys"] = list(internal_forces.keys())
                    print(f"internal_forces keys: {list(internal_forces.keys())}")

                    # Check for CS tables
                    if "cs_results" in internal_forces:
                        cs_results = internal_forces["cs_results"]
                        scia_summary["cs_results_type"] = str(type(cs_results))
                        if isinstance(cs_results, dict):
                            scia_summary["cs_results_keys"] = list(cs_results.keys())
                            print(f"cs_results keys: {list(cs_results.keys())}")

                            # Try to process CS results
                            try:
                                from src.integrations.idea_integration.scia_to_idea_functions import (
                                    process_scia_cs_results_for_idea,
                                )

                                if bridge_segments:
                                    cs_envelope_df = process_scia_cs_results_for_idea(scia_results, bridge_segments)
                                    scia_summary["cs_envelope_df_empty"] = cs_envelope_df.empty
                                    scia_summary["cs_envelope_df_shape"] = cs_envelope_df.shape if not cs_envelope_df.empty else None
                                    scia_summary["cs_envelope_df_columns"] = list(cs_envelope_df.columns) if not cs_envelope_df.empty else []
                                    print(f"CS envelope DataFrame: empty={cs_envelope_df.empty}, shape={cs_envelope_df.shape}")
                                    if not cs_envelope_df.empty:
                                        print(f"CS envelope columns: {list(cs_envelope_df.columns)}")

                                    # Save DataFrame to Excel
                                    excel_path = output_dir / f"entity_{entity_id}_scia_cs_envelope.xlsx"
                                    cs_envelope_df.to_excel(excel_path, index=False)
                                    print(f"Saved CS envelope DataFrame to: {excel_path}")
                            except Exception as e:
                                scia_summary["cs_processing_error"] = str(e)
                                print(f"ERROR processing CS results: {e}")

        # Save SCIA summary
        summary_path = output_dir / f"entity_{entity_id}_scia_summary.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(scia_summary, f, indent=2, default=str)
        print(f"Saved SCIA summary to: {summary_path}")

    else:
        print("No SCIA cache found!")

    # Inspect IDEA cache
    print("\n" + "=" * 80)
    print("INSPECTING IDEA CACHE")
    print("=" * 80)

    idea_results = cache.get_cached_analysis(params, AnalysisType.IDEA, entity_id)
    if idea_results:
        print("IDEA cache found!")
        print(f"IDEA results type: {type(idea_results)}")
        print(f"IDEA results keys: {list(idea_results.keys()) if isinstance(idea_results, dict) else 'N/A'}")

        idea_summary = {
            "entity_id": entity_id,
            "entity_name": entity_name,
            "num_segments": num_segments,
            "cache_keys": list(idea_results.keys()) if isinstance(idea_results, dict) else [],
        }

        if isinstance(idea_results, dict):
            # Check analysis status
            analysis_status = idea_results.get("analysis_status", "unknown")
            idea_summary["analysis_status"] = analysis_status
            print(f"Analysis status: {analysis_status}")

            if analysis_status == "failed":
                error = idea_results.get("error", "No error message")
                idea_summary["error"] = error
                print(f"Error: {error}")

            # Check for IDEA XML input
            if "idea_xml_input_bytes" in idea_results:
                idea_xml_input = idea_results["idea_xml_input_bytes"]
                if idea_xml_input:
                    if hasattr(idea_xml_input, "getvalue"):
                        xml_content = idea_xml_input.getvalue()
                    elif hasattr(idea_xml_input, "read"):
                        idea_xml_input.seek(0)
                        xml_content = idea_xml_input.read()
                    else:
                        xml_content = idea_xml_input

                    if isinstance(xml_content, bytes):
                        xml_str = xml_content.decode("utf-8", errors="ignore")
                    else:
                        xml_str = str(xml_content)

                    idea_summary["idea_xml_input_length"] = len(xml_str)
                    print(f"IDEA XML input length: {len(xml_str)} characters")

                    # Save IDEA XML input
                    xml_path = output_dir / f"entity_{entity_id}_idea_input.xml"
                    with open(xml_path, "w", encoding="utf-8") as f:
                        f.write(xml_str)
                    print(f"Saved IDEA XML input to: {xml_path}")

                    # Try to extract basic info from XML
                    try:
                        import xml.etree.ElementTree as ET

                        root = ET.fromstring(xml_str)
                        idea_summary["idea_xml_root_tag"] = root.tag
                        idea_summary["idea_xml_num_slabs"] = len(root.findall(".//OneWaySlab"))
                        idea_summary["idea_xml_num_loads"] = len(root.findall(".//Load"))
                        print(f"IDEA XML: {idea_summary['idea_xml_num_slabs']} slabs, {idea_summary['idea_xml_num_loads']} loads")
                    except Exception as e:
                        idea_summary["idea_xml_parse_error"] = str(e)
                        print(f"Could not parse IDEA XML: {e}")

        # Save IDEA summary
        summary_path = output_dir / f"entity_{entity_id}_idea_summary.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(idea_summary, f, indent=2, default=str)
        print(f"Saved IDEA summary to: {summary_path}")

    else:
        print("No IDEA cache found!")

    # List all cache keys for this entity
    print("\n" + "=" * 80)
    print("ALL CACHE KEYS FOR ENTITY")
    print("=" * 80)

    storage = Storage()
    try:
        all_keys = storage.list(scope="entity")
        entity_keys = [key for key in all_keys if key.startswith(f"analysis_cache_{entity_id}_")]
        print(f"Found {len(entity_keys)} cache keys:")
        for key in entity_keys:
            print(f"  - {key}")

            # Try to get hash from key
            parts = key.split("_")
            if len(parts) >= 4:
                analysis_type = parts[2]
                cache_hash = parts[3] if len(parts) > 3 else "unknown"
                print(f"    Type: {analysis_type}, Hash: {cache_hash[:16]}...")

    except Exception as e:
        print(f"ERROR listing cache keys: {e}")

    print("\n" + "=" * 80)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    # Entity ID from user's report
    entity_id = 13545
    inspect_cache_for_entity(entity_id)

