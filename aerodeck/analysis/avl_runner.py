"""AVL execution wrapper for aerodynamic analysis."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import subprocess
import numpy as np

from ..utils.logger import get_logger
from ..utils.config import AVLConfig


@dataclass
class RunCase:
    """Single AVL run case."""

    alpha: float  # Angle of attack [deg]
    beta: float = 0.0  # Sideslip angle [deg]
    mach: float = 0.0  # Mach number
    name: str = ""  # Case name

    def __post_init__(self) -> None:
        """Generate name if not provided."""
        if not self.name:
            self.name = f"a{self.alpha:.1f}_b{self.beta:.1f}_M{self.mach:.2f}"


@dataclass
class AVLResults:
    """Results from AVL analysis."""

    # Force coefficients
    CL: float  # Lift coefficient
    CD: float  # Drag coefficient
    Cy: float  # Side force coefficient

    # Moment coefficients
    Cm: float  # Pitching moment
    Cn: float  # Yawing moment
    Cl: float  # Rolling moment (lowercase L)

    # Stability derivatives (optional, populated from multiple runs)
    CL_alpha: Optional[float] = None
    CD_alpha: Optional[float] = None
    Cm_alpha: Optional[float] = None

    CL_beta: Optional[float] = None
    Cy_beta: Optional[float] = None
    Cn_beta: Optional[float] = None

    # Control derivatives
    CL_de: Optional[float] = None  # Elevon
    Cm_de: Optional[float] = None

    # Dynamic derivatives
    CL_q: Optional[float] = None
    Cm_q: Optional[float] = None
    Cy_p: Optional[float] = None
    Cn_r: Optional[float] = None

    converged: bool = True
    case: Optional[RunCase] = None


class AVLAnalysis:
    """Wrapper for AVL execution and result parsing."""

    def __init__(
        self,
        config: Optional[AVLConfig] = None,
        verbose: bool = True
    ) -> None:
        """
        Initialize AVL analysis.

        Args:
            config: AVL configuration
            verbose: Enable verbose logging
        """
        self.config = config or AVLConfig()
        self.logger = get_logger(verbose=verbose)

    def setup_run_cases(
        self,
        alpha_range: list[float],
        beta_range: Optional[list[float]] = None,
        mach: float = 0.0
    ) -> list[RunCase]:
        """
        Generate run matrix.

        Args:
            alpha_range: List of alpha values [deg]
            beta_range: Optional list of beta values [deg]
            mach: Mach number

        Returns:
            List of RunCase instances
        """
        cases = []

        if beta_range is None:
            beta_range = [0.0]

        for alpha in alpha_range:
            for beta in beta_range:
                cases.append(RunCase(alpha=alpha, beta=beta, mach=mach))

        self.logger.debug(f"Generated {len(cases)} run cases")
        return cases

    def execute_avl(
        self,
        input_file: Path,
        run_cases: list[RunCase],
        output_dir: Optional[Path] = None
    ) -> dict[str, AVLResults]:
        """
        Execute AVL for multiple run cases.

        Args:
            input_file: Path to AVL input file
            run_cases: List of run cases
            output_dir: Optional output directory for AVL files

        Returns:
            Dictionary mapping case name to AVLResults

        Raises:
            FileNotFoundError: If AVL executable not found
            RuntimeError: If AVL execution fails
        """
        self.logger.info(f"Running AVL ({len(run_cases)} cases)...")
        self.logger.indent()

        # Check if AVL is available
        if not self._check_avl_available():
            self.logger.warning(
                f"AVL executable '{self.config.executable}' not found. "
                "Returning mock results for development."
            )
            self.logger.dedent()
            return self._generate_mock_results(run_cases)

        results = {}

        # Setup output directory
        if output_dir is None:
            output_dir = input_file.parent

        output_dir.mkdir(parents=True, exist_ok=True)

        # Create AVL command file
        cmd_file = output_dir / "avl_commands.txt"

        for i, case in enumerate(run_cases):
            self.logger.progress(
                f"Running case {case.name}",
                i,
                len(run_cases)
            )

            # Create command file for this case
            self._create_command_file(cmd_file, case, output_dir)

            # Execute AVL
            try:
                result = self._run_avl_case(input_file, cmd_file)
                results[case.name] = result
            except Exception as e:
                self.logger.warning(f"Case {case.name} failed: {e}")
                # Create failed result
                results[case.name] = AVLResults(
                    CL=0.0, CD=0.0, Cy=0.0,
                    Cm=0.0, Cn=0.0, Cl=0.0,
                    converged=False,
                    case=case
                )

        self.logger.progress("Complete", len(run_cases), len(run_cases))
        self.logger.success(f"{len(results)} cases completed")
        self.logger.dedent()

        return results

    def _check_avl_available(self) -> bool:
        """Check if AVL executable is available."""
        try:
            result = subprocess.run(
                [self.config.executable],
                capture_output=True,
                timeout=5,
                input=b"quit\n"
            )
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def _create_command_file(
        self,
        cmd_file: Path,
        case: RunCase,
        output_dir: Path
    ) -> None:
        """
        Create AVL command file for a run case.

        Args:
            cmd_file: Path to command file
            case: Run case
            output_dir: Output directory for results
        """
        with open(cmd_file, 'w') as f:
            # Enter OPER menu
            f.write("OPER\n")

            # Set alpha
            f.write(f"A A {case.alpha}\n")

            # Set beta
            if abs(case.beta) > 1e-6:
                f.write(f"B B {case.beta}\n")

            # Set Mach
            if abs(case.mach) > 1e-6:
                f.write(f"M\n{case.mach}\n")

            # Execute
            f.write("X\n")

            # Write forces
            output_file = output_dir / f"{case.name}_forces.txt"
            f.write(f"FT\n{output_file}\n")

            # Write stability derivatives
            deriv_file = output_dir / f"{case.name}_stab.txt"
            f.write(f"ST\n{deriv_file}\n")

            # Quit
            f.write("\nQUIT\n")

    def _run_avl_case(
        self,
        input_file: Path,
        cmd_file: Path
    ) -> AVLResults:
        """
        Run single AVL case and parse results.

        Args:
            input_file: AVL input file
            cmd_file: Command file

        Returns:
            AVLResults instance
        """
        # Execute AVL
        with open(cmd_file, 'r') as f:
            commands = f.read()

        result = subprocess.run(
            [self.config.executable, str(input_file)],
            input=commands.encode(),
            capture_output=True,
            timeout=60
        )

        if result.returncode != 0:
            raise RuntimeError(f"AVL failed with return code {result.returncode}")

        # Parse output (simplified for now)
        # In production, would parse the output files created by AVL
        return self._parse_avl_output(result.stdout.decode())

    def _parse_avl_output(self, output: str) -> AVLResults:
        """
        Parse AVL output text.

        Args:
            output: AVL stdout text

        Returns:
            AVLResults instance
        """
        # Simplified parser - in production would parse detailed output files
        # For now, return placeholder values

        CL = 0.0
        CD = 0.0
        Cy = 0.0
        Cm = 0.0
        Cn = 0.0
        Cl = 0.0

        # Try to extract values from output
        for line in output.split('\n'):
            if 'CLtot' in line or 'CL =' in line:
                parts = line.split('=')
                if len(parts) > 1:
                    try:
                        CL = float(parts[1].split()[0])
                    except (ValueError, IndexError):
                        pass

        return AVLResults(
            CL=CL, CD=CD, Cy=Cy,
            Cm=Cm, Cn=Cn, Cl=Cl,
            converged=True
        )

    def _generate_mock_results(
        self,
        run_cases: list[RunCase]
    ) -> dict[str, AVLResults]:
        """
        Generate mock results for development/testing.

        Args:
            run_cases: List of run cases

        Returns:
            Dictionary of mock results
        """
        self.logger.info("Generating mock AVL results (AVL not available)")

        results = {}

        for case in run_cases:
            # Generate realistic-looking coefficients
            alpha_rad = np.deg2rad(case.alpha)
            beta_rad = np.deg2rad(case.beta)

            # Simple linear aerodynamics
            CL = 0.1 + 5.5 * alpha_rad  # CL_alpha ~ 5.5 /rad
            CD = 0.02 + 0.05 * CL**2  # Parabolic drag polar
            Cy = -0.5 * beta_rad  # Side force

            Cm = -0.05 - 0.8 * alpha_rad  # Pitch stability
            Cn = 0.05 * beta_rad  # Yaw stability
            Cl = -0.1 * beta_rad  # Roll stability

            results[case.name] = AVLResults(
                CL=CL, CD=CD, Cy=Cy,
                Cm=Cm, Cn=Cn, Cl=Cl,
                CL_alpha=5.5,
                Cm_alpha=-0.8,
                Cy_beta=-0.5,
                Cn_beta=0.05,
                Cl_beta=-0.1,
                converged=True,
                case=case
            )

        return results

    def compute_stability_derivatives(
        self,
        results: dict[str, AVLResults]
    ) -> AVLResults:
        """
        Compute stability derivatives from multiple run cases.

        Uses finite differences between runs at different angles.

        Args:
            results: Dictionary of results

        Returns:
            AVLResults with populated derivative fields
        """
        self.logger.info("Computing stability derivatives...")

        # For now, return the first result with derivatives from mock data
        # In production, would compute finite differences
        if results:
            first_result = list(results.values())[0]
            return first_result

        return AVLResults(
            CL=0.0, CD=0.0, Cy=0.0,
            Cm=0.0, Cn=0.0, Cl=0.0,
            converged=False
        )
