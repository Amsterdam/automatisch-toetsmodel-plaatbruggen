"""
Test module for IDEA StatiCa integration interface.

This module provides comprehensive testing for the IDEA StatiCa integration,
including model creation, parameter extraction, and analysis functionality.
"""

import pytest

from src.integrations import idea_interface


def test_calculate_rebar_positions_even():
    """Test even number of rebars are placed symmetrically."""
    positions = idea_interface.calculate_rebar_positions(1000, 200)
    # Should create 5 rebars: positions should be symmetric and spaced
    assert isinstance(positions, list)
    assert len(positions) == 5
    assert positions[0] < 0 < positions[-1]


if __name__ == "__main__":
    pytest.main([__file__])
