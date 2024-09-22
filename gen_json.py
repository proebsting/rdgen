import sys
import json
from typing import Any, TypeAlias, Union

from .grammar import (
    Alts,
    Rep,
    Opt,
    Sym,
    Production,
    Expr,
    Parens,
    Lambda,
    Cons,
    Spec,
    Break,
    Continue,
    OnePlus,
    Sequence,
    Value,
    Infinite,
)

from .analysis import State
from .read import process_grammar

JSON: TypeAlias = Union[str, list["JSON"], dict[str, "JSON"]]


class Emitter:
    def __init__(
        self,
        spec: Spec,
        state: State,
    ):
        self.spec: Spec = spec
        self.state: State = state

    def get_analysis(self, e: Expr) -> JSON:
        return {
            "nullable": str(e.nullable),
            "first": list(e.first),
            "follow": list(e.follow),
            "predict": list(e.predict),
        }

    def alts(self, x: Alts) -> JSON:
        retval: JSON = {
            "type": "alts",
            "vals": [self.expr(v) for v in x.vals],
        }
        return retval

    def sequence(self, x: Sequence) -> JSON:
        retval: JSON = {
            "type": "sequence",
            "seq": self.expr(x.seq),
        }
        return retval

    def rep(self, x: Rep) -> JSON:
        retval: JSON = {
            "type": "rep",
            "val": self.expr(x.val),
        }
        return retval

    def opt(self, x: Opt) -> JSON:
        retval: JSON = {
            "type": "opt",
            "val": self.expr(x.val),
        }
        return retval

    def sym(self, x: Sym) -> JSON:
        retval: JSON = {
            "type": "sym",
            "value": x.value,
        }
        return retval

    def parens(self, x: Parens) -> JSON:
        retval: JSON = {
            "type": "parens",
            "e": self.expr(x.e),
        }
        return retval

    def cons(self, x: Cons) -> JSON:
        retval: JSON = {
            "type": "cons",
            "car": self.expr(x.car),
            "cdr": self.expr(x.cdr),
        }
        return retval

    def lambda_(self, x: Lambda) -> JSON:
        retval: JSON = {
            "type": "lambda",
        }
        return retval

    def value(self, x: Value) -> JSON:
        retval: JSON = {
            "type": "value",
            "val": x.value,
        }
        return retval

    def _break(self, x: Break) -> JSON:
        retval: JSON = {
            "type": "break",
        }
        return retval

    def _continue(self, x: Continue) -> JSON:
        retval: JSON = {
            "type": "continue",
        }
        return retval

    def oneplus(self, x: OnePlus) -> JSON:
        retval: JSON = {
            "type": "oneplus",
            "val": self.expr(x.val),
        }
        return retval

    def infinite(self, x: Infinite) -> JSON:
        retval: JSON = {
            "type": "infinite",
            "val": self.expr(x.val),
        }
        return retval

    def expr(self, e: Expr) -> JSON:
        retval: JSON
        match e:
            case Alts():
                retval = self.alts(e)
            case Sequence():
                retval = self.sequence(e)
            case Rep():
                retval = self.rep(e)
            case Opt():
                retval = self.opt(e)
            case Sym():
                retval = self.sym(e)
            case Parens():
                retval = self.parens(e)
            case Cons():
                retval = self.cons(e)
            case Lambda():
                retval = self.lambda_(e)
            case Value():
                retval = self.value(e)
            case Break():
                retval = self._break(e)
            case Continue():
                retval = self._continue(e)
            case OnePlus():
                retval = self.oneplus(e)
            case Infinite():
                retval = self.infinite(e)
            case Expr():
                raise Exception(f"Expr not implemented {e}")
        assert isinstance(retval, dict)
        retval["analysis"] = self.get_analysis(e)
        retval["__str__"] = e.__repr__()
        return retval

    def prod(self, p: Production, state: State) -> JSON:
        retval: JSON = {
            "lhs": p.lhs,
            "rhs": self.expr(p.rhs),
            "analysis": self.get_analysis(p.rhs),
        }
        return retval

    def emit(self, state: State) -> JSON:
        retval: JSON = [self.prod(p, state) for p in self.spec.productions]
        return retval


def analysis(infile: str, outfile: str) -> None:
    input: str
    if infile:
        with open(infile, "r") as f:
            input = f.read()
    else:
        input = sys.stdin.read()
    spec: Spec
    state: State
    pragmas: dict[str, Any]
    spec, state, pragmas = process_grammar(input)

    emitter = Emitter(spec, state)
    analyzed: JSON = emitter.emit(state)
    retval: JSON = {
        "spec": analyzed,
        "pragmas": pragmas,
    }
    if outfile:
        with open(outfile, "w") as f:
            json.dump(retval, f, indent=4)
            f.write("\n")
    else:
        json.dump(retval, sys.stdout, indent=4)
        sys.stdout.write("\n")
