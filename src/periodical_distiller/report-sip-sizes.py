"""Report PIP and SIP sizes for all issues as a CSV."""

import csv
import subprocess
import sys
from pathlib import Path

DEFAULT_PIP_DIR = Path("./workspace/pips")
DEFAULT_SIP_DIR = Path("./workspace/sips")
OUTPUT_PATH = Path("./workspace/sip-size-report.csv")


def _dir_size_mb(path: Path) -> float:
    result = subprocess.run(["du", "-sk", str(path)], capture_output=True, text=True)
    kb = int(result.stdout.split()[0])
    return round(kb / 1024, 2)


def main() -> int:
    pip_dir = DEFAULT_PIP_DIR
    sip_dir = DEFAULT_SIP_DIR

    pip_paths = sorted(
        p for p in pip_dir.iterdir()
        if p.is_dir() and (p / "pip-manifest.json").exists()
    )

    if not pip_paths:
        print("No PIPs found.", file=sys.stderr)
        return 1

    rows: list[dict] = []
    warnings = 0

    for pip_path in pip_paths:
        date = pip_path.name
        sip_path = sip_dir / date
        zip_path = sip_dir / f"{date}-sip.zip"

        if not sip_path.exists():
            print(f"WARNING: no SIP directory for {date}, skipping", file=sys.stderr)
            warnings += 1
            continue
        if not zip_path.exists():
            print(f"WARNING: no SIP zip for {date}, skipping", file=sys.stderr)
            warnings += 1
            continue

        rows.append({
            "date": date,
            "pip_size_mb": _dir_size_mb(pip_path),
            "sip_size_mb": _dir_size_mb(sip_path),
            "sip_zip_size_mb": round(zip_path.stat().st_size / (1024 * 1024), 2),
        })

    with OUTPUT_PATH.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "pip_size_mb", "sip_size_mb", "sip_zip_size_mb"])
        writer.writeheader()
        writer.writerows(rows)

    total_pip = round(sum(r["pip_size_mb"] for r in rows) / 1024, 2)
    total_sip = round(sum(r["sip_size_mb"] for r in rows) / 1024, 2)
    total_zip = round(sum(r["sip_zip_size_mb"] for r in rows) / 1024, 2)

    print(f"Wrote {len(rows)} rows to {OUTPUT_PATH}")
    print(f"Totals (GB): PIPs={total_pip}  SIPs={total_sip}  ZIPs={total_zip}")
    if warnings:
        print(f"{warnings} date(s) skipped due to missing SIP or zip.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
