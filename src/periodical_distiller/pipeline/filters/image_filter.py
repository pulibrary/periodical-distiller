"""Image filter for the Kanban pipeline.

Wraps ImageTransformer to generate JPEG page images from PDFs in a SIP token.
"""

from .sip_transformer_filter import SIPTransformerFilter


class ImageFilter(SIPTransformerFilter):
    """Pipeline filter that wraps ImageTransformer."""
