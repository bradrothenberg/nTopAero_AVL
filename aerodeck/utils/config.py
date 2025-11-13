"""Configuration management for aerodeck generation."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Any
import yaml


@dataclass
class AnalysisConfig:
    """Analysis parameters configuration."""

    # Angle of attack range [min, max, step] in degrees
    alpha_range: list[float] = field(default_factory=lambda: [-10.0, 20.0, 2.0])

    # Sideslip angle range [min, max, step] in degrees
    beta_range: list[float] = field(default_factory=lambda: [-5.0, 5.0, 2.0])

    # Mach numbers to analyze
    mach_numbers: list[float] = field(default_factory=lambda: [0.1, 0.3, 0.5])

    # Reynolds numbers
    reynolds_numbers: list[float] = field(default_factory=lambda: [1.0e6, 2.0e6, 5.0e6])

    # Control surface deflection ranges [min, max, step] in degrees
    elevon_range: list[float] = field(default_factory=lambda: [-30.0, 30.0, 10.0])
    rudder_range: list[float] = field(default_factory=lambda: [-25.0, 25.0, 10.0])


@dataclass
class AVLConfig:
    """AVL-specific configuration."""

    # Path to AVL executable
    executable: str = "avl"

    # Maximum iterations for convergence
    max_iterations: int = 100

    # Convergence tolerance
    convergence_tolerance: float = 1e-6

    # Enable ground effect
    ground_effect: bool = False

    # Ground height (if ground_effect enabled)
    ground_height: Optional[float] = None


@dataclass
class XFOILConfig:
    """XFOIL-specific configuration."""

    # Path to XFOIL executable
    executable: str = "xfoil"

    # Transition criterion (N-critical)
    n_critical: float = 9.0

    # Maximum iterations
    max_iterations: int = 200

    # Enable viscous analysis
    viscous: bool = True

    # Panel refinement
    panel_refinement: int = 140


@dataclass
class OutputConfig:
    """Output generation configuration."""

    # Output formats
    formats: list[str] = field(default_factory=lambda: ["json", "pdf", "html"])

    # Save intermediate files (AVL/XFOIL raw output)
    save_intermediate: bool = True

    # Plot style
    plot_style: str = "seaborn"

    # Figure DPI for raster outputs
    figure_dpi: int = 150


@dataclass
class ReferenceConfig:
    """Reference geometry values (auto-computed if None)."""

    # Reference area [m²]
    area: Optional[float] = None

    # Reference span [m]
    span: Optional[float] = None

    # Reference chord (MAC) [m]
    chord: Optional[float] = None

    # Reference point for moments [x, y, z] in meters
    moment_reference: Optional[list[float]] = None


@dataclass
class ValidationConfig:
    """Validation thresholds."""

    # Maximum aspect ratio warning
    max_aspect_ratio: float = 30.0

    # Minimum aspect ratio warning
    min_aspect_ratio: float = 2.0

    # Warn if CG shifts by this fraction of MAC
    warn_cg_shift: float = 0.05

    # Minimum panel points
    min_panel_points: int = 3


@dataclass
class Config:
    """Main configuration class."""

    analysis: AnalysisConfig = field(default_factory=AnalysisConfig)
    avl: AVLConfig = field(default_factory=AVLConfig)
    xfoil: XFOILConfig = field(default_factory=XFOILConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    reference: ReferenceConfig = field(default_factory=ReferenceConfig)
    validation: ValidationConfig = field(default_factory=ValidationConfig)

    @classmethod
    def from_yaml(cls, path: Path) -> "Config":
        """
        Load configuration from YAML file.

        Args:
            path: Path to YAML configuration file

        Returns:
            Config instance

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config file is invalid
        """
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")

        try:
            with open(path, "r") as f:
                data = yaml.safe_load(f)

            if data is None:
                return cls()

            return cls(
                analysis=AnalysisConfig(**data.get("analysis", {})),
                avl=AVLConfig(**data.get("avl", {})),
                xfoil=XFOILConfig(**data.get("xfoil", {})),
                output=OutputConfig(**data.get("output", {})),
                reference=ReferenceConfig(**data.get("reference", {})),
                validation=ValidationConfig(**data.get("validation", {})),
            )
        except Exception as e:
            raise ValueError(f"Failed to parse configuration file: {e}")

    def to_yaml(self, path: Path) -> None:
        """
        Save configuration to YAML file.

        Args:
            path: Path to save YAML configuration file
        """
        data = {
            "analysis": {
                "alpha_range": self.analysis.alpha_range,
                "beta_range": self.analysis.beta_range,
                "mach_numbers": self.analysis.mach_numbers,
                "reynolds_numbers": self.analysis.reynolds_numbers,
                "controls": {
                    "elevon": self.analysis.elevon_range,
                    "rudder": self.analysis.rudder_range,
                },
            },
            "avl": {
                "executable": self.avl.executable,
                "max_iterations": self.avl.max_iterations,
                "convergence_tolerance": self.avl.convergence_tolerance,
                "ground_effect": self.avl.ground_effect,
                "ground_height": self.avl.ground_height,
            },
            "xfoil": {
                "executable": self.xfoil.executable,
                "n_critical": self.xfoil.n_critical,
                "max_iterations": self.xfoil.max_iterations,
                "viscous": self.xfoil.viscous,
                "panel_refinement": self.xfoil.panel_refinement,
            },
            "output": {
                "formats": self.output.formats,
                "save_intermediate": self.output.save_intermediate,
                "plot_style": self.output.plot_style,
                "figure_dpi": self.output.figure_dpi,
            },
            "reference": {
                "area": self.reference.area,
                "span": self.reference.span,
                "chord": self.reference.chord,
                "moment_reference": self.reference.moment_reference,
            },
            "validation": {
                "max_aspect_ratio": self.validation.max_aspect_ratio,
                "min_aspect_ratio": self.validation.min_aspect_ratio,
                "warn_cg_shift": self.validation.warn_cg_shift,
                "min_panel_points": self.validation.min_panel_points,
            },
        }

        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    def get_alpha_values(self) -> list[float]:
        """Get list of alpha values from range."""
        min_alpha, max_alpha, step = self.analysis.alpha_range
        import numpy as np
        return np.arange(min_alpha, max_alpha + step/2, step).tolist()

    def get_beta_values(self) -> list[float]:
        """Get list of beta values from range."""
        min_beta, max_beta, step = self.analysis.beta_range
        import numpy as np
        return np.arange(min_beta, max_beta + step/2, step).tolist()

    def get_elevon_values(self) -> list[float]:
        """Get list of elevon deflection values from range."""
        min_de, max_de, step = self.analysis.elevon_range
        import numpy as np
        return np.arange(min_de, max_de + step/2, step).tolist()


def load_config(config_path: Optional[Path] = None) -> Config:
    """
    Load configuration from file or return default.

    Args:
        config_path: Optional path to configuration file

    Returns:
        Config instance
    """
    if config_path and config_path.exists():
        return Config.from_yaml(config_path)
    return Config()


def create_default_config(output_path: Path) -> None:
    """
    Create a default configuration file.

    Args:
        output_path: Path to save the default configuration
    """
    config = Config()
    config.to_yaml(output_path)
