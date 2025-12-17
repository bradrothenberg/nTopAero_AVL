"""Command-line interface for aerodeck generation."""

import sys
from pathlib import Path
from typing import Optional
import click
import numpy as np

from . import __version__
from .geometry.loader import GeometryLoader
from .geometry.validator import GeometryValidator
from .geometry.avl_translator import AVLGeometryWriter
from .analysis.avl_runner import AVLAnalysis
from .utils.logger import get_logger, set_verbose
from .utils.config import Config, load_config, create_default_config


@click.group()
@click.version_option(version=__version__)
def main() -> None:
    """nTop AeroDeck Generator - Automated aerodynamic deck generation."""
    pass


@main.command()
@click.argument('input_dir', type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    '--output-dir', '-o',
    type=click.Path(path_type=Path),
    default=None,
    help='Output directory (default: ./results)'
)
@click.option(
    '--config', '-c',
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help='Configuration file (YAML)'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Enable verbose output'
)
@click.option(
    '--quiet', '-q',
    is_flag=True,
    help='Quiet mode (minimal output)'
)
@click.option(
    '--validate-only',
    is_flag=True,
    help='Only validate geometry, do not run analysis'
)
@click.option(
    '--aircraft-name',
    default='group3-NQX-rev1',
    help='Aircraft name for reports'
)
@click.option(
    '--plot-trefftz',
    is_flag=True,
    help='Generate Trefftz plane plots during AVL analysis'
)
def generate(
    input_dir: Path,
    output_dir: Optional[Path],
    config: Optional[Path],
    verbose: bool,
    quiet: bool,
    validate_only: bool,
    aircraft_name: str,
    plot_trefftz: bool
) -> None:
    """
    Generate aerodynamic deck from nTop geometry export.

    INPUT_DIR: Directory containing nTop CSV files (mass.csv, LEpts.csv, TEpts.csv, etc.)
    """
    # Setup logging
    verbose_mode = verbose and not quiet
    set_verbose(verbose_mode)
    logger = get_logger()

    # Print banner
    logger.banner("nTop AeroDeck Generator", __version__)

    # Setup output directory
    if output_dir is None:
        output_dir = Path.cwd() / "results"

    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Input directory: {input_dir}")
    logger.info(f"Output directory: {output_dir}")

    # Load configuration
    cfg = load_config(config)
    if config:
        logger.info(f"Configuration: {config}")

    try:
        # Phase 1: Load geometry
        logger.section("Phase 1: Geometry Loading")
        loader = GeometryLoader(verbose=verbose_mode)
        geometry = loader.load_panel_data(input_dir)

        # Phase 2: Validate geometry
        logger.section("Phase 2: Geometry Validation")
        validator = GeometryValidator(config=cfg.validation, verbose=verbose_mode)
        validation_result = validator.validate(geometry)

        if not validation_result.is_valid:
            logger.error("Geometry validation failed")
            sys.exit(1)

        if validate_only:
            logger.summary("Validation complete")
            sys.exit(0)

        # Phase 3: Generate AVL input
        logger.section("Phase 3: AVL Input Generation")

        # Check for custom airfoil file
        airfoil_files = list(input_dir.glob("*.dat"))
        airfoil_file = airfoil_files[0] if airfoil_files else None
        if airfoil_file:
            logger.info(f"Using airfoil file: {airfoil_file.name}")

        avl_translator = AVLGeometryWriter(
            ref_config=cfg.reference,
            airfoil_file=airfoil_file,
            verbose=verbose_mode
        )

        avl_file = output_dir / f"{aircraft_name.replace(' ', '_').lower()}.avl"
        ref_geom = avl_translator.write_avl_input(
            geometry,
            avl_file,
            aircraft_name
        )

        # Phase 4: Run AVL analysis
        logger.section("Phase 4: AVL Analysis")
        if plot_trefftz:
            logger.info("Trefftz plane plots will be generated")
        avl_runner = AVLAnalysis(config=cfg.avl, verbose=verbose_mode, plot_trefftz=plot_trefftz)

        # Setup run cases
        alpha_values = cfg.get_alpha_values()
        beta_values = cfg.get_beta_values()
        mach = cfg.analysis.mach_numbers[0] if cfg.analysis.mach_numbers else 0.0

        run_cases = avl_runner.setup_run_cases(alpha_values, beta_values, mach)

        # Execute AVL
        results = avl_runner.execute_avl(avl_file, run_cases, output_dir)

        # Compute derivatives - find the case closest to trim (alpha=0, beta=0)
        trim_case = min(run_cases, key=lambda c: abs(c.alpha) + abs(c.beta))
        logger.debug(f"Using trim case: alpha={trim_case.alpha}°, beta={trim_case.beta}°")

        stability = results.get(trim_case.name)
        if stability is None:
            logger.warning(f"Trim case {trim_case.name} not found, using first case")
            stability = list(results.values())[0]

        # Keep reference to first case for backwards compatibility
        first_case_name = run_cases[0].name
        avl_results = results.get(first_case_name)

        if avl_results:
            logger.debug(f"AVL Results: CL_alpha={avl_results.CL_alpha}, Cm_alpha={avl_results.Cm_alpha}")
        else:
            logger.warning(f"No AVL results found for case {first_case_name}")

        # Phase 4.5: Control Derivative Analysis
        logger.section("Phase 4.5: Control Derivatives")

        # Run elevon (symmetric) deflection sweep at trim condition (alpha=0, beta=0)
        # Extended range to match control limits (±30°)
        control_deflections = [-30.0, -20.0, -10.0, 0.0, 10.0, 20.0, 30.0]  # degrees
        control_cases = []

        logger.info("Running elevon (pitch control) deflection sweep...")
        for delta in control_deflections:
            from .analysis.avl_runner import RunCase
            control_cases.append(RunCase(
                alpha=0.0,
                beta=0.0,
                elevon=delta,
                mach=mach
            ))

        logger.info(f"Running {len(control_cases)} elevon deflection cases...")
        elevon_results = avl_runner.execute_avl(avl_file, control_cases, output_dir)

        # Run aileron (differential) deflection sweep
        logger.info("Running aileron (roll control) deflection sweep...")
        aileron_cases = []
        for delta in control_deflections:
            from .analysis.avl_runner import RunCase
            aileron_cases.append(RunCase(
                alpha=0.0,
                beta=0.0,
                aileron=delta,
                mach=mach
            ))

        logger.info(f"Running {len(aileron_cases)} aileron deflection cases...")
        aileron_results = avl_runner.execute_avl(avl_file, aileron_cases, output_dir)

        # Extract control derivatives via finite differences
        control_derivatives = {}

        # Elevon derivatives (pitch control)
        if len(elevon_results) >= 3:
            # Extract CL, Cm for each elevon deflection
            deltas = []
            CLs = []
            Cms = []

            for case in control_cases:
                result = elevon_results.get(case.name)
                if result:
                    deltas.append(case.elevon)
                    CLs.append(result.CL)
                    Cms.append(result.Cm)

            if len(deltas) >= 3:
                # Linear fit to get derivatives (per degree)
                CL_de = np.polyfit(deltas, CLs, 1)[0]  # /deg
                Cm_de = np.polyfit(deltas, Cms, 1)[0]  # /deg

                control_derivatives['CL_de_per_deg'] = float(CL_de)
                control_derivatives['Cm_de_per_deg'] = float(Cm_de)

                logger.info(f"  Elevon: CL_de = {CL_de:.4f} /deg")
                logger.info(f"  Elevon: Cm_de = {Cm_de:.4f} /deg")

                # Extract hinge moment coefficient from a non-zero deflection case
                for case in control_cases:
                    result = elevon_results.get(case.name)
                    if result and result.Ch_elevon is not None and abs(case.elevon) > 1e-6:
                        control_derivatives['Ch_elevon'] = float(result.Ch_elevon)
                        logger.info(f"  Elevon: Ch = {result.Ch_elevon:.6f} (hinge moment coeff)")
                        break

        # Aileron derivatives (roll control)
        if len(aileron_results) >= 3:
            # Extract Cl, Cn for each aileron deflection
            deltas = []
            Cls = []
            Cns = []

            for case in aileron_cases:
                result = aileron_results.get(case.name)
                if result:
                    deltas.append(case.aileron)
                    Cls.append(result.Cl)
                    Cns.append(result.Cn)

            if len(deltas) >= 3:
                # Linear fit to get derivatives (per degree)
                Cl_da = np.polyfit(deltas, Cls, 1)[0]  # /deg
                Cn_da = np.polyfit(deltas, Cns, 1)[0]  # /deg (adverse yaw)

                control_derivatives['Cl_da_per_deg'] = float(Cl_da)
                control_derivatives['Cn_da_per_deg'] = float(Cn_da)

                logger.info(f"  Aileron: Cl_da = {Cl_da:.4f} /deg")
                logger.info(f"  Aileron: Cn_da = {Cn_da:.4f} /deg (adverse yaw)")

                # Extract hinge moment coefficient from a non-zero deflection case
                for case in aileron_cases:
                    result = aileron_results.get(case.name)
                    if result and result.Ch_aileron is not None and abs(case.aileron) > 1e-6:
                        control_derivatives['Ch_aileron'] = float(result.Ch_aileron)
                        logger.info(f"  Aileron: Ch = {result.Ch_aileron:.6f} (hinge moment coeff)")
                        break

        # Phase 4.6: Generate XFOIL Polars
        logger.section("Phase 4.6: XFOIL Airfoil Polars")

        from .analysis.xfoil_runner import XFOILRunner, AirfoilPolars

        xfoil_runner = XFOILRunner(
            xfoil_path=cfg.xfoil.executable,
            verbose=verbose_mode
        )

        # Generate polars for airfoil
        # Reynolds numbers for 20,000 ft operation:
        # At 100 mph: Re ≈ 3.2e6
        # At 150 mph: Re ≈ 4.8e6
        # At 200 mph: Re ≈ 6.4e6
        # At 250 mph: Re ≈ 8.0e6
        # Also include lower Re for stall/low-speed analysis
        reynolds_numbers = [5e5, 1e6, 3e6, 5e6, 7e6]

        # Check for custom airfoil file in input directory
        airfoil_files = list(input_dir.glob("*.dat"))

        try:
            if airfoil_files:
                # Use first .dat file found
                airfoil_file = airfoil_files[0]
                logger.info(f"Using custom airfoil: {airfoil_file.name}")
                airfoil_polars = xfoil_runner.generate_airfoil_polar(
                    airfoil_file=str(airfoil_file),
                    reynolds_numbers=reynolds_numbers,
                    alpha_range=(-5.0, 15.0),
                    alpha_step=1.0,
                    mach=mach,
                    n_iter=150
                )
            else:
                # Fallback to NACA 0012
                naca_code = "0012"
                logger.info(f"No custom airfoil found, using NACA {naca_code}")
                airfoil_polars = xfoil_runner.generate_naca_polar(
                    naca_code=naca_code,
                    reynolds_numbers=reynolds_numbers,
                    alpha_range=(-5.0, 15.0),
                    alpha_step=1.0,
                    mach=mach,
                    n_iter=150
                )

            # Save polars to CSV
            polar_dir = output_dir / "polars"
            xfoil_runner.save_polars(airfoil_polars, polar_dir)

            logger.success(f"Generated {len(airfoil_polars.polars)} airfoil polars")
        except Exception as e:
            logger.warning(f"XFOIL polar generation failed: {e}")
            logger.warning("Continuing with AVL-only aerodeck")
            airfoil_polars = None

        # Phase 5: Generate AeroDeck
        logger.section("Phase 5: AeroDeck Generation")

        from .output.aerodeck import (
            AeroDeck, ReferenceGeometry, MassProperties
        )

        # Create reference geometry
        ref_geometry = ReferenceGeometry(
            S_ref=ref_geom.area,
            b_ref=ref_geom.span,
            c_ref=ref_geom.chord,
            x_ref=geometry.mass_properties.cg[0],
            y_ref=geometry.mass_properties.cg[1],
            z_ref=geometry.mass_properties.cg[2]
        )

        # Create mass properties (extract from inertia tensor)
        inertia = geometry.mass_properties.inertia
        mass_props = MassProperties(
            mass=geometry.mass_properties.mass,
            cg_x=geometry.mass_properties.cg[0],
            cg_y=geometry.mass_properties.cg[1],
            cg_z=geometry.mass_properties.cg[2],
            Ixx=inertia[0, 0],
            Iyy=inertia[1, 1],
            Izz=inertia[2, 2],
            Ixy=inertia[0, 1],
            Ixz=inertia[0, 2],
            Iyz=inertia[1, 2],
            fuel_mass=geometry.mass_properties.fuel_mass
        )

        # Create aerodeck (use stability which has all derivatives including Xnp)
        aerodeck = AeroDeck.from_avl_results(
            aircraft_name=aircraft_name,
            avl_results=stability,
            reference_geometry=ref_geometry,
            mass_properties=mass_props,
            airfoil_polars=airfoil_polars if 'airfoil_polars' in locals() else None,
            control_derivatives=control_derivatives if control_derivatives else None
        )

        # Save aerodeck JSON
        aerodeck_file = output_dir / f"{aircraft_name.replace(' ', '_').lower()}_aerodeck.json"
        aerodeck.save_json(aerodeck_file)
        logger.success(f"Saved aerodeck: {aerodeck_file.name}")

        # Print summary
        logger.summary(
            "Analysis complete!",
            [
                f"AVL input file: {avl_file.name}",
                f"Aerodeck file: {aerodeck_file.name}",
                f"Number of cases: {len(results)}",
                f"Reference area: {ref_geom.area:.3f} ft²",
                f"Reference span: {ref_geom.span:.3f} ft",
                f"Reference chord: {ref_geom.chord:.3f} ft",
                "",
                "Key stability derivatives:",
                f"  CL_a = {avl_results.CL_alpha:.3f} /rad" if avl_results.CL_alpha else "  CL_a = (not computed)",
                f"  Cm_a = {avl_results.Cm_alpha:.3f} /rad" if avl_results.Cm_alpha else "  Cm_a = (not computed)",
                f"  CL_q = {avl_results.CL_q:.5f} /rad" if avl_results.CL_q else "  CL_q = (not computed)",
            ]
        )

        logger.info(f"\nOutput files saved to: {output_dir}")

    except Exception as e:
        logger.error(f"Failed to generate aerodeck: {e}")
        if verbose_mode:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@main.command()
@click.argument('input_dir', type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
def validate(input_dir: Path, verbose: bool) -> None:
    """
    Validate nTop geometry export without running analysis.

    INPUT_DIR: Directory containing nTop CSV files
    """
    set_verbose(verbose)
    logger = get_logger()

    logger.banner("nTop Geometry Validator", __version__)

    try:
        # Load geometry
        loader = GeometryLoader(verbose=verbose)
        geometry = loader.load_panel_data(input_dir)

        # Validate
        validator = GeometryValidator(verbose=verbose)
        result = validator.validate(geometry)

        if result.is_valid:
            logger.summary("[OK] Validation passed")
            sys.exit(0)
        else:
            logger.error("[ERR] Validation failed")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Validation error: {e}")
        sys.exit(1)


@main.command()
@click.argument('output_path', type=click.Path(path_type=Path))
def init_config(output_path: Path) -> None:
    """
    Create a default configuration file.

    OUTPUT_PATH: Path to save configuration file (e.g., config.yaml)
    """
    logger = get_logger(verbose=False)

    try:
        create_default_config(output_path)
        logger.info(f"Created default configuration: {output_path}")
        logger.info("\nEdit this file to customize analysis parameters.")

    except Exception as e:
        logger.error(f"Failed to create config: {e}")
        sys.exit(1)


@main.command()
@click.argument('deck_file', type=click.Path(exists=True, path_type=Path))
def view(deck_file: Path) -> None:
    """
    View aerodynamic deck file.

    DECK_FILE: Path to aerodeck JSON file
    """
    logger = get_logger(verbose=False)

    try:
        import json

        with open(deck_file, 'r') as f:
            deck = json.load(f)

        # Pretty print deck contents
        click.echo("\n" + "=" * 70)
        click.echo(f"Aerodynamic Deck: {deck_file.name}")
        click.echo("=" * 70)

        if 'metadata' in deck:
            click.echo("\nMetadata:")
            for key, value in deck['metadata'].items():
                click.echo(f"  {key}: {value}")

        if 'mass_properties' in deck:
            click.echo("\nMass Properties:")
            mass = deck['mass_properties']
            click.echo(f"  Mass: {mass.get('mass', 'N/A')} kg")
            click.echo(f"  CG: {mass.get('cg', 'N/A')}")

        if 'aerodynamics' in deck and 'static_stability' in deck['aerodynamics']:
            click.echo("\nStability Derivatives:")
            stab = deck['aerodynamics']['static_stability']
            for key, value in stab.items():
                click.echo(f"  {key}: {value}")

    except Exception as e:
        logger.error(f"Failed to view deck: {e}")
        sys.exit(1)


@main.command()
@click.option(
    '--naca',
    default='0012',
    help='NACA 4-digit airfoil code (default: 0012)'
)
@click.option(
    '--reynolds',
    '-re',
    multiple=True,
    type=float,
    help='Reynolds numbers to analyze (can specify multiple times)'
)
@click.option(
    '--alpha-min',
    default=-10.0,
    help='Minimum angle of attack [deg]'
)
@click.option(
    '--alpha-max',
    default=20.0,
    help='Maximum angle of attack [deg]'
)
@click.option(
    '--alpha-step',
    default=0.5,
    help='Angle of attack increment [deg]'
)
@click.option(
    '--mach',
    default=0.0,
    help='Mach number'
)
@click.option(
    '--output',
    '-o',
    type=click.Path(path_type=Path),
    default=Path('polars'),
    help='Output directory for polar files'
)
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def generate_polars(
    naca: str,
    reynolds: tuple,
    alpha_min: float,
    alpha_max: float,
    alpha_step: float,
    mach: float,
    output: Path,
    verbose: bool
) -> None:
    """
    Generate airfoil polars using XFOIL.

    Examples:
        aerodeck generate-polars --naca 0012 -re 1e6 -re 5e6
        aerodeck generate-polars --naca 2412 -re 1e6 --alpha-min -5 --alpha-max 15
    """
    from .analysis.xfoil_runner import XFOILRunner

    logger = get_logger(verbose=verbose)

    # Use default Reynolds numbers if none specified
    if not reynolds:
        reynolds = (1e6, 5e6, 1e7)

    try:
        logger.info("=" * 60)
        logger.info(f"  XFOIL Polar Generation")
        logger.info("=" * 60)
        logger.info(f"Airfoil: NACA {naca}")
        logger.info(f"Reynolds: {', '.join([f'{r:.2e}' for r in reynolds])}")
        logger.info(f"Alpha range: {alpha_min}° to {alpha_max}° (step {alpha_step}°)")
        logger.info(f"Mach: {mach}")
        logger.info("")

        # Create XFOIL runner
        xfoil = XFOILRunner(verbose=verbose)

        # Generate polars
        polars = xfoil.generate_naca_polar(
            naca_code=naca,
            reynolds_numbers=list(reynolds),
            alpha_range=(alpha_min, alpha_max),
            alpha_step=alpha_step,
            mach=mach
        )

        # Save polars
        xfoil.save_polars(polars, output)

        logger.info("")
        logger.info("=" * 60)
        logger.success(f"Polar generation complete!")
        logger.info(f"Output: {output.absolute()}")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Polar generation failed: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@main.command()
@click.argument('aerodeck_file', type=click.Path(exists=True, path_type=Path))
@click.option(
    '--output',
    '-o',
    type=click.Path(path_type=Path),
    default=None,
    help='Output PDF path (default: same name as JSON with .pdf)'
)
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def report(
    aerodeck_file: Path,
    output: Optional[Path],
    verbose: bool
) -> None:
    """
    Generate PDF report from aerodeck JSON file.

    AERODECK_FILE: Path to aerodeck JSON file

    Examples:
        aerodeck report results/testaircraft_aerodeck.json
        aerodeck report results/testaircraft_aerodeck.json -o my_report.pdf
    """
    from .output.report_generator import ReportGenerator

    logger = get_logger(verbose=verbose)

    try:
        logger.info("=" * 60)
        logger.info("  AeroDeck Report Generator")
        logger.info("=" * 60)
        logger.info(f"Input: {aerodeck_file.name}")
        logger.info("")

        # Create report generator
        generator = ReportGenerator(verbose=verbose)

        # Generate report
        output_file = generator.generate_report(aerodeck_file, output)

        logger.info("")
        logger.info("=" * 60)
        logger.success(f"Report generated successfully!")
        logger.info(f"Output: {output_file.absolute()}")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@main.command()
@click.argument('aerodeck_file', type=click.Path(exists=True, path_type=Path))
@click.option(
    '--output', '-o',
    type=click.Path(path_type=Path),
    default=None,
    help='Output HTML file path (default: same location as JSON)'
)
@click.option(
    '--no-browser',
    is_flag=True,
    help='Do not open browser automatically'
)
def html(
    aerodeck_file: Path,
    output: Optional[Path],
    no_browser: bool
) -> None:
    """Generate interactive HTML viewer from aerodeck JSON file."""
    from .output.html_viewer import HTMLViewer

    try:
        click.echo(f"\n{'='*60}")
        click.echo("  nTop AeroDeck HTML Viewer")
        click.echo(f"{'='*60}\n")

        click.echo(f"Loading aerodeck: {aerodeck_file.name}")

        viewer = HTMLViewer(aerodeck_file)
        html_path = viewer.generate_html(output_path=output, open_browser=not no_browser)

        click.echo(f"[OK] HTML viewer generated: {html_path}")

        if not no_browser:
            click.echo(f"[OK] Opening in browser...")

        click.echo(f"\n{'='*60}\n")

    except FileNotFoundError:
        click.echo(f"Error: File not found: {aerodeck_file}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error generating HTML viewer: {e}", err=True)
        sys.exit(1)


@main.command()
def version() -> None:
    """Show version information."""
    click.echo(f"nTop AeroDeck Generator v{__version__}")
    click.echo("Copyright (c) 2025 nTop Aero Team")


@main.command()
@click.argument('aerodeck_file', type=click.Path(exists=True, path_type=Path))
@click.option(
    '--load-factor', '-g',
    default=6.0,
    help='Load factor (g) for max-g condition (default: 6.0)'
)
@click.option(
    '--velocity', '-v',
    default=None,
    type=float,
    help='Velocity in mph (default: uses design cruise speed from aerodeck)'
)
@click.option(
    '--altitude', '-alt',
    default=20000,
    type=float,
    help='Altitude in feet (default: 20000)'
)
@click.option(
    '--chord-percent', '-c',
    default=25.0,
    type=float,
    help='Chordwise position for load application as percent (default: 25 = quarter-chord)'
)
@click.option(
    '--output', '-o',
    type=click.Path(path_type=Path),
    default=None,
    help='Output CSV file (default: <aerodeck>_loads.csv)'
)
@click.option('--verbose', is_flag=True, help='Verbose output')
def loads(
    aerodeck_file: Path,
    load_factor: float,
    velocity: Optional[float],
    altitude: float,
    chord_percent: float,
    output: Optional[Path],
    verbose: bool
) -> None:
    """
    Export spanwise wing loads at max-g condition for nTop FEA import.

    Generates a CSV with X, Y, Z positions and lift force at each spanwise station.
    The loads are computed at the specified load factor (g) and can be imported
    into nTop for bending simulation.

    AERODECK_FILE: Path to aerodeck JSON file

    Examples:
        aerodeck loads results/aircraft_aerodeck.json -g 6 -v 250
        aerodeck loads results/aircraft_aerodeck.json --load-factor 4.5 --altitude 10000
    """
    import json

    logger = get_logger(verbose=verbose)

    try:
        click.echo(f"\n{'='*60}")
        click.echo("  nTop AeroDeck Loads Export")
        click.echo(f"{'='*60}\n")

        # Load aerodeck JSON
        click.echo(f"Loading aerodeck: {aerodeck_file.name}")
        with open(aerodeck_file, 'r') as f:
            aerodeck_data = json.load(f)

        # Extract reference geometry
        ref = aerodeck_data.get('reference_geometry', {})
        S_ref = ref.get('S_ref', 8.4)  # ft²
        b_ref = ref.get('b_ref', 4.0)  # ft
        c_ref = ref.get('c_ref', 2.1)  # ft

        # Get mass for weight calculation
        mass_props = aerodeck_data.get('mass_properties', {})
        weight_lb = mass_props.get('mass', 50.0) * 2.20462  # kg to lb

        # Get velocity - use provided or extract from aerodeck
        if velocity is None:
            flight_cond = aerodeck_data.get('flight_conditions', {})
            velocity = flight_cond.get('cruise_speed_mph', 209)  # Default 209 mph

        click.echo(f"  Weight: {weight_lb:.1f} lb")
        click.echo(f"  Load factor: {load_factor:.1f} g")
        click.echo(f"  Velocity: {velocity:.1f} mph")
        click.echo(f"  Altitude: {altitude:.0f} ft")

        # Calculate required lift at max-g
        lift_required_lb = weight_lb * load_factor
        click.echo(f"  Required lift: {lift_required_lb:.1f} lb")

        # Calculate dynamic pressure at altitude
        # Standard atmosphere at altitude
        if altitude <= 36089:  # Troposphere
            T = 518.67 - 0.00356616 * altitude  # °R
            p = 2116.22 * (T / 518.67) ** 5.256  # psf
        else:  # Stratosphere
            T = 389.97  # °R (constant)
            p = 472.68 * np.exp(-0.0000480634 * (altitude - 36089))  # psf

        rho = p / (1716.49 * T)  # slug/ft³

        v_fps = velocity * 1.467  # mph to ft/s
        q = 0.5 * rho * v_fps ** 2  # dynamic pressure, psf

        click.echo(f"  Dynamic pressure: {q:.2f} psf")

        # Calculate CL required
        CL_required = lift_required_lb / (q * S_ref)
        click.echo(f"  CL required: {CL_required:.3f}")

        # Get CL_alpha to find required alpha
        aero = aerodeck_data.get('aerodynamics', {})
        static = aero.get('static_stability', {})
        CL_alpha = static.get('CL_alpha', 2.8)  # /rad, default typical value
        CL_0 = 0.1  # Approximate zero-lift CL

        alpha_required_rad = (CL_required - CL_0) / CL_alpha
        alpha_required_deg = np.rad2deg(alpha_required_rad)

        click.echo(f"  Alpha required: {alpha_required_deg:.2f}°")

        # Now we need to run AVL at this condition to get strip forces
        # First, find the AVL file
        avl_dir = aerodeck_file.parent
        avl_files = list(avl_dir.glob("*.avl"))
        if not avl_files:
            click.echo("Error: No AVL input file found in results directory", err=True)
            sys.exit(1)

        avl_file = avl_files[0]
        click.echo(f"\nRunning AVL at max-g condition...")
        click.echo(f"  AVL file: {avl_file.name}")

        # Run AVL at the required alpha
        from .analysis.avl_runner import AVLAnalysis, RunCase

        avl_runner = AVLAnalysis(verbose=verbose)

        max_g_case = RunCase(
            alpha=alpha_required_deg,
            beta=0.0,
            mach=velocity / 761.2,  # Approximate Mach at sea level
            name=f"maxg_{load_factor:.1f}g"
        )

        results = avl_runner.execute_avl(avl_file, [max_g_case], avl_dir)
        result = results.get(max_g_case.name)

        if not result:
            click.echo("Error: AVL failed to converge at max-g condition", err=True)
            sys.exit(1)

        click.echo(f"  CL actual: {result.CL:.4f}")
        click.echo(f"  CD actual: {result.CD:.4f}")

        # Check if we got strip forces
        if not result.strip_forces:
            click.echo("Error: No strip force data from AVL", err=True)
            sys.exit(1)

        click.echo(f"  Strip forces: {len(result.strip_forces)} stations")

        # Convert strip forces to dimensional loads
        # AVL gives us c_cl (chord × section Cl) at each station
        # The strip area is already provided
        #
        # IMPORTANT: AVL geometry is in FEET (loader.py converts inches→feet)
        # We convert back to inches for nTop FEA import (multiply by 12)

        # Build CSV data
        # NOTE: Positions are in inches to match nTop geometry units
        csv_rows = []
        csv_rows.append("X_in,Y_in,Z_in,Lift_lb,Chord_in,Cl,Surface")

        # Filter to wing surfaces only (exclude tail, etc.)
        wing_strips = [s for s in result.strip_forces if 'Wing' in s.surface or 'wing' in s.surface.lower()]

        if not wing_strips:
            # If no explicit "Wing" surface, use all strips
            wing_strips = result.strip_forces
            click.echo("  Note: Using all surfaces for loads (no 'Wing' surface found)")

        # AVL's CL is based on the geometry units - we need to compute actual lift
        # using the aerodynamic result and scale to required lift

        # Total strip areas in AVL units (inches²)
        total_strip_area = sum(s.area for s in wing_strips)

        # Convert AVL area to ft² (divide by 144)
        total_strip_area_ft2 = total_strip_area / 144.0

        click.echo(f"  Wing area (from strips): {total_strip_area_ft2:.2f} ft²")
        click.echo(f"  Reference area (S_ref): {S_ref:.2f} ft²")

        # Compute lift from AVL result
        # L_avl = q × S_ref × CL
        # But S_ref in aerodeck is already in ft², and q is in psf
        lift_avl = q * S_ref * result.CL
        click.echo(f"  Lift from AVL (at alpha={alpha_required_deg:.1f}°): {lift_avl:.1f} lb")

        # Scale factor to get required lift
        lift_scale = lift_required_lb / lift_avl if lift_avl > 0 else 1.0
        click.echo(f"  Lift scaling factor: {lift_scale:.3f}")

        # Distribute lift proportionally across strips based on cl × area
        total_cl_area = sum(s.cl * s.area for s in wing_strips)

        # Convert chord percent to fraction
        chord_fraction = chord_percent / 100.0
        click.echo(f"  Load position: {chord_percent:.0f}% chord")

        for strip in wing_strips:
            # Position at specified chord fraction
            # AVL geometry is in feet (converted from inches by loader)
            # Convert back to inches for nTop import: multiply by 12
            x_pos = (strip.Xle + chord_fraction * strip.chord) * 12.0
            y = strip.Yle * 12.0
            z = strip.Zle * 12.0
            chord_in = strip.chord * 12.0

            # Lift force on this strip proportional to its cl × area contribution
            if total_cl_area > 0:
                lift_lb = lift_required_lb * (strip.cl * strip.area) / total_cl_area
            else:
                lift_lb = 0.0

            csv_rows.append(f"{x_pos:.4f},{y:.4f},{z:.4f},{lift_lb:.4f},{chord_in:.4f},{strip.cl:.4f},{strip.surface}")

        # Write CSV
        if output is None:
            output = aerodeck_file.parent / f"{aerodeck_file.stem}_loads.csv"

        with open(output, 'w') as f:
            f.write('\n'.join(csv_rows))

        click.echo(f"\n[OK] Loads exported: {output}")
        click.echo(f"     {len(wing_strips)} strip stations")

        # Summary
        total_lift = sum(float(row.split(',')[3]) for row in csv_rows[1:])
        click.echo(f"     Total lift: {total_lift:.1f} lb")
        click.echo(f"     Required:   {lift_required_lb:.1f} lb")

        click.echo(f"\n{'='*60}\n")

    except Exception as e:
        click.echo(f"Error exporting loads: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
