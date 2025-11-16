"""XFOIL execution wrapper for airfoil polar generation.

This module provides interfaces to run XFOIL in batch mode to generate
airfoil polars (CL, CD, CM vs alpha) at various Reynolds numbers.

Units: US Customary (feet, lbm)
"""

import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Tuple
import numpy as np
import pandas as pd

from ..utils.logger import get_logger


@dataclass
class PolarData:
    """Airfoil polar data at a single Reynolds number."""

    reynolds: float  # Reynolds number
    mach: float  # Mach number
    alpha: np.ndarray  # Angle of attack [deg]
    cl: np.ndarray  # Lift coefficient
    cd: np.ndarray  # Drag coefficient
    cm: np.ndarray  # Moment coefficient (about c/4)

    def interpolate(self, alpha_query: float) -> Tuple[float, float, float]:
        """
        Interpolate CL, CD, CM at a given angle of attack.

        Args:
            alpha_query: Angle of attack to query [deg]

        Returns:
            Tuple of (CL, CD, CM) at the queried alpha
        """
        cl_interp = np.interp(alpha_query, self.alpha, self.cl)
        cd_interp = np.interp(alpha_query, self.alpha, self.cd)
        cm_interp = np.interp(alpha_query, self.alpha, self.cm)
        return cl_interp, cd_interp, cm_interp


@dataclass
class AirfoilPolars:
    """Collection of polar data at multiple Reynolds numbers."""

    airfoil_name: str
    polars: List[PolarData]

    def get_polar(self, reynolds: float, mach: float = 0.0) -> Optional[PolarData]:
        """
        Get polar data for a specific Reynolds number.

        Uses nearest neighbor if exact match not found.

        Args:
            reynolds: Reynolds number
            mach: Mach number (optional)

        Returns:
            PolarData for the closest Reynolds number, or None if no data
        """
        if not self.polars:
            return None

        # Find closest Reynolds number
        re_values = np.array([p.reynolds for p in self.polars])
        idx = np.argmin(np.abs(re_values - reynolds))
        return self.polars[idx]

    def interpolate_coeffs(
        self,
        alpha: float,
        reynolds: float,
        mach: float = 0.0
    ) -> Tuple[float, float, float]:
        """
        Interpolate coefficients at given flight condition.

        Args:
            alpha: Angle of attack [deg]
            reynolds: Reynolds number
            mach: Mach number

        Returns:
            Tuple of (CL, CD, CM)
        """
        polar = self.get_polar(reynolds, mach)
        if polar is None:
            return 0.0, 0.0, 0.0
        return polar.interpolate(alpha)


class XFOILRunner:
    """Execute XFOIL to generate airfoil polars."""

    def __init__(
        self,
        xfoil_path: str = "xfoil",
        verbose: bool = True
    ) -> None:
        """
        Initialize XFOIL runner.

        Args:
            xfoil_path: Path to XFOIL executable (default: "xfoil" in PATH)
            verbose: Enable verbose logging
        """
        self.xfoil_path = xfoil_path
        self.logger = get_logger(verbose=verbose)

    def generate_naca_polar(
        self,
        naca_code: str,
        reynolds_numbers: List[float],
        alpha_range: Tuple[float, float] = (-10.0, 20.0),
        alpha_step: float = 0.5,
        mach: float = 0.0,
        n_iter: int = 200
    ) -> AirfoilPolars:
        """
        Generate polars for a NACA 4-digit airfoil.

        Args:
            naca_code: NACA 4-digit code (e.g., "0012")
            reynolds_numbers: List of Reynolds numbers to analyze
            alpha_range: (min, max) angle of attack range [deg]
            alpha_step: Alpha increment [deg]
            mach: Mach number
            n_iter: Maximum iterations for convergence

        Returns:
            AirfoilPolars with data for all Reynolds numbers
        """
        self.logger.info(f"Generating NACA {naca_code} polars...")
        self.logger.indent()

        polars = []

        for re in reynolds_numbers:
            self.logger.debug(f"Reynolds = {re:.2e}")

            polar = self._run_xfoil_naca(
                naca_code=naca_code,
                reynolds=re,
                alpha_range=alpha_range,
                alpha_step=alpha_step,
                mach=mach,
                n_iter=n_iter
            )

            if polar is not None:
                polars.append(polar)
                self.logger.success(f"Generated polar with {len(polar.alpha)} points")
            else:
                self.logger.warning(f"Failed to generate polar at Re={re:.2e}")

        self.logger.dedent()
        self.logger.success(f"Generated {len(polars)} polars")

        return AirfoilPolars(
            airfoil_name=f"NACA {naca_code}",
            polars=polars
        )

    def generate_airfoil_polar(
        self,
        airfoil_file: str,
        reynolds_numbers: List[float],
        alpha_range: Tuple[float, float] = (-10.0, 20.0),
        alpha_step: float = 0.5,
        mach: float = 0.0,
        n_iter: int = 200
    ) -> AirfoilPolars:
        """
        Generate polars for an airfoil from a coordinate file.

        Args:
            airfoil_file: Path to airfoil .dat file (Selig or Lednicer format)
            reynolds_numbers: List of Reynolds numbers to analyze
            alpha_range: (min, max) alpha range in degrees
            alpha_step: Alpha increment in degrees
            mach: Mach number
            n_iter: Maximum iterations for convergence

        Returns:
            AirfoilPolars with data for all Reynolds numbers
        """
        from pathlib import Path

        airfoil_path = Path(airfoil_file)
        if not airfoil_path.exists():
            raise FileNotFoundError(f"Airfoil file not found: {airfoil_file}")

        # Extract airfoil name from file (first line)
        with open(airfoil_path, 'r') as f:
            airfoil_name = f.readline().strip()

        self.logger.info(f"Generating {airfoil_name} polars from {airfoil_path.name}...")

        polars = []
        for re in reynolds_numbers:
            self.logger.info(f"  Computing polar at Re = {re:.2e}...")

            polar = self._run_xfoil_file(
                airfoil_file=str(airfoil_path),
                reynolds=re,
                alpha_range=alpha_range,
                alpha_step=alpha_step,
                mach=mach,
                n_iter=n_iter
            )

            if polar:
                polars.append(polar)
                self.logger.info(f"    OK Converged for {len(polar.alpha)} points")
            else:
                self.logger.warning(f"    X Failed to converge at Re = {re:.2e}")

        return AirfoilPolars(
            airfoil_name=airfoil_name,
            polars=polars
        )

    def _run_xfoil_naca(
        self,
        naca_code: str,
        reynolds: float,
        alpha_range: Tuple[float, float],
        alpha_step: float,
        mach: float,
        n_iter: int
    ) -> Optional[PolarData]:
        """
        Run XFOIL for a NACA airfoil at a single Reynolds number.

        Args:
            naca_code: NACA 4-digit code
            reynolds: Reynolds number
            alpha_range: (min, max) alpha range
            alpha_step: Alpha increment
            mach: Mach number
            n_iter: Max iterations

        Returns:
            PolarData if successful, None if failed
        """
        # Create temporary directory for XFOIL output
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            polar_file = tmpdir_path / "polar.txt"

            # Create XFOIL command file
            commands = self._create_xfoil_commands(
                naca_code=naca_code,
                reynolds=reynolds,
                alpha_range=alpha_range,
                alpha_step=alpha_step,
                mach=mach,
                n_iter=n_iter,
                output_file=polar_file
            )

            # Run XFOIL
            try:
                result = subprocess.run(
                    [self.xfoil_path],
                    input=commands,
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                if result.returncode != 0:
                    self.logger.debug(f"XFOIL returned code {result.returncode}")

                # Parse polar data
                if polar_file.exists():
                    return self._parse_polar_file(polar_file, reynolds, mach)
                else:
                    return None

            except subprocess.TimeoutExpired:
                self.logger.warning("XFOIL timeout")
                return None
            except FileNotFoundError:
                self.logger.error(f"XFOIL not found at: {self.xfoil_path}")
                return None

    def _run_xfoil_file(
        self,
        airfoil_file: str,
        reynolds: float,
        alpha_range: Tuple[float, float],
        alpha_step: float,
        mach: float,
        n_iter: int
    ) -> Optional[PolarData]:
        """
        Run XFOIL for an airfoil from a coordinate file.

        Args:
            airfoil_file: Path to airfoil .dat file
            reynolds: Reynolds number
            alpha_range: (min, max) alpha range
            alpha_step: Alpha increment
            mach: Mach number
            n_iter: Max iterations

        Returns:
            PolarData if successful, None if failed
        """
        # Create temporary directory for XFOIL output
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            polar_file = tmpdir_path / "polar.txt"

            # Copy airfoil to temp directory (XFOIL can't handle spaces in paths)
            import shutil
            temp_airfoil = tmpdir_path / "airfoil.dat"
            shutil.copy2(airfoil_file, temp_airfoil)

            # Create XFOIL command file
            commands = self._create_xfoil_commands_file(
                airfoil_file=str(temp_airfoil),
                reynolds=reynolds,
                alpha_range=alpha_range,
                alpha_step=alpha_step,
                mach=mach,
                n_iter=n_iter,
                output_file=polar_file
            )

            # Run XFOIL
            try:
                result = subprocess.run(
                    [self.xfoil_path],
                    input=commands,
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                if result.returncode != 0:
                    self.logger.debug(f"XFOIL returned code {result.returncode}")

                # Parse polar data
                if polar_file.exists():
                    return self._parse_polar_file(polar_file, reynolds, mach)
                else:
                    return None

            except subprocess.TimeoutExpired:
                self.logger.warning("XFOIL timeout")
                return None
            except FileNotFoundError:
                self.logger.error(f"XFOIL not found at: {self.xfoil_path}")
                return None

    def _create_xfoil_commands(
        self,
        naca_code: str,
        reynolds: float,
        alpha_range: Tuple[float, float],
        alpha_step: float,
        mach: float,
        n_iter: int,
        output_file: Path
    ) -> str:
        """
        Create XFOIL command string for batch execution.

        Args:
            naca_code: NACA 4-digit code
            reynolds: Reynolds number
            alpha_range: (min, max) alpha
            alpha_step: Alpha increment
            mach: Mach number
            n_iter: Max iterations
            output_file: Path to output polar file

        Returns:
            XFOIL command string
        """
        commands = [
            f"NACA {naca_code}",  # Load NACA airfoil
            "OPER",  # Enter OPER menu
            f"ITER {n_iter}",  # Set max iterations
            f"VISC {reynolds}",  # Set Reynolds number
            f"MACH {mach}",  # Set Mach number
            "PACC",  # Accumulate polar
            str(output_file),  # Polar save file
            "",  # No dump file
            f"ASEQ {alpha_range[0]} {alpha_range[1]} {alpha_step}",  # Alpha sequence
            "PACC",  # Close polar accumulation
            "",  # Exit OPER
            "QUIT"  # Exit XFOIL
        ]

        return "\n".join(commands) + "\n"

    def _create_xfoil_commands_file(
        self,
        airfoil_file: str,
        reynolds: float,
        alpha_range: Tuple[float, float],
        alpha_step: float,
        mach: float,
        n_iter: int,
        output_file: Path
    ) -> str:
        """
        Create XFOIL command string for batch execution with airfoil file.

        Args:
            airfoil_file: Path to airfoil coordinate file
            reynolds: Reynolds number
            alpha_range: (min, max) alpha
            alpha_step: Alpha increment
            mach: Mach number
            n_iter: Max iterations
            output_file: Path to output polar file

        Returns:
            XFOIL command string
        """
        # Convert to forward slashes for XFOIL (works on Windows too)
        airfoil_file_unix = str(Path(airfoil_file).as_posix())

        commands = [
            f"LOAD {airfoil_file_unix}",  # Load airfoil from file
            "PPAR",  # Panel parameters for better convergence
            "N 200",  # Use 200 panels (more resolution)
            "T 1.0",  # Panel bunching parameter
            "",  # Accept
            "",  # Exit PPAR
            "OPER",  # Enter OPER menu
            f"ITER {n_iter}",  # Set max iterations
            f"VISC {reynolds}",  # Set Reynolds number
            f"MACH {mach}",  # Set Mach number
            "VPAR",  # Viscous parameters
            "N 9.0",  # Amplification factor (default 9.0, lower = more sensitive to transition)
            "",  # Exit VPAR
            "PACC",  # Accumulate polar
            str(output_file),  # Polar save file
            "",  # No dump file
            f"ASEQ {alpha_range[0]} {alpha_range[1]} {alpha_step}",  # Alpha sequence
            "PACC",  # Close polar accumulation
            "",  # Exit OPER
            "QUIT"  # Exit XFOIL
        ]

        return "\n".join(commands) + "\n"

    def _parse_polar_file(
        self,
        polar_file: Path,
        reynolds: float,
        mach: float
    ) -> Optional[PolarData]:
        """
        Parse XFOIL polar output file.

        XFOIL polar format (after header):
        alpha    CL        CD       CDp       CM     Top_Xtr  Bot_Xtr

        Args:
            polar_file: Path to polar file
            reynolds: Reynolds number
            mach: Mach number

        Returns:
            PolarData if parsing successful, None otherwise
        """
        try:
            # Read polar file, skipping header lines
            with open(polar_file, 'r') as f:
                lines = f.readlines()

            # Find where data starts (after "---" separator)
            data_start = 0
            for i, line in enumerate(lines):
                if '---' in line:
                    data_start = i + 1
                    break

            if data_start == 0:
                return None

            # Parse data
            data_lines = lines[data_start:]
            alpha_list = []
            cl_list = []
            cd_list = []
            cm_list = []

            for line in data_lines:
                parts = line.split()
                if len(parts) >= 7:
                    try:
                        alpha_list.append(float(parts[0]))
                        cl_list.append(float(parts[1]))
                        cd_list.append(float(parts[2]))
                        cm_list.append(float(parts[4]))
                    except ValueError:
                        continue

            if len(alpha_list) == 0:
                return None

            return PolarData(
                reynolds=reynolds,
                mach=mach,
                alpha=np.array(alpha_list),
                cl=np.array(cl_list),
                cd=np.array(cd_list),
                cm=np.array(cm_list)
            )

        except Exception as e:
            self.logger.debug(f"Error parsing polar file: {e}")
            return None

    def save_polars(
        self,
        polars: AirfoilPolars,
        output_dir: Path
    ) -> None:
        """
        Save polar data to CSV files.

        Args:
            polars: AirfoilPolars to save
            output_dir: Directory to save polar files
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"Saving polars to: {output_dir}")

        for polar in polars.polars:
            filename = f"polar_re{polar.reynolds:.2e}_m{polar.mach:.2f}.csv"
            filepath = output_dir / filename

            df = pd.DataFrame({
                'alpha': polar.alpha,
                'CL': polar.cl,
                'CD': polar.cd,
                'CM': polar.cm
            })

            df.to_csv(filepath, index=False)
            self.logger.debug(f"Saved: {filename}")

        self.logger.success(f"Saved {len(polars.polars)} polar files")
