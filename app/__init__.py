"""viktor."""

import warnings

# Suppress a specific DeprecationWarning from geopandas._compat.
# This warning is related to an internal import in geopandas (version 1.0.1)
# that still uses `shapely.geos`, which is deprecated in Shapely 2.x.
# Geopandas 1.0.1 is the latest stable version and is intended for Shapely 2.x,
# so this warning is an internal matter for geopandas and does not affect
# our application's functionality. It is suppressed to keep logs clean.
# This can be removed if a future geopandas version resolves the internal import.
warnings.filterwarnings("ignore", category=DeprecationWarning, module="geopandas._compat")

# Suppress the pkg_resources deprecation warning from docxcompose
# We've pinned setuptools<81 in requirements.txt to prevent pkg_resources removal
# This warning is unavoidable until docxcompose updates their code
warnings.filterwarnings(
    "ignore",
    message="pkg_resources is deprecated as an API",
    category=UserWarning,
    module="docxcompose.properties",
)

from viktor import InitialEntity  # type: ignore[attr-defined] # noqa: E402

from .bridge.controller import BridgeController as Bridge  # Uncommented Bridge import # noqa: E402

# from .simple_controller import SimpleController # Old import
from .overview_bridges.controller import OverviewBridgesController as OverviewBridges  # New import # noqa: E402

__version__ = "0.0.1"

# Viktor app package for Automatisch Toetsmodel Plaatbruggen

# --- IMPORTANT NOTE (VIKTOR SDK v14 Compatibility) ---
# The 'InitialEntity' class below is deprecated in SDK v14+ and should ideally
# be replaced by assigning a list of dictionaries directly to 'viktor.initial_entities'.
# Example recommended format:
# viktor.initial_entities = [
#     {"entity_type_name": "OverviewBridges", "is_initial_entity": True},
# ]
# However, attempts to use the recommended format resulted in persistent runtime errors:
# "App specification is invalid: You should provide at least 1 top level entity when using tree app type."
# This occurred despite correct syntax and environment restarts (SDK 14.20.0, Connector 6.4.0).
# Therefore, the deprecated 'InitialEntity' is used here as a temporary workaround.
# The MyPy error for the 'InitialEntity' import is suppressed above using '# type: ignore[attr-defined]'.
# This situation should be revisited if the SDK or connector is updated.
# --- END NOTE ---

initial_entities = [
    InitialEntity(
        entity_type_name="OverviewBridges",  # Use the alias
        name="Overzicht Bruggen",  # Updated name
        children=[],
        use_as_start_page=True,
    )
]
