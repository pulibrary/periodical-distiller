"""HTML Transformer for converting CEO3 articles to styled HTML.

Transforms PIPs containing CEO3 article records into SIPs with rendered
HTML files, copied media, and updated SIP manifests.
"""

import json
import logging
import re
import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, Template

from schemas.ceo_item import CeoItem
from schemas.pip import PIPArticle, PIPManifest
from schemas.sip import SIPArticle, SIPManifest

from .filters import FILTERS
from .transformer import PIPTransformer

logger = logging.getLogger(__name__)

# Resolve the project root (4 levels up from this file):
#   html_transformer.py → transformers/ → periodical_distiller/ → src/ → project root
# If this file is ever moved, the chain of .parent calls must be updated.
PACKAGE_ROOT = Path(__file__).parent.parent.parent.parent
TEMPLATES_DIR = PACKAGE_ROOT / "resources" / "templates"
STYLESHEETS_DIR = PACKAGE_ROOT / "resources" / "stylesheets"


class HTMLTransformer(PIPTransformer):
    """Transform CEO3 articles from PIPs into styled HTML in SIPs.

    The HTMLTransformer:
    1. Loads the PIP manifest and article records
    2. Creates the SIP directory structure
    3. Copies the stylesheet and article media
    4. Replaces Flourish embeds with local chart images
    5. Renders each article through a Jinja2 template
    6. Writes the SIP manifest

    Attributes:
        template_name: Name of the Jinja2 template file
        stylesheet_name: Name of the CSS stylesheet file
    """

    def __init__(
        self,
        template_name: str = "article.html.j2",
        stylesheet_name: str = "article.css",
        templates_dir: Path | None = None,
        stylesheets_dir: Path | None = None,
    ):
        """Initialize the HTML transformer.

        Args:
            template_name: Name of the Jinja2 template file
            stylesheet_name: Name of the CSS stylesheet file
            templates_dir: Directory containing templates (default: resources/templates)
            stylesheets_dir: Directory containing stylesheets (default: resources/stylesheets)
        """
        self.template_name = template_name
        self.stylesheet_name = stylesheet_name
        self.templates_dir = templates_dir or TEMPLATES_DIR
        self.stylesheets_dir = stylesheets_dir or STYLESHEETS_DIR

        self._env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=True,
        )
        for name, func in FILTERS.items():
            self._env.filters[name] = func

    def transform(self, pip_path: Path, sip_path: Path) -> SIPManifest:
        """Transform PIP content into HTML files in a SIP.

        Args:
            pip_path: Path to the sealed PIP directory
            sip_path: Path to the SIP directory to create

        Returns:
            SIPManifest describing the transformed content
        """
        pip_manifest = self._load_pip_manifest(pip_path)
        logger.info(
            f"Transforming PIP {pip_manifest.id} with {len(pip_manifest.articles)} articles"
        )

        sip_manifest = SIPManifest(
            id=pip_manifest.id,
            pip_id=pip_manifest.id,
            pip_path=str(pip_path),
        )

        sip_path.mkdir(parents=True, exist_ok=True)
        articles_dir = sip_path / "articles"
        articles_dir.mkdir(exist_ok=True)

        self._copy_stylesheet(sip_path)

        template = self._env.get_template(self.template_name)

        for pip_article in pip_manifest.articles:
            try:
                sip_article = self._transform_article(
                    pip_path=pip_path,
                    pip_article=pip_article,
                    sip_path=sip_path,
                    template=template,
                )
                sip_manifest.articles.append(sip_article)
            except Exception as e:
                logger.error(f"Failed to transform article {pip_article.ceo_id}: {e}")
                sip_manifest.validation_errors.append(
                    f"Article {pip_article.ceo_id}: {e}"
                )

        sip_manifest.status = "sealed"
        self._write_sip_manifest(sip_path, sip_manifest)

        logger.info(f"Created SIP {sip_manifest.id} with {len(sip_manifest.articles)} articles")
        return sip_manifest

    def _load_pip_manifest(self, pip_path: Path) -> PIPManifest:
        """Load and validate the PIP manifest."""
        manifest_path = pip_path / "pip-manifest.json"
        data = json.loads(manifest_path.read_text())
        return PIPManifest.model_validate(data)

    def _copy_stylesheet(self, sip_path: Path) -> None:
        """Copy the stylesheet to the SIP directory."""
        src = self.stylesheets_dir / self.stylesheet_name
        dst = sip_path / self.stylesheet_name
        if src.exists():
            shutil.copy2(src, dst)
            logger.debug(f"Copied stylesheet to {dst}")

    def _transform_article(
        self,
        pip_path: Path,
        pip_article: PIPArticle,
        sip_path: Path,
        template: Template,
    ) -> SIPArticle:
        """Transform a single article from PIP to SIP.

        Args:
            pip_path: Path to the PIP directory
            pip_article: PIPArticle from the manifest
            sip_path: Path to the SIP directory
            template: Jinja2 template for rendering

        Returns:
            SIPArticle describing the transformed article
        """
        ceo_id = pip_article.ceo_id

        ceo_record_path = pip_path / pip_article.ceo_record_path
        ceo_data = json.loads(ceo_record_path.read_text())
        ceo_item = CeoItem.model_validate(ceo_data)

        article_dir = sip_path / "articles" / ceo_id
        article_dir.mkdir(parents=True, exist_ok=True)

        images_dir = article_dir / "images"
        charts_dir = article_dir / "charts"

        self._copy_article_media(
            pip_path, pip_article, article_dir, images_dir, charts_dir
        )

        content = self._replace_flourish_embeds(
            ceo_item.content or "",
            pip_article.media,
            ceo_id,
        )

        featured_image_path = self._find_featured_image_path(
            ceo_item, pip_article.media
        )

        stylesheet_path = f"../../{self.stylesheet_name}"
        html_content = template.render(
            item=ceo_item,
            stylesheet_path=stylesheet_path,
            content=content,
            featured_image_path=featured_image_path,
        )

        html_path = article_dir / "article.html"
        html_path.write_text(html_content)
        logger.debug(f"Wrote HTML for article {ceo_id}")

        return SIPArticle(
            ceo_id=ceo_id,
            html_path=f"articles/{ceo_id}/article.html",
        )

    def _copy_article_media(
        self,
        pip_path: Path,
        pip_article: PIPArticle,
        article_dir: Path,
        images_dir: Path,
        charts_dir: Path,
    ) -> None:
        """Copy media files from PIP to SIP article directory.

        Args:
            pip_path: Path to the PIP directory
            pip_article: PIPArticle with media list
            article_dir: SIP article directory
            images_dir: Target directory for images
            charts_dir: Target directory for charts
        """
        for media in pip_article.media:
            src_path = pip_path / media.local_path

            if not src_path.exists():
                logger.warning(f"Media file not found: {src_path}")
                continue

            if "/charts/" in media.local_path:
                charts_dir.mkdir(exist_ok=True)
                dst_path = charts_dir / src_path.name
            else:
                images_dir.mkdir(exist_ok=True)
                dst_path = images_dir / src_path.name

            shutil.copy2(src_path, dst_path)
            logger.debug(f"Copied media {src_path.name}")

    def _find_featured_image_path(
        self,
        ceo_item: CeoItem,
        media: list,
    ) -> str | None:
        """Find the local path for the dominant media image.

        Args:
            ceo_item: The CEO article item
            media: List of PIPMedia items for this article

        Returns:
            Relative path to the featured image, or None if not found
        """
        if not ceo_item.dominant_media:
            return None

        if ceo_item.dominant_media.type != "image":
            return None

        # Find the media item matching the dominant media
        # Match by base_name in the local_path (images directory)
        base_name = ceo_item.dominant_media.base_name
        for m in media:
            if "/images/" in m.local_path and base_name in m.local_path:
                # Return path relative to article directory
                filename = Path(m.local_path).name
                return f"images/{filename}"

        return None

    def _replace_flourish_embeds(
        self,
        content: str,
        media: list,
        ceo_id: str,
    ) -> str:
        """Replace Flourish embeds with local chart images.

        Finds Flourish embed divs and replaces them with img tags pointing
        to locally downloaded chart thumbnails.

        Args:
            content: HTML content with potential Flourish embeds
            media: List of PIPMedia items that may include chart images
            ceo_id: Article CEO ID for path construction

        Returns:
            Content with Flourish embeds replaced by img tags
        """
        if not content:
            return ""

        chart_map = {}
        for m in media:
            if "/charts/" in m.local_path:
                match = re.search(r"flourish-(\d+)", m.local_path)
                if match:
                    vis_id = match.group(1)
                    chart_map[vis_id] = m.local_path

        pattern = re.compile(
            r'<div\s+class="flourish-embed[^"]*"\s+data-src="visualisation/(\d+)"[^>]*>'
            r'.*?</div>',
            re.DOTALL | re.IGNORECASE,
        )

        def replace_embed(match):
            vis_id = match.group(1)
            if vis_id in chart_map:
                local_path = chart_map[vis_id]
                filename = Path(local_path).name
                return (
                    f'<div class="chart-image">'
                    f'<img src="charts/{filename}" alt="Chart visualization">'
                    f'</div>'
                )
            return ""

        content = pattern.sub(replace_embed, content)

        figure_pattern = re.compile(
            r'<figure>\s*<div\s+class="embed-code">\s*'
            r'(<div\s+class="chart-image">.*?</div>)\s*'
            r'</div>\s*</figure>',
            re.DOTALL,
        )
        content = figure_pattern.sub(r'\1', content)

        return content

    def _write_sip_manifest(self, sip_path: Path, manifest: SIPManifest) -> None:
        """Write the SIP manifest to disk."""
        manifest_path = sip_path / "sip-manifest.json"
        manifest_path.write_text(
            manifest.model_dump_json(indent=2, exclude_none=True)
        )
        logger.debug(f"Wrote SIP manifest to {manifest_path}")
