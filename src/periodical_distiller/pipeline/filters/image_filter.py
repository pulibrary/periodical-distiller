"""Image filter for the Kanban pipeline.

Wraps ImageTransformer to generate JPEG page images from PDFs in a SIP token.
"""

from pathlib import Path

from periodical_distiller.pipeline.plumbing import Filter, Pipe, Token
from periodical_distiller.transformers.image_transformer import ImageTransformer


class ImageFilter(Filter):
    """Pipeline filter that wraps ImageTransformer.

    Reads sip_path from the token, runs ImageTransformer, and writes any
    validation errors back to the token.

    Attributes:
        transformer: ImageTransformer instance
    """

    def __init__(self, pipe: Pipe, transformer: ImageTransformer):
        super().__init__(pipe)
        self.transformer = transformer

    def validate_token(self, token: Token) -> bool:
        return bool(token.get_prop("sip_path"))

    def process_token(self, token: Token) -> bool:
        manifest = self.transformer.transform(Path(token.get_prop("sip_path")))
        if manifest.validation_errors:
            token.put_prop("validation_errors", manifest.validation_errors)
        return True
