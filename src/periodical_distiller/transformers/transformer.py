"""Base classes for transformers.

Transformers convert content between pipeline stages. There are two types:

- PIPTransformer: Creates a new SIP from PIP content (e.g., HTMLTransformer)
- SIPTransformer: Enriches an existing SIP with derivatives (e.g., PDFTransformer)
"""

from abc import ABC, abstractmethod
from pathlib import Path

from schemas.sip import SIPManifest


class PIPTransformer(ABC):
    """Abstract base class for PIP-to-SIP transformers.

    PIPTransformers read sealed PIPs and produce new SIPs.
    They are typically the first transformer in a pipeline.
    """

    @abstractmethod
    def transform(self, pip_path: Path, sip_path: Path) -> SIPManifest:
        """Transform PIP content into a new SIP.

        Args:
            pip_path: Path to the sealed PIP directory
            sip_path: Path to the SIP directory to create

        Returns:
            SIPManifest describing the transformed content
        """
        pass


class SIPTransformer(ABC):
    """Abstract base class for SIP-to-SIP transformers.

    SIPTransformers enrich existing SIPs with additional derivatives.
    They operate on SIPs that already contain some content (e.g., HTML).
    """

    @abstractmethod
    def transform(self, sip_path: Path) -> SIPManifest:
        """Enrich a SIP with additional derivatives.

        Args:
            sip_path: Path to the existing SIP directory

        Returns:
            SIPManifest with updated derivative paths
        """
        pass


# Backwards compatibility alias
Transformer = PIPTransformer
