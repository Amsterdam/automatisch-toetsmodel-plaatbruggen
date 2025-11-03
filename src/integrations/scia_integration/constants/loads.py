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
DEFAULT_UDL_VALUE = 9000.0  # Default UDL value for main lane (in N/m²)

# Crowd load (NEN-EN 1991-2 art. 5.3.2.1 LM4)
CROWD_LOAD_PER_SQM = 5.0  # kN/m²
CROWD_LOAD_PER_SQM_N = CROWD_LOAD_PER_SQM * 1000.0  # Convert to N/m²

# Alpha factors for load calculations
ALPHA_Q_ONDERLIGGEND = 0.8  # Alpha Q factor for underlying road network
ALPHA_Q_MAIN_LANE_ONDERLIGGEND = 1.35  # Alpha Q for main lane, underlying network
ALPHA_Q_OTHER_LANE_ONDERLIGGEND = 1.0  # Alpha Q for other lanes
NOBS_DEFAULT = 20000  # Default number of trucks per year for NEN-EN 1991-2

# Reference period values for load factor calculations
REFERENCE_PERIOD_AFKEUR = 15  # Years for NEN 8700 afkeur design code
REFERENCE_PERIOD_DEFAULT = 30  # Years for other design codes (gebruik, verbouw)

# Signage options (must match app/constants/technical.py SIGNAGE_OPTIONS)
SIGNAGE_WEIGHT_OPTIONS = ["50 ton", "45 ton", "40 ton", "35 ton", "30 ton", "25 ton", "20 ton"]

# Temperature loads
DELTA_T_N_CON = 27  # Constant temperature component for contraction
DELTA_T_N_EXP = 22  # Constant temperature component for expansion
W_N = 0.35  # Load combination factor
W_M = 0.75  # Load combination factor
