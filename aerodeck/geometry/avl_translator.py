"""Translate nTop geometry to AVL input format.

Units: US Customary (feet, lbm)
All dimensions in feet for AVL.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, TextIO
import numpy as np

from .loader import GeometryData, PanelPoints
from ..utils.logger import get_logger
from ..utils.config import ReferenceConfig


@dataclass
class ReferenceGeometry:
    """Reference geometry values for aerodynamic analysis (US Customary)."""

    area: float  # Reference area [ft²]
    span: float  # Reference span [ft]
    chord: float  # Mean aerodynamic chord [ft]
    cg: np.ndarray  # Center of gravity [x, y, z] ft


class AVLGeometryWriter:
    """Convert nTop geometry to AVL input format."""

    def __init__(
        self,
        ref_config: Optional[ReferenceConfig] = None,
        airfoil_file: Optional[Path] = None,
        verbose: bool = True
    ) -> None:
        """
        Initialize the AVL translator.

        Args:
            ref_config: Reference geometry configuration
            airfoil_file: Path to custom airfoil .dat file (optional)
            verbose: Enable verbose logging
        """
        self.ref_config = ref_config or ReferenceConfig()
        self.airfoil_file = airfoil_file
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

        self.logger.debug(f"S_ref = {ref_geom.area:.3f} ft²")
        self.logger.debug(f"b_ref = {ref_geom.span:.3f} ft")
        self.logger.debug(f"c_ref = {ref_geom.chord:.3f} ft (MAC)")

        # Write AVL file
        with open(output_path, 'w') as f:
            self._write_header(f, aircraft_name, ref_geom)

            # Write main wing with integrated control surfaces
            self._write_main_wing(f, geometry, ref_geom)

            # Write winglet as vertical surface
            if geometry.winglet:
                self._write_winglet(f, geometry.winglet)

        self.logger.success(f"AVL input written: {output_path.name}")

        # Write mass file
        mass_file = output_path.with_suffix('.mass')
        self._write_mass_file(mass_file, geometry, ref_geom)
        self.logger.success(f"Mass file written: {mass_file.name}")

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
            Wingspan [ft] (full span, doubled if half-span model)
        """
        y_coords = le_pts[:, 1]
        half_span = np.max(y_coords) - np.min(y_coords)

        # Double if half-span model (all Y coords >= 0 indicates half-span)
        # When we have YDUPLICATE, we need to report the full span
        if np.min(y_coords) >= -0.01:  # Tolerance for floating point
            return abs(half_span * 2)

        return abs(half_span)

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

        # Y-duplication for symmetric aircraft (mirror across Y=0)
        f.write("YDUPLICATE\n")
        f.write("0.0\n\n")

        # Write sections with control surface
        self._write_sections(
            f,
            geometry.leading_edge.points,
            geometry.trailing_edge.points,
            geometry.elevon  # Enable elevon control surface
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

        # Calculate spanwise distances for intelligent panel distribution
        y_sorted = y_coords[sort_idx]

        # Determine where to place elevon control surface (outboard sections)
        # Control should start at midspan and extend to tip for effectiveness
        elevon_start_idx = len(sort_idx) // 2 if elevon else len(sort_idx)
        elevon_end_idx = len(sort_idx) - 1  # Extend to second-to-last section

        for idx, i in enumerate(sort_idx):
            le = le_pts[i]
            te = te_pts[i]

            chord = np.linalg.norm(te - le)

            # Compute spanwise panel count proportional to local span
            # Aim for roughly equal panel sizes spanwise (~0.4-0.5 ft per panel)
            if idx < len(sort_idx) - 1:
                span_segment = abs(y_sorted[idx + 1] - y_sorted[idx])
                # Target ~0.4 ft (5 inches) panel width for more uniform distribution
                target_panel_width = 0.4  # ft
                nspan = max(3, min(40, int(round(span_segment / target_panel_width))))
                sspace = 1.0  # Uniform spacing
            else:
                nspan = 0
                sspace = 0

            f.write("#" + "-" * 70 + "\n")
            f.write("SECTION\n")
            f.write(f"#Xle    Yle     Zle     Chord   Ainc  [ Nspan  Sspace ]\n")
            if nspan > 0:
                f.write(f"{le[0]:.6f}  {le[1]:.6f}  {le[2]:.6f}  {chord:.6f}  0.0  {nspan}  {sspace}\n\n")
            else:
                f.write(f"{le[0]:.6f}  {le[1]:.6f}  {le[2]:.6f}  {chord:.6f}  0.0\n\n")

            # Write airfoil section
            self._write_airfoil_section(f)

            # Add control surfaces on outboard sections (from midspan to near-tip)
            # Control surfaces need to span between sections to be effective
            if elevon and elevon_start_idx <= idx < elevon_end_idx:
                # Elevon: SgnDup = 1.0 means same deflection on both sides (for pitch control)
                f.write("CONTROL\n")
                f.write("#Cname   Cgain  Xhinge  XYZhvec  SgnDup\n")
                f.write(f"elevon   1.0    0.75    0. 0. 0.    1.0\n\n")

                # Aileron: SgnDup = -1.0 means opposite deflection on each side (for roll control)
                f.write("CONTROL\n")
                f.write("#Cname   Cgain  Xhinge  XYZhvec  SgnDup\n")
                f.write(f"aileron  1.0    0.75    0. 0. 0.   -1.0\n\n")

    def _interpret_clockwise_panel(self, pts: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """
        Interpret a clockwise panel outline and extract LE/TE edges.

        For a quadrilateral panel in clockwise notation starting from root LE:
        - Points: [root_LE, tip_LE, tip_TE, root_TE]
        - LE edge: points 0, 1 (root to tip)
        - TE edge: points 3, 2 (root to tip, reversed order)

        For more complex panels, we identify LE/TE by X-coordinate.

        Args:
            pts: Panel points in clockwise order

        Returns:
            Tuple of (le_points, te_points)
        """
        # Remove duplicate closing point if present
        if len(pts) > 3 and np.allclose(pts[0], pts[-1]):
            pts = pts[:-1]

        if len(pts) == 4:
            # Quadrilateral: clockwise from root LE
            # [root_LE, tip_LE, tip_TE, root_TE]
            le_pts = np.array([pts[0], pts[1]])  # Root LE to Tip LE
            te_pts = np.array([pts[3], pts[2]])  # Root TE to Tip TE
            return le_pts, te_pts
        else:
            # More complex shape: split by X coordinate
            # Forward half (min X) is LE, aft half (max X) is TE
            n = len(pts)
            mid = n // 2

            # Sort by X to identify forward/aft
            x_coords = pts[:, 0]
            if np.max(x_coords[:mid]) < np.min(x_coords[mid:]):
                # First half is forward (LE), second half is aft (TE)
                le_pts = pts[:mid]
                te_pts = pts[mid:][::-1]  # Reverse to match spanwise order
            else:
                # Need more sophisticated splitting
                # Find the two points with min/max X
                min_x_idx = np.argmin(x_coords)
                max_x_idx = np.argmax(x_coords)

                # Split at these points
                if min_x_idx < max_x_idx:
                    le_pts = pts[min_x_idx:max_x_idx+1]
                    te_pts = np.vstack([pts[max_x_idx:], pts[:min_x_idx+1]])
                else:
                    le_pts = np.vstack([pts[min_x_idx:], pts[:max_x_idx+1]])
                    te_pts = pts[max_x_idx:min_x_idx+1]

            return le_pts, te_pts

    def _write_elevon(
        self,
        f: TextIO,
        elevon: PanelPoints
    ) -> None:
        """Write elevon control surface as a separate movable surface."""
        f.write("#" + "-" * 70 + "\n")
        f.write("SURFACE\n")
        f.write("Elevon\n\n")

        f.write("#Nchordwise  Cspace  [Nspanwise  Sspace]\n")
        f.write("8          1.0\n\n")

        # Y-duplication for symmetric aircraft
        f.write("YDUPLICATE\n")
        f.write("0.0\n\n")

        # Interpret clockwise panel notation
        le_pts, te_pts = self._interpret_clockwise_panel(elevon.points)

        # Write sections
        self._write_sections(f, le_pts, te_pts, None)

    def _write_winglet(
        self,
        f: TextIO,
        winglet: PanelPoints
    ) -> None:
        """
        Write winglet surface definition.

        Winglet is a vertical surface, so we sort by Z (height) rather than Y (span).
        The winglet polygon defines sections at different heights.
        """
        f.write("#" + "-" * 70 + "\n")
        f.write("SURFACE\n")
        f.write("Winglet\n\n")

        f.write("#Nchordwise  Cspace  [Nspanwise  Sspace]\n")
        f.write("8          1.0\n\n")

        # Y-duplication for symmetric aircraft
        f.write("YDUPLICATE\n")
        f.write("0.0\n\n")

        # For winglet: interpret as vertical surface
        # Group points by Z coordinate to find sections at each height
        pts = winglet.points

        # Remove closing point if present
        if len(pts) > 3 and np.allclose(pts[0], pts[-1]):
            pts = pts[:-1]

        # Group points by Z level (rounded to avoid floating point issues)
        z_coords = pts[:, 2]
        z_rounded = np.round(z_coords, 2)
        unique_z = np.unique(z_rounded)

        # Create sections at each Z level (sorted bottom to top)
        unique_z_sorted = np.sort(unique_z)

        for idx, z_level in enumerate(unique_z_sorted):
            # Get all points at this Z level
            mask = np.abs(z_rounded - z_level) < 0.01
            level_pts = pts[mask]

            # Sort by X coordinate (forward to aft)
            x_sort_idx = np.argsort(level_pts[:, 0])
            level_pts_sorted = level_pts[x_sort_idx]

            # LE is forward-most, TE is aft-most
            le = level_pts_sorted[0]
            te = level_pts_sorted[-1]
            chord = np.linalg.norm(te - le)

            # Compute vertical span to next section
            if idx < len(unique_z_sorted) - 1:
                z_span = abs(unique_z_sorted[idx + 1] - z_level)
                nspan = max(3, min(15, int(round(z_span / 0.5))))  # ~0.5 ft panels
                sspace = 1.0
            else:
                nspan = 0
                sspace = 0

            f.write("#" + "-" * 70 + "\n")
            f.write("SECTION\n")
            f.write(f"#Xle    Yle     Zle     Chord   Ainc  [ Nspan  Sspace ]\n")
            if nspan > 0:
                f.write(f"{le[0]:.6f}  {le[1]:.6f}  {le[2]:.6f}  {chord:.6f}  0.0  {nspan}  {sspace}\n\n")
            else:
                f.write(f"{le[0]:.6f}  {le[1]:.6f}  {le[2]:.6f}  {chord:.6f}  0.0\n\n")

            # Winglets use NACA 0012 symmetric airfoil (flat plate)
            self._write_airfoil_section(f, use_custom_airfoil=False)

    def _write_airfoil_section(self, f: TextIO, use_custom_airfoil: bool = True) -> None:
        """
        Write airfoil section to AVL file.

        Args:
            f: File handle to write to
            use_custom_airfoil: If True, uses custom airfoil file (if available).
                               If False, forces NACA 0012 symmetric airfoil.

        For main wing: use_custom_airfoil=True (NACA 64-208 cambered airfoil)
        For winglets: use_custom_airfoil=False (NACA 0012 flat plate)
        """
        if use_custom_airfoil and self.airfoil_file and self.airfoil_file.exists():
            # Use AFILE command to load airfoil from file
            # Must use ABSOLUTE path since AVL will be run from a different directory
            # Convert to forward slashes for AVL (works on Windows too)
            airfoil_path = str(self.airfoil_file.resolve().as_posix())
            f.write(f"AFILE\n")
            f.write(f"{airfoil_path}\n\n")
        else:
            # Default to NACA 0012 for symmetric airfoil (flat plate)
            f.write("NACA\n")
            f.write("0012\n\n")

    def _write_mass_file(
        self,
        mass_file: Path,
        geometry: GeometryData,
        ref_geom: ReferenceGeometry
    ) -> None:
        """
        Write AVL .mass file with mass and inertia properties.

        AVL .mass file format:
        #  mass   x       y       z       Ixx     Iyy     Izz     Ixy     Ixz     Iyz
        Units: Lunit, Munit  (from .avl file - we use feet and lbm)

        Args:
            mass_file: Path to .mass file
            geometry: Geometry data with mass properties
            ref_geom: Reference geometry
        """
        mass_props = geometry.mass_properties
        inertia = mass_props.inertia

        with open(mass_file, 'w') as f:
            f.write("#  AVL Mass File\n")
            f.write("#  Units: feet, lbm, lbm-ft^2\n")
            f.write("#\n")
            f.write("#  mass       x          y          z          Ixx        Iyy        Izz        Ixy        Ixz        Iyz\n")
            f.write(f"{mass_props.mass:10.4f}  "
                   f"{mass_props.cg[0]:10.6f}  "
                   f"{mass_props.cg[1]:10.6f}  "
                   f"{mass_props.cg[2]:10.6f}  "
                   f"{inertia[0,0]:10.4f}  "
                   f"{inertia[1,1]:10.4f}  "
                   f"{inertia[2,2]:10.4f}  "
                   f"{inertia[0,1]:10.4f}  "
                   f"{inertia[0,2]:10.4f}  "
                   f"{inertia[1,2]:10.4f}\n")

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
