# Sample Data Directory

This directory contains sample nTop geometry export files for testing the aerodeck generator.

## Files

- `mass.csv` - Mass properties (mass, CG, inertia tensor)
- `LEpts.csv` - Leading edge panel points (x, y, z)
- `TEpts.csv` - Trailing edge panel points (x, y, z)
- `WINGLETpts.csv` - Winglet geometry points
- `ELEVONpts.csv` - Control surface hinge line points
- `NACA 64-208.dat` - Airfoil coordinate file

## Usage

Run the aerodeck generator with this sample data:

```bash
aerodeck generate data -v
```

This will generate aerodynamic analysis results in the `results/` directory.
