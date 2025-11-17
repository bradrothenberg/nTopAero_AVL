# Hinge Line Correction - Summary Report
**Date:** November 16, 2025
**Aircraft:** group3-NQX-rev1

---

## Problem Identified

The AVL file had **incorrect hinge line positions** that did not match the elevon leading edge defined in `ELEVONpts.csv`.

### Root Cause
The AVL file contained hinge positions calculated from a previous modification attempt to `ELEVONpts.csv`. When the CSV was reverted to original values, the AVL file was not regenerated, causing an 8-inch mismatch at the root.

---

## Fix Applied

**Action:** Regenerated AVL file from current (original) `ELEVONpts.csv`

**Result:** ✅ **Hinge line now correctly follows elevon LE sweep**

---

## Verification Results

### Elevon LE Definition (from CSV)
- **Root:** X = 5.745 ft, Y = 2.000 ft
- **Tip:** X = 6.750 ft, Y = 5.750 ft
- **Span:** 3.75 ft (45 inches)

### Hinge Position Verification

| Section | Y [ft] | AVL Hinge | Expected Hinge X | Error | Status |
|---------|--------|-----------|------------------|-------|--------|
| 3 (root) | 1.997 | 85.0% (5.745 ft) | 5.745 ft | 0.00 in | ✅ OK |
| 4 | 5.742 | 51.4% (6.748 ft) | 6.748 ft | 0.00 in | ✅ OK |
| 5 (tip) | 5.992 | 50.0% (6.893 ft) | 6.750 ft | +1.72 in | ⚠️ Clamped* |

*Section 5 is beyond elevon span, so hinge is clamped to 50% minimum

---

## Control Surface Sizing

### Current Configuration

| Section | Y [ft] | Hinge | Control Surface | Notes |
|---------|--------|-------|-----------------|-------|
| 3 | 2.000 | 85.0% | **15.0%** | ⚠️ Too small for effective pitch control |
| 4 | 5.742 | 51.4% | **48.6%** | ✅ Reasonable size |
| 5 | 5.992 | 50.0% | **50.0%** | ✅ Good size |

**Key Issue:** The elevon LE is positioned very far aft at the root (X=5.745 ft vs wing TE at X=6.406 ft), creating only **15% control surface** at Section 3.

---

## Control Effectiveness Analysis

### Before Fix (Incorrect Hinge Line)
- Hinge at Section 3: 70% chord (X=5.081 ft)
- Control surface: 30% chord
- **Cm_δe = -0.00635 /deg**

### After Fix (Correct Hinge Line)
- Hinge at Section 3: 85% chord (X=5.745 ft)
- Control surface: 15% chord
- **Cm_δe = -0.00652 /deg**

**Conclusion:** Control effectiveness is essentially unchanged (+2.7% improvement). The hinge line fix corrects the geometry representation but does not solve the fundamental control authority problem.

---

## Trim Analysis

With corrected geometry:

| Alpha | Required Elevon | Within Limits? |
|-------|-----------------|----------------|
| 2° | **-47.0°** | ❌ NO (limit ±30°) |
| 5° | **-117.6°** | ❌ NO (limit ±30°) |

**Status:** ❌ **Aircraft cannot be trimmed at moderate angles of attack**

---

## Root Cause of Weak Control Effectiveness

The fundamental problem is **extremely high static stability** combined with **small control surface at root**:

1. **Static Stability:** Cm_α = -0.153 /rad (very stable)
2. **Control Effectiveness:** Cm_δe = -0.00652 /deg (very weak)
3. **Authority Ratio:** 23.5 deg_elevon/deg_alpha (typical: 0.3-1.5)

This means the elevon must deflect **23.5 degrees for every 1 degree of alpha** - completely impractical!

---

## Recommendations

### Option 1: Increase Control Surface Size ⭐ RECOMMENDED
**Move elevon LE forward** to create larger control surface at root:
- Current root LE: X = 5.745 ft (85% chord, 15% control)
- **Target root LE: X ≈ 3.3 ft (50% chord, 50% control)**

This would roughly **triple** control effectiveness (Cm_δe ≈ -0.020 /deg), reducing trim at α=5° from -117° to **-38°** (still outside limits but much better).

### Option 2: Move CG Aft
**Reduce static stability** by moving CG aft:
- Current CG: X = 3.47 ft
- Need to reduce Cm_α from -0.153 to ≈ -0.05 /rad
- Would require CG shift of ~1 ft aft

⚠️ **Risk:** Reduced static stability affects handling qualities and spiral stability

### Option 3: Redesign Control Surface Layout
**Split elevon into elevator + aileron** with separate surfaces:
- Pure elevator on inboard section (larger chord)
- Ailerons on outboard section (current elevon position)

This would optimize pitch control authority while maintaining roll control.

---

## Files Updated

- ✅ `results/group3-nqx-rev1.avl` - Regenerated with correct hinge positions
- ✅ `results/group3-nqx-rev1_aerodeck.json` - Updated with correct geometry
- ✅ `results/planform_updated_nov16.png` - Visualization showing correct hinge line

---

## Next Steps

**Decision Required:** Choose one of the three options above to address control effectiveness:

1. **Increase control surface size** (easiest, most effective)
2. **Move CG aft** (requires mass redistribution)
3. **Redesign control layout** (most complex, best performance)

---

## Technical Details

### AVL Hinge Line Calculation
The hinge position is interpolated along the elevon LE sweep line:

```python
# Linear interpolation at section Y coordinate
y_frac = (section_y - elevon_root_y) / (elevon_tip_y - elevon_root_y)
elevon_hinge_x = elevon_root_le_x + (elevon_tip_le_x - elevon_root_le_x) * y_frac

# Hinge as fraction of wing chord
hinge_frac = (elevon_hinge_x - section_le_x) / section_chord
```

This correctly tracks the swept elevon LE geometry provided in `ELEVONpts.csv`.

### Control Authority Ratio
```
Authority Ratio = |Cm_α| / |Cm_δe| = 0.153 / 0.00652 = 23.5 deg/deg
```

**Typical values:** 0.3 to 1.5 deg/deg (this design is **15x too high**)

---

*Generated by nTop AeroDeck Generator*
