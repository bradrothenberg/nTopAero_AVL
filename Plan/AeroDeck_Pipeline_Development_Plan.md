# nTop-to-AeroDeck Automated Pipeline
## 3-Phase Development Plan

**Project Goal:** Create a production-ready Python pipeline that ingests nTop panel geometry exports and automatically generates comprehensive aerodynamic decks using AVL and XFOIL, with both human-readable reports and machine-readable output files for downstream 6-DOF simulation.

---

## Input Data Structure (From nTop)

Based on analysis of your uploaded files, the pipeline will process:

- **mass.csv**: Mass properties (mass, CG location, inertia tensor)
- **LEpts.csv**: Leading edge panel points (x, y, z)
- **TEpts.csv**: Trailing edge panel points (x, y, z)
- **WINGLETpts.csv**: Winglet geometry points
- **ELEVONpts.csv**: Control surface (elevon) hinge line points

---

## Phase 1: Core Infrastructure & AVL Integration (Weeks 1-2)

### Objectives
- Establish robust file I/O and validation
- Build AVL geometry translator
- Create basic AVL execution wrapper
- Implement initial testing framework

### Deliverables

#### 1.1 Project Structure
```
ntop-aerodeck/
├── aerodeck/
│   ├── __init__.py
│   ├── cli.py                 # Command-line interface
│   ├── geometry/
│   │   ├── __init__.py
│   │   ├── loader.py          # Load nTop CSV files
│   │   ├── validator.py       # Geometry validation
│   │   └── avl_translator.py  # Convert to AVL format
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── avl_runner.py      # AVL execution wrapper
│   │   └── xfoil_runner.py    # XFOIL execution wrapper
│   ├── output/
│   │   ├── __init__.py
│   │   ├── report_generator.py # Human-readable reports
│   │   └── deck_writer.py     # 6-DOF input files
│   └── utils/
│       ├── __init__.py
│       ├── logger.py          # Verbose logging system
│       └── config.py          # Configuration management
├── tests/
│   ├── __init__.py
│   ├── test_geometry.py
│   ├── test_avl.py
│   └── fixtures/              # Test data
├── examples/
│   └── sample_run/            # Your uploaded files
├── docs/
│   ├── user_guide.md
│   └── api_reference.md
├── setup.py
├── requirements.txt
├── README.md
└── .gitignore
```

#### 1.2 Core Components

**geometry/loader.py**
- Class: `GeometryLoader`
- Methods:
  - `load_panel_data(folder_path)` → Returns structured panel data
  - `load_mass_properties(file_path)` → Returns mass/inertia dict
- Validation: Check for required files, data completeness
- Error handling: Graceful failures with informative messages

**geometry/avl_translator.py**
- Class: `AVLGeometryWriter`
- Methods:
  - `create_surface_definition(le_points, te_points)` → AVL SURFACE block
  - `create_control_surface(elevon_points, hinge_line)` → AVL CONTROL block
  - `write_avl_input(output_path, geometry, mass_props)`
- Features:
  - Automatic chord calculation from LE/TE points
  - Section definition with airfoil assignment
  - Control surface hinge line detection
  - Reference area/length calculation

**analysis/avl_runner.py**
- Class: `AVLAnalysis`
- Methods:
  - `setup_run_cases(alpha_range, beta_range, mach)` → Generate run matrix
  - `execute_avl(input_file, run_cases)` → Run AVL batch mode
  - `parse_results(output_files)` → Extract stability derivatives
- Features:
  - Subprocess management for AVL execution
  - Command file generation for automated runs
  - Result parsing (forces, moments, stability derivatives)
  - Error detection and recovery

**utils/logger.py**
- Class: `VerboseLogger`
- Features:
  - Timestamped progress messages
  - Hierarchical indentation for nested operations
  - Color-coded output (warnings, errors, success)
  - Toggle verbose/quiet modes
- Example output:
  ```
  [12:34:56] Starting aero deck generation...
  [12:34:56]   ✓ Loaded 5 geometry files
  [12:34:57]   → Creating AVL input file...
  [12:34:58]   ✓ AVL geometry written: aircraft.avl
  [12:35:00]   → Running AVL analysis (24 cases)...
  [12:35:15]   ✓ AVL analysis complete
  ```

#### 1.3 Testing Strategy (Phase 1)

**Unit Tests**
- `test_geometry_loader`: Valid/invalid CSV handling
- `test_avl_translator`: Verify AVL format correctness
- `test_avl_runner`: Mock AVL execution and parsing

**Integration Tests**
- End-to-end: Load your sample data → Generate AVL file → Validate format
- Regression: Golden file comparison for consistent output

**Success Criteria**
- All unit tests pass
- Sample geometry successfully converted to valid AVL input
- AVL can be executed manually on generated files

---

## Phase 2: XFOIL Integration & Aero Deck Generation (Weeks 3-4)

### Objectives
- Integrate XFOIL for airfoil analysis
- Implement comprehensive run matrix generation
- Build aero deck data structure
- Create 6-DOF output file format

### Deliverables

#### 2.1 XFOIL Integration

**analysis/xfoil_runner.py**
- Class: `XFOILAnalysis`
- Methods:
  - `generate_airfoil_polars(airfoil_file, re_range, alpha_range)`
  - `interpolate_cl_cd_cm(alpha, re, mach)` → Coefficient lookup
  - `export_polar_data(output_file)`
- Features:
  - Batch mode XFOIL execution
  - Polar convergence checking
  - Reynolds number sweep
  - Mach number corrections (if applicable)

**Workflow:**
1. Extract representative airfoils from nTop geometry (or use defaults)
2. Run XFOIL polars at relevant Reynolds numbers
3. Store polars for section assignment in AVL
4. Use polars to validate AVL results

#### 2.2 Run Matrix Definition

**analysis/run_matrix.py**
- Class: `FlightConditionMatrix`
- Parameters:
  - Alpha: [-10° to 20°] in 2° increments
  - Beta: [-5° to 5°] in 2° increments
  - Mach: [0.1, 0.3, 0.5, 0.7] (user configurable)
  - Altitude/Reynolds number correlation
  - Control surface deflections (elevon: -30° to +30°)
- Methods:
  - `generate_trim_conditions()` → For level flight
  - `generate_stability_matrix()` → For derivative extraction
  - `generate_control_effectiveness()` → For control power

#### 2.3 Aero Deck Data Structure

**output/aerodeck.py**
- Class: `AeroDeck`
- Data structure:
```python
aerodeck = {
    'metadata': {
        'aircraft_name': str,
        'date_generated': datetime,
        'reference_geometry': {
            'S_ref': float,  # Reference area [m²]
            'c_ref': float,  # Reference chord [m]
            'b_ref': float,  # Reference span [m]
        }
    },
    'mass_properties': {
        'mass': float,  # [kg]
        'cg': [x, y, z],  # [m]
        'inertia': [[Ixx, Ixy, Ixz],
                    [Ixy, Iyy, Iyz],
                    [Ixz, Iyz, Izz]]  # [kg⋅m²]
    },
    'aerodynamics': {
        'static_stability': {
            'CL_alpha': float,  # 1/rad
            'CD_alpha': float,
            'Cm_alpha': float,
            'CL_beta': float,
            'Cy_beta': float,
            'Cn_beta': float,
            # ... full stability derivative set
        },
        'control_derivatives': {
            'CL_de': float,  # Elevon effectiveness
            'Cm_de': float,
            'Cy_dr': float,  # If rudder present
            # ...
        },
        'dynamic_derivatives': {
            'CL_q': float,  # Pitch damping
            'Cm_q': float,
            'Cy_p': float,  # Roll damping
            'Cn_r': float,  # Yaw damping
            # ...
        },
        'lookup_tables': {
            'CL_alpha_mach': ndarray,  # 2D: (alpha, mach)
            'CD_alpha_mach': ndarray,
            # ... for nonlinear effects
        }
    }
}
```

#### 2.4 Output Files

**6-DOF Input File (JSON format)**
- Filename: `aerodeck_6dof.json`
- Contains complete aerodeck structure above
- Machine-readable for direct import into flight dynamics code
- Includes metadata for traceability

**Alternative Format (Optional)**
- `.mat` file for MATLAB/Simulink users
- `.csv` for spreadsheet-based tools

#### 2.5 Testing Strategy (Phase 2)

**Integration Tests**
- Full pipeline: nTop data → AVL+XFOIL → Aero deck generation
- Cross-validation: AVL results vs. XFOIL polars
- Physical sanity checks:
  - CL_alpha > 0 (stable wing)
  - Cm_alpha < 0 (pitch stability)
  - Reasonable drag polar shape

**Success Criteria**
- Complete aero deck generated from sample data
- All stability derivatives populated
- Output file parseable by 6-DOF simulator

---

## Phase 3: Reporting, Polish & Documentation (Weeks 5-6)

### Objectives
- Create comprehensive human-readable reports
- Build professional CLI with rich output
- Write complete documentation
- Package for distribution

### Deliverables

#### 3.1 Report Generation

**output/report_generator.py**
- Class: `AeroReport`
- Output formats:
  - **PDF report** (using ReportLab or matplotlib)
  - **HTML report** (interactive, with plots)
  - **Markdown summary** (for version control)

**Report Contents:**

1. **Executive Summary**
   - Aircraft configuration description
   - Reference geometry summary
   - Key aerodynamic characteristics
   - Stability assessment (stable/unstable in each axis)

2. **Geometry Section**
   - 3D wireframe plot of aircraft
   - Top/side/front view projections
   - Planform area and span efficiency
   - Control surface locations and sizes

3. **Mass Properties**
   - CG location relative to aerodynamic center
   - Static margin calculation
   - Principal moments of inertia
   - Radius of gyration

4. **Aerodynamic Characteristics**
   - Lift curve (CL vs. α) with stall indicators
   - Drag polar (CL vs. CD)
   - Pitch moment curve (Cm vs. α)
   - Lateral-directional stability derivatives
   - Control effectiveness plots

5. **Stability Derivatives Table**
   - Complete derivative matrix
   - Dimensional and non-dimensional forms
   - Mach number effects (if applicable)

6. **Quality Metrics**
   - AVL convergence status
   - XFOIL convergence warnings
   - Data coverage in flight envelope
   - Uncertainty estimates

7. **Appendix**
   - Run matrix details
   - AVL input file (raw)
   - XFOIL polar data
   - Processing timestamps

**Example Visualizations:**
- 3D aircraft geometry with color-coded surfaces
- Stability derivative spider plot
- Control surface authority bar chart
- Flight envelope coverage map

#### 3.2 Command-Line Interface

**cli.py**
```bash
# Basic usage
aerodeck generate /path/to/ntop_export/

# Advanced options
aerodeck generate /path/to/ntop_export/ \
    --output-dir ./results \
    --verbose \
    --config ./custom_config.yaml \
    --report-format pdf html \
    --mach 0.3 0.5 0.7 \
    --alpha-range -10 20 \
    --include-xfoil

# View existing deck
aerodeck view ./results/aerodeck_6dof.json

# Validate geometry only
aerodeck validate /path/to/ntop_export/
```

**Features:**
- Progress bar for long-running analyses
- Color-coded console output
- Real-time feedback in verbose mode
- Graceful interruption (Ctrl+C handling)
- Exit codes for CI/CD integration

**Verbose Mode Output Example:**
```
═══════════════════════════════════════════════════════
  nTop AeroDeck Generator v1.0.0
═══════════════════════════════════════════════════════

[2025-11-12 14:30:00] Starting analysis...
[2025-11-12 14:30:00] Input directory: /data/aircraft_001/
[2025-11-12 14:30:00] Output directory: /results/aircraft_001/

┌─ Phase 1: Geometry Loading ────────────────────────┐
│ [14:30:01] Reading panel definitions...             │
│ [14:30:01]   ✓ mass.csv        (1 row)              │
│ [14:30:01]   ✓ LEpts.csv       (5 points)           │
│ [14:30:01]   ✓ TEpts.csv       (5 points)           │
│ [14:30:01]   ✓ WINGLETpts.csv  (7 points)           │
│ [14:30:01]   ✓ ELEVONpts.csv   (4 points)           │
│ [14:30:02] Validating geometry...                   │
│ [14:30:02]   ✓ All panels closed                    │
│ [14:30:02]   ✓ No self-intersections                │
│ [14:30:02]   ⚠ Winglet dihedral: 85° (very high)    │
└────────────────────────────────────────────────────┘

┌─ Phase 2: AVL Analysis ────────────────────────────┐
│ [14:30:03] Generating AVL input file...             │
│ [14:30:03]   → Computed S_ref = 45.2 m²             │
│ [14:30:03]   → Computed b_ref = 143.8 m             │
│ [14:30:03]   → Computed c_ref = 0.314 m (MAC)       │
│ [14:30:04]   ✓ Written: aircraft.avl                │
│ [14:30:04] Running AVL (48 flight conditions)...    │
│ [14:30:04] [━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━] 0%      │
│ [14:30:15] [████████████████████████████████] 100%  │
│ [14:30:15]   ✓ All cases converged                  │
│ [14:30:16] Extracting stability derivatives...      │
│ [14:30:16]   ✓ Longitudinal: CL_α = 5.23 /rad       │
│ [14:30:16]   ✓ Lateral: Cn_β = 0.084 /rad           │
└────────────────────────────────────────────────────┘

┌─ Phase 3: XFOIL Analysis ─────────────────────────┐
│ [14:30:17] Extracting airfoil sections...           │
│ [14:30:17]   → Root airfoil: NACA 0012 equiv.       │
│ [14:30:18] Running XFOIL polars...                  │
│ [14:30:18]   Re = 1.0e6  [████████████] ✓           │
│ [14:30:22]   Re = 2.0e6  [████████████] ✓           │
│ [14:30:26]   ✓ Polars generated                     │
└────────────────────────────────────────────────────┘

┌─ Phase 4: Output Generation ──────────────────────┐
│ [14:30:27] Building aero deck...                    │
│ [14:30:28]   ✓ Stability derivatives computed       │
│ [14:30:28]   ✓ Control effectiveness computed       │
│ [14:30:29]   ✓ Lookup tables generated              │
│ [14:30:29] Writing output files...                  │
│ [14:30:29]   ✓ aerodeck_6dof.json (42 KB)           │
│ [14:30:30]   ✓ aerodeck_report.pdf (8 pages)        │
│ [14:30:30]   ✓ aerodeck_summary.md                  │
└────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════
  ✓ Analysis complete in 30.2 seconds
  
  Output files:
    → /results/aircraft_001/aerodeck_6dof.json
    → /results/aircraft_001/aerodeck_report.pdf
    → /results/aircraft_001/aerodeck_summary.md
    
  Next steps:
    • Review the PDF report for aerodynamic characteristics
    • Use aerodeck_6dof.json in your flight dynamics model
    • Run 'aerodeck view' to inspect derivatives interactively
═══════════════════════════════════════════════════════
```

#### 3.3 Configuration System

**config.yaml** (example)
```yaml
# Analysis settings
analysis:
  alpha_range: [-10, 20, 2]  # [min, max, step] in degrees
  beta_range: [-5, 5, 2]
  mach_numbers: [0.1, 0.3, 0.5]
  reynolds_numbers: [1.0e6, 2.0e6, 5.0e6]
  
  # Control surface deflection ranges
  controls:
    elevon: [-30, 30, 10]  # degrees
    rudder: [-25, 25, 10]  # if present

# AVL settings
avl:
  executable: "avl"  # Path to AVL binary
  max_iterations: 100
  convergence_tolerance: 1e-6

# XFOIL settings
xfoil:
  executable: "xfoil"
  n_critical: 9  # Transition criterion
  max_iterations: 200
  viscous: true

# Output settings
output:
  formats: ["json", "pdf", "html"]
  save_intermediate: true  # Keep AVL/XFOIL raw files
  plot_style: "seaborn"
  
# Reference values (auto-computed if not specified)
reference:
  area: null      # m² - computed from geometry
  span: null      # m
  chord: null     # m (MAC)
  
# Validation thresholds
validation:
  max_aspect_ratio: 30
  min_aspect_ratio: 2
  warn_cg_shift: 0.05  # Fraction of MAC
```

#### 3.4 Documentation

**README.md**
- Quick start guide
- Installation instructions
- Basic usage examples
- Link to full documentation

**docs/user_guide.md**
- Detailed usage examples
- Configuration options
- Interpreting results
- Troubleshooting common issues
- nTop export procedure

**docs/api_reference.md**
- Python API documentation for programmatic use
- Class and method descriptions
- Type hints and return values

**docs/theory.md**
- Coordinate system conventions
- Stability derivative definitions
- AVL/XFOIL methodology
- Limitations and assumptions

#### 3.5 Packaging & Distribution

**setup.py / pyproject.toml**
```python
name = "ntop-aerodeck"
version = "1.0.0"
description = "Automated aerodynamic deck generation from nTop geometry"
dependencies = [
    "numpy>=1.21",
    "pandas>=1.3",
    "matplotlib>=3.4",
    "scipy>=1.7",
    "click>=8.0",  # CLI framework
    "pyyaml>=6.0",
    "reportlab>=3.6",  # PDF generation
    "jinja2>=3.0",  # HTML templating
    "tqdm>=4.62",  # Progress bars
]
```

**Installation:**
```bash
pip install ntop-aerodeck
# or
python setup.py install
```

**Docker Container (Optional)**
- Pre-installed AVL and XFOIL
- Ready-to-run environment
- Useful for CI/CD and reproducibility

#### 3.6 Testing Strategy (Phase 3)

**End-to-End Tests**
- Complete pipeline with your sample data
- Verify all output files generated
- Check report rendering (PDF, HTML)
- Validate 6-DOF file structure

**User Acceptance Testing**
- Run generated aero deck in your 6-DOF simulator
- Compare results against expected behavior
- Stress test with edge cases:
  - Very high aspect ratio wings
  - Low aspect ratio configurations
  - Extreme control deflections

**Performance Testing**
- Benchmark runtime for typical cases
- Memory usage profiling
- Optimize bottlenecks (AVL execution, plotting)

**Documentation Testing**
- Fresh install on clean system
- Follow README instructions verbatim
- Verify all examples work

**Success Criteria**
- Complete documentation suite
- All tests passing (unit, integration, E2E)
- Professional report generation
- CLI intuitive and informative
- Package installable via pip

---

## Repository Structure (Final)

```
ntop-aerodeck/
├── .github/
│   └── workflows/
│       ├── tests.yml          # CI/CD pipeline
│       └── publish.yml        # PyPI deployment
├── aerodeck/
│   ├── __init__.py
│   ├── cli.py
│   ├── version.py
│   ├── geometry/
│   │   ├── __init__.py
│   │   ├── loader.py
│   │   ├── validator.py
│   │   ├── avl_translator.py
│   │   └── mesh_utils.py
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── avl_runner.py
│   │   ├── xfoil_runner.py
│   │   ├── run_matrix.py
│   │   └── derivatives.py
│   ├── output/
│   │   ├── __init__.py
│   │   ├── aerodeck.py
│   │   ├── report_generator.py
│   │   ├── deck_writer.py
│   │   └── templates/
│   │       ├── report.html
│   │       └── summary.md
│   └── utils/
│       ├── __init__.py
│       ├── logger.py
│       ├── config.py
│       └── validators.py
├── tests/
│   ├── __init__.py
│   ├── test_geometry_loader.py
│   ├── test_avl_translator.py
│   ├── test_avl_runner.py
│   ├── test_xfoil_runner.py
│   ├── test_aerodeck.py
│   ├── test_report.py
│   ├── test_cli.py
│   ├── test_integration.py
│   └── fixtures/
│       ├── sample_aircraft/     # Your uploaded files
│       └── expected_outputs/
├── examples/
│   ├── basic_usage.py
│   ├── advanced_config.py
│   └── programmatic_api.py
├── docs/
│   ├── index.md
│   ├── installation.md
│   ├── user_guide.md
│   ├── api_reference.md
│   ├── theory.md
│   ├── troubleshooting.md
│   └── images/
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── .gitignore
├── .pre-commit-config.yaml
├── setup.py
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── LICENSE
├── README.md
├── CHANGELOG.md
└── CONTRIBUTING.md
```

---

## Development Timeline

| Phase | Duration | Key Milestones |
|-------|----------|----------------|
| **Phase 1** | Weeks 1-2 | • Core structure complete<br>• AVL translator working<br>• Basic CLI functional<br>• Unit tests passing |
| **Phase 2** | Weeks 3-4 | • XFOIL integration complete<br>• Full aero deck generation<br>• 6-DOF output file<br>• Integration tests passing |
| **Phase 3** | Weeks 5-6 | • Professional reports<br>• Complete documentation<br>• Package published<br>• All tests passing |

**Total Duration:** 6 weeks

---

## Key Technologies

- **Python 3.9+**: Core language
- **NumPy/SciPy**: Numerical computations
- **Pandas**: Data manipulation
- **Matplotlib/Seaborn**: Visualization
- **Click**: CLI framework
- **PyYAML**: Configuration management
- **ReportLab**: PDF generation
- **Jinja2**: HTML templating
- **pytest**: Testing framework
- **Black/isort**: Code formatting
- **mypy**: Type checking

---

## Risk Mitigation

### Technical Risks

1. **AVL/XFOIL Convergence Issues**
   - Mitigation: Implement retry logic, relaxed tolerances, fallback methods
   - Logging: Capture all solver warnings and failures

2. **Complex Geometry Handling**
   - Mitigation: Robust validation, clear error messages, manual override options
   - Testing: Wide range of aircraft configurations

3. **Performance for Large Run Matrices**
   - Mitigation: Parallel execution, caching, progress indication
   - Optimization: Profile and optimize bottlenecks

### Usability Risks

1. **Unclear Output Format**
   - Mitigation: Extensive documentation, example files, validation tools
   - User testing: Iterate based on your feedback

2. **Installation Complexity**
   - Mitigation: pip-installable package, Docker container, detailed instructions
   - Testing: Fresh install on multiple platforms

---

## Success Criteria (Final)

**Functional:**
- ✓ Accepts nTop panel geometry CSV files
- ✓ Generates valid AVL input automatically
- ✓ Executes AVL and XFOIL analyses
- ✓ Produces 6-DOF-compatible aero deck file
- ✓ Creates comprehensive PDF/HTML report

**Quality:**
- ✓ >90% test coverage
- ✓ All tests passing
- ✓ Type hints throughout
- ✓ Linted and formatted code

**Usability:**
- ✓ Single-command execution
- ✓ Verbose mode with clear feedback
- ✓ Handles errors gracefully
- ✓ Complete documentation

**Performance:**
- ✓ Typical run < 5 minutes for 50 flight conditions
- ✓ Memory efficient (< 1GB for typical cases)

**Professional:**
- ✓ Clean git history
- ✓ Semantic versioning
- ✓ CI/CD pipeline
- ✓ Published to PyPI

---

## Post-Delivery Support

### Maintenance Plan
- Bug fixes and patches
- Support for additional aircraft configurations
- Performance improvements
- Documentation updates

### Future Enhancements (Beyond Phase 3)
- GUI interface for non-CLI users
- Real-time geometry validation viewer
- Integration with other analysis tools (OpenVSP, SU2)
- Machine learning surrogate models for faster analysis
- Uncertainty quantification
- Multi-fidelity analysis (AVL → CFD escalation)

---

## Next Steps

1. **Review and approve** this plan
2. **Clarify requirements:**
   - Desired 6-DOF input file format (JSON sufficient?)
   - Specific stability derivatives needed?
   - Report format preferences?
   - Any nTop-specific export conventions?
3. **Set up development environment**
4. **Begin Phase 1 implementation**

---

## Questions for Clarification

1. **6-DOF Simulator Interface:**
   - What format does your 6-DOF code expect? (JSON, CSV, custom?)
   - Which stability derivatives are critical vs. optional?
   - Any specific coordinate system conventions?

2. **nTop Export:**
   - Will all aircraft have winglets and elevons?
   - Are airfoil coordinates exported separately, or should we use standard NACA?
   - Any other control surfaces (rudder, flaps)?

3. **Analysis Fidelity:**
   - What Mach number range?
   - Viscous or inviscid AVL analysis?
   - Do you need dynamic derivatives (Q-derivatives)?

4. **Report Preferences:**
   - Must-have plots/tables?
   - Company branding requirements?
   - Integration with existing reporting systems?

5. **Deployment:**
   - Will this run on Linux/Mac/Windows?
   - On-premises or cloud execution?
   - Integration with existing CI/CD?

---

**End of Development Plan**

This plan provides a clear roadmap from initial prototype to production-ready tool. Each phase builds on the previous, with testing integrated throughout. The final deliverable will be a professional, well-documented package that seamlessly integrates nTop geometry exports with aerodynamic analysis tools.
