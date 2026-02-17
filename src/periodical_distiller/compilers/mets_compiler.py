"""METS Compiler for assembling METS XML documents from SIP and PIP manifests.

Builds a METS document conforming to the Veridian ingest specification,
modelled on Blue Mountain periodicals with adaptations for born-digital CEO3
content (per-article PDFs, no amdSec, JPEG images).
"""

import json
import logging
from pathlib import Path

from lxml import etree

from schemas.pip import PIPManifest
from schemas.sip import SIPArticle, SIPManifest, SIPPage

from .compiler import Compiler

logger = logging.getLogger(__name__)

METS_NS = "http://www.loc.gov/METS/"
MODS_NS = "http://www.loc.gov/mods/v3"
XLINK_NS = "http://www.w3.org/1999/xlink"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"


class METSCompiler(Compiler):
    """Compile METS XML documents from SIP and PIP manifests.

    The METSCompiler:
    1. Loads the SIP manifest and linked PIP manifest
    2. Builds a METS document with:
       - metsHdr: creator information
       - dmdSec: inline MODS with issue title and per-article relatedItems
       - fileSec: file groups for images (IMGGRP), ALTO (ALTOGRP),
                  PDF (PDFGRP), and MODS (MODSGRP)
       - structMap (PHYSICAL): one div per global page in issue order
       - structMap (LOGICAL): one div per article
    3. Writes mets.xml to the SIP root
    4. Updates sip_manifest.mets_path and rewrites the manifest
    """

    def compile(self, sip_path: Path) -> SIPManifest:
        """Compile METS XML for a SIP.

        Args:
            sip_path: Path to the SIP directory

        Returns:
            SIPManifest with mets_path set
        """
        sip_manifest = self._load_sip_manifest(sip_path)
        logger.info(f"Compiling METS for SIP {sip_manifest.id}")

        pip_manifest = self._load_pip_manifest(sip_manifest)
        mets_root = self._build_mets(sip_path, sip_manifest, pip_manifest)

        mets_path = sip_path / "mets.xml"
        mets_path.write_bytes(
            etree.tostring(
                mets_root,
                xml_declaration=True,
                encoding="UTF-8",
                pretty_print=True,
            )
        )
        logger.info(f"Wrote METS to {mets_path}")

        sip_manifest.mets_path = "mets.xml"
        self._write_sip_manifest(sip_path, sip_manifest)
        return sip_manifest

    def _load_sip_manifest(self, sip_path: Path) -> SIPManifest:
        """Load and validate the SIP manifest."""
        manifest_path = sip_path / "sip-manifest.json"
        data = json.loads(manifest_path.read_text())
        return SIPManifest.model_validate(data)

    def _load_pip_manifest(self, sip_manifest: SIPManifest) -> PIPManifest:
        """Load the linked PIP manifest.

        Args:
            sip_manifest: SIP manifest with pip_path set

        Returns:
            PIPManifest from the linked PIP

        Raises:
            ValueError: If pip_path is not set
        """
        if not sip_manifest.pip_path:
            raise ValueError("SIP manifest has no pip_path; cannot load PIP")

        pip_path = Path(sip_manifest.pip_path)
        pip_manifest_path = pip_path / "pip-manifest.json"
        data = json.loads(pip_manifest_path.read_text())
        return PIPManifest.model_validate(data)

    def _write_sip_manifest(self, sip_path: Path, manifest: SIPManifest) -> None:
        """Write the updated SIP manifest to disk."""
        manifest_path = sip_path / "sip-manifest.json"
        manifest_path.write_text(
            manifest.model_dump_json(indent=2, exclude_none=True)
        )
        logger.debug(f"Wrote updated SIP manifest to {manifest_path}")

    def _build_mets(
        self,
        sip_path: Path,
        sip_manifest: SIPManifest,
        pip_manifest: PIPManifest,
    ) -> etree._Element:
        """Build the METS root element with all sections."""
        issue_id = sip_manifest.id

        nsmap = {
            None: METS_NS,
            "xsi": XSI_NS,
            "xlink": XLINK_NS,
            "mods": MODS_NS,
        }
        root = etree.Element(f"{{{METS_NS}}}mets", nsmap=nsmap)
        root.set(
            f"{{{XSI_NS}}}schemaLocation",
            (
                f"{METS_NS} http://www.loc.gov/standards/mets/mets.xsd "
                f"{MODS_NS} http://www.loc.gov/standards/mods/v3/mods-3-8.xsd"
            ),
        )
        root.set("TYPE", "Newspaper")
        root.set("OBJID", f"urn:PUL:periodicals:daily-princetonian:{issue_id}")

        root.append(self._build_mets_hdr(issue_id))
        root.append(self._build_dmd_sec(sip_path, sip_manifest, pip_manifest))
        root.append(self._build_file_sec(sip_manifest))
        root.append(self._build_physical_struct_map(sip_manifest))
        root.append(self._build_logical_struct_map(sip_manifest, pip_manifest))

        return root

    def _build_mets_hdr(self, issue_id: str) -> etree._Element:
        """Build the metsHdr element."""
        hdr = etree.Element(f"{{{METS_NS}}}metsHdr")

        agent = etree.SubElement(hdr, f"{{{METS_NS}}}agent")
        agent.set("ROLE", "CREATOR")
        agent.set("TYPE", "ORGANIZATION")
        name = etree.SubElement(agent, f"{{{METS_NS}}}name")
        name.text = "Princeton University Library, Digital Initiatives"

        doc_id = etree.SubElement(hdr, f"{{{METS_NS}}}metsDocumentID")
        doc_id.set("TYPE", "URN")
        doc_id.text = f"urn:PUL:daily-princetonian:mets:{issue_id}"

        return hdr

    def _build_dmd_sec(
        self,
        sip_path: Path,
        sip_manifest: SIPManifest,
        pip_manifest: PIPManifest,
    ) -> etree._Element:
        """Build the dmdSec with inline MODS for issue and article constituents."""
        dmd = etree.Element(f"{{{METS_NS}}}dmdSec")
        dmd.set("ID", "dmd1")

        md_wrap = etree.SubElement(dmd, f"{{{METS_NS}}}mdWrap")
        md_wrap.set("MDTYPE", "MODS")

        xml_data = etree.SubElement(md_wrap, f"{{{METS_NS}}}xmlData")

        mods_root = etree.SubElement(xml_data, f"{{{MODS_NS}}}mods")
        mods_root.set("version", "3.8")

        # Issue title
        title_info = etree.SubElement(mods_root, f"{{{MODS_NS}}}titleInfo")
        title_el = etree.SubElement(title_info, f"{{{MODS_NS}}}title")
        title_el.text = pip_manifest.title

        # Issue date
        origin_info = etree.SubElement(mods_root, f"{{{MODS_NS}}}originInfo")
        date_issued = etree.SubElement(origin_info, f"{{{MODS_NS}}}dateIssued")
        date_issued.set("encoding", "iso8601")
        date_issued.text = pip_manifest.date_range[0]

        # Per-article relatedItems
        for n, article in enumerate(sip_manifest.articles, start=1):
            article_data = self._extract_article_mods(sip_path, article)

            related = etree.SubElement(mods_root, f"{{{MODS_NS}}}relatedItem")
            related.set("type", "constituent")
            related.set("ID", f"c{n:04d}")

            rel_title_info = etree.SubElement(related, f"{{{MODS_NS}}}titleInfo")
            rel_title = etree.SubElement(rel_title_info, f"{{{MODS_NS}}}title")
            rel_title.text = article_data.get("title", f"Article {article.ceo_id}")

            for author in article_data.get("authors", []):
                name_el = etree.SubElement(related, f"{{{MODS_NS}}}name")
                name_el.set("type", "personal")
                name_part = etree.SubElement(name_el, f"{{{MODS_NS}}}namePart")
                name_part.text = author

            type_el = etree.SubElement(related, f"{{{MODS_NS}}}typeOfResource")
            type_el.text = "text"

            if article.pages:
                page_numbers = sorted(p.page_number for p in article.pages)
                part = etree.SubElement(related, f"{{{MODS_NS}}}part")
                extent = etree.SubElement(part, f"{{{MODS_NS}}}extent")
                extent.set("unit", "page")
                start_el = etree.SubElement(extent, f"{{{MODS_NS}}}start")
                start_el.text = str(page_numbers[0])
                if len(page_numbers) > 1:
                    end_el = etree.SubElement(extent, f"{{{MODS_NS}}}end")
                    end_el.text = str(page_numbers[-1])

        return dmd

    def _build_file_sec(self, sip_manifest: SIPManifest) -> etree._Element:
        """Build the fileSec with IMGGRP, ALTOGRP, PDFGRP, and MODSGRP."""
        file_sec = etree.Element(f"{{{METS_NS}}}fileSec")
        global_pages = self._global_pages(sip_manifest)

        # IMGGRP — only emit if at least one page has an image
        has_images = any(page.image_path for _, page, _ in global_pages)
        if has_images:
            img_grp = etree.SubElement(file_sec, f"{{{METS_NS}}}fileGrp")
            img_grp.set("ID", "IMGGRP")
            img_grp.set("USE", "Images")
            for article, page, global_n in global_pages:
                if not page.image_path:
                    continue
                file_el = etree.SubElement(img_grp, f"{{{METS_NS}}}file")
                file_el.set("ID", f"IMG_{article.ceo_id}_{page.page_number:03d}")
                file_el.set("GROUPID", f"pg{global_n}")
                file_el.set("MIMETYPE", "image/jpeg")
                flocat = etree.SubElement(file_el, f"{{{METS_NS}}}FLocat")
                flocat.set("LOCTYPE", "URL")
                flocat.set(f"{{{XLINK_NS}}}href", f"file://./{page.image_path}")

        # ALTOGRP
        alto_grp = etree.SubElement(file_sec, f"{{{METS_NS}}}fileGrp")
        alto_grp.set("ID", "ALTOGRP")
        alto_grp.set("USE", "OCR")
        for article, page, global_n in global_pages:
            if not page.alto_path:
                continue
            file_el = etree.SubElement(alto_grp, f"{{{METS_NS}}}file")
            file_el.set("ID", f"ALTO_{article.ceo_id}_{page.page_number:03d}")
            file_el.set("GROUPID", f"pg{global_n}")
            file_el.set("MIMETYPE", "text/xml")
            flocat = etree.SubElement(file_el, f"{{{METS_NS}}}FLocat")
            flocat.set("LOCTYPE", "URL")
            flocat.set(f"{{{XLINK_NS}}}href", f"file://./{page.alto_path}")

        # PDFGRP
        pdf_grp = etree.SubElement(file_sec, f"{{{METS_NS}}}fileGrp")
        pdf_grp.set("ID", "PDFGRP")
        pdf_grp.set("USE", "PDF")
        for article in sip_manifest.articles:
            if not article.pdf_path:
                continue
            file_el = etree.SubElement(pdf_grp, f"{{{METS_NS}}}file")
            file_el.set("ID", f"PDF_{article.ceo_id}")
            file_el.set("MIMETYPE", "application/pdf")
            flocat = etree.SubElement(file_el, f"{{{METS_NS}}}FLocat")
            flocat.set("LOCTYPE", "URL")
            flocat.set(f"{{{XLINK_NS}}}href", f"file://./{article.pdf_path}")

        # MODSGRP
        mods_grp = etree.SubElement(file_sec, f"{{{METS_NS}}}fileGrp")
        mods_grp.set("ID", "MODSGRP")
        mods_grp.set("USE", "MODS")
        for article in sip_manifest.articles:
            if not article.mods_path:
                continue
            file_el = etree.SubElement(mods_grp, f"{{{METS_NS}}}file")
            file_el.set("ID", f"MODS_{article.ceo_id}")
            file_el.set("MIMETYPE", "text/xml")
            flocat = etree.SubElement(file_el, f"{{{METS_NS}}}FLocat")
            flocat.set("LOCTYPE", "URL")
            flocat.set(f"{{{XLINK_NS}}}href", f"file://./{article.mods_path}")

        return file_sec

    def _build_physical_struct_map(self, sip_manifest: SIPManifest) -> etree._Element:
        """Build the physical structMap — one div per global page."""
        struct_map = etree.Element(f"{{{METS_NS}}}structMap")
        struct_map.set("LABEL", "Physical Structure")
        struct_map.set("TYPE", "PHYSICAL")

        root_div = etree.SubElement(struct_map, f"{{{METS_NS}}}div")
        root_div.set("TYPE", "Newspaper")
        root_div.set("DMDID", "dmd1")

        for article, page, global_n in self._global_pages(sip_manifest):
            page_div = etree.SubElement(root_div, f"{{{METS_NS}}}div")
            page_div.set("ID", f"DIVP{global_n}")
            page_div.set("ORDER", str(global_n))
            page_div.set("ORDERLABEL", str(global_n))
            page_div.set("TYPE", "INSIDE")

            fptr = etree.SubElement(page_div, f"{{{METS_NS}}}fptr")
            par = etree.SubElement(fptr, f"{{{METS_NS}}}par")

            if page.image_path:
                img_area = etree.SubElement(par, f"{{{METS_NS}}}area")
                img_area.set("FILEID", f"IMG_{article.ceo_id}_{page.page_number:03d}")

            if page.alto_path:
                alto_area = etree.SubElement(par, f"{{{METS_NS}}}area")
                alto_area.set("FILEID", f"ALTO_{article.ceo_id}_{page.page_number:03d}")
                alto_area.set("BETYPE", "IDREF")
                alto_area.set("BEGIN", f"page_{page.page_number}")

        return struct_map

    def _build_logical_struct_map(
        self,
        sip_manifest: SIPManifest,
        pip_manifest: PIPManifest,
    ) -> etree._Element:
        """Build the logical structMap — one div per article."""
        struct_map = etree.Element(f"{{{METS_NS}}}structMap")
        struct_map.set("LABEL", "Logical Structure")
        struct_map.set("TYPE", "LOGICAL")

        newspaper_div = etree.SubElement(struct_map, f"{{{METS_NS}}}div")
        newspaper_div.set("TYPE", "Newspaper")
        newspaper_div.set("LABEL", pip_manifest.title)

        issue_div = etree.SubElement(newspaper_div, f"{{{METS_NS}}}div")
        issue_div.set("TYPE", "Issue")
        issue_div.set("LABEL", pip_manifest.date_range[0])
        issue_div.set("DMDID", "dmd1")

        contents_div = etree.SubElement(issue_div, f"{{{METS_NS}}}div")
        contents_div.set("TYPE", "EditorialContent")
        contents_div.set("LABEL", "Contents")

        for n, article in enumerate(sip_manifest.articles, start=1):
            article_div = etree.SubElement(contents_div, f"{{{METS_NS}}}div")
            article_div.set("TYPE", "Article")
            article_div.set("DMDID", f"c{n:04d}")
            article_div.set("ORDER", str(n))
            if article.pdf_path:
                fptr = etree.SubElement(article_div, f"{{{METS_NS}}}fptr")
                fptr.set("FILEID", f"PDF_{article.ceo_id}")

        return struct_map

    def _extract_article_mods(self, sip_path: Path, article: SIPArticle) -> dict:
        """Extract title and authors from a per-article MODS file.

        Args:
            sip_path: Path to the SIP directory
            article: SIPArticle with optional mods_path

        Returns:
            Dict with "title" (str) and "authors" (list[str])
        """
        if not article.mods_path:
            return {"title": f"Article {article.ceo_id}", "authors": []}

        try:
            mods_abs = sip_path / article.mods_path
            tree = etree.parse(str(mods_abs))
            root = tree.getroot()

            title_el = root.find(f"{{{MODS_NS}}}titleInfo/{{{MODS_NS}}}title")
            title = (
                title_el.text
                if title_el is not None and title_el.text
                else f"Article {article.ceo_id}"
            )

            authors = []
            for name_el in root.findall(f"{{{MODS_NS}}}name"):
                name_part = name_el.find(f"{{{MODS_NS}}}namePart")
                if name_part is not None and name_part.text:
                    authors.append(name_part.text)

            return {"title": title, "authors": authors}

        except Exception as e:
            logger.warning(f"Could not parse MODS for article {article.ceo_id}: {e}")
            return {"title": f"Article {article.ceo_id}", "authors": []}

    def _global_pages(
        self, sip_manifest: SIPManifest
    ) -> list[tuple[SIPArticle, SIPPage, int]]:
        """Generate globally-numbered pages across all articles.

        Iterates articles in manifest order, pages in page_number order,
        assigning a sequential global counter starting at 1.

        Returns:
            List of (article, page, global_n) tuples
        """
        result = []
        global_n = 0
        for article in sip_manifest.articles:
            sorted_pages = sorted(article.pages, key=lambda p: p.page_number)
            for page in sorted_pages:
                global_n += 1
                result.append((article, page, global_n))
        return result
