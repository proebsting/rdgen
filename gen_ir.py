from typing import List, Optional, Dict, Any

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
    Seq0,
    Value,
    Infinite,
    Loop,
)

from . import ir

from .analysis import State


def append(L: List[ir.Stmt], x: Optional[ir.Stmt]) -> None:
    if x and not isinstance(x, ir.Empty):
        L.append(x)


class Emitter:
    def __init__(
        self,
        spec: Spec,
        state: State,
        pragmas: Dict[str, Any],
        verbose: bool,
        decorate: bool,
    ):
        self.spec: Spec = spec
        self.state: State = state
        self.pragmas: Dict[str, Any] = pragmas
        self.verbose: bool = verbose
        self.decorate: bool = decorate

    def alts(self, x: Alts) -> List[ir.Stmt]:
        guardeds: List[ir.Guarded] = []
        for v in x.vals:
            guard: ir.Guard = ir.Guard(v.predict)
            body: List[ir.Stmt] = self.sequence(v)
            guardeds.append(ir.Guarded(guard, body))

        if_ = ir.SelectAlternative(guardeds, ir.ParseError("syntax error"))
        return [if_]

    def cons0(
        self, x: Seq0, decls: List[ir.Decl], stmts: List[ir.Stmt]
    ) -> None:
        while isinstance(x, Cons):
            car: List[ir.Stmt] = self.expr(x.car)
            if x.car.name:
                decls.append(ir.Decl(x.car.name))
            stmts.extend(car)
            x = x.cdr
        assert isinstance(x, Lambda)

    def sequence(
        self, x: Sequence, tmps: Optional[List[str]] = None
    ) -> List[ir.Stmt]:
        decls: List[ir.Decl] = [ir.Decl(t) for t in tmps] if tmps else []
        stmts: List[ir.Stmt] = []
        self.cons0(x.seq, decls, stmts)
        seq = ir.Sequence(decls, stmts)
        return [seq]

    def value(self, x: Value) -> List[ir.Stmt]:
        if x.target:
            return [ir.Copy(x.target.name, x.value)]
        else:
            return [ir.Corn(x.value)]

    def loop_shared(
        self, x: Loop, before: Optional[ir.Guard], after: Optional[ir.Guard]
    ) -> List[ir.Stmt]:
        init: List[ir.Stmt] = (
            [ir.AssignEmptyList(x.target.name)]
            if x.target and not x.simple
            else []
        )
        tmps: list[str] | None = [x.element] if x.element else None
        body: List[ir.Stmt] = self.sequence(x.val, tmps)
        loop = ir.Loop(before, body, after)
        return init + [loop]

    def rep(self, x: Rep) -> List[ir.Stmt]:
        guard: ir.Guard = ir.Guard(x.val.predict)
        return self.loop_shared(x, guard, None)

    def oneplus(self, x: OnePlus) -> List[ir.Stmt]:
        guard: ir.Guard = ir.Guard(x.val.predict)
        return self.loop_shared(x, None, guard)

    def infinite(self, x: Infinite) -> List[ir.Stmt]:
        return self.loop_shared(x, None, None)

    def _break(self, x: Break) -> List[ir.Stmt]:
        return [ir.Break()]

    def _continue(self, x: Continue) -> List[ir.Stmt]:
        return [ir.Continue()]

    def opt(self, x: Opt) -> List[ir.Stmt]:
        init: List[ir.Stmt]
        if x.target and not x.simple:
            init = [ir.AssignNull(x.target.name)]
        else:
            init = [ir.Empty()]

        guardeds: List[ir.Guarded] = [
            ir.Guarded(ir.Guard(x.val.predict), self.expr(x.val))
        ]
        if_ = ir.SelectAlternative(guardeds, None)
        return init + [if_]

    def sym(self, x: Sym) -> List[ir.Stmt]:
        if x.value in (self.state.terms):
            return [ir.Terminal(x.target and x.target.name, x.value)]
        else:
            return [ir.NonTerminal(x.target and x.target.name, x.value)]

    def parens(self, x: Parens) -> List[ir.Stmt]:
        return self.expr(x.e)

    def lambda_(self, x: Lambda) -> List[ir.Stmt]:
        return []

    def expr(self, e: Expr) -> List[ir.Stmt]:
        retval: List[ir.Stmt] = []
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

        warnings: list[ir.Warning] = [
            ir.Warning(w) for w in self.state.warnings[e]
        ]
        verbose: list[ir.Verbose] = [
            ir.Verbose(e.dump0()),
        ]
        epilogue = e.target.side_effect if e.target else []
        return verbose + warnings + retval + epilogue

    def prod(self, p: Production, state: State) -> ir.Function:
        preamble: list[ir.Stmt] = [
            ir.Comment(f"{p.lhs} -> {p.rhs.__repr__()}"),
            ir.Verbose(
                f"{p.lhs}: nullable {state.syms_nullable[p.lhs].get_value()}"
            ),
            ir.Verbose(f"   first {state.syms_first[p.lhs].get_value()}"),
            ir.Verbose(f"   follow {state.syms_follow[p.lhs].get_value()}"),
        ]

        name: str = p.lhs
        ret: Optional[ir.Return] = None
        tmps = []
        if self.decorate:
            target: str = f"_{name}_"
            tmps = [target]
            ret = ir.Return(target)
        body: List[ir.Stmt] = self.sequence(p.rhs, tmps)
        if ret:
            body.append(ret)
        return ir.Function(name, preamble + body)

    def emit_parser(self, state: State) -> ir.Program:
        functions: List[ir.Function] = []
        for p in self.spec.productions:
            f: ir.Function = self.prod(p, state)
            functions.append(f)
        return ir.Program(
            self.spec.productions[0].lhs,
            self.spec.preamble,
            functions,
            self.pragmas,
        )
