"""METS filter for the Kanban pipeline.

Wraps VeridianSIPCompiler to compile and seal a SIP token.
"""

from pathlib import Path

from periodical_distiller.compilers.veridian_sip_compiler import VeridianSIPCompiler
from periodical_distiller.pipeline.plumbing import Filter, Pipe, Token


class MetsFilter(Filter):
    """Pipeline filter that wraps VeridianSIPCompiler.

    Reads sip_path from the token, runs VeridianSIPCompiler, and writes
    mets_path, status, and any validation errors back to the token.

    Attributes:
        compiler: VeridianSIPCompiler instance
    """

    def __init__(self, pipe: Pipe, compiler: VeridianSIPCompiler):
        super().__init__(pipe)
        self.compiler = compiler

    def validate_token(self, token: Token) -> bool:
        return bool(token.get_prop("sip_path"))

    def process_token(self, token: Token) -> bool:
        sip_path_str = token.get_prop("sip_path")
        assert sip_path_str is not None
        manifest = self.compiler.compile(Path(sip_path_str))
        if manifest.mets_path:
            token.put_prop("mets_path", manifest.mets_path)
        token.put_prop("status", manifest.status)
        if manifest.validation_errors:
            token.put_prop("validation_errors", manifest.validation_errors)
        return True
