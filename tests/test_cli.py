"""Tests for the CLI module."""

import json
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from periodical_distiller.cli import main


class TestCLIHarvestPIP:
    """Tests for the harvest-pip command."""

    def test_harvest_pip_requires_date_arguments(self, caplog):
        """harvest-pip fails without date arguments."""
        result = main(["harvest-pip"])

        assert result == 1
        assert "Must specify either --date or both --start and --end" in caplog.text

    def test_harvest_pip_rejects_mixed_arguments(self, caplog):
        """harvest-pip fails with both --date and --start/--end."""
        result = main([
            "harvest-pip",
            "--date", "2026-01-15",
            "--start", "2026-01-15",
            "--end", "2026-01-17",
        ])

        assert result == 1
        assert "Cannot specify both --date and --start/--end" in caplog.text

    def test_harvest_pip_rejects_partial_range(self, caplog):
        """harvest-pip fails with only --start or only --end."""
        result = main(["harvest-pip", "--start", "2026-01-15"])

        assert result == 1
        assert "Must specify either --date or both --start and --end" in caplog.text

    @patch("periodical_distiller.cli.CeoClient")
    def test_harvest_pip_single_date(
        self, mock_client_class, tmp_path, sample_ceo_record
    ):
        """harvest-pip creates PIP for single date."""
        from schemas.ceo_item import CeoItem

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.base_url = "https://www.dailyprincetonian.com"
        mock_client.fetch_by_date = MagicMock(
            return_value=[CeoItem.model_validate(sample_ceo_record)]
        )
        mock_client_class.return_value = mock_client

        result = main([
            "harvest-pip",
            "--date", "2026-01-15",
            "--output", str(tmp_path),
        ])

        assert result == 0
        mock_client.fetch_by_date.assert_called_once_with(date(2026, 1, 15))
        assert (tmp_path / "2026-01-15" / "pip-manifest.json").exists()

    @patch("periodical_distiller.cli.CeoClient")
    def test_harvest_pip_date_range(
        self, mock_client_class, tmp_path, sample_ceo_record
    ):
        """harvest-pip creates PIP for date range."""
        from schemas.ceo_item import CeoItem

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.base_url = "https://www.dailyprincetonian.com"
        mock_client.fetch_by_date_range = MagicMock(
            return_value=[CeoItem.model_validate(sample_ceo_record)]
        )
        mock_client_class.return_value = mock_client

        result = main([
            "harvest-pip",
            "--start", "2026-01-15",
            "--end", "2026-01-17",
            "--output", str(tmp_path),
        ])

        assert result == 0
        mock_client.fetch_by_date_range.assert_called_once_with(
            date(2026, 1, 15), date(2026, 1, 17)
        )
        assert (tmp_path / "2026-01-15_to_2026-01-17" / "pip-manifest.json").exists()

    @patch("periodical_distiller.cli.CeoClient")
    def test_harvest_pip_creates_output_dir(
        self, mock_client_class, tmp_path, sample_ceo_record
    ):
        """harvest-pip creates output directory if it doesn't exist."""
        from schemas.ceo_item import CeoItem

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.base_url = "https://www.dailyprincetonian.com"
        mock_client.fetch_by_date = MagicMock(
            return_value=[CeoItem.model_validate(sample_ceo_record)]
        )
        mock_client_class.return_value = mock_client

        output_dir = tmp_path / "nested" / "output"

        result = main([
            "harvest-pip",
            "--date", "2026-01-15",
            "--output", str(output_dir),
        ])

        assert result == 0
        assert output_dir.exists()

    @patch("periodical_distiller.cli.CeoClient")
    def test_harvest_pip_custom_base_url(
        self, mock_client_class, tmp_path, sample_ceo_record
    ):
        """harvest-pip accepts custom base URL."""
        from schemas.ceo_item import CeoItem

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.base_url = "https://custom.example.com"
        mock_client.fetch_by_date = MagicMock(
            return_value=[CeoItem.model_validate(sample_ceo_record)]
        )
        mock_client_class.return_value = mock_client

        result = main([
            "harvest-pip",
            "--date", "2026-01-15",
            "--output", str(tmp_path),
            "--base-url", "https://custom.example.com",
        ])

        assert result == 0
        call_args = mock_client_class.call_args[0][0]
        assert call_args["base_url"] == "https://custom.example.com"
        assert "User-Agent" in call_args["headers"]

    @patch("periodical_distiller.cli.CeoClient")
    def test_harvest_pip_handles_exception(
        self, mock_client_class, tmp_path, caplog
    ):
        """harvest-pip returns error code on exception."""
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.fetch_by_date = MagicMock(
            side_effect=Exception("Network error")
        )
        mock_client_class.return_value = mock_client

        result = main([
            "harvest-pip",
            "--date", "2026-01-15",
            "--output", str(tmp_path),
        ])

        assert result == 1
        assert "Failed to create PIP" in caplog.text


class TestCLITransformALTO:
    """Tests for the transform-alto command."""

    def test_transform_alto_requires_sip_argument(self, capsys):
        """transform-alto fails without --sip argument."""
        with pytest.raises(SystemExit) as exc_info:
            main(["transform-alto"])
        assert exc_info.value.code != 0

    def test_transform_alto_missing_sip_directory(self, tmp_path, caplog):
        """transform-alto returns error when SIP directory does not exist."""
        result = main(["transform-alto", "--sip", str(tmp_path / "nonexistent")])
        assert result == 1
        assert "SIP directory not found" in caplog.text

    def test_transform_alto_missing_manifest(self, tmp_path, caplog):
        """transform-alto returns error when SIP manifest is missing."""
        sip_dir = tmp_path / "sip"
        sip_dir.mkdir()

        result = main(["transform-alto", "--sip", str(sip_dir)])
        assert result == 1
        assert "SIP manifest not found" in caplog.text

    @patch("periodical_distiller.cli.ALTOTransformer")
    def test_transform_alto_success(self, mock_transformer_class, tmp_path):
        """transform-alto returns 0 on success."""
        from schemas.sip import SIPArticle, SIPManifest, SIPPage

        sip_dir = tmp_path / "sip"
        sip_dir.mkdir()
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

        mock_transformer = MagicMock()
        mock_transformer.transform.return_value = manifest
        mock_transformer_class.return_value = mock_transformer

        result = main(["transform-alto", "--sip", str(sip_dir)])

        assert result == 0
        mock_transformer.transform.assert_called_once_with(sip_dir.resolve())

    @patch("periodical_distiller.cli.ALTOTransformer")
    def test_transform_alto_reports_validation_errors(
        self, mock_transformer_class, tmp_path, caplog
    ):
        """transform-alto logs validation errors from the manifest."""
        from schemas.sip import SIPManifest

        sip_dir = tmp_path / "sip"
        sip_dir.mkdir()
        manifest = SIPManifest(
            id="2026-01-29",
            pip_id="2026-01-29",
            validation_errors=["ALTO generation failed for 12345: file not found"],
        )
        (sip_dir / "sip-manifest.json").write_text(manifest.model_dump_json(indent=2))

        mock_transformer = MagicMock()
        mock_transformer.transform.return_value = manifest
        mock_transformer_class.return_value = mock_transformer

        result = main(["transform-alto", "--sip", str(sip_dir)])

        assert result == 0
        assert "ALTO generation failed for 12345" in caplog.text

    @patch("periodical_distiller.cli.ALTOTransformer")
    def test_transform_alto_handles_exception(
        self, mock_transformer_class, tmp_path, caplog
    ):
        """transform-alto returns error code on unexpected exception."""
        sip_dir = tmp_path / "sip"
        sip_dir.mkdir()
        from schemas.sip import SIPManifest
        manifest = SIPManifest(id="x", pip_id="x")
        (sip_dir / "sip-manifest.json").write_text(manifest.model_dump_json(indent=2))

        mock_transformer = MagicMock()
        mock_transformer.transform.side_effect = Exception("unexpected error")
        mock_transformer_class.return_value = mock_transformer

        result = main(["transform-alto", "--sip", str(sip_dir)])

        assert result == 1
        assert "Failed to transform SIP to ALTO" in caplog.text


class TestCLITransformMODS:
    """Tests for the transform-mods command."""

    def test_transform_mods_requires_sip_argument(self, capsys):
        """transform-mods fails without --sip argument."""
        with pytest.raises(SystemExit) as exc_info:
            main(["transform-mods"])
        assert exc_info.value.code != 0

    def test_transform_mods_missing_sip_directory(self, tmp_path, caplog):
        """transform-mods returns error when SIP directory does not exist."""
        result = main(["transform-mods", "--sip", str(tmp_path / "nonexistent")])
        assert result == 1
        assert "SIP directory not found" in caplog.text

    def test_transform_mods_missing_manifest(self, tmp_path, caplog):
        """transform-mods returns error when SIP manifest is missing."""
        sip_dir = tmp_path / "sip"
        sip_dir.mkdir()

        result = main(["transform-mods", "--sip", str(sip_dir)])
        assert result == 1
        assert "SIP manifest not found" in caplog.text

    @patch("periodical_distiller.cli.MODSTransformer")
    def test_transform_mods_success(self, mock_transformer_class, tmp_path):
        """transform-mods returns 0 on success."""
        from schemas.sip import SIPArticle, SIPManifest

        sip_dir = tmp_path / "sip"
        sip_dir.mkdir()
        manifest = SIPManifest(
            id="2026-01-29",
            pip_id="2026-01-29",
            articles=[
                SIPArticle(
                    ceo_id="12345",
                    mods_path="articles/12345/article.mods.xml",
                )
            ],
        )
        (sip_dir / "sip-manifest.json").write_text(manifest.model_dump_json(indent=2))

        mock_transformer = MagicMock()
        mock_transformer.transform.return_value = manifest
        mock_transformer_class.return_value = mock_transformer

        result = main(["transform-mods", "--sip", str(sip_dir)])

        assert result == 0
        mock_transformer.transform.assert_called_once_with(sip_dir.resolve())

    @patch("periodical_distiller.cli.MODSTransformer")
    def test_transform_mods_reports_validation_errors(
        self, mock_transformer_class, tmp_path, caplog
    ):
        """transform-mods logs validation errors from the manifest."""
        from schemas.sip import SIPManifest

        sip_dir = tmp_path / "sip"
        sip_dir.mkdir()
        manifest = SIPManifest(
            id="2026-01-29",
            pip_id="2026-01-29",
            validation_errors=["MODS generation failed for 12345: file not found"],
        )
        (sip_dir / "sip-manifest.json").write_text(manifest.model_dump_json(indent=2))

        mock_transformer = MagicMock()
        mock_transformer.transform.return_value = manifest
        mock_transformer_class.return_value = mock_transformer

        result = main(["transform-mods", "--sip", str(sip_dir)])

        assert result == 0
        assert "MODS generation failed for 12345" in caplog.text

    @patch("periodical_distiller.cli.MODSTransformer")
    def test_transform_mods_handles_exception(
        self, mock_transformer_class, tmp_path, caplog
    ):
        """transform-mods returns error code on unexpected exception."""
        sip_dir = tmp_path / "sip"
        sip_dir.mkdir()
        from schemas.sip import SIPManifest
        manifest = SIPManifest(id="x", pip_id="x")
        (sip_dir / "sip-manifest.json").write_text(manifest.model_dump_json(indent=2))

        mock_transformer = MagicMock()
        mock_transformer.transform.side_effect = Exception("unexpected error")
        mock_transformer_class.return_value = mock_transformer

        result = main(["transform-mods", "--sip", str(sip_dir)])

        assert result == 1
        assert "Failed to transform SIP to MODS" in caplog.text


class TestCLITransformImage:
    """Tests for the transform-image command."""

    def test_transform_image_requires_sip_argument(self, capsys):
        """transform-image fails without --sip argument."""
        with pytest.raises(SystemExit) as exc_info:
            main(["transform-image"])
        assert exc_info.value.code != 0

    def test_transform_image_missing_sip_directory(self, tmp_path, caplog):
        """transform-image returns error when SIP directory does not exist."""
        result = main(["transform-image", "--sip", str(tmp_path / "nonexistent")])
        assert result == 1
        assert "SIP directory not found" in caplog.text

    def test_transform_image_missing_manifest(self, tmp_path, caplog):
        """transform-image returns error when SIP manifest is missing."""
        sip_dir = tmp_path / "sip"
        sip_dir.mkdir()

        result = main(["transform-image", "--sip", str(sip_dir)])
        assert result == 1
        assert "SIP manifest not found" in caplog.text

    @patch("periodical_distiller.cli.ImageTransformer")
    def test_transform_image_success(self, mock_transformer_class, tmp_path):
        """transform-image returns 0 on success."""
        from schemas.sip import SIPArticle, SIPManifest, SIPPage

        sip_dir = tmp_path / "sip"
        sip_dir.mkdir()
        manifest = SIPManifest(
            id="2026-01-29",
            pip_id="2026-01-29",
            articles=[
                SIPArticle(
                    ceo_id="12345",
                    pdf_path="articles/12345/article.pdf",
                    pages=[
                        SIPPage(
                            page_number=1,
                            alto_path="articles/12345/001.alto.xml",
                            image_path="articles/12345/001.jpg",
                        )
                    ],
                )
            ],
        )
        (sip_dir / "sip-manifest.json").write_text(manifest.model_dump_json(indent=2))

        mock_transformer = MagicMock()
        mock_transformer.transform.return_value = manifest
        mock_transformer_class.return_value = mock_transformer

        result = main(["transform-image", "--sip", str(sip_dir)])

        assert result == 0
        mock_transformer.transform.assert_called_once_with(sip_dir.resolve())

    @patch("periodical_distiller.cli.ImageTransformer")
    def test_transform_image_reports_validation_errors(
        self, mock_transformer_class, tmp_path, caplog
    ):
        """transform-image logs validation errors from the manifest."""
        from schemas.sip import SIPManifest

        sip_dir = tmp_path / "sip"
        sip_dir.mkdir()
        manifest = SIPManifest(
            id="2026-01-29",
            pip_id="2026-01-29",
            validation_errors=["Image generation failed for 12345: file not found"],
        )
        (sip_dir / "sip-manifest.json").write_text(manifest.model_dump_json(indent=2))

        mock_transformer = MagicMock()
        mock_transformer.transform.return_value = manifest
        mock_transformer_class.return_value = mock_transformer

        result = main(["transform-image", "--sip", str(sip_dir)])

        assert result == 0
        assert "Image generation failed for 12345" in caplog.text

    @patch("periodical_distiller.cli.ImageTransformer")
    def test_transform_image_handles_exception(
        self, mock_transformer_class, tmp_path, caplog
    ):
        """transform-image returns error code on unexpected exception."""
        sip_dir = tmp_path / "sip"
        sip_dir.mkdir()
        from schemas.sip import SIPManifest
        manifest = SIPManifest(id="x", pip_id="x")
        (sip_dir / "sip-manifest.json").write_text(manifest.model_dump_json(indent=2))

        mock_transformer = MagicMock()
        mock_transformer.transform.side_effect = Exception("unexpected error")
        mock_transformer_class.return_value = mock_transformer

        result = main(["transform-image", "--sip", str(sip_dir)])

        assert result == 1
        assert "Failed to transform SIP to images" in caplog.text


class TestCLICompileSIP:
    """Tests for the compile-sip command."""

    def test_compile_sip_requires_sip_argument(self, capsys):
        """compile-sip fails without --sip argument."""
        with pytest.raises(SystemExit) as exc_info:
            main(["compile-sip"])
        assert exc_info.value.code != 0

    def test_compile_sip_missing_sip_directory(self, tmp_path, caplog):
        """compile-sip returns error when SIP directory does not exist."""
        result = main(["compile-sip", "--sip", str(tmp_path / "nonexistent")])
        assert result == 1
        assert "SIP directory not found" in caplog.text

    def test_compile_sip_missing_manifest(self, tmp_path, caplog):
        """compile-sip returns error when SIP manifest is missing."""
        sip_dir = tmp_path / "sip"
        sip_dir.mkdir()

        result = main(["compile-sip", "--sip", str(sip_dir)])
        assert result == 1
        assert "SIP manifest not found" in caplog.text

    @patch("periodical_distiller.cli.VeridianSIPCompiler")
    def test_compile_sip_success(self, mock_compiler_class, tmp_path):
        """compile-sip returns 0 on success."""
        from schemas.sip import SIPManifest

        sip_dir = tmp_path / "sip"
        sip_dir.mkdir()
        manifest = SIPManifest(
            id="2026-01-29",
            pip_id="2026-01-29",
            mets_path="mets.xml",
            status="sealed",
        )
        (sip_dir / "sip-manifest.json").write_text(manifest.model_dump_json(indent=2))

        mock_compiler = MagicMock()
        mock_compiler.compile.return_value = manifest
        mock_compiler_class.return_value = mock_compiler

        result = main(["compile-sip", "--sip", str(sip_dir)])

        assert result == 0
        mock_compiler.compile.assert_called_once_with(sip_dir.resolve())

    @patch("periodical_distiller.cli.VeridianSIPCompiler")
    def test_compile_sip_reports_validation_errors(
        self, mock_compiler_class, tmp_path, caplog
    ):
        """compile-sip logs validation errors from the manifest."""
        from schemas.sip import SIPManifest

        sip_dir = tmp_path / "sip"
        sip_dir.mkdir()
        manifest = SIPManifest(
            id="2026-01-29",
            pip_id="2026-01-29",
            mets_path="mets.xml",
            status="sealed",
            validation_errors=["METS build error: missing file"],
        )
        (sip_dir / "sip-manifest.json").write_text(manifest.model_dump_json(indent=2))

        mock_compiler = MagicMock()
        mock_compiler.compile.return_value = manifest
        mock_compiler_class.return_value = mock_compiler

        result = main(["compile-sip", "--sip", str(sip_dir)])

        assert result == 0
        assert "METS build error: missing file" in caplog.text

    @patch("periodical_distiller.cli.VeridianSIPCompiler")
    def test_compile_sip_handles_exception(
        self, mock_compiler_class, tmp_path, caplog
    ):
        """compile-sip returns error code on unexpected exception."""
        sip_dir = tmp_path / "sip"
        sip_dir.mkdir()
        from schemas.sip import SIPManifest
        manifest = SIPManifest(id="x", pip_id="x")
        (sip_dir / "sip-manifest.json").write_text(manifest.model_dump_json(indent=2))

        mock_compiler = MagicMock()
        mock_compiler.compile.side_effect = Exception("unexpected error")
        mock_compiler_class.return_value = mock_compiler

        result = main(["compile-sip", "--sip", str(sip_dir)])

        assert result == 1
        assert "Failed to compile SIP" in caplog.text


class TestCLIMain:
    """Tests for CLI main entry point."""

    def test_no_command_shows_help(self, capsys):
        """Running with no command shows help."""
        result = main([])

        assert result == 0
        captured = capsys.readouterr()
        assert "usage:" in captured.out
        assert "harvest-pip" in captured.out

    def test_help_flag(self, capsys):
        """Running with --help shows help."""
        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])

        assert exc_info.value.code == 0

    def test_verbose_flag_accepted(self, capsys):
        """Verbose flag is accepted."""
        result = main(["-v", "harvest-pip"])

        assert result == 1  # Fails due to missing date, but -v was accepted
