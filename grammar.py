import collections
import typing
import sys


class State:
    nullable: collections.defaultdict[str, bool] = collections.defaultdict(bool)
    first: collections.defaultdict[str, typing.Set[str]] = collections.defaultdict(set)
    follow: collections.defaultdict[str, typing.Set[str]] = collections.defaultdict(set)
    nonterms: typing.Set[str] = set()
    terms: typing.Set[str] = set()
    changed: bool = False


class Expr:
    indentation = "    "
    first: set[str] = set()
    nullable = False
    follow: set[str] = set()

    def compute_nullable(self, state: State):
        assert False, "Expr.compute_nullable() not implemented"

    def compute_first(self, state: State):
        assert False, "Expr.compute_first() not implemented"

    def compute_follow(self, follow: set[str], state: State):
        assert False, "Expr.compute_follow() not implemented"

    def compute_predict(self, state: State):
        assert False, "Expr.compute_predict() not implemented"

    def __repr__(self):
        assert False, "Expr.__repr__() not implemented"

    def predict0(self, state: State):
        self.predict = self.first
        if self.nullable:
            self.predict |= self.follow

    def dump(self, indent):
        assert False, "Expr.dump() not implemented"

    def dump0(self, indent, name):
        print(
            f"{indent}{name}: nullable: {self.nullable} first: {self.first} follow: {self.follow} predict: {self.predict}"
        )

    def dump_flat(self, indent):
        if isinstance(self, Seq):
            self.car.dump_flat(indent)
            self.cdr.dump_flat(indent)
        else:
            self.dump(indent)


class Alts(Expr):
    def __init__(self, vals: list[Expr]):
        self.vals = vals

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

    def dump(self, indent):
        self.dump0(indent, "Alts")
        for i, v in enumerate(self.vals):
            print(f"{indent}#{i}:")
            v.dump(indent + "  ")


def repr_seq(e, L):
    if isinstance(e, Seq):
        repr_seq(e.car, L)
        repr_seq(e.cdr, L)
    elif isinstance(e, Alts):
        L.append(f"( {repr(e)} )")
    else:
        L.append(repr(e))


class Seq(Expr):
    def __init__(self, car: Expr, cdr: Expr):
        self.car = car
        self.cdr = cdr

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
            self.first = self.first | self.cdr.first
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

    def dump(self, indent):
        self.dump0(indent, "Seq")
        self.car.dump_flat(indent + "  ")
        self.cdr.dump_flat(indent + "  ")


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

    def dump(self, indent):
        self.dump0(indent, f"Sym({self.value})")


class Rep(Expr):
    def __init__(self, val: Expr):
        self.val = val

    def __repr__(self):
        return "{" + f" {self.val.__repr__()} " + "}"

    def compute_nullable(self, state: State):
        state.changed = state.changed or self.nullable != True
        self.nullable = True

    def compute_first(self, state: State):
        self.val.compute_first(state)
        state.changed = state.changed or self.first != self.val.first
        self.first = self.val.first.copy()

    def compute_follow(self, follow: set[str], state: State):
        assert self.follow.issubset(follow)
        self.val.compute_follow(follow | self.val.first, state)
        state.changed = state.changed or self.follow != follow
        self.follow = follow.copy()

    def compute_predict(self, state: State):
        self.val.compute_predict(state)
        self.predict0(state)

    def dump(self, indent):
        self.dump0(indent, "Rep")
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

    def dump(self, indent):
        self.dump0(indent, "Opt")
        self.val.dump(indent + "  ")


class Production:
    def __init__(self, lhs: str, rhs: Expr):
        self.lhs: str = lhs
        self.rhs: Expr = rhs

    def dump(self):
        print(self.lhs, " -> ")
        self.rhs.dump("  ")


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
            state.changed = state.changed or state.nullable[p.lhs] != p.rhs.nullable
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

    # for p in g:
    #     p.dump()
