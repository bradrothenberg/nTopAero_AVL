"""Tests for AVL translator."""

import pytest
import numpy as np
from pathlib import Path
import tempfile

from aerodeck.geometry.avl_translator import AVLGeometryWriter, ReferenceGeometry
from aerodeck.geometry.loader import GeometryData, MassProperties, PanelPoints


class TestAVLGeometryWriter:
    """Test AVL geometry writer."""

    @pytest.fixture
    def sample_geometry(self):
        """Create sample geometry for testing."""
        mass_props = MassProperties(
            mass=100.0,
            cg=np.array([1.0, 0.0, 0.5]),
            inertia=np.eye(3) * 10.0
        )

        le_points = PanelPoints(
            points=np.array([
                [0.0, 0.0, 0.0],
                [0.1, 1.0, 0.0],
                [0.2, 2.0, 0.0],
            ]),
            label="Leading Edge"
        )

        te_points = PanelPoints(
            points=np.array([
                [1.0, 0.0, 0.0],
                [0.9, 1.0, 0.0],
                [0.8, 2.0, 0.0],
            ]),
            label="Trailing Edge"
        )

        return GeometryData(
            mass_properties=mass_props,
            leading_edge=le_points,
            trailing_edge=te_points
        )

    def test_compute_reference_geometry(self, sample_geometry):
        """Test reference geometry computation."""
        writer = AVLGeometryWriter(verbose=False)
        ref_geom = writer._compute_reference_geometry(sample_geometry)

        assert ref_geom.area > 0
        assert ref_geom.span > 0
        assert ref_geom.chord > 0
        assert len(ref_geom.cg) == 3

    def test_compute_span(self, sample_geometry):
        """Test span computation."""
        writer = AVLGeometryWriter(verbose=False)
        le_points = sample_geometry.leading_edge.points

        span = writer._compute_span(le_points)

        # Span should be 2.0 * 2 = 4.0 (doubled for full span)
        assert span == pytest.approx(4.0)

    def test_compute_mac(self, sample_geometry):
        """Test MAC computation."""
        writer = AVLGeometryWriter(verbose=False)
        le_points = sample_geometry.leading_edge.points
        te_points = sample_geometry.trailing_edge.points

        mac = writer._compute_mac(le_points, te_points)

        assert mac > 0
        # Should be around 0.9-1.0 for this geometry
        assert 0.5 < mac < 1.5

    def test_write_avl_input(self, sample_geometry):
        """Test writing complete AVL file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.avl', delete=False) as f:
            output_path = Path(f.name)

        try:
            writer = AVLGeometryWriter(verbose=False)
            ref_geom = writer.write_avl_input(
                sample_geometry,
                output_path,
                "Test Aircraft"
            )

            # Check file was created
            assert output_path.exists()

            # Check file contents
            content = output_path.read_text()
            assert "Test Aircraft" in content
            assert "SURFACE" in content
            assert "SECTION" in content

            # Check reference geometry is valid
            assert ref_geom.area > 0
            assert ref_geom.span > 0
            assert ref_geom.chord > 0

        finally:
            if output_path.exists():
                output_path.unlink()

    def test_create_surface_definition(self, sample_geometry):
        """Test creating surface definition string."""
        writer = AVLGeometryWriter(verbose=False)

        le_points = sample_geometry.leading_edge.points
        te_points = sample_geometry.trailing_edge.points

        surface_def = writer.create_surface_definition(
            le_points,
            te_points,
            "Test Wing"
        )

        assert "SURFACE" in surface_def
        assert "Test Wing" in surface_def
        assert "SECTION" in surface_def
