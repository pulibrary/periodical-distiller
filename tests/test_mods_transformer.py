"""Tests for the MODS Transformer."""

import json
from pathlib import Path

import pytest
from lxml import etree

from periodical_distiller.transformers.mods_transformer import MODS_NS, MODSTransformer
from schemas.pip import PIPArticle, PIPManifest, PreservationDescriptionInfo
from schemas.sip import SIPArticle, SIPManifest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mods_tag(local: str) -> str:
    return f"{{{MODS_NS}}}{local}"


def _parse_mods(path: Path) -> etree._Element:
    return etree.parse(str(path)).getroot()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def pip_and_sip(tmp_path, sample_ceo_record):
    """PIP and SIP linked by sip_manifest.pip_path, with one article."""
    pip_dir = tmp_path / "pips" / "2026-01-29"
    article_dir = pip_dir / "articles" / "12345"
    article_dir.mkdir(parents=True)
    (article_dir / "ceo_record.json").write_text(json.dumps(sample_ceo_record))

    pip_manifest = PIPManifest(
        id="2026-01-29",
        title="The Daily Princetonian - January 29, 2026",
        date_range=("2026-01-29", "2026-01-29"),
        articles=[
            PIPArticle(
                ceo_id="12345",
                ceo_record_path="articles/12345/ceo_record.json",
            )
        ],
        pdi=PreservationDescriptionInfo(),
        status="sealed",
    )
    (pip_dir / "pip-manifest.json").write_text(pip_manifest.model_dump_json(indent=2))

    sip_dir = tmp_path / "sips" / "2026-01-29"
    (sip_dir / "articles" / "12345").mkdir(parents=True)

    sip_manifest = SIPManifest(
        id="2026-01-29",
        pip_id="2026-01-29",
        pip_path=str(pip_dir),
        articles=[SIPArticle(ceo_id="12345")],
        status="building",
    )
    (sip_dir / "sip-manifest.json").write_text(sip_manifest.model_dump_json(indent=2))

    return pip_dir, sip_dir


@pytest.fixture
def pip_and_sip_two_articles(tmp_path, sample_ceo_record):
    """PIP and SIP with two articles."""
    pip_dir = tmp_path / "pips" / "2026-01-30"

    records = [
        ("11111", {**sample_ceo_record, "id": "11111", "ceo_id": "11111",
                   "headline": "First Article", "uuid": "uuid-11111"}),
        ("22222", {**sample_ceo_record, "id": "22222", "ceo_id": "22222",
                   "headline": "Second Article", "uuid": "uuid-22222"}),
    ]

    pip_articles = []
    for ceo_id, record in records:
        art_dir = pip_dir / "articles" / ceo_id
        art_dir.mkdir(parents=True)
        (art_dir / "ceo_record.json").write_text(json.dumps(record))
        pip_articles.append(PIPArticle(
            ceo_id=ceo_id,
            ceo_record_path=f"articles/{ceo_id}/ceo_record.json",
        ))

    pip_manifest = PIPManifest(
        id="2026-01-30",
        title="The Daily Princetonian - January 30, 2026",
        date_range=("2026-01-30", "2026-01-30"),
        articles=pip_articles,
        pdi=PreservationDescriptionInfo(),
        status="sealed",
    )
    (pip_dir / "pip-manifest.json").write_text(pip_manifest.model_dump_json(indent=2))

    sip_dir = tmp_path / "sips" / "2026-01-30"
    for ceo_id, _ in records:
        (sip_dir / "articles" / ceo_id).mkdir(parents=True)

    sip_manifest = SIPManifest(
        id="2026-01-30",
        pip_id="2026-01-30",
        pip_path=str(pip_dir),
        articles=[SIPArticle(ceo_id=ceo_id) for ceo_id, _ in records],
        status="building",
    )
    (sip_dir / "sip-manifest.json").write_text(sip_manifest.model_dump_json(indent=2))

    return pip_dir, sip_dir


# ---------------------------------------------------------------------------
# Tests: Initialization
# ---------------------------------------------------------------------------

class TestMODSTransformerInit:
    def test_instantiation(self):
        """MODSTransformer can be instantiated with no arguments."""
        transformer = MODSTransformer()
        assert transformer is not None


# ---------------------------------------------------------------------------
# Tests: transform() – file creation and manifest updates
# ---------------------------------------------------------------------------

class TestMODSTransformerTransform:
    def test_transform_creates_mods_file(self, pip_and_sip):
        """transform() writes article.mods.xml for each article."""
        _pip_dir, sip_dir = pip_and_sip
        MODSTransformer().transform(sip_dir)
        mods_path = sip_dir / "articles" / "12345" / "article.mods.xml"
        assert mods_path.exists()

    def test_transform_returns_sip_manifest(self, pip_and_sip):
        """transform() returns a SIPManifest."""
        _pip_dir, sip_dir = pip_and_sip
        result = MODSTransformer().transform(sip_dir)
        assert isinstance(result, SIPManifest)
        assert result.id == "2026-01-29"

    def test_transform_sets_mods_path_in_manifest(self, pip_and_sip):
        """transform() updates article.mods_path in the returned manifest."""
        _pip_dir, sip_dir = pip_and_sip
        result = MODSTransformer().transform(sip_dir)
        article = result.articles[0]
        assert article.mods_path == "articles/12345/article.mods.xml"

    def test_transform_writes_updated_manifest_to_disk(self, pip_and_sip):
        """transform() rewrites the SIP manifest with mods_path set."""
        _pip_dir, sip_dir = pip_and_sip
        MODSTransformer().transform(sip_dir)
        data = json.loads((sip_dir / "sip-manifest.json").read_text())
        assert data["articles"][0]["mods_path"] == "articles/12345/article.mods.xml"

    def test_transform_no_validation_errors_on_success(self, pip_and_sip):
        """transform() produces no validation errors when everything succeeds."""
        _pip_dir, sip_dir = pip_and_sip
        result = MODSTransformer().transform(sip_dir)
        assert result.validation_errors == []

    def test_transform_multiple_articles(self, pip_and_sip_two_articles):
        """transform() generates MODS for every article in the manifest."""
        _pip_dir, sip_dir = pip_and_sip_two_articles
        result = MODSTransformer().transform(sip_dir)
        assert (sip_dir / "articles" / "11111" / "article.mods.xml").exists()
        assert (sip_dir / "articles" / "22222" / "article.mods.xml").exists()
        mods_paths = [a.mods_path for a in result.articles]
        assert "articles/11111/article.mods.xml" in mods_paths
        assert "articles/22222/article.mods.xml" in mods_paths


# ---------------------------------------------------------------------------
# Tests: MODS XML structure
# ---------------------------------------------------------------------------

class TestMODSXMLStructure:
    def test_mods_root_element(self, pip_and_sip):
        """MODS file has <mods:mods> root element in the correct namespace."""
        _pip_dir, sip_dir = pip_and_sip
        MODSTransformer().transform(sip_dir)
        root = _parse_mods(sip_dir / "articles" / "12345" / "article.mods.xml")
        assert root.tag == _mods_tag("mods")

    def test_mods_version_attribute(self, pip_and_sip):
        """Root element carries version="3.8"."""
        _pip_dir, sip_dir = pip_and_sip
        MODSTransformer().transform(sip_dir)
        root = _parse_mods(sip_dir / "articles" / "12345" / "article.mods.xml")
        assert root.get("version") == "3.8"

    def test_mods_has_title_info(self, pip_and_sip):
        """MODS file has a <mods:titleInfo> element."""
        _pip_dir, sip_dir = pip_and_sip
        MODSTransformer().transform(sip_dir)
        root = _parse_mods(sip_dir / "articles" / "12345" / "article.mods.xml")
        title_info = root.find(_mods_tag("titleInfo"))
        assert title_info is not None

    def test_mods_has_title(self, pip_and_sip):
        """<mods:titleInfo> contains a <mods:title> child."""
        _pip_dir, sip_dir = pip_and_sip
        MODSTransformer().transform(sip_dir)
        root = _parse_mods(sip_dir / "articles" / "12345" / "article.mods.xml")
        title = root.find(f".//{_mods_tag('title')}")
        assert title is not None

    def test_mods_has_name_elements(self, pip_and_sip):
        """MODS file has <mods:name> elements for authors."""
        _pip_dir, sip_dir = pip_and_sip
        MODSTransformer().transform(sip_dir)
        root = _parse_mods(sip_dir / "articles" / "12345" / "article.mods.xml")
        names = root.findall(_mods_tag("name"))
        assert len(names) >= 1

    def test_mods_name_type_attribute(self, pip_and_sip):
        """<mods:name> elements carry type="personal"."""
        _pip_dir, sip_dir = pip_and_sip
        MODSTransformer().transform(sip_dir)
        root = _parse_mods(sip_dir / "articles" / "12345" / "article.mods.xml")
        for name_el in root.findall(_mods_tag("name")):
            assert name_el.get("type") == "personal"

    def test_mods_has_origin_info(self, pip_and_sip):
        """MODS file has <mods:originInfo> with <mods:dateIssued>."""
        _pip_dir, sip_dir = pip_and_sip
        MODSTransformer().transform(sip_dir)
        root = _parse_mods(sip_dir / "articles" / "12345" / "article.mods.xml")
        origin = root.find(_mods_tag("originInfo"))
        assert origin is not None
        date_issued = origin.find(_mods_tag("dateIssued"))
        assert date_issued is not None
        assert date_issued.get("encoding") == "iso8601"

    def test_mods_has_type_of_resource(self, pip_and_sip):
        """MODS file has <mods:typeOfResource> set to "text"."""
        _pip_dir, sip_dir = pip_and_sip
        MODSTransformer().transform(sip_dir)
        root = _parse_mods(sip_dir / "articles" / "12345" / "article.mods.xml")
        tor = root.find(_mods_tag("typeOfResource"))
        assert tor is not None
        assert tor.text == "text"

    def test_mods_has_identifiers(self, pip_and_sip):
        """MODS file has ceo-id and uuid identifier elements."""
        _pip_dir, sip_dir = pip_and_sip
        MODSTransformer().transform(sip_dir)
        root = _parse_mods(sip_dir / "articles" / "12345" / "article.mods.xml")
        identifiers = root.findall(_mods_tag("identifier"))
        types = {el.get("type") for el in identifiers}
        assert "ceo-id" in types
        assert "uuid" in types


# ---------------------------------------------------------------------------
# Tests: Metadata mapping (CEO → MODS values)
# ---------------------------------------------------------------------------

class TestMODSMetadataMapping:
    def test_headline_mapped_to_title(self, pip_and_sip, sample_ceo_record):
        """Headline is mapped to <mods:title> text."""
        _pip_dir, sip_dir = pip_and_sip
        MODSTransformer().transform(sip_dir)
        root = _parse_mods(sip_dir / "articles" / "12345" / "article.mods.xml")
        title = root.find(f".//{_mods_tag('title')}")
        assert title.text == sample_ceo_record["headline"]

    def test_subhead_mapped_to_subtitle(self, pip_and_sip, sample_ceo_record):
        """Subhead is mapped to <mods:subTitle> text."""
        _pip_dir, sip_dir = pip_and_sip
        MODSTransformer().transform(sip_dir)
        root = _parse_mods(sip_dir / "articles" / "12345" / "article.mods.xml")
        subtitle = root.find(f".//{_mods_tag('subTitle')}")
        assert subtitle is not None
        assert subtitle.text == sample_ceo_record["subhead"]

    def test_authors_mapped_to_name_elements(self, pip_and_sip, sample_ceo_record):
        """Each author produces a <mods:name> element with the correct namePart."""
        _pip_dir, sip_dir = pip_and_sip
        MODSTransformer().transform(sip_dir)
        root = _parse_mods(sip_dir / "articles" / "12345" / "article.mods.xml")
        name_parts = [
            el.text
            for el in root.findall(f".//{_mods_tag('namePart')}")
        ]
        expected_names = [a["name"] for a in sample_ceo_record["authors"]]
        for name in expected_names:
            assert name in name_parts

    def test_author_role_is_author(self, pip_and_sip):
        """Each <mods:name> has roleTerm "author"."""
        _pip_dir, sip_dir = pip_and_sip
        MODSTransformer().transform(sip_dir)
        root = _parse_mods(sip_dir / "articles" / "12345" / "article.mods.xml")
        role_terms = root.findall(f".//{_mods_tag('roleTerm')}")
        assert len(role_terms) >= 1
        for rt in role_terms:
            assert rt.text == "author"

    def test_published_at_date_part_mapped(self, pip_and_sip, sample_ceo_record):
        """Only the date part of published_at is used in dateIssued."""
        _pip_dir, sip_dir = pip_and_sip
        MODSTransformer().transform(sip_dir)
        root = _parse_mods(sip_dir / "articles" / "12345" / "article.mods.xml")
        date_issued = root.find(f".//{_mods_tag('dateIssued')}")
        expected_date = sample_ceo_record["published_at"].split(" ")[0]
        assert date_issued.text == expected_date

    def test_ceo_id_identifier_value(self, pip_and_sip, sample_ceo_record):
        """<mods:identifier type="ceo-id"> contains the ceo_id value."""
        _pip_dir, sip_dir = pip_and_sip
        MODSTransformer().transform(sip_dir)
        root = _parse_mods(sip_dir / "articles" / "12345" / "article.mods.xml")
        ceo_id_el = next(
            el for el in root.findall(_mods_tag("identifier"))
            if el.get("type") == "ceo-id"
        )
        assert ceo_id_el.text == sample_ceo_record["ceo_id"]

    def test_uuid_identifier_value(self, pip_and_sip, sample_ceo_record):
        """<mods:identifier type="uuid"> contains the uuid value."""
        _pip_dir, sip_dir = pip_and_sip
        MODSTransformer().transform(sip_dir)
        root = _parse_mods(sip_dir / "articles" / "12345" / "article.mods.xml")
        uuid_el = next(
            el for el in root.findall(_mods_tag("identifier"))
            if el.get("type") == "uuid"
        )
        assert uuid_el.text == sample_ceo_record["uuid"]

    def test_abstract_html_stripped(self, pip_and_sip):
        """<mods:abstract> contains plain text with HTML tags removed."""
        _pip_dir, sip_dir = pip_and_sip
        MODSTransformer().transform(sip_dir)
        root = _parse_mods(sip_dir / "articles" / "12345" / "article.mods.xml")
        abstract = root.find(_mods_tag("abstract"))
        assert abstract is not None
        assert "<p>" not in abstract.text
        assert "abstract" in abstract.text.lower()

    def test_tags_mapped_to_subjects(self, pip_and_sip, sample_ceo_record):
        """Each tag produces a <mods:subject><mods:topic> element."""
        _pip_dir, sip_dir = pip_and_sip
        MODSTransformer().transform(sip_dir)
        root = _parse_mods(sip_dir / "articles" / "12345" / "article.mods.xml")
        topics = [el.text for el in root.findall(f".//{_mods_tag('topic')}")]
        expected_tags = [t["name"] for t in sample_ceo_record["tags"]]
        for tag_name in expected_tags:
            assert tag_name in topics

    def test_no_abstract_element_when_none(self, tmp_path, sample_ceo_record):
        """<mods:abstract> is omitted when abstract is None."""
        record = {**sample_ceo_record, "abstract": None}
        pip_dir = tmp_path / "pips" / "no-abstract"
        art_dir = pip_dir / "articles" / "12345"
        art_dir.mkdir(parents=True)
        (art_dir / "ceo_record.json").write_text(json.dumps(record))
        pip_manifest = PIPManifest(
            id="no-abstract",
            title="No Abstract",
            date_range=("2026-01-29", "2026-01-29"),
            articles=[PIPArticle(ceo_id="12345", ceo_record_path="articles/12345/ceo_record.json")],
            pdi=PreservationDescriptionInfo(),
            status="sealed",
        )
        (pip_dir / "pip-manifest.json").write_text(pip_manifest.model_dump_json(indent=2))

        sip_dir = tmp_path / "sips" / "no-abstract"
        (sip_dir / "articles" / "12345").mkdir(parents=True)
        sip_manifest = SIPManifest(
            id="no-abstract",
            pip_id="no-abstract",
            pip_path=str(pip_dir),
            articles=[SIPArticle(ceo_id="12345")],
        )
        (sip_dir / "sip-manifest.json").write_text(sip_manifest.model_dump_json(indent=2))

        MODSTransformer().transform(sip_dir)
        root = _parse_mods(sip_dir / "articles" / "12345" / "article.mods.xml")
        assert root.find(_mods_tag("abstract")) is None

    def test_no_subtitle_when_subhead_none(self, tmp_path, sample_ceo_record):
        """<mods:subTitle> is omitted when subhead is None."""
        record = {**sample_ceo_record, "subhead": None}
        pip_dir = tmp_path / "pips" / "no-subhead"
        art_dir = pip_dir / "articles" / "12345"
        art_dir.mkdir(parents=True)
        (art_dir / "ceo_record.json").write_text(json.dumps(record))
        pip_manifest = PIPManifest(
            id="no-subhead",
            title="No Subhead",
            date_range=("2026-01-29", "2026-01-29"),
            articles=[PIPArticle(ceo_id="12345", ceo_record_path="articles/12345/ceo_record.json")],
            pdi=PreservationDescriptionInfo(),
            status="sealed",
        )
        (pip_dir / "pip-manifest.json").write_text(pip_manifest.model_dump_json(indent=2))

        sip_dir = tmp_path / "sips" / "no-subhead"
        (sip_dir / "articles" / "12345").mkdir(parents=True)
        sip_manifest = SIPManifest(
            id="no-subhead",
            pip_id="no-subhead",
            pip_path=str(pip_dir),
            articles=[SIPArticle(ceo_id="12345")],
        )
        (sip_dir / "sip-manifest.json").write_text(sip_manifest.model_dump_json(indent=2))

        MODSTransformer().transform(sip_dir)
        root = _parse_mods(sip_dir / "articles" / "12345" / "article.mods.xml")
        assert root.find(f".//{_mods_tag('subTitle')}") is None


# ---------------------------------------------------------------------------
# Tests: Error handling
# ---------------------------------------------------------------------------

class TestMODSTransformerErrorHandling:
    def test_missing_pip_path_raises_error(self, tmp_path):
        """transform() records a validation error when pip_path is not set."""
        sip_dir = tmp_path / "sip"
        sip_dir.mkdir()
        manifest = SIPManifest(
            id="no-pip",
            pip_id="no-pip",
            pip_path=None,
            articles=[SIPArticle(ceo_id="12345")],
        )
        (sip_dir / "sip-manifest.json").write_text(manifest.model_dump_json(indent=2))

        result = MODSTransformer().transform(sip_dir)
        assert len(result.validation_errors) >= 1
        assert "12345" in result.validation_errors[0]

    def test_missing_ceo_record_records_error(self, tmp_path, sample_ceo_record):
        """transform() records a validation error when ceo_record.json is missing."""
        pip_dir = tmp_path / "pips" / "missing-record"
        (pip_dir / "articles" / "12345").mkdir(parents=True)
        # Intentionally do NOT write ceo_record.json

        pip_manifest = PIPManifest(
            id="missing-record",
            title="Missing Record",
            date_range=("2026-01-29", "2026-01-29"),
            articles=[PIPArticle(ceo_id="12345", ceo_record_path="articles/12345/ceo_record.json")],
            pdi=PreservationDescriptionInfo(),
            status="sealed",
        )
        (pip_dir / "pip-manifest.json").write_text(pip_manifest.model_dump_json(indent=2))

        sip_dir = tmp_path / "sips" / "missing-record"
        (sip_dir / "articles" / "12345").mkdir(parents=True)
        sip_manifest = SIPManifest(
            id="missing-record",
            pip_id="missing-record",
            pip_path=str(pip_dir),
            articles=[SIPArticle(ceo_id="12345")],
        )
        (sip_dir / "sip-manifest.json").write_text(sip_manifest.model_dump_json(indent=2))

        result = MODSTransformer().transform(sip_dir)
        assert len(result.validation_errors) == 1
        assert "12345" in result.validation_errors[0]

    def test_continues_after_article_error(self, tmp_path, sample_ceo_record):
        """transform() processes remaining articles after one fails."""
        pip_dir = tmp_path / "pips" / "partial"

        # First article: ceo_record.json is missing
        (pip_dir / "articles" / "bad").mkdir(parents=True)

        # Second article: valid record
        good_dir = pip_dir / "articles" / "good"
        good_dir.mkdir(parents=True)
        (good_dir / "ceo_record.json").write_text(
            json.dumps({**sample_ceo_record, "id": "good", "ceo_id": "good", "uuid": "uuid-good"})
        )

        pip_manifest = PIPManifest(
            id="partial",
            title="Partial",
            date_range=("2026-01-29", "2026-01-29"),
            articles=[
                PIPArticle(ceo_id="bad", ceo_record_path="articles/bad/ceo_record.json"),
                PIPArticle(ceo_id="good", ceo_record_path="articles/good/ceo_record.json"),
            ],
            pdi=PreservationDescriptionInfo(),
            status="sealed",
        )
        (pip_dir / "pip-manifest.json").write_text(pip_manifest.model_dump_json(indent=2))

        sip_dir = tmp_path / "sips" / "partial"
        for ceo_id in ("bad", "good"):
            (sip_dir / "articles" / ceo_id).mkdir(parents=True)

        sip_manifest = SIPManifest(
            id="partial",
            pip_id="partial",
            pip_path=str(pip_dir),
            articles=[SIPArticle(ceo_id="bad"), SIPArticle(ceo_id="good")],
        )
        (sip_dir / "sip-manifest.json").write_text(sip_manifest.model_dump_json(indent=2))

        result = MODSTransformer().transform(sip_dir)

        assert len(result.validation_errors) == 1
        assert "bad" in result.validation_errors[0]
        assert (sip_dir / "articles" / "good" / "article.mods.xml").exists()

    def test_article_not_in_pip_records_error(self, tmp_path, sample_ceo_record):
        """transform() records an error when a SIP article has no matching PIP entry."""
        pip_dir = tmp_path / "pips" / "mismatch"
        (pip_dir / "articles" / "known").mkdir(parents=True)
        (pip_dir / "articles" / "known" / "ceo_record.json").write_text(
            json.dumps({**sample_ceo_record, "id": "known", "ceo_id": "known"})
        )

        pip_manifest = PIPManifest(
            id="mismatch",
            title="Mismatch",
            date_range=("2026-01-29", "2026-01-29"),
            articles=[PIPArticle(ceo_id="known", ceo_record_path="articles/known/ceo_record.json")],
            pdi=PreservationDescriptionInfo(),
            status="sealed",
        )
        (pip_dir / "pip-manifest.json").write_text(pip_manifest.model_dump_json(indent=2))

        sip_dir = tmp_path / "sips" / "mismatch"
        (sip_dir / "articles" / "unknown").mkdir(parents=True)

        sip_manifest = SIPManifest(
            id="mismatch",
            pip_id="mismatch",
            pip_path=str(pip_dir),
            articles=[SIPArticle(ceo_id="unknown")],
        )
        (sip_dir / "sip-manifest.json").write_text(sip_manifest.model_dump_json(indent=2))

        result = MODSTransformer().transform(sip_dir)
        assert len(result.validation_errors) == 1
        assert "unknown" in result.validation_errors[0]


# ---------------------------------------------------------------------------
# Tests: Internal helpers
# ---------------------------------------------------------------------------

class TestMODSTransformerHelpers:
    def test_strip_html_removes_tags(self):
        """_strip_html() removes HTML tags from text."""
        transformer = MODSTransformer()
        assert transformer._strip_html("<p>Hello world</p>") == "Hello world"

    def test_strip_html_removes_nested_tags(self):
        """_strip_html() removes nested HTML tags."""
        transformer = MODSTransformer()
        result = transformer._strip_html("<p><strong>Bold</strong> text</p>")
        assert result == "Bold text"

    def test_strip_html_unescapes_entities(self):
        """_strip_html() converts HTML entities to unicode characters."""
        transformer = MODSTransformer()
        result = transformer._strip_html("A &amp; B &lt;C&gt;")
        assert result == "A & B <C>"

    def test_strip_html_plain_text_unchanged(self):
        """_strip_html() leaves plain text without HTML unchanged."""
        transformer = MODSTransformer()
        assert transformer._strip_html("plain text") == "plain text"

    def test_strip_html_empty_string(self):
        """_strip_html() handles empty string."""
        transformer = MODSTransformer()
        assert transformer._strip_html("") == ""
