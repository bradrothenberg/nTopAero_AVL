"""Geometry loading from nTop CSV exports.

Input Units: US Customary (inches, lbm)
- Geometry coordinates in inches
- Mass in lbm (pounds mass)
- Inertia in lbm⋅in²

Output Units: US Customary (feet, lbm) for AVL
- Geometry converted to feet (divide by 12)
- Mass stays in lbm
- Inertia converted to lbm⋅ft² (divide by 144)
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import numpy as np
import pandas as pd

from ..utils.logger import get_logger

# Unit conversion constants
INCHES_TO_FEET = 1.0 / 12.0  # 1 inch = 1/12 feet
IN2_TO_FT2 = 1.0 / 144.0  # 1 in² = 1/144 ft²


@dataclass
class MassProperties:
    """Mass and inertia properties (in feet/lbm for AVL)."""

    mass: float  # lbm (pounds mass)
    cg: np.ndarray  # [x, y, z] in feet
    inertia: np.ndarray  # 3x3 inertia tensor [lbm⋅ft²]

    def __post_init__(self) -> None:
        """Validate and convert arrays."""
        self.cg = np.array(self.cg).flatten()
        self.inertia = np.array(self.inertia).reshape(3, 3)

        if self.cg.shape != (3,):
            raise ValueError(f"CG must be 3-element array, got shape {self.cg.shape}")
        if self.inertia.shape != (3, 3):
            raise ValueError(f"Inertia must be 3x3 matrix, got shape {self.inertia.shape}")


@dataclass
class PanelPoints:
    """Panel point cloud data."""

    points: np.ndarray  # Nx3 array of [x, y, z] coordinates
    label: str

    def __post_init__(self) -> None:
        """Validate point array."""
        self.points = np.array(self.points)
        if self.points.ndim != 2 or self.points.shape[1] != 3:
            raise ValueError(
                f"Points must be Nx3 array, got shape {self.points.shape}"
            )

    @property
    def n_points(self) -> int:
        """Number of points."""
        return len(self.points)

    def get_bounds(self) -> tuple[np.ndarray, np.ndarray]:
        """Get bounding box [min, max] for each axis."""
        return self.points.min(axis=0), self.points.max(axis=0)


@dataclass
class GeometryData:
    """Complete geometry data from nTop export."""

    mass_properties: MassProperties
    leading_edge: PanelPoints
    trailing_edge: PanelPoints
    winglet: Optional[PanelPoints] = None
    elevon: Optional[PanelPoints] = None

    def get_all_panels(self) -> list[PanelPoints]:
        """Get list of all panel point sets."""
        panels = [self.leading_edge, self.trailing_edge]
        if self.winglet:
            panels.append(self.winglet)
        if self.elevon:
            panels.append(self.elevon)
        return panels

    def get_overall_bounds(self) -> tuple[np.ndarray, np.ndarray]:
        """Get overall bounding box for all geometry."""
        all_points = []
        for panel in self.get_all_panels():
            all_points.append(panel.points)

        combined = np.vstack(all_points)
        return combined.min(axis=0), combined.max(axis=0)


class GeometryLoader:
    """Load geometry data from nTop CSV exports."""

    REQUIRED_FILES = ["mass.csv", "LEpts.csv", "TEpts.csv"]
    OPTIONAL_FILES = ["WINGLETpts.csv", "ELEVONpts.csv"]

    def __init__(self, verbose: bool = True) -> None:
        """
        Initialize the loader.

        Args:
            verbose: Enable verbose logging
        """
        self.logger = get_logger(verbose=verbose)

    def load_panel_data(self, folder_path: Path) -> GeometryData:
        """
        Load all geometry data from folder.

        Args:
            folder_path: Path to folder containing CSV files

        Returns:
            GeometryData instance with all loaded data

        Raises:
            FileNotFoundError: If required files are missing
            ValueError: If data is invalid
        """
        folder = Path(folder_path)
        if not folder.is_dir():
            raise FileNotFoundError(f"Directory not found: {folder_path}")

        self.logger.info(f"Loading geometry from: {folder}")
        self.logger.indent()

        # Check for required files
        missing_files = []
        for filename in self.REQUIRED_FILES:
            if not (folder / filename).exists():
                missing_files.append(filename)

        if missing_files:
            raise FileNotFoundError(
                f"Missing required files: {', '.join(missing_files)}"
            )

        # Load mass properties
        mass_props = self._load_mass_properties(folder / "mass.csv")
        self.logger.success(f"mass.csv (mass={mass_props.mass:.3f} lbm)")

        # Load panel points
        le_points = self._load_panel_points(folder / "LEpts.csv", "Leading Edge")
        self.logger.success(f"LEpts.csv ({le_points.n_points} points)")

        te_points = self._load_panel_points(folder / "TEpts.csv", "Trailing Edge")
        self.logger.success(f"TEpts.csv ({te_points.n_points} points)")

        # Load optional files
        winglet_points = None
        if (folder / "WINGLETpts.csv").exists():
            winglet_points = self._load_panel_points(
                folder / "WINGLETpts.csv", "Winglet"
            )
            self.logger.success(f"WINGLETpts.csv ({winglet_points.n_points} points)")

        elevon_points = None
        if (folder / "ELEVONpts.csv").exists():
            elevon_points = self._load_panel_points(
                folder / "ELEVONpts.csv", "Elevon"
            )
            self.logger.success(f"ELEVONpts.csv ({elevon_points.n_points} points)")

        self.logger.dedent()

        geometry = GeometryData(
            mass_properties=mass_props,
            leading_edge=le_points,
            trailing_edge=te_points,
            winglet=winglet_points,
            elevon=elevon_points,
        )

        return geometry

    def _load_mass_properties(self, file_path: Path) -> MassProperties:
        """
        Load mass properties from CSV.

        Expected format:
        - Single row with columns: mass, cg_x, cg_y, cg_z, Ixx, Iyy, Izz, Ixy, Ixz, Iyz
        - Also supports prefixed columns: avl_mass, avl_CGx, avl_CGy, etc.

        Args:
            file_path: Path to mass.csv file

        Returns:
            MassProperties instance

        Raises:
            ValueError: If file format is invalid
        """
        try:
            df = pd.read_csv(file_path)

            if len(df) != 1:
                raise ValueError(f"Expected 1 row in mass.csv, got {len(df)}")

            row = df.iloc[0]

            # Helper function to find column value with multiple naming conventions
            def get_value(names: list[str], fallback_idx: int) -> float:
                for name in names:
                    if name in row.index:
                        return float(row[name])
                # Fallback to column index
                if fallback_idx < len(row):
                    return float(row.iloc[fallback_idx])
                raise ValueError(f"Could not find column for {names}")

            # Extract mass and CG with flexible column naming
            mass = get_value(["avl_mass", "mass"], 0)
            cg_x = get_value(["avl_CGx", "cg_x", "x"], 1)
            cg_y = get_value(["avl_CGy", "cg_y", "y"], 2)
            cg_z = get_value(["avl_CGz", "cg_z", "z"], 3)
            cg = np.array([cg_x, cg_y, cg_z])

            # Extract inertia tensor (symmetric)
            Ixx = get_value(["avl_Ixx", "Ixx"], 4)
            Iyy = get_value(["avl_Iyy", "Iyy"], 5)
            Izz = get_value(["avl_Izz", "Izz"], 6)

            # Products of inertia (optional, default to 0)
            try:
                Ixy = get_value(["avl_Ixy", "Ixy"], 7)
            except (ValueError, IndexError):
                Ixy = 0.0

            try:
                Iyz = get_value(["avl_Iyz", "Iyz"], 8)
            except (ValueError, IndexError):
                Iyz = 0.0

            try:
                Ixz = get_value(["avl_Ixz", "Ixz"], 9)
            except (ValueError, IndexError):
                Ixz = 0.0

            inertia = np.array([
                [Ixx, Ixy, Ixz],
                [Ixy, Iyy, Iyz],
                [Ixz, Iyz, Izz],
            ])

            # Convert from inches to feet for AVL
            cg_ft = cg * INCHES_TO_FEET
            inertia_ft = inertia * IN2_TO_FT2  # lbm⋅in² to lbm⋅ft²

            return MassProperties(mass=mass, cg=cg_ft, inertia=inertia_ft)

        except Exception as e:
            raise ValueError(f"Failed to load mass properties: {e}")

    def _load_panel_points(self, file_path: Path, label: str) -> PanelPoints:
        """
        Load panel points from CSV.

        Expected format: CSV with x, y, z columns (or first 3 columns as x,y,z)

        Args:
            file_path: Path to points CSV file
            label: Label for this panel

        Returns:
            PanelPoints instance

        Raises:
            ValueError: If file format is invalid
        """
        try:
            df = pd.read_csv(file_path)

            if len(df) == 0:
                raise ValueError("Empty CSV file")

            # Try to extract x, y, z columns
            if all(col in df.columns for col in ["x", "y", "z"]):
                points = df[["x", "y", "z"]].values
            elif df.shape[1] >= 3:
                # Use first 3 columns
                points = df.iloc[:, :3].values
            else:
                raise ValueError("Could not find x, y, z columns")

            # Convert from inches to feet for AVL
            points_ft = points * INCHES_TO_FEET

            return PanelPoints(points=points_ft, label=label)

        except Exception as e:
            raise ValueError(f"Failed to load panel points from {file_path}: {e}")

    def load_mass_properties(self, file_path: Path) -> MassProperties:
        """
        Load only mass properties.

        Args:
            file_path: Path to mass.csv file

        Returns:
            MassProperties instance
        """
        return self._load_mass_properties(file_path)
