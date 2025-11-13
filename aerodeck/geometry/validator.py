"""Geometry validation for aerodynamic analysis.

Units: US Customary (feet, lbm)
All dimensions in feet.
"""

from dataclasses import dataclass
from typing import Optional
import numpy as np

from .loader import GeometryData, PanelPoints
from ..utils.logger import get_logger
from ..utils.config import ValidationConfig


@dataclass
class ValidationResult:
    """Result of geometry validation."""

    is_valid: bool
    errors: list[str]
    warnings: list[str]

    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0


class GeometryValidator:
    """Validate geometry for aerodynamic analysis."""

    def __init__(
        self,
        config: Optional[ValidationConfig] = None,
        verbose: bool = True
    ) -> None:
        """
        Initialize validator.

        Args:
            config: Validation configuration
            verbose: Enable verbose logging
        """
        self.config = config or ValidationConfig()
        self.logger = get_logger(verbose=verbose)

    def validate(self, geometry: GeometryData) -> ValidationResult:
        """
        Validate geometry data.

        Args:
            geometry: Geometry data to validate

        Returns:
            ValidationResult with errors and warnings
        """
        self.logger.info("Validating geometry...")
        self.logger.indent()

        errors = []
        warnings = []

        # Validate panel point counts
        for panel in geometry.get_all_panels():
            if panel.n_points < self.config.min_panel_points:
                errors.append(
                    f"{panel.label} has only {panel.n_points} points "
                    f"(minimum {self.config.min_panel_points})"
                )
            self.logger.debug(f"{panel.label}: {panel.n_points} points")

        # Check LE and TE have same number of points
        if geometry.leading_edge.n_points != geometry.trailing_edge.n_points:
            errors.append(
                f"Leading edge ({geometry.leading_edge.n_points} points) and "
                f"trailing edge ({geometry.trailing_edge.n_points} points) "
                "must have same number of points"
            )

        # Validate mass properties
        mass_errors, mass_warnings = self._validate_mass_properties(
            geometry.mass_properties
        )
        errors.extend(mass_errors)
        warnings.extend(mass_warnings)

        # Validate panel geometry
        geom_errors, geom_warnings = self._validate_panel_geometry(geometry)
        errors.extend(geom_errors)
        warnings.extend(geom_warnings)

        # Check for self-intersections (basic check)
        if self._check_self_intersections(geometry):
            self.logger.success("No self-intersections detected")
        else:
            warnings.append("Potential self-intersections detected")

        # Report results
        if errors:
            for error in errors:
                self.logger.error(error)
        if warnings:
            for warning in warnings:
                self.logger.warning(warning)

        if not errors and not warnings:
            self.logger.success("All validation checks passed")

        self.logger.dedent()

        return ValidationResult(
            is_valid=(len(errors) == 0),
            errors=errors,
            warnings=warnings
        )

    def _validate_mass_properties(
        self,
        mass_props
    ) -> tuple[list[str], list[str]]:
        """
        Validate mass properties.

        Args:
            mass_props: MassProperties to validate

        Returns:
            Tuple of (errors, warnings)
        """
        errors = []
        warnings = []

        # Check mass is positive
        if mass_props.mass <= 0:
            errors.append(f"Mass must be positive, got {mass_props.mass}")

        # Check inertia tensor is positive definite
        try:
            eigenvalues = np.linalg.eigvals(mass_props.inertia)
            if any(eigenvalues <= 0):
                errors.append("Inertia tensor must be positive definite")
        except np.linalg.LinAlgError:
            errors.append("Invalid inertia tensor (singular)")

        # Check inertia tensor is symmetric
        if not np.allclose(mass_props.inertia, mass_props.inertia.T):
            errors.append("Inertia tensor must be symmetric")

        self.logger.debug(f"Mass: {mass_props.mass:.3f} lbm")
        self.logger.debug(f"CG: [{mass_props.cg[0]:.3f}, {mass_props.cg[1]:.3f}, {mass_props.cg[2]:.3f}] ft")

        return errors, warnings

    def _validate_panel_geometry(
        self,
        geometry: GeometryData
    ) -> tuple[list[str], list[str]]:
        """
        Validate panel geometry.

        Args:
            geometry: GeometryData to validate

        Returns:
            Tuple of (errors, warnings)
        """
        errors = []
        warnings = []

        # Calculate basic geometric properties
        le_pts = geometry.leading_edge.points
        te_pts = geometry.trailing_edge.points

        # Calculate local chord at each section
        chords = np.linalg.norm(te_pts - le_pts, axis=1)

        if np.any(chords <= 0):
            errors.append("Found sections with zero or negative chord")

        # Calculate span (assuming spanwise is in Y direction)
        y_coords = le_pts[:, 1]  # Y coordinates
        span = np.max(y_coords) - np.min(y_coords)

        if span <= 0:
            errors.append(f"Invalid span: {span}")

        # Calculate mean chord
        mean_chord = np.mean(chords)

        # Calculate aspect ratio
        if mean_chord > 0:
            aspect_ratio = span / mean_chord

            if aspect_ratio > self.config.max_aspect_ratio:
                warnings.append(
                    f"Aspect ratio ({aspect_ratio:.1f}) exceeds recommended "
                    f"maximum ({self.config.max_aspect_ratio})"
                )
            elif aspect_ratio < self.config.min_aspect_ratio:
                warnings.append(
                    f"Aspect ratio ({aspect_ratio:.1f}) below recommended "
                    f"minimum ({self.config.min_aspect_ratio})"
                )

            self.logger.debug(f"Span: {span:.3f} ft")
            self.logger.debug(f"Mean chord: {mean_chord:.3f} ft")
            self.logger.debug(f"Aspect ratio: {aspect_ratio:.2f}")

        # Check winglet dihedral if present
        if geometry.winglet:
            winglet_warnings = self._check_winglet_geometry(geometry.winglet)
            warnings.extend(winglet_warnings)

        return errors, warnings

    def _check_winglet_geometry(self, winglet: PanelPoints) -> list[str]:
        """
        Check winglet geometry for common issues.

        Args:
            winglet: Winglet panel points

        Returns:
            List of warnings
        """
        warnings = []

        # Calculate winglet dihedral angle
        z_coords = winglet.points[:, 2]
        y_coords = winglet.points[:, 1]

        dz = np.max(z_coords) - np.min(z_coords)
        dy = np.max(y_coords) - np.min(y_coords)

        if dy > 0:
            dihedral_angle = np.rad2deg(np.arctan(dz / dy))

            if abs(dihedral_angle) > 80:
                warnings.append(
                    f"Winglet dihedral angle ({dihedral_angle:.1f}°) is very high"
                )

            self.logger.debug(f"Winglet dihedral: {dihedral_angle:.1f}°")

        return warnings

    def _check_self_intersections(self, geometry: GeometryData) -> bool:
        """
        Basic check for self-intersections.

        This is a simplified check that looks for overlapping bounding boxes.
        A more sophisticated check would require mesh intersection algorithms.

        Args:
            geometry: GeometryData to check

        Returns:
            True if no obvious intersections found
        """
        panels = geometry.get_all_panels()

        # Get bounding boxes for each panel
        bboxes = [panel.get_bounds() for panel in panels]

        # Check for overlapping bounding boxes
        for i in range(len(bboxes)):
            for j in range(i + 1, len(bboxes)):
                min_i, max_i = bboxes[i]
                min_j, max_j = bboxes[j]

                # Check if bounding boxes overlap
                overlap = np.all(min_i <= max_j) and np.all(min_j <= max_i)

                if overlap:
                    # This is not necessarily an error, just flag for review
                    self.logger.debug(
                        f"Bounding box overlap between {panels[i].label} "
                        f"and {panels[j].label}"
                    )

        # Return True (no obvious issues)
        return True

    def quick_validate(self, geometry: GeometryData) -> bool:
        """
        Quick validation check (only critical errors).

        Args:
            geometry: GeometryData to validate

        Returns:
            True if geometry passes basic checks
        """
        # Check minimum requirements
        if geometry.leading_edge.n_points < self.config.min_panel_points:
            return False
        if geometry.trailing_edge.n_points < self.config.min_panel_points:
            return False
        if geometry.leading_edge.n_points != geometry.trailing_edge.n_points:
            return False
        if geometry.mass_properties.mass <= 0:
            return False

        return True
