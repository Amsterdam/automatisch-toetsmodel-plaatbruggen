#!/usr/bin/env python3
"""
Simple test to verify the updated force envelope extraction function.
"""


def test_updated_force_envelope_extraction():
    """Test the updated force envelope extraction with new data structure."""
    # Mock results structure based on process_scia_results_for_idea pattern
    mock_results = {
        "xml_parsing": {
            "parsed_tables": {
                "Interne 2D-krachten basis ULS": {
                    "status": "success",
                    "data": {
                        "Basis grootheden": {
                            "x": [1.0, 2.0, 3.0],
                            "y": [0.0, 0.0, 0.0],
                            "z": [0.0, 0.0, 0.0],
                            "Naam": ["Z1_1", "Z2_1", "Z3_1"],
                            "v_x": [100.0, 200.0, 150.0],  # These will become Vz
                            "v_y": [50.0, 75.0, 60.0],  # These will become Vy
                            "n_x": [1000.0, 1500.0, 1200.0],  # These will become N
                        }
                    },
                },
                "Interne 2D-krachten elementair ULS": {
                    "status": "success",
                    "data": {
                        "Elementaire ontwerpgrootheden": {
                            "x": [1.0, 2.0, 3.0],
                            "y": [0.0, 0.0, 0.0],
                            "z": [0.0, 0.0, 0.0],
                            "Naam": ["Z1_1", "Z2_1", "Z3_1"],
                            "m_xD+": [50000.0, 75000.0, 60000.0],  # Positive X moments
                            "m_xD-": [-30000.0, -45000.0, -35000.0],  # Negative X moments
                            "m_yD+": [40000.0, 55000.0, 45000.0],  # Positive Y moments
                            "m_yD-": [-25000.0, -35000.0, -30000.0],  # Negative Y moments
                        }
                    },
                },
            }
        }
    }

    try:
        from src.integrations.scia_integration.scia_force_envelopes import extract_force_envelopes

        print("Testing extract_force_envelopes with new data structure...")
        envelopes = extract_force_envelopes(mock_results)

        print(f"Extracted envelopes for {len(envelopes)} sections")
        for section, section_data in envelopes.items():
            print(f"  Section {section}: {len(section_data)} components")
            for component, envelope in section_data.items():
                max_val = envelope["max"]["value"]
                min_val = envelope["min"]["value"]
                if max_val != float("-inf") or min_val != float("inf"):
                    print(f"    {component}: max={max_val}, min={min_val}")

        print("✅ Test completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    test_updated_force_envelope_extraction()
