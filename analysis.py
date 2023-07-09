from typing import Any, Dict, List, Set
from collections import defaultdict, Counter

import grammar
from react import Indirect, Constant, Gate, Undefined, Expr


class State:
    syms_nullable: Dict[str, Indirect] = {}
    syms_first: Dict[str, Indirect] = {}
    syms_follow: Dict[str, Indirect] = {}
    ancestors: List[grammar.Expr] = []
    terms: Set[str] = set()
    nonterms: Set[str] = set()

    nullable: Dict[grammar.Expr, Indirect] = {}
    first: Dict[grammar.Expr, Indirect] = {}
    follow: Dict[grammar.Expr, Indirect] = {}
    predict: Dict[grammar.Expr, Indirect] = {}

    warnings: Dict[grammar.Expr, List[str]] = defaultdict(list)


def noop(self: grammar.Expr, x: Any) -> None:
    assert x == x
    match self:
        case grammar.Lambda():
            pass
        case grammar.Value():
            pass
        case grammar.Parens():
            pass
        case grammar.Alts():
            pass
        case grammar.Cons():
            pass
        case grammar.Rep():
            pass
        case grammar.Opt():
            pass
        case grammar.OnePlus():
            pass
        case grammar.Break():
            pass
        case grammar.Continue():
            pass
        case grammar.Sym():
            pass
        case grammar.Sequence():
            pass
        case _:
            raise NotImplementedError(
                f"Unexpected expr: {self.__class__.__name__}"
            )


def populate(self: grammar.Expr, x: Any):
    assert isinstance(x, State)
    x.nullable[self] = Indirect(Undefined(False))
    x.first[self] = Indirect(Undefined(set()))
    x.follow[self] = Indirect(Undefined(set()))
    x.predict[self] = Indirect(Undefined(set()))


def pre_setup(self: grammar.Expr, x: Any) -> None:
    assert isinstance(x, State)
    x.ancestors.append(self)


def post_setup(self: grammar.Expr, x: Any) -> None:
    assert isinstance(x, State)
    x.ancestors.pop()
    match self:
        case grammar.Lambda():
            x.nullable[self] ^= Constant(True)
            x.first[self] ^= Constant(set())
        case grammar.Value():
            x.nullable[self] ^= Constant(True)
            x.first[self] ^= Constant(set())
        case grammar.Parens():
            x.nullable[self] ^= x.nullable[self.e]
            x.first[self] ^= x.first[self.e]
            x.follow[self.e] ^= x.follow[self]
        case grammar.Alts():
            first: Expr = Constant(set())
            nullable: Expr = Constant(False)
            f: grammar.Expr
            for f in self.vals:
                first = first | x.first[f]
                nullable = nullable | x.nullable[f]
            x.nullable[self] ^= nullable
            x.first[self] ^= first
            for f in self.vals:
                x.follow[f] ^= x.follow[self]
        case grammar.Sequence():
            x.nullable[self] ^= x.nullable[self.seq]
            x.first[self] ^= x.first[self.seq]
            x.follow[self.seq] ^= x.follow[self]
        case grammar.Cons():
            x.nullable[self] ^= x.nullable[self.car] & x.nullable[self.cdr]
            x.first[self] ^= x.first[self.car] | Gate(
                x.nullable[self.car], x.first[self.cdr], Constant(set())
            )
            x.follow[self.cdr] ^= x.follow[self]
            x.follow[self.car] ^= x.first[self.cdr] | Gate(
                x.nullable[self.cdr],
                x.follow[self.cdr],
                Constant(set()),
            )
        case grammar.Sym():
            x.nullable[self] ^= x.syms_nullable[self.value]
            x.first[self] ^= x.syms_first[self.value]

            x.syms_follow[self.value] |= x.follow[self]
        case grammar.Rep():
            x.nullable[self] ^= Constant(True)
            x.first[self] ^= x.first[self.val]

            x.follow[self.val] ^= x.first[self] | x.follow[self]
        case grammar.Opt():
            x.nullable[self] ^= Constant(True)
            x.first[self] ^= x.first[self.val]
            x.follow[self.val] ^= x.follow[self]
        case grammar.Break():
            x.nullable[self] ^= Constant(False)
            for a in reversed(x.ancestors):
                if isinstance(a, grammar.Loop):
                    x.first[self] ^= x.follow[a]
                    x.predict[self] ^= x.follow[a]
                    break
            assert x.first[self] is not None
            assert x.predict[self] is not None
        case _:
            raise NotImplementedError(
                f"Unexpected expr: {self.__class__.__name__}"
            )

    if not isinstance(self, grammar.Exit):
        x.predict[self] ^= x.first[self] | Gate(
            x.nullable[self], x.follow[self], Constant(set())
        )


def compute_warnings(self: grammar.Expr, x: Any) -> None:
    assert isinstance(x, State)
    match self:
        case grammar.Alts():
            counts: Counter[str] = Counter(
                s for v in self.vals for s in v.predict
            )
            for v in self.vals:
                ambiguous: set[str] = {s for s in v.predict if counts[s] > 1}
                if ambiguous:
                    x.warnings[self].append(
                        f"AMBIGUOUS LOOKAHEADS: {(ambiguous)}"
                    )
        case grammar.Rep():
            inter = self.val.first & self.follow
            if inter:
                x.warnings[self].append(f"AMBIGUOUS: with lookahead {(inter)}")
            if self.val.nullable:
                x.warnings[self].append(f"AMBIGUOUS: Nullable Repetition")
        case grammar.OnePlus():
            inter = self.val.first & self.follow
            if inter:
                x.warnings[self].append(f"AMBIGUOUS: with lookahead {(inter)}")
            if self.val.nullable:
                x.warnings[self].append(f"AMBIGUOUS: Nullable Optional\n")
        case grammar.Opt():
            inter = self.val.first & self.follow
            if inter:
                x.warnings[self].append(f"AMBIGUOUS: with lookahead {(inter)}")
            if self.val.nullable:
                x.warnings[self].append(f"AMBIGUOUS: Nullable Optional\n")
        case grammar.Break():
            pass
        case grammar.Lambda():
            pass
        case grammar.Value():
            pass
        case grammar.Parens():
            pass
        case grammar.Sequence():
            pass
        case grammar.Cons():
            pass
        case grammar.Sym():
            pass
        case _:
            raise NotImplementedError(
                f"Unexpected expr: {self.__class__.__name__}"
            )


def check(self: grammar.Expr, x: Any) -> None:
    assert not isinstance(x.nullable[self], Undefined)
    assert not isinstance(x.first[self], Undefined)
    assert not isinstance(x.follow[self], Undefined)
    assert not isinstance(x.predict[self], Undefined)


def overwrite(self: grammar.Expr, x: Any) -> None:
    self.first = x.first[self].get_value()
    self.nullable = x.nullable[self].get_value()
    self.follow = x.follow[self].get_value()
    self.predict = x.predict[self].get_value()


def compute_terms(self: grammar.Expr, x: Any) -> None:
    assert isinstance(x, State)
    match self:
        case grammar.Sym():
            if self.value not in x.nonterms:
                x.terms.add(self.value)
        case _:
            pass


def analysis(g: List[grammar.Production]) -> State:
    state = State()
    for p in g:
        assert p.lhs not in state.nonterms
        state.nonterms.add(p.lhs)
    for p in g:
        p.rhs.visit(compute_terms, noop, state)
    for t in state.terms:
        state.syms_first[t] = Indirect(Constant({t}))
        state.syms_nullable[t] = Indirect(Constant(False))
        state.syms_follow[t] = Indirect(Constant(set()))
    for nt in state.nonterms:
        state.syms_first[nt] = Indirect(Constant(set()))
        state.syms_nullable[nt] = Indirect(Constant(False))
        state.syms_follow[nt] = Indirect(Constant(set()))
    state.syms_follow[g[0].lhs] |= {"EOF"}

    for p in g:
        p.rhs.visit(populate, noop, state)
        state.follow[p.rhs] ^= state.syms_follow[p.lhs]
        p.rhs.visit(pre_setup, post_setup, state)
        state.syms_first[p.lhs] |= state.first[p.rhs]
        state.syms_nullable[p.lhs] |= state.nullable[p.rhs]

    for p in g:
        p.rhs.visit(check, noop, state)

    for p in g:
        p.rhs.visit(overwrite, noop, state)

    for p in g:
        p.rhs.visit(compute_warnings, noop, state)

    return state
    # for nt in grammarstate.nonterms | grammarstate.terms:
    #     print(f"--- {nt}")
    #     print("     first:", grammarstate.first[nt])
    #     print(" pre_first:", state.syms_first[nt].get_value())
    #     # assert grammarstate.first[nt] == state.syms_first[nt].get_value()
    #     print("  follow:", grammarstate.follow[nt])
    #     print(" post_LA:", state.syms_follow[nt].get_value())
    #     # assert grammarstate.follow[nt] == state.syms_follow[nt].get_value()

    # def chk(e: grammar.Expr, x) -> None:
    #     print(f"--- {e}")
    #     print("     first:", e.first)
    #     print("    efirst:", e.efirst.get_value())
    #     # assert e.first == e.efirst.get_value()
    #     print("  follow:", e.follow)
    #     print(" efollow:", e.efollow.get_value())
    #     # assert e.follow == e.efollow.get_value()
    #     print("     predict:", e.predict)
    #     print("    epredict:", e.epredict.get_value())
    #     # assert e.predict == e.epredict.get_value()

    # for p in g:
    #     p.rhs.visit(noop, chk, None)
