import argparse

import gen_random
import ascending
from create import create
from sentences import gen_examples


def main():
    args = parse_args()
    match args.command:
        case "create":
            create(args.input, args.output, args.verbose, args.decorate)
        case "examples":
            gen_examples(
                ascending, args.input, args.output, args.quantity, args.limit
            )
        case "shortest":
            gen_examples(
                gen_random, args.input, args.output, args.quantity, args.limit
            )
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
    create.add_argument("--decorate", action="store_true", help="decorate")

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
