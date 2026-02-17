"""Veridian SIP Compiler for assembling Veridian-compliant SIP packages.

Thin orchestrator that delegates METS generation to METSCompiler and
seals the SIP manifest for Veridian ingest.
"""

import json
import logging
from pathlib import Path

from schemas.sip import SIPManifest

from .compiler import Compiler
from .mets_compiler import METSCompiler

logger = logging.getLogger(__name__)


class VeridianSIPCompiler(Compiler):
    """Compile a Veridian-compliant SIP package.

    Orchestrates:
    1. METSCompiler builds mets.xml and updates sip_manifest.mets_path
    2. SIP manifest status is set to "sealed"
    """

    def __init__(self, mets_compiler: METSCompiler | None = None):
        self._mets = mets_compiler or METSCompiler()

    def compile(self, sip_path: Path) -> SIPManifest:
        """Compile and seal a Veridian SIP.

        Args:
            sip_path: Path to the SIP directory

        Returns:
            Sealed SIPManifest with mets_path set and status "sealed"
        """
        logger.info(f"Compiling Veridian SIP at {sip_path}")
        manifest = self._mets.compile(sip_path)
        manifest.status = "sealed"
        self._write_sip_manifest(sip_path, manifest)
        logger.info(f"SIP {manifest.id} sealed with METS at {manifest.mets_path}")
        return manifest

    def _write_sip_manifest(self, sip_path: Path, manifest: SIPManifest) -> None:
        """Write the sealed SIP manifest to disk."""
        manifest_path = sip_path / "sip-manifest.json"
        manifest_path.write_text(
            manifest.model_dump_json(indent=2, exclude_none=True)
        )
        logger.debug(f"Wrote sealed SIP manifest to {manifest_path}")
