"""Base class for SIP compilers."""

from abc import ABC, abstractmethod
from pathlib import Path

from schemas.sip import SIPManifest


class Compiler(ABC):
    """Abstract base class for SIP compilers.

    Compilers assemble the final SIP package, producing METS documents and
    sealing the package for ingest.
    """

    @abstractmethod
    def compile(self, sip_path: Path) -> SIPManifest:
        """Compile a SIP package.

        Args:
            sip_path: Path to the SIP directory

        Returns:
            SIPManifest describing the compiled package
        """
        pass
