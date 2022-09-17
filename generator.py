import sys

from grammar import Production, State, analyze
from parse_ebnf import Parser
import emit
import scanner


def main() -> None:
    input = sys.stdin.read()
    lexer = scanner.Scanner(input)
    p = Parser(lexer)
    g: list[Production] = p.grammar()
    state = analyze(g)
    emit.emit_parser(g, state)


if __name__ == "__main__":
    main()
