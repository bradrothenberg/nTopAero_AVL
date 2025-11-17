"""Planform visualization with updated geometry - Nov 16, 2025"""
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

# ============================================================================
# LOAD GEOMETRY FROM CSV FILES
# ============================================================================
elevon_pts = np.loadtxt('data/ELEVONpts.csv', delimiter=',', skiprows=1) / 12.0  # Convert to feet
le_pts = np.loadtxt('data/LEpts.csv', delimiter=',', skiprows=1) / 12.0
te_pts = np.loadtxt('data/TEpts.csv', delimiter=',', skiprows=1) / 12.0

# Elevon LE sweep line
elevon_root_le = elevon_pts[0, :]  # [x, y, z]
elevon_tip_le = elevon_pts[1, :]

print(f"Elevon LE: Root ({elevon_root_le[0]:.3f}, {elevon_root_le[1]:.3f}) to Tip ({elevon_tip_le[0]:.3f}, {elevon_tip_le[1]:.3f})")

# ============================================================================
# AVL WING GEOMETRY (from updated AVL file)
# ============================================================================
wing_sections = [
    # Section 0: Root
    {'idx': 0, 'le': [-0.405357, 0.000000, 0.000000], 'chord': 7.563660},
    # Section 1
    {'idx': 1, 'le': [0.068550, 0.665753, 0.034891], 'chord': 7.554064},
    # Section 2
    {'idx': 2, 'le': [1.074856, 1.331506, 0.069781], 'chord': 5.846987},
    # Section 3: Has elevon control (hinge at 0.8502)
    {'idx': 3, 'le': [1.989388, 1.997259, 0.104672], 'chord': 4.416955, 'hinge_frac': 0.8502},
    # Section 4: Has elevon control (hinge at 0.5144)
    {'idx': 4, 'le': [6.050890, 5.742120, 0.300932], 'chord': 1.354260, 'hinge_frac': 0.5144},
    # Section 5: Has elevon control (hinge at 0.5000)
    {'idx': 5, 'le': [6.313973, 5.991777, 0.314016], 'chord': 1.158072, 'hinge_frac': 0.5000}
]

# Calculate hinge positions
hinge_positions = []
for sec in wing_sections:
    if 'hinge_frac' in sec:
        hinge_x = sec['le'][0] + sec['chord'] * sec['hinge_frac']
        hinge_y = sec['le'][1]
        hinge_positions.append({'idx': sec['idx'], 'x': hinge_x, 'y': hinge_y, 'frac': sec['hinge_frac']})
        print(f"Section {sec['idx']}: Y={hinge_y:.3f} ft, Hinge X={hinge_x:.3f} ft ({sec['hinge_frac']*100:.1f}% chord)")

# ============================================================================
# PLOTTING
# ============================================================================
fig, ax = plt.subplots(figsize=(16, 10))

# --- WING PLANFORM (Blue outline with light fill) ---
for i in range(len(wing_sections)-1):
    sec = wing_sections[i]
    sec_next = wing_sections[i+1]

    # LE line
    ax.plot([sec['le'][0], sec_next['le'][0]],
            [sec['le'][1], sec_next['le'][1]],
            'b-', linewidth=2.5, label='Wing LE' if i == 0 else '', zorder=3)

    # TE line
    te_x = sec['le'][0] + sec['chord']
    te_x_next = sec_next['le'][0] + sec_next['chord']
    ax.plot([te_x, te_x_next],
            [sec['le'][1], sec_next['le'][1]],
            'b--', linewidth=2.5, label='Wing TE' if i == 0 else '', zorder=3)

    # Fill wing section
    wing_poly = np.array([
        [sec['le'][0], sec['le'][1]],
        [te_x, sec['le'][1]],
        [te_x_next, sec_next['le'][1]],
        [sec_next['le'][0], sec_next['le'][1]]
    ])
    poly_patch = patches.Polygon(wing_poly, closed=True, facecolor='lightblue',
                                edgecolor='none', alpha=0.3, zorder=1)
    ax.add_patch(poly_patch)

# Last section chord
last_sec = wing_sections[-1]
last_te_x = last_sec['le'][0] + last_sec['chord']

# --- ELEVON DESIGN AREA (Red polygon with pattern) ---
elevon_poly = patches.Polygon(
    elevon_pts[:, :2],  # x, y coordinates
    closed=True,
    edgecolor='red',
    facecolor='red',
    alpha=0.25,
    linewidth=3,
    linestyle='-',
    label='Elevon Surface Area',
    zorder=2
)
ax.add_patch(elevon_poly)

# --- ELEVON LEADING EDGE LINE (Magenta dashed - reference) ---
ax.plot([elevon_root_le[0], elevon_tip_le[0]],
        [elevon_root_le[1], elevon_tip_le[1]],
        'm--', linewidth=2.5, marker='s', markersize=8,
        label='Elevon LE (Design)', zorder=4)

# --- ACTUAL HINGE LINE (Orange solid - from AVL) ---
hinge_x_coords = [h['x'] for h in hinge_positions]
hinge_y_coords = [h['y'] for h in hinge_positions]
ax.plot(hinge_x_coords, hinge_y_coords,
        'o-', color='darkorange', linewidth=4, marker='o', markersize=10,
        label='Actual Hinge Line (AVL)', zorder=5)

# --- CONTROL SURFACE BARS (showing hinge to TE) ---
colors = ['forestgreen', 'limegreen', 'yellowgreen']
ctrl_idx = 0
for sec in wing_sections:
    if 'hinge_frac' in sec:
        hinge_x = sec['le'][0] + sec['chord'] * sec['hinge_frac']
        te_x = sec['le'][0] + sec['chord']
        y = sec['le'][1]

        # Thick bar from hinge to TE
        ax.plot([hinge_x, te_x], [y, y],
                color=colors[ctrl_idx], linewidth=8, solid_capstyle='round',
                label=f'Control Surface (Sec {sec["idx"]})', zorder=3)
        ctrl_idx += 1

        # Hinge point marker
        ax.plot([hinge_x], [y], 'o', color='darkorange', markersize=12,
                markeredgecolor='black', markeredgewidth=1.5, zorder=6)

# --- SECTION MARKERS ---
for sec in wing_sections:
    ax.plot(sec['le'][0], sec['le'][1], 'ko', markersize=7, zorder=6)

    # Section labels
    offset_x = -0.4 if sec['idx'] < 3 else -0.5
    ax.text(sec['le'][0] + offset_x, sec['le'][1], f'Sec {sec["idx"]}',
            ha='right', va='center', fontsize=10, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))

# --- HINGE POSITION ANNOTATIONS ---
for h in hinge_positions:
    y_offset = 0.35 if h['idx'] % 2 == 1 else -0.45
    va = 'bottom' if h['idx'] % 2 == 1 else 'top'

    ax.text(h['x'], h['y'] + y_offset,
            f"Sec {h['idx']}\nX = {h['x']:.3f} ft\n{h['frac']*100:.1f}% chord",
            ha='center', va=va, fontsize=9, color='darkorange', fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.95,
                     edgecolor='darkorange', linewidth=2))

# --- ELEVON LE ENDPOINTS ---
ax.plot([elevon_root_le[0]], [elevon_root_le[1]], 'ms', markersize=12,
        markeredgecolor='black', markeredgewidth=1, zorder=6)
ax.plot([elevon_tip_le[0]], [elevon_tip_le[1]], 'ms', markersize=12,
        markeredgecolor='black', markeredgewidth=1, zorder=6)

ax.text(elevon_root_le[0] - 0.5, elevon_root_le[1],
        f'Elevon Root LE\nX = {elevon_root_le[0]:.3f} ft',
        ha='right', va='center', fontsize=9, color='magenta', fontweight='bold',
        bbox=dict(boxstyle='round', facecolor='white', alpha=0.9, edgecolor='magenta'))

ax.text(elevon_tip_le[0] + 0.4, elevon_tip_le[1],
        f'Elevon Tip LE\nX = {elevon_tip_le[0]:.3f} ft',
        ha='left', va='center', fontsize=9, color='magenta', fontweight='bold',
        bbox=dict(boxstyle='round', facecolor='white', alpha=0.9, edgecolor='magenta'))

# ============================================================================
# FORMATTING
# ============================================================================
ax.set_xlabel('X - Streamwise (ft)', fontsize=13, fontweight='bold')
ax.set_ylabel('Y - Spanwise (ft)', fontsize=13, fontweight='bold')
ax.set_title('Aircraft Planform - Updated Geometry (Nov 16, 2025)\nElevon Control Surfaces with Interpolated Hinge Line',
             fontsize=15, fontweight='bold', pad=20)
ax.legend(loc='upper left', fontsize=10, framealpha=0.95)
ax.grid(True, alpha=0.3, linestyle='--')
ax.set_aspect('equal')
ax.set_xlim(-1.5, 8.5)
ax.set_ylim(-0.5, 7)

# Add info box
info_text = f"""UPDATED GEOMETRY:
• Wing area: 48.06 ft²
• Mass: 430.99 lbm
• Elevon span: {elevon_tip_le[1] - elevon_root_le[1]:.2f} ft
• Hinge interpolation: Linear along elevon LE
• Control sections: 3, 4, 5
• CG X: 41.65 in (3.47 ft)"""

ax.text(0.02, 0.98, info_text,
        transform=ax.transAxes,
        ha='left', va='top', fontsize=9,
        bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.9,
                 edgecolor='black', linewidth=1.5),
        family='monospace')

plt.tight_layout()
plt.savefig('results/planform_updated_nov16.png', dpi=200, bbox_inches='tight')
print("\n[OK] Saved: results/planform_updated_nov16.png")
plt.close()

print("\n" + "="*70)
print("PLANFORM VISUALIZATION COMPLETE")
print("="*70)
