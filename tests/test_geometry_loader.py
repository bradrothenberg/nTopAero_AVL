"""Tests for geometry loader."""

import pytest
import numpy as np
from pathlib import Path
import tempfile
import pandas as pd

from aerodeck.geometry.loader import GeometryLoader, MassProperties, PanelPoints


class TestMassProperties:
    """Test MassProperties dataclass."""

    def test_valid_mass_properties(self):
        """Test creating valid mass properties."""
        mass_props = MassProperties(
            mass=100.0,
            cg=np.array([1.0, 0.0, 0.0]),
            inertia=np.eye(3)
        )

        assert mass_props.mass == 100.0
        assert mass_props.cg.shape == (3,)
        assert mass_props.inertia.shape == (3, 3)

    def test_invalid_cg_shape(self):
        """Test that invalid CG shape raises error."""
        with pytest.raises(ValueError):
            MassProperties(
                mass=100.0,
                cg=np.array([1.0, 0.0]),  # Only 2 elements
                inertia=np.eye(3)
            )

    def test_invalid_inertia_shape(self):
        """Test that invalid inertia shape raises error."""
        with pytest.raises(ValueError):
            MassProperties(
                mass=100.0,
                cg=np.array([1.0, 0.0, 0.0]),
                inertia=np.eye(2)  # 2x2 instead of 3x3
            )


class TestPanelPoints:
    """Test PanelPoints dataclass."""

    def test_valid_panel_points(self):
        """Test creating valid panel points."""
        points = np.array([
            [0.0, 0.0, 0.0],
            [1.0, 1.0, 0.0],
            [2.0, 2.0, 0.0],
        ])

        panel = PanelPoints(points=points, label="Test Panel")

        assert panel.n_points == 3
        assert panel.label == "Test Panel"
        assert panel.points.shape == (3, 3)

    def test_get_bounds(self):
        """Test bounding box calculation."""
        points = np.array([
            [0.0, 0.0, 0.0],
            [1.0, 2.0, 3.0],
            [-1.0, -2.0, -3.0],
        ])

        panel = PanelPoints(points=points, label="Test")
        min_bounds, max_bounds = panel.get_bounds()

        np.testing.assert_array_equal(min_bounds, [-1.0, -2.0, -3.0])
        np.testing.assert_array_equal(max_bounds, [1.0, 2.0, 3.0])


class TestGeometryLoader:
    """Test GeometryLoader class."""

    @pytest.fixture
    def temp_geometry_dir(self):
        """Create temporary directory with sample CSV files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create mass.csv
            mass_df = pd.DataFrame({
                'mass': [100.0],
                'cg_x': [1.0],
                'cg_y': [0.0],
                'cg_z': [0.5],
                'Ixx': [10.0],
                'Iyy': [20.0],
                'Izz': [25.0],
                'Ixy': [0.0],
                'Ixz': [0.0],
                'Iyz': [0.0],
            })
            mass_df.to_csv(tmpdir / 'mass.csv', index=False)

            # Create LEpts.csv
            le_df = pd.DataFrame({
                'x': [0.0, 0.1, 0.2],
                'y': [0.0, 1.0, 2.0],
                'z': [0.0, 0.0, 0.0],
            })
            le_df.to_csv(tmpdir / 'LEpts.csv', index=False)

            # Create TEpts.csv
            te_df = pd.DataFrame({
                'x': [1.0, 1.1, 1.2],
                'y': [0.0, 1.0, 2.0],
                'z': [0.0, 0.0, 0.0],
            })
            te_df.to_csv(tmpdir / 'TEpts.csv', index=False)

            yield tmpdir

    def test_load_panel_data(self, temp_geometry_dir):
        """Test loading complete panel data."""
        loader = GeometryLoader(verbose=False)
        geometry = loader.load_panel_data(temp_geometry_dir)

        assert geometry.mass_properties.mass == 100.0
        assert geometry.leading_edge.n_points == 3
        assert geometry.trailing_edge.n_points == 3
        assert geometry.winglet is None
        assert geometry.elevon is None

    def test_load_missing_directory(self):
        """Test loading from non-existent directory."""
        loader = GeometryLoader(verbose=False)

        with pytest.raises(FileNotFoundError):
            loader.load_panel_data(Path("/nonexistent/path"))

    def test_load_missing_required_file(self, temp_geometry_dir):
        """Test loading with missing required file."""
        # Remove LEpts.csv
        (temp_geometry_dir / 'LEpts.csv').unlink()

        loader = GeometryLoader(verbose=False)

        with pytest.raises(FileNotFoundError):
            loader.load_panel_data(temp_geometry_dir)

    def test_load_mass_properties(self, temp_geometry_dir):
        """Test loading only mass properties."""
        loader = GeometryLoader(verbose=False)
        mass_props = loader.load_mass_properties(temp_geometry_dir / 'mass.csv')

        assert mass_props.mass == 100.0
        np.testing.assert_array_equal(mass_props.cg, [1.0, 0.0, 0.5])
        assert mass_props.inertia[0, 0] == 10.0
