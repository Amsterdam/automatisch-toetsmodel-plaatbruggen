from typing import Any, TypeAlias

# Global VIKTOR imports with error handling for CI/testing environments
try:
    from viktor.external import scia

    VIKTOR_AVAILABLE = True
except ImportError:
    # Mock objects for environments without VIKTOR SDK
    scia = None  # type: ignore[misc,assignment]
    VIKTOR_AVAILABLE = False


# Type aliases
SciaModel: TypeAlias = Any
SciaAnalysis: TypeAlias = Any


def _check_scia_availability() -> None:
    """Check if VIKTOR SCIA module is available, raise ImportError if not."""
    if not VIKTOR_AVAILABLE or scia is None:
        raise ImportError("VIKTOR SCIA module not available")
