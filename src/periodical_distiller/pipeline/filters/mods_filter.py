"""MODS filter for the Kanban pipeline.

Wraps MODSTransformer to generate MODS XML from CEO records in a SIP token.
"""

from .sip_transformer_filter import SIPTransformerFilter


class ModsFilter(SIPTransformerFilter):
    """Pipeline filter that wraps MODSTransformer."""
