"""
Optimization component for BridgeController.

This component provides optimization functionality for load zones based on
user-defined criteria. It iterates through calculation levels and signage
options to find the optimal configuration.
"""

import pandas as pd
from viktor.result import OptimizationResult, OptimizationResultElement

from app.bridge.parametrization import BridgeParametrization
from app.constants import CALCULATION_LEVEL_OPTIONS, SIGNAGE_OPTIONS


class Optimization:
    """
    Component providing optimization functionality for the BridgeController.

    Contains methods for:
    - Optimizing load zones based on calculation level and signage
    - Iterating through scenarios to find optimal configurations
    - Evaluating capacity and shear force constraints
    """

    # ============================================================================================================
    # Optimization
    # ============================================================================================================

    def perform_optimization(self, params: BridgeParametrization, **kwargs) -> OptimizationResult:
        """
        Perform optimization of load zones based on user-defined criteria.

        Iterates through all calculation levels and signage options to find the
        optimal configuration that satisfies capacity and shear force requirements.
        The optimization stops when a configuration without failures is found.

        The results table includes:
        - Input parameters: berekeningsniveau, signage
        - Output results: UC Capaciteit values, UC Schuifkracht values

        :param params: Bridge parametrization object
        :type params: BridgeParametrization
        :param kwargs: Additional keyword arguments (includes entity_id)
        :returns: OptimizationResult containing optimization scenarios with UC values
        :rtype: OptimizationResult
        """
        # Initialize a list to store optimization results for each scenario
        results: list[OptimizationResultElement] = []

        # Loop over all calculation levels defined in CALCULATION_LEVEL_OPTIONS
        for calc_level in CALCULATION_LEVEL_OPTIONS:
            # Special case: if calculation level requires iterating over signage options
            if calc_level == "Werkelijke wegindeling met bebording":
                # Try all possible signage options for this calculation level
                for signage in SIGNAGE_OPTIONS:
                    # Set the current calculation level and signage in the params
                    # Note: Fields with 'name' attribute are accessed directly on params object
                    copied_params = params.copy()
                    copied_params.berekeningsniveau = calc_level
                    copied_params.signage = signage

                    # Call the IDEA RCS results view to get the results table for this scenario
                    idea_rcs_results_table = self.get_view_idea_rcs_results(self, copied_params, **kwargs)  # type: ignore[attr-defined]
                    # Convert the table data to a DataFrame for easier processing
                    results_df = pd.DataFrame(idea_rcs_results_table.data, columns=idea_rcs_results_table.column_headers)

                    # Extract UC capacity and UC shearforce numeric values from the DataFrame
                    uc_capacity_values = results_df["UC Capaciteit"].tolist() if "UC Capaciteit" in results_df else []
                    uc_shearforce_values = results_df["UC Schuifkracht"].tolist() if "UC Schuifkracht" in results_df else []

                    # Extract status values to check for failures
                    capacity_status = results_df["Capaciteit"].tolist() if "Capaciteit" in results_df else []
                    shearforce_status = results_df["Schuifkracht"].tolist() if "Schuifkracht" in results_df else []

                    # Store the results for this scenario
                    results.append(
                        OptimizationResultElement(
                            copied_params,
                            {
                                "calculation_level": calc_level,
                                "signage": signage,
                                "capacity_status": capacity_status,
                                "capacity_uc": uc_capacity_values,
                                "shearforce_status": shearforce_status,
                                "shearforce_uc": uc_shearforce_values,
                            },
                        )
                    )

                    # If there are no failures in either capacity or shearforce, stop iterating signage options
                    if "Failed" not in capacity_status and "Failed" not in shearforce_status:
                        break
            else:
                # For other calculation levels, signage is not relevant we set it to the first option (50 ton)
                # Note: Fields with 'name' attribute are accessed directly on params object
                copied_params = params.copy()
                copied_params.berekeningsniveau = calc_level
                copied_params.signage = SIGNAGE_OPTIONS[0]

                # Call the IDEA RCS results view to get the results table for this scenario
                idea_rcs_results_table = self.get_view_idea_rcs_results(self, copied_params, **kwargs)  # type: ignore[attr-defined]
                # Convert the table data to a DataFrame for easier processing
                results_df = pd.DataFrame(idea_rcs_results_table.data, columns=idea_rcs_results_table.column_headers)

                # Extract UC capacity and UC shearforce numeric values from the DataFrame
                uc_capacity_values = results_df["UC Capaciteit"].tolist() if "UC Capaciteit" in results_df else []
                uc_shearforce_values = results_df["UC Schuifkracht"].tolist() if "UC Schuifkracht" in results_df else []

                # Extract status values to check for failures
                capacity_status = results_df["Capaciteit"].tolist() if "Capaciteit" in results_df else []
                shearforce_status = results_df["Schuifkracht"].tolist() if "Schuifkracht" in results_df else []

                # Store the results for this scenario
                results.append(
                    OptimizationResultElement(
                        copied_params,
                        {
                            "calculation_level": calc_level,
                            "signage": None,
                            "capacity_status": capacity_status,
                            "capacity_uc": uc_capacity_values,
                            "shearforce_status": shearforce_status,
                            "shearforce_uc": uc_shearforce_values,
                        },
                    )
                )

                # If there are no failures in either capacity or shearforce, stop iterating calculation levels
                if "Failed" not in capacity_status and "Failed" not in shearforce_status:
                    break

        # Define which input parameters to show in the optimization results table
        # Note: For fields with 'name' attribute, use the name value directly
        result_column_names_input = [
            "berekeningsniveau",  # Calculation level field (has name="berekeningsniveau")
            "signage",  # Signage field (has name="signage")
        ]

        # Define the output headers for the analysis results columns
        # Keys must match the dictionary keys in OptimizationResultElement's analysis_result
        output_headers = {
            "calculation_level": "Berekeningsniveau",
            "signage": "Bebording",
            "capacity_status": "Capaciteit Status",
            "capacity_uc": "Capaciteit UC Waarden",
            "shearforce_status": "Schuifkracht Status",
            "shearforce_uc": "Schuifkracht UC Waarden",
        }

        # Return the OptimizationResult object containing all results and headers
        return OptimizationResult(
            results,
            result_column_names_input=result_column_names_input,
            output_headers=output_headers,
        )
