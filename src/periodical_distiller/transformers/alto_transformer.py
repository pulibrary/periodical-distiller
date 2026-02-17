"""ALTO Transformer for generating ALTO XML from PDF articles.

Transforms SIPs containing PDF articles into SIPs with ALTO XML files using
PyMuPDF for word-level text extraction.
"""

import json
import logging
from collections import defaultdict
from pathlib import Path

import fitz  # PyMuPDF
from lxml import etree

from schemas.sip import SIPManifest

from .transformer import SIPTransformer

logger = logging.getLogger(__name__)

ALTO_NS = "http://www.loc.gov/standards/alto/ns-v2#"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"


class ALTOTransformer(SIPTransformer):
    """Transform PDF articles in a SIP to ALTO XML format.

    The ALTOTransformer:
    1. Loads the existing SIP manifest
    2. For each article with a pdf_path and pages:
       a. Opens the PDF with PyMuPDF
       b. For each page, extracts word-level text and bounding boxes
       c. Generates ALTO 2.1 XML with TextBlock/TextLine/String structure
       d. Writes the ALTO file to the path specified in page.alto_path
    3. Writes the updated SIP manifest
    """

    def transform(self, sip_path: Path) -> SIPManifest:
        """Transform PDF files in a SIP to ALTO XML.

        Args:
            sip_path: Path to the SIP directory containing PDF files

        Returns:
            SIPManifest with ALTO files written for each page
        """
        sip_manifest = self._load_sip_manifest(sip_path)
        logger.info(
            f"Transforming SIP {sip_manifest.id} with "
            f"{len(sip_manifest.articles)} articles to ALTO"
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
                logger.error(f"Failed to transform article {article.ceo_id} to ALTO: {e}")
                sip_manifest.validation_errors.append(
                    f"ALTO generation failed for {article.ceo_id}: {e}"
                )

        self._write_sip_manifest(sip_path, sip_manifest)
        logger.info(f"ALTO transformation complete for SIP {sip_manifest.id}")
        return sip_manifest

    def _load_sip_manifest(self, sip_path: Path) -> SIPManifest:
        """Load and validate the SIP manifest."""
        manifest_path = sip_path / "sip-manifest.json"
        data = json.loads(manifest_path.read_text())
        return SIPManifest.model_validate(data)

    def _transform_article(self, sip_path: Path, article) -> None:
        """Transform all pages of a single article from PDF to ALTO.

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

                pdf_page = doc[page_index]
                alto_tree = self._build_alto(pdf_page, page_info.page_number)

                alto_path = sip_path / page_info.alto_path
                alto_path.parent.mkdir(parents=True, exist_ok=True)
                alto_path.write_bytes(
                    etree.tostring(
                        alto_tree,
                        xml_declaration=True,
                        encoding="UTF-8",
                        pretty_print=True,
                    )
                )
                logger.debug(
                    f"Wrote ALTO for article {article.ceo_id} page {page_info.page_number}"
                )
        finally:
            doc.close()

    def _build_alto(self, page: fitz.Page, page_number: int) -> etree._Element:
        """Build an ALTO XML element tree for a single PDF page.

        Args:
            page: PyMuPDF page object
            page_number: 1-based page number

        Returns:
            Root lxml element of the ALTO document
        """
        rect = page.rect
        width = int(round(rect.width))
        height = int(round(rect.height))

        nsmap = {None: ALTO_NS, "xsi": XSI_NS}
        root = etree.Element(f"{{{ALTO_NS}}}alto", nsmap=nsmap)
        root.set(
            f"{{{XSI_NS}}}schemaLocation",
            f"{ALTO_NS} https://www.loc.gov/standards/alto/alto.xsd",
        )

        description = etree.SubElement(root, f"{{{ALTO_NS}}}Description")
        measurement = etree.SubElement(description, f"{{{ALTO_NS}}}MeasurementUnit")
        measurement.text = "pixel"

        layout = etree.SubElement(root, f"{{{ALTO_NS}}}Layout")
        page_el = etree.SubElement(layout, f"{{{ALTO_NS}}}Page")
        page_el.set("ID", f"page_{page_number}")
        page_el.set("PHYSICAL_IMG_NR", str(page_number))
        page_el.set("WIDTH", str(width))
        page_el.set("HEIGHT", str(height))

        print_space = etree.SubElement(page_el, f"{{{ALTO_NS}}}PrintSpace")
        print_space.set("HPOS", "0")
        print_space.set("VPOS", "0")
        print_space.set("WIDTH", str(width))
        print_space.set("HEIGHT", str(height))

        words = page.get_text("words")
        text_blocks = self._group_words(words)

        for block_index, (block_bbox, lines) in enumerate(text_blocks):
            block_el = self._build_text_block(
                block_bbox=block_bbox,
                lines=lines,
                page_number=page_number,
                block_index=block_index,
            )
            print_space.append(block_el)

        return root

    def _group_words(self, words: list) -> list:
        """Group words by block number and line number.

        Args:
            words: List of (x0, y0, x1, y1, word, block_no, line_no, word_no) tuples
                   as returned by PyMuPDF page.get_text('words')

        Returns:
            Ordered list of (block_bbox, lines) pairs where:
              - block_bbox is the (x0, y0, x1, y1) union of all words in the block
              - lines is a list of (line_no, word_list) pairs sorted by line_no,
                where word_list contains (x0, y0, x1, y1, word) tuples
        """
        blocks: dict = {}
        block_order: list = []

        for x0, y0, x1, y1, word, block_no, line_no, word_no in words:
            if block_no not in blocks:
                block_order.append(block_no)
                blocks[block_no] = defaultdict(list)
            blocks[block_no][line_no].append((x0, y0, x1, y1, word))

        result = []
        for block_no in block_order:
            lines = blocks[block_no]
            all_words = [w for line_words in lines.values() for w in line_words]
            block_bbox = self._union_bbox(all_words)
            sorted_lines = sorted(lines.items())
            result.append((block_bbox, sorted_lines))

        return result

    def _build_text_block(
        self,
        block_bbox: tuple,
        lines: list,
        page_number: int,
        block_index: int,
    ) -> etree._Element:
        """Build a TextBlock element with TextLine and String children.

        Args:
            block_bbox: (x0, y0, x1, y1) bounding box of the block
            lines: List of (line_no, word_list) pairs
            page_number: 1-based page number (used for unique IDs)
            block_index: 0-based block index within the page (used for unique IDs)

        Returns:
            TextBlock lxml element
        """
        x0, y0, x1, y1 = block_bbox
        block_el = etree.Element(f"{{{ALTO_NS}}}TextBlock")
        block_el.set("ID", f"block_{page_number}_{block_index}")
        block_el.set("HPOS", str(int(round(x0))))
        block_el.set("VPOS", str(int(round(y0))))
        block_el.set("WIDTH", str(int(round(x1 - x0))))
        block_el.set("HEIGHT", str(int(round(y1 - y0))))

        for line_idx, (_line_no, words) in enumerate(lines):
            line_bbox = self._union_bbox(words)
            lx0, ly0, lx1, ly1 = line_bbox

            line_el = etree.SubElement(block_el, f"{{{ALTO_NS}}}TextLine")
            line_el.set("ID", f"line_{page_number}_{block_index}_{line_idx}")
            line_el.set("HPOS", str(int(round(lx0))))
            line_el.set("VPOS", str(int(round(ly0))))
            line_el.set("WIDTH", str(int(round(lx1 - lx0))))
            line_el.set("HEIGHT", str(int(round(ly1 - ly0))))

            for word_idx, (wx0, wy0, wx1, wy1, word_text) in enumerate(words):
                string_el = etree.SubElement(line_el, f"{{{ALTO_NS}}}String")
                string_el.set("ID", f"str_{page_number}_{block_index}_{line_idx}_{word_idx}")
                string_el.set("HPOS", str(int(round(wx0))))
                string_el.set("VPOS", str(int(round(wy0))))
                string_el.set("WIDTH", str(int(round(wx1 - wx0))))
                string_el.set("HEIGHT", str(int(round(wy1 - wy0))))
                string_el.set("CONTENT", word_text)

        return block_el

    def _union_bbox(self, words: list) -> tuple:
        """Compute the union bounding box of a list of word tuples.

        Args:
            words: List of (x0, y0, x1, y1, ...) tuples

        Returns:
            (x0, y0, x1, y1) union bounding box
        """
        x0 = min(w[0] for w in words)
        y0 = min(w[1] for w in words)
        x1 = max(w[2] for w in words)
        y1 = max(w[3] for w in words)
        return x0, y0, x1, y1

    def _write_sip_manifest(self, sip_path: Path, manifest: SIPManifest) -> None:
        """Write the updated SIP manifest to disk."""
        manifest_path = sip_path / "sip-manifest.json"
        manifest_path.write_text(
            manifest.model_dump_json(indent=2, exclude_none=True)
        )
        logger.debug(f"Wrote updated SIP manifest to {manifest_path}")
