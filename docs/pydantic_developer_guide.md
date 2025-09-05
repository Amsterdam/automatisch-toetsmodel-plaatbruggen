# Pydantic Developer Guide

## What is Pydantic?

Pydantic is a Python library that provides **data validation** and **type safety** using Python type hints. Think of it as a smart way to ensure your data is correct before your code uses it.

### How Pydantic Works

Pydantic uses Python's **type hints** (like `str`, `int`, `float`) to automatically:
1. **Validate** that data matches the expected types
2. **Convert** data to the correct types when possible (e.g., "123" → 123)
3. **Reject** data that can't be converted or doesn't meet requirements
4. **Provide clear error messages** when validation fails

The magic happens when you create an object from your data - Pydantic runs all the validation automatically and either gives you a valid object or tells you exactly what's wrong.

### Why We Use Pydantic

**Before Pydantic (Manual Validation):**
```python
def validate_load_zone(data: dict) -> bool:
    if "zone_type" not in data:
        raise KeyError("Missing zone_type")
    if data["zone_type"] not in ["Auto", "Voetgangers", "Fietsers", "Berm"]:
        raise ValueError("Invalid zone_type")
    if "pavement_thickness" not in data:
        raise KeyError("Missing pavement_thickness")
    if not isinstance(data["pavement_thickness"], (int, float)):
        raise ValueError("pavement_thickness must be a number")
    if data["pavement_thickness"] <= 0 or data["pavement_thickness"] > 0.5:
        raise ValueError("pavement_thickness must be between 0 and 0.5 meters")
    # ... 20+ more lines of validation
    return True
```

**With Pydantic (Automatic Validation):**
```python
from pydantic import BaseModel, Field

# [What is a class?](#what-is-a-class) - A blueprint for creating objects with validation rules
class LoadZoneData(BaseModel):
    zone_type: str = Field(description="Type of load zone")
    pavement_thickness: float = Field(gt=0, le=0.5, description="Pavement thickness in meters")
    
    # [What is @field_validator?](#what-is-field_validator) - Custom validation function that runs automatically
    @field_validator('zone_type')
    # [What is @classmethod?](#what-is-classmethod) - Method that belongs to the class, not individual objects
    @classmethod
    def validate_zone_type(cls, v: str) -> str:
        valid_types = ["Auto", "Voetgangers", "Fietsers", "Berm"]
        if v not in valid_types:
            raise ValueError(f"Zone type must be one of: {valid_types}")
        return v

# Usage: Automatic validation happens when you create the object
# [What is an object?](#what-is-an-object) - An instance created from a class blueprint
zone = LoadZoneData(zone_type="Auto", pavement_thickness=0.1)  # ✅ Valid
zone = LoadZoneData(zone_type="Invalid", pavement_thickness=2.0)  # ❌ Raises ValidationError
```

---

## When to Use Pydantic

### Understanding the Validation Landscape

In our application, we have **three layers of validation** that work together:

1. **VIKTOR UI Validation** - Catches user input errors in the interface
2. **MyPy Static Type Checking** - Catches type errors before code runs  
3. **Pydantic Runtime Validation** - Catches business rule violations when data is processed

Each layer catches different types of problems and they complement each other perfectly.

### 🤔 **But VIKTOR Already Has Input Validation!**

You're absolutely right! VIKTOR has excellent built-in validation for:
- **Numeric constraints** - min/max boundaries on NumberField
- **Option validation** - ensures selected options exist in OptionField
- **Format validation** - coordinates, colors, dates in their respective fields
- **Custom validation** - with `UserError` and `InputViolation` for complex rules

**So why do we need Pydantic too?** Here's the key insight:

**VIKTOR validation happens in the UI layer** - it prevents bad data from reaching your controller methods. But once data leaves the VIKTOR interface and enters your business logic, you need **additional validation** to ensure data integrity throughout your application.

Think of it like airport security:
- **VIKTOR** = Security checkpoint at the entrance (catches obvious problems)
- **Pydantic** = Additional checks throughout the terminal (catches subtle business rule violations)

### 🔍 **But We Already Have MyPy for Type Safety!**

You're absolutely correct! We already use MyPy for static type checking, which is fantastic for:
- **Catching type errors** before code runs (during development)
- **Ensuring type consistency** - `width: float` means it should be a float
- **Preventing type mismatches** - like `bridge.width + "hello"`
- **IDE support** - autocomplete and type hints
- **Quality assurance** - runs in our `ruft.py` quality checks

**So why do we need Pydantic too?** Here's the crucial difference:

**MyPy works at development time** - it analyzes your code and tells you about potential type issues. But it can't validate **actual data** that comes from users, APIs, or files at runtime.

Think of it like this:
- **MyPy** = Code reviewer who checks your code before you commit
- **Pydantic** = Security guard who checks every person (data) entering your building

| Tool | What It Does | When It Runs | Example |
|------|--------------|--------------|---------|
| **MyPy** | Static type checking | Before code runs | `width: float` - "This should be a float" |
| **Pydantic** | Runtime data validation | When code runs | `width: float = Field(gt=0, le=50)` - "This IS a float between 0-50" |

**MyPy catches:** `bridge.width + "hello"` (type error)  
**Pydantic catches:** `BridgeData(width=-5.0)` (business rule violation)

### 🤝 **How All Three Tools Work Together:**

Here's how our **three-layer validation system** protects your application:

1. **VIKTOR UI Layer** - Catches user input errors before they reach your code
   - "You can't enter a negative width"
   - "That option doesn't exist in the dropdown"
   - "Please enter a valid date format"

2. **MyPy Development Layer** - Catches type errors before code runs
   - "You're trying to add a string to a number"
   - "This function expects a float but you're passing a string"
   - "You're missing a required parameter"

3. **Pydantic Runtime Layer** - Catches business rule violations when data is processed
   - "Auto zones need at least 5cm pavement thickness"
   - "This material doesn't exist in our database"
   - "The bridge width is too narrow for this load combination"

**They work together like a security system:**
- **VIKTOR** = Front door security (stops obvious problems at the entrance)
- **MyPy** = Building inspector (checks the structure before it's used)
- **Pydantic** = Security cameras (monitors what's happening inside the building)

**The result:** Your application is protected at every level, with clear error messages that help users and developers fix problems quickly.

### ✅ **Use Pydantic When:**

Now that you understand the validation landscape, here are the specific scenarios where Pydantic adds the most value:

1. **Complex Business Rules** - VIKTOR can't handle cross-field validation
   ```python
   # VIKTOR can't validate: "Auto zones need thicker pavement than pedestrian zones"
   @model_validator(mode="after")
   def validate_business_rules(self) -> 'LoadZoneData':
       if self.zone_type == ZoneType.AUTO and self.pavement_thickness < 0.05:
           raise ValueError("Auto zones require minimum 5cm pavement thickness")
       return self
   ```
   **Why Pydantic?** VIKTOR validates individual fields, but business rules often depend on multiple fields together.

2. **Data Processing After VIKTOR** - Once data leaves the UI, you need validation
   ```python
   # VIKTOR validates the input, but what about data transformations?
   processed_data = LoadZoneData.from_params_dict(params["load_zones"][0])
   # Now you have validated, type-safe data for calculations
   ```
   **Why Pydantic?** Data can become invalid during processing, transformations, or when passed between functions.

3. **External API Integration** - Data from SCIA, IDEA StatiCa, etc.
   ```python
   # VIKTOR can't validate external API responses
   scia_result = SciaAnalysisResult.model_validate_json(response_data)
   ```
   **Why Pydantic?** External APIs can return unexpected data structures or values that break your application.

4. **Data Transfer Between Modules** - Runtime validation + type safety
   ```python
   # MyPy gives you static type checking, Pydantic adds runtime validation
   bridge_config = BridgeSegmentDimensions.from_params_dict(params["bridge"])
   # MyPy: "bridge_config.width is a float" (compile time)
   # Pydantic: "bridge_config.width is actually 10.5 and within valid range" (runtime)
   ```
   **Why Pydantic?** MyPy can't validate actual data values, only types. Pydantic ensures the data makes sense.

5. **Configuration Objects** - Settings that need validation beyond UI constraints
   ```python
   # Material validation against project database
   material_config = MaterialConfig(concrete_type="C30/37", reinforcement_type="B500B")
   # VIKTOR can't check if materials exist in your CSV files
   ```
   **Why Pydantic?** Configuration data often comes from files or databases, not user input.

6. **Data Serialization/Deserialization** - Converting between formats
   ```python
   # Safe conversion to/from JSON, dictionaries
   zone_dict = zone_data.model_dump()  # Type-safe serialization
   zone_json = zone_data.model_dump_json()  # JSON with validation
   ```
   **Why Pydantic?** When converting data between formats, you need to ensure it remains valid.

7. **Testing** - Easier to test data validation logic
   ```python
   # Test business rules independently of VIKTOR UI
   def test_auto_zone_validation():
       with pytest.raises(ValidationError):
           LoadZoneData(zone_type=ZoneType.AUTO, pavement_thickness=0.01)  # Too thin!
   ```
   **Why Pydantic?** You can test business logic without setting up the entire VIKTOR UI.

### ❌ **Don't Use Pydantic When:**

Understanding when **not** to use Pydantic is just as important as knowing when to use it. Here are scenarios where Pydantic would be overkill:

1. **Simple Variables** - Basic types that don't need validation
   ```python
   # ❌ Overkill for simple variables
   name = "Bridge Name"  # Just use a string
   count = 5  # Just use an int
   
   # ✅ Good for complex data structures
   bridge_data = BridgeData(name="Bridge Name", width=10.0, height=2.5)
   ```
   **Why not Pydantic?** Pydantic adds overhead for simple operations. Use it when you have complex data structures with multiple fields and business rules.

2. **Performance-Critical Loops** - Where validation overhead matters
   ```python
   # ❌ Don't validate in tight loops
   for i in range(1000000):
       validated_number = NumberModel(value=i)  # Too slow!
   
   # ✅ Validate once, then use
   validated_config = ConfigModel(**data)
   for i in range(1000000):
       use_config(validated_config)  # Fast!
   ```
   **Why not Pydantic?** Validation has overhead. In performance-critical code, validate once outside the loop, then use the validated data inside.

3. **Temporary Data** - Short-lived variables that don't cross module boundaries
   ```python
   # ❌ Unnecessary for temporary calculations
   temp_result = TempData(x=1, y=2)  # Just use a dict or tuple
   
   # ✅ Good for data that gets passed around
   result = CalculationResult(x=1, y=2, z=3)  # Validated and type-safe
   ```
   **Why not Pydantic?** If data is only used locally and doesn't cross module boundaries, the validation overhead isn't worth it.

4. **Data That's Already Validated** - Don't validate the same data multiple times
   ```python
   # ❌ Redundant validation
   validated_zone = LoadZoneData(**data)  # Already validated
   validated_zone_again = LoadZoneData(**validated_zone.model_dump())  # Unnecessary!
   
   # ✅ Use the already-validated data
   result = calculate_something(validated_zone)  # Good!
   ```
   **Why not Pydantic?** Once data is validated, trust it. Re-validating the same data is wasteful.

### 🎯 **Our Project Guidelines:**

- **Use MyPy** for static type checking (you already do this!)
- **Use VIKTOR validation** for UI input constraints (min/max, options, etc.)
- **Use Pydantic** for complex business rules that VIKTOR can't handle
- **Use Pydantic** for data processing after it leaves the VIKTOR UI
- **Use Pydantic** for external API data (SCIA, IDEA StatiCa responses)
- **Use Pydantic** for runtime validation of business rules
- **Use Pydantic** for configuration objects with database validation
- **Skip Pydantic** for simple local variables and temporary calculations

### 🔄 **The Perfect Workflow:**

```python
# 1. VIKTOR validates user input in the UI
# 2. Data comes to controller as params
def some_controller_method(self, params, **kwargs):
    # 3. Pydantic validates business rules and data integrity
    zone_data = LoadZoneData.from_params_dict(params["load_zones"][0])
    
    # 4. MyPy ensures type safety (width is float, zone_type is str)
    # 5. Pydantic ensures business rules (width > 0, zone_type is valid)
    result = calculate_something(zone_data)
    
    # 6. Return results with confidence - data is both type-safe AND validated!
    return result
```

---

## Real Example from Our Codebase

Let's examine our `LoadZoneData` model from `src/data_models/load_models.py`:

```python
from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

# Import constants from src layer for single source of truth
from src.common.constants.parametrization import LOAD_ZONE_TYPES, PAVEMENT_MATERIAL_OPTIONS

class LoadZoneData(BaseModel):
    """
    Represents a single load zone with pavement and width data.
    
    Validates zone types, materials, and geometric constraints.
    """
    
    # Basic fields with validation
    zone_type: str = Field(description=f"Type of load zone ({', '.join(LOAD_ZONE_TYPES)})")
    pavement_thickness: float = Field(gt=0, le=0.5, description="Pavement thickness in meters (0-0.5m)")
    pavement_material: str = Field(description=f"Pavement material type ({', '.join(PAVEMENT_MATERIAL_OPTIONS)})")
    
    # Optional width fields for D-points 1-15
    d1_width: float | None = Field(default=None, ge=0, le=50, description="Width at D1 point in meters")
    d2_width: float | None = Field(default=None, ge=0, le=50, description="Width at D2 point in meters")
    # ... d3_width through d15_width (15 total D-fields)
    
    # Calculated fields (populated by system)
    zone_widths_per_d: list[float] = Field(default_factory=list, description="Calculated widths for each D-point")
    y_coords_top_current_zone: list[float] = Field(default_factory=list, description="Y-coordinates for zone top boundary")
    
    # Field validation against constants
    @field_validator("zone_type")
    @classmethod
    def validate_zone_type_against_constants(cls, v: str) -> str:
        """Validate zone type against constants - true single source of truth."""
        if v not in LOAD_ZONE_TYPES:
            valid_options = ", ".join(LOAD_ZONE_TYPES)
            raise ValueError(f"Invalid zone_type '{v}'. Must be one of: {valid_options}")
        return v
    
    @field_validator("pavement_material")
    @classmethod
    def validate_pavement_material_against_constants(cls, v: str) -> str:
        """Validate pavement material against constants - true single source of truth."""
        if v not in PAVEMENT_MATERIAL_OPTIONS:
            valid_options = ", ".join(PAVEMENT_MATERIAL_OPTIONS)
            raise ValueError(f"Invalid pavement_material '{v}'. Must be one of: {valid_options}")
        return v
    
    # Cross-field business rules using field validator with info.data
    @field_validator("pavement_thickness")
    @classmethod
    def validate_pavement_thickness_by_type(cls, v: float, info: ValidationInfo) -> float:
        """Validate pavement thickness based on zone type."""
        if info.data and "zone_type" in info.data:
            zone_type = info.data["zone_type"]
            if zone_type == "Auto" and v < 0.05:
                raise ValueError(f"Auto zones require minimum 5cm pavement thickness, got {v * 100:.1f}cm")
            if zone_type in ["Voetgangers", "Fietsers"] and v < 0.02:
                raise ValueError(f"{zone_type} zones require minimum 2cm pavement thickness, got {v * 100:.1f}cm")
        return v
    
    # Model configuration
    model_config = ConfigDict(
        validate_assignment=True,  # Validate when fields are changed after creation
        use_enum_values=True,      # Use enum values in serialization
    )
```

---

## Our Pydantic Models in Action

Our codebase contains several Pydantic models that demonstrate different validation patterns:

### **BridgeSegmentDimensions** - Simple Field Validation
```python
class BridgeSegmentDimensions(BaseModel):
    bz1: float = Field(gt=0, description="Bridge zone 1 width in meters")
    bz2: float = Field(gt=0, description="Bridge zone 2 width in meters")
    bz3: float = Field(gt=0, description="Bridge zone 3 width in meters")
    segment_length: float = Field(ge=0, description="Length to previous segment in meters")
    
    @field_validator("bz1", "bz2", "bz3")
    @classmethod
    def validate_zone_widths(cls, v: float) -> float:
        """Validate that bridge zone widths are reasonable (between 0.1m and 50m)."""
        if not 0.1 <= v <= 50.0:
            raise ValueError(f"Bridge zone width {v}m is unrealistic. Must be between 0.1m and 50m.")
        return v
```

### **LoadCombinationConfig** - Constants Integration
```python
class LoadCombinationConfig(BaseModel):
    cc_class: str = Field(description=f"Consequence class ({', '.join(CC_CLASS_OPTIONS)})")
    design_code: str = Field(description=f"Design code ({', '.join(DESIGN_CODE_OPTIONS)})")
    construction_year: int = Field(ge=1850, le=2100, description="Year of construction")
    
    @field_validator("cc_class", mode="before")
    @classmethod
    def validate_cc_class_format(cls, v: str) -> str:
        """Validate CC class against constants - true single source of truth."""
        v = v.strip() if isinstance(v, str) else v
        if v not in CC_CLASS_OPTIONS:
            raise ValueError(f"Invalid cc_class '{v}'. Must be one of: {', '.join(CC_CLASS_OPTIONS)}")
        return v
```

### **MaterialConfig** - Database Validation
```python
class MaterialConfig(BaseModel):
    concrete_type: str = Field(description="Concrete quality designation")
    reinforcement_type: str = Field(description="Reinforcement steel quality")
    prestress_type: str | None = Field(None, description="Prestressing steel quality (optional)")
    
    @field_validator("concrete_type")
    @classmethod
    def validate_concrete_exists(cls, v: str) -> str:
        """Validate concrete type exists in project database."""
        valid_concretes = get_concrete_qualities()
        if v not in valid_concretes:
            available = ", ".join(valid_concretes[:5])
            raise ValueError(f"Concrete type '{v}' not found in database. Available: {available}...")
        return v
```

### **BridgeBaseGeometry** - Complex Coordinate Validation
```python
class BridgeBaseGeometry(BaseModel):
    x_coords_d_points: list[float] = Field(min_length=1, max_length=15, description="X coordinates of D-points")
    y_coords_bridge_top_edge: list[float] = Field(min_length=1, max_length=15, description="Y coordinates of top edge")
    y_coords_bridge_bottom_edge: list[list[float]] = Field(min_length=1, max_length=15, description="Y coordinates of bottom edge")
    num_defined_d_points: int = Field(ge=1, le=15, description="Number of defined D-points")
    
    @field_validator("x_coords_d_points")
    @classmethod
    def validate_x_coords_ascending(cls, v: list[float]) -> list[float]:
        """Validate X coordinates are unique and in ascending order."""
        if len(v) != len(set(v)):
            raise ValueError("X coordinates must be unique (no duplicate D-points)")
        if v != sorted(v):
            raise ValueError("X coordinates must be in ascending order along bridge length")
        return v
```

---

## How to Define Different Types of Validation

### 1. **Built-in Field Constraints (Simple Validation)**

```python
# Numeric constraints
width: float = Field(gt=0, le=50, description="Bridge width in meters")
# gt = greater than, ge = greater than or equal, lt = less than, le = less than or equal

# String constraints  
bridge_name: str = Field(min_length=1, max_length=100, description="Bridge name")

# List constraints
coordinates: list[float] = Field(min_length=2, max_length=15, description="Bridge coordinates")

# Optional fields (can be None)
notes: str | None = Field(None, max_length=500, description="Optional notes")
```

### 2. **Custom Field Validators (Business Rules)**

```python
@field_validator('zone_type')  # Validates the 'zone_type' field
@classmethod
def validate_zone_type_against_constants(cls, v: str) -> str:
    """
    Custom validation function for zone_type field.
    - v: The value being validated
    - Must return the validated value
    - Raise ValueError if validation fails
    """
    from src.common.constants.parametrization import LOAD_ZONE_TYPES
    
    if v not in LOAD_ZONE_TYPES:
        available_options = ", ".join(LOAD_ZONE_TYPES)
        raise ValueError(f"Zone type '{v}' is not valid. Available options: {available_options}")
    
    return v  # IMPORTANT: Always return the value if it's valid!
```

### 3. **Cross-Field Validation (Multiple Fields Together)**

```python
@field_validator("pavement_thickness")
@classmethod
def validate_pavement_thickness_by_type(cls, v: float, info: ValidationInfo) -> float:
    """
    Validate pavement thickness based on zone type (business rule).
    - v: The pavement_thickness value being validated
    - info: ValidationInfo object that gives access to other field values
    """
    if info.data and "zone_type" in info.data:
        zone_type = info.data["zone_type"]  # Get the zone_type value
        
        # Business rule: Auto zones need thicker pavement
        if zone_type == "Auto" and v < 0.05:  # Less than 5cm
            raise ValueError(f"Auto zones require minimum 5cm pavement thickness, got {v*100:.1f}cm")
        
        # Business rule: Pedestrian/cycle zones need minimum thickness
        if zone_type in ["Voetgangers", "Fietsers"] and v < 0.02:
            raise ValueError(f"{zone_type} zones require minimum 2cm pavement thickness, got {v*100:.1f}cm")
    
    return v  # Return the value if all checks pass
```

**Note:** In our current implementation, we use `field_validator` with `info.data` for cross-field validation. This works well for simple cases. For more complex cross-field validation, consider using `@model_validator(mode="after")` as shown in the advanced examples.

### 4. **Database/External Validation**

```python
@field_validator("concrete_type")
@classmethod
def validate_concrete_exists(cls, v: str) -> str:
    """Validate concrete type exists in project database."""
    from src.common.materials import get_concrete_qualities
    
    valid_concretes = get_concrete_qualities()  # Returns list from CSV files
    if v not in valid_concretes:
        available = ", ".join(valid_concretes[:5])
        raise ValueError(f"Concrete type '{v}' not found in database. Available: {available}...")
    return v
```

---

## How to Use Pydantic Models

### **Creating Objects**

```python
# Valid data
zone = LoadZoneData(
    zone_type="Auto",
    pavement_thickness=0.1,
    pavement_material="Asfalt",
    d1_width=3.5
)

# Access fields
print(zone.zone_type)  # "Auto"
print(zone.pavement_thickness)  # 0.1
```

### **Handling Validation Errors**

```python
from pydantic import ValidationError

try:
    zone = LoadZoneData(
        zone_type="InvalidType",  # ❌ Not in LOAD_ZONE_TYPES
        pavement_thickness=2.0,   # ❌ Too thick (> 0.5m)
        pavement_material="Asfalt"
    )
except ValidationError as e:
    # Simple error message
    print(str(e))
    # "2 validation errors for LoadZoneData..."
    
    # Structured error details for better handling
    for error in e.errors():
        print(f"Field: {error['loc']}")
        print(f"Message: {error['msg']}")
        print(f"Type: {error['type']}")
        # Field: ('zone_type',)
        # Message: Invalid zone_type 'InvalidType'. Must be one of: Auto, Voetgangers, Fietsers, Berm, Emergency
        # Type: value_error
```

### **Converting from Dictionaries**

```python
# From VIKTOR params (common pattern)
params_data = {
    "zone_type": "Auto",
    "pavement_thickness": 0.1,
    "pavement_material": "Asfalt"
}

zone = LoadZoneData.from_params_dict(params_data)
# OR
zone = LoadZoneData(**params_data)
```

### **Converting to Dictionaries**

```python
zone = LoadZoneData(zone_type="Auto", pavement_thickness=0.1, pavement_material="Asfalt")

# Basic serialization
zone_dict = zone.model_dump()
print(zone_dict)
# {'zone_type': 'Auto', 'pavement_thickness': 0.1, 'pavement_material': 'Asfalt', ...}

# Exclude None values (useful for API responses)
zone_dict_clean = zone.model_dump(exclude_none=True)
print(zone_dict_clean)
# {'zone_type': 'Auto', 'pavement_thickness': 0.1, 'pavement_material': 'Asfalt'}

# To JSON with options
zone_json = zone.model_dump_json(exclude_none=True)
print(zone_json)
# '{"zone_type":"Auto","pavement_thickness":0.1,"pavement_material":"Asfalt"}'

# With aliases (if you define them)
zone_json_aliased = zone.model_dump_json(by_alias=True, exclude_none=True)
```

---

## Best Practices for Our Codebase

### 1. **Always Use Constants**

```python
# ✅ Good - Import from constants
from src.common.constants.parametrization import LOAD_ZONE_TYPES

@field_validator('zone_type')
@classmethod
def validate_zone_type_exists(cls, v: str) -> str:
    if v not in LOAD_ZONE_TYPES:  # Single source of truth
        raise ValueError(f"Zone type '{v}' not valid. Available: {', '.join(LOAD_ZONE_TYPES)}")
    return v

# ❌ Bad - Hardcoded values
@field_validator('zone_type')
@classmethod
def validate_zone_type_exists(cls, v: str) -> str:
    if v not in ["Auto", "Voetgangers"]:  # Duplicated, can get out of sync
        raise ValueError("Invalid zone type")
    return v
```

### 2. **Provide Clear Error Messages**

```python
# ✅ Good - Helpful error message
if v not in LOAD_ZONE_TYPES:
    available = ", ".join(LOAD_ZONE_TYPES)
    raise ValueError(f"Zone type '{v}' not valid. Available: {available}")

# ❌ Bad - Unclear error message
if v not in LOAD_ZONE_TYPES:
    raise ValueError("Invalid zone type")
```

### 3. **Use from_params_dict for VIKTOR Integration**

```python
@classmethod
def from_params_dict(cls, params: dict) -> 'LoadZoneData':
    """Create LoadZoneData from VIKTOR params dictionary."""
    return cls(**params)

# Usage in controllers
def some_controller_method(self, params, **kwargs):
    try:
        zone_data = LoadZoneData.from_params_dict(params["load_zones"][0])
        # Use zone_data with confidence - it's validated!
    except ValidationError as e:
        raise UserError(f"Invalid load zone data: {e}")
```

---

## Testing Pydantic Models

Always test both **valid** and **invalid** scenarios:

```python
import pytest
from pydantic import ValidationError
from src.data_models.load_models import LoadZoneData

class TestLoadZoneData:
    def test_valid_zone_creation(self):
        """Test creating a valid load zone."""
        zone = LoadZoneData(
            zone_type="Auto",
            pavement_thickness=0.1,
            pavement_material="Asfalt",
            d1_width=3.5
        )
        assert zone.zone_type == "Auto"
        assert zone.pavement_thickness == 0.1

    def test_invalid_zone_type_rejected(self):
        """Test that invalid zone types are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            LoadZoneData(
                zone_type="InvalidType",  # Not in LOAD_ZONE_TYPES
                pavement_thickness=0.1,
                pavement_material="Asfalt"
            )
        
        error_message = str(exc_info.value)
        assert "Invalid zone_type 'InvalidType'" in error_message
        assert "Must be one of:" in error_message

    def test_assignment_revalidation(self):
        """Test that field changes are revalidated."""
        zone = LoadZoneData(
            zone_type="Auto",
            pavement_thickness=0.1,
            pavement_material="Asfalt"
        )
        
        # This should work
        zone.pavement_thickness = 0.15
        
        # This should fail
        with pytest.raises(ValidationError):
            zone.pavement_thickness = 0.01  # Too thin for Auto zone

    def test_cross_field_business_rules(self):
        """Test business rules that depend on multiple fields."""
        # Auto zone with too thin pavement
        with pytest.raises(ValidationError) as exc_info:
            LoadZoneData(
                zone_type="Auto",
                pavement_thickness=0.01,  # Too thin for Auto
                pavement_material="Asfalt"
            )
        
        assert "Auto zones require minimum 5cm" in str(exc_info.value)
```

---

## Advanced Features

### **Function Input Validation**

For controller methods and utilities, you can validate function inputs automatically:

```python
from pydantic import validate_call

@validate_call
def design_load(width: float, *, zone: LoadZoneData) -> float:
    """
    Design load calculation with automatic input validation.
    
    - width: Bridge width (validated as positive float)
    - zone: Load zone data (validated as LoadZoneData instance)
    """
    # Function automatically validates inputs before execution
    return width * zone.pavement_thickness * 1.5

# Usage - validation happens automatically
result = design_load(10.0, zone=zone_data)  # ✅ Valid
result = design_load(-5.0, zone=zone_data)  # ❌ ValidationError: width must be positive
```

### **Strict Mode for Critical Paths**

For security-critical or performance-critical code, disable automatic type coercion:

```python
from pydantic import StrictFloat, StrictStr

class CriticalConfig(BaseModel):
    """Configuration for critical calculations - no type coercion allowed."""
    precision: StrictFloat = Field(gt=0, le=1)  # Must be exactly float
    algorithm: StrictStr = Field(min_length=1)  # Must be exactly string
    
    model_config = ConfigDict(strict=True)  # Strict mode for entire model
```

---

## Quick Reference

### **Field Constraints:**
- `gt=5` - Greater than 5
- `ge=5` - Greater than or equal to 5  
- `lt=10` - Less than 10
- `le=10` - Less than or equal to 10
- `min_length=1` - Minimum string/list length
- `max_length=50` - Maximum string/list length

### **Common Field Types:**
- `str` - String
- `int` - Integer
- `float` - Float
- `bool` - Boolean
- `list[float]` - List of floats
- `str | None` - Optional string
- `datetime` - Date and time

### **Essential Methods:**
- `model_dump()` - Convert to dictionary
- `model_dump_json()` - Convert to JSON string
- `from_params_dict(params)` - Create from VIKTOR params (our custom method)

---

## Technical Concepts Reference

### **Why Create a Class?**

```python
# Instead of using a dictionary (error-prone):
load_zone = {"zone_type": "Auto", "pavement_thickness": 0.1}
# Problems: No validation, typos allowed, no IDE support

# We create a class (safe and validated):
class LoadZoneData(BaseModel):
    """A class is like a blueprint or template for creating objects."""
    zone_type: str = Field(description="Type of load zone")
    pavement_thickness: float = Field(gt=0, le=0.5, description="Pavement thickness in meters")

# Benefits: Automatic validation, IDE autocomplete, clear structure
```

### **What is an Object?**

```python
# The class is the blueprint, the object is the actual instance
class LoadZoneData(BaseModel):  # This is the CLASS (blueprint)
    zone_type: str = Field(description="Type of load zone")

# Creating objects (instances) from the class:
zone1 = LoadZoneData(zone_type="Auto", pavement_thickness=0.1)      # This is an OBJECT
zone2 = LoadZoneData(zone_type="Fietsers", pavement_thickness=0.05) # This is another OBJECT

# Each object has its own data, but follows the same rules (class definition)
print(zone1.zone_type)  # "Auto"
print(zone2.zone_type)  # "Fietsers"
```

### **What is @classmethod?**

```python
class LoadZoneData(BaseModel):
    zone_type: str = Field(description="Type of load zone")
    
    @classmethod  # This decorator means "this method belongs to the CLASS, not to individual objects"
    def from_params_dict(cls, params: dict) -> 'LoadZoneData':
        """
        cls = the class itself (LoadZoneData)
        This method can be called WITHOUT creating an object first
        It's like a factory method - it creates and returns a new object
        """
        return cls(**params)  # cls(**params) is the same as LoadZoneData(**params)

# Usage - we call it on the CLASS, not on an object:
params = {"zone_type": "Auto", "pavement_thickness": 0.1}
zone = LoadZoneData.from_params_dict(params)  # Called on the CLASS
# NOT: zone.from_params_dict(params)  # This would be wrong - we don't have a zone object yet!
```

### **What is @field_validator?**

```python
class LoadZoneData(BaseModel):
    zone_type: str = Field(description="Type of load zone")
    
    @field_validator('zone_type')  # This decorator says "run this function when zone_type is set"
    @classmethod                   # Must be @classmethod because it's called during object creation
    def validate_zone_type_exists(cls, v: str) -> str:
        """
        This is a CUSTOM VALIDATION FUNCTION
        - It runs automatically when someone tries to set zone_type
        - v = the value someone is trying to set
        - cls = the class (we usually don't need this in validators)
        - Must return the value (possibly modified)
        - Raise ValueError if the value is invalid
        """
        valid_types = ["Auto", "Voetgangers", "Fietsers", "Berm"]
        
        if v not in valid_types:
            raise ValueError(f"Zone type '{v}' not valid. Available: {', '.join(valid_types)}")
        
        return v  # Return the value if it's valid (required!)

# When this runs:
zone = LoadZoneData(zone_type="Auto", pavement_thickness=0.1)
# 1. Pydantic sees zone_type="Auto"
# 2. Pydantic calls validate_zone_type_exists("Auto")
# 3. Function checks if "Auto" is in valid_types
# 4. It is, so function returns "Auto"
# 5. Pydantic sets zone_type = "Auto"
```


---

## Summary

Pydantic transforms error-prone manual validation into **automatic, reliable, and self-documenting** data validation. In our codebase:

1. **Replace manual validation functions** with Pydantic models
2. **Use constants** for single source of truth
3. **Provide clear error messages** that help users fix problems
4. **Test both valid and invalid scenarios** thoroughly
5. **Follow our established patterns** for consistency

**Result:** More robust code, fewer bugs, and better developer experience!