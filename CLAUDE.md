# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Periodical Distiller creates METS/ALTO packages (MAPs) for ingest into the Veridian Presentation Software system. The initial use case converts born-digital content from The Daily Princetonian (published via the CEO3 headless CMS) into discrete periodical packages for the Papers of Princeton archive. A secondary goal (Project Strawberry) is to generalize these capabilities for other Princeton University Library periodicals.

## Build and Development Commands

- **Package manager:** PDM with uv backend
- **Install dependencies:** `pdm install`
- **Run all tests:** `pdm run pytest`
- **Run a single test:** `pdm run pytest tests/test_file.py::test_function`
- **CI/CD:** GitHub Actions

## Architecture

The system follows an OAIS-inspired pipeline with loosely coupled modules:

```
Aggregators → [PIP] → Transformers → Serializers → SIP Compilers → [SIP]
```

### Data Modules
- **Primary Information Packages (PIPs):** Source data and metadata gathered from external sources (e.g., CEO3 API)
- **Submission Information Packages (SIPs):** Output packages containing METS, ALTO, PDF, and image files for Veridian ingest

### Functional Modules (in `src/periodical_distiller/`)
- **`clients/`** — Network clients for external data sources. Base class in `client.py`; `ceo_client.py` accesses the Daily Princetonian CEO3 endpoint.
- **`aggregators/`** — Gather and organize resources from clients into PIPs.
- **`transformers/`** — Convert PIP data into derivatives (HTML, PDF, ALTO, MODS, text). Base class in `transformer.py`. Each transformer has a dedicated module.
- **`serializers/`** — Persist transformer outputs to disk. Base class in `serializer.py`. One serializer per derivative type.
- **`compilers/`** — Generate final SIPs. Base class in `compiler.py`. `mets_compiler.py` builds METS documents; `veridian_sip_compiler.py` assembles Veridian-compliant packages.
- **`cli.py`** — Command-line entry points for harvesting and transformation scripts.

### Schemas (`src/schemas/`)
- `ceo_item.py` — CEO content record schema
- `pip.py` — Primary Information Package schema
- `sip.py` — Submission Information Package schema

### Configuration and Support Files
- **Jinja2 templates** for HTML generation from CEO records
- **CSS stylesheets** for styling generated HTML
- Template/stylesheet selection is configuration-driven

## Key Standards
- [METS](https://www.loc.gov/standards/mets/) — Metadata Encoding & Transmission Standard
- [ALTO](https://www.loc.gov/standards/alto/) — Analyzed Layout and Text Object
- [MODS](https://www.loc.gov/standards/mods/) — Metadata Object Description Schema

## Coding Conventions
- Python (latest stable version), PEP 8
- Object-oriented with dependency injection
- SOLID principles
- pytest for testing
