from typing import Tuple, Dict, Any, NoReturn
import tomllib

import scanner
from parse import Parser
from grammar import Spec, Production
import analysis


class ParseErrorException(Exception):
    msg: str
    token: scanner.Token
    expected: set[str]

    def __init__(self, msg: str, current: scanner.Token, expected: set[str]):
        self.msg = msg
        self.current = current
        self.expected = expected

    def __str__(self):
        return f"Parse error {self.msg} at {self.current}:  Expected {self.expected}"


def handler(current: scanner.Token, expected: set[str], msg: str) -> NoReturn:
    if not msg:
        msg = "syntax error"
    full: str = f"{msg} at {current}:  Expected {expected}"
    raise ParseErrorException(full, current, expected)


def process_grammar(input: str) -> Tuple[Spec, analysis.State, Dict[str, Any]]:
    lexer = scanner.Scanner(input)
    p = Parser(lexer.tokens, handler)
    spec: Spec = p.parse()

    concatenated = "\n".join(spec.pragmas)
    toml: Dict[str, Any] = tomllib.loads(concatenated)

    g: list[Production] = spec.productions

    state: analysis.State = analysis.analysis(g)

    return spec, state, toml
