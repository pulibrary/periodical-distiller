"""PDF Transformer for converting HTML articles to PDF format.

Transforms SIPs containing HTML articles into SIPs with PDF files using WeasyPrint.
"""

import json
import logging
from pathlib import Path

import fitz  # PyMuPDF
from weasyprint import CSS, HTML

from schemas.sip import SIPManifest, SIPPage

from .transformer import SIPTransformer

logger = logging.getLogger(__name__)

# Resolve the project root (4 levels up from this file):
#   pdf_transformer.py → transformers/ → periodical_distiller/ → src/ → project root
# If this file is ever moved, the chain of .parent calls must be updated.
PACKAGE_ROOT = Path(__file__).parent.parent.parent.parent
STYLESHEETS_DIR = PACKAGE_ROOT / "resources" / "stylesheets"


class PDFTransformer(SIPTransformer):
    """Transform HTML articles in a SIP to PDF format.

    The PDFTransformer:
    1. Loads the existing SIP manifest
    2. Loads the stylesheet once
    3. For each article with an html_path:
       a. Renders HTML to PDF using WeasyPrint
       b. Counts pages using PyMuPDF
       c. Updates article.pdf_path and article.pages
    4. Writes the updated SIP manifest

    Attributes:
        base_url: Base URL for resolving relative paths in HTML (optional)
        stylesheet_name: Name of the CSS stylesheet file
    """

    def __init__(
        self,
        base_url: str | None = None,
        stylesheet_name: str = "article.css",
        stylesheets_dir: Path | None = None,
    ):
        """Initialize the PDF transformer.

        Args:
            base_url: Base URL for resolving relative paths (default: uses file:// URLs)
            stylesheet_name: Name of the CSS stylesheet file
            stylesheets_dir: Directory containing stylesheets (default: resources/stylesheets)
        """
        self.base_url = base_url
        self.stylesheet_name = stylesheet_name
        self.stylesheets_dir = stylesheets_dir or STYLESHEETS_DIR

    def transform(self, sip_path: Path) -> SIPManifest:
        """Transform HTML files in a SIP to PDF.

        Args:
            sip_path: Path to the SIP directory containing HTML files

        Returns:
            SIPManifest with updated pdf_path and pages for each article
        """
        sip_manifest = self._load_sip_manifest(sip_path)
        logger.info(
            f"Transforming SIP {sip_manifest.id} with {len(sip_manifest.articles)} articles to PDF"
        )

        css = self._load_stylesheet(sip_path)

        for article in sip_manifest.articles:
            if not article.html_path:
                logger.warning(f"Article {article.ceo_id} has no HTML path, skipping")
                continue

            try:
                self._transform_article(sip_path, article, css)
            except Exception as e:
                logger.error(f"Failed to transform article {article.ceo_id} to PDF: {e}")
                sip_manifest.validation_errors.append(
                    f"PDF generation failed for {article.ceo_id}: {e}"
                )

        self._write_sip_manifest(sip_path, sip_manifest)

        logger.info(
            f"PDF transformation complete for SIP {sip_manifest.id}"
        )
        return sip_manifest

    def _load_sip_manifest(self, sip_path: Path) -> SIPManifest:
        """Load and validate the SIP manifest."""
        manifest_path = sip_path / "sip-manifest.json"
        data = json.loads(manifest_path.read_text())
        return SIPManifest.model_validate(data)

    def _load_stylesheet(self, sip_path: Path) -> CSS | None:
        """Load the CSS stylesheet for PDF rendering.

        First tries to load from the SIP directory, then falls back to
        the resources directory.

        Args:
            sip_path: Path to the SIP directory

        Returns:
            WeasyPrint CSS object or None if not found
        """
        sip_css_path = sip_path / self.stylesheet_name
        if sip_css_path.exists():
            return CSS(filename=str(sip_css_path))

        resource_css_path = self.stylesheets_dir / self.stylesheet_name
        if resource_css_path.exists():
            return CSS(filename=str(resource_css_path))

        logger.warning(f"Stylesheet {self.stylesheet_name} not found")
        return None

    def _transform_article(self, sip_path: Path, article, css: CSS | None) -> None:
        """Transform a single article from HTML to PDF.

        Args:
            sip_path: Path to the SIP directory
            article: SIPArticle to transform
            css: WeasyPrint CSS object for styling
        """
        ceo_id = article.ceo_id
        article_dir = sip_path / "articles" / ceo_id
        html_path = sip_path / article.html_path
        pdf_path = article_dir / "article.pdf"

        base_url = self.base_url or article_dir.resolve().as_uri() + "/"

        html_doc = HTML(filename=str(html_path), base_url=base_url)

        stylesheets = [css] if css else None
        html_doc.write_pdf(str(pdf_path), stylesheets=stylesheets)

        logger.debug(f"Generated PDF for article {ceo_id}")

        page_count = self._count_pages(pdf_path)

        article.pdf_path = f"articles/{ceo_id}/article.pdf"
        article.pages = [
            SIPPage(
                page_number=i + 1,
                alto_path=f"articles/{ceo_id}/{i + 1:03d}.alto.xml",
            )
            for i in range(page_count)
        ]

        logger.debug(f"Article {ceo_id} has {page_count} pages")

    def _count_pages(self, pdf_path: Path) -> int:
        """Count the number of pages in a PDF file.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Number of pages in the PDF
        """
        doc = fitz.open(str(pdf_path))
        page_count = len(doc)
        doc.close()
        return page_count

    def _write_sip_manifest(self, sip_path: Path, manifest: SIPManifest) -> None:
        """Write the updated SIP manifest to disk."""
        manifest_path = sip_path / "sip-manifest.json"
        manifest_path.write_text(
            manifest.model_dump_json(indent=2, exclude_none=True)
        )
        logger.debug(f"Wrote updated SIP manifest to {manifest_path}")
