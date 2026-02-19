"""Command-line interface for periodical-distiller."""

import argparse
import logging
import sys
from datetime import date
from pathlib import Path

from periodical_distiller.aggregators import PIPAggregator
from periodical_distiller.clients import CeoClient
from periodical_distiller.compilers import VeridianSIPCompiler
from periodical_distiller.pipeline.orchestrator import Orchestrator
from periodical_distiller.transformers import ALTOTransformer, HTMLTransformer, ImageTransformer, MODSTransformer, PDFTransformer

DEFAULT_OUTPUT_DIR = Path("./workspace/pips")
DEFAULT_SIP_OUTPUT_DIR = Path("./workspace/sips")
DEFAULT_CEO_BASE_URL = "https://www.dailyprincetonian.com"


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for the CLI."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
    )


def harvest_pip(args: argparse.Namespace) -> int:
    """Execute the harvest-pip command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    if args.date is None and (args.start is None or args.end is None):
        logger.error("Must specify either --date or both --start and --end")
        return 1

    if args.date is not None and (args.start is not None or args.end is not None):
        logger.error("Cannot specify both --date and --start/--end")
        return 1

    output_dir = args.output
    output_dir.mkdir(parents=True, exist_ok=True)

    config = {
        "base_url": args.base_url,
        "headers": {
            "User-Agent": "periodical-distiller/1.0 (Princeton University Library)",
        },
    }

    try:
        with CeoClient(config) as client:
            with PIPAggregator(
                output_dir, client, download_media=not args.no_media
            ) as aggregator:
                if args.date is not None:
                    logger.info(f"Fetching articles for {args.date}")
                    manifest = aggregator.create_pip_for_date(args.date)
                else:
                    logger.info(f"Fetching articles from {args.start} to {args.end}")
                    manifest = aggregator.create_pip_for_date_range(args.start, args.end)

        logger.info(f"Created PIP: {manifest.id}")
        logger.info(f"  Title: {manifest.title}")
        logger.info(f"  Articles: {len(manifest.articles)}")
        logger.info(f"  Output: {output_dir / manifest.id}")

        return 0

    except Exception as e:
        logger.error(f"Failed to create PIP: {e}")
        return 1


def transform_html(args: argparse.Namespace) -> int:
    """Execute the transform-html command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    pip_path = args.pip.resolve()
    if not pip_path.exists():
        logger.error(f"PIP directory not found: {pip_path}")
        return 1

    manifest_path = pip_path / "pip-manifest.json"
    if not manifest_path.exists():
        logger.error(f"PIP manifest not found: {manifest_path}")
        return 1

    output_dir = args.output
    output_dir.mkdir(parents=True, exist_ok=True)

    sip_path = output_dir / pip_path.name

    try:
        transformer = HTMLTransformer()
        manifest = transformer.transform(pip_path, sip_path)

        logger.info(f"Created SIP: {manifest.id}")
        logger.info(f"  Articles: {len(manifest.articles)}")
        logger.info(f"  Output: {sip_path}")

        if manifest.validation_errors:
            logger.warning(f"  Errors: {len(manifest.validation_errors)}")
            for error in manifest.validation_errors:
                logger.warning(f"    - {error}")

        return 0

    except Exception as e:
        logger.error(f"Failed to transform PIP: {e}")
        return 1


def transform_pdf(args: argparse.Namespace) -> int:
    """Execute the transform-pdf command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    sip_path = args.sip.resolve()
    if not sip_path.exists():
        logger.error(f"SIP directory not found: {sip_path}")
        return 1

    manifest_path = sip_path / "sip-manifest.json"
    if not manifest_path.exists():
        logger.error(f"SIP manifest not found: {manifest_path}")
        return 1

    try:
        transformer = PDFTransformer()
        manifest = transformer.transform(sip_path)

        pdf_count = sum(1 for a in manifest.articles if a.pdf_path)
        logger.info(f"Transformed SIP: {manifest.id}")
        logger.info(f"  PDFs generated: {pdf_count}")
        logger.info(f"  Output: {sip_path}")

        if manifest.validation_errors:
            logger.warning(f"  Errors: {len(manifest.validation_errors)}")
            for error in manifest.validation_errors:
                logger.warning(f"    - {error}")

        return 0

    except Exception as e:
        logger.error(f"Failed to transform SIP to PDF: {e}")
        return 1


def transform_alto(args: argparse.Namespace) -> int:
    """Execute the transform-alto command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    sip_path = args.sip.resolve()
    if not sip_path.exists():
        logger.error(f"SIP directory not found: {sip_path}")
        return 1

    manifest_path = sip_path / "sip-manifest.json"
    if not manifest_path.exists():
        logger.error(f"SIP manifest not found: {manifest_path}")
        return 1

    try:
        transformer = ALTOTransformer()
        manifest = transformer.transform(sip_path)

        alto_count = sum(len(a.pages) for a in manifest.articles if a.pdf_path)
        logger.info(f"Transformed SIP: {manifest.id}")
        logger.info(f"  ALTO files generated: {alto_count}")
        logger.info(f"  Output: {sip_path}")

        if manifest.validation_errors:
            logger.warning(f"  Errors: {len(manifest.validation_errors)}")
            for error in manifest.validation_errors:
                logger.warning(f"    - {error}")

        return 0

    except Exception as e:
        logger.error(f"Failed to transform SIP to ALTO: {e}")
        return 1


def transform_mods(args: argparse.Namespace) -> int:
    """Execute the transform-mods command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    sip_path = args.sip.resolve()
    if not sip_path.exists():
        logger.error(f"SIP directory not found: {sip_path}")
        return 1

    manifest_path = sip_path / "sip-manifest.json"
    if not manifest_path.exists():
        logger.error(f"SIP manifest not found: {manifest_path}")
        return 1

    try:
        transformer = MODSTransformer()
        manifest = transformer.transform(sip_path)

        mods_count = sum(1 for a in manifest.articles if a.mods_path)
        logger.info(f"Transformed SIP: {manifest.id}")
        logger.info(f"  MODS files generated: {mods_count}")
        logger.info(f"  Output: {sip_path}")

        if manifest.validation_errors:
            logger.warning(f"  Errors: {len(manifest.validation_errors)}")
            for error in manifest.validation_errors:
                logger.warning(f"    - {error}")

        return 0

    except Exception as e:
        logger.error(f"Failed to transform SIP to MODS: {e}")
        return 1


def transform_image(args: argparse.Namespace) -> int:
    """Execute the transform-image command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    sip_path = args.sip.resolve()
    if not sip_path.exists():
        logger.error(f"SIP directory not found: {sip_path}")
        return 1

    manifest_path = sip_path / "sip-manifest.json"
    if not manifest_path.exists():
        logger.error(f"SIP manifest not found: {manifest_path}")
        return 1

    try:
        transformer = ImageTransformer()
        manifest = transformer.transform(sip_path)

        image_count = sum(
            sum(1 for p in a.pages if p.image_path)
            for a in manifest.articles
        )
        logger.info(f"Transformed SIP: {manifest.id}")
        logger.info(f"  Images generated: {image_count}")
        logger.info(f"  Output: {sip_path}")

        if manifest.validation_errors:
            logger.warning(f"  Errors: {len(manifest.validation_errors)}")
            for error in manifest.validation_errors:
                logger.warning(f"    - {error}")

        return 0

    except Exception as e:
        logger.error(f"Failed to transform SIP to images: {e}")
        return 1


def compile_sip(args: argparse.Namespace) -> int:
    """Execute the compile-sip command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    sip_path = args.sip.resolve()
    if not sip_path.exists():
        logger.error(f"SIP directory not found: {sip_path}")
        return 1

    manifest_path = sip_path / "sip-manifest.json"
    if not manifest_path.exists():
        logger.error(f"SIP manifest not found: {manifest_path}")
        return 1

    try:
        compiler = VeridianSIPCompiler()
        manifest = compiler.compile(sip_path)

        logger.info(f"Compiled SIP: {manifest.id}")
        logger.info(f"  METS: {manifest.mets_path}")
        logger.info(f"  Status: {manifest.status}")
        logger.info(f"  Output: {sip_path}")

        if manifest.validation_errors:
            logger.warning(f"  Errors: {len(manifest.validation_errors)}")
            for error in manifest.validation_errors:
                logger.warning(f"    - {error}")

        return 0

    except Exception as e:
        logger.error(f"Failed to compile SIP: {e}")
        return 1


def run_pipeline(args: argparse.Namespace) -> int:
    """Execute the run-pipeline command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    pip_path = args.pip.resolve()
    if not pip_path.exists():
        logger.error(f"PIP directory not found: {pip_path}")
        return 1

    manifest_path = pip_path / "pip-manifest.json"
    if not manifest_path.exists():
        logger.error(f"PIP manifest not found: {manifest_path}")
        return 1

    output_dir = args.output
    output_dir.mkdir(parents=True, exist_ok=True)

    workspace = args.workspace or pip_path.parent / "pipeline-workspace" / pip_path.name
    workspace.mkdir(parents=True, exist_ok=True)

    try:
        orchestrator = Orchestrator(workspace=workspace, sip_output=output_dir)
        token = orchestrator.run(pip_path)

        status = token.get_prop("status") or "unknown"
        mets_path = token.get_prop("mets_path")
        validation_errors = token.get_prop("validation_errors") or []

        logger.info(f"Pipeline complete for {pip_path.name}")
        logger.info(f"  Status: {status}")
        if mets_path:
            logger.info(f"  METS: {mets_path}")
        logger.info(f"  Output: {output_dir / pip_path.name}")

        if validation_errors:
            logger.warning(f"  Errors: {len(validation_errors)}")
            for error in validation_errors:
                logger.warning(f"    - {error}")

        return 0 if status == "sealed" else 1

    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        return 1


def main(argv: list[str] | None = None) -> int:
    """Main entry point for the CLI.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:])

    Returns:
        Exit code
    """
    parser = argparse.ArgumentParser(
        prog="periodical-distiller",
        description="Create METS/ALTO packages for Veridian ingest",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    subparsers = parser.add_subparsers(
        title="commands",
        description="Available commands",
        dest="command",
    )

    harvest_parser = subparsers.add_parser(
        "harvest-pip",
        help="Fetch articles from CEO3 and create a PIP",
        description="Fetch articles from the CEO3 API and assemble them into a Primary Information Package (PIP).",
    )
    harvest_parser.add_argument(
        "--date",
        type=date.fromisoformat,
        help="Single date to fetch (ISO format: YYYY-MM-DD)",
    )
    harvest_parser.add_argument(
        "--start",
        type=date.fromisoformat,
        help="Start date for range (ISO format: YYYY-MM-DD)",
    )
    harvest_parser.add_argument(
        "--end",
        type=date.fromisoformat,
        help="End date for range (ISO format: YYYY-MM-DD)",
    )
    harvest_parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory for PIPs (default: {DEFAULT_OUTPUT_DIR})",
    )
    harvest_parser.add_argument(
        "--base-url",
        type=str,
        default=DEFAULT_CEO_BASE_URL,
        help=f"CEO3 API base URL (default: {DEFAULT_CEO_BASE_URL})",
    )
    harvest_parser.add_argument(
        "--no-media",
        action="store_true",
        help="Skip downloading article media",
    )
    harvest_parser.set_defaults(func=harvest_pip)

    transform_parser = subparsers.add_parser(
        "transform-html",
        help="Transform a PIP into a SIP with HTML files",
        description="Transform a Primary Information Package (PIP) into a Submission Information Package (SIP) containing styled HTML articles.",
    )
    transform_parser.add_argument(
        "--pip",
        type=Path,
        required=True,
        help="Path to the PIP directory to transform",
    )
    transform_parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_SIP_OUTPUT_DIR,
        help=f"Output directory for SIPs (default: {DEFAULT_SIP_OUTPUT_DIR})",
    )
    transform_parser.set_defaults(func=transform_html)

    pdf_parser = subparsers.add_parser(
        "transform-pdf",
        help="Transform HTML files in a SIP to PDF",
        description="Transform HTML articles in a Submission Information Package (SIP) to PDF format using WeasyPrint.",
    )
    pdf_parser.add_argument(
        "--sip",
        type=Path,
        required=True,
        help="Path to the SIP directory containing HTML files",
    )
    pdf_parser.set_defaults(func=transform_pdf)

    alto_parser = subparsers.add_parser(
        "transform-alto",
        help="Generate ALTO XML files from PDFs in a SIP",
        description="Extract word-level text from PDF articles in a Submission Information Package (SIP) and write ALTO 2.1 XML files.",
    )
    alto_parser.add_argument(
        "--sip",
        type=Path,
        required=True,
        help="Path to the SIP directory containing PDF files",
    )
    alto_parser.set_defaults(func=transform_alto)

    mods_parser = subparsers.add_parser(
        "transform-mods",
        help="Generate MODS XML files from CEO3 records in a SIP",
        description="Read CEO3 source records from the linked PIP and write MODS 3.8 XML files into a Submission Information Package (SIP).",
    )
    mods_parser.add_argument(
        "--sip",
        type=Path,
        required=True,
        help="Path to the SIP directory",
    )
    mods_parser.set_defaults(func=transform_mods)

    image_parser = subparsers.add_parser(
        "transform-image",
        help="Generate JPEG page images from PDFs in a SIP",
        description="Rasterize PDF articles in a Submission Information Package (SIP) to JPEG images at 150 DPI.",
    )
    image_parser.add_argument(
        "--sip",
        type=Path,
        required=True,
        help="Path to the SIP directory containing PDF files",
    )
    image_parser.set_defaults(func=transform_image)

    compile_parser = subparsers.add_parser(
        "compile-sip",
        help="Compile METS and seal a SIP for Veridian ingest",
        description="Build a METS document from SIP and PIP manifests and seal the Submission Information Package for Veridian ingest.",
    )
    compile_parser.add_argument(
        "--sip",
        type=Path,
        required=True,
        help="Path to the SIP directory",
    )
    compile_parser.set_defaults(func=compile_sip)

    pipeline_parser = subparsers.add_parser(
        "run-pipeline",
        help="Run the full pipeline from PIP to sealed SIP",
        description="Run a Primary Information Package (PIP) through the complete transformation pipeline to produce a sealed Veridian SIP.",
    )
    pipeline_parser.add_argument(
        "--pip",
        type=Path,
        required=True,
        help="Path to the PIP directory to process",
    )
    pipeline_parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_SIP_OUTPUT_DIR,
        help=f"Output directory for SIPs (default: {DEFAULT_SIP_OUTPUT_DIR})",
    )
    pipeline_parser.add_argument(
        "--workspace",
        type=Path,
        default=None,
        help="Pipeline workspace directory for bucket state (default: <pip-parent>/pipeline-workspace/<pip-id>)",
    )
    pipeline_parser.set_defaults(func=run_pipeline)

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
