"""Tests for schema definitions."""

import json
from datetime import date, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from schemas import (
    Article,
    Issue,
    Page,
    PIPArticle,
    PIPManifest,
    PIPMedia,
    PreservationDescriptionInfo,
    SIPArticle,
    SIPManifest,
    SIPPage,
)
from schemas.tokens import ArticleTokenContent, IssueTokenContent


class TestArticle:
    """Tests for Article dataclass."""

    def test_article_creation(self):
        """Article can be created with required fields."""
        article = Article(ceo_id="12345", issue_id="2026-01-15")

        assert article.ceo_id == "12345"
        assert article.issue_id == "2026-01-15"
        assert article.metadata == {}
        assert article.html_path is None
        assert article.pdf_path is None
        assert article.page_count == 0
        assert article.alto_paths == []
        assert article.mods is None

    def test_article_with_all_fields(self, tmp_path):
        """Article can be created with all fields."""
        html_path = tmp_path / "article.html"
        pdf_path = tmp_path / "article.pdf"
        alto_paths = [tmp_path / "001.xml", tmp_path / "002.xml"]

        article = Article(
            ceo_id="12345",
            issue_id="2026-01-15",
            metadata={"headline": "Test Article"},
            html_path=html_path,
            pdf_path=pdf_path,
            page_count=2,
            alto_paths=alto_paths,
        )

        assert article.html_path == html_path
        assert article.pdf_path == pdf_path
        assert article.page_count == 2
        assert len(article.alto_paths) == 2


class TestIssue:
    """Tests for Issue dataclass."""

    def test_issue_creation(self):
        """Issue can be created with required fields."""
        issue = Issue(
            issue_id="2026-01-15",
            date_range=(date(2026, 1, 15), date(2026, 1, 15)),
            title="The Daily Princetonian - January 15, 2026",
        )

        assert issue.issue_id == "2026-01-15"
        assert issue.date_range == (date(2026, 1, 15), date(2026, 1, 15))
        assert issue.title == "The Daily Princetonian - January 15, 2026"
        assert issue.article_ids == []

    def test_issue_with_articles(self):
        """Issue can track article IDs."""
        issue = Issue(
            issue_id="2026-01-15",
            date_range=(date(2026, 1, 15), date(2026, 1, 15)),
            title="Test Issue",
            article_ids=["article1", "article2", "article3"],
        )

        assert len(issue.article_ids) == 3
        assert "article2" in issue.article_ids


class TestPage:
    """Tests for Page dataclass."""

    def test_page_creation(self):
        """Page can be created with required fields."""
        page = Page(
            page_number=1,
            article_id="article-123",
            alto_path=Path("/path/to/001.xml"),
        )

        assert page.page_number == 1
        assert page.article_id == "article-123"
        assert page.alto_path == Path("/path/to/001.xml")
        assert page.image_path is None

    def test_page_with_image(self):
        """Page can include image path."""
        page = Page(
            page_number=1,
            article_id="article-123",
            alto_path=Path("/path/to/001.xml"),
            image_path=Path("/path/to/001.png"),
        )

        assert page.image_path == Path("/path/to/001.png")


class TestArticleTokenContent:
    """Tests for ArticleTokenContent Pydantic model."""

    def test_article_token_creation(self):
        """ArticleTokenContent can be created with required fields."""
        token = ArticleTokenContent(id="12345", issue_id="2026-01-15")

        assert token.id == "12345"
        assert token.issue_id == "2026-01-15"
        assert token.ceo_record is None
        assert token.html_path is None
        assert token.pdf_path is None
        assert token.alto_paths == []
        assert token.page_count == 0
        assert token.error is None

    def test_article_token_with_ceo_record(self, sample_ceo_record):
        """ArticleTokenContent can hold CEO record."""
        token = ArticleTokenContent(
            id="12345",
            issue_id="2026-01-15",
            ceo_record=sample_ceo_record,
        )

        assert token.ceo_record is not None
        assert token.ceo_record.headline == "Test Article Headline"

    def test_article_token_allows_extra_fields(self):
        """ArticleTokenContent allows extra fields like 'log'."""
        token = ArticleTokenContent(
            id="12345",
            issue_id="2026-01-15",
            log=[{"message": "test"}],
        )

        # Extra fields should be accessible
        assert hasattr(token, "log") or "log" in token.model_extra

    def test_article_token_serialization(self):
        """ArticleTokenContent can be serialized to dict."""
        token = ArticleTokenContent(
            id="12345",
            issue_id="2026-01-15",
            html_path="/path/to/file.html",
            page_count=3,
        )

        data = token.model_dump()

        assert data["id"] == "12345"
        assert data["html_path"] == "/path/to/file.html"
        assert data["page_count"] == 3

    def test_article_token_validation(self):
        """ArticleTokenContent validates required fields."""
        with pytest.raises(ValidationError):
            ArticleTokenContent(issue_id="2026-01-15")  # Missing id


class TestIssueTokenContent:
    """Tests for IssueTokenContent Pydantic model."""

    def test_issue_token_creation(self):
        """IssueTokenContent can be created with required fields."""
        token = IssueTokenContent(
            id="2026-01-15",
            date_range=(date(2026, 1, 15), date(2026, 1, 15)),
            title="Test Issue",
        )

        assert token.id == "2026-01-15"
        assert token.date_range == (date(2026, 1, 15), date(2026, 1, 15))
        assert token.title == "Test Issue"
        assert token.article_ids == []
        assert token.articles == []
        assert token.mets_path is None
        assert token.validation_errors == []

    def test_issue_token_with_articles(self):
        """IssueTokenContent can track articles."""
        token = IssueTokenContent(
            id="2026-01-15",
            date_range=(date(2026, 1, 15), date(2026, 1, 15)),
            title="Test Issue",
            article_ids=["a1", "a2", "a3"],
            articles=[
                {"id": "a1", "html_path": "/path/a1.html"},
                {"id": "a2", "html_path": "/path/a2.html"},
            ],
        )

        assert len(token.article_ids) == 3
        assert len(token.articles) == 2

    def test_issue_token_validation_errors(self):
        """IssueTokenContent can track validation errors."""
        token = IssueTokenContent(
            id="2026-01-15",
            date_range=(date(2026, 1, 15), date(2026, 1, 15)),
            title="Test Issue",
            validation_errors=[
                "ALTO file 001.xml failed schema validation",
                "MODS missing required field: title",
            ],
        )

        assert len(token.validation_errors) == 2

    def test_issue_token_serialization(self):
        """IssueTokenContent can be serialized to dict."""
        token = IssueTokenContent(
            id="2026-01-15",
            date_range=(date(2026, 1, 15), date(2026, 1, 15)),
            title="Test Issue",
            mets_path="/path/to/mets.xml",
        )

        data = token.model_dump()

        assert data["id"] == "2026-01-15"
        assert data["mets_path"] == "/path/to/mets.xml"
        # date_range should serialize to dates
        assert data["date_range"] == (date(2026, 1, 15), date(2026, 1, 15))

    def test_issue_token_with_pip_sip_paths(self):
        """IssueTokenContent can include pip_path and sip_path."""
        token = IssueTokenContent(
            id="2026-01-15",
            date_range=(date(2026, 1, 15), date(2026, 1, 15)),
            title="Test Issue",
            pip_path="/workspace/pips/2026-01-15",
            sip_path="/workspace/sips/2026-01-15",
        )

        assert token.pip_path == "/workspace/pips/2026-01-15"
        assert token.sip_path == "/workspace/sips/2026-01-15"


class TestArticleTokenWithPackagePaths:
    """Tests for ArticleTokenContent pip_path/sip_path fields."""

    def test_article_token_with_pip_sip_paths(self):
        """ArticleTokenContent can include pip_path and sip_path."""
        token = ArticleTokenContent(
            id="12345",
            issue_id="2026-01-15",
            pip_path="/workspace/pips/2026-01-15",
            sip_path="/workspace/sips/2026-01-15",
        )

        assert token.pip_path == "/workspace/pips/2026-01-15"
        assert token.sip_path == "/workspace/sips/2026-01-15"


class TestPIPMedia:
    """Tests for PIPMedia schema."""

    def test_pip_media_creation(self):
        """PIPMedia can be created with required fields."""
        media = PIPMedia(
            original_url="https://example.com/image.jpg",
            local_path="articles/12345/images/image.jpg",
        )

        assert media.original_url == "https://example.com/image.jpg"
        assert media.local_path == "articles/12345/images/image.jpg"
        assert media.media_type is None
        assert media.checksum is None

    def test_pip_media_with_all_fields(self):
        """PIPMedia can include optional fields."""
        media = PIPMedia(
            original_url="https://example.com/image.jpg",
            local_path="articles/12345/images/image.jpg",
            media_type="image/jpeg",
            checksum="abc123def456",
        )

        assert media.media_type == "image/jpeg"
        assert media.checksum == "abc123def456"


class TestPIPArticle:
    """Tests for PIPArticle schema."""

    def test_pip_article_creation(self):
        """PIPArticle can be created with required fields."""
        article = PIPArticle(
            ceo_id="12345",
            ceo_record_path="articles/12345/ceo_record.json",
        )

        assert article.ceo_id == "12345"
        assert article.ceo_record_path == "articles/12345/ceo_record.json"
        assert article.media == []

    def test_pip_article_with_media(self):
        """PIPArticle can include media files."""
        media = PIPMedia(
            original_url="https://example.com/image.jpg",
            local_path="articles/12345/images/image.jpg",
        )
        article = PIPArticle(
            ceo_id="12345",
            ceo_record_path="articles/12345/ceo_record.json",
            media=[media],
        )

        assert len(article.media) == 1
        assert article.media[0].original_url == "https://example.com/image.jpg"


class TestPreservationDescriptionInfo:
    """Tests for PreservationDescriptionInfo schema."""

    def test_pdi_default_values(self):
        """PreservationDescriptionInfo has sensible defaults."""
        pdi = PreservationDescriptionInfo()

        assert pdi.source_system == "CEO3"
        assert pdi.harvest_agent == "periodical-distiller"
        assert pdi.source_url is None
        assert pdi.content_hash is None
        assert isinstance(pdi.harvest_timestamp, datetime)

    def test_pdi_with_custom_values(self):
        """PreservationDescriptionInfo accepts custom values."""
        timestamp = datetime(2026, 1, 15, 10, 30, 0)
        pdi = PreservationDescriptionInfo(
            source_system="CEO3",
            source_url="https://api.dailyprincetonian.com",
            harvest_timestamp=timestamp,
            harvest_agent="periodical-distiller/1.0",
            content_hash="sha256:abc123",
        )

        assert pdi.source_url == "https://api.dailyprincetonian.com"
        assert pdi.harvest_timestamp == timestamp
        assert pdi.content_hash == "sha256:abc123"


class TestPIPManifest:
    """Tests for PIPManifest schema."""

    def test_pip_manifest_creation(self):
        """PIPManifest can be created with required fields."""
        manifest = PIPManifest(
            id="2026-01-15",
            title="The Daily Princetonian - January 15, 2026",
            date_range=("2026-01-15", "2026-01-15"),
        )

        assert manifest.id == "2026-01-15"
        assert manifest.version == "1.0"
        assert manifest.title == "The Daily Princetonian - January 15, 2026"
        assert manifest.date_range == ("2026-01-15", "2026-01-15")
        assert manifest.articles == []
        assert manifest.status == "building"
        assert manifest.pdi.source_system == "CEO3"

    def test_pip_manifest_with_articles(self):
        """PIPManifest can include articles."""
        article = PIPArticle(
            ceo_id="12345",
            ceo_record_path="articles/12345/ceo_record.json",
        )
        manifest = PIPManifest(
            id="2026-01-15",
            title="Test Issue",
            date_range=("2026-01-15", "2026-01-15"),
            articles=[article],
            status="sealed",
        )

        assert len(manifest.articles) == 1
        assert manifest.articles[0].ceo_id == "12345"
        assert manifest.status == "sealed"

    def test_pip_manifest_json_serialization(self):
        """PIPManifest can be serialized to and from JSON."""
        manifest = PIPManifest(
            id="2026-01-15",
            title="Test Issue",
            date_range=("2026-01-15", "2026-01-15"),
            articles=[
                PIPArticle(
                    ceo_id="12345",
                    ceo_record_path="articles/12345/ceo_record.json",
                )
            ],
        )

        # Serialize to JSON
        json_str = manifest.model_dump_json()
        data = json.loads(json_str)

        assert data["id"] == "2026-01-15"
        assert data["version"] == "1.0"
        assert len(data["articles"]) == 1

        # Deserialize from JSON
        restored = PIPManifest.model_validate_json(json_str)
        assert restored.id == manifest.id
        assert restored.articles[0].ceo_id == "12345"


class TestSIPPage:
    """Tests for SIPPage schema."""

    def test_sip_page_creation(self):
        """SIPPage can be created with required fields."""
        page = SIPPage(
            page_number=1,
            alto_path="articles/12345/001.alto.xml",
        )

        assert page.page_number == 1
        assert page.alto_path == "articles/12345/001.alto.xml"
        assert page.image_path is None

    def test_sip_page_with_image(self):
        """SIPPage can include image path."""
        page = SIPPage(
            page_number=1,
            alto_path="articles/12345/001.alto.xml",
            image_path="articles/12345/001.png",
        )

        assert page.image_path == "articles/12345/001.png"


class TestSIPArticle:
    """Tests for SIPArticle schema."""

    def test_sip_article_creation(self):
        """SIPArticle can be created with required fields."""
        article = SIPArticle(ceo_id="12345")

        assert article.ceo_id == "12345"
        assert article.html_path is None
        assert article.pdf_path is None
        assert article.mods_path is None
        assert article.pages == []

    def test_sip_article_with_derivatives(self):
        """SIPArticle can include all derivative paths."""
        pages = [
            SIPPage(page_number=1, alto_path="articles/12345/001.alto.xml"),
            SIPPage(page_number=2, alto_path="articles/12345/002.alto.xml"),
        ]
        article = SIPArticle(
            ceo_id="12345",
            html_path="articles/12345/article.html",
            pdf_path="articles/12345/article.pdf",
            mods_path="articles/12345/article.mods.xml",
            pages=pages,
        )

        assert article.html_path == "articles/12345/article.html"
        assert article.pdf_path == "articles/12345/article.pdf"
        assert article.mods_path == "articles/12345/article.mods.xml"
        assert len(article.pages) == 2


class TestSIPManifest:
    """Tests for SIPManifest schema."""

    def test_sip_manifest_creation(self):
        """SIPManifest can be created with required fields."""
        manifest = SIPManifest(
            id="2026-01-15",
            pip_id="2026-01-15",
        )

        assert manifest.id == "2026-01-15"
        assert manifest.version == "1.0"
        assert manifest.pip_id == "2026-01-15"
        assert manifest.pip_path is None
        assert manifest.articles == []
        assert manifest.mets_path is None
        assert manifest.status == "building"
        assert manifest.validation_errors == []

    def test_sip_manifest_with_articles(self):
        """SIPManifest can include articles."""
        article = SIPArticle(
            ceo_id="12345",
            html_path="articles/12345/article.html",
            pdf_path="articles/12345/article.pdf",
        )
        manifest = SIPManifest(
            id="2026-01-15",
            pip_id="2026-01-15",
            pip_path="/workspace/pips/2026-01-15",
            articles=[article],
            mets_path="mets.xml",
            status="sealed",
        )

        assert manifest.pip_path == "/workspace/pips/2026-01-15"
        assert len(manifest.articles) == 1
        assert manifest.mets_path == "mets.xml"
        assert manifest.status == "sealed"

    def test_sip_manifest_with_validation_errors(self):
        """SIPManifest can track validation errors."""
        manifest = SIPManifest(
            id="2026-01-15",
            pip_id="2026-01-15",
            validation_errors=[
                "ALTO file 001.xml failed schema validation",
                "Missing required MODS field: title",
            ],
        )

        assert len(manifest.validation_errors) == 2

    def test_sip_manifest_json_serialization(self):
        """SIPManifest can be serialized to and from JSON."""
        manifest = SIPManifest(
            id="2026-01-15",
            pip_id="2026-01-15",
            pip_path="/workspace/pips/2026-01-15",
            articles=[
                SIPArticle(
                    ceo_id="12345",
                    html_path="articles/12345/article.html",
                    pages=[
                        SIPPage(page_number=1, alto_path="articles/12345/001.alto.xml")
                    ],
                )
            ],
            mets_path="mets.xml",
            status="sealed",
        )

        # Serialize to JSON
        json_str = manifest.model_dump_json()
        data = json.loads(json_str)

        assert data["id"] == "2026-01-15"
        assert data["pip_id"] == "2026-01-15"
        assert data["status"] == "sealed"
        assert len(data["articles"]) == 1

        # Deserialize from JSON
        restored = SIPManifest.model_validate_json(json_str)
        assert restored.id == manifest.id
        assert restored.articles[0].ceo_id == "12345"
        assert restored.articles[0].pages[0].page_number == 1
