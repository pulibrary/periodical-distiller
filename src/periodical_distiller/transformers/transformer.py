"""Base class for transformers.

Transformers convert content from PIPs into derivatives stored in SIPs.
Each transformer type produces a specific output format (HTML, PDF, ALTO, etc.).
"""

from abc import ABC, abstractmethod
from pathlib import Path

from schemas.sip import SIPManifest


class Transformer(ABC):
    """Abstract base class for all transformers.

    Transformers read sealed PIPs and produce derivatives in SIPs.
    Each transformer is responsible for one type of output.
    """

    @abstractmethod
    def transform(self, pip_path: Path, sip_path: Path) -> SIPManifest:
        """Transform PIP content into SIP derivatives.

        Args:
            pip_path: Path to the sealed PIP directory
            sip_path: Path to the SIP directory to create/update

        Returns:
            SIPManifest describing the transformed content
        """
        pass
