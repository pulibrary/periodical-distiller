"""Submission Information Package (SIP) schemas.

SIPs are OAIS-inspired packages containing transformed derivatives ready for
ingest into Veridian. SIPs are mutable during construction and become sealed
when complete.

Directory structure:
    sips/
    └── {issue_id}/
        ├── sip-manifest.json     # SIPManifest
        ├── mets.xml              # METS document
        └── articles/
            ├── {ceo_id}/
            │   ├── article.html
            │   ├── article.pdf
            │   ├── 001.alto.xml
            │   ├── 002.alto.xml
            │   └── ...
            └── ...
"""

from typing import Literal

from pydantic import BaseModel


class SIPPage(BaseModel):
    """A page within a SIP article.

    Represents a single page of a PDF with its corresponding ALTO file.

    Attributes:
        page_number: 1-based page number
        alto_path: Relative path to ALTO XML file
        image_path: Relative path to page image (optional)
    """

    page_number: int
    alto_path: str
    image_path: str | None = None


class SIPArticle(BaseModel):
    """An article within a SIP.

    Contains paths to all derivative files generated from a source article.

    Attributes:
        ceo_id: CEO3 article identifier (links back to PIP)
        html_path: Relative path to generated HTML
        pdf_path: Relative path to generated PDF
        mods_path: Relative path to generated MODS XML
        pages: List of pages with ALTO files
    """

    ceo_id: str
    html_path: str | None = None
    pdf_path: str | None = None
    mods_path: str | None = None
    pages: list[SIPPage] = []


class SIPManifest(BaseModel):
    """Manifest for a Submission Information Package.

    The SIP manifest describes an issue-level package ready for Veridian ingest,
    containing METS, ALTO, PDF, and supporting files.

    Attributes:
        id: Issue identifier (e.g., "2026-01-15")
        version: Manifest schema version
        pip_id: ID of the source PIP (for provenance)
        pip_path: Path to the source PIP directory
        articles: List of articles with their derivative paths
        mets_path: Relative path to the METS document
        status: Package status ("building" while transforming, "sealed" when complete)
        validation_errors: List of any validation errors encountered
    """

    id: str
    version: str = "1.0"
    pip_id: str
    pip_path: str | None = None
    articles: list[SIPArticle] = []
    mets_path: str | None = None
    status: Literal["building", "sealed"] = "building"
    validation_errors: list[str] = []

    model_config = {"extra": "allow"}
