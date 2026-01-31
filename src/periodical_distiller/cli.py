"""Command-line interface for periodical-distiller."""

import argparse
import logging
import sys
from datetime import date
from pathlib import Path

from periodical_distiller.aggregators import PIPAggregator
from periodical_distiller.clients import CeoClient

DEFAULT_OUTPUT_DIR = Path("./workspace/pips")
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
            aggregator = PIPAggregator(
                output_dir, client, download_media=not args.no_media
            )

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

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
