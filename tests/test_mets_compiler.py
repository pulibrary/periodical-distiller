"""Tests for the METS Compiler and Veridian SIP Compiler."""

import json
from pathlib import Path

import fitz  # PyMuPDF
import pytest
from lxml import etree

from periodical_distiller.compilers.mets_compiler import (
    METS_NS,
    MODS_NS,
    METSCompiler,
)
from periodical_distiller.compilers.veridian_sip_compiler import VeridianSIPCompiler
from schemas.pip import PIPArticle, PIPManifest
from schemas.sip import SIPArticle, SIPManifest, SIPPage

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mets_tag(local: str) -> str:
    return f"{{{METS_NS}}}{local}"


def _mods_tag(local: str) -> str:
    return f"{{{MODS_NS}}}{local}"


def _parse_mets(path: Path) -> etree._Element:
    return etree.parse(str(path)).getroot()


def _make_pdf(path: Path, pages: int = 1) -> None:
    """Write a minimal PDF to *path*."""
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page(width=595, height=842)
        page.insert_text((50, 100), f"Page {i + 1}")
    doc.save(str(path))
    doc.close()


def _make_mods_xml(title: str, authors: list[str]) -> bytes:
    """Build a minimal MODS XML document."""
    ns = MODS_NS
    root = etree.Element(f"{{{ns}}}mods")
    root.set("version", "3.8")
    title_info = etree.SubElement(root, f"{{{ns}}}titleInfo")
    title_el = etree.SubElement(title_info, f"{{{ns}}}title")
    title_el.text = title
    for author in authors:
        name_el = etree.SubElement(root, f"{{{ns}}}name")
        name_el.set("type", "personal")
        name_part = etree.SubElement(name_el, f"{{{ns}}}namePart")
        name_part.text = author
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", pretty_print=True)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def full_sip(tmp_path) -> Path:
    """Fully populated SIP + PIP fixture.

    Structure::

        tmp_path/
          pips/2026-01-29/
            pip-manifest.json
            articles/12345/
              ceo_record.json
          sips/2026-01-29/
            sip-manifest.json   (pip_path set, all article paths set)
            articles/12345/
              article.pdf
              article.mods.xml
              001.alto.xml
    """
    pip_dir = tmp_path / "pips" / "2026-01-29"
    pip_article_dir = pip_dir / "articles" / "12345"
    pip_article_dir.mkdir(parents=True)

    pip_manifest = PIPManifest(
        id="2026-01-29",
        title="The Daily Princetonian",
        date_range=("2026-01-29", "2026-01-29"),
        articles=[
            PIPArticle(
                ceo_id="12345",
                ceo_record_path="articles/12345/ceo_record.json",
            )
        ],
    )
    (pip_dir / "pip-manifest.json").write_text(
        pip_manifest.model_dump_json(indent=2)
    )

    sip_dir = tmp_path / "sips" / "2026-01-29"
    article_dir = sip_dir / "articles" / "12345"
    article_dir.mkdir(parents=True)

    _make_pdf(article_dir / "article.pdf", pages=1)
    (article_dir / "article.mods.xml").write_bytes(
        _make_mods_xml("Test Headline", ["Jane Doe"])
    )
    (article_dir / "001.alto.xml").write_text(
        '<?xml version="1.0"?><alto xmlns="http://www.loc.gov/standards/alto/ns-v2#"/>'
    )

    sip_manifest = SIPManifest(
        id="2026-01-29",
        pip_id="2026-01-29",
        pip_path=str(pip_dir),
        articles=[
            SIPArticle(
                ceo_id="12345",
                html_path="articles/12345/article.html",
                pdf_path="articles/12345/article.pdf",
                mods_path="articles/12345/article.mods.xml",
                pages=[
                    SIPPage(
                        page_number=1,
                        alto_path="articles/12345/001.alto.xml",
                    )
                ],
            )
        ],
    )
    (sip_dir / "sip-manifest.json").write_text(
        sip_manifest.model_dump_json(indent=2)
    )
    return sip_dir


@pytest.fixture
def full_sip_with_images(full_sip) -> Path:
    """Extends full_sip with a JPEG image on the page."""
    article_dir = full_sip / "articles" / "12345"
    # Write a minimal JPEG (just the magic bytes + some padding)
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    mat = fitz.Matrix(150 / 72, 150 / 72)
    pix = page.get_pixmap(matrix=mat)
    pix.save(str(article_dir / "001.jpg"))
    doc.close()

    # Update the manifest to include image_path
    manifest_path = full_sip / "sip-manifest.json"
    data = json.loads(manifest_path.read_text())
    data["articles"][0]["pages"][0]["image_path"] = "articles/12345/001.jpg"
    manifest_path.write_text(json.dumps(data, indent=2))
    return full_sip


@pytest.fixture
def full_sip_two_articles(tmp_path) -> Path:
    """SIP with two articles for multi-article tests."""
    pip_dir = tmp_path / "pips" / "2026-01-29"
    for ceo_id in ("11111", "22222"):
        (pip_dir / "articles" / ceo_id).mkdir(parents=True)

    pip_manifest = PIPManifest(
        id="2026-01-29",
        title="The Daily Princetonian",
        date_range=("2026-01-29", "2026-01-29"),
        articles=[
            PIPArticle(ceo_id="11111", ceo_record_path="articles/11111/ceo_record.json"),
            PIPArticle(ceo_id="22222", ceo_record_path="articles/22222/ceo_record.json"),
        ],
    )
    (pip_dir / "pip-manifest.json").write_text(pip_manifest.model_dump_json(indent=2))

    sip_dir = tmp_path / "sips" / "2026-01-29"

    articles = []
    for i, ceo_id in enumerate(("11111", "22222"), start=1):
        article_dir = sip_dir / "articles" / ceo_id
        article_dir.mkdir(parents=True)
        _make_pdf(article_dir / "article.pdf", pages=1)
        (article_dir / "article.mods.xml").write_bytes(
            _make_mods_xml(f"Article {i}", [f"Author {i}"])
        )
        (article_dir / "001.alto.xml").write_text(
            '<?xml version="1.0"?><alto xmlns="http://www.loc.gov/standards/alto/ns-v2#"/>'
        )
        articles.append(
            SIPArticle(
                ceo_id=ceo_id,
                pdf_path=f"articles/{ceo_id}/article.pdf",
                mods_path=f"articles/{ceo_id}/article.mods.xml",
                pages=[SIPPage(page_number=1, alto_path=f"articles/{ceo_id}/001.alto.xml")],
            )
        )

    sip_manifest = SIPManifest(
        id="2026-01-29",
        pip_id="2026-01-29",
        pip_path=str(pip_dir),
        articles=articles,
    )
    (sip_dir / "sip-manifest.json").write_text(sip_manifest.model_dump_json(indent=2))
    return sip_dir


# ---------------------------------------------------------------------------
# Tests: Initialization
# ---------------------------------------------------------------------------

class TestMETSCompilerInit:
    def test_instantiation(self):
        """METSCompiler can be instantiated with no arguments."""
        assert METSCompiler() is not None


# ---------------------------------------------------------------------------
# Tests: compile() — file creation and manifest update
# ---------------------------------------------------------------------------

class TestMETSCompilerCompile:
    def test_compile_creates_mets_file(self, full_sip):
        """compile() writes mets.xml to the SIP root."""
        METSCompiler().compile(full_sip)
        assert (full_sip / "mets.xml").exists()

    def test_compile_returns_sip_manifest(self, full_sip):
        """compile() returns a SIPManifest."""
        result = METSCompiler().compile(full_sip)
        assert isinstance(result, SIPManifest)
        assert result.id == "2026-01-29"

    def test_compile_sets_mets_path(self, full_sip):
        """compile() sets mets_path on the returned manifest."""
        result = METSCompiler().compile(full_sip)
        assert result.mets_path == "mets.xml"

    def test_compile_writes_mets_path_to_disk(self, full_sip):
        """compile() persists mets_path in the on-disk manifest."""
        METSCompiler().compile(full_sip)
        data = json.loads((full_sip / "sip-manifest.json").read_text())
        assert data["mets_path"] == "mets.xml"


# ---------------------------------------------------------------------------
# Tests: METS XML root structure
# ---------------------------------------------------------------------------

class TestMETSXMLStructure:
    def test_root_element_is_mets(self, full_sip):
        """Root element is <mets> in the METS namespace."""
        METSCompiler().compile(full_sip)
        root = _parse_mets(full_sip / "mets.xml")
        assert root.tag == _mets_tag("mets")

    def test_root_type_is_newspaper(self, full_sip):
        """Root element has TYPE='Newspaper'."""
        METSCompiler().compile(full_sip)
        root = _parse_mets(full_sip / "mets.xml")
        assert root.get("TYPE") == "Newspaper"

    def test_root_objid_contains_issue_id(self, full_sip):
        """Root OBJID contains the issue identifier."""
        METSCompiler().compile(full_sip)
        root = _parse_mets(full_sip / "mets.xml")
        assert "2026-01-29" in root.get("OBJID", "")

    def test_has_mets_hdr(self, full_sip):
        """METS document has a metsHdr element."""
        METSCompiler().compile(full_sip)
        root = _parse_mets(full_sip / "mets.xml")
        assert root.find(_mets_tag("metsHdr")) is not None

    def test_mets_hdr_has_agent(self, full_sip):
        """metsHdr contains an agent element."""
        METSCompiler().compile(full_sip)
        root = _parse_mets(full_sip / "mets.xml")
        hdr = root.find(_mets_tag("metsHdr"))
        agent = hdr.find(_mets_tag("agent"))
        assert agent is not None
        assert agent.get("ROLE") == "CREATOR"

    def test_mets_hdr_agent_name(self, full_sip):
        """metsHdr agent name contains Princeton University Library."""
        METSCompiler().compile(full_sip)
        root = _parse_mets(full_sip / "mets.xml")
        name = root.find(f".//{_mets_tag('name')}")
        assert name is not None
        assert "Princeton University Library" in name.text

    def test_has_dmd_sec(self, full_sip):
        """METS document has a dmdSec with ID='dmd1'."""
        METSCompiler().compile(full_sip)
        root = _parse_mets(full_sip / "mets.xml")
        dmd = root.find(_mets_tag("dmdSec"))
        assert dmd is not None
        assert dmd.get("ID") == "dmd1"

    def test_dmd_sec_has_mods_type(self, full_sip):
        """dmdSec mdWrap has MDTYPE='MODS'."""
        METSCompiler().compile(full_sip)
        root = _parse_mets(full_sip / "mets.xml")
        md_wrap = root.find(f".//{_mets_tag('mdWrap')}")
        assert md_wrap is not None
        assert md_wrap.get("MDTYPE") == "MODS"

    def test_dmd_sec_has_issue_title(self, full_sip):
        """dmdSec inline MODS contains the publication title."""
        METSCompiler().compile(full_sip)
        root = _parse_mets(full_sip / "mets.xml")
        title_el = root.find(f".//{_mods_tag('titleInfo')}/{_mods_tag('title')}")
        assert title_el is not None
        assert title_el.text == "The Daily Princetonian"

    def test_dmd_sec_has_date_issued(self, full_sip):
        """dmdSec inline MODS has a dateIssued element."""
        METSCompiler().compile(full_sip)
        root = _parse_mets(full_sip / "mets.xml")
        date_el = root.find(f".//{_mods_tag('dateIssued')}")
        assert date_el is not None
        assert date_el.text == "2026-01-29"

    def test_dmd_sec_has_related_item_per_article(self, full_sip):
        """dmdSec has one relatedItem constituent per article."""
        METSCompiler().compile(full_sip)
        root = _parse_mets(full_sip / "mets.xml")
        related = root.findall(f".//{_mods_tag('relatedItem')}")
        constituent_items = [r for r in related if r.get("type") == "constituent"]
        assert len(constituent_items) == 1

    def test_has_file_sec(self, full_sip):
        """METS document has a fileSec element."""
        METSCompiler().compile(full_sip)
        root = _parse_mets(full_sip / "mets.xml")
        assert root.find(_mets_tag("fileSec")) is not None

    def test_has_two_struct_maps(self, full_sip):
        """METS document has both physical and logical structMaps."""
        METSCompiler().compile(full_sip)
        root = _parse_mets(full_sip / "mets.xml")
        struct_maps = root.findall(_mets_tag("structMap"))
        types = {sm.get("TYPE") for sm in struct_maps}
        assert "PHYSICAL" in types
        assert "LOGICAL" in types


# ---------------------------------------------------------------------------
# Tests: fileSec contents
# ---------------------------------------------------------------------------

class TestMETSFileSec:
    def test_file_sec_has_altogrp(self, full_sip):
        """fileSec contains an ALTOGRP fileGrp."""
        METSCompiler().compile(full_sip)
        root = _parse_mets(full_sip / "mets.xml")
        file_sec = root.find(_mets_tag("fileSec"))
        grp_ids = [grp.get("ID") for grp in file_sec.findall(_mets_tag("fileGrp"))]
        assert "ALTOGRP" in grp_ids

    def test_file_sec_has_pdfgrp(self, full_sip):
        """fileSec contains a PDFGRP fileGrp."""
        METSCompiler().compile(full_sip)
        root = _parse_mets(full_sip / "mets.xml")
        file_sec = root.find(_mets_tag("fileSec"))
        grp_ids = [grp.get("ID") for grp in file_sec.findall(_mets_tag("fileGrp"))]
        assert "PDFGRP" in grp_ids

    def test_file_sec_has_modsgrp(self, full_sip):
        """fileSec contains a MODSGRP fileGrp."""
        METSCompiler().compile(full_sip)
        root = _parse_mets(full_sip / "mets.xml")
        file_sec = root.find(_mets_tag("fileSec"))
        grp_ids = [grp.get("ID") for grp in file_sec.findall(_mets_tag("fileGrp"))]
        assert "MODSGRP" in grp_ids

    def test_file_sec_no_imggrp_without_images(self, full_sip):
        """fileSec omits IMGGRP when no pages have image_path."""
        METSCompiler().compile(full_sip)
        root = _parse_mets(full_sip / "mets.xml")
        file_sec = root.find(_mets_tag("fileSec"))
        grp_ids = [grp.get("ID") for grp in file_sec.findall(_mets_tag("fileGrp"))]
        assert "IMGGRP" not in grp_ids

    def test_file_sec_has_imggrp_with_images(self, full_sip_with_images):
        """fileSec includes IMGGRP when pages have image_path."""
        METSCompiler().compile(full_sip_with_images)
        root = _parse_mets(full_sip_with_images / "mets.xml")
        file_sec = root.find(_mets_tag("fileSec"))
        grp_ids = [grp.get("ID") for grp in file_sec.findall(_mets_tag("fileGrp"))]
        assert "IMGGRP" in grp_ids

    def test_alto_file_has_correct_href(self, full_sip):
        """ALTOGRP file FLocat href matches the alto_path."""
        METSCompiler().compile(full_sip)
        root = _parse_mets(full_sip / "mets.xml")
        xlink_href = "{http://www.w3.org/1999/xlink}href"
        alto_files = root.findall(
            f".//{_mets_tag('fileGrp')}[@ID='ALTOGRP']/{_mets_tag('file')}/{_mets_tag('FLocat')}"
        )
        assert len(alto_files) == 1
        assert "001.alto.xml" in alto_files[0].get(xlink_href, "")

    def test_pdf_file_has_correct_href(self, full_sip):
        """PDFGRP file FLocat href matches the pdf_path."""
        METSCompiler().compile(full_sip)
        root = _parse_mets(full_sip / "mets.xml")
        xlink_href = "{http://www.w3.org/1999/xlink}href"
        pdf_files = root.findall(
            f".//{_mets_tag('fileGrp')}[@ID='PDFGRP']/{_mets_tag('file')}/{_mets_tag('FLocat')}"
        )
        assert len(pdf_files) == 1
        assert "article.pdf" in pdf_files[0].get(xlink_href, "")

    def test_mods_file_has_correct_href(self, full_sip):
        """MODSGRP file FLocat href matches the mods_path."""
        METSCompiler().compile(full_sip)
        root = _parse_mets(full_sip / "mets.xml")
        xlink_href = "{http://www.w3.org/1999/xlink}href"
        mods_files = root.findall(
            f".//{_mets_tag('fileGrp')}[@ID='MODSGRP']/{_mets_tag('file')}/{_mets_tag('FLocat')}"
        )
        assert len(mods_files) == 1
        assert "article.mods.xml" in mods_files[0].get(xlink_href, "")


# ---------------------------------------------------------------------------
# Tests: structMap contents
# ---------------------------------------------------------------------------

class TestMETSStructMaps:
    def test_physical_struct_map_has_page_div(self, full_sip):
        """Physical structMap has a DIVP1 div for the first page."""
        METSCompiler().compile(full_sip)
        root = _parse_mets(full_sip / "mets.xml")
        phys = next(
            sm for sm in root.findall(_mets_tag("structMap"))
            if sm.get("TYPE") == "PHYSICAL"
        )
        divp = phys.find(f".//{_mets_tag('div')}[@ID='DIVP1']")
        assert divp is not None
        assert divp.get("ORDER") == "1"

    def test_physical_struct_map_alto_area(self, full_sip):
        """Physical structMap page div references the ALTO file."""
        METSCompiler().compile(full_sip)
        root = _parse_mets(full_sip / "mets.xml")
        areas = root.findall(f".//{_mets_tag('area')}")
        alto_file_ids = [a.get("FILEID", "") for a in areas if "ALTO_" in a.get("FILEID", "")]
        assert len(alto_file_ids) >= 1

    def test_logical_struct_map_has_article_div(self, full_sip):
        """Logical structMap has an Article div with DMDID='c0001'."""
        METSCompiler().compile(full_sip)
        root = _parse_mets(full_sip / "mets.xml")
        logical = next(
            sm for sm in root.findall(_mets_tag("structMap"))
            if sm.get("TYPE") == "LOGICAL"
        )
        article_div = logical.find(f".//{_mets_tag('div')}[@TYPE='Article']")
        assert article_div is not None
        assert article_div.get("DMDID") == "c0001"

    def test_logical_struct_map_article_fptr(self, full_sip):
        """Logical structMap article div has fptr pointing to the PDF."""
        METSCompiler().compile(full_sip)
        root = _parse_mets(full_sip / "mets.xml")
        logical = next(
            sm for sm in root.findall(_mets_tag("structMap"))
            if sm.get("TYPE") == "LOGICAL"
        )
        fptr = logical.find(f".//{_mets_tag('fptr')}")
        assert fptr is not None
        assert "PDF_12345" in fptr.get("FILEID", "")

    def test_logical_struct_map_newspaper_label(self, full_sip):
        """Logical structMap Newspaper div has the publication title as LABEL."""
        METSCompiler().compile(full_sip)
        root = _parse_mets(full_sip / "mets.xml")
        logical = next(
            sm for sm in root.findall(_mets_tag("structMap"))
            if sm.get("TYPE") == "LOGICAL"
        )
        newspaper_div = logical.find(f"{_mets_tag('div')}[@TYPE='Newspaper']")
        assert newspaper_div is not None
        assert newspaper_div.get("LABEL") == "The Daily Princetonian"


# ---------------------------------------------------------------------------
# Tests: Multiple articles
# ---------------------------------------------------------------------------

class TestMETSCompilerMultipleArticles:
    def test_two_articles_two_related_items(self, full_sip_two_articles):
        """Two articles produce two relatedItem constituents in dmdSec."""
        METSCompiler().compile(full_sip_two_articles)
        root = _parse_mets(full_sip_two_articles / "mets.xml")
        related = [
            r for r in root.findall(f".//{_mods_tag('relatedItem')}")
            if r.get("type") == "constituent"
        ]
        assert len(related) == 2
        assert related[0].get("ID") == "c0001"
        assert related[1].get("ID") == "c0002"

    def test_two_articles_two_pdf_files(self, full_sip_two_articles):
        """Two articles produce two entries in PDFGRP."""
        METSCompiler().compile(full_sip_two_articles)
        root = _parse_mets(full_sip_two_articles / "mets.xml")
        pdf_files = root.findall(
            f".//{_mets_tag('fileGrp')}[@ID='PDFGRP']/{_mets_tag('file')}"
        )
        assert len(pdf_files) == 2

    def test_two_articles_global_page_ordering(self, full_sip_two_articles):
        """Two articles get sequentially numbered pages DIVP1 and DIVP2."""
        METSCompiler().compile(full_sip_two_articles)
        root = _parse_mets(full_sip_two_articles / "mets.xml")
        phys = next(
            sm for sm in root.findall(_mets_tag("structMap"))
            if sm.get("TYPE") == "PHYSICAL"
        )
        assert phys.find(f".//{_mets_tag('div')}[@ID='DIVP1']") is not None
        assert phys.find(f".//{_mets_tag('div')}[@ID='DIVP2']") is not None

    def test_two_articles_logical_order(self, full_sip_two_articles):
        """Logical structMap lists articles in ORDER 1, 2."""
        METSCompiler().compile(full_sip_two_articles)
        root = _parse_mets(full_sip_two_articles / "mets.xml")
        logical = next(
            sm for sm in root.findall(_mets_tag("structMap"))
            if sm.get("TYPE") == "LOGICAL"
        )
        article_divs = logical.findall(f".//{_mets_tag('div')}[@TYPE='Article']")
        orders = [div.get("ORDER") for div in article_divs]
        assert orders == ["1", "2"]


# ---------------------------------------------------------------------------
# Tests: Error handling
# ---------------------------------------------------------------------------

class TestMETSCompilerErrorHandling:
    def test_missing_mods_path_falls_back_to_ceo_id(self, tmp_path):
        """Articles without mods_path use fallback title in relatedItem."""
        pip_dir = tmp_path / "pips" / "2026-01-29"
        pip_dir.mkdir(parents=True)
        pip_manifest = PIPManifest(
            id="2026-01-29",
            title="The Daily Princetonian",
            date_range=("2026-01-29", "2026-01-29"),
        )
        (pip_dir / "pip-manifest.json").write_text(pip_manifest.model_dump_json(indent=2))

        sip_dir = tmp_path / "sips" / "2026-01-29"
        article_dir = sip_dir / "articles" / "99999"
        article_dir.mkdir(parents=True)
        _make_pdf(article_dir / "article.pdf")
        (article_dir / "001.alto.xml").write_text(
            '<?xml version="1.0"?><alto xmlns="http://www.loc.gov/standards/alto/ns-v2#"/>'
        )

        sip_manifest = SIPManifest(
            id="2026-01-29",
            pip_id="2026-01-29",
            pip_path=str(pip_dir),
            articles=[
                SIPArticle(
                    ceo_id="99999",
                    pdf_path="articles/99999/article.pdf",
                    mods_path=None,  # no MODS file
                    pages=[SIPPage(page_number=1, alto_path="articles/99999/001.alto.xml")],
                )
            ],
        )
        (sip_dir / "sip-manifest.json").write_text(sip_manifest.model_dump_json(indent=2))

        METSCompiler().compile(sip_dir)
        root = _parse_mets(sip_dir / "mets.xml")
        title_els = root.findall(f".//{_mods_tag('relatedItem')}/{_mods_tag('titleInfo')}/{_mods_tag('title')}")
        assert len(title_els) == 1
        assert "99999" in title_els[0].text


# ---------------------------------------------------------------------------
# Tests: VeridianSIPCompiler
# ---------------------------------------------------------------------------

class TestVeridianSIPCompiler:
    def test_instantiation(self):
        """VeridianSIPCompiler can be instantiated with no arguments."""
        assert VeridianSIPCompiler() is not None

    def test_compile_calls_mets_compiler(self, full_sip):
        """compile() produces mets.xml via METSCompiler."""
        VeridianSIPCompiler().compile(full_sip)
        assert (full_sip / "mets.xml").exists()

    def test_compile_seals_manifest(self, full_sip):
        """compile() sets manifest status to 'sealed'."""
        result = VeridianSIPCompiler().compile(full_sip)
        assert result.status == "sealed"

    def test_compile_persists_sealed_status(self, full_sip):
        """compile() writes status='sealed' to the on-disk manifest."""
        VeridianSIPCompiler().compile(full_sip)
        data = json.loads((full_sip / "sip-manifest.json").read_text())
        assert data["status"] == "sealed"

    def test_compile_sets_mets_path(self, full_sip):
        """compile() returns manifest with mets_path set."""
        result = VeridianSIPCompiler().compile(full_sip)
        assert result.mets_path == "mets.xml"

    def test_compile_accepts_injected_mets_compiler(self, full_sip):
        """VeridianSIPCompiler accepts an injected METSCompiler."""
        custom_mets = METSCompiler()
        compiler = VeridianSIPCompiler(mets_compiler=custom_mets)
        result = compiler.compile(full_sip)
        assert result.status == "sealed"
