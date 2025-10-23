"""
SCIA load specification constants.

These constants define the engineering values used for load calculations
in SCIA Engineer integration, including tandem systems, UDL values,
and alpha factors according to Dutch standards.
"""

# Tandem System (TS) Load Base Values
TANDEM_LOAD_BASE_MAIN = 300000  # N (300 kN)
TANDEM_LOAD_BASE_SECOND = 200000  # N (200 kN)
TANDEM_LOAD_BASE_THIRD = 100000  # N (100 kN)

# Tandem System Contact Dimensions
TANDEM_CONTACT_AREA_SIDE = 0.4  # m (0.4m x 0.4m contact patch)

# UDL (Uniformly Distributed Load) Values
UDL_OTHER_LANE_VALUE = 2500.0  # N/m²
UDL_REST_AREA_VALUE = 2500.0  # N/m²

# Alpha factors for load calculations
ALPHA_Q_ONDERLIGGEND = 0.8  # Alpha Q factor for underlying road network
ALPHA_Q_MAIN_LANE_ONDERLIGGEND = 1.35  # Alpha Q for main lane, underlying network
ALPHA_Q_OTHER_LANE_ONDERLIGGEND = 1.0  # Alpha Q for other lanes
NOBS_DEFAULT = 20000  # Default number of trucks per year for NEN-EN 1991-2

# Signage options (must match app/constants/technical.py SIGNAGE_OPTIONS)
SIGNAGE_WEIGHT_OPTIONS = ["50 ton", "45 ton", "40 ton", "35 ton", "30 ton", "25 ton", "20 ton"]
