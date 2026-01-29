"""Issue token content schema for pipeline processing."""

from datetime import date

from pydantic import BaseModel


class IssueTokenContent(BaseModel):
    """Schema for issue token content.

    This model defines the structure of data carried by issue tokens
    as they flow through the issue assembly pipeline.

    Attributes:
        id: Unique issue identifier
        date_range: Publication date range (start, end)
        title: Issue title
        article_ids: CEO IDs of articles expected in this issue
        articles: Completed article data gathered from article pipeline
        mets_path: Path to generated METS file
        validation_errors: List of validation errors if any
    """

    id: str
    date_range: tuple[date, date]
    title: str
    article_ids: list[str] = []
    articles: list[dict] = []
    mets_path: str | None = None
    validation_errors: list[str] = []

    model_config = {"extra": "allow"}  # Allow additional fields like 'log'
