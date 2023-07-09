from typing import List, Optional, Dict, Any

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
    Spec,
    Break,
    Continue,
    OnePlus,
    Sequence,
    Seq0,
    Value,
    Infinite,
    Target,
)

import ir

from analysis import State


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
    ):
        self.spec: Spec = spec
        self.state: State = state
        self.pragmas: Dict[str, Any] = pragmas
        self.verbose: bool = verbose

    def epilogue(self, x: Expr) -> List[ir.Stmt]:
        stmts: list[ir.Stmt] = []
        # if x.name and x.target:
        #     append(stmts, ir.mkCopy(x.target.name, x.name))
        if x.target:
            stmts.extend(x.target.side_effect)
        return stmts

    def alts(self, x: Alts) -> List[ir.Stmt]:
        warnings: list[ir.Warning] = [
            ir.Warning(w) for w in self.state.warnings[x]
        ]
        guardeds: List[ir.Guarded] = []
        for v in x.vals:
            guard: ir.Guard = ir.Guard(v.predict)
            body: List[ir.Stmt] = self.sequence(v)
            guardeds.append(ir.Guarded(guard, body))

        if_ = ir.SelectAlternative(guardeds, ir.ParseError("syntax error"))
        return warnings + [if_] + self.epilogue(x)

    def cons0(
        self, x: Seq0, decls: List[ir.Decl], stmts: List[ir.Stmt]
    ) -> None:
        while isinstance(x, Cons):
            car: List[ir.Stmt] = self.expr(x.car)
            if x.car.name:
                decls.append(ir.Decl(x.car.name))
            stmts.extend(car)
            x = x.cdr

    def sequence(
        self, x: Sequence, tmps: Optional[List[str]] = None
    ) -> List[ir.Stmt]:
        decls: List[ir.Decl] = [ir.Decl(t) for t in tmps] if tmps else []
        stmts: List[ir.Stmt] = []
        self.cons0(x.seq, decls, stmts)
        seq = ir.Sequence(decls, stmts)
        return [seq] + self.epilogue(x)

    def value(self, x: Value) -> List[ir.Stmt]:
        if x.target:
            return [ir.Copy(x.target.name, x.value)]
        else:
            return [ir.Corn(x.value)]

    def loop_simple(self, target: Optional[Target], simple: bool) -> ir.Stmt:
        if target and not simple:
            return ir.AssignEmptyList(target.name)
        else:
            return ir.Empty()

    def rep(self, x: Rep) -> List[ir.Stmt]:
        warnings: list[ir.Warning] = [
            ir.Warning(w) for w in self.state.warnings[x]
        ]
        init = self.loop_simple(x.target, x.simple)
        guard: ir.Guard = ir.Guard(x.val.predict)
        tmps = [x.element] if x.element else None
        body: List[ir.Stmt] = self.sequence(x.val, tmps)
        loop = ir.Loop(guard, body, None)
        return [init] + warnings + [loop] + self.epilogue(x)

    def oneplus(self, x: OnePlus) -> List[ir.Stmt]:
        warnings: list[ir.Warning] = [
            ir.Warning(w) for w in self.state.warnings[x]
        ]
        init = self.loop_simple(x.target, x.simple)
        guard: ir.Guard = ir.Guard(x.val.predict)
        tmps = [x.element] if x.element else None
        body: List[ir.Stmt] = self.sequence(x.val, tmps)
        loop = ir.Loop(None, body, guard)
        return [init] + warnings + [loop] + self.epilogue(x)

    def infinite(self, x: Infinite) -> List[ir.Stmt]:
        init = self.loop_simple(x.target, x.simple)
        tmps = [x.element] if x.element else None
        body: List[ir.Stmt] = self.sequence(x.val, tmps)
        loop = ir.Loop(None, body, None)
        return [init] + [loop] + self.epilogue(x)

    def _break(self, x: Break) -> List[ir.Stmt]:
        return [ir.Break()]

    def _continue(self, x: Continue) -> List[ir.Stmt]:
        return [ir.Continue()]

    def opt(self, x: Opt) -> List[ir.Stmt]:
        warnings: list[ir.Warning] = [
            ir.Warning(w) for w in self.state.warnings[x]
        ]
        if x.target and not x.simple:
            init = ir.AssignNull(x.target.name)
        else:
            init = ir.Empty()

        guardeds: List[ir.Guarded] = [
            ir.Guarded(ir.Guard(x.val.predict), self.expr(x.val))
        ]
        if_ = ir.SelectAlternative(guardeds, None)
        return [init] + warnings + [if_] + self.epilogue(x)

    def sym(self, x: Sym) -> List[ir.Stmt]:
        s: ir.Stmt
        if x.value in (self.state.terms):
            s = ir.Terminal((x.target and x.target.name), x.value)
        else:
            s = ir.NonTerminal((x.target and x.target.name), x.value)
        return [s] + self.epilogue(x)

    def parens(self, x: Parens) -> List[ir.Stmt]:
        p: List[ir.Stmt] = self.expr(x.e)
        return p + self.epilogue(x)

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
        verbose: list[ir.Verbose] = [
            ir.Verbose(e.dump0()),
        ]
        return verbose + retval

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
        body: List[ir.Stmt] = self.expr(p.rhs)
        target: str = f"_{name}_"
        ret = ir.Return(target)
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
