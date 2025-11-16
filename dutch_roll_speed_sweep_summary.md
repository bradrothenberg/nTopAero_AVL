# Dutch Roll Speed Sweep Analysis Summary

## Report Location
**File:** [results/ntop_aircraft_aerodeck.pdf](results/ntop_aircraft_aerodeck.pdf) - Page 6

## Speed Range Analyzed
- **Minimum:** 50 ft/s (34 mph)
- **Maximum:** 350 ft/s (238 mph)
- **Current analysis speed:** 200 mph (293.3 ft/s) - marked with black dot

## What the Speed Sweep Shows

### Plot 1: Damping Ratio (ζ) vs Speed
- **Red curve = UNSTABLE** (ζ < 0)
- **Green curve = STABLE** (ζ > 0)
- **Horizontal reference lines:**
  - Black dashed at ζ = 0 (stability boundary)
  - Orange dotted at ζ = 0.04 (MIL-F-8785C Category C)
  - Blue dotted at ζ = 0.08 (MIL-F-8785C Category B)
  - Purple dotted at ζ = 0.19 (MIL-F-8785C Category A)

**Key Finding:** The entire speed range shows NEGATIVE damping ratio (unstable Dutch roll). However, the damping ratio approaches zero (less unstable) as speed increases.

### Plot 2: Dutch Roll Frequency vs Speed
Shows how fast the oscillation occurs:
- **At 50 mph:** ~0.07 Hz (period ~14 seconds) - slow oscillation
- **At 200 mph:** ~0.17 Hz (period ~6 seconds) - faster oscillation
- **At 238 mph:** ~0.20 Hz (period ~5 seconds) - fastest

**Interpretation:** Higher speeds = faster oscillations = pilot needs to respond more quickly

### Plot 3: Oscillation Period vs Speed
The time for one complete yaw-roll-yaw cycle:
- **Decreases with speed** (inverse of frequency)
- At current speed (200 mph): **6.0 seconds per oscillation**

### Plot 4: Time to Half/Double Amplitude
Most critical plot for safety:
- **Red curve:** Time for oscillation to DOUBLE in amplitude (unstable region)
- **Green curve:** Time for oscillation to HALF in amplitude (stable region - not present)

**Key Findings:**
- At **50 mph:** Doubles in ~2 seconds ⚠️ DANGEROUS
- At **100 mph:** Doubles in ~4.3 seconds ⚠️ CONCERNING
- At **200 mph:** Doubles in ~12.9 seconds ⚠️ MANAGEABLE
- At **238 mph:** Doubles in ~18 seconds ⚠️ BORDERLINE OK

## Practical Implications

### Low Speed Flight (< 100 mph)
❌ **Not Recommended Without SAS**
- Oscillations grow too quickly (doubles in < 5 seconds)
- Pilot cannot maintain control for extended periods
- High workload, imprecise control

### Medium Speed Flight (100-150 mph)
⚠️ **Marginal - Requires Skilled Pilot**
- Oscillations double in 5-10 seconds
- Experienced pilot can manually damp with rudder
- Tiring for extended flight

### High Speed Flight (> 200 mph)
✓ **Acceptable with Caution**
- Oscillations double in > 12 seconds
- Manageable for skilled pilot
- Simple yaw damper would fully stabilize
- Suitable for test flights and experienced RC pilots

## Design Recommendations

### Option 1: Flight Envelope Restriction (No Modifications)
- **Minimum speed:** 180 mph
- **Cruise speed:** 200+ mph
- **Requires:** Experienced pilot, active yaw control
- **Risk:** Medium

### Option 2: Add Electronic Yaw Damper (Recommended)
- **Simple implementation:** Gyro + rudder/elevon feedback
- **Gains required:** Moderate (yaw rate → rudder deflection)
- **Result:** Fully stable across all speeds
- **Cost:** Low (RC gyro ~$50-100)
- **Risk:** Low

### Option 3: Increase Winglet Size/Effectiveness
- **Required improvement:** +40-50% effective area
- **Methods:**
  - Increase physical size
  - Increase cant angle (more vertical component)
  - Add small vertical fins at wing tips
- **Result:** Passive stability across speed range
- **Cost:** Medium (redesign + rebuild)
- **Risk:** Low

### Option 4: Combination (Best)
- Modest winglet improvement (+20-30%)
- Simple yaw damper
- **Result:** Excellent stability with redundancy
- **Cost:** Medium
- **Risk:** Very Low

## Stability Derivatives Analysis

The root cause of the instability can be traced to:

### Weathercock Stability (Cn_β)
- **Current:** 0.0399 /rad
- **Status:** Decent for a flying wing
- **Assessment:** ✓ Acceptable

### Yaw Damping (Cn_r)
- **Current:** -0.0296 /rad
- **Status:** Too weak for the oscillation frequency
- **Assessment:** ✗ INSUFFICIENT

### Dihedral Effect (Cl_β)
- **Current:** -0.0408 /rad
- **Status:** Good, provides stable roll response
- **Assessment:** ✓ Good

**Conclusion:** The issue is INSUFFICIENT YAW DAMPING (Cn_r), not lack of weathercock stability. This is typical for flying wings with small winglets.

## Speed-Dependent Physics

Why does higher speed help?

1. **Dynamic pressure increases with V²**
   - More aerodynamic force available for damping
   - Yaw damping term Cn_r becomes more effective

2. **Non-dimensional rate decreases with V**
   - r̂ = r·b/(2V)
   - Same physical yaw rate produces smaller non-dimensional rate
   - Easier for aerodynamics to control

3. **Inertial effects decrease relative to aero forces**
   - Izz doesn't change, but q·S·b increases
   - Aero moments dominate over inertia at high speed

## MIL-F-8785C Compliance

**Current aircraft meets:**
- ❌ Category A (fighters): Requires ζ ≥ 0.19
- ❌ Category B (medium): Requires ζ ≥ 0.08
- ❌ Category C (large/heavy): Requires ζ ≥ 0.04
- ❌ **No category requirements met** at any speed

**To meet Category C** (minimum):
- Need to shift curve upward by ~0.09 in damping ratio
- Requires ~3x improvement in effective yaw damping
- Achievable with winglet modifications OR simple SAS

## Next Steps

1. **Immediate (for testing):**
   - Restrict flight to > 180 mph
   - Experienced pilot only
   - Clear weather, no turbulence

2. **Short term (recommended):**
   - Implement basic yaw damper
   - Test incrementally from high to low speed
   - Document handling qualities

3. **Long term (if passive stability desired):**
   - Analyze winglet modifications using AVL
   - Test modified design
   - Validate with flight test

## References

- MIL-F-8785C: Military Specification - Flying Qualities of Piloted Airplanes
- Nelson, R. C. (1998). Flight Stability and Automatic Control
- Roskam, J. (1995). Airplane Flight Dynamics and Automatic Flight Controls

---

*Generated: 2025-11-15*
*Analysis speed range: 34-238 mph (50-350 ft/s)*
*Aircraft: nTop Flying Wing (S=52.07 ft², b=11.98 ft, m=523.7 lbm)*
