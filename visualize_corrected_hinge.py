"""Visualize the CORRECTED hinge line following elevon LE sweep"""
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

# ============================================================================
# ELEVON DESIGN GEOMETRY (from ELEVONpts.csv)
# ============================================================================
elevon_pts = np.array([
    [74.634315734662763, 23.999999999999996, 0],    # Root LE
    [86.691982171483332, 69, 0],                     # Tip LE
    [95.279367716654633, 69, 0],                     # Tip TE
    [83.278921673670524, 23.999999999999996, 0]     # Root TE
])

# Convert from inches to feet
elevon_pts_ft = elevon_pts / 12.0
elevon_x = elevon_pts_ft[:, 0]
elevon_y = elevon_pts_ft[:, 1]

# Elevon LE sweep line
elevon_root_le_x = elevon_x[0]  # 6.220 ft
elevon_root_y = elevon_y[0]      # 2.000 ft
elevon_tip_le_x = elevon_x[1]    # 7.224 ft
elevon_tip_y = elevon_y[1]       # 5.750 ft

# ============================================================================
# AVL WING GEOMETRY (6 sections - from new geometry)
# ============================================================================
wing_sections = [
    # Section 0: Root
    {'le': [-0.386381, 0.000000, 0.000000], 'chord': 8.219687, 'y': 0.000000},
    # Section 1:
    {'le': [0.104256, 0.665753, 0.034891], 'chord': 8.143204, 'y': 0.665753},
    # Section 2:
    {'le': [1.157541, 1.331506, 0.069781], 'chord': 6.337421, 'y': 1.331506},
    # Section 3: Has control (hinge at 0.8502)
    {'le': [2.133893, 1.997259, 0.104672], 'chord': 4.805395, 'y': 1.997259, 'hinge_frac': 0.8502},
    # Section 4: Has control (hinge at 0.5057)
    {'le': [6.490239, 5.742120, 0.300932], 'chord': 1.447593, 'y': 5.742120, 'hinge_frac': 0.5057},
    # Section 5: Has control (hinge at 0.5000)
    {'le': [6.772425, 5.991777, 0.314016], 'chord': 1.232303, 'y': 5.991777, 'hinge_frac': 0.5000}
]

# Calculate actual hinge positions
hinge_positions = []
for sec in wing_sections:
    if 'hinge_frac' in sec:
        hinge_x = sec['le'][0] + sec['chord'] * sec['hinge_frac']
        hinge_positions.append({'x': hinge_x, 'y': sec['y']})

# ============================================================================
# PLOTTING
# ============================================================================
fig, ax = plt.subplots(figsize=(14, 8))

# --- WING PLANFORM (Blue) ---
for i in range(len(wing_sections)-1):
    sec = wing_sections[i]
    sec_next = wing_sections[i+1]

    # LE line
    ax.plot([sec['le'][0], sec_next['le'][0]],
            [sec['y'], sec_next['y']],
            'b-', linewidth=2, label='Wing LE' if i == 0 else '')

    # TE line
    te_x = sec['le'][0] + sec['chord']
    te_x_next = sec_next['le'][0] + sec_next['chord']
    ax.plot([te_x, te_x_next],
            [sec['y'], sec_next['y']],
            'b--', linewidth=2, label='Wing TE' if i == 0 else '')

    # Chord lines at each section
    ax.plot([sec['le'][0], te_x], [sec['y'], sec['y']], 'b-', linewidth=0.5, alpha=0.3)

# Last section chord
last_sec = wing_sections[-1]
last_te_x = last_sec['le'][0] + last_sec['chord']
ax.plot([last_sec['le'][0], last_te_x], [last_sec['y'], last_sec['y']], 'b-', linewidth=0.5, alpha=0.3)

# --- ELEVON DESIGN (Red polygon) ---
elevon_poly = patches.Polygon(
    np.column_stack([elevon_x, elevon_y]),
    closed=True,
    edgecolor='red',
    facecolor='red',
    alpha=0.2,
    linewidth=2,
    label='Elevon Design (ELEVONpts.csv)'
)
ax.add_patch(elevon_poly)

# --- ELEVON LEADING EDGE LINE (Magenta dashed) ---
ax.plot([elevon_root_le_x, elevon_tip_le_x],
        [elevon_root_y, elevon_tip_y],
        'm--', linewidth=2, marker='s', markersize=6,
        label='Elevon LE (Hinge Line)')

# --- AVL CONTROL SURFACES (Show hinge bars) ---
colors = ['green', 'lime', 'yellow']
for i, sec in enumerate(wing_sections[3:]):  # Sections 3, 4, 5
    if 'hinge_frac' in sec:
        hinge_x = sec['le'][0] + sec['chord'] * sec['hinge_frac']
        te_x = sec['le'][0] + sec['chord']

        # Control surface (from hinge to TE)
        control = patches.Rectangle(
            (hinge_x, sec['y'] - 0.05),
            te_x - hinge_x,
            0.1,
            linewidth=2,
            edgecolor=colors[i],
            facecolor=colors[i],
            alpha=0.5,
            label=f'AVL Control (Section {i+3})'
        )
        ax.add_patch(control)

# --- ACTUAL HINGE LINE (Orange solid) ---
hinge_x_coords = [h['x'] for h in hinge_positions]
hinge_y_coords = [h['y'] for h in hinge_positions]
ax.plot(hinge_x_coords, hinge_y_coords,
        'orange', linewidth=3, marker='o', markersize=8,
        label='Actual Hinge Line (Interpolated)', zorder=5)

# --- ANNOTATIONS ---
# Elevon span annotation
elevon_y_min = elevon_y.min()
elevon_y_max = elevon_y.max()

# Section markers
for i, sec in enumerate(wing_sections):
    ax.plot(sec['le'][0], sec['y'], 'ko', markersize=6, zorder=6)
    ax.text(sec['le'][0] - 0.3, sec['y'], f'Sec {i}', ha='right', va='center', fontsize=9)

# Hinge position annotations
for i, h in enumerate(hinge_positions):
    sec_idx = i + 3
    sec = wing_sections[sec_idx]
    hinge_frac_pct = sec['hinge_frac'] * 100

    y_offset = 0.3 if i % 2 == 0 else -0.4
    va = 'bottom' if i % 2 == 0 else 'top'

    ax.text(h['x'], h['y'] + y_offset,
            f"Sec {sec_idx}\nX={h['x']:.3f} ft\n{hinge_frac_pct:.1f}% chord",
            ha='center', va=va, fontsize=8, color='orange', fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.9, edgecolor='orange'))

# Elevon LE endpoints
ax.plot([elevon_root_le_x], [elevon_root_y], 'ms', markersize=10, zorder=6)
ax.plot([elevon_tip_le_x], [elevon_tip_y], 'ms', markersize=10, zorder=6)

ax.text(elevon_root_le_x - 0.4, elevon_root_y,
        f'Elevon Root LE\nX={elevon_root_le_x:.3f} ft',
        ha='right', va='center', fontsize=8, color='magenta',
        bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

ax.text(elevon_tip_le_x + 0.3, elevon_tip_y,
        f'Elevon Tip LE\nX={elevon_tip_le_x:.3f} ft',
        ha='left', va='center', fontsize=8, color='magenta',
        bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

# ============================================================================
# FORMATTING
# ============================================================================
ax.set_xlabel('X (ft)', fontsize=12, fontweight='bold')
ax.set_ylabel('Y - Spanwise (ft)', fontsize=12, fontweight='bold')
ax.set_title('CORRECTED Hinge Line: Interpolated Along Elevon LE Sweep',
             fontsize=14, fontweight='bold')
ax.legend(loc='upper left', fontsize=9)
ax.grid(True, alpha=0.3)
ax.set_aspect('equal')
ax.set_xlim(-1, 9)
ax.set_ylim(-0.5, 7)

# Add status box
status_text = """CORRECTED HINGE LINE:
- Section 3: 85.0% chord (X=6.219 ft)
- Section 4: 50.6% chord (X=7.222 ft)
- Section 5: 50.0% chord (X=7.389 ft)
- Hinge follows elevon LE sweep!
- Section 3 moved FORWARD 6 inches"""

ax.text(0.02, 0.98, status_text,
        transform=ax.transAxes,
        ha='left', va='top', fontsize=9,
        bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.8),
        family='monospace')

plt.tight_layout()
plt.savefig('results/elevon_planform_CORRECTED.png', dpi=150, bbox_inches='tight')
print("[OK] Saved: results/elevon_planform_CORRECTED.png")

# ============================================================================
# TEXT SUMMARY
# ============================================================================
print("\n" + "="*70)
print("CORRECTED HINGE LINE VISUALIZATION")
print("="*70)

print("\nELEVON LE SWEEP:")
print(f"  Root: X={elevon_root_le_x:.3f} ft at Y={elevon_root_y:.3f} ft")
print(f"  Tip:  X={elevon_tip_le_x:.3f} ft at Y={elevon_tip_y:.3f} ft")
print(f"  Sweep: {elevon_tip_le_x - elevon_root_le_x:.3f} ft over {elevon_tip_y - elevon_root_y:.3f} ft span")

print("\nHINGE POSITIONS (Following Elevon LE):")
for i, h in enumerate(hinge_positions):
    sec_idx = i + 3
    sec = wing_sections[sec_idx]
    print(f"  Section {sec_idx}: X={h['x']:.3f} ft ({sec['hinge_frac']*100:.1f}% chord)")

print("\nKEY IMPROVEMENT:")
print("  - Hinge line now follows the swept elevon leading edge")
print("  - Section 3 hinge moved FORWARD from 6.722 to 6.219 ft (6 inches!)")
print("  - Interpolation ensures accurate hinge position at each section")

print("="*70)
