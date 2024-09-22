import sys
from typing import Any, Dict

from . import infer
from .read import process_grammar
from . import gen_ir


def create(infile: str, outfile: str, verbose: bool, decorate: bool) -> None:
    if infile:
        with open(infile, "r") as f:
            input = f.read()
    else:
        input = sys.stdin.read()
    pragmas: Dict[str, Any]
    spec, state, pragmas = process_grammar(input)
    if decorate:
        inferer = infer.Inference(spec.productions, verbose)
        inferer.do_inference()
    from . import emit_ir_python

    ir_emitter = gen_ir.Emitter(spec, state, pragmas, verbose, decorate)
    generated = ir_emitter.emit_parser(state)
    if outfile:
        with open(outfile, "w") as f:
            py_emitter = emit_ir_python.Emitter(generated, f, verbose)
            py_emitter.emit_program()
    else:
        py_emitter = emit_ir_python.Emitter(generated, sys.stdout, verbose)
        py_emitter.emit_program()

    if verbose:
        spec.dump("# ")
