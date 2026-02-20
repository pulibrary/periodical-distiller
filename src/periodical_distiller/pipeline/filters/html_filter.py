"""HTML filter for the Kanban pipeline.

Wraps HTMLTransformer to create a SIP from a PIP token.
"""

from pathlib import Path

from periodical_distiller.pipeline.plumbing import Filter, Pipe, Token
from periodical_distiller.transformers.html_transformer import HTMLTransformer


class HtmlFilter(Filter):
    """Pipeline filter that wraps HTMLTransformer.

    Reads pip_path from the token, creates a SIP directory under sip_base,
    runs HTMLTransformer, and writes sip_path and article_ids back to the token.

    Attributes:
        transformer: HTMLTransformer instance
        sip_base: Base directory for SIP output
    """

    def __init__(self, pipe: Pipe, transformer: HTMLTransformer, sip_base: Path):
        super().__init__(pipe)
        self.transformer = transformer
        self.sip_base = sip_base

    def validate_token(self, token: Token) -> bool:
        return bool(token.get_prop("pip_path"))

    def process_token(self, token: Token) -> bool:
        pip_path_str = token.get_prop("pip_path")
        assert pip_path_str is not None
        pip_path = Path(pip_path_str)
        token_name = token.name
        assert token_name is not None
        sip_path = self.sip_base / token_name
        sip_path.mkdir(parents=True, exist_ok=True)
        manifest = self.transformer.transform(pip_path, sip_path)
        token.put_prop("sip_path", str(sip_path))
        token.put_prop("article_ids", [a.ceo_id for a in manifest.articles])
        if manifest.validation_errors:
            token.put_prop("validation_errors", manifest.validation_errors)
        return True
