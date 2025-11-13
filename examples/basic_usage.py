"""
Basic usage example for aerodeck generation.

This example shows how to use the aerodeck package programmatically
instead of through the CLI.
"""

from pathlib import Path
from aerodeck.geometry.loader import GeometryLoader
from aerodeck.geometry.validator import GeometryValidator
from aerodeck.geometry.avl_translator import AVLGeometryWriter
from aerodeck.analysis.avl_runner import AVLAnalysis
from aerodeck.utils.config import Config
from aerodeck.utils.logger import get_logger


def main():
    """Run basic aerodeck generation example."""
    # Setup
    logger = get_logger(verbose=True)
    logger.banner("nTop AeroDeck Example", "1.0.0")

    # Define paths
    input_dir = Path("../Data")  # Adjust to your data location
    output_dir = Path("./output")
    output_dir.mkdir(exist_ok=True)

    # Load configuration
    config = Config()

    try:
        # Step 1: Load geometry
        logger.section("Step 1: Load Geometry")
        loader = GeometryLoader(verbose=True)
        geometry = loader.load_panel_data(input_dir)

        # Step 2: Validate geometry
        logger.section("Step 2: Validate Geometry")
        validator = GeometryValidator(config=config.validation, verbose=True)
        result = validator.validate(geometry)

        if not result.is_valid:
            logger.error("Geometry validation failed!")
            return

        # Step 3: Generate AVL input
        logger.section("Step 3: Generate AVL Input")
        avl_writer = AVLGeometryWriter(ref_config=config.reference, verbose=True)
        avl_file = output_dir / "aircraft.avl"
        ref_geom = avl_writer.write_avl_input(geometry, avl_file, "Example Aircraft")

        logger.info(f"Reference Area: {ref_geom.area:.3f} m²")
        logger.info(f"Reference Span: {ref_geom.span:.3f} m")
        logger.info(f"Reference Chord: {ref_geom.chord:.3f} m")

        # Step 4: Run AVL analysis
        logger.section("Step 4: Run AVL Analysis")
        avl_runner = AVLAnalysis(config=config.avl, verbose=True)

        # Setup run cases
        alpha_values = config.get_alpha_values()
        run_cases = avl_runner.setup_run_cases(alpha_values[:5])  # Just first 5 for demo

        # Execute AVL
        results = avl_runner.execute_avl(avl_file, run_cases, output_dir)

        # Compute stability derivatives
        stability = avl_runner.compute_stability_derivatives(results)

        logger.success(f"Analysis complete! Processed {len(results)} cases")

        # Print results
        logger.summary(
            "Results Summary",
            [
                f"Cases run: {len(results)}",
                f"CL_α: {stability.CL_alpha:.3f} /rad" if stability.CL_alpha else "CL_α: Not computed",
                f"Cm_α: {stability.Cm_alpha:.3f} /rad" if stability.Cm_alpha else "Cm_α: Not computed",
            ]
        )

    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
