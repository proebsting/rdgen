import sys
import json
import argparse
from types import ModuleType
import tomllib
from typing import Tuple, Dict, Any

from grammar import Spec, Production

import gen_random
import ascending

import scanner

# import emit
import infer
from parse import Parser

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


def create(args: argparse.Namespace) -> None:
    if args.input:
        with open(args.input, "r") as f:
            input = f.read()
    else:
        input = sys.stdin.read()
    pragmas: Dict[str, Any]
    spec, state, pragmas = process_grammar(input)
    inferer = infer.Inference(spec.productions, args.verbose)
    inferer.do_inference()
    # if args.output:
    #     with open(args.output, "w") as f:
    #         emitter = emit_python.Emitter(spec, state, f, args.verbose)
    #         emitter.emit_parser(state)
    # else:
    #     emitter = emit_python.Emitter(spec, state, sys.stdout, args.verbose)
    #     emitter.emit_parser(state)

    import gen_ir
    import emit_ir_python

    ir_emitter = gen_ir.Emitter(spec, state, pragmas, args.verbose)
    generated = ir_emitter.emit_parser(state)
    if args.output:
        with open(args.output, "w") as f:
            py_emitter = emit_ir_python.Emitter(generated, f, args.verbose)
            py_emitter.emit_program()
    else:
        py_emitter = emit_ir_python.Emitter(
            generated, sys.stdout, args.verbose
        )
        py_emitter.emit_program()

    if args.verbose:
        spec.dump()


def gen_examples(ns: ModuleType, args: argparse.Namespace) -> None:
    if args.input:
        with open(args.input, "r") as f:
            input = f.read()
    else:
        input = sys.stdin.read()
    g, state, _ = process_grammar(input)
    L = ns.gen_examples(g, state, args.quantity, args.limit)
    js = json.dumps(L, indent=2) + "\n"
    if args.output:
        with open(args.output, "w") as f:
            f.write(js)
    else:
        sys.stdout.write(js)


def examples(args: argparse.Namespace) -> None:
    gen_examples(gen_random, args)


def shortest(args: argparse.Namespace) -> None:
    gen_examples(ascending, args)


def main():
    args = parse_args()
    match args.command:
        case "create":
            try:
                create(args)
            except Exception as e:
                raise e
                print(f"Error: {e}")
        case "examples":
            examples(args)
        case "shortest":
            shortest(args)
        case _:
            raise NotImplementedError(args.command)


def parse_args():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create", help="create a parser")
    create.add_argument("--input", type=str, help="input file")
    create.add_argument("--output", type=str, help="output file")
    create.add_argument(
        "--verbose", action="store_true", help="verbose output"
    )

    examples = subparsers.add_parser(
        "examples", help="create a JSON file with example sentences"
    )
    examples.add_argument("--input", type=str, help="input file")
    examples.add_argument("--output", type=str, help="output file")
    examples.add_argument(
        "--quantity", type=int, default=1, help="quantity of output needed"
    )
    examples.add_argument(
        "--limit", type=int, default=100, help="limit on number of iterations"
    )

    shortest = subparsers.add_parser(
        "shortest",
        help="create a JSON file with example sentences, starting with the shortest",
    )
    shortest.add_argument("--input", type=str, help="input file")
    shortest.add_argument("--output", type=str, help="output file")
    shortest.add_argument(
        "--quantity", type=int, default=1, help="quantity of output needed"
    )
    shortest.add_argument(
        "--limit", type=int, default=100, help="limit length of sentences"
    )

    return parser.parse_args()


if __name__ == "__main__":
    main()
