"""Page domain object."""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Page:
    """Represents Veridian's view of a page within the assembled issue.

    Attributes:
        page_number: Sequential page number within issue
        article_id: Source article this page belongs to
        alto_path: Path to ALTO file for this page
        image_path: Path to page image
    """

    page_number: int
    article_id: str
    alto_path: Path
    image_path: Path | None = None
