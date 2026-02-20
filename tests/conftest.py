"""Pytest fixtures for Periodical Distiller tests."""

import json

import pytest


@pytest.fixture
def tmp_buckets(tmp_path):
    """Create temporary bucket directories for pipeline testing."""
    buckets = {
        "harvest": tmp_path / "01_harvest",
        "html": tmp_path / "02_html",
        "pdf": tmp_path / "03_pdf",
        "alto": tmp_path / "04_alto",
        "mods": tmp_path / "05_mods",
        "complete": tmp_path / "06_complete",
    }
    for bucket in buckets.values():
        bucket.mkdir(parents=True)
    return buckets


@pytest.fixture
def sample_ceo_record():
    """Sample CEO3 record for testing.

    This matches the structure returned by the CEO3 API with properly
    typed nested objects.
    """
    return {
        "id": "12345",
        "uuid": "abc-123-def-456",
        "slug": "test-article-headline",
        "seo_title": "Test Article SEO Title",
        "seo_description": "Test article description for SEO",
        "seo_image": None,
        "headline": "Test Article Headline",
        "subhead": "A subheadline for testing",
        "abstract": "<p>This is the article abstract.</p>",
        "content": "<p>This is the main article content.</p><p>It has multiple paragraphs.</p>",
        "infobox": None,
        "template": "standard",
        "short_token": "abc123",
        "status": "published",
        "weight": "0",
        "media_id": "",
        "created_at": "2026-01-15 10:00:00",
        "modified_at": "2026-01-15 12:00:00",
        "published_at": "2026-01-15 14:00:00",
        "metadata": [],
        "hits": "100",
        "normalized_tags": "",
        "ceo_id": "12345",
        "ssts_id": None,
        "ssts_path": None,
        "tags": [
            {
                "id": "1",
                "uuid": "tag-uuid-1",
                "name": "Campus News",
                "slug": "campus-news",
                "ceo_id": "t1",
                "metadata": None,
            },
            {
                "id": "2",
                "uuid": "tag-uuid-2",
                "name": "University",
                "slug": "university",
                "ceo_id": "t2",
                "metadata": None,
            },
        ],
        "authors": [
            {
                "id": "a1",
                "uuid": "author-uuid-1",
                "name": "John Doe",
                "email": "john@example.com",
                "slug": "john-doe",
                "bio": "",
                "tagline": "",
                "ceo_id": "author1",
                "status": "active",
                "metadata": None,
            },
            {
                "id": "a2",
                "uuid": "author-uuid-2",
                "name": "Jane Smith",
                "email": "jane@example.com",
                "slug": "jane-smith",
                "bio": "",
                "tagline": "",
                "ceo_id": "author2",
                "status": "active",
                "metadata": None,
            },
        ],
        "dominantMedia": None,
    }


@pytest.fixture
def sample_article_token_content(sample_ceo_record):
    """Sample article token content for pipeline testing."""
    return {
        "id": "12345",
        "issue_id": "2026-01-15",
        "ceo_record": sample_ceo_record,
        "html_path": None,
        "pdf_path": None,
        "alto_paths": [],
        "page_count": 0,
        "error": None,
        "log": [],
    }


@pytest.fixture
def sample_issue_token_content():
    """Sample issue token content for pipeline testing."""
    return {
        "id": "2026-01-15",
        "date_range": ["2026-01-15", "2026-01-15"],
        "title": "The Daily Princetonian - January 15, 2026",
        "article_ids": ["12345", "12346", "12347"],
        "articles": [],
        "mets_path": None,
        "validation_errors": [],
        "log": [],
    }


@pytest.fixture
def sample_token_file(tmp_path, sample_article_token_content):
    """Create a sample token JSON file."""
    token_path = tmp_path / "12345.json"
    token_path.write_text(json.dumps(sample_article_token_content, indent=2))
    return token_path
