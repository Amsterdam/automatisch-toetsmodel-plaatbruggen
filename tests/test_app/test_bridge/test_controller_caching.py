"""Tests for controller methods that use the analysis caching system."""

import unittest

from tests.test_data.seed_loader import load_bridge_default_params


class TestControllerCaching(unittest.TestCase):
    """Test controller methods that use the caching system."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.default_params = load_bridge_default_params()
        self.entity_id = 12345

    def test_controller_import(self) -> None:
        """Test that controller can be imported."""
        try:
            # Import to test availability, but don't use the imported object
            import app.bridge.controller  # noqa: F401

            assert True  # Import successful
        except ImportError as e:
            self.fail(f"Failed to import controller: {e}")

    def test_analysis_cache_import(self) -> None:
        """Test that analysis_cache can be imported."""
        try:
            # Import to test availability, but don't use the imported objects
            import app.bridge.analysis_cache  # noqa: F401

            assert True  # Import successful
        except ImportError as e:
            self.fail(f"Failed to import analysis_cache: {e}")

    def test_controller_instantiation(self) -> None:
        """Test that BridgeController can be instantiated."""
        try:
            from app.bridge.controller import BridgeController

            controller = BridgeController()
            assert controller is not None
        except Exception as e:
            self.fail(f"Failed to instantiate BridgeController: {e}")

    def test_caching_function_availability(self) -> None:
        """Test that caching functions are available."""
        try:
            from app.bridge.analysis_cache import get_cached_analysis_results
            from src.common.constants.technical import AnalysisType

            assert callable(get_cached_analysis_results)
            assert AnalysisType.SCIA.value == "scia"
            assert AnalysisType.IDEA.value == "idea"
        except ImportError as e:
            self.fail(f"Failed to import caching functions: {e}")


if __name__ == "__main__":
    unittest.main()
