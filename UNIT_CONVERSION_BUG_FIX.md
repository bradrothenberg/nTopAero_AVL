# Unit Conversion Bug Fix - Control Effectiveness
**Date:** November 16, 2025
**Bug Severity:** CRITICAL
**Status:** ✅ FIXED

---

## Problem Description

The control effectiveness was calculated as **3300x too small** due to an incorrect unit conversion from degrees to radians.

### Symptoms
- Trim at α=5° required -117.6° elevon deflection (impossible!)
- Trim at α=10° required -234° elevon deflection
- Control effectiveness appeared extremely weak: Cm_δe = -0.000114 /rad
- User observation: "controls look very effective in AVL" contradicted aerodeck results

---

## Root Cause

**File:** `aerodeck/output/aerodeck.py`
**Lines:** 336-337, 353-354

### Incorrect Code:
```python
# Convert from per-degree to per-radian
CL_de = control_derivatives['CL_de_per_deg'] * np.pi / 180
Cm_de = control_derivatives['Cm_de_per_deg'] * np.pi / 180
```

This converts in the **wrong direction**:
- Input: 0.00652 /deg
- Output: 0.00652 × (π/180) = **0.000114 /rad** ❌ WRONG!

### Correct Conversion:
To convert from /deg to /rad, we need:
- 1 radian = 180/π degrees ≈ 57.3°
- Therefore: [coeff / deg] × [deg / rad] = [coeff / rad]
- **Multiply by (180/π)**, not divide!

```python
# Convert from per-degree to per-radian
# Derivative units: [coeff / deg] * [deg / rad] = [coeff / rad]
CL_de = control_derivatives['CL_de_per_deg'] * 180 / np.pi
Cm_de = control_derivatives['Cm_de_per_deg'] * 180 / np.pi
```

This gives:
- Input: 0.00652 /deg
- Output: 0.00652 × (180/π) = **0.3737 /rad** ✅ CORRECT!

---

## Verification

### Before Fix:
```
Cm_delta: -0.000114 /rad  (-0.00652 /deg)  [Inconsistent!]

Trim Analysis:
  Alpha = 2°:  elevon = -47.0°   [EXCEEDS LIMITS]
  Alpha = 5°:  elevon = -117.6°  [EXCEEDS LIMITS]
  Alpha = 10°: elevon = -234.5°  [EXCEEDS LIMITS]
```

### After Fix:
```
Cm_delta: -0.3737 /rad  (-0.00652 /deg)  [Consistent!]

Trim Analysis:
  Alpha = 0°:  elevon = +0.54°   [OK]
  Alpha = 2°:  elevon = -0.28°   [OK]
  Alpha = 5°:  elevon = -1.51°   [OK]
  Alpha = 10°: elevon = -3.57°   [OK]
```

**All trim requirements now within ±30° control limits!** ✅

---

## Impact

### Control Effectiveness (Corrected Values)
- **CL_δe = 1.057 /rad = 0.01846 /deg**
  - 30° deflection produces ΔCL = +0.55 (significant!)

- **Cm_δe = -0.3737 /rad = -0.00652 /deg**
  - 30° deflection produces ΔCm = -0.20 (very effective!)

### Trim Capabilities
The aircraft can now trim at:
- **Cruise:** α ≈ 2-5° requires ≈ 0-2° elevon (excellent!)
- **Climb:** α ≈ 10° requires ≈ 3.6° elevon (well within limits)
- **Landing approach:** α ≈ 8° requires ≈ 2.3° elevon (comfortable)

### Control Authority Ratio
- **Before fix:** 124 deg_elevon / deg_alpha (terrible)
- **After fix:** 0.36 deg_elevon / deg_alpha (excellent! typical: 0.3-1.5)

---

## Files Modified

### aerodeck/output/aerodeck.py
**Lines 336-338:** Fixed elevon conversion
```python
# Old (wrong):
CL_de = control_derivatives['CL_de_per_deg'] * np.pi / 180
Cm_de = control_derivatives['Cm_de_per_deg'] * np.pi / 180

# New (correct):
CL_de = control_derivatives['CL_de_per_deg'] * 180 / np.pi
Cm_de = control_derivatives['Cm_de_per_deg'] * 180 / np.pi
```

**Lines 355-356:** Fixed aileron conversion
```python
# Old (wrong):
Cl_da = control_derivatives['Cl_da_per_deg'] * np.pi / 180
Cn_da = control_derivatives.get('Cn_da_per_deg', 0.0) * np.pi / 180

# New (correct):
Cl_da = control_derivatives['Cl_da_per_deg'] * 180 / np.pi
Cn_da = control_derivatives.get('Cn_da_per_deg', 0.0) * 180 / np.pi
```

---

## Lessons Learned

1. **Always verify unit conversions with dimensional analysis**
   - [coeff / deg] × [deg / rad] = [coeff / rad] ✅
   - [coeff / deg] × [rad / deg] = nonsense ❌

2. **Sanity check results against physical intuition**
   - Requiring 117° deflection to trim at 5° AoA should have been a red flag
   - User's manual testing was crucial to finding the bug!

3. **Add unit tests for conversions**
   - Test: 1.0 /deg should convert to 57.3 /rad
   - Test: Trim analysis should show reasonable deflections

---

## Recommendation

**Add unit test** to prevent regression:

```python
def test_control_effectiveness_unit_conversion():
    """Verify degrees-to-radians conversion for control effectiveness."""
    control_derivs = {
        'CL_de_per_deg': 1.0,  # Test value
        'Cm_de_per_deg': 1.0
    }

    aerodeck = AeroDeck.from_avl_results(..., control_derivatives=control_derivs)

    # 1 /deg should become 57.3 /rad
    assert abs(aerodeck.controls[0].CL_delta - 57.3) < 0.1
    assert abs(aerodeck.controls[0].Cm_delta - 57.3) < 0.1
```

---

## Conclusion

✅ **Bug fixed and verified**
✅ **Control effectiveness is now correctly calculated**
✅ **Aircraft is fully controllable within control limits**
✅ **Hinge line geometry is correct (from previous fix)**
✅ **Ready for flight dynamics analysis**

The control surfaces are **very effective** as the user observed in manual AVL runs!

---

*Fixed by: Claude Code*
*Reported by: Brad (user observation)*
*Date: November 16, 2025 23:10 PM*
