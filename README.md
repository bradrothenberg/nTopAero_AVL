# nTop AeroDeck Generator

A production-ready Python pipeline that ingests nTop panel geometry exports and automatically generates comprehensive aerodynamic decks using AVL and XFOIL, with both human-readable reports and machine-readable output files for downstream 6-DOF simulation.

## Features

- **Automated Pipeline**: Load nTop CSV exports → Generate AVL input → Run analysis → Create aero deck
- **Comprehensive Validation**: Geometry validation with detailed error/warning reporting
- **AVL Integration**: Automated AVL execution with batch processing
- **Verbose Logging**: Beautiful, color-coded progress output
- **Flexible Configuration**: YAML-based configuration for all analysis parameters
- **Production Ready**: Type hints, comprehensive error handling, and extensive testing

## Installation

### From Source

```bash
# Clone the repository
git clone <repository-url>
cd ntop-aerodeck

# Install dependencies
pip install -e .

# Or install with development dependencies
pip install -e ".[dev]"
```

### Requirements

- Python 3.9+
- AVL (for aerodynamic analysis)
- XFOIL (optional, for airfoil analysis - Phase 2)

## Quick Start

### 1. Prepare Your nTop Export

Export your aircraft geometry from nTop with the following CSV files:

- `mass.csv` - Mass properties (mass, CG, inertia tensor)
- `LEpts.csv` - Leading edge panel points (x, y, z)
- `TEpts.csv` - Trailing edge panel points (x, y, z)
- `WINGLETpts.csv` - (Optional) Winglet geometry points
- `ELEVONpts.csv` - (Optional) Control surface hinge line points

### 2. Run the Generator

```bash
# Basic usage
aerodeck generate /path/to/ntop_export/

# With custom output directory
aerodeck generate /path/to/ntop_export/ --output-dir ./my_results

# Verbose mode
aerodeck generate /path/to/ntop_export/ -v

# With custom configuration
aerodeck generate /path/to/ntop_export/ --config config.yaml
```

### 3. View Results

The generator automatically creates both a JSON aerodeck and a PDF report.

```bash
# View the JSON aerodeck contents
aerodeck view ./results/{aircraft_name}_aerodeck.json

# Open the PDF report (automatically generated)
# Location: ./results/{aircraft_name}_aerodeck.pdf

# Or regenerate the report manually
aerodeck report ./results/{aircraft_name}_aerodeck.json
```

## Command Line Interface

### `aerodeck generate`

Generate aerodynamic deck from nTop geometry export.

```bash
aerodeck generate INPUT_DIR [OPTIONS]

Options:
  -o, --output-dir PATH    Output directory (default: ./results)
  -c, --config PATH        Configuration file (YAML)
  -v, --verbose            Enable verbose output
  -q, --quiet              Quiet mode (minimal output)
  --validate-only          Only validate geometry, do not run analysis
  --aircraft-name TEXT     Aircraft name for reports (default: "nTop Aircraft")
```

**Example:**
```bash
aerodeck generate ./aircraft_001/ -v --aircraft-name "MyDrone_V1"
```

### `aerodeck validate`

Validate nTop geometry export without running analysis.

```bash
aerodeck validate INPUT_DIR [OPTIONS]

Options:
  -v, --verbose  Enable verbose output
```

**Example:**
```bash
aerodeck validate ./aircraft_001/
```

### `aerodeck init-config`

Create a default configuration file.

```bash
aerodeck init-config OUTPUT_PATH
```

**Example:**
```bash
aerodeck init-config my_config.yaml
# Edit my_config.yaml to customize parameters
aerodeck generate ./aircraft_001/ --config my_config.yaml
```

### `aerodeck view`

View aerodynamic deck file contents.

```bash
aerodeck view DECK_FILE
```

**Example:**
```bash
aerodeck view ./results/aerodeck_6dof.json
```

### `aerodeck report`

Generate a comprehensive PDF report from an existing aerodeck JSON file.

```bash
aerodeck report DECK_FILE [OPTIONS]

Options:
  -o, --output PATH    Output PDF file path (default: same location as JSON)
```

**Example:**
```bash
# Generate report from aerodeck JSON
aerodeck report ./results/group3-nqx-rev1_aerodeck.json

# Specify custom output path
aerodeck report ./results/my_aerodeck.json -o ./reports/analysis_report.pdf
```

**What's in the report?**
- Summary page with metadata, reference geometry, and mass properties
- Static stability derivatives (CL_α, Cm_α, Cn_β, etc.)
- Dynamic stability derivatives (CL_q, Cm_q, Cl_p, etc.)
- Roll-yaw coupling characteristics
- Dynamic modes analysis (Dutch roll, spiral, roll subsidence)
- Dutch roll speed sweep
- Elevon control effectiveness with trim requirements
- Elevon forces and hinge loading at 10° deflection

## Configuration

Create a configuration file to customize analysis parameters:

```bash
aerodeck init-config config.yaml
```

### Example Configuration

```yaml
# Analysis settings
analysis:
  alpha_range: [-10, 20, 2]  # [min, max, step] in degrees
  beta_range: [-5, 5, 2]
  mach_numbers: [0.1, 0.3, 0.5]
  reynolds_numbers: [1.0e6, 2.0e6, 5.0e6]

  controls:
    elevon: [-30, 30, 10]  # degrees
    rudder: [-25, 25, 10]

# AVL settings
avl:
  executable: "avl"  # Path to AVL binary
  max_iterations: 100
  convergence_tolerance: 1e-6

# XFOIL settings
xfoil:
  executable: "xfoil"
  n_critical: 9
  max_iterations: 200
  viscous: true

# Output settings
output:
  formats: ["json", "pdf", "html"]
  save_intermediate: true
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
  warn_cg_shift: 0.05
```

## Input File Format

### mass.csv

Single row with mass properties:

| Column | Description | Units |
|--------|-------------|-------|
| mass | Total mass | kg |
| cg_x, cg_y, cg_z | Center of gravity | m |
| Ixx, Iyy, Izz | Principal moments of inertia | kg⋅m² |
| Ixy, Ixz, Iyz | Products of inertia (optional) | kg⋅m² |

### LEpts.csv, TEpts.csv

Panel point coordinates (one point per row):

| Column | Description | Units |
|--------|-------------|-------|
| x | X coordinate | m |
| y | Y coordinate | m |
| z | Z coordinate | m |

**Note:** Leading edge and trailing edge files must have the same number of points.

### WINGLETpts.csv, ELEVONpts.csv (Optional)

Same format as panel points above.

## Output Files

After running `aerodeck generate`, you'll find these files in the output directory:

1. **`{aircraft_name}.avl`** - AVL input file (human-readable geometry definition)
2. **`{aircraft_name}.mass`** - AVL mass file (mass, CG, inertia tensor)
3. **`{aircraft_name}_aerodeck.json`** - Machine-readable aero deck for 6-DOF simulation
4. **`{aircraft_name}_aerodeck.pdf`** - Comprehensive analysis report (auto-generated)
5. **`avl_outputs/`** - Directory containing all AVL text output files
6. **`polars/`** - Directory containing XFOIL airfoil polars (CSV format)

### Aerodeck JSON Structure

The `*_aerodeck.json` file contains:
- **Metadata**: Aircraft name, generation date, version info
- **Reference geometry**: Wing area, span, chord, CG location
- **Mass properties**: Mass, moments of inertia, products of inertia
- **Static stability**: CL_α, Cm_α, Cn_β, neutral point
- **Dynamic stability**: CL_q, Cm_q, Cl_p, Cn_r, etc.
- **Control surfaces**: Control effectiveness (Cm_δe, Cl_δa, etc.)
- **Airfoil polars**: Lift, drag, and moment vs. alpha at various Reynolds numbers

### PDF Report Contents

The automatically generated PDF report includes:
1. **Summary page**: Metadata, reference geometry, mass properties
2. **Static stability**: Longitudinal and lateral-directional derivatives
3. **Dynamic stability**: Pitch, roll, and yaw damping derivatives
4. **Roll-yaw coupling**: Adverse yaw and proverse roll characteristics
5. **Dynamic modes**: Dutch roll frequency/damping, spiral stability, roll time constant
6. **Control effectiveness**: Pitch and roll control authority with trim requirements
7. **Elevon loading**: Forces and hinge moments at various deflections

## Development Status

This project follows a 3-phase development plan:

### ✅ Phase 1: Core Infrastructure & AVL Integration (Current)

- [x] Project structure and packaging
- [x] CSV geometry loader
- [x] Geometry validation
- [x] AVL input file generator
- [x] AVL execution wrapper
- [x] Verbose logging system
- [x] Configuration management
- [x] Basic CLI
- [x] Unit tests

### 🔄 Phase 2: XFOIL Integration & Aero Deck Generation (Next)

- [ ] XFOIL integration
- [ ] Run matrix generation
- [ ] Aero deck data structure
- [ ] 6-DOF output file writer
- [ ] Stability derivative extraction
- [ ] Integration tests

### 📅 Phase 3: Reporting, Polish & Documentation

- [ ] PDF report generation
- [ ] HTML interactive reports
- [ ] 3D geometry visualization
- [ ] Comprehensive documentation
- [ ] Package distribution
- [ ] CI/CD pipeline

## Development

### Running Tests

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests with coverage
pytest

# Run specific test file
pytest tests/test_geometry_loader.py

# Run with verbose output
pytest -v
```

### Code Quality

```bash
# Format code
black aerodeck/

# Sort imports
isort aerodeck/

# Type checking
mypy aerodeck/

# Linting
flake8 aerodeck/
```

## Project Structure

```
ntop-aerodeck/
├── aerodeck/               # Main package
│   ├── geometry/           # Geometry loading and translation
│   │   ├── loader.py       # CSV file loader
│   │   ├── validator.py    # Geometry validation
│   │   └── avl_translator.py  # AVL format converter
│   ├── analysis/           # Analysis modules
│   │   ├── avl_runner.py   # AVL execution wrapper
│   │   └── xfoil_runner.py # XFOIL wrapper (Phase 2)
│   ├── output/             # Output generation
│   │   ├── report_generator.py  # Reports (Phase 3)
│   │   └── deck_writer.py       # Aero deck files
│   ├── utils/              # Utilities
│   │   ├── logger.py       # Verbose logging
│   │   └── config.py       # Configuration
│   └── cli.py              # Command-line interface
├── tests/                  # Test suite
├── examples/               # Example scripts
├── docs/                   # Documentation
├── requirements.txt        # Dependencies
├── pyproject.toml          # Package configuration
└── README.md              # This file
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Run the test suite
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Authors

nTop Team

## Acknowledgments

- AVL by Mark Drela (MIT)
- XFOIL by Mark Drela (MIT)

## Support

For issues, questions, or feature requests, please open an issue on GitHub.

---

**Status:** Phase 1 Complete ✅ | Next: Phase 2 Development 🔄
