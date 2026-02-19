"""ALTO filter for the Kanban pipeline.

Wraps ALTOTransformer to generate ALTO XML from PDFs in a SIP token.
"""

from .sip_transformer_filter import SIPTransformerFilter


class AltoFilter(SIPTransformerFilter):
    """Pipeline filter that wraps ALTOTransformer."""
