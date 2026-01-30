"""Article token content schema for pipeline processing."""

from pydantic import BaseModel

from schemas.ceo_item import CeoItem


class ArticleTokenContent(BaseModel):
    """Schema for article token content.

    This model defines the structure of data carried by article tokens
    as they flow through the pipeline.

    Attributes:
        id: Unique article identifier (CEO ID)
        issue_id: Parent issue identifier
        ceo_record: Validated CEO3 record data
        html_path: Path to generated HTML file
        pdf_path: Path to generated PDF file
        alto_paths: Paths to generated ALTO files
        page_count: Number of pages in the PDF
        error: Error message if processing failed
        pip_path: Path to the PIP directory containing this article
        sip_path: Path to the SIP directory for this article's derivatives
    """

    id: str
    issue_id: str
    ceo_record: CeoItem | None = None
    html_path: str | None = None
    pdf_path: str | None = None
    alto_paths: list[str] = []
    page_count: int = 0
    error: str | None = None
    pip_path: str | None = None
    sip_path: str | None = None

    model_config = {"extra": "allow"}  # Allow additional fields like 'log'
