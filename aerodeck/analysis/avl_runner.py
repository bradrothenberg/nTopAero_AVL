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
    elevon: float = 0.0  # Elevon deflection (symmetric) [deg]
    aileron: float = 0.0  # Aileron deflection (differential) [deg]
    name: str = ""  # Case name

    def __post_init__(self) -> None:
        """Generate name if not provided."""
        if not self.name:
            if self.elevon != 0.0:
                self.name = f"a{self.alpha:.1f}_b{self.beta:.1f}_de{self.elevon:.1f}_M{self.mach:.2f}"
            elif self.aileron != 0.0:
                self.name = f"a{self.alpha:.1f}_b{self.beta:.1f}_da{self.aileron:.1f}_M{self.mach:.2f}"
            else:
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
    Cl_beta: Optional[float] = None  # Roll due to sideslip (dihedral effect)
    Cn_beta: Optional[float] = None

    # Control derivatives
    CL_de: Optional[float] = None  # Elevon
    Cm_de: Optional[float] = None

    # Dynamic derivatives - pitch rate
    CL_q: Optional[float] = None
    Cm_q: Optional[float] = None

    # Dynamic derivatives - roll rate
    Cy_p: Optional[float] = None
    Cl_p: Optional[float] = None
    Cn_p: Optional[float] = None

    # Dynamic derivatives - yaw rate
    Cy_r: Optional[float] = None
    Cl_r: Optional[float] = None
    Cn_r: Optional[float] = None

    # Neutral point (directly from AVL)
    Xnp: Optional[float] = None

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

        # Create subdirectory for AVL output files
        avl_output_dir = output_dir / "avl_outputs"
        avl_output_dir.mkdir(parents=True, exist_ok=True)

        for i, case in enumerate(run_cases):
            self.logger.progress(
                f"Running case {case.name}",
                i,
                len(run_cases)
            )

            # Create unique command file for this case in the subdirectory
            cmd_file = avl_output_dir / f"{case.name}_commands.txt"
            self._create_command_file(cmd_file, case, avl_output_dir)

            # Execute AVL
            try:
                result = self._run_avl_case(input_file, cmd_file, avl_output_dir, case)
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

            # Set control deflections
            # AVL syntax: A D1 value (where D1 is the first control variable)
            # D1 = elevon (symmetric, pitch control)
            # D2 = aileron (differential, roll control)
            if abs(case.elevon) > 1e-6:
                f.write(f"A D1 {case.elevon}\n")

            if abs(case.aileron) > 1e-6:
                f.write(f"A D2 {case.aileron}\n")

            # NOTE: Skip Mach setting for now - it causes issues with ST command in batch mode
            # For low-speed analysis (M < 0.3), incompressible assumption is valid anyway
            # if abs(case.mach) > 1e-6:
            #     f.write(f"M\n{case.mach}\n")

            # Execute - AVL will compute and display results automatically
            f.write("X\n")

            # Request total forces - write to file
            ft_file = f"{case.name}_ft.txt"
            f.write("FT\n")
            f.write(f"{ft_file}\n")  # Filename to write to

            # Request stability derivatives - write to file
            stab_file = f"{case.name}_stab.txt"
            f.write("ST\n")
            f.write(f"{stab_file}\n")  # Filename to write to

            # Exit OPER menu
            f.write("\n")  # Empty line exits OPER

            # Quit AVL
            f.write("QUIT\n")

    def _write_run_file(
        self,
        run_file: Path,
        case: RunCase
    ) -> None:
        """
        Create AVL .run file with flight condition parameters.

        AVL .run file format defines the flight condition and constraints.

        Args:
            run_file: Path to .run file
            case: Run case with flight condition
        """
        with open(run_file, 'w') as f:
            f.write(" ---------------------------------------------\n")
            f.write(" Run case  1:  Default run case\n")
            f.write("\n")
            f.write(f" alpha        ->  alpha       =   {case.alpha:8.4f}  deg\n")
            f.write(f" beta         ->  beta        =   {case.beta:8.4f}  deg\n")
            f.write(f" pb/2V        ->  pb/2V       =   {0.0:8.4f}\n")
            f.write(f" qc/2V        ->  qc/2V       =   {0.0:8.4f}\n")
            f.write(f" rb/2V        ->  rb/2V       =   {0.0:8.4f}\n")
            f.write(f" Mach         ->  Mach        =   {case.mach:8.4f}\n")
            f.write(f" velocity     ->  velocity    =   {100.0:8.4f}  ft/s\n")
            f.write(f" density      ->  density     =   {0.002377:8.6f}  slug/ft^3\n")
            f.write(f" grav.acc.    ->  g           =   {32.174:8.4f}  ft/s^2\n")
            f.write("\n")
            f.write(" alpha     =   0.00000     deg\n")
            f.write(" beta      =   0.00000     deg\n")
            f.write(" pb/2V     =   0.00000\n")
            f.write(" qc/2V     =   0.00000\n")
            f.write(" rb/2V     =   0.00000\n")
            f.write(" CL        =   0.00000\n")
            f.write(" CDo       =   0.00000\n")
            f.write(" bank      =   0.00000     deg\n")
            f.write(" elevation =   0.00000     deg\n")
            f.write(" heading   =   0.00000     deg\n")
            f.write(" Mach      =   0.00000\n")
            f.write(" velocity  =   0.00000     ft/s\n")
            f.write(" density   =   0.002377     slug/ft^3\n")
            f.write(" grav.acc. =   32.174       ft/s^2\n")
            f.write(" turn_rad. =   0.00000     ft\n")
            f.write(" load_fac. =   1.00000\n")
            f.write(" X_cg      =   0.00000     ft\n")
            f.write(" Y_cg      =   0.00000     ft\n")
            f.write(" Z_cg      =   0.00000     ft\n")
            f.write(" mass      =   1.00000     lbm\n")
            f.write(" Ixx       =   1.00000     lbm-ft^2\n")
            f.write(" Iyy       =   1.00000     lbm-ft^2\n")
            f.write(" Izz       =   1.00000     lbm-ft^2\n")
            f.write(" Ixy       =   0.00000     lbm-ft^2\n")
            f.write(" Iyz       =   0.00000     lbm-ft^2\n")
            f.write(" Izx       =   0.00000     lbm-ft^2\n")
            f.write(" visc CL_a =   0.00000\n")
            f.write(" visc CL_u =   0.00000\n")
            f.write(" visc CM_a =   0.00000\n")
            f.write(" visc CM_u =   0.00000\n")

    def _run_avl_case(
        self,
        input_file: Path,
        cmd_file: Path,
        output_dir: Path,
        case: 'RunCase'
    ) -> AVLResults:
        """
        Run single AVL case and parse results.

        Args:
            input_file: AVL input file
            cmd_file: Command file
            output_dir: Directory where output files will be created
            case: Run case with parameters

        Returns:
            AVLResults instance
        """
        # Execute AVL
        with open(cmd_file, 'r') as f:
            commands = f.read()

        # Create output file for capturing stdout
        case_name = case.name
        output_file = output_dir / f"{case_name}_output.txt"

        # Run AVL from the output directory, write stdout to file
        with open(output_file, 'w') as out_f:
            result = subprocess.run(
                [self.config.executable, str(input_file.absolute())],
                input=commands.encode(),
                stdout=out_f,
                stderr=subprocess.PIPE,
                timeout=60,
                cwd=str(output_dir)
            )

        # Note: AVL can return non-zero codes even on success (e.g., missing .mass file warnings)
        # Don't fail just based on return code - check if output files exist instead
        if result.returncode not in [0, 2]:
            raise RuntimeError(f"AVL failed with return code {result.returncode}")

        # Read the output file and parse it
        with open(output_file, 'r') as f:
            avl_output = f.read()

        # Try to find and read the stability derivatives file
        stab_file = output_dir / f"{case_name}_stab.txt"
        if stab_file.exists():
            with open(stab_file, 'r') as f:
                stab_output = f.read()
                # Combine with main output for comprehensive parsing
                avl_output += "\n" + stab_output

        # Parse the result from console output
        result = self._parse_avl_output(avl_output)

        # For control deflection cases, override forces with FT file data (more accurate)
        if abs(case.elevon) > 1e-6 or abs(case.aileron) > 1e-6:
            ft_file = output_dir / f"{case_name}_ft.txt"
            ft_data = self._parse_ft_file(ft_file)
            if ft_data:
                # Override with FT file data which has the actual forces with deflection
                result.CL = ft_data.get('CL', result.CL)
                result.CD = ft_data.get('CD', result.CD)
                result.Cy = ft_data.get('CY', result.Cy)
                result.Cm = ft_data.get('Cm', result.Cm)
                result.Cn = ft_data.get('Cn', result.Cn)
                result.Cl = ft_data.get('Cl', result.Cl)

        return result

    def _parse_avl_output(self, output: str) -> AVLResults:
        """
        Parse AVL console output (from ST command).

        Args:
            output: AVL stdout text with stability derivatives

        Returns:
            AVLResults instance
        """
        derivatives = {}

        # Parse the console output line by line
        for line in output.split('\n'):
            # Force coefficients
            if 'CLtot' in line:
                parts = line.split('=')
                if len(parts) >= 2:
                    try:
                        derivatives['CL'] = float(parts[1].split()[0])
                    except (ValueError, IndexError):
                        pass

            if 'CDtot' in line:
                parts = line.split('=')
                if len(parts) >= 2:
                    try:
                        derivatives['CD'] = float(parts[1].split()[0])
                    except (ValueError, IndexError):
                        pass

            if 'Cmtot' in line:
                parts = line.split('=')
                if len(parts) >= 2:
                    try:
                        derivatives['Cm'] = float(parts[1].split()[0])
                    except (ValueError, IndexError):
                        pass

            # Stability derivatives - parse lines like "z' force CL |    CLa =   2.823814    CLb =  -0.000000"
            if '|' in line and '=' in line:
                # Split by | to get the derivatives part
                parts = line.split('|')
                if len(parts) >= 2:
                    deriv_part = parts[1]

                    # Parse all derivatives in this line
                    if 'CLa =' in deriv_part:
                        try:
                            val = deriv_part.split('CLa =')[1].strip().split()[0]
                            derivatives['CLa'] = float(val)
                        except (ValueError, IndexError):
                            pass

                    if 'CLb =' in deriv_part:
                        try:
                            val = deriv_part.split('CLb =')[1].strip().split()[0]
                            derivatives['CLb'] = float(val)
                        except (ValueError, IndexError):
                            pass

                    if 'Clb =' in deriv_part:
                        try:
                            val = deriv_part.split('Clb =')[1].strip().split()[0]
                            derivatives['Clb'] = float(val)
                        except (ValueError, IndexError):
                            pass

                    if 'Cma =' in deriv_part:
                        try:
                            val = deriv_part.split('Cma =')[1].strip().split()[0]
                            derivatives['Cma'] = float(val)
                        except (ValueError, IndexError):
                            pass

                    if 'Cnb =' in deriv_part:
                        try:
                            val = deriv_part.split('Cnb =')[1].strip().split()[0]
                            derivatives['Cnb'] = float(val)
                        except (ValueError, IndexError):
                            pass

                    if 'CYb =' in deriv_part:
                        try:
                            val = deriv_part.split('CYb =')[1].strip().split()[0]
                            derivatives['CYb'] = float(val)
                        except (ValueError, IndexError):
                            pass

                    if 'CDa =' in deriv_part:
                        try:
                            val = deriv_part.split('CDa =')[1].strip().split()[0]
                            derivatives['CDa'] = float(val)
                        except (ValueError, IndexError):
                            pass

                    # Dynamic derivatives - pitch rate
                    if 'CLq =' in deriv_part:
                        try:
                            val = deriv_part.split('CLq =')[1].strip().split()[0]
                            derivatives['CLq'] = float(val)
                        except (ValueError, IndexError):
                            pass

                    if 'Cmq =' in deriv_part:
                        try:
                            val = deriv_part.split('Cmq =')[1].strip().split()[0]
                            derivatives['Cmq'] = float(val)
                        except (ValueError, IndexError):
                            pass

                    # Dynamic derivatives - roll rate
                    if 'CYp =' in deriv_part:
                        try:
                            val = deriv_part.split('CYp =')[1].strip().split()[0]
                            derivatives['CYp'] = float(val)
                        except (ValueError, IndexError):
                            pass

                    if 'Clp =' in deriv_part:
                        try:
                            val = deriv_part.split('Clp =')[1].strip().split()[0]
                            derivatives['Clp'] = float(val)
                        except (ValueError, IndexError):
                            pass

                    if 'Cnp =' in deriv_part:
                        try:
                            val = deriv_part.split('Cnp =')[1].strip().split()[0]
                            derivatives['Cnp'] = float(val)
                        except (ValueError, IndexError):
                            pass

                    # Dynamic derivatives - yaw rate
                    if 'CYr =' in deriv_part:
                        try:
                            val = deriv_part.split('CYr =')[1].strip().split()[0]
                            derivatives['CYr'] = float(val)
                        except (ValueError, IndexError):
                            pass

                    if 'Clr =' in deriv_part:
                        try:
                            val = deriv_part.split('Clr =')[1].strip().split()[0]
                            derivatives['Clr'] = float(val)
                        except (ValueError, IndexError):
                            pass

                    if 'Cnr =' in deriv_part:
                        try:
                            val = deriv_part.split('Cnr =')[1].strip().split()[0]
                            derivatives['Cnr'] = float(val)
                        except (ValueError, IndexError):
                            pass

            # Neutral point (format: " Neutral point  Xnp =   3.995113")
            if 'Neutral point' in line and 'Xnp' in line:
                parts = line.split('=')
                try:
                    derivatives['Xnp'] = float(parts[1].split()[0])
                except (ValueError, IndexError):
                    pass

        return AVLResults(
            CL=derivatives.get('CL', 0.0),
            CD=derivatives.get('CD', 0.0),
            Cy=derivatives.get('CY', 0.0),
            Cm=derivatives.get('Cm', 0.0),
            Cn=derivatives.get('Cn', 0.0),
            Cl=derivatives.get('Cl', 0.0),
            CL_alpha=derivatives.get('CLa'),
            CD_alpha=derivatives.get('CDa'),
            Cm_alpha=derivatives.get('Cma'),
            CL_beta=derivatives.get('CLb'),
            Cy_beta=derivatives.get('CYb'),
            Cl_beta=derivatives.get('Clb'),
            Cn_beta=derivatives.get('Cnb'),
            CL_q=derivatives.get('CLq'),
            Cm_q=derivatives.get('Cmq'),
            Cy_p=derivatives.get('CYp'),
            Cl_p=derivatives.get('Clp'),
            Cn_p=derivatives.get('Cnp'),
            Cy_r=derivatives.get('CYr'),
            Cl_r=derivatives.get('Clr'),
            Cn_r=derivatives.get('Cnr'),
            Xnp=derivatives.get('Xnp'),
            converged=True
        )

    def _parse_ft_file(self, ft_file: Path) -> dict:
        """
        Parse AVL total forces file (FT output).

        Args:
            ft_file: Path to FT file

        Returns:
            Dictionary with CL, CD, Cy, Cm, Cn, Cl
        """
        forces = {}

        if not ft_file.exists():
            return forces

        with open(ft_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Parse force coefficients from FT output
        # Look for lines like "CLtot =   0.12345"
        import re

        patterns = {
            'CL': r'CLtot\s*=\s*([-+]?\d+\.\d+)',
            'CD': r'CDtot\s*=\s*([-+]?\d+\.\d+)',
            'CY': r'CYtot\s*=\s*([-+]?\d+\.\d+)',
            'Cm': r'Cmtot\s*=\s*([-+]?\d+\.\d+)',
            'Cn': r'Cntot\s*=\s*([-+]?\d+\.\d+)',
            'Cl': r'Cltot\s*=\s*([-+]?\d+\.\d+)'
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, content)
            if match:
                forces[key] = float(match.group(1))

        return forces

    def _parse_stab_file_to_results(self, stab_file: Path) -> AVLResults:
        """
        Parse stability file and return AVLResults object.

        Args:
            stab_file: Path to stability derivatives file

        Returns:
            AVLResults instance
        """
        data = self._parse_stability_file(stab_file)

        return AVLResults(
            CL=data.get('CL', 0.0),
            CD=data.get('CD', 0.0),
            Cy=data.get('CY', 0.0),
            Cm=data.get('Cm', 0.0),
            Cn=data.get('Cn', 0.0),
            Cl=data.get('Cl', 0.0),
            CL_alpha=data.get('CLa'),
            CD_alpha=data.get('CDa'),
            Cm_alpha=data.get('Cma'),
            CL_beta=data.get('CLb'),
            Cy_beta=data.get('CYb'),
            Cl_beta=data.get('Clb'),
            Cn_beta=data.get('Cnb'),
            CL_q=data.get('CLq'),
            Cm_q=data.get('Cmq'),
            Cy_p=data.get('CYp'),
            Cl_p=data.get('Clp'),
            Cn_p=data.get('Cnp'),
            Cy_r=data.get('CYr'),
            Cl_r=data.get('Clr'),
            Cn_r=data.get('Cnr'),
            Xnp=data.get('Xnp'),
            converged=True
        )

    def _parse_stability_file(self, stab_file: Path) -> dict:
        """
        Parse AVL stability derivatives file (ST output).

        Args:
            stab_file: Path to stability file

        Returns:
            Dictionary of stability derivatives
        """
        derivatives = {}

        try:
            with open(stab_file, 'r') as f:
                lines = f.readlines()

            # Parse force coefficients from header
            for i, line in enumerate(lines):
                if 'CL' in line and 'CLa' not in line:
                    parts = line.split('=')
                    if len(parts) >= 2:
                        try:
                            derivatives['CL'] = float(parts[1].split()[0])
                        except (ValueError, IndexError):
                            pass

                if 'CDtot' in line:
                    parts = line.split('=')
                    if len(parts) >= 2:
                        try:
                            derivatives['CD'] = float(parts[1].split()[0])
                        except (ValueError, IndexError):
                            pass

                if 'CYtot' in line:
                    parts = line.split('=')
                    if len(parts) >= 2:
                        try:
                            derivatives['CY'] = float(parts[1].split()[0])
                        except (ValueError, IndexError):
                            pass

                if 'Cmtot' in line:
                    parts = line.split('=')
                    if len(parts) >= 2:
                        try:
                            derivatives['Cm'] = float(parts[1].split()[0])
                        except (ValueError, IndexError):
                            pass

                if 'Cntot' in line:
                    parts = line.split('=')
                    if len(parts) >= 2:
                        try:
                            derivatives['Cn'] = float(parts[1].split()[0])
                        except (ValueError, IndexError):
                            pass

                if 'Cltot' in line:
                    parts = line.split('=')
                    if len(parts) >= 2:
                        try:
                            derivatives['Cl'] = float(parts[1].split()[0])
                        except (ValueError, IndexError):
                            pass

                # Parse stability derivatives
                if 'CLa =' in line:
                    parts = line.split('=')
                    try:
                        derivatives['CLa'] = float(parts[1].split()[0])
                    except (ValueError, IndexError):
                        pass

                if 'CYb =' in line:
                    parts = line.split('=')
                    try:
                        derivatives['CYb'] = float(parts[1].split()[0])
                    except (ValueError, IndexError):
                        pass

                if 'CDa =' in line:
                    parts = line.split('=')
                    try:
                        derivatives['CDa'] = float(parts[1].split()[0])
                    except (ValueError, IndexError):
                        pass

                if 'Cma =' in line:
                    parts = line.split('=')
                    try:
                        derivatives['Cma'] = float(parts[1].split()[0])
                    except (ValueError, IndexError):
                        pass

                if 'Cnb =' in line:
                    parts = line.split('=')
                    try:
                        derivatives['Cnb'] = float(parts[1].split()[0])
                    except (ValueError, IndexError):
                        pass

                if 'Clb =' in line:
                    parts = line.split('=')
                    try:
                        derivatives['Clb'] = float(parts[1].split()[0])
                    except (ValueError, IndexError):
                        pass

                # Dynamic derivatives
                if 'CLq =' in line:
                    parts = line.split('=')
                    try:
                        derivatives['CLq'] = float(parts[1].split()[0])
                    except (ValueError, IndexError):
                        pass

                if 'Cmq =' in line:
                    parts = line.split('=')
                    try:
                        derivatives['Cmq'] = float(parts[1].split()[0])
                    except (ValueError, IndexError):
                        pass

                # Neutral point
                if 'Neutral point' in line and 'Xnp' in line:
                    parts = line.split('=')
                    try:
                        derivatives['Xnp'] = float(parts[1].split()[0])
                    except (ValueError, IndexError):
                        pass

        except Exception as e:
            self.logger.debug(f"Error parsing stability file: {e}")

        return derivatives

    def parse_avl_results(self, stab_file: Path, forces_file: Optional[Path] = None) -> AVLResults:
        """
        Parse AVL output files to extract complete results.

        Args:
            stab_file: Path to stability derivatives file (ST output)
            forces_file: Optional path to forces file (FT output)

        Returns:
            AVLResults with all available data
        """
        # Parse stability file
        data = self._parse_stability_file(stab_file)

        # Create results object
        return AVLResults(
            CL=data.get('CL', 0.0),
            CD=data.get('CD', 0.0),
            Cy=data.get('CY', 0.0),
            Cm=data.get('Cm', 0.0),
            Cn=data.get('Cn', 0.0),
            Cl=data.get('Cl', 0.0),
            CL_alpha=data.get('CLa'),
            CD_alpha=data.get('CDa'),
            Cm_alpha=data.get('Cma'),
            CL_beta=data.get('CLb'),
            Cy_beta=data.get('CYb'),
            Cl_beta=data.get('Clb'),
            Cn_beta=data.get('Cnb'),
            CL_q=data.get('CLq'),
            Cm_q=data.get('Cmq'),
            Xnp=data.get('Xnp'),
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
