"""Translate nTop geometry to AVL input format."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, TextIO
import numpy as np

from .loader import GeometryData, PanelPoints
from ..utils.logger import get_logger
from ..utils.config import ReferenceConfig


@dataclass
class ReferenceGeometry:
    """Reference geometry values for aerodynamic analysis."""

    area: float  # Reference area [m²]
    span: float  # Reference span [m]
    chord: float  # Mean aerodynamic chord [m]
    cg: np.ndarray  # Center of gravity [x, y, z] m


class AVLGeometryWriter:
    """Convert nTop geometry to AVL input format."""

    def __init__(
        self,
        ref_config: Optional[ReferenceConfig] = None,
        verbose: bool = True
    ) -> None:
        """
        Initialize the AVL translator.

        Args:
            ref_config: Reference geometry configuration
            verbose: Enable verbose logging
        """
        self.ref_config = ref_config or ReferenceConfig()
        self.logger = get_logger(verbose=verbose)

    def write_avl_input(
        self,
        geometry: GeometryData,
        output_path: Path,
        aircraft_name: str = "nTop Aircraft"
    ) -> ReferenceGeometry:
        """
        Write complete AVL input file.

        Args:
            geometry: Geometry data to convert
            output_path: Path to output AVL file
            aircraft_name: Name of aircraft

        Returns:
            ReferenceGeometry with computed reference values
        """
        self.logger.info("Generating AVL input file...")
        self.logger.indent()

        # Compute reference geometry
        ref_geom = self._compute_reference_geometry(geometry)

        self.logger.debug(f"S_ref = {ref_geom.area:.3f} m²")
        self.logger.debug(f"b_ref = {ref_geom.span:.3f} m")
        self.logger.debug(f"c_ref = {ref_geom.chord:.3f} m (MAC)")

        # Write AVL file
        with open(output_path, 'w') as f:
            self._write_header(f, aircraft_name, ref_geom)
            self._write_main_wing(f, geometry, ref_geom)

            if geometry.winglet:
                self._write_winglet(f, geometry)

        self.logger.success(f"AVL input written: {output_path.name}")
        self.logger.dedent()

        return ref_geom

    def _compute_reference_geometry(
        self,
        geometry: GeometryData
    ) -> ReferenceGeometry:
        """
        Compute reference geometry values.

        Args:
            geometry: Geometry data

        Returns:
            ReferenceGeometry with computed values
        """
        le_pts = geometry.leading_edge.points
        te_pts = geometry.trailing_edge.points

        # Use config values if provided, otherwise compute
        if self.ref_config.area is not None:
            area = self.ref_config.area
        else:
            area = self._compute_planform_area(le_pts, te_pts)

        if self.ref_config.span is not None:
            span = self.ref_config.span
        else:
            span = self._compute_span(le_pts)

        if self.ref_config.chord is not None:
            chord = self.ref_config.chord
        else:
            chord = self._compute_mac(le_pts, te_pts)

        cg = geometry.mass_properties.cg

        return ReferenceGeometry(area=area, span=span, chord=chord, cg=cg)

    def _compute_planform_area(
        self,
        le_pts: np.ndarray,
        te_pts: np.ndarray
    ) -> float:
        """
        Compute planform area using trapezoidal rule.

        Args:
            le_pts: Leading edge points
            te_pts: Trailing edge points

        Returns:
            Planform area [m²]
        """
        # Calculate local chords
        chords = np.linalg.norm(te_pts - le_pts, axis=1)

        # Get spanwise coordinates (Y)
        y_coords = le_pts[:, 1]

        # Sort by spanwise position
        sort_idx = np.argsort(y_coords)
        y_sorted = y_coords[sort_idx]
        chords_sorted = chords[sort_idx]

        # Integrate using trapezoidal rule
        area = 0.0
        for i in range(len(y_sorted) - 1):
            dy = y_sorted[i + 1] - y_sorted[i]
            avg_chord = (chords_sorted[i] + chords_sorted[i + 1]) / 2
            area += avg_chord * dy

        # Multiply by 2 for both sides (if half-span model)
        # Check if model is symmetric by looking at Y coordinates
        if np.min(y_coords) >= -0.01:  # Assuming origin at root
            area *= 2

        return abs(area)

    def _compute_span(self, le_pts: np.ndarray) -> float:
        """
        Compute wingspan.

        Args:
            le_pts: Leading edge points

        Returns:
            Wingspan [m]
        """
        y_coords = le_pts[:, 1]
        span = np.max(y_coords) - np.min(y_coords)

        # Double if half-span model
        if np.min(y_coords) >= -0.01:
            span *= 2

        return abs(span)

    def _compute_mac(
        self,
        le_pts: np.ndarray,
        te_pts: np.ndarray
    ) -> float:
        """
        Compute mean aerodynamic chord.

        Args:
            le_pts: Leading edge points
            te_pts: Trailing edge points

        Returns:
            Mean aerodynamic chord [m]
        """
        # Calculate local chords
        chords = np.linalg.norm(te_pts - le_pts, axis=1)

        # Simple mean for now (could be refined with proper MAC calculation)
        return np.mean(chords)

    def _write_header(
        self,
        f: TextIO,
        aircraft_name: str,
        ref_geom: ReferenceGeometry
    ) -> None:
        """Write AVL file header."""
        f.write(f"{aircraft_name}\n")
        f.write("#" + "=" * 70 + "\n")
        f.write("# AVL input file generated from nTop geometry export\n")
        f.write("#" + "=" * 70 + "\n\n")

        # Mach number
        f.write("#Mach\n")
        f.write("0.0\n\n")

        # Reference values
        f.write("#IYsym   IZsym   Zsym\n")
        f.write("0       0       0.0\n\n")

        f.write("#Sref    Cref    Bref\n")
        f.write(f"{ref_geom.area:.6f}  {ref_geom.chord:.6f}  {ref_geom.span:.6f}\n\n")

        f.write("#Xref    Yref    Zref\n")
        f.write(f"{ref_geom.cg[0]:.6f}  {ref_geom.cg[1]:.6f}  {ref_geom.cg[2]:.6f}\n\n")

    def _write_main_wing(
        self,
        f: TextIO,
        geometry: GeometryData,
        ref_geom: ReferenceGeometry
    ) -> None:
        """Write main wing surface definition."""
        f.write("#" + "-" * 70 + "\n")
        f.write("SURFACE\n")
        f.write("Main Wing\n\n")

        # Surface parameters
        f.write("#Nchordwise  Cspace  [Nspanwise  Sspace]\n")
        f.write("12          1.0\n\n")

        # Write sections
        self._write_sections(
            f,
            geometry.leading_edge.points,
            geometry.trailing_edge.points,
            geometry.elevon
        )

    def _write_sections(
        self,
        f: TextIO,
        le_pts: np.ndarray,
        te_pts: np.ndarray,
        elevon: Optional[PanelPoints] = None
    ) -> None:
        """
        Write wing sections.

        Args:
            f: File handle
            le_pts: Leading edge points
            te_pts: Trailing edge points
            elevon: Optional elevon control surface points
        """
        n_sections = len(le_pts)

        # Sort sections by spanwise position
        y_coords = le_pts[:, 1]
        sort_idx = np.argsort(y_coords)

        for i in sort_idx:
            le = le_pts[i]
            te = te_pts[i]

            chord = np.linalg.norm(te - le)

            f.write("#" + "-" * 70 + "\n")
            f.write("SECTION\n")
            f.write(f"#Xle    Yle     Zle     Chord   Ainc  [ Nspan  Sspace ]\n")
            f.write(f"{le[0]:.6f}  {le[1]:.6f}  {le[2]:.6f}  {chord:.6f}  0.0\n\n")

            # Airfoil designation (use NACA 0012 as default)
            f.write("AFIL\n")
            f.write("0.0 1.0\n\n")  # Flat plate for now

            # Add control surface if this is near the elevon hinge line
            if elevon and i > n_sections // 2:  # Outboard sections
                f.write("CONTROL\n")
                f.write("#Cname   Cgain  Xhinge  HingeVec     SgnDup\n")
                f.write(f"Elevon   1.0    0.75    0. 0. 0.    1.0\n\n")

    def _write_winglet(
        self,
        f: TextIO,
        geometry: GeometryData
    ) -> None:
        """Write winglet surface definition."""
        if not geometry.winglet:
            return

        f.write("#" + "-" * 70 + "\n")
        f.write("SURFACE\n")
        f.write("Winglet\n\n")

        f.write("#Nchordwise  Cspace\n")
        f.write("10          1.0\n\n")

        # Write winglet sections
        # For winglets, we need to infer LE/TE from the point cloud
        # This is a simplified approach
        pts = geometry.winglet.points

        # Sort by height (Z coordinate)
        z_coords = pts[:, 2]
        sort_idx = np.argsort(z_coords)

        # Assume first half is LE, second half is TE (may need refinement)
        n_pts = len(pts)
        mid = n_pts // 2

        for i in range(mid):
            pt = pts[sort_idx[i]]
            chord = 0.1  # Default small chord for winglet

            f.write("SECTION\n")
            f.write(f"#Xle    Yle     Zle     Chord   Ainc\n")
            f.write(f"{pt[0]:.6f}  {pt[1]:.6f}  {pt[2]:.6f}  {chord:.6f}  0.0\n\n")

            f.write("AFIL\n")
            f.write("0.0 1.0\n\n")

    def create_surface_definition(
        self,
        le_points: np.ndarray,
        te_points: np.ndarray,
        surface_name: str = "Wing"
    ) -> str:
        """
        Create AVL SURFACE block as string.

        Args:
            le_points: Leading edge points
            te_points: Trailing edge points
            surface_name: Name of surface

        Returns:
            AVL SURFACE block as string
        """
        lines = []
        lines.append("SURFACE")
        lines.append(surface_name)
        lines.append("")
        lines.append("#Nchordwise  Cspace")
        lines.append("12          1.0")
        lines.append("")

        # Add sections
        for i, (le, te) in enumerate(zip(le_points, te_points)):
            chord = np.linalg.norm(te - le)
            lines.append("SECTION")
            lines.append(f"#Xle    Yle     Zle     Chord   Ainc")
            lines.append(f"{le[0]:.6f}  {le[1]:.6f}  {le[2]:.6f}  {chord:.6f}  0.0")
            lines.append("")

        return "\n".join(lines)
