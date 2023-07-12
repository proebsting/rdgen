from typing import Tuple, Dict, Any
import tomllib

import scanner
from parse import Parser
from grammar import Spec, Production
import analysis


def process_grammar(input: str) -> Tuple[Spec, analysis.State, Dict[str, Any]]:
    lexer = scanner.Scanner(input)
    concatenated = "\n".join(lexer.pragmas)
    toml: Dict[str, Any] = tomllib.loads(concatenated)
    p = Parser(lexer)
    spec: Spec = p.parse()
    g: list[Production] = spec.productions

    state: analysis.State = analysis.analysis(g)

    return spec, state, toml