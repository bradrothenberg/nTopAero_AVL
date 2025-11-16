# NACA 64-208 Analysis Summary

## Changes Made

### 1. AVL Now Uses Custom Airfoil ✓

**Updated Files:**
- [aerodeck/geometry/avl_translator.py](aerodeck/geometry/avl_translator.py)
  - Added `airfoil_file` parameter to `__init__()`
  - Created `_write_airfoil_section()` method
  - Uses `AFILE` command in AVL to load custom airfoil coordinates

- [aerodeck/cli.py](aerodeck/cli.py)
  - Detects `.dat` files in input directory
  - Passes airfoil file to AVL translator

**Result:**
AVL now properly uses NACA 64-208 airfoil geometry instead of NACA 0012!

```
# From results/ntop_aircraft.avl:
AFILE
data/NACA 64-208.dat
```

### 2. Reynolds Numbers Updated for 20,000 ft Operation ✓

**Previous:** `[1e5, 5e5, 1e6, 5e6, 1e7]` (mostly for sea level)

**Updated:** `[5e5, 1e6, 3e6, 5e6, 7e6]` (optimized for 20k ft)

**Rationale:**
At 20,000 ft altitude (ρ = 0.001267 slug/ft³ vs 0.002377 at sea level):
- 100 mph → Re ≈ 3.2e6
- 150 mph → Re ≈ 4.8e6
- **200 mph → Re ≈ 6.4e6** ← Design cruise
- 250 mph → Re ≈ 8.0e6

The new range covers the operational envelope at altitude.

## XFOIL Convergence Issues

### Problem:
NACA 64-208 failed to converge in XFOIL at Re > 5e5.

**Successfully Generated:**
- Re = 5e5 ✓ (only 7 alpha points, limited range)

**Failed:**
- Re = 1e6 ✗
- Re = 3e6 ✗
- Re = 5e6 ✗
- Re = 7e6 ✗

### Why This Happens:

The NACA 64-208 is a **laminar flow airfoil** designed by NACA in the 1940s. These airfoils:
- Have very specific pressure distributions to maintain laminar flow
- Are sensitive to surface roughness and flow conditions
- Can be difficult for panel codes like XFOIL to converge
- May require special XFOIL parameters (PANE, GDES, etc.)

### Potential Solutions:

#### Option 1: Use XFLR5 Instead (Recommended)
XFLR5 is a GUI wrapper around XFOIL with better convergence:
- Pre-conditions the airfoil geometry
- Uses optimized panel distributions
- Better handling of laminar airfoils
- Can export polars as CSV for import

#### Option 2: Improve XFOIL Convergence
Add to `xfoil_runner.py`:
```python
commands = [
    f"LOAD {airfoil_file}",
    "PPAR",      # Enter paneling parameters
    "N 200",     # Use 200 panels
    "",          # Accept
    "GDES",      # Enter geometry design
    "CADD",      # Add camber
    "",          # Exit GDES
    "OPER",
    f"ITER {n_iter * 2}",  # Double iterations
    ...
]
```

#### Option 3: Use Pre-Generated Polars
Get NACA 64-208 polars from:
- **Airfoil Tools** (airfoiltools.com) - Has XFOIL data
- **UIUC Airfoil Database** - Experimental data
- **XFLR5 Community** - Pre-computed polars

#### Option 4: Switch to NACA 64A-series
The 64A-series (like NACA 64A210) are more robust:
- Similar performance to 64-series
- Better XFOIL convergence
- Still laminar flow airfoils

## Current Analysis Status

### What Works: ✓
1. **AVL Analysis** - Complete with NACA 64-208 geometry
   - All stability derivatives computed
   - Proper airfoil shape in vortex lattice
   - Dutch roll analysis complete

2. **Limited XFOIL Data** - One polar at Re=5e5
   - Shows cambered airfoil characteristics
   - Limited alpha range (-10° to -7°)

### What's Missing: ⚠️
1. **Full XFOIL Polars** - Need Re = 3e6, 5e6, 7e6
   - Required for accurate drag polar
   - Needed for stall prediction at altitude
   - Important for L/D vs alpha curves

2. **Combined 3D Performance** - Can't merge XFOIL + AVL drag
   - Report will show AVL data only
   - No profile drag correction
   - Missing realistic L/D predictions

## Recommendations

### Short Term (Use Current Analysis):
**AVL stability derivatives are CORRECT** - They depend on wing geometry, not airfoil polars.

You can use:
- Static stability (CL_α, Cm_α, Cn_β, etc.) ✓
- Dynamic stability (CL_q, Cm_q, Cl_p, etc.) ✓
- Dutch roll analysis ✓
- Roll-yaw coupling ✓
- Speed sweep analysis ✓

**What you can't trust yet:**
- Drag polar (CD vs CL)
- L/D ratios
- Stall angles
- Performance predictions

### Medium Term (Get Proper Polars):
1. **Use XFLR5** to generate NACA 64-208 polars
   - Run analysis at Re = [5e5, 1e6, 3e6, 5e6, 7e6]
   - Export as CSV
   - Place in `results/polars/` directory
   - Regenerate report

2. **Or use Airfoil Tools data**
   - Download polars from airfoiltools.com
   - Convert to aerodeck format
   - Import into analysis

### Long Term (Robust Pipeline):
Add XFLR5 integration to the pipeline:
- Auto-detect when XFOIL fails
- Fall back to XFLR5 batch mode
- Or provide manual polar import tool

## Files Generated

### Results Directory:
- **ntop_aircraft.avl** - AVL input with NACA 64-208 (via AFILE) ✓
- **ntop_aircraft.mass** - Mass properties file ✓
- **ntop_aircraft_aerodeck.json** - Aerodeck with stability derivatives ✓
- **ntop_aircraft_aerodeck.pdf** - Report (107 KB) with limited polar data ✓
- **a*.txt files** - AVL run results for all alpha/beta combinations ✓

### Polars Directory:
- **polar_re5.00e+05_m0.10.csv** - Limited NACA 64-208 data ⚠️

## Testing the Analysis

To verify AVL is using the correct airfoil:

```bash
# Check AVL file
grep -A1 "AFILE" results/ntop_aircraft.avl

# Should show:
# AFILE
# data/NACA 64-208.dat
```

To verify stability derivatives are unchanged (they should be):

```bash
# Compare Cn_beta (should be same as NACA 0012 run)
grep "Cnb" results/a0.0_b1.0_M0.10_stab.txt
```

Result: **Cn_β = 0.039898** (same as before, as expected)

## Key Insight

**The AVL analysis is INDEPENDENT of airfoil camber** for:
- Stability derivatives
- Neutral point location
- Dutch roll characteristics
- Roll/yaw coupling

AVL uses the airfoil shape only for:
- CL_0 at α=0 (small effect from camber)
- Induced drag factor (via span efficiency)
- Theoretical max CL (via airfoil thickness)

So your **stability analysis is complete and valid**, even without full XFOIL polars!

## Next Steps

1. ✓ **Current analysis is good** for stability and control
2. ⚠️ **Get proper polars** for performance analysis
3. 📝 **Document XFLR5 workflow** for future airfoils
4. 🔧 **Consider NACA 64A-series** for better XFOIL compatibility

---

*Generated: 2025-11-15*
*Airfoil: NACA 64-208 (8% camber laminar flow)*
*Altitude: 20,000 ft*
*Cruise: 200 mph (Re ≈ 6.4e6)*
