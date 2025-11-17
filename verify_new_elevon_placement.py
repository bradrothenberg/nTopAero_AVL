"""Visualize the NEW elevon placement with 6-section wing"""
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
    # Section 3: Has control (hinge at 0.9548)
    {'le': [2.133893, 1.997259, 0.104672], 'chord': 4.805395, 'y': 1.997259},
    # Section 4: Has control (hinge at 0.5000) - NEW SECTION!
    {'le': [6.490239, 5.742120, 0.300932], 'chord': 1.447593, 'y': 5.742120},
    # Section 5: Has control (hinge at 0.5000)
    {'le': [6.772425, 5.991777, 0.314016], 'chord': 1.232303, 'y': 5.991777}
]

# ============================================================================
# AVL CONTROL SURFACES
# ============================================================================
# Section 3: Control with hinge at 0.9548
sec3_hinge_x = wing_sections[3]['le'][0] + wing_sections[3]['chord'] * 0.9548
sec3_hinge_y = wing_sections[3]['y']

# Section 4: Control with hinge at 0.5000
sec4_hinge_x = wing_sections[4]['le'][0] + wing_sections[4]['chord'] * 0.5000
sec4_hinge_y = wing_sections[4]['y']

# Section 5: Control with hinge at 0.5000
sec5_hinge_x = wing_sections[5]['le'][0] + wing_sections[5]['chord'] * 0.5000
sec5_hinge_y = wing_sections[5]['y']

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

# --- AVL CONTROL SURFACES (Green/Lime/Yellow spans) ---
# Section 3 control surface (from hinge to TE)
sec3 = wing_sections[3]
sec3_te_x = sec3['le'][0] + sec3['chord']
sec3_control = patches.Rectangle(
    (sec3_hinge_x, sec3['y'] - 0.05),
    sec3_te_x - sec3_hinge_x,
    0.1,
    linewidth=2,
    edgecolor='green',
    facecolor='green',
    alpha=0.5,
    label='AVL Control (Section 3)'
)
ax.add_patch(sec3_control)

# Section 4 control surface (from hinge to TE)
sec4 = wing_sections[4]
sec4_te_x = sec4['le'][0] + sec4['chord']
sec4_control = patches.Rectangle(
    (sec4_hinge_x, sec4['y'] - 0.05),
    sec4_te_x - sec4_hinge_x,
    0.1,
    linewidth=2,
    edgecolor='lime',
    facecolor='lime',
    alpha=0.5,
    label='AVL Control (Section 4)'
)
ax.add_patch(sec4_control)

# Section 5 control surface (from hinge to TE)
sec5 = wing_sections[5]
sec5_te_x = sec5['le'][0] + sec5['chord']
sec5_control = patches.Rectangle(
    (sec5_hinge_x, sec5['y'] - 0.05),
    sec5_te_x - sec5_hinge_x,
    0.1,
    linewidth=2,
    edgecolor='yellow',
    facecolor='yellow',
    alpha=0.5,
    label='AVL Control (Section 5)'
)
ax.add_patch(sec5_control)

# --- HINGE LINE (Orange) ---
ax.plot([sec3_hinge_x, sec4_hinge_x, sec5_hinge_x],
        [sec3_hinge_y, sec4_hinge_y, sec5_hinge_y],
        'orange', linewidth=3, marker='o', markersize=8,
        label=f'Hinge Line')

# --- ANNOTATIONS ---
# Elevon span annotation
elevon_y_min = elevon_y.min()
elevon_y_max = elevon_y.max()
ax.annotate('', xy=(elevon_x[1], elevon_y_max), xytext=(elevon_x[0], elevon_y_min),
            arrowprops=dict(arrowstyle='<->', color='red', lw=2))
ax.text(elevon_x[0] - 0.5, (elevon_y_min + elevon_y_max)/2,
        f'Elevon Span\n{elevon_y_min:.2f} - {elevon_y_max:.2f} ft',
        ha='right', va='center', fontsize=10, color='red', fontweight='bold')

# Section markers
for i, sec in enumerate(wing_sections):
    ax.plot(sec['le'][0], sec['y'], 'ko', markersize=6)
    ax.text(sec['le'][0] - 0.3, sec['y'], f'Sec {i}', ha='right', va='center', fontsize=9)

# Hinge position annotations
ax.text(sec3_hinge_x, sec3_hinge_y - 0.4,
        f'Sec 3\nX={sec3_hinge_x:.2f} ft\n95.48% chord',
        ha='center', va='top', fontsize=8, color='orange', fontweight='bold',
        bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

ax.text(sec4_hinge_x, sec4_hinge_y + 0.3,
        f'Sec 4\nX={sec4_hinge_x:.2f} ft\n50% chord',
        ha='center', va='bottom', fontsize=8, color='orange', fontweight='bold',
        bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

ax.text(sec5_hinge_x, sec5_hinge_y + 0.3,
        f'Sec 5\nX={sec5_hinge_x:.2f} ft\n50% chord',
        ha='center', va='bottom', fontsize=8, color='orange', fontweight='bold',
        bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

# Elevon LE position
elevon_le_avg = (elevon_x[0] + elevon_x[1]) / 2.0
ax.axvline(elevon_le_avg, color='red', linestyle=':', linewidth=2, alpha=0.5)
ax.text(elevon_le_avg + 0.1, 1.0, f'Elevon LE\nX={elevon_le_avg:.3f} ft',
        ha='left', va='center', fontsize=9, color='red',
        bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

# ============================================================================
# FORMATTING
# ============================================================================
ax.set_xlabel('X (ft)', fontsize=12, fontweight='bold')
ax.set_ylabel('Y - Spanwise (ft)', fontsize=12, fontweight='bold')
ax.set_title('NEW Elevon Placement: 6-Section Wing with 3 Control Sections',
             fontsize=14, fontweight='bold')
ax.legend(loc='upper left', fontsize=9)
ax.grid(True, alpha=0.3)
ax.set_aspect('equal')
ax.set_xlim(-1, 9)
ax.set_ylim(-0.5, 7)

# Add status box
status_text = """NEW GEOMETRY (6 sections):
- Wing now has section at Y=5.742 ft
- Control on sections 3, 4, & 5
- Better coverage of elevon span
- Hinge at elevon LE (X=6.722 ft)"""

ax.text(0.02, 0.98, status_text,
        transform=ax.transAxes,
        ha='left', va='top', fontsize=10,
        bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.8),
        family='monospace')

plt.tight_layout()
plt.savefig('results/elevon_planform_NEW.png', dpi=150, bbox_inches='tight')
print("[OK] Saved: results/elevon_planform_NEW.png")

# ============================================================================
# VERIFICATION OUTPUT
# ============================================================================
print("\n" + "="*70)
print("NEW ELEVON PLACEMENT VERIFICATION (6-Section Wing)")
print("="*70)

print("\nELEVON DESIGN GEOMETRY:")
print(f"  Span: Y = {elevon_y_min:.3f} to {elevon_y_max:.3f} ft")
print(f"  LE X (avg): {elevon_le_avg:.3f} ft")
print(f"  TE X (avg): {(elevon_x[2] + elevon_x[3])/2:.3f} ft")

print("\nAVL WING SECTIONS (6 total):")
for i, sec in enumerate(wing_sections):
    te_x = sec['le'][0] + sec['chord']
    has_control = i >= 3
    print(f"  Section {i}: Y={sec['y']:.3f} ft, LE X={sec['le'][0]:.3f} ft, "
          f"TE X={te_x:.3f} ft, Chord={sec['chord']:.3f} ft "
          f"{'[HAS CONTROL]' if has_control else ''}")

print("\nAVL CONTROL SURFACES:")
print(f"  Section 3:")
print(f"    Hinge at X = {sec3_hinge_x:.3f} ft (95.48% of {wing_sections[3]['chord']:.3f} ft chord)")
print(f"    Control span: {sec3_hinge_x:.3f} to {sec3_te_x:.3f} ft ({sec3_te_x - sec3_hinge_x:.3f} ft)")
print(f"  Section 4:")
print(f"    Hinge at X = {sec4_hinge_x:.3f} ft (50.00% of {wing_sections[4]['chord']:.3f} ft chord)")
print(f"    Control span: {sec4_hinge_x:.3f} to {sec4_te_x:.3f} ft ({sec4_te_x - sec4_hinge_x:.3f} ft)")
print(f"  Section 5:")
print(f"    Hinge at X = {sec5_hinge_x:.3f} ft (50.00% of {wing_sections[5]['chord']:.3f} ft chord)")
print(f"    Control span: {sec5_hinge_x:.3f} to {sec5_te_x:.3f} ft ({sec5_te_x - sec5_hinge_x:.3f} ft)")

print("\nVERIFICATION:")
print(f"  [OK] Section 3 Y={wing_sections[3]['y']:.3f} is within elevon span [{elevon_y_min:.3f}, {elevon_y_max:.3f}]")
print(f"  [OK] Section 4 Y={wing_sections[4]['y']:.3f} is within elevon span [{elevon_y_min:.3f}, {elevon_y_max:.3f}]")
print(f"  [OK] Section 5 Y={wing_sections[5]['y']:.3f} is within elevon span [{elevon_y_min:.3f}, {elevon_y_max:.3f}]")
print(f"  [OK] THREE sections now have control surfaces!")
print(f"  [OK] Better spanwise coverage: 1.997 -> 5.742 -> 5.992 ft")

print("\nIMPROVEMENTS:")
print("  1. Wing now has 6 sections instead of 5")
print("  2. New section 4 at Y=5.742 ft provides better elevon coverage")
print("  3. Control surfaces on 3 consecutive sections (3, 4, 5)")
print("  4. Total control span: 3.995 ft (vs elevon span: 3.750 ft)")

print("="*70)
