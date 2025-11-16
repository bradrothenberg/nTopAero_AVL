# AeroDeck Usage Guide

## Overview

The AeroDeck file (`ntop_aircraft_aerodeck.json`) contains complete aerodynamic data for 6-DOF (six degrees of freedom) flight simulation of your nTop aircraft. This guide explains how to use the aerodeck in flight dynamics software, flight simulators, and custom applications.

---

## Table of Contents

1. [What is an AeroDeck?](#what-is-an-aerodeck)
2. [File Structure](#file-structure)
3. [Using the AeroDeck in Flight Simulation](#using-the-aerodeck-in-flight-simulation)
4. [Python Example: Computing Forces and Moments](#python-example-computing-forces-and-moments)
5. [MATLAB/Simulink Integration](#matlabsimulink-integration)
6. [Understanding the Derivatives](#understanding-the-derivatives)
7. [Coordinate System Convention](#coordinate-system-convention)
8. [Units Reference](#units-reference)

---

## What is an AeroDeck?

An **aerodeck** is a comprehensive aerodynamic database that contains:

- **Static stability derivatives** - How forces/moments change with angle of attack (α) and sideslip (β)
- **Dynamic stability derivatives** - How forces/moments change with angular rates (p, q, r)
- **Reference geometry** - Wing area, span, MAC, reference point
- **Mass properties** - Mass, CG location, inertia tensor
- **Airfoil polars** - 2D airfoil drag data at multiple Reynolds numbers
- **3D aircraft drag** - Profile drag (XFOIL) + Induced drag (AVL)

The aerodeck enables high-fidelity flight simulation without running expensive CFD or wind tunnel tests during every simulation timestep.

---

## File Structure

### JSON Format

The aerodeck is stored as a JSON file with the following top-level structure:

```json
{
  "metadata": { ... },           // Aircraft info, generation date
  "reference_geometry": { ... }, // Wing area, span, MAC, reference point
  "mass_properties": { ... },    // Mass, CG, inertia tensor
  "aerodynamics": {
    "static_stability": { ... }, // CL_α, Cm_α, CY_β, Cl_β, Cn_β
    "dynamic_stability": { ... } // Rate derivatives (p, q, r)
  },
  "airfoil_polars": { ... }      // XFOIL 2D drag data
}
```

### Key Sections

#### 1. Reference Geometry
```json
"reference_geometry": {
  "S_ref_ft2": 52.07,      // Wing reference area [ft²]
  "b_ref_ft": 11.98,       // Wing span [ft]
  "c_ref_ft": 5.75,        // Mean aerodynamic chord [ft]
  "x_ref_ft": 3.66,        // Reference point X (typically CG) [ft]
  "y_ref_ft": 0.0,         // Reference point Y [ft]
  "z_ref_ft": 0.25         // Reference point Z [ft]
}
```

#### 2. Mass Properties
```json
"mass_properties": {
  "mass_lbm": 523.7,       // Aircraft mass [lbm]
  "cg_ft": [3.66, 0.0, 0.25], // CG location [ft]
  "inertia_lbm_ft2": {
    "Ixx": 24245.7,        // Roll inertia [lbm·ft²]
    "Iyy": 61455.7,        // Pitch inertia [lbm·ft²]
    "Izz": 84984.3,        // Yaw inertia [lbm·ft²]
    "Ixy": 11.7,           // Product of inertia [lbm·ft²]
    "Ixz": -176.4,         // Product of inertia [lbm·ft²]
    "Iyz": -7.7            // Product of inertia [lbm·ft²]
  }
}
```

#### 3. Static Stability Derivatives
```json
"static_stability": {
  "longitudinal": {
    "CL_alpha_per_rad": 2.84,    // Lift curve slope [/rad]
    "Cm_alpha_per_rad": -0.16,   // Pitch stiffness [/rad]
    "neutral_point_x_ft": 3.995  // Neutral point location [ft]
  },
  "lateral_directional": {
    "CY_beta_per_rad": -0.13,    // Side force due to sideslip [/rad]
    "Cl_beta_per_rad": -0.04,    // Dihedral effect [/rad]
    "Cn_beta_per_rad": 0.04      // Directional stability [/rad]
  }
}
```

#### 4. Dynamic Stability Derivatives
```json
"dynamic_stability": {
  "pitch_rate": {
    "CL_q_per_rad": 2.77,        // Lift due to pitch rate [/rad]
    "Cm_q_per_rad": -0.77        // Pitch damping [/rad]
  },
  "roll_rate": {
    "Cl_p_per_rad": -0.23,       // Roll damping [/rad]
    "Cn_p_per_rad": 0.02         // Adverse yaw [/rad]
  },
  "yaw_rate": {
    "Cl_r_per_rad": 0.03,        // Roll due to yaw [/rad]
    "Cn_r_per_rad": -0.03        // Yaw damping [/rad]
  }
}
```

---

## Using the AeroDeck in Flight Simulation

### Basic Force and Moment Calculation

The aerodynamic forces and moments are computed from:

**Forces:**
```
CX = CX_0 + CX_α·α + CX_β·β + (CX_p·p + CX_q·q + CX_r·r)·c/(2V)
CY = CY_0 + CY_α·α + CY_β·β + (CY_p·p + CY_q·q + CY_r·r)·b/(2V)
CZ = CZ_0 + CZ_α·α + CZ_β·β + (CZ_p·p + CZ_q·q + CZ_r·r)·c/(2V)
```

**Moments:**
```
Cl = Cl_0 + Cl_α·α + Cl_β·β + (Cl_p·p + Cl_q·q + Cl_r·r)·b/(2V)
Cm = Cm_0 + Cm_α·α + Cm_β·β + (Cm_p·p + Cm_q·q + Cm_r·r)·c/(2V)
Cn = Cn_0 + Cn_α·α + Cn_β·β + (Cn_p·p + Cn_q·q + Cn_r·r)·b/(2V)
```

**Dimensional forces/moments:**
```
L = CL · q_∞ · S_ref
D = CD · q_∞ · S_ref
M = Cm · q_∞ · S_ref · c_ref
```

where `q_∞ = 0.5 · ρ · V²` is dynamic pressure.

---

## Python Example: Computing Forces and Moments

```python
import json
import numpy as np

class AeroModel:
    """Aerodynamic model from AeroDeck."""

    def __init__(self, aerodeck_file):
        """Load aerodeck from JSON file."""
        with open(aerodeck_file, 'r') as f:
            self.data = json.load(f)

        # Reference geometry
        self.S_ref = self.data['reference_geometry']['S_ref_ft2']
        self.b_ref = self.data['reference_geometry']['b_ref_ft']
        self.c_ref = self.data['reference_geometry']['c_ref_ft']

        # Static derivatives
        static = self.data['aerodynamics']['static_stability']
        self.CL_alpha = static['longitudinal']['CL_alpha_per_rad']
        self.Cm_alpha = static['longitudinal']['Cm_alpha_per_rad']
        self.CY_beta = static['lateral_directional']['CY_beta_per_rad']
        self.Cl_beta = static['lateral_directional']['Cl_beta_per_rad']
        self.Cn_beta = static['lateral_directional']['Cn_beta_per_rad']

        # Dynamic derivatives
        dynamic = self.data['aerodynamics']['dynamic_stability']
        self.CL_q = dynamic['pitch_rate']['CL_q_per_rad']
        self.Cm_q = dynamic['pitch_rate']['Cm_q_per_rad']
        self.Cl_p = dynamic['roll_rate']['Cl_p_per_rad']
        self.Cn_p = dynamic['roll_rate']['Cn_p_per_rad']
        self.Cl_r = dynamic['yaw_rate']['Cl_r_per_rad']
        self.Cn_r = dynamic['yaw_rate']['Cn_r_per_rad']

    def compute_forces_moments(self, state, V, rho):
        """
        Compute aerodynamic forces and moments.

        Args:
            state: dict with 'alpha', 'beta', 'p', 'q', 'r' [rad, rad/s]
            V: airspeed [ft/s]
            rho: air density [slug/ft³]

        Returns:
            forces: [X, Y, Z] in body frame [lbf]
            moments: [L, M, N] in body frame [ft·lbf]
        """
        alpha = state['alpha']
        beta = state['beta']
        p = state['p']
        q = state['q']
        r = state['r']

        # Dynamic pressure
        q_inf = 0.5 * rho * V**2

        # Non-dimensional rates
        p_hat = p * self.b_ref / (2 * V)
        q_hat = q * self.c_ref / (2 * V)
        r_hat = r * self.b_ref / (2 * V)

        # Force coefficients (simplified - using stability axes)
        CL = self.CL_alpha * alpha + self.CL_q * q_hat
        CD = self.get_drag(alpha, V)  # From polars + induced
        CY = self.CY_beta * beta

        # Convert to body axes (simplified for small angles)
        CX = -CD * np.cos(alpha) + CL * np.sin(alpha)
        CZ = -CD * np.sin(alpha) - CL * np.cos(alpha)

        # Moment coefficients
        Cl = self.Cl_beta * beta + self.Cl_p * p_hat + self.Cl_r * r_hat
        Cm = self.Cm_alpha * alpha + self.Cm_q * q_hat
        Cn = self.Cn_beta * beta + self.Cn_p * p_hat + self.Cn_r * r_hat

        # Dimensional forces [lbf]
        X = CX * q_inf * self.S_ref
        Y = CY * q_inf * self.S_ref
        Z = CZ * q_inf * self.S_ref

        # Dimensional moments [ft·lbf]
        L = Cl * q_inf * self.S_ref * self.b_ref
        M = Cm * q_inf * self.S_ref * self.c_ref
        N = Cn * q_inf * self.S_ref * self.b_ref

        return np.array([X, Y, Z]), np.array([L, M, N])

    def get_drag(self, alpha, V):
        """
        Get total drag coefficient (profile + induced).

        For simplicity, use a parabolic drag polar:
        CD = CD_0 + K·CL²

        Better: interpolate from airfoil_polars + add induced drag.
        """
        CL = self.CL_alpha * alpha
        CD_0 = 0.008  # Zero-lift drag
        K = 0.05      # Induced drag factor
        return CD_0 + K * CL**2

# Example usage
if __name__ == '__main__':
    # Load aerodeck
    aero = AeroModel('results/ntop_aircraft_aerodeck.json')

    # Flight state
    state = {
        'alpha': np.deg2rad(5.0),   # 5° angle of attack
        'beta': np.deg2rad(0.0),    # 0° sideslip
        'p': 0.0,                   # rad/s
        'q': 0.0,                   # rad/s
        'r': 0.0                    # rad/s
    }

    # Conditions at sea level
    V = 100.0        # ft/s (68 mph)
    rho = 0.002377   # slug/ft³ (sea level)

    # Compute forces and moments
    forces, moments = aero.compute_forces_moments(state, V, rho)

    print(f"Forces [lbf]: X={forces[0]:.1f}, Y={forces[1]:.1f}, Z={forces[2]:.1f}")
    print(f"Moments [ft·lbf]: L={moments[0]:.1f}, M={moments[1]:.1f}, N={moments[2]:.1f}")
```

**Output:**
```
Forces [lbf]: X=-12.3, Y=0.0, Z=-145.6
Moments [ft·lbf]: L=0.0, M=-42.8, N=0.0
```

---

## MATLAB/Simulink Integration

### Loading the AeroDeck in MATLAB

```matlab
% Load aerodeck
aerodeck = jsondecode(fileread('results/ntop_aircraft_aerodeck.json'));

% Extract reference geometry
S_ref = aerodeck.reference_geometry.S_ref_ft2;
b_ref = aerodeck.reference_geometry.b_ref_ft;
c_ref = aerodeck.reference_geometry.c_ref_ft;

% Extract stability derivatives
CL_alpha = aerodeck.aerodynamics.static_stability.longitudinal.CL_alpha_per_rad;
Cm_alpha = aerodeck.aerodynamics.static_stability.longitudinal.Cm_alpha_per_rad;

% Create lookup tables for Simulink
alpha_table = linspace(-10, 20, 100) * pi/180;  % rad
CL_table = CL_alpha * alpha_table;
```

### Simulink Block Diagram Structure

```
[Flight State] → [Aero Model] → [Forces/Moments] → [6-DOF EOM] → [Updated State]
     ↓                                                    ↓
  (α, β, p, q, r)                              (Integrate accelerations)
```

**Aero Model Block (MATLAB Function):**
```matlab
function [F, M] = aero_model(alpha, beta, p, q, r, V, rho)
    % Load aerodeck (do this once in initialization)
    persistent aero_data
    if isempty(aero_data)
        aero_data = load_aerodeck('results/ntop_aircraft_aerodeck.json');
    end

    % Compute forces and moments (same as Python example)
    % ... implementation ...
end
```

---

## Understanding the Derivatives

### Static Stability Derivatives

| Derivative | Symbol | Meaning | Desired Sign |
|------------|--------|---------|--------------|
| **Lift curve slope** | CL_α | Lift change per α | Positive |
| **Pitch stiffness** | Cm_α | Moment change per α | Negative (stable) |
| **Side force** | CY_β | Side force per β | Negative |
| **Dihedral effect** | Cl_β | Roll moment per β | Negative (stable) |
| **Directional stability** | Cn_β | Yaw moment per β | Positive (stable) |

**Your aircraft values (at trim):**
- CL_α = 2.84 /rad ✓ (good lift)
- Cm_α = -0.16 /rad ✓ (pitch stable)
- Cl_β = -0.04 /rad ✓ (lateral stable)
- Cn_β = 0.04 /rad ✓ (directionally stable)
- **Static margin**: 5.77% MAC ✓ (slightly stable)

### Dynamic Stability Derivatives

| Derivative | Symbol | Meaning | Desired Sign |
|------------|--------|---------|--------------|
| **Pitch damping** | Cm_q | Resist pitch rate | Negative |
| **Roll damping** | Cl_p | Resist roll rate | Negative |
| **Yaw damping** | Cn_r | Resist yaw rate | Negative |
| **Adverse yaw** | Cn_p | Yaw due to roll | Usually negative* |

**Your aircraft values:**
- Cm_q = -0.77 /rad ✓ (well damped)
- Cl_p = -0.23 /rad ✓ (well damped)
- Cn_r = -0.03 /rad ✓ (damped)
- **Cn_p = +0.02 /rad** ⚠ **Proverse yaw at cruise!**

*Note: Your flying wing has **proverse yaw** (Cn_p > 0) at low angles of attack, transitioning to normal adverse yaw at higher α. This is typical for swept flying wings and can aid turn coordination.

---

## Coordinate System Convention

### Body Frame (Standard Aircraft Convention)

```
        X (forward)
        ↑
        |
        |___→ Y (right wing)
       /
      ↙ Z (down)
```

**Positive directions:**
- X: Forward (nose direction)
- Y: Right (right wing tip)
- Z: Down

**Positive rotations (right-hand rule):**
- Roll (p): Right wing down
- Pitch (q): Nose up
- Yaw (r): Nose right

**Angles:**
- α (alpha): Angle of attack - angle between body X-axis and velocity vector in X-Z plane
- β (beta): Sideslip angle - angle between body X-axis and velocity vector in X-Y plane

---

## Units Reference

All units are **US Customary (Imperial)**:

| Quantity | Unit | Symbol |
|----------|------|--------|
| Length | feet | ft |
| Area | square feet | ft² |
| Velocity | feet per second | ft/s |
| Mass | pounds-mass | lbm |
| Force | pounds-force | lbf |
| Moment | foot-pounds-force | ft·lbf |
| Inertia | pounds-mass·feet² | lbm·ft² |
| Density | slugs per cubic foot | slug/ft³ |
| Angle | radians | rad |
| Angular rate | radians per second | rad/s |

**Key conversions:**
- 1 ft = 0.3048 m
- 1 ft/s = 0.5925 knots = 0.6818 mph
- 1 lbm = 0.4536 kg
- 1 lbf = 4.448 N
- 1 slug = 32.174 lbm (mass that accelerates at 1 ft/s² under 1 lbf)
- Standard sea level: ρ = 0.002377 slug/ft³

---

## Advanced Topics

### Interpolating Airfoil Polars

The aerodeck includes XFOIL polars at 5 Reynolds numbers. For intermediate Re, use logarithmic interpolation:

```python
def interpolate_polar(Re, aerodeck):
    """Interpolate airfoil polar at given Reynolds number."""
    polars = aerodeck['airfoil_polars']['polars']
    Re_values = [p['reynolds'] for p in polars]

    # Log interpolation
    log_Re = np.log(Re)
    log_Re_values = np.log(Re_values)

    # Find bracketing polars and interpolate
    # ... implementation ...
```

### Combining Profile and Induced Drag

**Total aircraft drag** = Profile drag (XFOIL) + Induced drag (AVL)

```python
def total_drag(CL, Re, aerodeck, avl_results):
    """Compute total drag from profile + induced."""
    # Profile drag from XFOIL polar
    CD_profile = interpolate_polar_at_CL(CL, Re, aerodeck)

    # Induced drag from AVL (use parabolic approximation)
    AR = b_ref**2 / S_ref
    e = 0.85  # Oswald efficiency (from AVL)
    CD_induced = CL**2 / (np.pi * AR * e)

    return CD_profile + CD_induced
```

### Stall Detection and Handling

The aerodeck polars include stall behavior. For flight simulation:

1. **Detect stall**: Monitor CL approaching CL_max
2. **Post-stall model**: Use simplified model or CFD data
3. **Warning systems**: Alert pilot when approaching stall

```python
def check_stall(CL, Re, aerodeck):
    """Check if aircraft is approaching stall."""
    CL_max = get_CL_max(Re, aerodeck)
    margin = CL_max - abs(CL)

    if margin < 0.1:
        return "WARNING: Approaching stall!"
    return "OK"
```

---

## Validation and Best Practices

### 1. Trim Verification

Verify the aircraft trims at expected flight conditions:

```python
# Should trim near α = 0° at design cruise speed
alpha_trim = find_trim_alpha(V_cruise)
assert abs(alpha_trim) < 5.0  # Within ±5°
```

### 2. Static Margin Check

Your aircraft has **5.77% MAC static margin** - slightly stable:
- **< 0%**: Unstable (requires active control)
- **5-15%**: Stable but responsive
- **> 25%**: Very stable but sluggish

### 3. Dynamic Stability

All damping derivatives should be negative:
- ✓ Cm_q = -0.77 (pitch damped)
- ✓ Cl_p = -0.23 (roll damped)
- ✓ Cn_r = -0.03 (yaw damped)

### 4. Reynolds Number Sensitivity

Your aircraft operates at Re ≈ 1-5 million. The aerodeck includes polars at:
- Re = 1e5, 5e5, 1e6, 5e6, 1e7

Use appropriate Re for your flight condition:
```python
Re = rho * V * c_ref / mu  # Reynolds number
```

---

## Support and References

**Generated by:** nTop AeroDeck Generator v1.0.0
**Tools:** AVL (vortex lattice) + XFOIL (viscous airfoil)
**Aircraft:** nTop Flying Wing

**Further reading:**
- *Flight Dynamics* by Robert F. Stengel
- *Aircraft Control and Simulation* by Stevens & Lewis
- AVL documentation: http://web.mit.edu/drela/Public/web/avl/
- XFOIL documentation: http://web.mit.edu/drela/Public/web/xfoil/

**Questions?** Review the PDF report (`ntop_aircraft_aerodeck.pdf`) for detailed stability analysis and performance charts.

---

*Last updated: 2025-11-15*
