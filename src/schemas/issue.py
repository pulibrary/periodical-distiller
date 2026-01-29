"""Issue domain object."""

from dataclasses import dataclass, field
from datetime import date


@dataclass
class Issue:
    """Represents a periodical issue containing multiple articles.

    Attributes:
        issue_id: Unique issue identifier
        date_range: Publication date range (start, end)
        title: Issue title
        article_ids: CEO IDs of articles in this issue
    """

    issue_id: str
    date_range: tuple[date, date]
    title: str
    article_ids: list[str] = field(default_factory=list)
