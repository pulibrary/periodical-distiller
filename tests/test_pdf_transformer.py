"""Tests for the PDF Transformer."""

import json
from pathlib import Path

import pytest

from periodical_distiller.transformers.pdf_transformer import PDFTransformer
from schemas.sip import SIPArticle, SIPManifest


@pytest.fixture
def sample_sip_structure(tmp_path):
    """Create a sample SIP directory structure for testing."""
    sip_dir = tmp_path / "sips" / "2026-01-29"
    sip_dir.mkdir(parents=True)

    article_dir = sip_dir / "articles" / "12345"
    article_dir.mkdir(parents=True)

    images_dir = article_dir / "images"
    images_dir.mkdir()

    test_image = images_dir / "test-image.jpg"
    # Create a minimal valid JPEG (1x1 pixel)
    jpeg_bytes = bytes([
        0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01,
        0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
        0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08, 0x07, 0x07, 0x07, 0x09,
        0x09, 0x08, 0x0A, 0x0C, 0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12,
        0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D, 0x1A, 0x1C, 0x1C, 0x20,
        0x24, 0x2E, 0x27, 0x20, 0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29,
        0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27, 0x39, 0x3D, 0x38, 0x32,
        0x3C, 0x2E, 0x33, 0x34, 0x32, 0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x00, 0x01,
        0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0xFF, 0xC4, 0x00, 0x1F, 0x00, 0x00,
        0x01, 0x05, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
        0x09, 0x0A, 0x0B, 0xFF, 0xC4, 0x00, 0xB5, 0x10, 0x00, 0x02, 0x01, 0x03,
        0x03, 0x02, 0x04, 0x03, 0x05, 0x05, 0x04, 0x04, 0x00, 0x00, 0x01, 0x7D,
        0x01, 0x02, 0x03, 0x00, 0x04, 0x11, 0x05, 0x12, 0x21, 0x31, 0x41, 0x06,
        0x13, 0x51, 0x61, 0x07, 0x22, 0x71, 0x14, 0x32, 0x81, 0x91, 0xA1, 0x08,
        0x23, 0x42, 0xB1, 0xC1, 0x15, 0x52, 0xD1, 0xF0, 0x24, 0x33, 0x62, 0x72,
        0x82, 0x09, 0x0A, 0x16, 0x17, 0x18, 0x19, 0x1A, 0x25, 0x26, 0x27, 0x28,
        0x29, 0x2A, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39, 0x3A, 0x43, 0x44, 0x45,
        0x46, 0x47, 0x48, 0x49, 0x4A, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59,
        0x5A, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68, 0x69, 0x6A, 0x73, 0x74, 0x75,
        0x76, 0x77, 0x78, 0x79, 0x7A, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89,
        0x8A, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0x98, 0x99, 0x9A, 0xA2, 0xA3,
        0xA4, 0xA5, 0xA6, 0xA7, 0xA8, 0xA9, 0xAA, 0xB2, 0xB3, 0xB4, 0xB5, 0xB6,
        0xB7, 0xB8, 0xB9, 0xBA, 0xC2, 0xC3, 0xC4, 0xC5, 0xC6, 0xC7, 0xC8, 0xC9,
        0xCA, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8, 0xD9, 0xDA, 0xE1, 0xE2,
        0xE3, 0xE4, 0xE5, 0xE6, 0xE7, 0xE8, 0xE9, 0xEA, 0xF1, 0xF2, 0xF3, 0xF4,
        0xF5, 0xF6, 0xF7, 0xF8, 0xF9, 0xFA, 0xFF, 0xDA, 0x00, 0x08, 0x01, 0x01,
        0x00, 0x00, 0x3F, 0x00, 0xFB, 0xD5, 0xDB, 0x20, 0xA8, 0xF1, 0x42, 0xCD,
        0xAB, 0xB5, 0x85, 0x8D, 0x94, 0x8F, 0x1F, 0xFF, 0xD9
    ])
    test_image.write_bytes(jpeg_bytes)

    html_content = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Test Article Headline</title>
    <link rel="stylesheet" href="../../article.css">
</head>
<body>
    <article>
        <header>
            <h1>Test Article Headline</h1>
            <p class="subhead">A test subheadline</p>
            <p class="meta">
                <span class="meta-item">January 29, 2026</span>
                <span class="meta-item">By John Doe</span>
            </p>
        </header>
        <div class="content">
            <p>Test content with <strong>formatting</strong>.</p>
            <p>Another paragraph of content.</p>
        </div>
    </article>
</body>
</html>"""
    html_path = article_dir / "article.html"
    html_path.write_text(html_content)

    css_content = """@page {
    size: letter;
    margin: 2.5cm;
}
body {
    font-family: Georgia, serif;
    font-size: 11pt;
}
h1 { font-size: 24pt; }
"""
    css_path = sip_dir / "article.css"
    css_path.write_text(css_content)

    manifest = SIPManifest(
        id="2026-01-29",
        pip_id="2026-01-29",
        pip_path=str(tmp_path / "pips" / "2026-01-29"),
        articles=[
            SIPArticle(
                ceo_id="12345",
                html_path="articles/12345/article.html",
            )
        ],
        status="sealed",
    )
    manifest_path = sip_dir / "sip-manifest.json"
    manifest_path.write_text(manifest.model_dump_json(indent=2))

    return sip_dir


@pytest.fixture
def sample_sip_with_image(tmp_path):
    """Create a SIP with an HTML file that includes an image."""
    sip_dir = tmp_path / "sips" / "2026-01-30"
    sip_dir.mkdir(parents=True)

    article_dir = sip_dir / "articles" / "67890"
    article_dir.mkdir(parents=True)

    images_dir = article_dir / "images"
    images_dir.mkdir()

    # Create a minimal valid 1x1 red PNG using proper zlib compression
    import zlib

    # IHDR chunk data: 1x1, 8-bit RGB
    ihdr_data = b'\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00'

    # Raw pixel data: filter byte (0) + RGB (255, 0, 0)
    raw_data = b'\x00\xff\x00\x00'
    compressed = zlib.compress(raw_data)

    def make_chunk(chunk_type: bytes, data: bytes) -> bytes:
        import struct
        length = struct.pack(">I", len(data))
        crc = zlib.crc32(chunk_type + data) & 0xffffffff
        crc_bytes = struct.pack(">I", crc)
        return length + chunk_type + data + crc_bytes

    png_bytes = (
        b'\x89PNG\r\n\x1a\n'
        + make_chunk(b'IHDR', ihdr_data)
        + make_chunk(b'IDAT', compressed)
        + make_chunk(b'IEND', b'')
    )
    test_image = images_dir / "featured-photo.png"
    test_image.write_bytes(png_bytes)

    html_content = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Article with Image</title>
    <link rel="stylesheet" href="../../article.css">
</head>
<body>
    <article>
        <header>
            <h1>Article with Image</h1>
        </header>
        <div class="featured-image">
            <img src="images/featured-photo.png" alt="Featured photo">
        </div>
        <div class="content">
            <p>Article content with an image.</p>
        </div>
    </article>
</body>
</html>"""
    html_path = article_dir / "article.html"
    html_path.write_text(html_content)

    css_content = """@page {
    size: letter;
    margin: 2.5cm;
}
body {
    font-family: Georgia, serif;
}
.featured-image img {
    max-width: 100%;
}
"""
    css_path = sip_dir / "article.css"
    css_path.write_text(css_content)

    manifest = SIPManifest(
        id="2026-01-30",
        pip_id="2026-01-30",
        pip_path=str(tmp_path / "pips" / "2026-01-30"),
        articles=[
            SIPArticle(
                ceo_id="67890",
                html_path="articles/67890/article.html",
            )
        ],
        status="sealed",
    )
    manifest_path = sip_dir / "sip-manifest.json"
    manifest_path.write_text(manifest.model_dump_json(indent=2))

    return sip_dir


@pytest.fixture
def sample_sip_multiple_articles(tmp_path):
    """Create a SIP with multiple articles."""
    sip_dir = tmp_path / "sips" / "2026-01-31"
    sip_dir.mkdir(parents=True)

    for ceo_id, title in [("11111", "First Article"), ("22222", "Second Article")]:
        article_dir = sip_dir / "articles" / ceo_id
        article_dir.mkdir(parents=True)

        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
</head>
<body>
    <article>
        <h1>{title}</h1>
        <p>Content for {title}.</p>
    </article>
</body>
</html>"""
        html_path = article_dir / "article.html"
        html_path.write_text(html_content)

    css_path = sip_dir / "article.css"
    css_path.write_text("body { font-family: serif; }")

    manifest = SIPManifest(
        id="2026-01-31",
        pip_id="2026-01-31",
        pip_path=str(tmp_path / "pips" / "2026-01-31"),
        articles=[
            SIPArticle(ceo_id="11111", html_path="articles/11111/article.html"),
            SIPArticle(ceo_id="22222", html_path="articles/22222/article.html"),
        ],
        status="sealed",
    )
    manifest_path = sip_dir / "sip-manifest.json"
    manifest_path.write_text(manifest.model_dump_json(indent=2))

    return sip_dir


class TestPDFTransformerInit:
    """Tests for PDFTransformer initialization."""

    def test_init_default_values(self):
        """PDFTransformer uses default values."""
        transformer = PDFTransformer()
        assert transformer.base_url is None
        assert transformer.stylesheet_name == "article.css"

    def test_init_custom_base_url(self):
        """PDFTransformer accepts custom base_url."""
        transformer = PDFTransformer(base_url="https://example.com/")
        assert transformer.base_url == "https://example.com/"

    def test_init_custom_stylesheet(self):
        """PDFTransformer accepts custom stylesheet name."""
        transformer = PDFTransformer(stylesheet_name="custom.css")
        assert transformer.stylesheet_name == "custom.css"

    def test_init_custom_stylesheets_dir(self, tmp_path):
        """PDFTransformer accepts custom stylesheets directory."""
        transformer = PDFTransformer(stylesheets_dir=tmp_path)
        assert transformer.stylesheets_dir == tmp_path


class TestPDFTransformerTransform:
    """Tests for PDFTransformer.transform() method."""

    def test_transform_creates_pdf_file(self, sample_sip_structure):
        """transform() generates a PDF file for each article."""
        transformer = PDFTransformer()
        transformer.transform(sample_sip_structure)

        pdf_path = sample_sip_structure / "articles" / "12345" / "article.pdf"
        assert pdf_path.exists()

    def test_transform_creates_valid_pdf(self, sample_sip_structure):
        """transform() creates a valid PDF file."""
        transformer = PDFTransformer()
        transformer.transform(sample_sip_structure)

        pdf_path = sample_sip_structure / "articles" / "12345" / "article.pdf"
        content = pdf_path.read_bytes()

        # Check PDF magic bytes
        assert content[:4] == b"%PDF"

    def test_transform_returns_sip_manifest(self, sample_sip_structure):
        """transform() returns a SIPManifest."""
        transformer = PDFTransformer()
        manifest = transformer.transform(sample_sip_structure)

        assert isinstance(manifest, SIPManifest)
        assert manifest.id == "2026-01-29"

    def test_transform_updates_pdf_path(self, sample_sip_structure):
        """transform() updates article.pdf_path in manifest."""
        transformer = PDFTransformer()
        manifest = transformer.transform(sample_sip_structure)

        assert manifest.articles[0].pdf_path == "articles/12345/article.pdf"

    def test_transform_writes_updated_manifest(self, sample_sip_structure):
        """transform() writes the updated manifest to disk."""
        transformer = PDFTransformer()
        transformer.transform(sample_sip_structure)

        manifest_path = sample_sip_structure / "sip-manifest.json"
        data = json.loads(manifest_path.read_text())

        assert data["articles"][0]["pdf_path"] == "articles/12345/article.pdf"

    def test_transform_multiple_articles(self, sample_sip_multiple_articles):
        """transform() generates PDFs for all articles."""
        transformer = PDFTransformer()
        manifest = transformer.transform(sample_sip_multiple_articles)

        assert len(manifest.articles) == 2

        for article in manifest.articles:
            assert article.pdf_path is not None
            pdf_path = sample_sip_multiple_articles / article.pdf_path
            assert pdf_path.exists()


class TestPDFTransformerPageCounting:
    """Tests for PDF page counting."""

    def test_transform_sets_pages_list(self, sample_sip_structure):
        """transform() populates article.pages with SIPPage objects."""
        transformer = PDFTransformer()
        manifest = transformer.transform(sample_sip_structure)

        article = manifest.articles[0]
        assert len(article.pages) >= 1

    def test_transform_pages_have_correct_page_numbers(self, sample_sip_structure):
        """transform() sets sequential page numbers starting from 1."""
        transformer = PDFTransformer()
        manifest = transformer.transform(sample_sip_structure)

        article = manifest.articles[0]
        for i, page in enumerate(article.pages):
            assert page.page_number == i + 1

    def test_transform_pages_have_alto_paths(self, sample_sip_structure):
        """transform() sets alto_path for each page."""
        transformer = PDFTransformer()
        manifest = transformer.transform(sample_sip_structure)

        article = manifest.articles[0]
        for i, page in enumerate(article.pages):
            expected_path = f"articles/12345/{i + 1:03d}.alto.xml"
            assert page.alto_path == expected_path

    def test_count_pages_returns_correct_count(self, sample_sip_structure):
        """_count_pages() returns the correct number of pages."""
        transformer = PDFTransformer()

        # First generate the PDF
        transformer.transform(sample_sip_structure)

        pdf_path = sample_sip_structure / "articles" / "12345" / "article.pdf"
        page_count = transformer._count_pages(pdf_path)

        assert page_count >= 1
        assert isinstance(page_count, int)


class TestPDFTransformerImageHandling:
    """Tests for handling images in HTML."""

    def test_transform_renders_html_with_images(self, sample_sip_with_image):
        """transform() successfully renders HTML containing images."""
        transformer = PDFTransformer()
        manifest = transformer.transform(sample_sip_with_image)

        assert manifest.articles[0].pdf_path is not None

        pdf_path = sample_sip_with_image / "articles" / "67890" / "article.pdf"
        assert pdf_path.exists()

        # Verify it's a valid PDF
        content = pdf_path.read_bytes()
        assert content[:4] == b"%PDF"


class TestPDFTransformerErrorHandling:
    """Tests for PDFTransformer error handling."""

    def test_transform_skips_article_without_html_path(self, tmp_path):
        """transform() skips articles without html_path."""
        sip_dir = tmp_path / "sips" / "no-html"
        sip_dir.mkdir(parents=True)

        manifest = SIPManifest(
            id="no-html",
            pip_id="no-html",
            articles=[
                SIPArticle(ceo_id="99999", html_path=None),
            ],
            status="sealed",
        )
        manifest_path = sip_dir / "sip-manifest.json"
        manifest_path.write_text(manifest.model_dump_json(indent=2))

        transformer = PDFTransformer()
        result = transformer.transform(sip_dir)

        # Should not have pdf_path set
        assert result.articles[0].pdf_path is None
        assert len(result.validation_errors) == 0

    def test_transform_records_error_for_missing_html(self, tmp_path):
        """transform() records error when HTML file is missing."""
        sip_dir = tmp_path / "sips" / "missing-html"
        sip_dir.mkdir(parents=True)

        article_dir = sip_dir / "articles" / "99999"
        article_dir.mkdir(parents=True)

        manifest = SIPManifest(
            id="missing-html",
            pip_id="missing-html",
            articles=[
                SIPArticle(
                    ceo_id="99999",
                    html_path="articles/99999/article.html",  # File doesn't exist
                ),
            ],
            status="sealed",
        )
        manifest_path = sip_dir / "sip-manifest.json"
        manifest_path.write_text(manifest.model_dump_json(indent=2))

        transformer = PDFTransformer()
        result = transformer.transform(sip_dir)

        assert len(result.validation_errors) == 1
        assert "99999" in result.validation_errors[0]

    def test_transform_continues_after_error(self, tmp_path):
        """transform() continues processing after an article error."""
        sip_dir = tmp_path / "sips" / "partial"
        sip_dir.mkdir(parents=True)

        # First article: missing HTML
        missing_dir = sip_dir / "articles" / "missing"
        missing_dir.mkdir(parents=True)

        # Second article: valid HTML
        valid_dir = sip_dir / "articles" / "valid"
        valid_dir.mkdir(parents=True)

        html_content = """<!DOCTYPE html>
<html>
<head><title>Valid</title></head>
<body><h1>Valid Article</h1></body>
</html>"""
        (valid_dir / "article.html").write_text(html_content)

        manifest = SIPManifest(
            id="partial",
            pip_id="partial",
            articles=[
                SIPArticle(
                    ceo_id="missing",
                    html_path="articles/missing/article.html",
                ),
                SIPArticle(
                    ceo_id="valid",
                    html_path="articles/valid/article.html",
                ),
            ],
            status="sealed",
        )
        manifest_path = sip_dir / "sip-manifest.json"
        manifest_path.write_text(manifest.model_dump_json(indent=2))

        transformer = PDFTransformer()
        result = transformer.transform(sip_dir)

        # First article should have an error
        assert len(result.validation_errors) == 1
        assert "missing" in result.validation_errors[0]

        # Second article should have a PDF
        assert result.articles[1].pdf_path == "articles/valid/article.pdf"
        assert (sip_dir / "articles" / "valid" / "article.pdf").exists()


class TestPDFTransformerStylesheet:
    """Tests for stylesheet loading."""

    def test_transform_uses_sip_stylesheet(self, sample_sip_structure):
        """transform() uses stylesheet from SIP directory."""
        transformer = PDFTransformer()
        transformer.transform(sample_sip_structure)

        # If it completes without error, the stylesheet was used
        pdf_path = sample_sip_structure / "articles" / "12345" / "article.pdf"
        assert pdf_path.exists()

    def test_transform_works_without_stylesheet(self, tmp_path):
        """transform() works even without a stylesheet."""
        sip_dir = tmp_path / "sips" / "no-css"
        sip_dir.mkdir(parents=True)

        article_dir = sip_dir / "articles" / "12345"
        article_dir.mkdir(parents=True)

        html_content = """<!DOCTYPE html>
<html>
<head><title>No CSS</title></head>
<body><h1>Article without CSS</h1></body>
</html>"""
        (article_dir / "article.html").write_text(html_content)

        manifest = SIPManifest(
            id="no-css",
            pip_id="no-css",
            articles=[
                SIPArticle(ceo_id="12345", html_path="articles/12345/article.html"),
            ],
            status="sealed",
        )
        manifest_path = sip_dir / "sip-manifest.json"
        manifest_path.write_text(manifest.model_dump_json(indent=2))

        transformer = PDFTransformer(stylesheet_name="nonexistent.css")
        manifest = transformer.transform(sip_dir)

        assert manifest.articles[0].pdf_path is not None
        pdf_path = sip_dir / "articles" / "12345" / "article.pdf"
        assert pdf_path.exists()
