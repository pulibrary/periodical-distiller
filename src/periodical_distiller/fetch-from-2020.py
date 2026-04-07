"""Harvest daily PIPs from 2020-01-01 to today."""

import logging
import shutil
import sys
from datetime import date, timedelta
from pathlib import Path

from periodical_distiller.aggregators import PIPAggregator
from periodical_distiller.clients import CeoClient

START_DATE = date(2020, 1, 1)
DEFAULT_OUTPUT_DIR = Path("./workspace/pips")
DEFAULT_CEO_BASE_URL = "https://www.dailyprincetonian.com"

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main() -> int:
    end_date = date.today()
    output_dir = DEFAULT_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    config = {
        "base_url": DEFAULT_CEO_BASE_URL,
        "headers": {
            "User-Agent": "periodical-distiller/1.0 (Princeton University Library)",
        },
    }

    total_days = (end_date - START_DATE).days + 1
    skipped = 0
    succeeded = 0
    failed: list[str] = []

    current = START_DATE
    with CeoClient(config) as client:
        with PIPAggregator(output_dir, client) as aggregator:
            while current <= end_date:
                pip_dir = output_dir / current.isoformat()
                if pip_dir.exists():
                    logger.debug(f"Skipping {current} (already exists)")
                    skipped += 1
                    current += timedelta(days=1)
                    continue

                try:
                    manifest = aggregator.create_pip_for_date(current)
                    if not manifest.articles:
                        logger.info(f"[{succeeded + skipped + len(failed) + 1}/{total_days}] {current}: no content, skipping")
                        shutil.rmtree(pip_dir)
                        skipped += 1
                        current += timedelta(days=1)
                        continue
                    logger.info(
                        f"[{succeeded + skipped + len(failed) + 1}/{total_days}]"
                        f" {current}: {len(manifest.articles)} articles → {manifest.id}"
                    )
                    succeeded += 1
                except Exception as e:
                    logger.warning(f"Failed {current}: {e}")
                    failed.append(current.isoformat())

                current += timedelta(days=1)

    logger.info(
        f"\nDone. succeeded={succeeded}, skipped={skipped}, failed={len(failed)}"
    )
    if failed:
        logger.warning(f"Failed dates: {', '.join(failed)}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
