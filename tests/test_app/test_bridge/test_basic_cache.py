"""Basic test for the analysis caching system."""

import unittest
from unittest.mock import Mock, patch


class TestBasicCache(unittest.TestCase):
    """Basic test for the caching system."""

    def test_import_analysis_cache(self) -> None:
        """Test that analysis_cache can be imported."""
        try:
            # Import to test availability, but don't use the imported objects
            import app.bridge.analysis_cache  # noqa: F401

            assert True  # Import successful
        except ImportError as e:
            self.fail(f"Failed to import analysis_cache: {e}")

    def test_analysis_type_enum(self) -> None:
        """Test AnalysisType enum values."""
        from src.common.constants.technical import AnalysisType

        assert AnalysisType.SCIA.value == "scia"
        assert AnalysisType.IDEA.value == "idea"

    def test_cache_instantiation(self) -> None:
        """Test that AnalysisCache can be instantiated."""
        from app.bridge.analysis_cache import AnalysisCache

        try:
            # Mock Storage to avoid "Job token is not set" error
            with patch("app.bridge.analysis_cache.Storage") as mock_storage:
                mock_storage.return_value = Mock()
                cache = AnalysisCache()
                assert cache is not None
        except Exception as e:
            self.fail(f"Failed to instantiate AnalysisCache: {e}")


if __name__ == "__main__":
    unittest.main()
