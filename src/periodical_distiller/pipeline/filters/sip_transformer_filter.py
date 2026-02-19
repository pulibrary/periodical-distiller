"""Base class for SIP-transformer pipeline filters.

Eliminates boilerplate shared by PdfFilter, AltoFilter, ModsFilter, and
ImageFilter: each wraps a SIPTransformer, validates the token has a
sip_path, runs the transformer, and propagates validation_errors.
"""

from pathlib import Path

from periodical_distiller.pipeline.plumbing import Filter, Pipe, Token
from periodical_distiller.transformers.transformer import SIPTransformer


class SIPTransformerFilter(Filter):
    """Pipeline filter base class for SIPTransformer wrappers.

    Subclasses only need to provide a class docstring and, optionally, a
    more specific type annotation for ``transformer`` in their own ``__init__``.

    Attributes:
        transformer: The SIPTransformer instance to invoke
    """

    def __init__(self, pipe: Pipe, transformer: SIPTransformer) -> None:
        super().__init__(pipe)
        self.transformer = transformer

    def validate_token(self, token: Token) -> bool:
        return bool(token.get_prop("sip_path"))

    def process_token(self, token: Token) -> bool:
        manifest = self.transformer.transform(Path(token.get_prop("sip_path")))
        if manifest.validation_errors:
            token.put_prop("validation_errors", manifest.validation_errors)
        return True
