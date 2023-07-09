from typing import Optional, List, Set

from grammar import (
    Alts,
    Rep,
    Opt,
    Sym,
    Production,
    Expr,
    Parens,
    Lambda,
    Cons,
    Break,
    Continue,
    OnePlus,
    Sequence,
    Value,
)


class Inference:
    def __init__(
        self,
        grammar: List[Production],
        verbose: bool,
    ):
        self.grammar: List[Production] = grammar
        self.verbose: bool = verbose
        self.nonterms: Set[str] = set(p.lhs for p in grammar)

    def mk_tmp(self, x: Expr) -> str:
        return f"_tmp_{id(x)}"

    def alts(self, x: Alts, target: Optional[str]):
        assert x.name is None
        for v in x.vals:
            self.infer(v, target)

    # in order, the value of a sequence is
    # 2. all =terms
    # 5. the value of the last term
    def sequence(self, x: Sequence, target: Optional[str]):
        assert x.name is None
        if isinstance(x.seq.cdr, Lambda):
            x.seq.car.keep0 = True
        self.infer(x.seq, target)

    def cons(self, x: Cons, target: Optional[str]):
        assert x.name is None
        tgt = target if x.car.keep or x.car.keep0 else None
        self.infer(x.car, tgt)
        self.infer(x.cdr, target)

    def rep(self, x: Rep, target: Optional[str]):
        x.target = target
        if not x.simple:
            # x.element = f"_tmp_{x.name}_{id(x)}"
            x.element = f"{x.name}_element_"
            self.infer(x.val, x.element)
        else:
            self.infer(x.val, None)

    def oneplus(self, x: OnePlus, target: Optional[str]):
        if x.name:
            x.target = target
        else:
            x.name = target

        if x.name and not x.simple:
            x.element = f"_tmp_{x.name}_{id(x)}"
            self.infer(x.val, x.element)
        else:
            self.infer(x.val, x.name)

    def opt(self, x: Opt, target: Optional[str]):
        x.target = target
        self.infer(x.val, x.name or target)

    def sym(self, x: Sym, target: Optional[str]):
        if not x.name and not target and (x.value in self.nonterms):
            x.name = x.value
        x.target = target

    def parens(self, x: Parens, target: Optional[str]):
        x.target = target
        self.infer(x.e, x.name or target)

    def _break(self, x: Break, target: Optional[str]):
        pass

    def _continue(self, x: Continue, target: Optional[str]):
        pass

    def prod(self, p: Production):
        var = f"_{p.lhs}_"
        self.infer(p.rhs, var)

    def infer(self, e: Expr, target: Optional[str]):
        if isinstance(e, Alts):
            self.alts(e, target)
        elif isinstance(e, Cons):
            self.cons(e, target)
        elif isinstance(e, Rep):
            self.rep(e, target)
        elif isinstance(e, Opt):
            self.opt(e, target)
        elif isinstance(e, Sym):
            self.sym(e, target)
        elif isinstance(e, Parens):
            self.parens(e, target)
        elif isinstance(e, Lambda):
            pass
        elif isinstance(e, Value):
            e.target = target
        elif isinstance(e, Break):
            self._break(e, target)
        elif isinstance(e, OnePlus):
            self.oneplus(e, target)
        elif isinstance(e, Continue):
            self._continue(e, target)
        elif isinstance(e, Sequence):
            self.sequence(e, target)
        else:
            raise Exception(f"unknown expr: {e}")

    def do_inference(self):
        for p in self.grammar:
            self.prod(p)
