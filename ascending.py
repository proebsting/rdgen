import heapq
from typing import List, Callable, Tuple

from .grammar import Alts, Rep, Opt, Sym, Production, Cons, Expr

from .analysis import State


# MyHeap adapted from https://stackoverflow.com/questions/8875706/heapq-with-custom-compare-predicate
class MyHeap(object):
    def __init__(
        self,
        key: Callable[[List[str | Expr]], Tuple[int, int]],
        limit: int = 20,
    ):
        self.key: Callable[[List[str | Expr]], Tuple[int, int]] = key
        self.index = 0
        self._data: List[Tuple[Tuple[int, int], int, List[str | Expr]]] = []
        self.limit = limit

    def push(self, item: List[str | Expr]):
        v = (self.key(item), self.index, item)
        if v[0][0] > self.limit:
            return
        if len(self._data) > 4000000:
            self._data = self._data[:3000000]
        heapq.heappush(self._data, v)
        self.index += 1

    def pop(self) -> List[str | Expr]:
        return heapq.heappop(self._data)[2]

    def __len__(self):
        return len(self._data)

    def dump(self):
        for item in self._data:
            print(item)
        print("---")


def flatten(exprs: List[Expr | str], state: State) -> List[str | Expr]:
    out: List[str | Expr] = []
    for e in exprs:
        if isinstance(e, Cons):
            out += flatten([e.car, e.cdr], state)
        elif isinstance(e, Sym) and e.value in state.terms:
            v: str
            if e.value[0] == '"':
                v = e.value[1:-1]
            else:
                v = e.value
            out.append(v)
        else:
            out.append(e)
    return out


# alts
def alts(
    self: Alts,
    before: List[Expr | str],
    after: List[Expr | str],
    heap: MyHeap,
    productions: list[Production],
    state: State,
):
    for alt in self.vals:
        lis: List[Expr | str] = before + [alt] + after
        lis = flatten(lis, state)
        heap.push(lis)


# seq
def cons(
    self: Cons,
    before: List[Expr | str],
    after: List[Expr | str],
    heap: MyHeap,
    productions: list[Production],
    state: State,
):
    lis = before + [self.car] + [self.cdr] + after
    lis = flatten(lis, state)
    heap.push(lis)


# rep
def rep(
    self: Rep,
    before: List[Expr | str],
    after: List[Expr | str],
    heap: MyHeap,
    productions: list[Production],
    state: State,
):
    for count in range(0, 3):
        lis = before + [self.val] * count + after
        lis = flatten(lis, state)
        heap.push(lis)


# opt
def opt(
    self: Opt,
    before: List[Expr | str],
    after: List[Expr | str],
    heap: MyHeap,
    productions: list[Production],
    state: State,
):
    lis = before + [self.val] + after
    lis = flatten(lis, state)
    heap.push(lis)
    lis = before + after
    lis = flatten(lis, state)
    heap.push(lis)


# sym
def sym(
    self: Sym,
    before: List[Expr | str],
    after: List[Expr | str],
    heap: MyHeap,
    productions: list[Production],
    state: State,
):
    if self.value in state.terms:
        if self.value[0] == '"':
            v = [self.value[1:-1]]
        else:
            v = [self.value]
        lis = before + v + after
        heap.push(lis)
    else:
        for p in productions:
            if p.lhs == self.value:
                inner = flatten([p.rhs], state)
                lis = before + inner + after
                heap.push(lis)
                return
        assert False, f"unknown symbol: {self.value}"


def add_derivations(
    e: Expr,
    before: List[Expr | str],
    after: List[Expr | str],
    heap: MyHeap,
    productions: List[Production],
    state: State,
):
    if isinstance(e, Alts):
        return alts(e, before, after, heap, productions, state)
    elif isinstance(e, Cons):
        return cons(e, before, after, heap, productions, state)
    elif isinstance(e, Rep):
        return rep(e, before, after, heap, productions, state)
    elif isinstance(e, Opt):
        return opt(e, before, after, heap, productions, state)
    elif isinstance(e, Sym):
        return sym(e, before, after, heap, productions, state)
    else:
        raise Exception(f"unknown expr: {e}")


def min_terminals0(e: Expr | str, state: State) -> int:
    if isinstance(e, Alts):
        return min([min_terminals0(v, state) for v in e.vals])
    elif isinstance(e, Cons):
        return min_terminals0(e.car, state) + min_terminals0(e.cdr, state)
    elif isinstance(e, Rep):
        return 0
    elif isinstance(e, Opt):
        return 0
    elif isinstance(e, Sym):
        if e.value in state.terms:
            return 1
        else:
            return 0
    elif isinstance(e, str):
        return 1
    else:
        raise Exception(f"unknown expr: {e}")


def count_terminals(lis: List[Expr | str]) -> int:
    assert isinstance(lis, list)
    count = 0
    e: Expr | str
    for e in lis:
        if isinstance(e, str):
            count += 1
    return count


def gen_examples(
    grammar: list[Production], state: State, quantity: int, limit: int
) -> list[str]:
    def min_terminals(lis: List[Expr | str]) -> int:
        assert isinstance(lis, list)
        return sum([min_terminals0(e, state) for e in lis])

    outputs: List[str] = []
    heap = MyHeap(key=lambda x: (min_terminals(x), len(x)), limit=limit)
    start = flatten([grammar[0].rhs], state)
    heap.push(start)
    while len(heap) > 0 and len(outputs) < quantity:
        # if len(outputs) % 1000 == 0:
        #     print(f"# len(outputs)={len(outputs)}")
        #     print(f"# len(heap)={len(heap._data)}")
        e: List[str | Expr] = heap.pop()
        if count_terminals(e) == len(e):
            assert all(isinstance(s, str) for s in e)
            ss: List[str] = [s for s in e if isinstance(s, str)]
            s: str = " ".join(ss)
            outputs.append(s)
            # print(f"output: {s.__repr__()}")
        else:
            for i, v in enumerate(e):
                if not isinstance(v, str):
                    before = e[:i]
                    after = e[i + 1 :]
                    add_derivations(v, before, after, heap, grammar, state)
                    break  # only do leftmost derivation
    return outputs
