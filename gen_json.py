import sys
import json
from typing import Any, TypedDict, Literal, NotRequired

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


class ExprDict(TypedDict):
    analysis: NotRequired["AnalysisDict"]
    _str_: NotRequired[str]


class AltDict(ExprDict):
    type: Literal["alts"]
    vals: list[ExprDict]


class SeqDict(ExprDict):
    type: Literal["sequence"]
    seq: ExprDict


class RepDict(ExprDict):
    type: Literal["rep"]
    val: ExprDict


class OptDict(ExprDict):
    type: Literal["opt"]
    val: ExprDict


class SymDict(ExprDict):
    type: Literal["sym"]
    value: str


class ParensDict(ExprDict):
    type: Literal["parens"]
    e: ExprDict


class ConsDict(ExprDict):
    type: Literal["cons"]
    car: ExprDict
    cdr: ExprDict


class LambdaDict(ExprDict):
    type: Literal["lambda"]


class ValueDict(ExprDict):
    type: Literal["value"]
    val: str


class BreakDict(ExprDict):
    type: Literal["break"]


class ContinueDict(ExprDict):
    type: Literal["continue"]


class OnePlusDict(ExprDict):
    type: Literal["oneplus"]
    val: ExprDict


class InfiniteDict(ExprDict):
    type: Literal["infinite"]
    val: ExprDict


class AnalysisDict(TypedDict):
    nullable: str
    first: list[str]
    follow: list[str]
    predict: list[str]


class ProdDict(TypedDict):
    lhs: str
    rhs: ExprDict
    analysis: AnalysisDict


class TotalDict(TypedDict):
    spec: list[ProdDict]
    pragmas: dict[str, Any]
    terminals: list[str]
    nonterminals: list[str]
    start: str


class Emitter:
    def __init__(
        self,
        spec: Spec,
        state: State,
    ):
        self.spec: Spec = spec
        self.state: State = state

    def get_analysis(self, e: Expr) -> AnalysisDict:
        return {
            "nullable": str(e.nullable),
            "first": list(e.first),
            "follow": list(e.follow),
            "predict": list(e.predict),
        }

    def alts(self, x: Alts) -> AltDict:
        retval: AltDict = {
            "type": "alts",
            "vals": [self.expr(v) for v in x.vals],
        }
        return retval

    def sequence(self, x: Sequence) -> SeqDict:
        retval: SeqDict = {
            "type": "sequence",
            "seq": self.expr(x.seq),
        }
        return retval

    def rep(self, x: Rep) -> RepDict:
        retval: RepDict = {
            "type": "rep",
            "val": self.expr(x.val),
        }
        return retval

    def opt(self, x: Opt) -> OptDict:
        retval: OptDict = {
            "type": "opt",
            "val": self.expr(x.val),
        }
        return retval

    def sym(self, x: Sym) -> SymDict:
        retval: SymDict = {
            "type": "sym",
            "value": x.value,
        }
        return retval

    def parens(self, x: Parens) -> ParensDict:
        retval: ParensDict = {
            "type": "parens",
            "e": self.expr(x.e),
        }
        return retval

    def cons(self, x: Cons) -> ConsDict:
        retval: ConsDict = {
            "type": "cons",
            "car": self.expr(x.car),
            "cdr": self.expr(x.cdr),
        }
        return retval

    def lambda_(self, x: Lambda) -> LambdaDict:
        retval: LambdaDict = {
            "type": "lambda",
        }
        return retval

    def value(self, x: Value) -> ValueDict:
        retval: ValueDict = {
            "type": "value",
            "val": x.value,
        }
        return retval

    def _break(self, x: Break) -> BreakDict:
        retval: BreakDict = {
            "type": "break",
        }
        return retval

    def _continue(self, x: Continue) -> ContinueDict:
        retval: ContinueDict = {
            "type": "continue",
        }
        return retval

    def oneplus(self, x: OnePlus) -> OnePlusDict:
        retval: OnePlusDict = {
            "type": "oneplus",
            "val": self.expr(x.val),
        }
        return retval

    def infinite(self, x: Infinite) -> InfiniteDict:
        retval: InfiniteDict = {
            "type": "infinite",
            "val": self.expr(x.val),
        }
        return retval

    def expr(self, e: Expr) -> ExprDict:
        retval: ExprDict
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
        retval["_str_"] = e.__repr__()
        return retval

    def prod(self, p: Production, state: State) -> ProdDict:
        retval: ProdDict = {
            "lhs": p.lhs,
            "rhs": self.expr(p.rhs),
            "analysis": self.get_analysis(p.rhs),
        }
        return retval

    def emit(self, state: State) -> list[ProdDict]:
        retval: list[ProdDict] = [self.prod(p, state) for p in self.spec.productions]
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
    analyzed: list[ProdDict] = emitter.emit(state)
    retval: TotalDict = {
        "spec": analyzed,
        "pragmas": pragmas,
        "terminals": sorted(list(state.terms)),
        "nonterminals": sorted(list(state.nonterms)),
        "start": spec.productions[0].lhs,
    }
    if outfile:
        with open(outfile, "w") as f:
            json.dump(retval, f, indent=4)
            f.write("\n")
    else:
        json.dump(retval, sys.stdout, indent=4)
        sys.stdout.write("\n")
