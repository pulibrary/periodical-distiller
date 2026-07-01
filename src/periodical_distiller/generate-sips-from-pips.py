"""Generate sealed SIP zip files from all existing PIPs."""

import json
import logging
import shutil
import sys
from pathlib import Path

from periodical_distiller.pipeline.orchestrator import Orchestrator

DEFAULT_PIP_DIR = Path("./workspace/pips")
DEFAULT_SIP_DIR = Path("./workspace/sips")
DEFAULT_WORKSPACE_DIR = Path("./workspace/pipeline-workspace")

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def _is_sealed(sip_path: Path) -> bool:
    manifest_path = sip_path / "sip-manifest.json"
    if not manifest_path.exists():
        return False
    data = json.loads(manifest_path.read_text())
    return data.get("status") == "sealed"


def main() -> int:
    pip_dir = DEFAULT_PIP_DIR
    sip_dir = DEFAULT_SIP_DIR
    workspace_dir = DEFAULT_WORKSPACE_DIR

    if not pip_dir.exists():
        logger.error(f"PIP directory not found: {pip_dir}")
        return 1

    pip_paths = sorted(
        p for p in pip_dir.iterdir() if p.is_dir() and (p / "pip-manifest.json").exists()
    )

    if not pip_paths:
        logger.info("No PIPs found.")
        return 0

    logger.info(f"Found {len(pip_paths)} PIPs in {pip_dir}")
    sip_dir.mkdir(parents=True, exist_ok=True)
    workspace_dir.mkdir(parents=True, exist_ok=True)

    skipped = 0
    succeeded = 0
    failed: list[str] = []

    for i, pip_path in enumerate(pip_paths, 1):
        pip_id = pip_path.name
        zip_path = sip_dir / f"{pip_id}-sip.zip"
        sip_path = sip_dir / pip_id

        if zip_path.exists():
            logger.debug(f"[{i}/{len(pip_paths)}] {pip_id}: zip exists, skipping")
            skipped += 1
            continue

        if _is_sealed(sip_path):
            logger.info(f"[{i}/{len(pip_paths)}] {pip_id}: already sealed, zipping")
            shutil.make_archive(str(sip_dir / f"{pip_id}-sip"), "zip", sip_dir, pip_id)
            succeeded += 1
            continue

        logger.info(f"[{i}/{len(pip_paths)}] {pip_id}: running pipeline")
        try:
            workspace = workspace_dir / pip_id
            workspace.mkdir(parents=True, exist_ok=True)
            orchestrator = Orchestrator(workspace=workspace, sip_output=sip_dir)
            token = orchestrator.run(pip_path)

            status = token.get_prop("status") or "unknown"
            if status != "sealed":
                errors = token.get_prop("validation_errors") or []
                logger.warning(f"  {pip_id}: pipeline ended with status={status}")
                for e in errors:
                    logger.warning(f"    - {e}")
                failed.append(pip_id)
                continue

            shutil.make_archive(str(sip_dir / f"{pip_id}-sip"), "zip", sip_dir, pip_id)
            logger.info(f"  {pip_id}: sealed → {zip_path.name}")
            succeeded += 1

        except Exception as e:
            logger.warning(f"  {pip_id}: failed — {e}")
            failed.append(pip_id)

    logger.info(f"\nDone. succeeded={succeeded}, skipped={skipped}, failed={len(failed)}")
    if failed:
        logger.warning(f"Failed PIPs: {', '.join(failed)}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
