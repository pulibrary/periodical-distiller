"""Primary Information Package (PIP) schemas.

PIPs are OAIS-inspired packages that capture source content from external
systems (e.g., CEO3 API) along with preservation description information.
PIPs are immutable after creation and serve as the authoritative source
for downstream transformation into SIPs.

Directory structure:
    pips/
    └── {issue_id}/
        ├── pip-manifest.json     # PIPManifest
        └── articles/
            ├── {ceo_id}/
            │   ├── ceo_record.json
            │   └── images/
            │       └── ...
            └── ...
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class PIPMedia(BaseModel):
    """Media file collected into a PIP.

    Attributes:
        original_url: Original URL from source system
        local_path: Relative path within the PIP directory
        media_type: MIME type of the media
        checksum: SHA-256 hash of the file
    """

    original_url: str
    local_path: str
    media_type: str | None = None
    checksum: str | None = None


class PIPArticle(BaseModel):
    """An article within a PIP.

    Attributes:
        ceo_id: CEO3 article identifier
        ceo_record_path: Relative path to ceo_record.json
        media: List of media files associated with this article
    """

    ceo_id: str
    ceo_record_path: str
    media: list[PIPMedia] = []


class PreservationDescriptionInfo(BaseModel):
    """OAIS Preservation Description Information.

    Captures provenance and context needed for long-term preservation.

    Attributes:
        source_system: Name of the source system (e.g., "CEO3")
        source_url: Base URL of the source API
        harvest_timestamp: When the content was harvested
        harvest_agent: Software/version that performed the harvest
        content_hash: Hash of all content for integrity verification
    """

    source_system: str = "CEO3"
    source_url: str | None = None
    harvest_timestamp: datetime = Field(default_factory=datetime.now)
    harvest_agent: str = "periodical-distiller"
    content_hash: str | None = None


class PIPManifest(BaseModel):
    """Manifest for a Primary Information Package.

    The PIP manifest describes an issue-level package containing all source
    content needed to generate a SIP for Veridian ingest.

    Attributes:
        id: Issue identifier (e.g., "2026-01-15")
        version: Manifest schema version
        title: Issue title for display
        date_range: Publication date range (start, end) as ISO strings
        articles: List of articles in this issue
        pdi: Preservation Description Information
        status: Package status (always "sealed" for PIPs once complete)
    """

    id: str
    version: str = "1.0"
    title: str
    date_range: tuple[str, str]
    articles: list[PIPArticle] = []
    pdi: PreservationDescriptionInfo = Field(
        default_factory=PreservationDescriptionInfo
    )
    status: Literal["building", "sealed"] = "building"

    model_config = {"extra": "allow"}
