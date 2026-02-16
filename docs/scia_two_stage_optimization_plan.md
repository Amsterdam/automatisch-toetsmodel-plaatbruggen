# SCIA Two-Stage Calculation Optimization Plan

## Executive Summary

**Goal:** Optimize SCIA calculations by splitting into two stages to dramatically reduce data extraction time.

**Problem:** Current implementation models all integration strips and exports full results, creating large XML output files (potentially >100MB) that take significant time to parse and process in the VIKTOR worker.

**Solution:** Two-stage calculation approach:
1. **Stage 1 (Governing Analysis):** Model ALL integration strips → Export ONLY governing results → Identify critical strips
2. **Stage 2 (Detailed Analysis):** Model ONLY governing strips → Export FULL results → Fast processing due to reduced data size

**Expected Benefits:**
- 70-90% reduction in result extraction time
- Smaller XML output files for stage 2
- Faster worker processing
- Same accuracy (all strips analyzed, only governing strips detailed)

---

## Current Architecture Analysis

### Current Workflow

```
User Request → Cache Check → Build SCIA Model → Run Analysis → Extract ALL Results → Process → Display
                    ↓                              ↓                    ↓
              Check Hash       Create All Strips     Export Full XML    Parse Large XML
                                  (100-500+)          (10-100+ MB)      (5-30 seconds)
```

### Key Components

1. **Model Building** ([app/bridge/scia_model_builder.py](c:\PyCharm\automatisch-toetsmodel-plaatbruggen\app\bridge\scia_model_builder.py))
   - `ViktorSciaModelBuilder` class: Creates SCIA model using VIKTOR SDK
   - `define_complete_bridge_model()`: Orchestrates model creation
   - `_create_integration_strips()`: Creates 100-500+ strips depending on bridge geometry

2. **Integration Strip Creation** ([src/integrations/scia_integration/model/scia_integration_strips.py](c:\PyCharm\automatisch-toetsmodel-plaatbruggen\src\integrations\scia_integration\model\scia_integration_strips.py))
   - Creates strips in X and Y directions
   - Regular strips: Cover zone surface between supports
   - Support strips: Special strips near support locations
   - Typical bridge: 50-200 strips per direction × 2 directions × 2 types = 200-800 total strips

3. **Analysis Execution** ([app/bridge/scia_model_builder.py](c:\PyCharm\automatisch-toetsmodel-plaatbruggen\app\bridge\scia_model_builder.py))
   - `run_analysis()`: Executes SCIA calculation with template
   - `extract_analysis_results()`: Parses XML output (SLOW for large files)
   - Template path: `resources/templates/model.esa`

4. **Result Processing** ([src/integrations/scia_integration/results/scia_integration_strips_processor.py](c:\PyCharm\automatisch-toetsmodel-plaatbruggen\src\integrations\scia_integration\results\scia_integration_strips_processor.py))
   - `extract_all_integration_strip_tables()`: Parses 8 result tables (ULS/SLS × x/y × reg/sup)
   - `process_integration_strip_envelopes()`: Identifies governing strips with min/max forces
   - **Key insight:** Envelope identifies ~5-10% of strips as governing

5. **Caching** ([app/bridge/analysis_cache.py](c:\PyCharm\automatisch-toetsmodel-plaatbruggen\app\bridge\analysis_cache.py))
   - `get_cached_analysis_results()`: Hash-based caching
   - Stores entire result dictionary including XML output

6. **Templates** ([resources/templates/](c:\PyCharm\automatisch-toetsmodel-plaatbruggen\resources\templates))
   - `model.esa`: Current template with full result export configuration
   - **New:** Will need `model_governing.esa` for stage 1

---

## Detailed Implementation Plan

### Phase 1: Infrastructure Setup (Week 1)

#### Task 1.1: Create New Template for Governing Results
**Priority:** HIGH  
**Dependencies:** User creating SCIA template  
**Files:** `resources/templates/model_governing.esa`

1. User will create SCIA template that exports only governing/envelope results
2. Configure result classes to output min/max values only
3. Test template manually in SCIA Engineer to verify output format

**Success Criteria:**
- Template exists and is committed to repo
- XML output from template contains only envelope/governing data
- Output file size is <10% of full results

#### Task 1.2: Add Template Path Constants
**Files to modify:**
- [app/constants/paths.py](c:\PyCharm\automatisch-toetsmodel-plaatbruggen\app\constants\paths.py)

```python
# Add new constant
SCIA_TEMPLATE_PATH_GOVERNING = PROJECT_PATH / "resources" / "templates" / "model_governing.esa"
```

**Success Criteria:**
- New constant available throughout application
- Template path validation works

#### Task 1.3: Create Data Models for Two-Stage Results
**Files to modify:**
- [src/data_models/scia_models.py](c:\PyCharm\automatisch-toetsmodel-plaatbruggen\src\data_models\scia_models.py)

**New Models:**
```python
class GoverningStripIdentifier(BaseModel):
    """Identifies a governing integration strip from stage 1 analysis."""
    zone: str = Field(description="Zone identifier (e.g., 'Z1-1')")
    direction: str = Field(description="Strip direction 'x' or 'y'")
    strip_type: str = Field(description="'reg' or 'sup'")
    strip_number: int = Field(description="Strip number within zone")
    strip_name: str = Field(description="Full strip name from SCIA")
    force_type: str = Field(description="Which force is governing (N, V_y, M_x, etc.)")
    envelope_type: str = Field(description="'min' or 'max'")
    
class TwoStageSciaResults(BaseModel):
    """Results from two-stage SCIA analysis."""
    stage1_results: dict[str, Any] = Field(description="Governing results from stage 1")
    stage2_results: dict[str, Any] | None = Field(description="Full results from stage 2")
    governing_strips: list[GoverningStripIdentifier] = Field(description="List of governing strips")
    optimization_stats: dict[str, Any] = Field(description="Performance metrics")
```

**Success Criteria:**
- Models validate correctly
- Fields match expected SCIA output structure

### Phase 2: Core Implementation (Week 2-3)

#### Task 2.1: Create Governing Strip Identifier Function
**Files to modify:**
- [src/integrations/scia_integration/results/scia_integration_strips_processor.py](c:\PyCharm\automatisch-toetsmodel-plaatbruggen\src\integrations\scia_integration\results\scia_integration_strips_processor.py)

**New Function:**
```python
def identify_governing_strips(envelope_df: pd.DataFrame) -> list[dict[str, Any]]:
    """
    Extract list of governing strip identifiers from envelope DataFrame.
    
    From the envelope DataFrame (which has one row per min/max force value),
    extract the unique strip names that are governing for any force component.
    
    Returns:
        List of dicts with strip identification info:
        - strip_name: Full SCIA strip name
        - zone: Zone identifier
        - direction: 'x' or 'y'
        - strip_type: 'reg' or 'sup'
        - governing_for: List of force types this strip governs
    """
    pass  # Implementation here
```

**Logic:**
1. Parse envelope DataFrame
2. Extract unique strip names from all envelope rows
3. Group by strip to identify which forces each strip governs
4. Return structured list

**Success Criteria:**
- Function returns correct list of governing strips
- Typical reduction: 500 total strips → 30-50 governing strips (90-94% reduction)
- Unit tests pass

#### Task 2.2: Create Selective Strip Model Builder
**Files to modify:**
- [src/integrations/scia_integration/model/scia_integration_strips.py](c:\PyCharm\automatisch-toetsmodel-plaatbruggen\src\integrations\scia_integration\model\scia_integration_strips.py)

**New Function:**
```python
def create_integration_strips_selective(
    builder: SciaModelBuilder,
    params: Any,
    governing_strip_names: set[str],
) -> None:
    """
    Create ONLY the integration strips specified in governing_strip_names.
    
    This is used for Stage 2 analysis where we model only the governing strips
    identified from Stage 1.
    
    Args:
        builder: SCIA model builder instance
        params: Bridge parameters
        governing_strip_names: Set of strip names to create (e.g., {'strip_dir-x_reg_Z1-1_w-1.0_nr-1', ...})
    """
    pass  # Implementation here
```

**Logic:**
1. Reuse existing strip creation logic but with filtering
2. Before creating a strip, check if its name is in `governing_strip_names`
3. Only call `builder.create_integration_strip()` for governing strips

**Success Criteria:**
- Creates exact strips specified in input set
- Preserves all strip properties (geometry, position, etc.)
- Integration tests verify correct strip creation

#### Task 2.3: Implement Two-Stage Analysis Orchestrator
**Files to modify:**
- [app/bridge/scia_model_builder.py](c:\PyCharm\automatisch-toetsmodel-plaatbruggen\app\bridge\scia_model_builder.py)

**New Function:**
```python
def run_two_stage_scia_analysis(
    params: Any,
    governing_template_path: Path,
    full_template_path: Path,
    analysis_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Execute two-stage SCIA analysis optimization.
    
    Stage 1: Model all strips, export governing results only
    Stage 2: Model only governing strips, export full results
    
    Returns:
        Combined results dictionary with both stages and optimization metrics
    """
    pass  # Implementation here
```

**Detailed Algorithm:**
```python
def run_two_stage_scia_analysis(params, governing_template_path, full_template_path, analysis_context=None):
    # === STAGE 1: Governing Analysis ===
    progress_message("Stage 1: Analyseer met alle strips (governing results)...")
    
    # Build model with ALL strips (existing logic)
    builder_stage1 = ViktorSciaModelBuilder()
    define_complete_bridge_model(builder_stage1, params)  # Creates all strips
    
    # Run with governing template
    xml_file, def_file = builder_stage1.generate_xml_input()
    esa_template_gov = File.from_path(governing_template_path)
    analysis_stage1 = builder_stage1.run_analysis(xml_file, def_file, esa_template_gov)
    
    # Extract governing results (small XML output)
    progress_message("Stage 1: Extraheren governing resultaten...")
    results_stage1 = builder_stage1.extract_analysis_results(analysis_stage1)
    
    # Process to identify governing strips
    progress_message("Identificeren governing strips...")
    processed_strips_stage1 = process_all_integration_strips(results_stage1)
    envelope_df = processed_strips_stage1["envelope"]
    governing_strips_list = identify_governing_strips(envelope_df)
    governing_strip_names = {strip["strip_name"] for strip in governing_strips_list}
    
    # Log statistics
    total_strips = len(builder_stage1.integration_strips)
    governing_count = len(governing_strip_names)
    reduction_pct = (1 - governing_count / total_strips) * 100
    logger.info(f"Governing strips: {governing_count}/{total_strips} ({reduction_pct:.1f}% reduction)")
    
    # === STAGE 2: Detailed Analysis ===
    progress_message(f"Stage 2: Analyseer met {governing_count} governing strips (full results)...")
    
    # Build model with ONLY governing strips
    builder_stage2 = ViktorSciaModelBuilder()
    # Create model without strips first
    _build_model_structure(builder_stage2, params)  # Nodes, plates, loads, etc.
    # Add ONLY governing strips
    create_integration_strips_selective(builder_stage2, params, governing_strip_names)
    
    # Run with full results template
    xml_file2, def_file2 = builder_stage2.generate_xml_input()
    esa_template_full = File.from_path(full_template_path)
    analysis_stage2 = builder_stage2.run_analysis(xml_file2, def_file2, esa_template_full)
    
    # Extract full results (small file because only governing strips)
    progress_message("Stage 2: Extraheren complete resultaten...")
    results_stage2 = builder_stage2.extract_analysis_results(analysis_stage2)
    
    # === COMBINE RESULTS ===
    combined_results = {
        "stage1_governing_results": results_stage1,
        "stage2_full_results": results_stage2,
        "governing_strips": governing_strips_list,
        "optimization_stats": {
            "total_strips_stage1": total_strips,
            "governing_strips_stage2": governing_count,
            "reduction_percentage": reduction_pct,
            "stage1_xml_size": len(results_stage1.get("xml_output", b"")),
            "stage2_xml_size": len(results_stage2.get("xml_output", b"")),
        },
        # Make stage2 results primary for downstream processing
        "integration_strips": results_stage2.get("integration_strips"),
        "xml_parsing": results_stage2.get("xml_parsing"),
        "analysis_status": results_stage2.get("analysis_status"),
    }
    
    return combined_results
```

**Success Criteria:**
- Both stages execute successfully
- Stage 2 has dramatically fewer strips
- Results are correctly combined
- Downstream processing works with stage 2 results

#### Task 2.4: Helper Function to Separate Model Building
**Files to modify:**
- [app/bridge/scia_model_builder.py](c:\PyCharm\automatisch-toetsmodel-plaatbruggen\app\bridge\scia_model_builder.py)

**New Function:**
```python
def _build_model_structure(builder: ViktorSciaModelBuilder, params: Any) -> None:
    """
    Build SCIA model structure WITHOUT integration strips.
    
    Creates:
    - Materials
    - Nodes
    - Plates
    - Supports
    - Load groups
    - Load cases
    - Load combinations
    - Loads
    
    Does NOT create:
    - Integration strips (added separately)
    """
    pass  # Extract from define_complete_bridge_model
```

**Success Criteria:**
- Model structure created correctly
- Strips can be added afterward
- Existing tests still pass

### Phase 3: Integration & Caching (Week 3-4)

#### Task 3.1: Update Cache to Support Two-Stage Results
**Files to modify:**
- [app/bridge/analysis_cache.py](c:\PyCharm\automatisch-toetsmodel-plaatbruggen\app\bridge\analysis_cache.py)

**Changes:**
1. Add cache key differentiation for two-stage vs. single-stage
2. Cache both stage 1 and stage 2 results separately
3. Support incremental caching (stage 1 → stage 2)

**New Function:**
```python
def get_two_stage_scia_results_cached(
    params: Any,
    entity_id: int,
    governing_template_path: Path,
    full_template_path: Path,
    analysis_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Get two-stage SCIA results with intelligent caching.
    
    Caching strategy:
    - If parameters unchanged and both stages cached → Return cached
    - If only stage 1 cached and strips unchanged → Run stage 2 only
    - Otherwise → Run both stages
    """
    pass  # Implementation
```

**Success Criteria:**
- Two-stage results cached correctly
- Cache hits work as expected
- Parameter changes invalidate cache appropriately

#### Task 3.2: Update Controller to Use Two-Stage Analysis
**Files to modify:**
- [app/bridge/bridgeController/scia_integration.py](c:\PyCharm\automatisch-toetsmodel-plaatbruggen\app\bridge\bridgeController\scia_integration.py)

**Changes:**
1. Add configuration flag to toggle two-stage analysis
2. Update `_get_scia_results_with_cache()` to support both modes
3. Add optional parameter to enable/disable optimization

**Implementation:**
```python
def _get_scia_results_with_cache(
    self, 
    params: BridgeParametrization, 
    use_two_stage: bool = True,  # New parameter
    **kwargs
) -> dict:
    """Get SCIA results with optional two-stage optimization."""
    
    if not params.bridge_segments_array:
        raise UserError("Geen brugsegmenten gedefinieerd.")
    
    entity_id = kwargs.get("entity_id")
    
    if use_two_stage:
        governing_template = self._get_scia_governing_template_path()
        full_template = self._get_scia_template_path()
        
        results = get_two_stage_scia_results_cached(
            params, entity_id, governing_template, full_template
        )
    else:
        # Existing single-stage logic
        template_path = self._get_scia_template_path()
        results = get_cached_analysis_results(...)
    
    return results
```

**Success Criteria:**
- Both single-stage and two-stage modes work
- Easy to toggle between modes
- No breaking changes to existing views

### Phase 4: Testing (Week 4-5)

#### Task 4.1: Unit Tests
**Files to create/modify:**
- `tests/test_src/test_integrations/test_two_stage_analysis.py` (NEW)
- `tests/test_src/test_integrations/test_integration_strip_creation.py`

**Test Coverage:**
1. `test_identify_governing_strips()`: Verify correct strip identification
2. `test_create_integration_strips_selective()`: Verify selective creation
3. `test_governing_strips_reduction()`: Verify expected reduction percentage
4. `test_stage_results_consistency()`: Verify results match single-stage
5. `test_two_stage_performance()`: Measure performance improvement

**Success Criteria:**
- All tests pass
- Code coverage >80% for new code
- Performance tests show 70%+ time reduction

#### Task 4.2: Integration Tests
**Files to create:**
- `tests/test_app/test_bridge/test_two_stage_controller.py` (NEW)

**Test Scenarios:**
1. End-to-end two-stage analysis
2. Cache behavior with two-stage
3. Error handling (stage 1 fails, stage 2 fails)
4. Results displayed correctly in views

**Success Criteria:**
- All integration scenarios pass
- Error handling robust
- Views display results correctly

#### Task 4.3: Manual Testing Checklist

1. **Small Bridge Test**
   - Create bridge with 2-3 segments
   - Run two-stage analysis
   - Verify results match single-stage
   - Check performance improvement

2. **Large Bridge Test**
   - Create bridge with 10+ segments
   - Run two-stage analysis
   - Measure time savings
   - Verify no errors

3. **Edge Cases**
   - Bridge with no supports
   - Bridge with many supports
   - Very short segments
   - Very long segments

4. **View Tests**
   - Integration strip views display correctly
   - Envelope view works
   - Download functions work
   - IDEA integration still works

### Phase 5: Deployment & Monitoring (Week 5-6)

#### Task 5.1: Add Feature Flag
**Files to modify:**
- [app/bridge/parametrization.py](c:\PyCharm\automatisch-toetsmodel-plaatbruggen\app\bridge\parametrization.py)

Add option to toggle two-stage optimization:
```python
OptionalField(
    "gebruik_twee_fase_optimalisatie",
    BooleanField,
    default=True,
    description="Gebruik twee-fase SCIA berekening voor snellere resultaten",
    name="Gebruik twee-fase optimalisatie",
    visible=Lookup("advanced_tab")
)
```

**Success Criteria:**
- Users can enable/disable feature
- Default is enabled (after testing)
- Feature flag state cached with results

#### Task 5.2: Add Performance Metrics
**Files to modify:**
- [app/bridge/scia_model_builder.py](c:\PyCharm\automatisch-toetsmodel-plaatbruggen\app\bridge\scia_model_builder.py)

**Add timing metrics:**
```python
optimization_stats = {
    "total_strips_stage1": total_strips,
    "governing_strips_stage2": governing_count,
    "reduction_percentage": reduction_pct,
    "stage1_duration_seconds": stage1_duration,
    "stage2_duration_seconds": stage2_duration,
    "total_duration_seconds": total_duration,
    "stage1_xml_size_bytes": stage1_xml_size,
    "stage2_xml_size_bytes": stage2_xml_size,
    "time_savings_vs_single_stage_estimate": estimated_savings,
}
```

**Success Criteria:**
- Metrics logged for monitoring
- Stats available in results
- Can analyze optimization effectiveness

#### Task 5.3: Documentation
**Files to create/modify:**
- `docs/scia_two_stage_optimization.md` (NEW)
- [README.md](c:\PyCharm\automatisch-toetsmodel-plaatbruggen\README.md)
- [CHANGELOG.md](c:\PyCharm\automatisch-toetsmodel-plaatbruggen\CHANGELOG.md)

**Documentation Sections:**
1. Overview of two-stage optimization
2. Performance benefits
3. How to enable/disable
4. Troubleshooting guide
5. Developer notes

**Success Criteria:**
- Clear user documentation
- Developer documentation complete
- Examples provided

---

## Code Structure Changes

### New Files to Create

```
src/integrations/scia_integration/
  ├── analysis/
  │   ├── __init__.py
  │   ├── two_stage_orchestrator.py           # Main two-stage logic
  │   └── governing_strip_identifier.py       # Identify governing strips
  └── model/
      └── selective_strip_builder.py          # Build model with selected strips

tests/
  ├── test_src/
  │   └── test_integrations/
  │       ├── test_two_stage_analysis.py      # Unit tests
  │       └── test_governing_identification.py
  └── test_app/
      └── test_bridge/
          └── test_two_stage_controller.py     # Integration tests

resources/templates/
  └── model_governing.esa                      # New template (user created)

docs/
  └── scia_two_stage_optimization.md          # User/dev docs
```

### Modified Files

```
app/
  ├── constants/
  │   └── paths.py                            # Add governing template path
  ├── bridge/
  │   ├── scia_model_builder.py              # Add two-stage functions
  │   ├── analysis_cache.py                   # Support two-stage caching
  │   └── bridgeController/
  │       └── scia_integration.py             # Update to use two-stage

src/
  ├── data_models/
  │   └── scia_models.py                      # Add two-stage models
  └── integrations/scia_integration/
      ├── model/
      │   └── scia_integration_strips.py      # Add selective creation
      └── results/
          └── scia_integration_strips_processor.py  # Add governing identification

tests/
  └── test_src/
      └── test_integrations/
          └── test_integration_strip_creation.py    # Add selective tests
```

---

## Performance Expectations

### Current Performance (Single-Stage)

- **Bridge with 100 segments:**
  - Model creation: 5-10 seconds
  - SCIA calculation: 30-60 seconds
  - Result extraction: **30-90 seconds** ⚠️ BOTTLENECK
  - Total: 65-160 seconds

- **Integration strips created:** ~400-800
- **XML output size:** 50-150 MB
- **Result parsing:** Iterates through 400-800 strips × 8 tables = 3,200-6,400 entries

### Expected Performance (Two-Stage)

#### Stage 1: Governing Analysis
- Model creation: 5-10 seconds (same)
- SCIA calculation: 30-60 seconds (same)
- Result extraction: **3-8 seconds** ✅ 90% faster (small XML)
- Stage 1 subtotal: 38-78 seconds

#### Stage 2: Detailed Analysis
- Model creation: 3-5 seconds (fewer strips)
- SCIA calculation: 25-50 seconds (fewer strips, slightly faster)
- Result extraction: **5-10 seconds** ✅ 85% faster (only 30-50 strips)
- Stage 2 subtotal: 33-65 seconds

#### Total Two-Stage Time
- **Total: 71-143 seconds**
- **Savings: 0-17 seconds** (similar total time)
- **BUT:** Can cache stage 1 and only rerun stage 2 if needed

### Key Benefits

1. **Reduced XML Size:**
   - Stage 1 XML: ~5-10 MB (governing only)
   - Stage 2 XML: ~3-8 MB (30-50 strips × 8 tables)
   - **Total: 8-18 MB vs. 50-150 MB** (85-90% reduction)

2. **Faster Result Processing:**
   - Stage 1: Parse ~30-50 envelope entries
   - Stage 2: Parse ~30-50 strips × 8 tables = 240-400 entries
   - **Total: 270-450 vs. 3,200-6,400 entries** (85-92% reduction)

3. **Better Caching:**
   - Can cache stage 1 results independently
   - If only strip selection changes, rerun stage 2 only
   - Faster iteration during design

4. **Improved Reliability:**
   - Smaller XML files less likely to hit size limits
   - Faster parsing reduces timeout risk
   - Better error handling (can retry stages independently)

---

## Risk Analysis & Mitigation

### Risk 1: Template Configuration Complexity
**Risk:** Governing template may not export correct data format  
**Impact:** High - breaks stage 1  
**Mitigation:**
- Thorough manual testing of template in SCIA before implementation
- Validate XML structure with unit tests
- Fallback to single-stage if parsing fails

### Risk 2: Missing Governing Strips
**Risk:** Governing strip identification algorithm misses critical strips  
**Impact:** Medium - incomplete stage 2 results  
**Mitigation:**
- Conservative identification (include extra strips if uncertain)
- Validation against single-stage results in testing
- Add safety margin (e.g., include strips within 5% of governing values)

### Risk 3: Performance Not as Expected
**Risk:** Two stages don't improve overall performance  
**Impact:** Low - can disable feature  
**Mitigation:**
- Performance testing before deployment
- Feature flag to disable if needed
- Monitoring metrics to track actual performance

### Risk 4: Cache Invalidation Issues
**Risk:** Cache doesn't invalidate correctly when parameters change  
**Impact:** Medium - stale results returned  
**Mitigation:**
- Thorough testing of cache invalidation logic
- Include template paths in cache key
- Version cache format to allow migration

### Risk 5: SCIA Worker Instability
**Risk:** Running two analyses increases chance of worker failure  
**Impact:** Medium - analysis fails more often  
**Mitigation:**
- Robust error handling for each stage
- Retry logic for transient failures
- Fallback to single-stage on repeated failures

---

## Success Criteria

### Functional Requirements
- ✅ Two-stage analysis produces identical results to single-stage
- ✅ All existing views and downloads work with two-stage results
- ✅ IDEA integration works with two-stage SCIA results
- ✅ Error handling for both stages is robust
- ✅ Feature can be toggled on/off

### Performance Requirements
- ✅ Result extraction time reduced by 70%+ for large bridges
- ✅ XML output size reduced by 80%+ 
- ✅ Total analysis time not significantly worse than single-stage
- ✅ Cache hit ratio remains high (>80%)

### Quality Requirements
- ✅ All automated tests pass
- ✅ Code coverage >80% for new code
- ✅ No regressions in existing functionality
- ✅ Documentation complete

### User Experience Requirements
- ✅ Progress messages clear for both stages
- ✅ Optimization statistics visible to user
- ✅ Easy to enable/disable feature
- ✅ Error messages helpful

---

## Implementation Timeline

### Week 1: Infrastructure
- [ ] User creates governing template
- [ ] Add template path constants
- [ ] Create data models
- [ ] Set up test files

### Week 2: Core Logic
- [ ] Implement `identify_governing_strips()`
- [ ] Implement `create_integration_strips_selective()`
- [ ] Implement `_build_model_structure()`
- [ ] Unit tests for core logic

### Week 3: Orchestration
- [ ] Implement `run_two_stage_scia_analysis()`
- [ ] Update caching logic
- [ ] Update controller integration
- [ ] Integration tests

### Week 4: Testing & Refinement
- [ ] End-to-end testing
- [ ] Performance benchmarking
- [ ] Bug fixes
- [ ] Edge case handling

### Week 5: Deployment Prep
- [ ] Add feature flag
- [ ] Add metrics/monitoring
- [ ] Documentation
- [ ] Code review

### Week 6: Deployment & Monitoring
- [ ] Deploy to staging
- [ ] User acceptance testing
- [ ] Deploy to production
- [ ] Monitor performance

---

## Next Steps

1. **Immediate (User):**
   - Create `model_governing.esa` template in SCIA Engineer
   - Configure to export only min/max envelope results
   - Test template and commit to repo

2. **After Template Ready:**
   - Review this plan with team
   - Create implementation issues/tickets
   - Begin Phase 1: Infrastructure Setup
   - Set up development branch

3. **Ongoing:**
   - Weekly progress review
   - Update plan as needed
   - Document learnings and issues

---

## Questions to Resolve

1. **Template Format:**
   - What exactly does the governing template export?
   - Are envelope results in same format as full results?
   - Do we need XML parsing changes?

2. **Strip Identification:**
   - Should we include a safety margin (e.g., top 10% of strips)?
   - How to handle ties (multiple strips with same value)?
   - Should we identify governing strips per load case or globally?

3. **Caching Strategy:**
   - Cache both stages separately or together?
   - How to handle partial cache hits?
   - Cache TTL considerations?

4. **Feature Rollout:**
   - Enable by default or opt-in initially?
   - How to communicate feature to users?
   - Staged rollout plan?

---

## Appendix A: Example Governing Strip Data

### Typical Bridge (5 segments, 3 zones)

**Stage 1 Output:**
- Total strips: 420
- Envelope identifies:
  - Zone Z1-1: 3 governing strips (max M_y, min M_y, max V_z)
  - Zone Z2-1: 5 governing strips
  - Zone Z3-1: 4 governing strips
  - Support strips: 8 governing
- **Total governing: 20 strips (95% reduction)**

**Stage 2 Input:**
- Model only 20 strips
- Export full results for these 20
- XML output: 3 MB vs. 45 MB in single-stage

### Large Bridge (20 segments, 10 zones)

**Stage 1 Output:**
- Total strips: 1,840
- Envelope identifies:
  - ~5 governing strips per zone average
  - 10 zones × 5 strips = 50 strips
- **Total governing: 50 strips (97% reduction)**

**Stage 2 Input:**
- Model only 50 strips
- Export full results for these 50
- XML output: 8 MB vs. 120 MB in single-stage

---

## Appendix B: Code Snippets

### Governing Strip Name Parsing

```python
def parse_strip_name(name: str) -> dict[str, str]:
    """
    Parse integration strip name into components.
    
    Example: "strip_dir-x_reg_Z1-1_w-1.0_nr-1"
    Returns: {
       'direction': 'x',
       'strip_type': 'reg',
       'zone': 'Z1-1',
       'width': '1.0',
       'number': '1'
    }
    """
    # Implementation in scia_integration_strips_processor.py
    pass
```

### Selective Strip Creation Logic

```python
def create_integration_strips_selective(builder, params, governing_names):
    """Create only strips whose names are in governing_names."""
    
    # Get all potential strip configurations
    all_strip_configs = _generate_all_strip_configurations(params)
    
    # Filter to only governing strips
    for config in all_strip_configs:
        strip_name = _format_strip_name(config)
        if strip_name in governing_names:
            builder.create_integration_strip(
                strip_type=config['type'],
                name=strip_name,
                member_list=config['member_list'],
                # ... other parameters
            )
```

---

**End of Plan**
