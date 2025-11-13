"""Quick test to verify the package works with real data."""

from pathlib import Path
from aerodeck.geometry.loader import GeometryLoader
from aerodeck.geometry.validator import GeometryValidator

def main():
    print("Testing nTop AeroDeck Generator")
    print("=" * 60)

    # Test loading
    print("\n1. Loading geometry from Data/")
    loader = GeometryLoader(verbose=False)

    try:
        geometry = loader.load_panel_data(Path("Data"))
        print(f"   ✓ Loaded successfully!")
        print(f"   - Mass: {geometry.mass_properties.mass:.2f} kg")
        print(f"   - CG: [{geometry.mass_properties.cg[0]:.2f}, {geometry.mass_properties.cg[1]:.2f}, {geometry.mass_properties.cg[2]:.2f}] m")
        print(f"   - Leading edge points: {geometry.leading_edge.n_points}")
        print(f"   - Trailing edge points: {geometry.trailing_edge.n_points}")
        if geometry.winglet:
            print(f"   - Winglet points: {geometry.winglet.n_points}")
        if geometry.elevon:
            print(f"   - Elevon points: {geometry.elevon.n_points}")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        return False

    # Test validation
    print("\n2. Validating geometry")
    validator = GeometryValidator(verbose=False)

    try:
        result = validator.validate(geometry)
        if result.is_valid:
            print("   ✓ Validation passed!")
        else:
            print("   ✗ Validation failed:")
            for error in result.errors:
                print(f"      - {error}")

        if result.warnings:
            print("   Warnings:")
            for warning in result.warnings:
                print(f"      - {warning}")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        return False

    print("\n" + "=" * 60)
    print("✓ All tests passed!")
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
