"""Article domain object."""

from dataclasses import dataclass, field
from pathlib import Path

from lxml import etree


@dataclass
class Article:
    """Represents a single article from the source publication.

    Attributes:
        ceo_id: Unique identifier from CEO3
        issue_id: Parent issue identifier
        metadata: Source metadata from CEO3
        html_path: Path to generated HTML file
        pdf_path: Path to generated PDF file
        page_count: Number of pages in the PDF
        alto_paths: Paths to ALTO files (one per page)
        mods: lxml Element containing MODS metadata fragment
    """

    ceo_id: str
    issue_id: str
    metadata: dict = field(default_factory=dict)
    html_path: Path | None = None
    pdf_path: Path | None = None
    page_count: int = 0
    alto_paths: list[Path] = field(default_factory=list)
    mods: etree._Element | None = None
