"""Calculate Reynolds number at 20,000 ft altitude"""

# Standard atmosphere at 20,000 ft
rho_20k = 0.001267  # slug/ft³ (vs 0.002377 at sea level)
T_20k = 447.42  # °R (vs 518.67°R at sea level)
mu_20k = 3.324e-7  # slug/(ft·s) (dynamic viscosity)

# Aircraft parameters
c_ref = 5.75  # ft (MAC)
V_mph = 200  # mph
V_fps = V_mph / 0.681818  # Convert to ft/s

print(f"Altitude: 20,000 ft")
print(f"Temperature: {T_20k:.2f} °R ({T_20k - 459.67:.2f} °F)")
print(f"Density: {rho_20k:.6f} slug/ft³ ({rho_20k/0.002377*100:.1f}% of sea level)")
print(f"Dynamic viscosity: {mu_20k:.3e} slug/(ft·s)")
print(f"\nFlight speed: {V_mph} mph = {V_fps:.1f} ft/s")
print(f"Reference chord: {c_ref} ft")

# Reynolds number
Re_20k = rho_20k * V_fps * c_ref / mu_20k

print(f"\nReynolds number at 20,000 ft: {Re_20k:.3e}")
print(f"Reynolds number at sea level: {0.002377 * V_fps * c_ref / (3.737e-7):.3e}")

print(f"\nCurrent Re values in code: [1e5, 5e5, 1e6, 5e6, 1e7]")
print(f"Recommended Re for 20k ft @ 200 mph: {Re_20k:.1e}")

# For range of speeds
print(f"\nReynolds numbers at 20,000 ft for different speeds:")
for mph in [100, 150, 200, 250]:
    fps = mph / 0.681818
    Re = rho_20k * fps * c_ref / mu_20k
    print(f"  {mph:3d} mph ({fps:5.1f} ft/s): Re = {Re:.2e}")
