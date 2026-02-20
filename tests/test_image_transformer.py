"""Tests for the Image Transformer."""

import json
from pathlib import Path

import fitz  # PyMuPDF
import pytest

from periodical_distiller.transformers.image_transformer import ImageTransformer
from schemas.sip import SIPArticle, SIPManifest, SIPPage

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pdf(path: Path, pages: int = 1) -> None:
    """Write a minimal PDF with *pages* pages to *path*."""
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page(width=595, height=842)
        page.insert_text((50, 100), f"Page {i + 1} content")
    doc.save(str(path))
    doc.close()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sip_with_pdf(tmp_path: Path) -> Path:
    """SIP with one article, a one-page PDF, and the manifest pre-populated."""
    sip_dir = tmp_path / "sips" / "2026-01-29"
    article_dir = sip_dir / "articles" / "12345"
    article_dir.mkdir(parents=True)

    _make_pdf(article_dir / "article.pdf", pages=1)

    manifest = SIPManifest(
        id="2026-01-29",
        pip_id="2026-01-29",
        articles=[
            SIPArticle(
                ceo_id="12345",
                pdf_path="articles/12345/article.pdf",
                pages=[SIPPage(page_number=1, alto_path="articles/12345/001.alto.xml")],
            )
        ],
    )
    (sip_dir / "sip-manifest.json").write_text(manifest.model_dump_json(indent=2))
    return sip_dir


@pytest.fixture
def sip_with_multipage_pdf(tmp_path: Path) -> Path:
    """SIP with one article containing a two-page PDF."""
    sip_dir = tmp_path / "sips" / "2026-01-30"
    article_dir = sip_dir / "articles" / "67890"
    article_dir.mkdir(parents=True)

    _make_pdf(article_dir / "article.pdf", pages=2)

    manifest = SIPManifest(
        id="2026-01-30",
        pip_id="2026-01-30",
        articles=[
            SIPArticle(
                ceo_id="67890",
                pdf_path="articles/67890/article.pdf",
                pages=[
                    SIPPage(page_number=1, alto_path="articles/67890/001.alto.xml"),
                    SIPPage(page_number=2, alto_path="articles/67890/002.alto.xml"),
                ],
            )
        ],
    )
    (sip_dir / "sip-manifest.json").write_text(manifest.model_dump_json(indent=2))
    return sip_dir


@pytest.fixture
def sip_multiple_articles(tmp_path: Path) -> Path:
    """SIP with two articles, each with a one-page PDF."""
    sip_dir = tmp_path / "sips" / "2026-01-31"
    sip_dir.mkdir(parents=True)

    for ceo_id in ("11111", "22222"):
        article_dir = sip_dir / "articles" / ceo_id
        article_dir.mkdir(parents=True)
        _make_pdf(article_dir / "article.pdf", pages=1)

    manifest = SIPManifest(
        id="2026-01-31",
        pip_id="2026-01-31",
        articles=[
            SIPArticle(
                ceo_id="11111",
                pdf_path="articles/11111/article.pdf",
                pages=[SIPPage(page_number=1, alto_path="articles/11111/001.alto.xml")],
            ),
            SIPArticle(
                ceo_id="22222",
                pdf_path="articles/22222/article.pdf",
                pages=[SIPPage(page_number=1, alto_path="articles/22222/001.alto.xml")],
            ),
        ],
    )
    (sip_dir / "sip-manifest.json").write_text(manifest.model_dump_json(indent=2))
    return sip_dir


# ---------------------------------------------------------------------------
# Tests: Initialization
# ---------------------------------------------------------------------------

class TestImageTransformerInit:
    def test_instantiation(self):
        """ImageTransformer can be instantiated with no arguments."""
        transformer = ImageTransformer()
        assert transformer is not None


# ---------------------------------------------------------------------------
# Tests: transform() – file creation
# ---------------------------------------------------------------------------

class TestImageTransformerTransform:
    def test_transform_creates_jpeg_file(self, sip_with_pdf):
        """transform() writes a JPEG file at the expected path."""
        ImageTransformer().transform(sip_with_pdf)
        img_path = sip_with_pdf / "articles" / "12345" / "001.jpg"
        assert img_path.exists()

    def test_transform_returns_sip_manifest(self, sip_with_pdf):
        """transform() returns a SIPManifest."""
        result = ImageTransformer().transform(sip_with_pdf)
        assert isinstance(result, SIPManifest)
        assert result.id == "2026-01-29"

    def test_transform_sets_image_path_on_page(self, sip_with_pdf):
        """transform() sets image_path on each SIPPage."""
        result = ImageTransformer().transform(sip_with_pdf)
        page = result.articles[0].pages[0]
        assert page.image_path == "articles/12345/001.jpg"

    def test_transform_writes_updated_manifest(self, sip_with_pdf):
        """transform() rewrites the SIP manifest to disk with image_path set."""
        ImageTransformer().transform(sip_with_pdf)
        data = json.loads((sip_with_pdf / "sip-manifest.json").read_text())
        page = data["articles"][0]["pages"][0]
        assert page["image_path"] == "articles/12345/001.jpg"
        assert len(data.get("validation_errors", [])) == 0

    def test_transform_creates_image_for_each_page(self, sip_with_multipage_pdf):
        """transform() creates one JPEG per page."""
        ImageTransformer().transform(sip_with_multipage_pdf)
        article_dir = sip_with_multipage_pdf / "articles" / "67890"
        assert (article_dir / "001.jpg").exists()
        assert (article_dir / "002.jpg").exists()

    def test_transform_creates_images_for_multiple_articles(self, sip_multiple_articles):
        """transform() processes every article in the manifest."""
        ImageTransformer().transform(sip_multiple_articles)
        assert (sip_multiple_articles / "articles" / "11111" / "001.jpg").exists()
        assert (sip_multiple_articles / "articles" / "22222" / "001.jpg").exists()

    def test_image_is_valid_jpeg(self, sip_with_pdf):
        """The generated file is a valid JPEG (starts with JPEG magic bytes)."""
        ImageTransformer().transform(sip_with_pdf)
        img_path = sip_with_pdf / "articles" / "12345" / "001.jpg"
        data = img_path.read_bytes()
        assert data[:2] == b"\xff\xd8"  # JPEG magic bytes


# ---------------------------------------------------------------------------
# Tests: Error handling
# ---------------------------------------------------------------------------

class TestImageTransformerErrorHandling:
    def test_skips_article_without_pdf_path(self, tmp_path):
        """transform() skips articles that have no pdf_path."""
        sip_dir = tmp_path / "sip"
        sip_dir.mkdir()

        manifest = SIPManifest(
            id="no-pdf",
            pip_id="no-pdf",
            articles=[SIPArticle(ceo_id="99999", pdf_path=None)],
        )
        (sip_dir / "sip-manifest.json").write_text(manifest.model_dump_json(indent=2))

        result = ImageTransformer().transform(sip_dir)
        assert len(result.validation_errors) == 0

    def test_skips_article_without_pages(self, tmp_path):
        """transform() skips articles that have no pages list."""
        sip_dir = tmp_path / "sip"
        article_dir = sip_dir / "articles" / "99999"
        article_dir.mkdir(parents=True)
        _make_pdf(article_dir / "article.pdf", pages=1)

        manifest = SIPManifest(
            id="no-pages",
            pip_id="no-pages",
            articles=[
                SIPArticle(
                    ceo_id="99999",
                    pdf_path="articles/99999/article.pdf",
                    pages=[],
                )
            ],
        )
        (sip_dir / "sip-manifest.json").write_text(manifest.model_dump_json(indent=2))

        result = ImageTransformer().transform(sip_dir)
        assert len(result.validation_errors) == 0

    def test_records_error_for_missing_pdf(self, tmp_path):
        """transform() records a validation error when the PDF file is missing."""
        sip_dir = tmp_path / "sip"
        article_dir = sip_dir / "articles" / "99999"
        article_dir.mkdir(parents=True)
        # Intentionally do NOT create the PDF

        manifest = SIPManifest(
            id="missing-pdf",
            pip_id="missing-pdf",
            articles=[
                SIPArticle(
                    ceo_id="99999",
                    pdf_path="articles/99999/article.pdf",
                    pages=[SIPPage(page_number=1, alto_path="articles/99999/001.alto.xml")],
                )
            ],
        )
        (sip_dir / "sip-manifest.json").write_text(manifest.model_dump_json(indent=2))

        result = ImageTransformer().transform(sip_dir)
        assert len(result.validation_errors) == 1
        assert "99999" in result.validation_errors[0]

    def test_continues_after_article_error(self, tmp_path):
        """transform() processes remaining articles after one fails."""
        sip_dir = tmp_path / "sip"
        sip_dir.mkdir()

        # First article: PDF is missing
        (sip_dir / "articles" / "bad").mkdir(parents=True)

        # Second article: valid PDF
        good_dir = sip_dir / "articles" / "good"
        good_dir.mkdir(parents=True)
        _make_pdf(good_dir / "article.pdf", pages=1)

        manifest = SIPManifest(
            id="partial",
            pip_id="partial",
            articles=[
                SIPArticle(
                    ceo_id="bad",
                    pdf_path="articles/bad/article.pdf",
                    pages=[SIPPage(page_number=1, alto_path="articles/bad/001.alto.xml")],
                ),
                SIPArticle(
                    ceo_id="good",
                    pdf_path="articles/good/article.pdf",
                    pages=[SIPPage(page_number=1, alto_path="articles/good/001.alto.xml")],
                ),
            ],
        )
        (sip_dir / "sip-manifest.json").write_text(manifest.model_dump_json(indent=2))

        result = ImageTransformer().transform(sip_dir)

        assert len(result.validation_errors) == 1
        assert "bad" in result.validation_errors[0]
        assert (sip_dir / "articles" / "good" / "001.jpg").exists()
