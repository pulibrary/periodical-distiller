"""Tests for schema definitions."""

from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from schemas import Article, Issue, Page
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
