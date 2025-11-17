"""Display neutral point and static margin information"""
import json

# Load aerodeck
with open('results/group3-nqx-rev1_aerodeck.json', 'r') as f:
    aerodeck = json.load(f)

# Get values
aero = aerodeck['aerodynamics']
static_stab = aero['static_stability']
long_stab = static_stab['longitudinal']

mass = aerodeck['mass_properties']
ref_geom = aerodeck['reference_geometry']

# Neutral point (in feet)
neutral_point_ft = long_stab['neutral_point_x_ft']
neutral_point_in = neutral_point_ft * 12

# CG (in feet)
cg_x_ft = mass['cg_ft'][0]
cg_x_in = cg_x_ft * 12

# MAC (in feet)
c_ref_ft = ref_geom['c_ref_ft']
c_ref_in = c_ref_ft * 12

# Static margin: (NP - CG) / MAC
static_margin_ft = (neutral_point_ft - cg_x_ft) / c_ref_ft
static_margin_pct = static_margin_ft * 100

# Determine stability
if static_margin_pct > 5:
    stability = "Stable"
elif static_margin_pct > 0:
    stability = "Marginally Stable"
else:
    stability = "Unstable"

print("="*70)
print("NEUTRAL POINT & STATIC MARGIN")
print("="*70)

print("\nLONGITUDINAL STABILITY:")
print(f"  Neutral Point X:  {neutral_point_in:.2f} in  ({neutral_point_ft:.3f} ft)")
print(f"  CG X:             {cg_x_in:.2f} in  ({cg_x_ft:.3f} ft)")
print(f"  Mean Chord (MAC): {c_ref_in:.2f} in  ({c_ref_ft:.3f} ft)")

print(f"\n  Static Margin:    {static_margin_pct:.1f}%")
print(f"  Status:           {stability}")

print("\nINTERPRETATION:")
if static_margin_pct > 5:
    print("  [OK] Aircraft is statically stable in pitch")
    print(f"  [OK] Neutral point is {neutral_point_in - cg_x_in:.2f} in aft of CG")
elif static_margin_pct > 0:
    print("  [WARNING] Aircraft is marginally stable")
    print(f"  [WARNING] Small margin: {neutral_point_in - cg_x_in:.2f} in")
else:
    print("  [CRITICAL] Aircraft is statically unstable!")
    print(f"  [CRITICAL] CG is aft of neutral point by {cg_x_in - neutral_point_in:.2f} in")

print("\nREPORT UPDATES:")
print("  [OK] Removed CG Y and CG Z from mass properties table")
print("  [OK] Added 'Neutral Point & Static Margin' table")
print("  [OK] Table includes:")
print("      - Neutral Point X (in)")
print("      - CG X (in)")
print("      - Static Margin (%)")
print("      - MAC (in)")
print("      - Stability Status (color coded)")

print("="*70)
