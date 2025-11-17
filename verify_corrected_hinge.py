"""Verify the CORRECTED hinge line positions"""
import numpy as np

# Elevon geometry from CSV (in inches, convert to feet)
elevon_pts = np.array([
    [74.634315734662763, 23.999999999999996, 0],    # Root LE
    [86.691982171483332, 69, 0],                     # Tip LE
    [95.279367716654633, 69, 0],                     # Tip TE
    [83.278921673670524, 23.999999999999996, 0]     # Root TE
]) / 12.0

# Wing sections from AVL file
wing_sections = [
    {'idx': 3, 'le_x': 2.133893, 'y': 1.997259, 'chord': 4.805395, 'hinge_frac': 0.8502},
    {'idx': 4, 'le_x': 6.490239, 'y': 5.742120, 'chord': 1.447593, 'hinge_frac': 0.5057},
    {'idx': 5, 'le_x': 6.772425, 'y': 5.991777, 'chord': 1.232303, 'hinge_frac': 0.5000}
]

# Elevon LE sweep line
elevon_root_le_x = elevon_pts[0, 0]  # 6.220 ft
elevon_root_y = elevon_pts[0, 1]      # 2.000 ft
elevon_tip_le_x = elevon_pts[1, 0]    # 7.224 ft
elevon_tip_y = elevon_pts[1, 1]       # 5.750 ft

print("="*70)
print("CORRECTED HINGE LINE VERIFICATION")
print("="*70)

print("\nELEVON LEADING EDGE SWEEP:")
print(f"  Root LE: X={elevon_root_le_x:.3f} ft at Y={elevon_root_y:.3f} ft")
print(f"  Tip LE:  X={elevon_tip_le_x:.3f} ft at Y={elevon_tip_y:.3f} ft")
print(f"  Sweep:   {elevon_tip_le_x - elevon_root_le_x:.3f} ft over {elevon_tip_y - elevon_root_y:.3f} ft span")

print("\nHINGE POSITIONS (Interpolated along Elevon LE):")
for sec in wing_sections:
    # Calculate expected hinge X from interpolation
    y_frac = (sec['y'] - elevon_root_y) / (elevon_tip_y - elevon_root_y)
    y_frac = max(0.0, min(1.0, y_frac))
    expected_hinge_x = elevon_root_le_x + (elevon_tip_le_x - elevon_root_le_x) * y_frac

    # Calculate actual hinge X from AVL file
    actual_hinge_x = sec['le_x'] + sec['chord'] * sec['hinge_frac']

    # Error
    error = actual_hinge_x - expected_hinge_x

    print(f"\n  Section {sec['idx']} (Y={sec['y']:.3f} ft):")
    print(f"    Wing LE:         X={sec['le_x']:.3f} ft")
    print(f"    Wing chord:      {sec['chord']:.3f} ft")
    print(f"    Hinge fraction:  {sec['hinge_frac']:.4f} ({sec['hinge_frac']*100:.2f}%)")
    print(f"    Actual hinge X:  {actual_hinge_x:.3f} ft")
    print(f"    Expected (interpolated): {expected_hinge_x:.3f} ft")
    print(f"    Error:           {error:.4f} ft ({abs(error)*12:.2f} in)")

    if abs(error) < 0.01:
        print(f"    Status:          [OK] Matches elevon LE")
    else:
        print(f"    Status:          [WARNING] Off by {abs(error)*12:.2f} in")

print("\n" + "="*70)
print("COMPARISON: OLD vs NEW")
print("="*70)

old_hinges = [
    {'sec': 3, 'frac': 0.9548, 'method': 'Averaged LE (X=6.722 ft)'},
    {'sec': 4, 'frac': 0.5000, 'method': 'Averaged LE (X=6.722 ft)'},
    {'sec': 5, 'frac': 0.5000, 'method': 'Averaged LE (X=6.722 ft)'}
]

print("\n                OLD (Averaged)         NEW (Interpolated)")
print("                ------------------     -------------------")
for i, sec in enumerate(wing_sections):
    old = old_hinges[i]
    old_hinge_x = sec['le_x'] + sec['chord'] * old['frac']
    new_hinge_x = sec['le_x'] + sec['chord'] * sec['hinge_frac']
    delta = new_hinge_x - old_hinge_x

    print(f"Section {sec['idx']}:      {old['frac']:.4f} = X={old_hinge_x:.3f}  ->  {sec['hinge_frac']:.4f} = X={new_hinge_x:.3f}  (Delta={delta:+.3f} ft)")

print("\nIMPROVEMENT:")
print("  - Section 3: Hinge moved FORWARD by ~0.5 ft (6 inches)")
print("  - Section 4: Hinge slightly adjusted")
print("  - Section 5: Hinge at clamped 50% (near tip)")
print("  - Hinge now follows the actual elevon LE sweep!")

print("="*70)
