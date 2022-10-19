from collections import defaultdict, Counter
from typing import Optional, Set, List
import sys


class State:
    nullable: defaultdict[str, bool] = defaultdict(bool)
    first: defaultdict[str, Set[str]] = defaultdict(set)
    follow: defaultdict[str, Set[str]] = defaultdict(set)
    nonterms: Set[str] = set()
    terms: Set[str] = set()
    changed: bool = False


class Expr:
    indentation = "    "
    first: set[str] = set()
    nullable = False
    follow: set[str] = set()

    # code generation directives
    name: Optional[str] = None
    keep: bool = False
    stmts: List[str] = []
    simple: bool = False

    # inherited target for computed value
    target: Optional[str] = None

    def compute_nullable(self, state: State):
        assert False, "Expr.compute_nullable() not implemented"

    def compute_first(self, state: State):
        assert False, "Expr.compute_first() not implemented"

    def compute_follow(self, follow: set[str], state: State):
        assert False, "Expr.compute_follow() not implemented"

    def compute_predict(self, state: State):
        assert False, "Expr.compute_predict() not implemented"

    def compute_warnings(self):
        assert False, "Expr.compute_warnings() not implemented"

    def __repr__(self):
        assert False, "Expr.__repr__() not implemented"

    def predict0(self, state: State):
        self.predict = self.first
        if self.nullable:
            self.predict |= self.follow

    def dump(self, indent):
        assert False, "Expr.dump() not implemented"

    def dump0(self, indent, name) -> str:
        s = f"{indent}{name}: nullable: {self.nullable} first: {self.first} follow: {self.follow} predict: {self.predict}"
        if self.name:
            s += f" name: {self.name}"
        if self.keep:
            s += f" keep: {self.keep}"
        if isinstance(self, Cons):
            if self.code:
                s += f" code: {self.code}"
        return s

    def dump_flat(self, indent):
        if isinstance(self, Cons):
            self.car.dump_flat(indent)
            self.cdr.dump_flat(indent)
        else:
            self.dump(indent)


class Seq(Expr):
    def filter(self, f):
        s = self
        L = []
        while isinstance(s, Cons):
            if f(s):
                L.append(s)
            s = s.cdr
        return L


class Lambda(Seq):
    def compute_nullable(self, state: State):
        self.nullable = True

    def compute_first(self, state: State):
        self.first = set()

    def compute_follow(self, follow: set[str], state: State):
        self.follow = follow.copy()

    def compute_predict(self, state: State):
        self.predict = self.follow

    def compute_warnings(self):
        pass

    def __repr__(self):
        return ""

    def dump(self, indent):
        # print(self.dump0(indent, "Lambda"))
        pass


class Parens(Expr):
    def __init__(self, e: Expr):
        self.e = e

    def compute_nullable(self, state: State):
        self.nullable = self.e.nullable

    def compute_first(self, state: State):
        self.e.compute_first(state)
        self.first = self.e.first.copy()

    def compute_follow(self, follow: set[str], state: State):
        self.e.compute_follow(follow, state)
        self.follow = follow.copy()

    def compute_predict(self, state: State):
        self.e.compute_predict(state)
        self.predict = self.e.predict.copy()

    def compute_warnings(self):
        self.e.compute_warnings()

    def __repr__(self):
        return f"({self.e.__repr__()})"

    def dump(self, indent):
        print(self.dump0(indent, "Parens"))
        self.e.dump(indent + "  ")


class Alts(Expr):
    def __init__(self, vals: list["Cons"]):
        self.vals: List["Cons"] = vals
        self.warnings: list[str | None]

    def __repr__(self):
        return f'{" | ".join(repr(v) for v in self.vals)}'

    def compute_nullable(self, state: State):
        for v in self.vals:
            v.compute_nullable(state)
        prev = self.nullable
        self.nullable = any(v.nullable for v in self.vals)
        state.changed = state.changed or prev != self.nullable

    def compute_first(self, state: State):
        union: set[str] = set()
        for v in self.vals:
            v.compute_first(state)
            union |= v.first
        prev = self.first
        state.changed = state.changed or prev != self.first
        self.first = union

    def compute_follow(self, follow: set[str], state: State):
        assert self.follow.issubset(follow)
        state.changed = state.changed or self.follow != follow
        self.follow = follow.copy()
        for v in self.vals:
            v.compute_follow(follow, state)

    def compute_predict(self, state: State):
        for v in self.vals:
            v.compute_predict(state)
        self.predict0(state)

    def compute_warnings(self):
        self.warnings = []
        counts: Counter[str] = Counter(s for v in self.vals for s in v.predict)
        for v in self.vals:
            v.compute_warnings()
            ambiguous: set[str] = {s for s in v.predict if counts[s] > 1}
            if ambiguous:
                self.warnings.append(
                    f"{indent}# AMBIGUOUS LOOKAHEADS: {set_repr(ambiguous)}:\n"
                )
            else:
                self.warnings.append(None)

    def dump(self, indent):
        print(self.dump0(indent, "Alts"))
        for i, v in enumerate(self.vals):
            print(f"{indent}#{i}:")
            v.dump(indent + "  ")


def repr_seq(e, L):
    if isinstance(e, Cons):
        repr_seq(e.car, L)
        repr_seq(e.cdr, L)
    elif isinstance(e, Lambda):
        pass
    # elif isinstance(e, Alts):
    #     L.append(f"( {repr(e)} )")
    else:
        L.append(repr(e))


class Cons(Seq):
    def __init__(self, car: Expr, cdr: Seq):
        self.car = car
        self.cdr: Seq = cdr
        self.code: Optional[str] = None
        self.prologue: List[str] = []

        # possible inferred values for the sequence
        self.at_term: Optional[str] = None
        self.tuple: Optional[List[str]] = None
        self.dict: Optional[List[str]] = None
        self.singleton: Optional[str] = None

    def __repr__(self):
        L: list[str] = []
        repr_seq(self, L)
        return " ".join(L)

    def compute_nullable(self, state: State):
        self.car.compute_nullable(state)
        self.cdr.compute_nullable(state)
        prev = self.nullable
        self.nullable = self.car.nullable and self.cdr.nullable
        state.changed = state.changed or prev != self.nullable

    def compute_first(self, state: State):
        self.car.compute_first(state)
        self.cdr.compute_first(state)
        prev = self.first
        if self.car.nullable:
            self.first = self.car.first | self.cdr.first
        else:
            self.first = self.car.first.copy()
        state.changed = state.changed or prev != self.first

    def compute_follow(self, follow: set[str], state: State):
        state.changed = state.changed or self.follow != follow
        assert self.follow.issubset(follow)
        self.cdr.compute_follow(follow, state)
        if self.cdr.nullable:
            f = follow | self.cdr.first
            self.car.compute_follow(f, state)
        else:
            self.car.compute_follow(self.cdr.first, state)
        self.follow = follow.copy()

    def compute_predict(self, state: State):
        self.car.compute_predict(state)
        self.cdr.compute_predict(state)
        self.predict0(state)

    def compute_warnings(self):
        self.car.compute_warnings()
        self.cdr.compute_warnings()

    def dump(self, indent):
        print(self.dump0(indent, "Seq"))
        self.car.dump(indent + "  ")
        self.cdr.dump(indent)


class Sym(Expr):
    def __init__(self, value: str):
        self.value = value

    def __repr__(self):
        return self.value

    def isterminal(self, state) -> bool:
        if self.value in state.nonterms:
            return False
        else:
            state.terms.add(self.value)
            return True

    def compute_nullable(self, state: State):
        if self.isterminal(state):
            v = False
        else:
            v = state.nullable[self.value]
        state.changed = state.changed or self.nullable != v
        self.nullable = v

    def compute_first(self, state: State):
        if self.isterminal(state):
            v = {self.value}
        else:
            v = state.first[self.value].copy()
        state.changed = state.changed or self.first != v
        self.first = v

    def compute_follow(self, follow: set[str], state: State):
        state.changed = state.changed or self.follow != follow
        assert self.follow.issubset(follow)
        self.follow = follow.copy()
        nt_follow = state.follow[self.value] | follow
        state.changed = state.changed or state.follow[self.value] != nt_follow
        state.follow[self.value] = nt_follow

    def compute_predict(self, state: State):
        self.predict0(state)

    def compute_warnings(self):
        pass

    def dump(self, indent):
        print(self.dump0(indent, f"Sym({self.value})"))


class Rep(Expr):
    def __init__(self, val: Expr):
        self.val = val
        self.element: Optional[str] = None

    def __repr__(self):
        return "{" + f" {self.val.__repr__()} " + "}"

    def compute_nullable(self, state: State):
        state.changed = state.changed or self.nullable != True
        self.nullable = True

    def compute_first(self, state: State):
        self.val.compute_first(state)
        state.changed = state.changed or self.first != self.val.first
        assert self.first.issubset(self.val.first)
        self.first = self.val.first.copy()

    def compute_follow(self, follow: set[str], state: State):
        assert self.follow.issubset(follow)
        self.val.compute_follow(follow | self.val.first, state)
        state.changed = state.changed or self.follow != follow
        self.follow = follow.copy()

    def compute_predict(self, state: State):
        self.val.compute_predict(state)
        self.predict0(state)

    def compute_warnings(self):
        self.warnings = []
        self.val.compute_warnings()
        inter = self.val.first.intersection(r.follow)
        if inter:
            self.warnings.append(
                f"{indent}# AMBIGUOUS: with lookahead {set_repr(inter)}\n"
            )
        if self.val.nullable:
            self.warnings.append(f"{indent}# AMBIGUOUS: Nullable Repetition\n")

    def dump(self, indent):
        print(self.dump0(indent, "Rep"))
        self.val.dump(indent + "  ")


class Opt(Expr):
    def __init__(self, val: Expr):
        self.val = val

    def __repr__(self):
        return f"[ {self.val.__repr__()} ]"

    def compute_nullable(self, state: State):
        state.changed = state.changed or self.nullable != True
        self.nullable = True

    def compute_first(self, state: State):
        self.val.compute_first(state)
        state.changed = state.changed or self.first != self.val.first
        self.first = self.val.first.copy()

    def compute_follow(self, follow: set[str], state: State):
        assert self.follow.issubset(follow)
        self.val.compute_follow(follow, state)
        state.changed = state.changed or self.follow != follow
        self.follow = follow.copy()

    def compute_predict(self, state: State):
        self.val.compute_predict(state)
        self.predict0(state)

    def compute_warnings(self):
        self.val.compute_warnings()
        self.warnings = []
        inter = self.val.first.intersection(o.follow)
        if inter:
            self.warnings.append(
                f"{indent}# AMBIGUOUS: with lookahead {set_repr(inter)}\n"
            )
        if self.val.nullable:
            self.warnings.append(f"{indent}# AMBIGUOUS: Nullable Optional\n")

    def dump(self, indent):
        print(self.dump0(indent, "Opt"))
        self.val.dump(indent + "  ")


class Production:
    def __init__(self, lhs: str, rhs: Expr):
        self.lhs: str = lhs
        self.rhs: Expr = rhs

    def dump(self):
        print(self.lhs, " -> ")
        self.rhs.dump("  ")


class Spec:
    def __init__(self, preamble: List[str], productions: list[Production]):
        self.preamble = preamble
        self.productions = productions

    def dump(self):
        for p in self.preamble:
            print(p)
        for p in self.productions:
            p.dump()


def analyze(g: list[Production]) -> State:
    state = State()
    for p in g:
        assert p.lhs not in state.nonterms
        state.nonterms.add(p.lhs)

    state.changed = True
    while state.changed:
        state.changed = False
        for p in g:
            p.rhs.compute_nullable(state)
            state.changed = (
                state.changed or state.nullable[p.lhs] != p.rhs.nullable
            )
            state.nullable[p.lhs] = p.rhs.nullable

    state.changed = True
    while state.changed:
        state.changed = False
        for p in g:
            p.rhs.compute_first(state)
            state.changed = state.changed or state.first[p.lhs] != p.rhs.first
            state.first[p.lhs] = p.rhs.first.copy()

    state.changed = True
    state.follow[g[0].lhs] = {"EOF"}
    while state.changed:
        state.changed = False
        for p in g:
            p.rhs.compute_follow(state.follow[p.lhs], state)

    for p in g:
        p.rhs.compute_predict(state)

    return state
