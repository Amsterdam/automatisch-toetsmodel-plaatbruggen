# SCIA Engineer Integration

This document describes the SCIA Engineer integration for the automatic bridge assessment tool.

## Overview

The SCIA integration allows users to generate SCIA Engineer models from bridge parameters defined in the VIKTOR interface. The integration follows a modular architecture with core logic in the `src` layer and VIKTOR-specific functionality in the `app` layer.

## Implementation

### Core Components

1. **`src/integrations/scia_interface.py`** - Core SCIA model creation logic
2. **`app/bridge/controller.py`** - VIKTOR views and download methods  
3. **`app/bridge/parametrization.py`** - Updated SCIA page with UI elements

### Features

#### Current Implementation (v1.0)

- **Simple Rectangular Plate Model**: Creates a basic rectangular plate approximation of the bridge
- **Bridge Geometry Extraction**: Calculates dimensions from bridge segment parameters
- **Material Definition**: Uses standard concrete material (C30/37) 
- **Preview Functionality**: 3D preview of the SCIA model geometry
- **File Downloads**: 
  - XML files for import into SCIA Engineer
  - Complete ESA model files (when SCIA worker is available)

#### Bridge Geometry Calculation

**Length**: Sum of all segment lengths (`Afstand tot vorige snede`)
```python
total_length = sum(segment.l for segment in bridge_segments_array)
```

**Width**: Uses first segment width only (simplified)
```python
total_width = first_segment.bz1 + first_segment.bz2 + first_segment.bz3
```

**Thickness**: Hardcoded to 0.5m (needs enhancement)
```python
thickness = 0.5  # TODO: Use variable thickness per zone
```

### SCIA Page Interface

The SCIA page provides:

1. **Model Preview**: 3D visualization of the rectangular plate model
2. **Download XML Files**: ZIP containing XML and definition files for SCIA import
3. **Download ESA Model**: Complete SCIA model file (requires SCIA worker)
4. **Information Panel**: Explains current limitations and future enhancements

### File Structure

```
automatisch-toetsmodel-plaatbruggen/
├── src/integrations/
│   ├── __init__.py
│   └── scia_interface.py           # Core SCIA logic
├── app/bridge/
│   ├── controller.py               # VIKTOR integration methods
│   └── parametrization.py          # Updated SCIA page
├── tests/test_src/test_integrations/
│   ├── __init__.py
│   └── test_scia_interface.py      # Unit tests
├── resources/templates/
│   └── model.esa                   # SCIA template file
└── README_SCIA_INTEGRATION.md      # This file
```

## Usage

### For Users

1. Navigate to the **SCIA** page in the bridge entity
2. View the 3D preview of the model that will be sent to SCIA
3. Use download buttons to get SCIA files:
   - **XML Files**: For manual import into SCIA Engineer
   - **ESA Model**: Complete model file (if SCIA worker available)

### For Developers

#### Creating a SCIA Model Programmatically

```python
from src.integrations.scia_interface import create_bridge_scia_model
from pathlib import Path

# Bridge segment data
bridge_segments = [
    {"bz1": 10.0, "bz2": 5.0, "bz3": 15.0, "l": 0, "dz": 2.0, "dz_2": 3.0},
    {"bz1": 10.0, "bz2": 5.0, "bz3": 15.0, "l": 25, "dz": 2.0, "dz_2": 3.0},
]

# Template path
template_path = Path("resources/templates/model.esa")

# Create SCIA model
xml_file, def_file, scia_analysis = create_bridge_scia_model(bridge_segments, template_path)
```

#### Testing

Run the SCIA integration tests:
```bash
cd automatisch-toetsmodel-plaatbruggen
python -m pytest tests/test_src/test_integrations/test_scia_interface.py -v
```

## Future Enhancements

### High Priority

1. **Complex Bridge Geometry**: Support actual bridge shape (1:1 with segments)
   - Variable width along bridge length
   - Proper handling of all bridge segments
   - Support for non-rectangular bridge outlines

2. **Variable Thickness**: Use actual thickness parameters
   - Zone 1 & 3: Use `dz` parameter
   - Zone 2: Use `dz_2` parameter
   - Interpolation between segments

3. **Load Cases**: Add support for bridge loading
   - Dead loads
   - Live loads (traffic, pedestrians)
   - Load combinations per Eurocode

### Medium Priority

4. **Material Customization**: Allow material property selection
5. **Mesh Refinement**: Configurable mesh parameters
6. **Reinforcement Integration**: Include reinforcement from parametrization
7. **Results Processing**: Parse SCIA results back into VIKTOR

### Low Priority

8. **Multiple Bridge Types**: Support for different bridge configurations
9. **Advanced Analysis**: Dynamic analysis, buckling, etc.
10. **Report Integration**: Include SCIA results in reports

## Technical Details

### Dependencies

- **VIKTOR SDK**: Required for SCIA module and File handling
- **SCIA Engineer**: Version 24.0.3015.64 (specified by user)
- **SCIA Worker**: Required for ESA model generation

### Template File

The integration uses `resources/templates/model.esa` as a base template. This file must:
- Be created in SCIA Engineer version 24.0.3015.64
- Contain an I/O document named "output"
- Have matching material definitions

### Error Handling

The integration provides user-friendly error messages for common issues:
- Missing bridge segments
- Invalid geometry parameters
- SCIA worker unavailability
- Template file problems

### Testing Strategy

Tests cover:
- Bridge geometry extraction logic
- SCIA model creation (with mocks)
- File handling and validation
- Error conditions and edge cases

## Known Limitations

1. **Simplified Geometry**: Only rectangular plate approximation
2. **Single Material**: Only concrete, no customization
3. **Fixed Thickness**: No variable thickness support
4. **No Loads**: Load cases not implemented yet
5. **SCIA Worker Dependency**: ESA download requires worker setup

## Version History

- **v1.0** (Current): Basic rectangular plate model with download functionality
- **v2.0** (Planned): Complex geometry and variable thickness
- **v3.0** (Planned): Load cases and combinations