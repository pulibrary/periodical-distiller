"""PDF filter for the Kanban pipeline.

Wraps PDFTransformer to generate PDFs from HTML in a SIP token.
"""

from pathlib import Path

from periodical_distiller.pipeline.plumbing import Filter, Pipe, Token
from periodical_distiller.transformers.pdf_transformer import PDFTransformer


class PdfFilter(Filter):
    """Pipeline filter that wraps PDFTransformer.

    Reads sip_path from the token, runs PDFTransformer, and writes any
    validation errors back to the token.

    Attributes:
        transformer: PDFTransformer instance
    """

    def __init__(self, pipe: Pipe, transformer: PDFTransformer):
        super().__init__(pipe)
        self.transformer = transformer

    def validate_token(self, token: Token) -> bool:
        return bool(token.get_prop("sip_path"))

    def process_token(self, token: Token) -> bool:
        manifest = self.transformer.transform(Path(token.get_prop("sip_path")))
        if manifest.validation_errors:
            token.put_prop("validation_errors", manifest.validation_errors)
        return True
