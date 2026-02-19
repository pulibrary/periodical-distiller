"""Image Transformer for generating JPEG page images from PDF articles.

Transforms SIPs containing PDF articles into SIPs with JPEG image files using
PyMuPDF for page rasterization at 150 DPI.
"""

import json
import logging
from pathlib import Path

import fitz  # PyMuPDF

from schemas.sip import SIPArticle, SIPManifest

from .transformer import SIPTransformer

logger = logging.getLogger(__name__)


class ImageTransformer(SIPTransformer):
    """Transform PDF articles in a SIP to JPEG page images.

    The ImageTransformer:
    1. Loads the existing SIP manifest
    2. For each article with a pdf_path and pages:
       a. Opens the PDF with PyMuPDF
       b. For each page, rasterizes at the configured DPI to JPEG
       c. Writes the image to articles/{ceo_id}/{page:03d}.jpg
       d. Sets page_info.image_path in the manifest
    3. Writes the updated SIP manifest
    """

    def __init__(self, dpi: int = 150) -> None:
        """Initialize the image transformer.

        Args:
            dpi: Resolution for page rasterization (default: 150).
                 Use 300+ for archival-quality output.
        """
        self.dpi = dpi

    def transform(self, sip_path: Path) -> SIPManifest:
        """Transform PDF files in a SIP to JPEG page images.

        Args:
            sip_path: Path to the SIP directory containing PDF files

        Returns:
            SIPManifest with image_path set for each page
        """
        sip_manifest = self._load_sip_manifest(sip_path)
        logger.info(
            f"Transforming SIP {sip_manifest.id} with "
            f"{len(sip_manifest.articles)} articles to JPEG images"
        )

        for article in sip_manifest.articles:
            if not article.pdf_path:
                logger.warning(f"Article {article.ceo_id} has no PDF path, skipping")
                continue
            if not article.pages:
                logger.warning(f"Article {article.ceo_id} has no pages, skipping")
                continue

            try:
                self._transform_article(sip_path, article)
            except Exception as e:
                logger.error(
                    f"Failed to generate images for article {article.ceo_id}: {e}"
                )
                sip_manifest.validation_errors.append(
                    f"Image generation failed for {article.ceo_id}: {e}"
                )

        self._write_sip_manifest(sip_path, sip_manifest)
        logger.info(f"Image transformation complete for SIP {sip_manifest.id}")
        return sip_manifest

    def _load_sip_manifest(self, sip_path: Path) -> SIPManifest:
        """Load and validate the SIP manifest."""
        manifest_path = sip_path / "sip-manifest.json"
        data = json.loads(manifest_path.read_text())
        return SIPManifest.model_validate(data)

    def _transform_article(self, sip_path: Path, article: SIPArticle) -> None:
        """Rasterize all pages of a single article PDF to JPEG.

        Args:
            sip_path: Path to the SIP directory
            article: SIPArticle with pdf_path and pages
        """
        pdf_path = sip_path / article.pdf_path
        doc = fitz.open(str(pdf_path))

        try:
            for page_info in article.pages:
                page_index = page_info.page_number - 1
                if page_index >= len(doc):
                    logger.warning(
                        f"Page {page_info.page_number} out of range for {article.ceo_id}"
                    )
                    continue

                page = doc[page_index]
                scale = self.dpi / 72
                mat = fitz.Matrix(scale, scale)
                pix = page.get_pixmap(matrix=mat)

                img_rel = f"articles/{article.ceo_id}/{page_info.page_number:03d}.jpg"
                img_abs = sip_path / img_rel
                img_abs.parent.mkdir(parents=True, exist_ok=True)
                pix.save(str(img_abs))

                page_info.image_path = img_rel
                logger.debug(
                    f"Wrote image for article {article.ceo_id} "
                    f"page {page_info.page_number}"
                )
        finally:
            doc.close()

    def _write_sip_manifest(self, sip_path: Path, manifest: SIPManifest) -> None:
        """Write the updated SIP manifest to disk."""
        manifest_path = sip_path / "sip-manifest.json"
        manifest_path.write_text(
            manifest.model_dump_json(indent=2, exclude_none=True)
        )
        logger.debug(f"Wrote updated SIP manifest to {manifest_path}")
