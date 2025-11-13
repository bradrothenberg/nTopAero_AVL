"""Command-line interface for aerodeck generation."""

import sys
from pathlib import Path
from typing import Optional
import click

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
    default='nTop Aircraft',
    help='Aircraft name for reports'
)
def generate(
    input_dir: Path,
    output_dir: Optional[Path],
    config: Optional[Path],
    verbose: bool,
    quiet: bool,
    validate_only: bool,
    aircraft_name: str
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
        avl_translator = AVLGeometryWriter(
            ref_config=cfg.reference,
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
        avl_runner = AVLAnalysis(config=cfg.avl, verbose=verbose_mode)

        # Setup run cases
        alpha_values = cfg.get_alpha_values()
        beta_values = cfg.get_beta_values()
        mach = cfg.analysis.mach_numbers[0] if cfg.analysis.mach_numbers else 0.0

        run_cases = avl_runner.setup_run_cases(alpha_values, beta_values, mach)

        # Execute AVL
        results = avl_runner.execute_avl(avl_file, run_cases, output_dir)

        # Compute derivatives
        stability = avl_runner.compute_stability_derivatives(results)

        # Print summary
        logger.summary(
            "Analysis complete!",
            [
                f"AVL input file: {avl_file}",
                f"Number of cases: {len(results)}",
                f"Reference area: {ref_geom.area:.3f} m²",
                f"Reference span: {ref_geom.span:.3f} m",
                f"Reference chord: {ref_geom.chord:.3f} m",
                "",
                "Key stability derivatives:",
                f"  CL_α = {stability.CL_alpha:.3f} /rad" if stability.CL_alpha else "  CL_α = (not computed)",
                f"  Cm_α = {stability.Cm_alpha:.3f} /rad" if stability.Cm_alpha else "  Cm_α = (not computed)",
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
def version() -> None:
    """Show version information."""
    click.echo(f"nTop AeroDeck Generator v{__version__}")
    click.echo("Copyright (c) 2025 nTop Aero Team")


if __name__ == "__main__":
    main()
