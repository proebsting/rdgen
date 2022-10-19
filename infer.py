from collections import Counter
from typing import TextIO, NamedTuple, Optional, List, Dict, Set, Tuple
from sys import stderr

from grammar import (
    Alts,
    Seq,
    Rep,
    Opt,
    Sym,
    Production,
    State,
    Expr,
    Parens,
    Lambda,
    Cons,
)


class Inference:
    def __init__(
        self,
        grammar: list[Production],
        verbose: bool,
    ):
        self.grammar = grammar
        self.verbose = verbose

    def alts(self, x: Alts, target: Optional[str]):
        assert x.name is None
        for i, v in enumerate(x.vals):
            self.infer(v, target)

    def cons(self, x: Cons, target: Optional[str]):
        assert x.name is None
        self.create_assignment(x, target)
        self.infer(x.car, None)
        self.infer(x.cdr, None)

    # in order, the value of a sequence is
    # 1. whatever =<<code>> produces
    # 2. the single @term
    # 3. a tuple of multiple @terms
    # 4. a dictionary of all the named terms
    # 5. the value of the singleton term
    # 6. None
    def create_assignment(self, x: Cons, target):
        """this has side effects!"""
        x.target = target
        if target is None:
            return
        if x.code is not None:
            return

        names = [c.car for c in x.filter(lambda x: x.car.name is not None)]
        keeps: List[Expr] = [c.car for c in x.filter(lambda x: x.car.keep)]

        if len(keeps) > 0:
            if len(keeps) == 1:
                k = keeps[0]
                if not k.name:
                    assert not isinstance(k, Cons)
                    k.name = target
                x.at_term = k.name
            else:
                knames: List[str] = []
                for i, k in enumerate(keeps):
                    if not k.name:
                        assert not isinstance(k, Cons)
                        k.name = f"_tmp{i}_{id(x)}"  # must fix
                    knames.append(k.name)
                x.tuple = knames
        if len(names) > 0:
            x.dict = [n.name for n in names]
        if isinstance(x.cdr, Lambda) and x.cdr.name is None:
            assert not isinstance(x.car, Cons)
            x.car.name = target
            x.singleton = target

    def rep(self, x: Rep, target: Optional[str]):
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
        if x.name:
            x.target = target
        else:
            x.name = target
        self.infer(x.val, x.name)

    def sym(self, x: Sym, target: Optional[str]):
        if x.name:
            x.target = target
        else:
            x.name = target

    def parens(self, x: Parens, target: Optional[str]):
        if x.name:
            x.target = target
        else:
            x.name = target
        self.infer(x.e, x.name)

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
        else:
            raise Exception(f"unknown expr: {e}")

    def do_inference(self):
        for p in self.grammar:
            self.prod(p)
