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
    Seq0,
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
    # 1. whatever =<<code>> produces
    # 2. all @terms
    # 5. the value of the last term
    def sequence(self, x: Sequence, target: Optional[str]):
        assert x.name is None
        x.target = target
        if x.code is not None:
            target = None
        if x.code is None and isinstance(x.seq.cdr, Lambda):
            self.infer(x.seq.car, target)
        else:
            p: Seq0 = x.seq
            while isinstance(p, Cons):
                t = target if p.car.keep else None
                self.infer(p.car, t)
                p = p.cdr

    def cons(self, x: Cons, target: Optional[str]):
        assert x.name is None
        self.infer(x.car, None)
        self.infer(x.cdr, None)

    # IGNORE: The following is obsolete!!!!
    # in order, the value of a sequence is
    # 1. whatever =<<code>> produces
    # 2. the single @term
    # 3. a tuple of multiple @terms
    # 4. a dictionary of all the named terms
    # 5. the value of the singleton term
    # 6. None
    def create_assignment(self, x: Sequence, target: Optional[str]):
        """this has side effects!"""
        x.target = target
        if target is None:
            return
        if x.code is not None:
            return

        names: List[Expr] = [
            c.car for c in x.filter(lambda x: x.car.name is not None)
        ]
        keeps: List[Expr] = [c.car for c in x.filter(lambda x: x.car.keep)]

        cons = x.seq

        if len(keeps) > 0:
            if len(keeps) == 1:
                k = keeps[0]
                if not k.name:
                    assert not isinstance(k, Cons)
                    k.name = target
                x.at_term = k.name
            else:
                knames: List[str] = []
                for _, k in enumerate(keeps):
                    if not k.name:
                        assert not isinstance(k, Cons)
                        # k.name = f"_tmp{i}_{id(x)}"  # must fix
                        k.name = self.mk_tmp(x)
                    knames.append(k.name)
                x.tuple = knames
        if len(names) > 0:
            x.dict = [n.name for n in names if n.name is not None]
        if isinstance(cons.cdr, Lambda) and cons.name is None:
            assert not isinstance(cons.car, Cons)
            cons.car.name = target
            x.singleton = target

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
