"""MODS Transformer for generating MODS XML from CEO3 article records.

Transforms SIPs by reading CEO3 source records from the linked PIP and
generating MODS 3.8 XML files, one per article.
"""

import html
import json
import logging
import re
from pathlib import Path

from lxml import etree

from schemas.ceo_item import CeoItem
from schemas.pip import PIPArticle, PIPManifest
from schemas.sip import SIPManifest

from .transformer import SIPTransformer

logger = logging.getLogger(__name__)

MODS_NS = "http://www.loc.gov/mods/v3"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"


class MODSTransformer(SIPTransformer):
    """Transform CEO3 articles in a SIP to MODS 3.8 XML.

    The MODSTransformer:
    1. Loads the existing SIP manifest
    2. Reads the linked PIP manifest to locate CEO3 source records
    3. For each article, loads the CEO record and builds a MODS document
    4. Writes article.mods.xml to the article directory
    5. Updates article.mods_path in the SIP manifest and rewrites it
    """

    def transform(self, sip_path: Path) -> SIPManifest:
        """Transform CEO3 articles in a SIP to MODS 3.8 XML.

        Args:
            sip_path: Path to the SIP directory

        Returns:
            SIPManifest with mods_path set for each article
        """
        sip_manifest = self._load_sip_manifest(sip_path)
        logger.info(
            f"Transforming SIP {sip_manifest.id} with "
            f"{len(sip_manifest.articles)} articles to MODS"
        )

        try:
            pip_articles = self._load_pip_article_map(sip_manifest)
            assert sip_manifest.pip_path is not None
            pip_path = Path(sip_manifest.pip_path)
        except Exception as e:
            logger.error(f"Failed to load PIP for SIP {sip_manifest.id}: {e}")
            for article in sip_manifest.articles:
                sip_manifest.validation_errors.append(
                    f"MODS generation failed for {article.ceo_id}: {e}"
                )
            self._write_sip_manifest(sip_path, sip_manifest)
            return sip_manifest

        for article in sip_manifest.articles:
            try:
                self._transform_article(sip_path, article, pip_articles, pip_path)
            except Exception as e:
                logger.error(f"Failed to transform article {article.ceo_id} to MODS: {e}")
                sip_manifest.validation_errors.append(
                    f"MODS generation failed for {article.ceo_id}: {e}"
                )

        self._write_sip_manifest(sip_path, sip_manifest)
        logger.info(f"MODS transformation complete for SIP {sip_manifest.id}")
        return sip_manifest

    def _load_sip_manifest(self, sip_path: Path) -> SIPManifest:
        """Load and validate the SIP manifest."""
        manifest_path = sip_path / "sip-manifest.json"
        data = json.loads(manifest_path.read_text())
        return SIPManifest.model_validate(data)

    def _load_pip_article_map(self, sip_manifest: SIPManifest) -> dict[str, PIPArticle]:
        """Load the PIP manifest and return a map of ceo_id → PIPArticle.

        Args:
            sip_manifest: SIP manifest with pip_path set

        Returns:
            Dict mapping ceo_id strings to PIPArticle objects

        Raises:
            ValueError: If pip_path is not set on the manifest
        """
        if not sip_manifest.pip_path:
            raise ValueError("SIP manifest has no pip_path; cannot locate CEO records")

        pip_path = Path(sip_manifest.pip_path)
        pip_manifest_path = pip_path / "pip-manifest.json"
        pip_data = json.loads(pip_manifest_path.read_text())
        pip_manifest = PIPManifest.model_validate(pip_data)

        return {article.ceo_id: article for article in pip_manifest.articles}

    def _transform_article(
        self,
        sip_path: Path,
        article,
        pip_articles: dict[str, PIPArticle],
        pip_path: Path,
    ) -> None:
        """Generate a MODS XML file for a single article.

        Args:
            sip_path: Path to the SIP directory
            article: SIPArticle to transform
            pip_articles: Map of ceo_id → PIPArticle from the linked PIP
            pip_path: Path to the PIP directory
        """
        ceo_id = article.ceo_id

        if ceo_id not in pip_articles:
            raise ValueError(f"Article {ceo_id} not found in PIP article map")

        pip_article = pip_articles[ceo_id]
        ceo_record_path = pip_path / pip_article.ceo_record_path
        ceo_data = json.loads(ceo_record_path.read_text())
        ceo_item = CeoItem.model_validate(ceo_data)

        mods_element = self._build_mods(ceo_item)

        mods_rel_path = f"articles/{ceo_id}/article.mods.xml"
        mods_abs_path = sip_path / mods_rel_path
        mods_abs_path.parent.mkdir(parents=True, exist_ok=True)
        mods_abs_path.write_bytes(
            etree.tostring(
                mods_element,
                xml_declaration=True,
                encoding="UTF-8",
                pretty_print=True,
            )
        )
        article.mods_path = mods_rel_path
        logger.debug(f"Wrote MODS for article {ceo_id}")

    def _build_mods(self, ceo_item: CeoItem) -> etree._Element:
        """Build a MODS 3.8 XML element tree from a CEO3 article record.

        Args:
            ceo_item: Validated CEO3 content item

        Returns:
            Root <mods:mods> lxml element
        """
        nsmap = {"mods": MODS_NS, "xsi": XSI_NS}
        root = etree.Element(f"{{{MODS_NS}}}mods", nsmap=nsmap)
        root.set("version", "3.8")
        root.set(
            f"{{{XSI_NS}}}schemaLocation",
            f"{MODS_NS} http://www.loc.gov/standards/mods/v3/mods-3-8.xsd",
        )

        # titleInfo
        title_info = etree.SubElement(root, f"{{{MODS_NS}}}titleInfo")
        title_el = etree.SubElement(title_info, f"{{{MODS_NS}}}title")
        title_el.text = ceo_item.headline
        if ceo_item.subhead:
            subtitle_el = etree.SubElement(title_info, f"{{{MODS_NS}}}subTitle")
            subtitle_el.text = ceo_item.subhead

        # name (authors)
        for author in ceo_item.authors:
            name_el = etree.SubElement(root, f"{{{MODS_NS}}}name")
            name_el.set("type", "personal")
            name_part = etree.SubElement(name_el, f"{{{MODS_NS}}}namePart")
            name_part.text = author.name
            role_el = etree.SubElement(name_el, f"{{{MODS_NS}}}role")
            role_term = etree.SubElement(role_el, f"{{{MODS_NS}}}roleTerm")
            role_term.set("type", "text")
            role_term.text = "author"

        # typeOfResource
        type_el = etree.SubElement(root, f"{{{MODS_NS}}}typeOfResource")
        type_el.text = "text"

        # originInfo
        origin_el = etree.SubElement(root, f"{{{MODS_NS}}}originInfo")
        date_el = etree.SubElement(origin_el, f"{{{MODS_NS}}}dateIssued")
        date_el.set("encoding", "iso8601")
        date_el.text = ceo_item.published_at.split(" ")[0]

        # identifiers
        ceo_id_el = etree.SubElement(root, f"{{{MODS_NS}}}identifier")
        ceo_id_el.set("type", "ceo-id")
        ceo_id_el.text = ceo_item.ceo_id

        uuid_el = etree.SubElement(root, f"{{{MODS_NS}}}identifier")
        uuid_el.set("type", "uuid")
        uuid_el.text = ceo_item.uuid

        # abstract (HTML stripped, omitted if None)
        if ceo_item.abstract:
            abstract_el = etree.SubElement(root, f"{{{MODS_NS}}}abstract")
            abstract_el.text = self._strip_html(ceo_item.abstract)

        # subjects (tags)
        for tag in ceo_item.tags:
            subject_el = etree.SubElement(root, f"{{{MODS_NS}}}subject")
            topic_el = etree.SubElement(subject_el, f"{{{MODS_NS}}}topic")
            topic_el.text = tag.name

        return root

    def _strip_html(self, text: str) -> str:
        """Strip HTML tags and unescape HTML entities.

        Args:
            text: String possibly containing HTML markup

        Returns:
            Plain text with tags removed and entities decoded
        """
        stripped = re.sub(r"<[^>]+>", "", text)
        return html.unescape(stripped)

    def _write_sip_manifest(self, sip_path: Path, manifest: SIPManifest) -> None:
        """Write the updated SIP manifest to disk."""
        manifest_path = sip_path / "sip-manifest.json"
        manifest_path.write_text(
            manifest.model_dump_json(indent=2, exclude_none=True)
        )
        logger.debug(f"Wrote updated SIP manifest to {manifest_path}")
