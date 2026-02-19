"""Tests for pipeline filter implementations and the Orchestrator."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from periodical_distiller.pipeline.filters.alto_filter import AltoFilter
from periodical_distiller.pipeline.filters.html_filter import HtmlFilter
from periodical_distiller.pipeline.filters.image_filter import ImageFilter
from periodical_distiller.pipeline.filters.mets_filter import MetsFilter
from periodical_distiller.pipeline.filters.mods_filter import ModsFilter
from periodical_distiller.pipeline.filters.pdf_filter import PdfFilter
from periodical_distiller.pipeline.filters.sip_transformer_filter import SIPTransformerFilter
from periodical_distiller.pipeline.orchestrator import Orchestrator
from periodical_distiller.pipeline.plumbing import Pipe, Token, dump_token, load_token
from schemas.pip import PIPArticle, PIPManifest
from schemas.sip import SIPArticle, SIPManifest, SIPPage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_manifest(ceo_id: str = "12345", mets_path: str | None = None) -> SIPManifest:
    """Build a minimal SIPManifest for use in mock returns."""
    return SIPManifest(
        id="2026-01-29",
        pip_id="2026-01-29",
        mets_path=mets_path,
        articles=[SIPArticle(ceo_id=ceo_id)],
    )


def _seed_token(bucket: Path, token_id: str, props: dict) -> Path:
    """Write a token JSON file to *bucket* and return the path."""
    content = {"id": token_id, **props}
    token_path = bucket / f"{token_id}.json"
    token_path.write_text(json.dumps(content, indent=2))
    return token_path


# ---------------------------------------------------------------------------
# Tests: HtmlFilter
# ---------------------------------------------------------------------------

class TestHtmlFilter:
    @pytest.fixture
    def buckets(self, tmp_path):
        in_bucket = tmp_path / "pip_harvested"
        out_bucket = tmp_path / "html_transform"
        in_bucket.mkdir()
        out_bucket.mkdir()
        return in_bucket, out_bucket

    @pytest.fixture
    def mock_transformer(self):
        t = MagicMock()
        t.transform.return_value = _make_manifest()
        return t

    def test_token_advances_to_output_bucket(self, buckets, mock_transformer, tmp_path):
        """run_once() moves token from input to output bucket."""
        in_bucket, out_bucket = buckets
        sip_base = tmp_path / "sips"
        pip_path = tmp_path / "pips" / "2026-01-29"
        pip_path.mkdir(parents=True)

        _seed_token(in_bucket, "2026-01-29", {"pip_path": str(pip_path)})

        f = HtmlFilter(
            pipe=Pipe(in_bucket, out_bucket),
            transformer=mock_transformer,
            sip_base=sip_base,
        )
        result = f.run_once()

        assert result is True
        assert (out_bucket / "2026-01-29.json").exists()

    def test_sets_sip_path_on_token(self, buckets, mock_transformer, tmp_path):
        """run_once() sets sip_path prop on the token."""
        in_bucket, out_bucket = buckets
        sip_base = tmp_path / "sips"
        pip_path = tmp_path / "pips" / "2026-01-29"
        pip_path.mkdir(parents=True)

        _seed_token(in_bucket, "2026-01-29", {"pip_path": str(pip_path)})

        f = HtmlFilter(
            pipe=Pipe(in_bucket, out_bucket),
            transformer=mock_transformer,
            sip_base=sip_base,
        )
        f.run_once()

        token_data = json.loads((out_bucket / "2026-01-29.json").read_text())
        assert "sip_path" in token_data
        assert "2026-01-29" in token_data["sip_path"]

    def test_sets_article_ids_on_token(self, buckets, mock_transformer, tmp_path):
        """run_once() sets article_ids prop from manifest articles."""
        in_bucket, out_bucket = buckets
        sip_base = tmp_path / "sips"
        pip_path = tmp_path / "pips" / "2026-01-29"
        pip_path.mkdir(parents=True)

        _seed_token(in_bucket, "2026-01-29", {"pip_path": str(pip_path)})

        f = HtmlFilter(
            pipe=Pipe(in_bucket, out_bucket),
            transformer=mock_transformer,
            sip_base=sip_base,
        )
        f.run_once()

        token_data = json.loads((out_bucket / "2026-01-29.json").read_text())
        assert token_data["article_ids"] == ["12345"]

    def test_validation_error_on_missing_pip_path(self, buckets, mock_transformer, tmp_path):
        """run_once() sends token to .err when pip_path is missing."""
        in_bucket, out_bucket = buckets
        sip_base = tmp_path / "sips"

        _seed_token(in_bucket, "2026-01-29", {})  # no pip_path

        f = HtmlFilter(
            pipe=Pipe(in_bucket, out_bucket),
            transformer=mock_transformer,
            sip_base=sip_base,
        )
        result = f.run_once()

        assert result is False
        assert (in_bucket / "2026-01-29.err").exists()
        assert not (out_bucket / "2026-01-29.json").exists()

    def test_transformer_exception_sends_token_to_err(self, buckets, tmp_path):
        """run_once() routes token to .err when transformer raises."""
        in_bucket, out_bucket = buckets
        sip_base = tmp_path / "sips"
        pip_path = tmp_path / "pips" / "2026-01-29"
        pip_path.mkdir(parents=True)

        _seed_token(in_bucket, "2026-01-29", {"pip_path": str(pip_path)})

        bad_transformer = MagicMock()
        bad_transformer.transform.side_effect = RuntimeError("HTML failed")

        f = HtmlFilter(
            pipe=Pipe(in_bucket, out_bucket),
            transformer=bad_transformer,
            sip_base=sip_base,
        )
        result = f.run_once()

        assert result is False
        assert (in_bucket / "2026-01-29.err").exists()

    def test_validation_errors_stored_on_token(self, buckets, tmp_path):
        """run_once() stores validation_errors from manifest on token."""
        in_bucket, out_bucket = buckets
        sip_base = tmp_path / "sips"
        pip_path = tmp_path / "pips" / "2026-01-29"
        pip_path.mkdir(parents=True)

        _seed_token(in_bucket, "2026-01-29", {"pip_path": str(pip_path)})

        manifest_with_errors = _make_manifest()
        manifest_with_errors.validation_errors = ["Article 99: some error"]

        transformer = MagicMock()
        transformer.transform.return_value = manifest_with_errors

        f = HtmlFilter(
            pipe=Pipe(in_bucket, out_bucket),
            transformer=transformer,
            sip_base=sip_base,
        )
        f.run_once()

        token_data = json.loads((out_bucket / "2026-01-29.json").read_text())
        assert "validation_errors" in token_data
        assert "Article 99: some error" in token_data["validation_errors"]

    def test_no_tokens_returns_false(self, buckets, mock_transformer, tmp_path):
        """run_once() returns False when no tokens are available."""
        in_bucket, out_bucket = buckets
        sip_base = tmp_path / "sips"

        f = HtmlFilter(
            pipe=Pipe(in_bucket, out_bucket),
            transformer=mock_transformer,
            sip_base=sip_base,
        )
        assert f.run_once() is False


# ---------------------------------------------------------------------------
# Tests: PdfFilter
# ---------------------------------------------------------------------------

class TestPdfFilter:
    @pytest.fixture
    def buckets(self, tmp_path):
        in_bucket = tmp_path / "html_transform"
        out_bucket = tmp_path / "pdf_transform"
        in_bucket.mkdir()
        out_bucket.mkdir()
        return in_bucket, out_bucket

    @pytest.fixture
    def mock_transformer(self):
        t = MagicMock()
        t.transform.return_value = _make_manifest()
        return t

    def test_token_advances_to_output_bucket(self, buckets, mock_transformer):
        """run_once() moves token from input to output bucket."""
        in_bucket, out_bucket = buckets
        _seed_token(in_bucket, "2026-01-29", {"sip_path": "/some/sip"})

        f = PdfFilter(pipe=Pipe(in_bucket, out_bucket), transformer=mock_transformer)
        assert f.run_once() is True
        assert (out_bucket / "2026-01-29.json").exists()

    def test_validation_error_on_missing_sip_path(self, buckets, mock_transformer):
        """run_once() sends token to .err when sip_path is missing."""
        in_bucket, out_bucket = buckets
        _seed_token(in_bucket, "2026-01-29", {})  # no sip_path

        f = PdfFilter(pipe=Pipe(in_bucket, out_bucket), transformer=mock_transformer)
        assert f.run_once() is False
        assert (in_bucket / "2026-01-29.err").exists()

    def test_transformer_exception_sends_token_to_err(self, buckets):
        """run_once() routes token to .err when transformer raises."""
        in_bucket, out_bucket = buckets
        _seed_token(in_bucket, "2026-01-29", {"sip_path": "/some/sip"})

        bad_transformer = MagicMock()
        bad_transformer.transform.side_effect = RuntimeError("PDF failed")

        f = PdfFilter(pipe=Pipe(in_bucket, out_bucket), transformer=bad_transformer)
        assert f.run_once() is False
        assert (in_bucket / "2026-01-29.err").exists()

    def test_no_tokens_returns_false(self, buckets, mock_transformer):
        """run_once() returns False when no tokens are available."""
        in_bucket, out_bucket = buckets
        f = PdfFilter(pipe=Pipe(in_bucket, out_bucket), transformer=mock_transformer)
        assert f.run_once() is False


# ---------------------------------------------------------------------------
# Tests: AltoFilter
# ---------------------------------------------------------------------------

class TestAltoFilter:
    @pytest.fixture
    def buckets(self, tmp_path):
        in_bucket = tmp_path / "pdf_transform"
        out_bucket = tmp_path / "alto_transform"
        in_bucket.mkdir()
        out_bucket.mkdir()
        return in_bucket, out_bucket

    @pytest.fixture
    def mock_transformer(self):
        t = MagicMock()
        t.transform.return_value = _make_manifest()
        return t

    def test_token_advances_to_output_bucket(self, buckets, mock_transformer):
        """run_once() moves token from input to output bucket."""
        in_bucket, out_bucket = buckets
        _seed_token(in_bucket, "2026-01-29", {"sip_path": "/some/sip"})

        f = AltoFilter(pipe=Pipe(in_bucket, out_bucket), transformer=mock_transformer)
        assert f.run_once() is True
        assert (out_bucket / "2026-01-29.json").exists()

    def test_validation_error_on_missing_sip_path(self, buckets, mock_transformer):
        """run_once() sends token to .err when sip_path is missing."""
        in_bucket, out_bucket = buckets
        _seed_token(in_bucket, "2026-01-29", {})

        f = AltoFilter(pipe=Pipe(in_bucket, out_bucket), transformer=mock_transformer)
        assert f.run_once() is False
        assert (in_bucket / "2026-01-29.err").exists()

    def test_transformer_exception_sends_token_to_err(self, buckets):
        """run_once() routes token to .err when transformer raises."""
        in_bucket, out_bucket = buckets
        _seed_token(in_bucket, "2026-01-29", {"sip_path": "/some/sip"})

        bad_transformer = MagicMock()
        bad_transformer.transform.side_effect = RuntimeError("ALTO failed")

        f = AltoFilter(pipe=Pipe(in_bucket, out_bucket), transformer=bad_transformer)
        assert f.run_once() is False
        assert (in_bucket / "2026-01-29.err").exists()


# ---------------------------------------------------------------------------
# Tests: ModsFilter
# ---------------------------------------------------------------------------

class TestModsFilter:
    @pytest.fixture
    def buckets(self, tmp_path):
        in_bucket = tmp_path / "alto_transform"
        out_bucket = tmp_path / "mods_transform"
        in_bucket.mkdir()
        out_bucket.mkdir()
        return in_bucket, out_bucket

    @pytest.fixture
    def mock_transformer(self):
        t = MagicMock()
        t.transform.return_value = _make_manifest()
        return t

    def test_token_advances_to_output_bucket(self, buckets, mock_transformer):
        """run_once() moves token from input to output bucket."""
        in_bucket, out_bucket = buckets
        _seed_token(in_bucket, "2026-01-29", {"sip_path": "/some/sip"})

        f = ModsFilter(pipe=Pipe(in_bucket, out_bucket), transformer=mock_transformer)
        assert f.run_once() is True
        assert (out_bucket / "2026-01-29.json").exists()

    def test_validation_error_on_missing_sip_path(self, buckets, mock_transformer):
        """run_once() sends token to .err when sip_path is missing."""
        in_bucket, out_bucket = buckets
        _seed_token(in_bucket, "2026-01-29", {})

        f = ModsFilter(pipe=Pipe(in_bucket, out_bucket), transformer=mock_transformer)
        assert f.run_once() is False
        assert (in_bucket / "2026-01-29.err").exists()

    def test_transformer_exception_sends_token_to_err(self, buckets):
        """run_once() routes token to .err when transformer raises."""
        in_bucket, out_bucket = buckets
        _seed_token(in_bucket, "2026-01-29", {"sip_path": "/some/sip"})

        bad_transformer = MagicMock()
        bad_transformer.transform.side_effect = RuntimeError("MODS failed")

        f = ModsFilter(pipe=Pipe(in_bucket, out_bucket), transformer=bad_transformer)
        assert f.run_once() is False
        assert (in_bucket / "2026-01-29.err").exists()


# ---------------------------------------------------------------------------
# Tests: ImageFilter
# ---------------------------------------------------------------------------

class TestImageFilter:
    @pytest.fixture
    def buckets(self, tmp_path):
        in_bucket = tmp_path / "mods_transform"
        out_bucket = tmp_path / "image_transform"
        in_bucket.mkdir()
        out_bucket.mkdir()
        return in_bucket, out_bucket

    @pytest.fixture
    def mock_transformer(self):
        t = MagicMock()
        t.transform.return_value = _make_manifest()
        return t

    def test_token_advances_to_output_bucket(self, buckets, mock_transformer):
        """run_once() moves token from input to output bucket."""
        in_bucket, out_bucket = buckets
        _seed_token(in_bucket, "2026-01-29", {"sip_path": "/some/sip"})

        f = ImageFilter(pipe=Pipe(in_bucket, out_bucket), transformer=mock_transformer)
        assert f.run_once() is True
        assert (out_bucket / "2026-01-29.json").exists()

    def test_validation_error_on_missing_sip_path(self, buckets, mock_transformer):
        """run_once() sends token to .err when sip_path is missing."""
        in_bucket, out_bucket = buckets
        _seed_token(in_bucket, "2026-01-29", {})

        f = ImageFilter(pipe=Pipe(in_bucket, out_bucket), transformer=mock_transformer)
        assert f.run_once() is False
        assert (in_bucket / "2026-01-29.err").exists()

    def test_transformer_exception_sends_token_to_err(self, buckets):
        """run_once() routes token to .err when transformer raises."""
        in_bucket, out_bucket = buckets
        _seed_token(in_bucket, "2026-01-29", {"sip_path": "/some/sip"})

        bad_transformer = MagicMock()
        bad_transformer.transform.side_effect = RuntimeError("Image failed")

        f = ImageFilter(pipe=Pipe(in_bucket, out_bucket), transformer=bad_transformer)
        assert f.run_once() is False
        assert (in_bucket / "2026-01-29.err").exists()


# ---------------------------------------------------------------------------
# Tests: SIPTransformerFilter — validation_errors propagation
# ---------------------------------------------------------------------------

class TestSIPTransformerFilterValidationErrors:
    """Verify that all SIPTransformerFilter subclasses propagate validation_errors.

    HtmlFilter already has test_validation_errors_stored_on_token; this class
    covers the four SIPTransformer-backed filters with a single parametrized test.
    """

    @pytest.mark.parametrize("filter_cls", [PdfFilter, AltoFilter, ModsFilter, ImageFilter])
    def test_validation_errors_stored_on_token(self, filter_cls, tmp_path):
        """Manifest validation_errors are written to the token for all SIP filters."""
        in_bucket = tmp_path / "in"
        out_bucket = tmp_path / "out"
        in_bucket.mkdir()
        out_bucket.mkdir()

        _seed_token(in_bucket, "2026-01-29", {"sip_path": "/some/sip"})

        manifest_with_errors = _make_manifest()
        manifest_with_errors.validation_errors = ["Article 99: transform failed"]

        mock_transformer = MagicMock()
        mock_transformer.transform.return_value = manifest_with_errors

        f = filter_cls(pipe=Pipe(in_bucket, out_bucket), transformer=mock_transformer)
        result = f.run_once()

        # Token still advances — validation_errors are non-fatal
        assert result is True
        token_data = json.loads((out_bucket / "2026-01-29.json").read_text())
        assert "validation_errors" in token_data
        assert "Article 99: transform failed" in token_data["validation_errors"]


# ---------------------------------------------------------------------------
# Tests: MetsFilter
# ---------------------------------------------------------------------------

class TestMetsFilter:
    @pytest.fixture
    def buckets(self, tmp_path):
        in_bucket = tmp_path / "image_transform"
        out_bucket = tmp_path / "sip_complete"
        in_bucket.mkdir()
        out_bucket.mkdir()
        return in_bucket, out_bucket

    @pytest.fixture
    def mock_compiler(self):
        c = MagicMock()
        sealed = _make_manifest(mets_path="mets.xml")
        sealed.status = "sealed"
        c.compile.return_value = sealed
        return c

    def test_token_advances_to_output_bucket(self, buckets, mock_compiler):
        """run_once() moves token from input to output bucket."""
        in_bucket, out_bucket = buckets
        _seed_token(in_bucket, "2026-01-29", {"sip_path": "/some/sip"})

        f = MetsFilter(pipe=Pipe(in_bucket, out_bucket), compiler=mock_compiler)
        assert f.run_once() is True
        assert (out_bucket / "2026-01-29.json").exists()

    def test_sets_mets_path_on_token(self, buckets, mock_compiler):
        """run_once() sets mets_path prop on the token."""
        in_bucket, out_bucket = buckets
        _seed_token(in_bucket, "2026-01-29", {"sip_path": "/some/sip"})

        f = MetsFilter(pipe=Pipe(in_bucket, out_bucket), compiler=mock_compiler)
        f.run_once()

        token_data = json.loads((out_bucket / "2026-01-29.json").read_text())
        assert token_data["mets_path"] == "mets.xml"

    def test_sets_status_on_token(self, buckets, mock_compiler):
        """run_once() sets status prop on the token."""
        in_bucket, out_bucket = buckets
        _seed_token(in_bucket, "2026-01-29", {"sip_path": "/some/sip"})

        f = MetsFilter(pipe=Pipe(in_bucket, out_bucket), compiler=mock_compiler)
        f.run_once()

        token_data = json.loads((out_bucket / "2026-01-29.json").read_text())
        assert token_data["status"] == "sealed"

    def test_validation_error_on_missing_sip_path(self, buckets, mock_compiler):
        """run_once() sends token to .err when sip_path is missing."""
        in_bucket, out_bucket = buckets
        _seed_token(in_bucket, "2026-01-29", {})

        f = MetsFilter(pipe=Pipe(in_bucket, out_bucket), compiler=mock_compiler)
        assert f.run_once() is False
        assert (in_bucket / "2026-01-29.err").exists()

    def test_compiler_exception_sends_token_to_err(self, buckets):
        """run_once() routes token to .err when compiler raises."""
        in_bucket, out_bucket = buckets
        _seed_token(in_bucket, "2026-01-29", {"sip_path": "/some/sip"})

        bad_compiler = MagicMock()
        bad_compiler.compile.side_effect = RuntimeError("METS compile failed")

        f = MetsFilter(pipe=Pipe(in_bucket, out_bucket), compiler=bad_compiler)
        assert f.run_once() is False
        assert (in_bucket / "2026-01-29.err").exists()

    def test_no_tokens_returns_false(self, buckets, mock_compiler):
        """run_once() returns False when no tokens are available."""
        in_bucket, out_bucket = buckets
        f = MetsFilter(pipe=Pipe(in_bucket, out_bucket), compiler=mock_compiler)
        assert f.run_once() is False


# ---------------------------------------------------------------------------
# Tests: Orchestrator (integration)
# ---------------------------------------------------------------------------

@pytest.fixture
def minimal_pip(tmp_path, sample_ceo_record):
    """Minimal PIP fixture for Orchestrator integration test."""
    pip_dir = tmp_path / "pips" / "2026-01-29"
    article_dir = pip_dir / "articles" / "12345"
    article_dir.mkdir(parents=True)
    (article_dir / "ceo_record.json").write_text(json.dumps(sample_ceo_record))

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
    (pip_dir / "pip-manifest.json").write_text(pip_manifest.model_dump_json(indent=2))
    return pip_dir


class TestOrchestrator:
    def test_instantiation(self, tmp_path):
        """Orchestrator can be instantiated with workspace and sip_output."""
        workspace = tmp_path / "workspace"
        sip_output = tmp_path / "sips"
        orchestrator = Orchestrator(workspace=workspace, sip_output=sip_output)
        assert orchestrator is not None

    def test_creates_all_bucket_dirs(self, tmp_path):
        """Orchestrator creates all BUCKET_NAMES directories under workspace."""
        from periodical_distiller.pipeline.orchestrator import BUCKET_NAMES
        workspace = tmp_path / "workspace"
        sip_output = tmp_path / "sips"
        Orchestrator(workspace=workspace, sip_output=sip_output)
        for name in BUCKET_NAMES:
            assert (workspace / name).is_dir(), f"Bucket dir missing: {name}"

    def test_run_returns_token(self, tmp_path, minimal_pip):
        """Orchestrator.run() returns a Token after processing."""
        workspace = tmp_path / "workspace"
        sip_output = tmp_path / "sips"
        orchestrator = Orchestrator(workspace=workspace, sip_output=sip_output)
        token = orchestrator.run(minimal_pip)
        assert isinstance(token, Token)

    def test_run_produces_sealed_sip(self, tmp_path, minimal_pip):
        """Orchestrator.run() produces a sealed SIP with status='sealed'."""
        workspace = tmp_path / "workspace"
        sip_output = tmp_path / "sips"
        orchestrator = Orchestrator(workspace=workspace, sip_output=sip_output)
        token = orchestrator.run(minimal_pip)
        assert token.get_prop("status") == "sealed"

    def test_run_produces_mets_xml(self, tmp_path, minimal_pip):
        """Orchestrator.run() produces a mets.xml file in the SIP."""
        workspace = tmp_path / "workspace"
        sip_output = tmp_path / "sips"
        orchestrator = Orchestrator(workspace=workspace, sip_output=sip_output)
        orchestrator.run(minimal_pip)
        sip_path = sip_output / "2026-01-29"
        assert (sip_path / "mets.xml").exists()

    def test_run_token_in_sip_complete_bucket(self, tmp_path, minimal_pip):
        """After Orchestrator.run(), token JSON is in sip_complete bucket."""
        workspace = tmp_path / "workspace"
        sip_output = tmp_path / "sips"
        orchestrator = Orchestrator(workspace=workspace, sip_output=sip_output)
        orchestrator.run(minimal_pip)
        sip_complete = workspace / "sip_complete"
        assert (sip_complete / "2026-01-29.json").exists()

    def test_run_sets_sip_path_on_token(self, tmp_path, minimal_pip):
        """Orchestrator.run() sets sip_path prop on the returned token."""
        workspace = tmp_path / "workspace"
        sip_output = tmp_path / "sips"
        orchestrator = Orchestrator(workspace=workspace, sip_output=sip_output)
        token = orchestrator.run(minimal_pip)
        sip_path = token.get_prop("sip_path")
        assert sip_path is not None
        assert "2026-01-29" in sip_path
