"""Pipeline orchestrator for end-to-end PIP → SIP processing.

Wires all filters together and runs a single PIP through the full pipeline.
"""

import json
import logging
from pathlib import Path

from periodical_distiller.compilers.veridian_sip_compiler import VeridianSIPCompiler
from periodical_distiller.pipeline.filters.alto_filter import AltoFilter
from periodical_distiller.pipeline.filters.html_filter import HtmlFilter
from periodical_distiller.pipeline.filters.image_filter import ImageFilter
from periodical_distiller.pipeline.filters.mets_filter import MetsFilter
from periodical_distiller.pipeline.filters.mods_filter import ModsFilter
from periodical_distiller.pipeline.filters.pdf_filter import PdfFilter
from periodical_distiller.pipeline.plumbing import Pipeline, Token, dump_token, load_token
from periodical_distiller.transformers.alto_transformer import ALTOTransformer
from periodical_distiller.transformers.html_transformer import HTMLTransformer
from periodical_distiller.transformers.image_transformer import ImageTransformer
from periodical_distiller.transformers.mods_transformer import MODSTransformer
from periodical_distiller.transformers.pdf_transformer import PDFTransformer
from schemas.pip import PIPManifest

logger = logging.getLogger(__name__)

BUCKET_NAMES = [
    "pip_harvested",
    "html_transform",
    "pdf_transform",
    "alto_transform",
    "mods_transform",
    "image_transform",
    "mets_compile",
    "sip_complete",
]


class Orchestrator:
    """End-to-end pipeline orchestrator.

    Creates the bucket directory structure, instantiates all filters, and
    runs a single PIP through the complete transformation pipeline.

    Attributes:
        workspace: Root directory for pipeline bucket directories
        sip_output: Base directory where SIPs are written
        pipeline: Pipeline instance managing all buckets
        filters: Ordered list of Filter instances to run
    """

    def __init__(self, workspace: Path, sip_output: Path):
        self.workspace = workspace
        self.sip_output = sip_output

        self.pipeline = Pipeline()
        for name in BUCKET_NAMES:
            bucket_path = workspace / name
            bucket_path.mkdir(parents=True, exist_ok=True)
            self.pipeline.add_bucket(name, bucket_path)

        self.filters = [
            HtmlFilter(
                pipe=self.pipeline.pipe("pip_harvested", "html_transform"),
                transformer=HTMLTransformer(),
                sip_base=sip_output,
            ),
            PdfFilter(
                pipe=self.pipeline.pipe("html_transform", "pdf_transform"),
                transformer=PDFTransformer(),
            ),
            AltoFilter(
                pipe=self.pipeline.pipe("pdf_transform", "alto_transform"),
                transformer=ALTOTransformer(),
            ),
            ModsFilter(
                pipe=self.pipeline.pipe("alto_transform", "mods_transform"),
                transformer=MODSTransformer(),
            ),
            ImageFilter(
                pipe=self.pipeline.pipe("mods_transform", "image_transform"),
                transformer=ImageTransformer(),
            ),
            MetsFilter(
                pipe=self.pipeline.pipe("image_transform", "sip_complete"),
                compiler=VeridianSIPCompiler(),
            ),
        ]

    def run(self, pip_path: Path) -> Token:
        """Run a single PIP through the full pipeline.

        Loads the PIP manifest, seeds a token into pip_harvested, runs each
        filter in order, and returns the final token from sip_complete (or
        from the last errored bucket if processing failed).

        Args:
            pip_path: Path to the sealed PIP directory

        Returns:
            The processed token with final state
        """
        pip_manifest = self._load_pip_manifest(pip_path)
        token = self._seed_token(pip_manifest, pip_path)

        for f in self.filters:
            processed = f.run_once()
            if not processed:
                logger.warning(
                    f"Filter {f.__class__.__name__} did not process token {token.name}"
                )
                break

        return self._find_token(pip_manifest.id)

    def _load_pip_manifest(self, pip_path: Path) -> PIPManifest:
        """Load and validate the PIP manifest."""
        manifest_path = pip_path / "pip-manifest.json"
        data = json.loads(manifest_path.read_text())
        return PIPManifest.model_validate(data)

    def _seed_token(self, pip_manifest: PIPManifest, pip_path: Path) -> Token:
        """Create a token from the PIP manifest and write it to pip_harvested."""
        content = {
            "id": pip_manifest.id,
            "date_range": list(pip_manifest.date_range),
            "title": pip_manifest.title,
            "article_ids": [a.ceo_id for a in pip_manifest.articles],
            "pip_path": str(pip_path),
        }
        token = Token(content)
        token_path = self.pipeline.bucket("pip_harvested") / f"{pip_manifest.id}.json"
        dump_token(token, token_path)
        logger.info(f"Seeded token {pip_manifest.id} to pip_harvested")
        return token

    def _find_token(self, issue_id: str) -> Token:
        """Find the token in any bucket (sip_complete first, then error states)."""
        sip_complete = self.pipeline.bucket("sip_complete")
        token_path = sip_complete / f"{issue_id}.json"
        if token_path.exists():
            return load_token(token_path)

        for name in reversed(BUCKET_NAMES):
            bucket = self.pipeline.bucket(name)
            err_path = bucket / f"{issue_id}.err"
            if err_path.exists():
                return load_token(err_path)
            json_path = bucket / f"{issue_id}.json"
            if json_path.exists():
                return load_token(json_path)

        raise FileNotFoundError(f"Token {issue_id} not found in any pipeline bucket")
