# Periodical Distiller

Periodical Distiller converts born-digital periodical content into
METS/ALTO packages (MAPs) suitable for ingest into the
[Veridian](https://veridiansoftware.com/services/presentation-software)
presentation software system.

## Background

The initial use case is the [Daily Princetonian](https://www.dailyprincetonian.com/),
a student newspaper published online since 2001 via the CEO3 headless CMS.
Periodical Distiller harvests articles from the CEO3 API, transforms them
through several derivative formats, and assembles a sealed Veridian-compliant
Submission Information Package (SIP) for ingest into the
[Papers of Princeton](https://papersofprinceton.princeton.edu/) archive.

A secondary goal (Project Strawberry) is to generalize the system for other
Princeton University Library periodicals.

See [`doc/design.org`](doc/design.org) for the full design background and
architectural rationale.

## Architecture

```
Aggregators → [PIP] → Transformers → SIP Compilers → [SIP]
```

- **PIP** (Primary Information Package) — raw CEO3 article records and
  downloaded media, organized into a directory with a JSON manifest.
- **SIP** (Submission Information Package) — derivative files (HTML, PDF,
  ALTO, MODS, JPEG) plus a METS document, ready for Veridian ingest.

## Requirements

- Python (latest stable)
- [PDM](https://pdm-project.org/en/latest/) with [uv](https://docs.astral.sh/uv/) backend

## Installation

```bash
pdm install
```

## CLI Quick Reference

| Command | Description |
|---|---|
| `harvest-pip` | Fetch articles from CEO3 and create a PIP |
| `transform-html` | Transform a PIP into a SIP with styled HTML articles |
| `transform-pdf` | Convert HTML articles in a SIP to PDF |
| `transform-alto` | Generate ALTO 2.1 XML files from PDFs in a SIP |
| `transform-mods` | Generate MODS 3.8 XML files from CEO3 records in a SIP |
| `transform-image` | Rasterize PDF articles to JPEG images at 150 DPI |
| `compile-sip` | Build a METS document and seal a SIP for Veridian ingest |
| `run-pipeline` | Run the full pipeline from PIP to sealed SIP |

Run any command with `--help` for full options:

```bash
pdm run python -m periodical_distiller.cli harvest-pip --help
```

## Running the Full Pipeline

Harvest a PIP for a date range and run it through the complete pipeline:

```bash
# Harvest articles for a date range into a PIP
pdm run python -m periodical_distiller.cli harvest-pip \
    --start 2026-01-15 --end 2026-01-17

# Run the full pipeline on that PIP
pdm run python -m periodical_distiller.cli run-pipeline \
    --pip ./pips/2026-01-15_2026-01-17
```

Or step through the pipeline manually:

```bash
pdm run python -m periodical_distiller.cli transform-html --pip ./pips/2026-01-15_2026-01-17
pdm run python -m periodical_distiller.cli transform-pdf  --sip ./sips/2026-01-15_2026-01-17
pdm run python -m periodical_distiller.cli transform-alto --sip ./sips/2026-01-15_2026-01-17
pdm run python -m periodical_distiller.cli transform-mods --sip ./sips/2026-01-15_2026-01-17
pdm run python -m periodical_distiller.cli transform-image --sip ./sips/2026-01-15_2026-01-17
pdm run python -m periodical_distiller.cli compile-sip    --sip ./sips/2026-01-15_2026-01-17
```

## Development

Run the test suite:

```bash
pdm run pytest
```

- Design document: [`doc/design.org`](doc/design.org)
- Known issues and backlog: [`doc/todo.org`](doc/todo.org)
