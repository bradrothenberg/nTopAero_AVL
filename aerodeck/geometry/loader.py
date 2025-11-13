"""Geometry loading from nTop CSV exports."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import numpy as np
import pandas as pd

from ..utils.logger import get_logger


@dataclass
class MassProperties:
    """Mass and inertia properties."""

    mass: float  # kg
    cg: np.ndarray  # [x, y, z] in meters
    inertia: np.ndarray  # 3x3 inertia tensor [kg⋅m²]

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
        self.logger.success(f"mass.csv (mass={mass_props.mass:.3f} kg)")

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

            # Extract mass and CG
            mass = float(row.get("mass", row.iloc[0]))
            cg = np.array([
                float(row.get("cg_x", row.get("x", row.iloc[1]))),
                float(row.get("cg_y", row.get("y", row.iloc[2]))),
                float(row.get("cg_z", row.get("z", row.iloc[3]))),
            ])

            # Extract inertia tensor (symmetric)
            # Check multiple possible column naming conventions
            if "Ixx" in row:
                Ixx = float(row["Ixx"])
                Iyy = float(row["Iyy"])
                Izz = float(row["Izz"])
                Ixy = float(row.get("Ixy", 0.0))
                Ixz = float(row.get("Ixz", 0.0))
                Iyz = float(row.get("Iyz", 0.0))
            else:
                # Fallback to column indices
                Ixx = float(row.iloc[4])
                Iyy = float(row.iloc[5])
                Izz = float(row.iloc[6])
                Ixy = float(row.iloc[7]) if len(row) > 7 else 0.0
                Ixz = float(row.iloc[8]) if len(row) > 8 else 0.0
                Iyz = float(row.iloc[9]) if len(row) > 9 else 0.0

            inertia = np.array([
                [Ixx, Ixy, Ixz],
                [Ixy, Iyy, Iyz],
                [Ixz, Iyz, Izz],
            ])

            return MassProperties(mass=mass, cg=cg, inertia=inertia)

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

            return PanelPoints(points=points, label=label)

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
