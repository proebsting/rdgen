from typing import Tuple, Dict, Any
import tomllib

from . import scanner
from .parse import Parser
from .grammar import Spec, Production
from . import analysis


def process_grammar(input: str) -> Tuple[Spec, analysis.State, Dict[str, Any]]:
    lexer = scanner.Scanner(input)
    p = Parser(lexer.tokens)
    spec: Spec = p.parse()

    concatenated = "\n".join(spec.pragmas)
    toml: Dict[str, Any] = tomllib.loads(concatenated)

    g: list[Production] = spec.productions

    state: analysis.State = analysis.analysis(g)

    return spec, state, toml
