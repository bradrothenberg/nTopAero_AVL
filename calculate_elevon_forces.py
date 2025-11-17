"""Calculate elevon forces and hinge moments at 10° deflection"""
import json
import numpy as np

# Load aerodeck
with open('results/group3-nqx-rev1_aerodeck.json', 'r') as f:
    aerodeck = json.load(f)

# Reference geometry
ref = aerodeck['reference_geometry']
S_ref_ft2 = ref['S_ref_ft2']
c_ref_ft = ref['c_ref_ft']
b_ref_ft = ref['b_ref_ft']

# Convert to inches
S_ref_in2 = S_ref_ft2 * 144
c_ref_in = c_ref_ft * 12
b_ref_in = b_ref_ft * 12

# Mass
mass_lbm = aerodeck['mass_properties']['mass_lbm']

# Flight condition - 150 mph
alpha = 0.0  # deg
delta_e = 10.0  # deg elevon deflection
V_mph = 150.0  # mph
V_fps = V_mph / 0.681818  # Convert to ft/s
M = V_fps / 1116.45  # Mach number
rho_slugft3 = 0.002377  # Sea level density (slug/ft³)
rho_lbmft3 = rho_slugft3 * 32.174  # Convert to lbm/ft³

# Dynamic pressure
q_lbft2 = 0.5 * rho_slugft3 * V_fps**2
q_lbin2 = q_lbft2 / 144  # Convert to lb/in²

# Force coefficients at alpha=0, delta_e=10 (from AVL FT output - UPDATED Nov 16, 2025)
# Using new geometry from updated CSV files
CL_total = 0.25452
CD_total = 0.00860
Cm_total = -0.10394

# Calculate total forces
L_total_lb = CL_total * q_lbft2 * S_ref_ft2
D_total_lb = CD_total * q_lbft2 * S_ref_ft2
M_total_lbft = Cm_total * q_lbft2 * S_ref_ft2 * c_ref_ft

# Convert moment to lb-in
M_total_lbin = M_total_lbft * 12

# Force per pound of aircraft weight
W_lb = mass_lbm  # Weight = mass in lbm (at 1g)
L_per_lb = L_total_lb / W_lb
D_per_lb = D_total_lb / W_lb

# Get control derivatives from comparing zero deflection to 10° deflection
# At alpha=0, delta_e=0: CL=0, Cm≈0
# At alpha=0, delta_e=10: CL=0.21455, Cm=-0.09644
# Therefore: CL_de ≈ 0.21455 / 10 = 0.02146 /deg
#            Cm_de ≈ -0.09644 / 10 = -0.00964 /deg

CL_de = CL_total / delta_e  # per degree
Cm_de = Cm_total / delta_e  # per degree

# Estimate hinge moment coefficient
# For a typical control surface: Ch_de ≈ -0.001 to -0.003 per degree
# We'll estimate based on geometry
# Elevon area from CSV: roughly 1/4 of wing area
elevon_area_factor = 0.25  # Approximate
Ch_de_estimate = -0.002  # Typical value for trailing edge control

Ch_at_10deg = Ch_de_estimate * delta_e

# Hinge moment
# H = Ch * q * S * c
# For control surface, use control surface reference
S_elevon_ft2 = S_ref_ft2 * elevon_area_factor
c_elevon_ft = 0.718  # From elevon geometry analysis (avg chord)

H_lbft = Ch_at_10deg * q_lbft2 * S_elevon_ft2 * c_elevon_ft
H_lbin = H_lbft * 12

# Alternative: Estimate from pitching moment
# The elevon creates a pitching moment, which requires a hinge moment
# Hinge moment arm is approximately the elevon chord
moment_arm_ft = 7.0  # Approximate distance from CG to elevon hinge line (avg)
elevon_normal_force_lb = abs(M_total_lbft) / moment_arm_ft
hinge_moment_est_lbft = elevon_normal_force_lb * c_elevon_ft * 0.25  # ~25% chord for hinge moment arm
hinge_moment_est_lbin = hinge_moment_est_lbft * 12

print("="*70)
print("ELEVON FORCES & HINGE MOMENTS AT 10° DEFLECTION")
print("="*70)

print("\nFLIGHT CONDITION:")
print(f"  Alpha:          {alpha:.1f} deg")
print(f"  Elevon:         {delta_e:.1f} deg")
print(f"  Mach:           {M:.2f}")
print(f"  Velocity:       {V_fps:.1f} ft/s ({V_fps * 0.681818:.1f} mph)")
print(f"  Dynamic Press:  {q_lbft2:.3f} lb/ft² ({q_lbin2:.4f} lb/in²)")
print(f"  Density:        {rho_lbmft3:.4f} lbm/ft³ (sea level)")

print("\nREFERENCE GEOMETRY:")
print(f"  Wing area:      {S_ref_ft2:.2f} ft² ({S_ref_in2:.1f} in²)")
print(f"  Wing span:      {b_ref_ft:.2f} ft ({b_ref_in:.1f} in)")
print(f"  Mean chord:     {c_ref_ft:.2f} ft ({c_ref_in:.1f} in)")
print(f"  Aircraft mass:  {mass_lbm:.2f} lbm ({mass_lbm:.2f} lb at 1g)")

print("\nFORCE COEFFICIENTS (From AVL):")
print(f"  CL:             {CL_total:.5f}")
print(f"  CD:             {CD_total:.5f}")
print(f"  Cm:             {Cm_total:.5f}")

print("\nTOTAL FORCES:")
print(f"  Lift:           {L_total_lb:.2f} lb")
print(f"  Drag:           {D_total_lb:.2f} lb")
print(f"  Pitch moment:   {M_total_lbft:.2f} lb-ft ({M_total_lbin:.0f} lb-in)")

print("\nFORCE PER POUND OF AIRCRAFT:")
print(f"  Lift/Weight:    {L_per_lb:.4f} lb/lb ({L_per_lb*100:.2f}%)")
print(f"  Drag/Weight:    {D_per_lb:.4f} lb/lb ({D_per_lb*100:.2f}%)")

print("\nCONTROL DERIVATIVES:")
print(f"  CL_de:          {CL_de:.5f} /deg ({CL_de*57.3:.3f} /rad)")
print(f"  Cm_de:          {Cm_de:.5f} /deg ({Cm_de*57.3:.3f} /rad)")

print("\nELEVON LOADING:")
print(f"  Elevon area:    ~{S_elevon_ft2:.2f} ft² ({S_elevon_ft2*144:.1f} in²) [estimated]")
print(f"  Elevon chord:   {c_elevon_ft:.3f} ft ({c_elevon_ft*12:.2f} in) [from geometry]")
print(f"  Normal force:   ~{elevon_normal_force_lb:.1f} lb [estimated from pitching moment]")
print(f"  Hinge moment:   ~{hinge_moment_est_lbft:.1f} lb-ft (~{hinge_moment_est_lbin:.0f} lb-in) [estimated]")

print("\nNOTES:")
print(f"  - Forces calculated at sea level, {V_mph:.1f} mph (M={M:.3f})")
print("  - Hinge moment estimated from pitching moment and geometry")
print("  - For accurate hinge moments, AVL HM command required")
print("  - Elevon area approximated as 25% of total wing area")

print("="*70)

# Return data for report
data_for_report = {
    'q_lbin2': q_lbin2,
    'CL': CL_total,
    'CD': CD_total,
    'Cm': Cm_total,
    'L_lb': L_total_lb,
    'D_lb': D_total_lb,
    'M_lbin': M_total_lbin,
    'L_per_lb': L_per_lb,
    'D_per_lb': D_per_lb,
    'CL_de': CL_de,
    'Cm_de': Cm_de,
    'H_lbin': hinge_moment_est_lbin,
    'V_mph': V_fps * 0.681818
}

# Save for report generator
with open('elevon_forces_data.json', 'w') as f:
    json.dump(data_for_report, f, indent=2)

print("\n[OK] Data saved to elevon_forces_data.json for report")
