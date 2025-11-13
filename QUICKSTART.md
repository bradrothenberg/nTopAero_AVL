# Quick Start Guide

Get up and running with nTop AeroDeck Generator in 5 minutes!

## 1. Installation (30 seconds)

```bash
# Clone or navigate to the repository
cd ntop-aerodeck

# Install the package
pip install -e .
```

## 2. Verify Installation (10 seconds)

```bash
# Check that the CLI is available
aerodeck --help

# Should show:
# Usage: aerodeck [OPTIONS] COMMAND [ARGS]...
#   nTop AeroDeck Generator - Automated aerodynamic deck generation.
```

## 3. Validate Your Geometry (30 seconds)

```bash
# Validate the sample data included in the repo
aerodeck validate Data/ -v

# Or validate your own nTop export
aerodeck validate /path/to/your/export/ -v
```

**Expected Output:**
```
[HH:MM:SS] Starting analysis...
[HH:MM:SS]   ✓ Loaded 5 geometry files
[HH:MM:SS]   → Validating geometry...
[HH:MM:SS]   ✓ All validation checks passed
```

## 4. Generate Your First Aerodeck (2 minutes)

```bash
# Generate aerodeck with verbose output
aerodeck generate Data/ -v --aircraft-name "MyDrone_V1"

# Or with custom output directory
aerodeck generate Data/ -v -o ./my_results/
```

**Expected Output:**
```
═══════════════════════════════════════════════════════
  nTop AeroDeck Generator v1.0.0
═══════════════════════════════════════════════════════

┌─ Phase 1: Geometry Loading ────────────────────────┐
│ [HH:MM:SS]   ✓ mass.csv        (mass=523.71 kg)   │
│ [HH:MM:SS]   ✓ LEpts.csv       (5 points)          │
│ [HH:MM:SS]   ✓ TEpts.csv       (5 points)          │
│ [HH:MM:SS]   ✓ WINGLETpts.csv  (7 points)          │
│ [HH:MM:SS]   ✓ ELEVONpts.csv   (4 points)          │
└────────────────────────────────────────────────────┘

┌─ Phase 2: Geometry Validation ─────────────────────┐
│ [HH:MM:SS]   ✓ All validation checks passed        │
└────────────────────────────────────────────────────┘

┌─ Phase 3: AVL Input Generation ────────────────────┐
│ [HH:MM:SS]   → Computed S_ref = XX.X m²            │
│ [HH:MM:SS]   → Computed b_ref = XX.X m             │
│ [HH:MM:SS]   → Computed c_ref = X.XX m (MAC)       │
│ [HH:MM:SS]   ✓ AVL input written: mydrone_v1.avl   │
└────────────────────────────────────────────────────┘

┌─ Phase 4: AVL Analysis ────────────────────────────┐
│ [HH:MM:SS] Running AVL (16 flight conditions)...   │
│ [HH:MM:SS] [████████████████████████████████] 100% │
│ [HH:MM:SS]   ✓ All cases completed                 │
└────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════
  ✓ Analysis complete!

  Output files:
    → ./results/mydrone_v1.avl
    → ./results/[additional analysis files]
═══════════════════════════════════════════════════════
```

## 5. Customize Your Analysis (1 minute)

Create a custom configuration file:

```bash
# Generate default config
aerodeck init-config my_config.yaml

# Edit the file (change alpha range, Mach numbers, etc.)
# Then run with your config
aerodeck generate Data/ --config my_config.yaml -v
```

**Example config.yaml:**
```yaml
analysis:
  alpha_range: [-10, 20, 2]  # Min, max, step in degrees
  beta_range: [-5, 5, 2]
  mach_numbers: [0.1, 0.3, 0.5]

avl:
  executable: "avl"  # Or full path: "C:/AVL/avl.exe"
```

## What Gets Generated?

After running `aerodeck generate`, you'll have:

1. **`aircraft.avl`** - AVL input file
   - Human-readable geometry definition
   - Can be opened directly in AVL for manual analysis

2. **AVL output files** - Analysis results
   - Force and moment coefficients
   - Stability derivatives
   - Convergence information

3. **Future (Phase 2/3):**
   - `aerodeck_6dof.json` - Machine-readable aero deck
   - `aerodeck_report.pdf` - Comprehensive report
   - Plots and visualizations

## Programmatic Usage

You can also use the package directly in Python:

```python
from pathlib import Path
from aerodeck.geometry.loader import GeometryLoader
from aerodeck.geometry.validator import GeometryValidator
from aerodeck.geometry.avl_translator import AVLGeometryWriter

# Load
loader = GeometryLoader(verbose=True)
geometry = loader.load_panel_data(Path("Data"))

# Validate
validator = GeometryValidator(verbose=True)
result = validator.validate(geometry)

# Generate AVL
writer = AVLGeometryWriter(verbose=True)
ref_geom = writer.write_avl_input(
    geometry,
    Path("aircraft.avl"),
    "MyAircraft"
)

print(f"Reference area: {ref_geom.area:.3f} m²")
print(f"Reference span: {ref_geom.span:.3f} m")
```

See [examples/basic_usage.py](examples/basic_usage.py) for a complete example.

## Troubleshooting

### "AVL executable not found"

The tool will run without AVL and generate mock results for development. To use real AVL:

1. Install AVL from [MIT AVL website](http://web.mit.edu/drela/Public/web/avl/)
2. Add AVL to your PATH, or
3. Specify full path in config.yaml:
   ```yaml
   avl:
     executable: "C:/path/to/avl.exe"
   ```

### "FileNotFoundError: Missing required files"

Make sure your nTop export directory contains:
- `mass.csv` (required)
- `LEpts.csv` (required)
- `TEpts.csv` (required)
- `WINGLETpts.csv` (optional)
- `ELEVONpts.csv` (optional)

### "Validation failed"

Check the error messages for details. Common issues:
- Leading edge and trailing edge must have same number of points
- Mass must be positive
- Inertia tensor must be symmetric and positive definite

Run with `-v` flag for detailed validation output:
```bash
aerodeck validate Data/ -v
```

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Check [PROJECT_STATUS.md](PROJECT_STATUS.md) for development roadmap
- Review [Plan/AeroDeck_Pipeline_Development_Plan.md](Plan/AeroDeck_Pipeline_Development_Plan.md) for complete feature list

## Need Help?

- Check CLI help: `aerodeck [command] --help`
- Review the development plan for feature roadmap
- Open an issue on GitHub (when available)

---

**Happy Analyzing!** 🚀✈️
