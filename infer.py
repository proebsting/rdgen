from typing import Optional, List, Set

from grammar import (
    Target,
    Alts,
    Opt,
    Sym,
    Production,
    Expr,
    Parens,
    Lambda,
    Cons,
    Break,
    Continue,
    Sequence,
    Value,
    Loop,
)

import ir


class Inference:
    def __init__(
        self,
        grammar: List[Production],
        verbose: bool,
    ):
        self.grammar: List[Production] = grammar
        self.verbose: bool = verbose
        self.nonterms: Set[str] = set(p.lhs for p in grammar)

    def destination(
        self, x: Expr, target: Optional[Target]
    ) -> Optional[Target]:
        if x.keep or x.keep0:
            if target:
                return target
        if x.name:
            return Target(x.name, [])
        return None

    def alts(self, x: Alts, target: Optional[Target]):
        assert x.name is None
        for v in x.vals:
            self.infer(v, target)

    # in order, the value of a sequence is
    # 2. all =terms
    # 5. the value of the last term
    def sequence(self, x: Sequence, target: Optional[Target]):
        assert x.name is None
        if isinstance(x.seq, Cons) and isinstance(x.seq.cdr, Lambda):
            x.seq.car.keep0 = True
        self.infer(x.seq, target)

    def cons(self, x: Cons, target: Optional[Target]):
        assert x.name is None
        self.infer(x.car, target)
        self.infer(x.cdr, target)

    def loop(self, x: Loop, target: Optional[Target]):
        dst = self.destination(x, target)
        x.target = dst
        if not x.simple and dst:
            x.element = f"{dst.name}_element_"
            t = Target(x.element, [ir.AppendToList(dst.name, x.element)])
            self.infer(x.val, t)
        else:
            self.infer(x.val, None)

    def opt(self, x: Opt, target: Optional[Target]):
        dst = self.destination(x, target)
        x.target = dst
        self.infer(x.val, dst)

    def sym(self, x: Sym, target: Optional[Target]):
        if (
            not x.name
            and (not x.keep and not x.keep0)
            and (x.value in self.nonterms)
        ):
            x.name = x.value
        x.target = self.destination(x, target)

    def value(self, x: Value, target: Optional[Target]):
        x.target = self.destination(x, target)

    def parens(self, x: Parens, target: Optional[Target]):
        dst = self.destination(x, target)
        x.target = dst
        self.infer(x.e, dst)

    def _break(self, x: Break, target: Optional[Target]):
        pass

    def _continue(self, x: Continue, target: Optional[Target]):
        pass

    def prod(self, p: Production):
        var = f"_{p.lhs}_"
        t = Target(var, [])
        self.infer(p.rhs, t)

    def infer(self, e: Expr, target: Optional[Target]):
        if isinstance(e, Alts):
            self.alts(e, target)
        elif isinstance(e, Cons):
            self.cons(e, target)
        elif isinstance(e, Loop):
            self.loop(e, target)
        elif isinstance(e, Opt):
            self.opt(e, target)
        elif isinstance(e, Sym):
            self.sym(e, target)
        elif isinstance(e, Parens):
            self.parens(e, target)
        elif isinstance(e, Lambda):
            pass
        elif isinstance(e, Value):
            self.value(e, target)
        elif isinstance(e, Break):
            self._break(e, target)
        elif isinstance(e, Continue):
            self._continue(e, target)
        elif isinstance(e, Sequence):
            self.sequence(e, target)
        else:
            raise Exception(f"unknown expr: {e}")

    def do_inference(self):
        for p in self.grammar:
            self.prod(p)
