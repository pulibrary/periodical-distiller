"""Tests for the ALTO Transformer."""

import json
from pathlib import Path

import fitz  # PyMuPDF
import pytest
from lxml import etree

from periodical_distiller.transformers.alto_transformer import ALTO_NS, ALTOTransformer
from schemas.sip import SIPArticle, SIPManifest, SIPPage

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_pdf(path: Path, pages: list[list[str]]) -> None:
    """Write a minimal PDF with text to *path*.

    Args:
        path: Destination file path.
        pages: List of pages; each page is a list of text strings to insert.
    """
    doc = fitz.open()
    for texts in pages:
        page = doc.new_page(width=595, height=842)
        y = 100
        for text in texts:
            page.insert_text((50, y), text)
            y += 20
    doc.save(str(path))
    doc.close()


def _parse_alto(path: Path) -> etree._Element:
    return etree.parse(str(path)).getroot()


def _alto_tag(local: str) -> str:
    return f"{{{ALTO_NS}}}{local}"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sip_with_pdf(tmp_path: Path) -> Path:
    """SIP with one article, a one-page PDF, and the manifest pre-populated."""
    sip_dir = tmp_path / "sips" / "2026-01-29"
    article_dir = sip_dir / "articles" / "12345"
    article_dir.mkdir(parents=True)

    _make_pdf(article_dir / "article.pdf", [["Hello World", "Second line of text"]])

    manifest = SIPManifest(
        id="2026-01-29",
        pip_id="2026-01-29",
        articles=[
            SIPArticle(
                ceo_id="12345",
                html_path="articles/12345/article.html",
                pdf_path="articles/12345/article.pdf",
                pages=[SIPPage(page_number=1, alto_path="articles/12345/001.alto.xml")],
            )
        ],
        status="sealed",
    )
    (sip_dir / "sip-manifest.json").write_text(manifest.model_dump_json(indent=2))
    return sip_dir


@pytest.fixture
def sip_with_multipage_pdf(tmp_path: Path) -> Path:
    """SIP with one article containing a two-page PDF."""
    sip_dir = tmp_path / "sips" / "2026-01-30"
    article_dir = sip_dir / "articles" / "67890"
    article_dir.mkdir(parents=True)

    _make_pdf(
        article_dir / "article.pdf",
        [["Page one content"], ["Page two content"]],
    )

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
        status="sealed",
    )
    (sip_dir / "sip-manifest.json").write_text(manifest.model_dump_json(indent=2))
    return sip_dir


@pytest.fixture
def sip_multiple_articles(tmp_path: Path) -> Path:
    """SIP with two articles, each with a one-page PDF."""
    sip_dir = tmp_path / "sips" / "2026-01-31"
    sip_dir.mkdir(parents=True)

    for ceo_id, text in [("11111", "First article"), ("22222", "Second article")]:
        article_dir = sip_dir / "articles" / ceo_id
        article_dir.mkdir(parents=True)
        _make_pdf(article_dir / "article.pdf", [[text]])

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
        status="sealed",
    )
    (sip_dir / "sip-manifest.json").write_text(manifest.model_dump_json(indent=2))
    return sip_dir


# ---------------------------------------------------------------------------
# Tests: Initialization
# ---------------------------------------------------------------------------


class TestALTOTransformerInit:
    def test_instantiation(self):
        """ALTOTransformer can be instantiated with no arguments."""
        transformer = ALTOTransformer()
        assert transformer is not None


# ---------------------------------------------------------------------------
# Tests: transform() – file creation
# ---------------------------------------------------------------------------


class TestALTOTransformerTransform:
    def test_transform_creates_alto_file(self, sip_with_pdf):
        """transform() writes an ALTO file at the path from the manifest."""
        ALTOTransformer().transform(sip_with_pdf)
        alto_path = sip_with_pdf / "articles" / "12345" / "001.alto.xml"
        assert alto_path.exists()

    def test_transform_returns_sip_manifest(self, sip_with_pdf):
        """transform() returns a SIPManifest."""
        result = ALTOTransformer().transform(sip_with_pdf)
        assert isinstance(result, SIPManifest)
        assert result.id == "2026-01-29"

    def test_transform_writes_updated_manifest(self, sip_with_pdf):
        """transform() rewrites the SIP manifest to disk (no errors)."""
        ALTOTransformer().transform(sip_with_pdf)
        data = json.loads((sip_with_pdf / "sip-manifest.json").read_text())
        assert data["id"] == "2026-01-29"
        assert len(data["validation_errors"]) == 0

    def test_transform_creates_alto_for_each_page(self, sip_with_multipage_pdf):
        """transform() creates one ALTO file per page."""
        ALTOTransformer().transform(sip_with_multipage_pdf)
        article_dir = sip_with_multipage_pdf / "articles" / "67890"
        assert (article_dir / "001.alto.xml").exists()
        assert (article_dir / "002.alto.xml").exists()

    def test_transform_creates_alto_for_multiple_articles(self, sip_multiple_articles):
        """transform() processes every article in the manifest."""
        ALTOTransformer().transform(sip_multiple_articles)
        assert (sip_multiple_articles / "articles" / "11111" / "001.alto.xml").exists()
        assert (sip_multiple_articles / "articles" / "22222" / "001.alto.xml").exists()


# ---------------------------------------------------------------------------
# Tests: ALTO XML structure
# ---------------------------------------------------------------------------


class TestALTOXMLStructure:
    def test_alto_root_element(self, sip_with_pdf):
        """ALTO file has <alto> root element in the correct namespace."""
        ALTOTransformer().transform(sip_with_pdf)
        root = _parse_alto(sip_with_pdf / "articles" / "12345" / "001.alto.xml")
        assert root.tag == _alto_tag("alto")

    def test_alto_has_description(self, sip_with_pdf):
        """ALTO file has a <Description> element with MeasurementUnit."""
        ALTOTransformer().transform(sip_with_pdf)
        root = _parse_alto(sip_with_pdf / "articles" / "12345" / "001.alto.xml")
        description = root.find(_alto_tag("Description"))
        assert description is not None
        measurement = description.find(_alto_tag("MeasurementUnit"))
        assert measurement is not None
        assert measurement.text == "pixel"

    def test_alto_has_layout_and_page(self, sip_with_pdf):
        """ALTO file has <Layout>/<Page> structure."""
        ALTOTransformer().transform(sip_with_pdf)
        root = _parse_alto(sip_with_pdf / "articles" / "12345" / "001.alto.xml")
        layout = root.find(_alto_tag("Layout"))
        assert layout is not None
        page = layout.find(_alto_tag("Page"))
        assert page is not None

    def test_alto_page_has_correct_number(self, sip_with_pdf):
        """ALTO page element has PHYSICAL_IMG_NR matching the page number."""
        ALTOTransformer().transform(sip_with_pdf)
        root = _parse_alto(sip_with_pdf / "articles" / "12345" / "001.alto.xml")
        page = root.find(f".//{_alto_tag('Page')}")
        assert page.get("PHYSICAL_IMG_NR") == "1"

    def test_alto_page_has_dimensions(self, sip_with_pdf):
        """ALTO page element carries WIDTH and HEIGHT attributes."""
        ALTOTransformer().transform(sip_with_pdf)
        root = _parse_alto(sip_with_pdf / "articles" / "12345" / "001.alto.xml")
        page = root.find(f".//{_alto_tag('Page')}")
        assert page.get("WIDTH") is not None
        assert page.get("HEIGHT") is not None
        assert int(page.get("WIDTH")) > 0
        assert int(page.get("HEIGHT")) > 0

    def test_alto_page_has_print_space(self, sip_with_pdf):
        """ALTO page element contains a <PrintSpace> element."""
        ALTOTransformer().transform(sip_with_pdf)
        root = _parse_alto(sip_with_pdf / "articles" / "12345" / "001.alto.xml")
        print_space = root.find(f".//{_alto_tag('PrintSpace')}")
        assert print_space is not None

    def test_alto_contains_text_blocks(self, sip_with_pdf):
        """ALTO file has TextBlock elements for pages with text."""
        ALTOTransformer().transform(sip_with_pdf)
        root = _parse_alto(sip_with_pdf / "articles" / "12345" / "001.alto.xml")
        blocks = root.findall(f".//{_alto_tag('TextBlock')}")
        assert len(blocks) >= 1

    def test_alto_text_blocks_have_bboxes(self, sip_with_pdf):
        """TextBlock elements carry HPOS, VPOS, WIDTH, HEIGHT attributes."""
        ALTOTransformer().transform(sip_with_pdf)
        root = _parse_alto(sip_with_pdf / "articles" / "12345" / "001.alto.xml")
        for block in root.findall(f".//{_alto_tag('TextBlock')}"):
            for attr in ("HPOS", "VPOS", "WIDTH", "HEIGHT"):
                assert block.get(attr) is not None, f"TextBlock missing {attr}"

    def test_alto_contains_text_lines(self, sip_with_pdf):
        """ALTO file has TextLine elements within text blocks."""
        ALTOTransformer().transform(sip_with_pdf)
        root = _parse_alto(sip_with_pdf / "articles" / "12345" / "001.alto.xml")
        lines = root.findall(f".//{_alto_tag('TextLine')}")
        assert len(lines) >= 1

    def test_alto_contains_strings_with_content(self, sip_with_pdf):
        """ALTO file has String elements with CONTENT attributes."""
        ALTOTransformer().transform(sip_with_pdf)
        root = _parse_alto(sip_with_pdf / "articles" / "12345" / "001.alto.xml")
        strings = root.findall(f".//{_alto_tag('String')}")
        assert len(strings) >= 1
        for s in strings:
            assert s.get("CONTENT") is not None

    def test_alto_string_content_matches_pdf_text(self, sip_with_pdf):
        """String CONTENT values collectively contain the text inserted into the PDF."""
        ALTOTransformer().transform(sip_with_pdf)
        root = _parse_alto(sip_with_pdf / "articles" / "12345" / "001.alto.xml")
        strings = root.findall(f".//{_alto_tag('String')}")
        all_text = " ".join(s.get("CONTENT", "") for s in strings)
        assert "Hello" in all_text
        assert "World" in all_text

    def test_alto_multipage_page_numbers(self, sip_with_multipage_pdf):
        """Each ALTO file reflects its correct page number."""
        ALTOTransformer().transform(sip_with_multipage_pdf)
        article_dir = sip_with_multipage_pdf / "articles" / "67890"

        root1 = _parse_alto(article_dir / "001.alto.xml")
        page1 = root1.find(f".//{_alto_tag('Page')}")
        assert page1.get("PHYSICAL_IMG_NR") == "1"

        root2 = _parse_alto(article_dir / "002.alto.xml")
        page2 = root2.find(f".//{_alto_tag('Page')}")
        assert page2.get("PHYSICAL_IMG_NR") == "2"

    def test_alto_string_ids_are_unique(self, sip_with_pdf):
        """All String ID attributes within an ALTO file are unique."""
        ALTOTransformer().transform(sip_with_pdf)
        root = _parse_alto(sip_with_pdf / "articles" / "12345" / "001.alto.xml")
        ids = [el.get("ID") for el in root.iter() if el.get("ID") is not None]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# Tests: Error handling
# ---------------------------------------------------------------------------


class TestALTOTransformerErrorHandling:
    def test_skips_article_without_pdf_path(self, tmp_path):
        """transform() skips articles that have no pdf_path."""
        sip_dir = tmp_path / "sip"
        sip_dir.mkdir()

        manifest = SIPManifest(
            id="no-pdf",
            pip_id="no-pdf",
            articles=[SIPArticle(ceo_id="99999", pdf_path=None)],
            status="sealed",
        )
        (sip_dir / "sip-manifest.json").write_text(manifest.model_dump_json(indent=2))

        result = ALTOTransformer().transform(sip_dir)
        assert len(result.validation_errors) == 0

    def test_skips_article_without_pages(self, tmp_path):
        """transform() skips articles that have no pages list."""
        sip_dir = tmp_path / "sip"
        article_dir = sip_dir / "articles" / "99999"
        article_dir.mkdir(parents=True)
        _make_pdf(article_dir / "article.pdf", [["some text"]])

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
            status="sealed",
        )
        (sip_dir / "sip-manifest.json").write_text(manifest.model_dump_json(indent=2))

        result = ALTOTransformer().transform(sip_dir)
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
            status="sealed",
        )
        (sip_dir / "sip-manifest.json").write_text(manifest.model_dump_json(indent=2))

        result = ALTOTransformer().transform(sip_dir)
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
        _make_pdf(good_dir / "article.pdf", [["Valid content"]])

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
            status="sealed",
        )
        (sip_dir / "sip-manifest.json").write_text(manifest.model_dump_json(indent=2))

        result = ALTOTransformer().transform(sip_dir)

        assert len(result.validation_errors) == 1
        assert "bad" in result.validation_errors[0]
        assert (sip_dir / "articles" / "good" / "001.alto.xml").exists()


# ---------------------------------------------------------------------------
# Tests: Internal helpers
# ---------------------------------------------------------------------------


class TestALTOTransformerHelpers:
    def test_union_bbox(self):
        """_union_bbox() returns the correct outer bounds."""
        transformer = ALTOTransformer()
        words = [(10, 20, 50, 30, "a"), (60, 15, 90, 35, "b")]
        assert transformer._union_bbox(words) == (10, 15, 90, 35)

    def test_group_words_preserves_block_order(self):
        """_group_words() returns blocks in the order they appear in the source list."""
        transformer = ALTOTransformer()
        words = [
            (0, 0, 10, 10, "first", 0, 0, 0),
            (20, 0, 30, 10, "second", 1, 0, 0),
        ]
        result = transformer._group_words(words)
        assert len(result) == 2

    def test_group_words_groups_by_block(self):
        """_group_words() groups words that share a block_no together."""
        transformer = ALTOTransformer()
        words = [
            (0, 0, 10, 10, "a", 0, 0, 0),
            (15, 0, 25, 10, "b", 0, 0, 1),
            (50, 50, 80, 60, "c", 1, 0, 0),
        ]
        result = transformer._group_words(words)
        assert len(result) == 2
        _bbox0, lines0 = result[0]
        all_words_0 = [w for _ln, ws in lines0 for w in ws]
        assert len(all_words_0) == 2

    def test_group_words_sorts_lines(self):
        """_group_words() returns lines sorted by line number."""
        transformer = ALTOTransformer()
        words = [
            (0, 20, 10, 30, "line2", 0, 1, 0),
            (0, 0, 10, 10, "line1", 0, 0, 0),
        ]
        result = transformer._group_words(words)
        _bbox, lines = result[0]
        line_numbers = [ln for ln, _ws in lines]
        assert line_numbers == sorted(line_numbers)

    def test_build_alto_empty_page(self):
        """_build_alto() produces valid XML for a page with no text."""
        transformer = ALTOTransformer()
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        alto = transformer._build_alto(page, 1)
        doc.close()

        assert alto.tag == f"{{{ALTO_NS}}}alto"
        print_space = alto.find(f".//{{{ALTO_NS}}}PrintSpace")
        assert print_space is not None
        blocks = alto.findall(f".//{{{ALTO_NS}}}TextBlock")
        assert len(blocks) == 0


# ---------------------------------------------------------------------------
# Tests: _merge_nearby_blocks()
# ---------------------------------------------------------------------------


def _make_block(x0, y0, x1, y1, words=None):
    """Minimal (block_bbox, lines) pair for testing _merge_nearby_blocks."""
    if words is None:
        words = [(x0, y0, x1, y1, "word")]
    return ((x0, y0, x1, y1), [(0, words)])


class TestALTOMergeBlocks:
    def test_empty_input(self):
        """Empty block list returns empty list."""
        assert ALTOTransformer()._merge_nearby_blocks([]) == []

    def test_single_block_unchanged(self):
        """A single block is returned as-is."""
        block = _make_block(0, 0, 100, 12)
        result = ALTOTransformer()._merge_nearby_blocks([block])
        assert len(result) == 1

    def test_merge_close_blocks(self):
        """Two blocks with small vertical gap and horizontal overlap are merged."""
        # gap = 5, height = 12, ratio = 0.42 < 0.6 → should merge
        b0 = _make_block(50, 0, 400, 12)
        b1 = _make_block(50, 17, 400, 29)
        result = ALTOTransformer()._merge_nearby_blocks([b0, b1])
        assert len(result) == 1
        bbox, lines = result[0]
        assert bbox == (50, 0, 400, 29)
        assert len(lines) == 2

    def test_keep_distant_blocks_separate(self):
        """Blocks with a large vertical gap are kept as separate TextBlocks."""
        # gap = 100, height = 12, ratio = 8.3 > 0.6 → should not merge
        b0 = _make_block(50, 0, 400, 12)
        b1 = _make_block(50, 112, 400, 124)
        result = ALTOTransformer()._merge_nearby_blocks([b0, b1])
        assert len(result) == 2

    def test_keep_nonoverlapping_blocks_separate(self):
        """Horizontally non-overlapping blocks (two-column) are not merged."""
        # Columns side by side, small vertical gap
        b0 = _make_block(0, 0, 200, 12)
        b1 = _make_block(250, 17, 450, 29)  # no horizontal overlap with b0
        result = ALTOTransformer()._merge_nearby_blocks([b0, b1])
        assert len(result) == 2

    def test_merge_preserves_line_order(self):
        """After merging, lines appear in top-to-bottom order."""
        b0 = _make_block(50, 0, 400, 12, [(50, 0, 200, 12, "first")])
        b1 = _make_block(50, 17, 400, 29, [(50, 17, 200, 29, "second")])
        _, lines = ALTOTransformer()._merge_nearby_blocks([b0, b1])[0]
        word_texts = [w[4] for _ln, ws in lines for w in ws]
        assert word_texts == ["first", "second"]

    def test_chain_merge_three_blocks(self):
        """Three vertically adjacent blocks collapse into one."""
        b0 = _make_block(50, 0, 400, 12)
        b1 = _make_block(50, 17, 400, 29)
        b2 = _make_block(50, 34, 400, 46)
        result = ALTOTransformer()._merge_nearby_blocks([b0, b1, b2])
        assert len(result) == 1
        _, lines = result[0]
        assert len(lines) == 3

    def test_partial_merge(self):
        """A+B merge, C is far away → two blocks total."""
        b0 = _make_block(50, 0, 400, 12)
        b1 = _make_block(50, 17, 400, 29)
        b2 = _make_block(50, 200, 400, 212)  # far below
        result = ALTOTransformer()._merge_nearby_blocks([b0, b1, b2])
        assert len(result) == 2
        _, lines0 = result[0]
        assert len(lines0) == 2
        _, lines1 = result[1]
        assert len(lines1) == 1

    def test_gap_factor_boundary(self):
        """Blocks at exactly gap_factor × height are not merged (strict <)."""
        # gap = 6, height = 10, ratio = 0.6 exactly → not merged (≤ boundary: merged)
        b0 = _make_block(50, 0, 400, 10)
        b1 = _make_block(50, 16, 400, 26)  # gap = 16 - 10 = 6, ratio = 0.6
        result = ALTOTransformer()._merge_nearby_blocks([b0, b1])
        # ratio == gap_factor → condition is 0 <= 6 <= 0.6*10=6 → True → merged
        assert len(result) == 1

    def test_overlapping_blocks_not_merged(self):
        """Blocks that overlap vertically (gap < 0) are not merged."""
        b0 = _make_block(50, 0, 400, 20)
        b1 = _make_block(50, 15, 400, 35)  # gap = 15 - 20 = -5
        result = ALTOTransformer()._merge_nearby_blocks([b0, b1])
        assert len(result) == 2
