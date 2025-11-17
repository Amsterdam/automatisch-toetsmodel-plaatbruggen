"""
Information views component for BridgeController.

This component provides views for displaying bridge information:
- Map view showing bridge location
- Load combinations table
"""

from viktor.errors import UserError
from viktor.views import MapPoint, MapResult, MapView, TableResult, TableView

from app.bridge.parametrization import BridgeParametrization
from app.common.map_utils import load_and_filter_bridge_shapefile, process_bridge_geometries, validate_shapefile_exists
from src.combinations.load_factors import create_load_combination_table


class InfoViews:
    """
    Component providing information display views.

    Contains methods for:
    - Bridge location map display
    - Load combination tables
    """

    @MapView("Locatie Brug", duration_guess=2)
    def get_bridge_map_view(self, params: BridgeParametrization, **kwargs) -> MapResult:  # noqa: ARG002
        """
        Display the current bridge polygon from the shapefile in the resources folder.

        :param params: Bridge parametrization object
        :type params: BridgeParametrization
        :param kwargs: Additional arguments including entity_id
        :returns: MapResult with bridge location
        :rtype: MapResult
        """
        entity_id = kwargs.get("entity_id")

        if not isinstance(entity_id, int):
            return MapResult([MapPoint(52.37, 4.89, description="Ongeldige entity ID ontvangen.")])

        current_objectnumm, bridge_name_from_params, error_result = self._get_bridge_entity_data(entity_id)  # type: ignore[attr-defined]
        if error_result:
            return error_result

        if current_objectnumm is None:
            return MapResult([MapPoint(52.37, 4.89, description="Interne fout: OBJECTNUMM onbekend na API call.")])

        if bridge_name_from_params is None:
            bridge_name_from_params = ""

        try:
            shapefile_path = validate_shapefile_exists()
            target_bridge_gdf = load_and_filter_bridge_shapefile(shapefile_path, current_objectnumm)
        except UserError as ue:
            return MapResult([MapPoint(52.37, 4.89, description=str(ue))])

        features, error_point = process_bridge_geometries(target_bridge_gdf.iloc[0], current_objectnumm, bridge_name_from_params)

        if error_point:
            return MapResult([error_point])

        return MapResult(features)

    @TableView("Belastingscombinaties", duration_guess=1)
    def get_load_combinations_view(self, params: BridgeParametrization, **kwargs) -> TableResult:  # noqa: ARG002
        """
        Display the table of load combinations for the bridge.

        :param params: Bridge parametrization object
        :type params: BridgeParametrization
        :param kwargs: Additional arguments
        :returns: TableResult containing the load combinations
        :rtype: TableResult
        """
        try:
            cc_class = (
                getattr(params, "cc_class", None)
                or getattr(getattr(getattr(params, "input", None), "berekeningsinstellingen", None), "cc_class", None)
                or "CC2"
            )
            design_code = (
                getattr(params, "design_code", None)
                or getattr(getattr(getattr(params, "input", None), "berekeningsinstellingen", None), "design_code", None)
                or "NEN 8700 verbouw"
            )
        except Exception:
            cc_class = "CC2"
            design_code = "NEN 8700 verbouw"

        try:
            construction_year = (
                getattr(getattr(params, "info", None), "construction_year", None) or getattr(params, "construction_year", None) or "2000"
            )
        except Exception:
            construction_year = "2000"

        if not construction_year or str(construction_year).strip() == "":
            construction_year = "2000"

        # Extract bridge_segments_array for dynamic UDL factor calculation
        bridge_segments_array = None
        try:
            if hasattr(params, "bridge_segments_array") and params.bridge_segments_array:
                # Convert to list of dicts for compatibility
                bridge_segments_array = [{"l": getattr(segment, "l", 0)} for segment in params.bridge_segments_array]
        except (AttributeError, TypeError):
            # If extraction fails, leave as None (dynamic factors won't be applied)
            pass

        # Extract berekeningsniveau and signage for UDL factor calculation
        berekeningsniveau = None
        signage = None
        try:
            # Try to get from calc_page.calc_level hierarchy
            if hasattr(params, "calc_page") and hasattr(params.calc_page, "calc_level"):
                berekeningsniveau = getattr(params.calc_page.calc_level, "calculation_level", None)
                signage = getattr(params.calc_page.calc_level, "signage", None)
            # Also try direct access (params.berekeningsniveau might be available)
            if not berekeningsniveau:
                berekeningsniveau = getattr(params, "berekeningsniveau", None)
            if not signage:
                signage = getattr(params, "signage", None)
        except (AttributeError, TypeError):
            pass

        load_combination_params = {
            "cc_class": cc_class,
            "design_code": design_code,
            "info": {
                "construction_year": construction_year,
            },
        }

        # Add optional parameters if available
        if bridge_segments_array:
            load_combination_params["bridge_segments_array"] = bridge_segments_array
        if berekeningsniveau:
            load_combination_params["berekeningsniveau"] = berekeningsniveau
        if signage:
            load_combination_params["signage"] = signage

        combination_table = create_load_combination_table(load_combination_params)
        return TableResult(combination_table)
