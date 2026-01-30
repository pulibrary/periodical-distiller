"""CEO3 content item schemas."""

from pydantic import BaseModel, Field


class CeoMetadataEntry(BaseModel):
    """A label-value pair in CEO3 metadata arrays."""

    label: str
    value: str


class CeoTag(BaseModel):
    """A tag associated with a CEO3 item."""

    id: str
    uuid: str
    name: str
    slug: str
    ceo_id: str
    metadata: None = None


class CeoAuthor(BaseModel):
    """An author/staff member in CEO3."""

    id: str
    uuid: str
    name: str
    email: str
    slug: str
    bio: str
    tagline: str
    ceo_id: str
    status: str
    metadata: None = None


class CeoMedia(BaseModel):
    """Media attachment in CEO3 (images, videos, etc.)."""

    id: str
    uuid: str
    attachment_uuid: str
    base_name: str
    extension: str
    preview_extension: str
    title: str | None = None
    content: str | None = None
    source: str | None = None
    click_through: str | None = None
    type: str | None = None
    height: str | None = None
    width: str | None = None
    seo_title: str | None = None
    seo_description: str | None = None
    seo_image: str | None = None
    svg_preview: str | None = None
    status: str
    weight: str
    hits: str
    transcoded: str
    created_at: str
    modified_at: str
    published_at: str
    normalized_tags: str | None = None
    ceo_id: str
    ssts_id: str | None = None
    ssts_path: str | None = None
    metadata: list[CeoMetadataEntry] = []
    authors: list = []

    model_config = {"extra": "allow"}


class CeoItem(BaseModel):
    """A content item from the CEO3 API (article, post, etc.)."""

    # Identifiers
    id: str
    uuid: str
    slug: str
    ceo_id: str
    short_token: str

    # Article content
    headline: str
    subhead: str | None = None
    abstract: str | None = None
    content: str | None = None
    infobox: str | None = None

    # SEO metadata
    seo_title: str | None = None
    seo_description: str | None = None
    seo_image: str | None = None

    # Display/state
    template: str | None = None
    status: str
    weight: str

    # Media
    media_id: str
    dominant_media: CeoMedia | None = Field(default=None, alias="dominantMedia")

    # Timestamps (kept as strings per user preference)
    created_at: str
    modified_at: str
    published_at: str

    # Analytics
    hits: str
    metadata: list[CeoMetadataEntry] = []

    # Relationships
    normalized_tags: str
    tags: list[CeoTag] = []
    authors: list[CeoAuthor] = []

    # SSTS references
    ssts_id: str | None = None
    ssts_path: str | None = None

    model_config = {"extra": "allow", "populate_by_name": True}
