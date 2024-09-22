from types import ModuleType
import sys
import json


from .read import process_grammar


def gen_examples(
    ns: ModuleType, input: str, outfile: str, quantity: int, limit: int
) -> None:
    if input:
        with open(input, "r") as f:
            input = f.read()
    else:
        input = sys.stdin.read()
    g, state, _ = process_grammar(input)
    L = ns.gen_examples(g, state, quantity, limit)
    js = json.dumps(L, indent=2) + "\n"
    if outfile:
        with open(outfile, "w") as f:
            f.write(js)
    else:
        sys.stdout.write(js)
