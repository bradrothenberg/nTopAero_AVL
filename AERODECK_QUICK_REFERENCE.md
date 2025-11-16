# AeroDeck Quick Reference

## Your Aircraft Summary

**File:** `results/ntop_aircraft_aerodeck.json`

### Key Specifications

| Parameter | Value | Units |
|-----------|-------|-------|
| **Wing Area** | 52.07 | ft² |
| **Wing Span** | 11.98 | ft |
| **MAC** | 5.75 | ft |
| **Mass** | 523.7 | lbm |
| **CG Location** | (3.66, 0.0, 0.25) | ft |
| **Static Margin** | 5.77% MAC | - |

### Stability Assessment at Cruise

| Characteristic | Value | Status |
|----------------|-------|--------|
| **Lift curve slope** (CL_α) | 2.84 /rad | ✓ Good |
| **Pitch stability** (Cm_α) | -0.16 /rad | ✓ Stable |
| **Dihedral effect** (Cl_β) | -0.04 /rad | ✓ Stable |
| **Directional stability** (Cn_β) | 0.04 /rad | ✓ Stable |
| **Pitch damping** (Cm_q) | -0.77 /rad | ✓ Well damped |
| **Roll damping** (Cl_p) | -0.23 /rad | ✓ Well damped |
| **Yaw damping** (Cn_r) | -0.03 /rad | ✓ Damped |
| **Adverse yaw** (Cn_p) | +0.02 /rad | ⚠ Proverse* |

*Proverse yaw at cruise (α < 5°), normal adverse yaw at higher α

### Performance

| Metric | Value |
|--------|-------|
| **Max L/D** | ~13-15 @ α ≈ 4-6° |
| **Stall angle (Re=1e6)** | ~15.5° |
| **Neutral point** | 3.995 ft (5.77% MAC aft of CG) |

---

## Quick Code Example

### Python: Load and Use

```python
import json
import numpy as np

# Load aerodeck
with open('results/ntop_aircraft_aerodeck.json', 'r') as f:
    aero = json.load(f)

# Get key parameters
S_ref = aero['reference_geometry']['S_ref_ft2']  # 52.07 ft²
CL_alpha = aero['aerodynamics']['static_stability']['longitudinal']['CL_alpha_per_rad']  # 2.84

# Compute lift at 5° angle of attack
alpha = np.deg2rad(5.0)
V = 100.0  # ft/s
rho = 0.002377  # slug/ft³
q = 0.5 * rho * V**2  # Dynamic pressure

CL = CL_alpha * alpha  # 0.248
L = CL * q * S_ref     # ~146 lbf
```

---

## Force & Moment Equations

### Body Frame Forces
```
X = CX · q∞ · S_ref
Y = CY · q∞ · S_ref
Z = CZ · q∞ · S_ref
```

### Body Frame Moments
```
L = Cl · q∞ · S_ref · b_ref
M = Cm · q∞ · S_ref · c_ref
N = Cn · q∞ · S_ref · b_ref
```

### Non-dimensional Rates
```
p̂ = p · b / (2V)
q̂ = q · c / (2V)
r̂ = r · b / (2V)
```

---

## Units Cheat Sheet

| Quantity | Unit | Conversion |
|----------|------|------------|
| Length | ft | 1 ft = 0.3048 m |
| Speed | ft/s | 1 ft/s = 0.6818 mph |
| Mass | lbm | 1 lbm = 0.4536 kg |
| Force | lbf | 1 lbf = 4.448 N |
| Density | slug/ft³ | ρ_SL = 0.002377 |
| Angle | rad | 1° = 0.01745 rad |

---

## Coordinate System

```
      X (forward)
      ↑
      |
      |___→ Y (right)
     /
    ↙ Z (down)
```

**Positive rotations:**
- **p** (roll): Right wing down
- **q** (pitch): Nose up
- **r** (yaw): Nose right

---

## Common Flight Conditions

### Sea Level (Standard Atmosphere)
- ρ = 0.002377 slug/ft³
- T = 59°F (15°C)
- p = 2116.2 lbf/ft²

### Reynolds Number
```
Re = ρ · V · c_ref / μ

Typical values:
- Cruise (70 mph): Re ≈ 1.2e6
- Max speed (100 mph): Re ≈ 1.7e6
```

### Dynamic Pressure
```
q∞ = 0.5 · ρ · V²

Examples:
- 50 ft/s (34 mph): q = 2.97 lbf/ft²
- 100 ft/s (68 mph): q = 11.89 lbf/ft²
```

---

## Stall Angles (by Reynolds Number)

| Re | Stall α | CL_max |
|----|---------|--------|
| 1e5 | 10° | 0.96 |
| 5e5 | 14.5° | 1.22 |
| 1e6 | 15.5° | 1.37 |
| 5e6 | 19° | 1.74 |
| 1e7 | 19.5° | 1.85 |

---

## Files Generated

- **`ntop_aircraft_aerodeck.json`** - Complete aerodynamic database
- **`ntop_aircraft_aerodeck.pdf`** - Detailed analysis report (8 pages)
- **`AERODECK_USAGE_GUIDE.md`** - Full documentation (this file)

---

*For detailed documentation, see AERODECK_USAGE_GUIDE.md*
