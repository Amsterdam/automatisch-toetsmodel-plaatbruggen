"""
Test module for IDEA StatiCa integration interface.

This module provides comprehensive testing for the IDEA StatiCa integration,
including model creation, parameter extraction, and analysis functionality.
"""

from unittest.mock import Mock, patch

import pytest

from src.integrations import idea_interface
from tests.test_data.seed_loader import load_bridge_default_params


def test_calculate_rebar_positions_even():
    """Test even number of rebars are placed symmetrically."""
    positions = idea_interface.calculate_rebar_positions(1000, 200)
    # Should create 5 rebars: positions should be symmetric and spaced
    assert isinstance(positions, list)
    assert len(positions) == 5
    assert positions[0] < 0 < positions[-1]


def test_calculate_rebar_positions_odd():
    """Test odd number of rebars includes center at 0."""
    positions = idea_interface.calculate_rebar_positions(900, 300)
    # Should create 3 rebars: center at 0
    assert isinstance(positions, list)
    assert len(positions) == 3
    assert 0 in positions


def test_calculate_rebar_positions_too_small():
    """Test that too small width returns empty list."""
    positions = idea_interface.calculate_rebar_positions(100, 200)
    assert positions == []


def test_get_unique_matching_zone_keys():
    """Test extraction of unique matching zone keys from params."""
    params = load_bridge_default_params()
    result, grouped_thickness, grouped_rebar_configs = idea_interface._get_unique_matching_zone_keys(params)
    assert isinstance(result, list)
    assert isinstance(grouped_thickness, dict)
    assert isinstance(grouped_rebar_configs, dict)


def test_create_bridge_idea_model_runs():
    """Test that create_bridge_idea_model runs and returns a model object."""
    params = load_bridge_default_params()
    with patch("src.integrations.idea_interface.idea_rcs.Model") as MockModel:
        mock_model = Mock()
        MockModel.return_value = mock_model
        # Patch all methods used on the model
        mock_model.create_concrete_material.return_value = Mock()
        mock_model.create_reinforcement_material.return_value = Mock()
        mock_model.create_one_way_slab.return_value = Mock()
        mock_slab = mock_model.create_one_way_slab.return_value
        mock_slab.create_bar.return_value = None
        mock_slab.create_extreme.return_value = None
        model = idea_interface.create_bridge_idea_model(params)
        assert model is mock_model


def test_run_idea_analysis_success():
    """Test successful run of run_idea_analysis returns file."""
    mock_model = Mock()
    with patch("src.integrations.idea_interface.idea_rcs.IdeaRcsAnalysis") as MockAnalysis:
        mock_analysis = Mock()
        MockAnalysis.return_value = mock_analysis
        mock_model.generate_xml_input.return_value = "<xml>...</xml>"
        mock_analysis.get_idea_rcs_file.return_value = "dummy_rcs_file"
        mock_analysis.execute.return_value = None
        with patch("src.integrations.idea_interface.idea_rcs", create=True):
            result = idea_interface.run_idea_analysis(mock_model, timeout=10)
            assert result == "dummy_rcs_file"


def test_run_idea_analysis_importerror():
    """Test ImportError is raised if idea_rcs cannot be imported."""
    mock_model = Mock()
    with patch("src.integrations.idea_interface.idea_rcs", side_effect=ImportError):
        with pytest.raises(ImportError):
            idea_interface.run_idea_analysis(mock_model)


def test_run_idea_analysis_runtimeerror():
    """Test RuntimeError is raised if analysis execution fails."""
    mock_model = Mock()
    with patch("src.integrations.idea_interface.idea_rcs.IdeaRcsAnalysis") as MockAnalysis:
        mock_analysis = Mock()
        MockAnalysis.return_value = mock_analysis
        mock_model.generate_xml_input.side_effect = Exception("fail")
        with patch("src.integrations.idea_interface.idea_rcs", create=True):
            with pytest.raises(RuntimeError):
                idea_interface.run_idea_analysis(mock_model)


if __name__ == "__main__":
    pytest.main([__file__])
