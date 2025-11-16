"""Quick check of Dutch roll stability at 200 mph"""
import numpy as np
import json

# Load aerodeck
with open('results/ntop_aircraft_aerodeck.json', 'r') as f:
    aerodeck = json.load(f)

# Extract derivatives
ref_geom = aerodeck['reference_geometry']
S_ref = ref_geom['S_ref_ft2']
b_ref = ref_geom['b_ref_ft']
c_ref = ref_geom['c_ref_ft']

mass_props = aerodeck['mass_properties']
m = mass_props['mass_lbm'] / 32.174  # Convert to slugs
Ixx = mass_props['inertia_lbm_ft2']['Ixx'] / 32.174
Iyy = mass_props['inertia_lbm_ft2']['Iyy'] / 32.174
Izz = mass_props['inertia_lbm_ft2']['Izz'] / 32.174
Ixz = mass_props['inertia_lbm_ft2']['Ixz'] / 32.174

static = aerodeck['aerodynamics']['static_stability']['lateral_directional']
CY_beta = static['CY_beta_per_rad']
Cl_beta = static['Cl_beta_per_rad']
Cn_beta = static['Cn_beta_per_rad']

dynamic = aerodeck['aerodynamics']['dynamic_stability']
CY_p = dynamic['roll_rate']['CY_p_per_rad']
Cl_p = dynamic['roll_rate']['Cl_p_per_rad']
Cn_p = dynamic['roll_rate']['Cn_p_per_rad']
CY_r = dynamic['yaw_rate']['CY_r_per_rad']
Cl_r = dynamic['yaw_rate']['Cl_r_per_rad']
Cn_r = dynamic['yaw_rate']['Cn_r_per_rad']

# Flight condition
V = 293.3  # ft/s (200 mph)
rho = 0.002377  # slug/ft³
q_bar = 0.5 * rho * V**2

print(f"\n{'='*60}")
print(f"Dutch Roll Analysis at 200 mph (V = {V:.1f} ft/s)")
print(f"{'='*60}")

# Dimensional derivatives
Y_beta = (q_bar * S_ref / m) * CY_beta
L_beta = (q_bar * S_ref * b_ref / Ixx) * Cl_beta
N_beta = (q_bar * S_ref * b_ref / Izz) * Cn_beta

Y_p = (q_bar * S_ref * b_ref / (2 * m * V)) * CY_p
L_p = (q_bar * S_ref * b_ref**2 / (2 * Ixx * V)) * Cl_p
N_p = (q_bar * S_ref * b_ref**2 / (2 * Izz * V)) * Cn_p

Y_r = (q_bar * S_ref * b_ref / (2 * m * V)) * CY_r
L_r = (q_bar * S_ref * b_ref**2 / (2 * Ixx * V)) * Cl_r
N_r = (q_bar * S_ref * b_ref**2 / (2 * Izz * V)) * Cn_r

# Build lateral state matrix [beta, p, r, phi]
A_lat = np.array([
    [Y_beta/V, 0, -1, 32.174/V],  # beta_dot
    [L_beta, L_p, L_r, 0],         # p_dot
    [N_beta, N_p, N_r, 0],         # r_dot
    [0, 1, 0, 0]                   # phi_dot
])

print(f"\nLateral State Matrix A:")
print(A_lat)

# Compute eigenvalues
eigenvalues = np.linalg.eigvals(A_lat)
print(f"\nEigenvalues:")
for i, eig in enumerate(eigenvalues):
    print(f"  {i+1}: {eig:.6f}")

# Find Dutch roll mode (complex pair with highest frequency)
complex_modes = [(eig, i) for i, eig in enumerate(eigenvalues) if abs(eig.imag) > 0.01]
if complex_modes:
    dutch_roll_eig = max(complex_modes, key=lambda x: abs(x[0].imag))[0]

    real_part = dutch_roll_eig.real
    imag_part = abs(dutch_roll_eig.imag)
    omega_n = abs(dutch_roll_eig)
    zeta = -real_part / omega_n if omega_n > 0 else 0
    period = 2 * np.pi / imag_part if imag_part > 0 else float('inf')

    print(f"\n{'='*60}")
    print(f"Dutch Roll Mode:")
    print(f"{'='*60}")
    print(f"  Eigenvalue: {dutch_roll_eig:.4f}")
    print(f"  Real part: {real_part:.6f} (damping)")
    print(f"  Imaginary part: ±{imag_part:.6f} rad/s")
    print(f"  Natural frequency (ωn): {omega_n:.3f} rad/s ({omega_n/(2*np.pi):.3f} Hz)")
    print(f"  Damping ratio (ζ): {zeta:.3f}")
    print(f"  Period: {period:.2f} seconds")

    if real_part < 0:
        t_half = abs(0.693 / real_part)
        print(f"  Time to half amplitude: {t_half:.2f} seconds")
        print(f"\n  Status: ✓ STABLE (damping is positive)")
    else:
        t_double = 0.693 / real_part
        print(f"  Time to double amplitude: {t_double:.2f} seconds")
        print(f"\n  Status: ✗ UNSTABLE (damping is negative)")

    # MIL-F-8785C requirements
    print(f"\n{'='*60}")
    print(f"MIL-F-8785C Requirements:")
    print(f"{'='*60}")
    print(f"  Category A (fighters): ζ ≥ 0.19")
    print(f"  Category B (medium): ζ ≥ 0.08")
    print(f"  Category C (large/heavy): ζ ≥ 0.04")

    if zeta >= 0.19:
        print(f"  Result: ✓ Meets Cat A requirements")
    elif zeta >= 0.08:
        print(f"  Result: ✓ Meets Cat B requirements")
    elif zeta >= 0.04:
        print(f"  Result: ✓ Meets Cat C requirements")
    else:
        print(f"  Result: ✗ Does NOT meet any category")

print(f"\n{'='*60}\n")
