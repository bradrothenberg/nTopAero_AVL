"""Verify the new panel geometry"""
import numpy as np

# LE points (6 sections now)
le_pts = np.array([
    [-4.6365757698597401, 0, 0],
    [1.2510702292252047, 7.9890362780365889, 0.41868764994355062],
    [13.890491197825773, 15.978072556073178, 0.83737529988710124],
    [25.606717529642076, 23.967108834109769, 1.2560629498306519],
    [77.882870938055007, 68.9054378980656, 3.6111809807631245],
    [81.269094396392035, 71.901326502329326, 3.7681888494919571]
])

# TE points
te_pts = np.array([
    [93.999672441213818, 0, 0],
    [98.969521105063848, 7.9890362780365889, 0.41868764994355062],
    [89.939545053905334, 15.978072556073178, 0.83737529988710124],
    [83.271462213743277, 23.967108834109769, 1.2560629498306519],
    [95.253992233174586, 68.9054378980656, 3.6111809807631245],
    [96.056736118695724, 71.901326502329326, 3.7681888494919571]
])

# Elevon points (quadrilateral)
elevon_pts = np.array([
    [74.634315734662763, 23.999999999999996, 0],    # Root LE
    [86.691982171483332, 69, 0],                     # Tip LE
    [95.279367716654633, 69, 0],                     # Tip TE
    [83.278921673670524, 23.999999999999996, 0]     # Root TE
])

# Convert to feet
le_pts_ft = le_pts / 12.0
te_pts_ft = te_pts / 12.0
elevon_pts_ft = elevon_pts / 12.0

print("="*70)
print("NEW WING GEOMETRY")
print("="*70)

print("\nWING SECTIONS (6 total):")
for i in range(len(le_pts_ft)):
    le = le_pts_ft[i]
    te = te_pts_ft[i]
    chord = np.linalg.norm(te[:2] - le[:2])  # Chord in XY plane
    print(f"  Section {i}: Y={le[1]:.3f} ft")
    print(f"    LE: X={le[0]:.3f} ft, Z={le[2]:.3f} ft")
    print(f"    TE: X={te[0]:.3f} ft, Z={te[2]:.3f} ft")
    print(f"    Chord: {chord:.3f} ft")

print("\nELEVON PANEL:")
elevon_y_min = elevon_pts_ft[:, 1].min()
elevon_y_max = elevon_pts_ft[:, 1].max()
elevon_x_le_avg = (elevon_pts_ft[0, 0] + elevon_pts_ft[1, 0]) / 2.0
elevon_x_te_avg = (elevon_pts_ft[2, 0] + elevon_pts_ft[3, 0]) / 2.0

print(f"  Spanwise range: Y = {elevon_y_min:.3f} to {elevon_y_max:.3f} ft")
print(f"  LE X (avg): {elevon_x_le_avg:.3f} ft")
print(f"  TE X (avg): {elevon_x_te_avg:.3f} ft")
print(f"  Chord (avg): {elevon_x_te_avg - elevon_x_le_avg:.3f} ft")

print("\nWHICH SECTIONS OVERLAP WITH ELEVON?")
for i in range(len(le_pts_ft)):
    y = le_pts_ft[i, 1]
    if elevon_y_min - 0.5 <= y <= elevon_y_max + 0.5:
        print(f"  Section {i} at Y={y:.3f} ft: OVERLAPS (should have control)")

print("="*70)
