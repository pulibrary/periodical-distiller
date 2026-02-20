"""Tests for the HTML Transformer and Jinja2 filters."""

import json

import pytest

from periodical_distiller.transformers.filters import (
    clean_content,
    format_authors,
    format_date,
    parse_media_caption,
    parse_tags,
)
from periodical_distiller.transformers.html_transformer import HTMLTransformer
from schemas.pip import PIPArticle, PIPManifest, PIPMedia


class TestFormatDate:
    """Tests for the format_date filter."""

    def test_format_standard_date(self):
        """Formats CEO3 datetime string to human-readable date."""
        result = format_date("2026-01-29 06:51:50")
        assert result == "January 29, 2026"

    def test_format_date_removes_leading_zero(self):
        """Removes leading zero from single-digit days."""
        result = format_date("2026-01-05 12:00:00")
        assert result == "January 5, 2026"

    def test_format_date_empty_string(self):
        """Returns empty string for empty input."""
        assert format_date("") == ""

    def test_format_date_none(self):
        """Returns empty string for None input."""
        assert format_date(None) == ""

    def test_format_date_invalid_format(self):
        """Returns original string for invalid format."""
        result = format_date("invalid-date")
        assert result == "invalid-date"


class TestFormatAuthors:
    """Tests for the format_authors filter."""

    def test_format_single_author_dict(self):
        """Formats single author from dict."""
        authors = [{"name": "John Doe"}]
        assert format_authors(authors) == "John Doe"

    def test_format_multiple_authors_dict(self):
        """Formats multiple authors as comma-separated list."""
        authors = [{"name": "John Doe"}, {"name": "Jane Smith"}]
        assert format_authors(authors) == "John Doe, Jane Smith"

    def test_format_authors_empty_list(self):
        """Returns empty string for empty list."""
        assert format_authors([]) == ""

    def test_format_authors_none(self):
        """Returns empty string for None."""
        assert format_authors(None) == ""

    def test_format_authors_skips_empty_names(self):
        """Skips authors with empty names."""
        authors = [{"name": "John"}, {"name": ""}, {"name": "Jane"}]
        assert format_authors(authors) == "John, Jane"

    def test_format_authors_with_objects(self):
        """Works with objects that have name attribute."""

        class Author:
            def __init__(self, name):
                self.name = name

        authors = [Author("John"), Author("Jane")]
        assert format_authors(authors) == "John, Jane"


class TestParseTags:
    """Tests for the parse_tags filter."""

    def test_parse_single_tag(self):
        """Extracts single tag name."""
        tags = [{"name": "news"}]
        assert parse_tags(tags) == ["news"]

    def test_parse_multiple_tags(self):
        """Extracts multiple tag names."""
        tags = [{"name": "news"}, {"name": "top"}, {"name": "featured"}]
        assert parse_tags(tags) == ["news", "top", "featured"]

    def test_parse_tags_empty_list(self):
        """Returns empty list for empty input."""
        assert parse_tags([]) == []

    def test_parse_tags_none(self):
        """Returns empty list for None."""
        assert parse_tags(None) == []

    def test_parse_tags_skips_empty_names(self):
        """Skips tags with empty names."""
        tags = [{"name": "news"}, {"name": ""}, {"name": "top"}]
        assert parse_tags(tags) == ["news", "top"]


class TestParseMediaCaption:
    """Tests for the parse_media_caption filter."""

    def test_parse_caption_and_credit(self):
        """Extracts both caption and credit from content."""
        content = '<h5>A beautiful photo.</h5><h6>John Doe / Daily Prince</h6>'
        result = parse_media_caption(content)
        assert result["caption"] == "A beautiful photo."
        assert result["credit"] == "John Doe / Daily Prince"

    def test_parse_caption_only(self):
        """Extracts caption when no credit present."""
        content = '<h5>Just a caption</h5>'
        result = parse_media_caption(content)
        assert result["caption"] == "Just a caption"
        assert result["credit"] == ""

    def test_parse_credit_only(self):
        """Extracts credit when no caption present."""
        content = '<h6>Photo by Jane</h6>'
        result = parse_media_caption(content)
        assert result["caption"] == ""
        assert result["credit"] == "Photo by Jane"

    def test_parse_empty_content(self):
        """Returns empty values for empty content."""
        result = parse_media_caption("")
        assert result["caption"] == ""
        assert result["credit"] == ""

    def test_parse_none_content(self):
        """Returns empty values for None content."""
        result = parse_media_caption(None)
        assert result["caption"] == ""
        assert result["credit"] == ""

    def test_parse_strips_whitespace(self):
        """Strips whitespace from extracted values."""
        content = '<h5>  Caption with spaces  </h5><h6>  Credit  </h6>'
        result = parse_media_caption(content)
        assert result["caption"] == "Caption with spaces"
        assert result["credit"] == "Credit"


class TestCleanContent:
    """Tests for the clean_content filter."""

    def test_clean_removes_script_tags(self):
        """Removes script tags and their content."""
        html = '<p>Hello</p><script>alert("x")</script><p>World</p>'
        assert clean_content(html) == "<p>Hello</p><p>World</p>"

    def test_clean_removes_multiline_scripts(self):
        """Removes multiline script tags."""
        html = """<p>Hello</p>
        <script>
            var x = 1;
            console.log(x);
        </script>
        <p>World</p>"""
        result = clean_content(html)
        assert "<script>" not in result
        assert "console.log" not in result

    def test_clean_removes_iframes(self):
        """Removes iframe tags."""
        html = '<p>Hello</p><iframe src="https://example.com"></iframe><p>World</p>'
        result = clean_content(html)
        assert "<iframe" not in result

    def test_clean_removes_self_closing_iframes(self):
        """Removes self-closing iframe tags."""
        html = '<p>Hello</p><iframe src="https://example.com" /><p>World</p>'
        result = clean_content(html)
        assert "<iframe" not in result

    def test_clean_removes_noscript_tags(self):
        """Removes noscript tags and their content."""
        html = '<p>Hello</p><noscript><img src="fallback.png"></noscript><p>World</p>'
        result = clean_content(html)
        assert "<noscript>" not in result
        assert "fallback.png" not in result

    def test_clean_preserves_regular_content(self):
        """Preserves normal HTML content."""
        html = "<p>Hello <strong>World</strong></p>"
        assert clean_content(html) == html

    def test_clean_empty_string(self):
        """Returns empty string for empty input."""
        assert clean_content("") == ""

    def test_clean_none(self):
        """Returns empty string for None."""
        assert clean_content(None) == ""


@pytest.fixture
def sample_pip_structure(tmp_path):
    """Create a sample PIP directory structure for testing."""
    pip_dir = tmp_path / "pips" / "2026-01-29"
    pip_dir.mkdir(parents=True)

    article_dir = pip_dir / "articles" / "12345"
    article_dir.mkdir(parents=True)

    images_dir = article_dir / "images"
    images_dir.mkdir()

    test_image = images_dir / "test-image.jpg"
    test_image.write_bytes(b"fake image content")

    ceo_record = {
        "id": "12345",
        "uuid": "test-uuid",
        "slug": "test-article",
        "ceo_id": "12345",
        "short_token": "abc123",
        "headline": "Test Article Headline",
        "subhead": "A test subheadline",
        "abstract": "<p>Test abstract</p>",
        "content": "<p>Test content with <strong>formatting</strong>.</p>",
        "infobox": None,
        "seo_title": None,
        "seo_description": None,
        "seo_image": None,
        "template": None,
        "status": "published",
        "weight": "0",
        "media_id": "",
        "created_at": "2026-01-29 10:00:00",
        "modified_at": "2026-01-29 12:00:00",
        "published_at": "2026-01-29 14:00:00",
        "hits": "100",
        "metadata": [],
        "normalized_tags": "",
        "tags": [{"id": "1", "uuid": "t1", "name": "news", "slug": "news", "ceo_id": "1", "metadata": None}],
        "authors": [
            {
                "id": "a1",
                "uuid": "auth1",
                "name": "John Doe",
                "email": "john@example.com",
                "slug": "john-doe",
                "bio": "",
                "tagline": "",
                "ceo_id": "a1",
                "status": "active",
                "metadata": None,
            }
        ],
        "dominantMedia": None,
    }
    ceo_record_path = article_dir / "ceo_record.json"
    ceo_record_path.write_text(json.dumps(ceo_record, indent=2))

    manifest = PIPManifest(
        id="2026-01-29",
        title="Test Issue",
        date_range=("2026-01-29", "2026-01-29"),
        articles=[
            PIPArticle(
                ceo_id="12345",
                ceo_record_path="articles/12345/ceo_record.json",
                media=[
                    PIPMedia(
                        original_url="https://example.com/test-image.jpg",
                        local_path="articles/12345/images/test-image.jpg",
                        media_type="image/jpeg",
                        checksum="abc123",
                    )
                ],
            )
        ],
        status="sealed",
    )
    manifest_path = pip_dir / "pip-manifest.json"
    manifest_path.write_text(manifest.model_dump_json(indent=2))

    return pip_dir


@pytest.fixture
def sample_pip_with_flourish(tmp_path):
    """Create a sample PIP with Flourish embed content."""
    pip_dir = tmp_path / "pips" / "2026-01-30"
    pip_dir.mkdir(parents=True)

    article_dir = pip_dir / "articles" / "67890"
    article_dir.mkdir(parents=True)

    charts_dir = article_dir / "charts"
    charts_dir.mkdir()

    chart_image = charts_dir / "flourish-12345678.png"
    chart_image.write_bytes(b"fake chart image")

    ceo_record = {
        "id": "67890",
        "uuid": "test-uuid-2",
        "slug": "article-with-chart",
        "ceo_id": "67890",
        "short_token": "xyz789",
        "headline": "Article with Flourish Chart",
        "subhead": None,
        "abstract": None,
        "content": (
            '<p>Before chart</p>'
            '<figure><div class="embed-code">'
            '<div class="flourish-embed flourish-chart" data-src="visualisation/12345678">'
            '<script src="https://public.flourish.studio/resources/embed.js"></script>'
            '<noscript><img src="https://public.flourish.studio/visualisation/12345678/thumbnail" '
            'width="100%" alt="chart visualization" /></noscript>'
            '</div></div></figure>'
            '<p>After chart</p>'
        ),
        "infobox": None,
        "seo_title": None,
        "seo_description": None,
        "seo_image": None,
        "template": None,
        "status": "published",
        "weight": "0",
        "media_id": "",
        "created_at": "2026-01-30 10:00:00",
        "modified_at": "2026-01-30 12:00:00",
        "published_at": "2026-01-30 14:00:00",
        "hits": "50",
        "metadata": [],
        "normalized_tags": "",
        "tags": [],
        "authors": [],
        "dominantMedia": None,
    }
    ceo_record_path = article_dir / "ceo_record.json"
    ceo_record_path.write_text(json.dumps(ceo_record, indent=2))

    manifest = PIPManifest(
        id="2026-01-30",
        title="Test Issue with Charts",
        date_range=("2026-01-30", "2026-01-30"),
        articles=[
            PIPArticle(
                ceo_id="67890",
                ceo_record_path="articles/67890/ceo_record.json",
                media=[
                    PIPMedia(
                        original_url="https://public.flourish.studio/visualisation/12345678/thumbnail",
                        local_path="articles/67890/charts/flourish-12345678.png",
                        media_type="image/png",
                        checksum="chart123",
                    )
                ],
            )
        ],
        status="sealed",
    )
    manifest_path = pip_dir / "pip-manifest.json"
    manifest_path.write_text(manifest.model_dump_json(indent=2))

    return pip_dir


@pytest.fixture
def sample_pip_with_dominant_media(tmp_path):
    """Create a sample PIP with dominant media (featured image)."""
    pip_dir = tmp_path / "pips" / "2026-01-31"
    pip_dir.mkdir(parents=True)

    article_dir = pip_dir / "articles" / "11111"
    article_dir.mkdir(parents=True)

    images_dir = article_dir / "images"
    images_dir.mkdir()

    featured_image = images_dir / "featured-photo.jpg"
    featured_image.write_bytes(b"fake featured image content")

    ceo_record = {
        "id": "11111",
        "uuid": "test-uuid-3",
        "slug": "article-with-featured-image",
        "ceo_id": "11111",
        "short_token": "feat123",
        "headline": "Article with Featured Image",
        "subhead": "A story with a beautiful photo",
        "abstract": "<p>Test abstract</p>",
        "content": "<p>Article body content.</p>",
        "infobox": None,
        "seo_title": None,
        "seo_description": None,
        "seo_image": None,
        "template": None,
        "status": "published",
        "weight": "0",
        "media_id": "m123",
        "dominantMedia": {
            "id": "m123",
            "uuid": "media-uuid",
            "attachment_uuid": "attach-uuid",
            "base_name": "featured-photo",
            "extension": "jpg",
            "preview_extension": "jpg",
            "title": "Featured Photo",
            "content": "<h5>View of campus from the library.</h5><h6>Jane Smith / The Daily Princetonian</h6>",
            "source": None,
            "click_through": None,
            "type": "image",
            "height": None,
            "width": None,
            "seo_title": None,
            "seo_description": None,
            "seo_image": None,
            "svg_preview": None,
            "status": "0",
            "weight": "0",
            "hits": "0",
            "transcoded": "0",
            "created_at": "2026-01-31 10:00:00",
            "modified_at": "2026-01-31 12:00:00",
            "published_at": None,
            "normalized_tags": "||",
            "ceo_id": "m456",
            "ssts_id": None,
            "ssts_path": None,
            "metadata": [],
            "authors": [],
        },
        "created_at": "2026-01-31 10:00:00",
        "modified_at": "2026-01-31 12:00:00",
        "published_at": "2026-01-31 14:00:00",
        "hits": "200",
        "metadata": [],
        "normalized_tags": "",
        "tags": [],
        "authors": [
            {
                "id": "a1",
                "uuid": "auth1",
                "name": "Test Author",
                "email": "test@example.com",
                "slug": "test-author",
                "bio": "",
                "tagline": "",
                "ceo_id": "a1",
                "status": "active",
                "metadata": None,
            }
        ],
    }
    ceo_record_path = article_dir / "ceo_record.json"
    ceo_record_path.write_text(json.dumps(ceo_record, indent=2))

    manifest = PIPManifest(
        id="2026-01-31",
        title="Test Issue with Featured Image",
        date_range=("2026-01-31", "2026-01-31"),
        articles=[
            PIPArticle(
                ceo_id="11111",
                ceo_record_path="articles/11111/ceo_record.json",
                media=[
                    PIPMedia(
                        original_url="https://example.com/featured-photo.jpg",
                        local_path="articles/11111/images/featured-photo.jpg",
                        media_type="image/jpeg",
                        checksum="featured123",
                    )
                ],
            )
        ],
        status="sealed",
    )
    manifest_path = pip_dir / "pip-manifest.json"
    manifest_path.write_text(manifest.model_dump_json(indent=2))

    return pip_dir


class TestHTMLTransformerInit:
    """Tests for HTMLTransformer initialization."""

    def test_init_default_values(self):
        """HTMLTransformer uses default template and stylesheet."""
        transformer = HTMLTransformer()
        assert transformer.template_name == "article.html.j2"
        assert transformer.stylesheet_name == "article.css"

    def test_init_custom_values(self, tmp_path):
        """HTMLTransformer accepts custom template and stylesheet."""
        transformer = HTMLTransformer(
            template_name="custom.html.j2",
            stylesheet_name="custom.css",
            templates_dir=tmp_path,
            stylesheets_dir=tmp_path,
        )
        assert transformer.template_name == "custom.html.j2"
        assert transformer.stylesheet_name == "custom.css"


class TestHTMLTransformerTransform:
    """Tests for HTMLTransformer.transform() method."""

    def test_transform_creates_sip_directory(self, sample_pip_structure, tmp_path):
        """transform() creates the SIP directory structure."""
        sip_dir = tmp_path / "sips" / "2026-01-29"

        transformer = HTMLTransformer()
        transformer.transform(sample_pip_structure, sip_dir)

        assert sip_dir.exists()
        assert (sip_dir / "articles").exists()
        assert (sip_dir / "article.css").exists()

    def test_transform_creates_article_html(self, sample_pip_structure, tmp_path):
        """transform() generates HTML for each article."""
        sip_dir = tmp_path / "sips" / "2026-01-29"

        transformer = HTMLTransformer()
        transformer.transform(sample_pip_structure, sip_dir)

        html_path = sip_dir / "articles" / "12345" / "article.html"
        assert html_path.exists()

        content = html_path.read_text()
        assert "Test Article Headline" in content
        assert "January 29, 2026" in content
        assert "John Doe" in content

    def test_transform_copies_images(self, sample_pip_structure, tmp_path):
        """transform() copies article images to SIP."""
        sip_dir = tmp_path / "sips" / "2026-01-29"

        transformer = HTMLTransformer()
        transformer.transform(sample_pip_structure, sip_dir)

        image_path = sip_dir / "articles" / "12345" / "images" / "test-image.jpg"
        assert image_path.exists()

    def test_transform_returns_sip_manifest(self, sample_pip_structure, tmp_path):
        """transform() returns a SIPManifest."""
        sip_dir = tmp_path / "sips" / "2026-01-29"

        transformer = HTMLTransformer()
        manifest = transformer.transform(sample_pip_structure, sip_dir)

        assert manifest.id == "2026-01-29"
        assert manifest.pip_id == "2026-01-29"
        assert len(manifest.articles) == 1
        assert manifest.articles[0].ceo_id == "12345"
        assert manifest.articles[0].html_path == "articles/12345/article.html"

    def test_transform_writes_sip_manifest(self, sample_pip_structure, tmp_path):
        """transform() writes sip-manifest.json."""
        sip_dir = tmp_path / "sips" / "2026-01-29"

        transformer = HTMLTransformer()
        transformer.transform(sample_pip_structure, sip_dir)

        manifest_path = sip_dir / "sip-manifest.json"
        assert manifest_path.exists()

        data = json.loads(manifest_path.read_text())
        assert data["id"] == "2026-01-29"
        assert data["status"] == "sealed"

    def test_transform_sets_stylesheet_path_in_html(self, sample_pip_structure, tmp_path):
        """transform() sets relative stylesheet path in HTML."""
        sip_dir = tmp_path / "sips" / "2026-01-29"

        transformer = HTMLTransformer()
        transformer.transform(sample_pip_structure, sip_dir)

        html_path = sip_dir / "articles" / "12345" / "article.html"
        content = html_path.read_text()
        assert '../../article.css' in content


class TestHTMLTransformerFlourishEmbeds:
    """Tests for Flourish embed replacement."""

    def test_transform_replaces_flourish_with_local_image(
        self, sample_pip_with_flourish, tmp_path
    ):
        """transform() replaces Flourish embeds with local chart images."""
        sip_dir = tmp_path / "sips" / "2026-01-30"

        transformer = HTMLTransformer()
        transformer.transform(sample_pip_with_flourish, sip_dir)

        html_path = sip_dir / "articles" / "67890" / "article.html"
        content = html_path.read_text()

        assert "flourish-embed" not in content
        assert "data-src" not in content
        assert '<script' not in content.lower() or "embed.js" not in content
        assert 'charts/flourish-12345678.png' in content
        assert 'class="chart-image"' in content

    def test_transform_copies_chart_images(self, sample_pip_with_flourish, tmp_path):
        """transform() copies chart images to SIP."""
        sip_dir = tmp_path / "sips" / "2026-01-30"

        transformer = HTMLTransformer()
        transformer.transform(sample_pip_with_flourish, sip_dir)

        chart_path = sip_dir / "articles" / "67890" / "charts" / "flourish-12345678.png"
        assert chart_path.exists()

    def test_replace_flourish_preserves_surrounding_content(self):
        """_replace_flourish_embeds preserves content around embeds."""
        transformer = HTMLTransformer()

        media = [
            PIPMedia(
                original_url="https://public.flourish.studio/visualisation/99999/thumbnail",
                local_path="articles/1/charts/flourish-99999.png",
                media_type="image/png",
            )
        ]

        content = (
            '<p>Before</p>'
            '<div class="flourish-embed" data-src="visualisation/99999">stuff</div>'
            '<p>After</p>'
        )

        result = transformer._replace_flourish_embeds(content, media, "1")

        assert "<p>Before</p>" in result
        assert "<p>After</p>" in result
        assert 'charts/flourish-99999.png' in result


class TestHTMLTransformerFeaturedImage:
    """Tests for dominant media / featured image rendering."""

    def test_transform_includes_featured_image(
        self, sample_pip_with_dominant_media, tmp_path
    ):
        """transform() includes featured image in HTML output."""
        sip_dir = tmp_path / "sips" / "2026-01-31"

        transformer = HTMLTransformer()
        transformer.transform(sample_pip_with_dominant_media, sip_dir)

        html_path = sip_dir / "articles" / "11111" / "article.html"
        content = html_path.read_text()

        assert 'class="featured-image"' in content
        assert 'images/featured-photo.jpg' in content

    def test_transform_includes_image_caption(
        self, sample_pip_with_dominant_media, tmp_path
    ):
        """transform() includes caption from dominant media content."""
        sip_dir = tmp_path / "sips" / "2026-01-31"

        transformer = HTMLTransformer()
        transformer.transform(sample_pip_with_dominant_media, sip_dir)

        html_path = sip_dir / "articles" / "11111" / "article.html"
        content = html_path.read_text()

        assert 'class="image-caption"' in content
        assert "View of campus from the library." in content

    def test_transform_includes_image_credit(
        self, sample_pip_with_dominant_media, tmp_path
    ):
        """transform() includes credit from dominant media content."""
        sip_dir = tmp_path / "sips" / "2026-01-31"

        transformer = HTMLTransformer()
        transformer.transform(sample_pip_with_dominant_media, sip_dir)

        html_path = sip_dir / "articles" / "11111" / "article.html"
        content = html_path.read_text()

        assert 'class="image-credit"' in content
        assert "Jane Smith / The Daily Princetonian" in content

    def test_transform_no_featured_image_without_dominant_media(
        self, sample_pip_structure, tmp_path
    ):
        """transform() does not include featured image when no dominant media."""
        sip_dir = tmp_path / "sips" / "2026-01-29"

        transformer = HTMLTransformer()
        transformer.transform(sample_pip_structure, sip_dir)

        html_path = sip_dir / "articles" / "12345" / "article.html"
        content = html_path.read_text()

        assert 'class="featured-image"' not in content

    def test_find_featured_image_path_returns_correct_path(self):
        """_find_featured_image_path returns relative path to image."""
        from schemas.ceo_item import CeoItem, CeoMedia

        transformer = HTMLTransformer()

        ceo_item = CeoItem(
            id="1",
            uuid="u1",
            slug="test",
            ceo_id="1",
            short_token="t1",
            headline="Test",
            status="published",
            weight="0",
            media_id="m1",
            dominant_media=CeoMedia(
                id="m1",
                uuid="mu1",
                attachment_uuid="au1",
                base_name="my-image",
                extension="jpg",
                preview_extension="jpg",
                status="0",
                weight="0",
                hits="0",
                transcoded="0",
                created_at="2026-01-01 10:00:00",
                modified_at="2026-01-01 10:00:00",
                ceo_id="mc1",
                type="image",
            ),
            created_at="2026-01-01 10:00:00",
            modified_at="2026-01-01 10:00:00",
            published_at="2026-01-01 10:00:00",
            hits="0",
            normalized_tags="",
        )

        media = [
            PIPMedia(
                original_url="https://example.com/my-image.jpg",
                local_path="articles/1/images/my-image.jpg",
                media_type="image/jpeg",
            )
        ]

        result = transformer._find_featured_image_path(ceo_item, media)
        assert result == "images/my-image.jpg"

    def test_find_featured_image_path_returns_none_without_dominant_media(self):
        """_find_featured_image_path returns None when no dominant media."""
        from schemas.ceo_item import CeoItem

        transformer = HTMLTransformer()

        ceo_item = CeoItem(
            id="1",
            uuid="u1",
            slug="test",
            ceo_id="1",
            short_token="t1",
            headline="Test",
            status="published",
            weight="0",
            media_id="",
            dominant_media=None,
            created_at="2026-01-01 10:00:00",
            modified_at="2026-01-01 10:00:00",
            published_at="2026-01-01 10:00:00",
            hits="0",
            normalized_tags="",
        )

        result = transformer._find_featured_image_path(ceo_item, [])
        assert result is None


class TestHTMLTransformerErrorHandling:
    """Tests for HTMLTransformer error handling."""

    def test_transform_records_article_errors(self, tmp_path):
        """transform() records errors for failed articles."""
        pip_dir = tmp_path / "pips" / "broken"
        pip_dir.mkdir(parents=True)

        manifest = PIPManifest(
            id="broken",
            title="Broken Issue",
            date_range=("2026-01-01", "2026-01-01"),
            articles=[
                PIPArticle(
                    ceo_id="99999",
                    ceo_record_path="articles/99999/ceo_record.json",
                    media=[],
                )
            ],
            status="sealed",
        )
        manifest_path = pip_dir / "pip-manifest.json"
        manifest_path.write_text(manifest.model_dump_json(indent=2))

        sip_dir = tmp_path / "sips" / "broken"

        transformer = HTMLTransformer()
        result = transformer.transform(pip_dir, sip_dir)

        assert len(result.validation_errors) == 1
        assert "99999" in result.validation_errors[0]

    def test_transform_continues_after_article_error(self, sample_pip_structure, tmp_path):
        """transform() continues processing after article errors."""
        pip_dir = sample_pip_structure

        manifest_path = pip_dir / "pip-manifest.json"
        manifest_data = json.loads(manifest_path.read_text())
        manifest_data["articles"].append({
            "ceo_id": "broken",
            "ceo_record_path": "articles/broken/ceo_record.json",
            "media": [],
        })
        manifest_path.write_text(json.dumps(manifest_data, indent=2))

        sip_dir = tmp_path / "sips" / "2026-01-29"

        transformer = HTMLTransformer()
        result = transformer.transform(pip_dir, sip_dir)

        assert len(result.articles) == 1
        assert result.articles[0].ceo_id == "12345"
        assert len(result.validation_errors) == 1
