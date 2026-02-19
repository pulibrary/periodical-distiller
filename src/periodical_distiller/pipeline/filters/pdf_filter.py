"""PDF filter for the Kanban pipeline.

Wraps PDFTransformer to generate PDFs from HTML in a SIP token.
"""

from .sip_transformer_filter import SIPTransformerFilter


class PdfFilter(SIPTransformerFilter):
    """Pipeline filter that wraps PDFTransformer."""
