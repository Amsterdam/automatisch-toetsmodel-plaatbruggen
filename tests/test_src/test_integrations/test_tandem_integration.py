"""
Tests for tandem system integration with src.loads.loadcase_helper_functions.

These tests verify the integration between bridge parameters and tandem load generation
using the established src.loads.loadcase_helper_functions.
"""

import pytest


class TestTandemFunctionIntegration:
    """Test integration with src.loads.loadcase_helper_functions tandem systems."""

    def test_determine_lane_configuration_from_bridge_width(self) -> None:
        """Test lane count determination for a wide bridge."""
        from src.integrations.scia_integration.scia_bridge_geometry import determine_tandem_function_for_bridge

        # Test with a wide bridge (30m width)
        bridge_dims = {"width_bridgedeck": 30.0}

        # Using default 'theoretical' mode
        result = determine_tandem_function_for_bridge(bridge_dims)

        # 30m width should result in 10 lanes (30/3)
        assert result["function_name"] == "tandem_systems_theoretical_lanes"
        assert result["lane_count"] == 10
        assert result["mode"] == "theoretical"

    def test_determine_lane_configuration_narrow_bridge(self) -> None:
        """Test lane count for a narrow bridge."""
        from src.integrations.scia_integration.scia_bridge_geometry import determine_tandem_function_for_bridge

        bridge_dims = {"width_bridgedeck": 5.0}  # Less than 2 lanes wide
        result = determine_tandem_function_for_bridge(bridge_dims)

        assert result["function_name"] == "tandem_systems_theoretical_lanes"
        assert result["lane_count"] == 1  # 5.0 // 3.0 = 1
        assert result["mode"] == "theoretical"

    def test_determine_tandem_function_actual_mode(self) -> None:
        """Test tandem function determination in actual mode."""
        from src.integrations.scia_integration.scia_bridge_geometry import determine_tandem_function_for_bridge

        bridge_dims = {"width_bridgedeck": 24.0}
        result = determine_tandem_function_for_bridge(bridge_dims, mode="actual")

        assert result["function_name"] == "tandem_systems_actual_lanes"
        assert result["mode"] == "actual"

    def test_generate_tandem_loads_single_lane(self) -> None:
        """Test tandem load generation for single lane bridge."""
        from src.integrations.scia_integration.scia_bridge_geometry import generate_tandem_loads_for_bridge

        bridge_params = {
            "length_bridgedeck": 10.0,
            "width_bridgedeck": 5.0,
            "thickness_bridgedeck": 2.0,
        }

        result = generate_tandem_loads_for_bridge(bridge_params)

        # Should return list of tandem load data
        assert isinstance(result, list)
        assert len(result) > 0

        # Each item should have expected structure for single lane
        for tandem in result:
            assert "load_case" in tandem
            assert "wheels" in tandem
            assert "load" in tandem
            assert tandem["load_case"].startswith("BG6")

    def test_generate_tandem_loads_multi_lane(self) -> None:
        """Test tandem load generation for multi-lane bridge."""
        from src.integrations.scia_integration.scia_bridge_geometry import generate_tandem_loads_for_bridge

        bridge_params = {
            "length_bridgedeck": 10.0,
            "width_bridgedeck": 12.0,  # 4 lanes
            "thickness_bridgedeck": 2.0,
        }

        result = generate_tandem_loads_for_bridge(bridge_params)

        # Should return list of tandem load data
        assert isinstance(result, list)
        assert len(result) > 0

        # Each item should have expected structure for multi-lane
        for tandem in result:
            assert "load_case" in tandem
            assert "tandems" in tandem
            assert tandem["load_case"].startswith("BG6")

            # Each tandem configuration should have multiple lane loads
            for lane_tandem in tandem["tandems"]:
                assert "wheels" in lane_tandem
                assert "load" in lane_tandem
                assert "lane" in lane_tandem

    def test_tandem_load_count_proportional_to_bridge_length(self) -> None:
        """Test that longer bridges generate more tandem positions."""
        from src.integrations.scia_integration.scia_bridge_geometry import generate_tandem_loads_for_bridge

        # Short bridge
        short_params = {
            "length_bridgedeck": 5.0,
            "width_bridgedeck": 8.0,
            "thickness_bridgedeck": 2.0,
        }

        # Long bridge
        long_params = {
            "length_bridgedeck": 20.0,
            "width_bridgedeck": 8.0,
            "thickness_bridgedeck": 2.0,
        }

        short_result = generate_tandem_loads_for_bridge(short_params)
        long_result = generate_tandem_loads_for_bridge(long_params)

        # Longer bridge should have more tandem positions
        assert len(long_result) > len(short_result)


class TestTandemDataConversion:
    """Test converting tandem data to SCIA format."""

    def test_convert_single_lane_format_to_scia(self) -> None:
        """Test converting single lane data structure."""
        from src.integrations.scia_integration.scia_bridge_geometry import convert_tandem_data_to_scia_format

        # Mock single lane tandem data
        tandem_data = [
            {
                "load_case": "BG6001",
                "wheels": [
                    [[10.0, 1.0], [10.4, 1.0], [10.4, 1.4], [10.0, 1.4]],  # Wheel 1
                    [[11.2, 1.0], [11.6, 1.0], [11.6, 1.4], [11.2, 1.4]],  # Wheel 2
                ],
                "load": 1875000.0,  # N/m²
            }
        ]

        result = convert_tandem_data_to_scia_format(tandem_data)

        assert len(result) == 1
        load_case_data = result[0]

        assert load_case_data["load_case"] == "BG6001"
        assert len(load_case_data["patch_loads"]) == 2  # Two wheels

        # Check 3D coordinate conversion
        for patch_load in load_case_data["patch_loads"]:
            assert len(patch_load["corners"]) == 4
            for corner in patch_load["corners"]:
                assert len(corner) == 3  # x, y, z
                assert corner[2] == 0.0  # z-coordinate should be 0

    def test_convert_multi_lane_format_to_scia(self) -> None:
        """Test converting multi-lane data structure."""
        from src.integrations.scia_integration.scia_bridge_geometry import convert_tandem_data_to_scia_format

        # Mock multi-lane tandem data
        tandem_data = [
            {
                "load_case": "BG6001",
                "tandems": [
                    {
                        "wheels": [
                            [[10.0, 1.0], [10.4, 1.0], [10.4, 1.4], [10.0, 1.4]],
                        ],
                        "load": 1875000.0,
                        "lane": 1,
                    },
                    {
                        "wheels": [
                            [[10.0, 4.0], [10.4, 4.0], [10.4, 4.4], [10.0, 4.4]],
                        ],
                        "load": 1250000.0,
                        "lane": 2,
                    },
                ],
            }
        ]

        result = convert_tandem_data_to_scia_format(tandem_data)

        assert len(result) == 1
        load_case_data = result[0]

        assert load_case_data["load_case"] == "BG6001"
        assert len(load_case_data["patch_loads"]) == 2  # Two lane tandems

    def test_wheel_coordinate_conversion_2d_to_3d(self) -> None:
        """Test 2D wheel coordinates to 3D SCIA coordinates."""
        from src.integrations.scia_integration.scia_bridge_geometry import convert_wheel_coordinates_to_3d

        wheel_2d = [[10.0, 1.0], [10.4, 1.0], [10.4, 1.4], [10.0, 1.4]]

        result = convert_wheel_coordinates_to_3d(wheel_2d)

        expected = [(10.0, 1.0, 0.0), (10.4, 1.0, 0.0), (10.4, 1.4, 0.0), (10.0, 1.4, 0.0)]
        assert result == expected

    def test_coordinate_system_alignment_bridge_to_scia(self) -> None:
        """Test coordinate system alignment between bridge and SCIA model."""
        from src.integrations.scia_integration.scia_bridge_geometry import align_bridge_coordinates_to_scia

        bridge_coords = [(10.0, 1.0, 0.0), (10.4, 1.0, 0.0), (10.4, 1.4, 0.0), (10.0, 1.4, 0.0)]
        bridge_center_y = 15.0  # Y coordinate of bridge center

        result = align_bridge_coordinates_to_scia(bridge_coords, bridge_center_y)

        # Should maintain X coordinates, adjust Y coordinates for SCIA model
        assert len(result) == 4
        for i, coord in enumerate(result):
            assert coord[0] == bridge_coords[i][0]  # X unchanged
            assert coord[1] == bridge_coords[i][1] + bridge_center_y  # Y adjusted by center offset
            assert coord[2] == 0.0  # Z should be 0


class TestErrorHandling:
    """Test error handling in tandem integration."""

    def test_invalid_bridge_width_handling(self) -> None:
        """Test handling of invalid bridge width."""
        from src.integrations.scia_integration.scia_bridge_geometry import determine_tandem_function_for_bridge

        bridge_dims = {"width_bridgedeck": 0.0}

        with pytest.raises(ValueError, match="Invalid bridge width"):
            determine_tandem_function_for_bridge(bridge_dims)

    def test_missing_bridge_parameters(self) -> None:
        """Test handling of missing bridge parameters."""
        from src.integrations.scia_integration.scia_bridge_geometry import generate_tandem_loads_for_bridge

        incomplete_params = {"length_bridgedeck": 10.0}  # Missing width and thickness

        with pytest.raises(KeyError):
            generate_tandem_loads_for_bridge(incomplete_params)

    def test_invalid_tandem_data_structure(self) -> None:
        """Test handling of invalid tandem data structure."""
        from src.integrations.scia_integration.scia_bridge_geometry import convert_tandem_data_to_scia_format

        invalid_data = [{"invalid": "structure"}]

        with pytest.raises(KeyError):
            convert_tandem_data_to_scia_format(invalid_data)


if __name__ == "__main__":
    pytest.main([__file__])
