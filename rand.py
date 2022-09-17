import sys
import argparse

from grammar import Production, State, analyze
from parse_ebnf import Parser
import gen_random
import scanner


def main() -> None:
    args = parse_args()
    input = sys.stdin.read()
    lexer = scanner.Scanner(input)
    p = Parser(lexer)
    g: list[Production] = p.grammar()
    state = analyze(g)
    out = gen_random.gen(g[0].rhs, g, state, args.limit, args.substitutions)
    print(out)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("substitutions", nargs="*", help="substitutions from:to")
    parser.add_argument("--limit", type=int, help="limit on number of iterations")
    return parser.parse_args()


if __name__ == "__main__":
    main()
