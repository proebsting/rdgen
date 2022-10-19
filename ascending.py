import heapq
import pprint

from grammar import Alts, Seq, Rep, Opt, Sym, Production, State, Expr, Cons


# MyHeap adapted from https://stackoverflow.com/questions/8875706/heapq-with-custom-compare-predicate
class MyHeap(object):
    def __init__(self, key=lambda x: x, limit=20):
        self.key = key
        self.index = 0
        self._data = []
        self.limit = limit

    def push(self, item):
        v = (self.key(item), self.index, item)
        if v[0][0] > self.limit:
            return
        if len(self._data) > 4000000:
            self._data = self._data[:3000000]
        heapq.heappush(self._data, v)
        self.index += 1

    def pop(self):
        return heapq.heappop(self._data)[2]

    def dump(self):
        for item in self._data:
            print(item)
        print("---")


def flatten(L, state: State) -> list:
    out = []
    for e in L:
        if isinstance(e, Cons):
            out += flatten([e.car, e.cdr], state)
        elif isinstance(e, Sym) and e.isterminal(state):
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
    before,
    after,
    heap,
    productions: list[Production],
    state: State,
):
    for alt in self.vals:
        L = before + [alt] + after
        L = flatten(L, state)
        heap.push(L)


# seq
def cons(
    self: Cons,
    before,
    after,
    heap,
    productions: list[Production],
    state: State,
):
    L = before + [self.car] + [self.cdr] + after
    L = flatten(L, state)
    heap.push(L)


# rep
def rep(
    self: Rep, before, after, heap, productions: list[Production], state: State
):
    for count in range(0, 3):
        L = before + [self.val] * count + after
        L = flatten(L, state)
        heap.push(L)


# opt
def opt(
    self: Opt, before, after, heap, productions: list[Production], state: State
):
    L = before + [self.val] + after
    L = flatten(L, state)
    heap.push(L)
    L = before + after
    L = flatten(L, state)
    heap.push(L)


# sym
def sym(
    self: Sym, before, after, heap, productions: list[Production], state: State
):
    if self.isterminal(state):
        if self.value[0] == '"':
            v = [self.value[1:-1]]
        else:
            v = [self.value]
        L = before + v + after
        heap.push(L)
    else:
        for p in productions:
            if p.lhs == self.value:
                inner = flatten([p.rhs], state)
                L = before + inner + after
                heap.push(L)
                return
        assert False, f"unknown symbol: {self.value}"


def add_derivations(e, before, after, heap, productions, state):
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


def min_terminals0(e, state: State) -> int:
    if isinstance(e, Alts):
        return min([min_terminals0(v, state) for v in e.vals])
    elif isinstance(e, Cons):
        return min_terminals0(e.car, state) + min_terminals0(e.cdr, state)
    elif isinstance(e, Rep):
        return 0
    elif isinstance(e, Opt):
        return 0
    elif isinstance(e, Sym):
        if e.isterminal(state):
            return 1
        else:
            return 0
    elif isinstance(e, str):
        return 1
    else:
        raise Exception(f"unknown expr: {e}")


def count_terminals(L: list) -> int:
    assert isinstance(L, list)
    count = 0
    for e in L:
        if isinstance(e, str):
            count += 1
    return count


def gen_examples(
    grammar: list[Production], state: State, quantity: int, limit: int
) -> list[str]:
    def min_terminals(L) -> int:
        assert isinstance(L, list)
        return sum([min_terminals0(e, state) for e in L])

    outputs = []
    heap = MyHeap(key=lambda x: (min_terminals(x), len(x)), limit=limit)
    start = flatten([grammar[0].rhs], state)
    heap.push(start)
    while len(heap._data) > 0 and len(outputs) < quantity:
        # if len(outputs) % 1000 == 0:
        #     print(f"# len(outputs)={len(outputs)}")
        #     print(f"# len(heap)={len(heap._data)}")
        e = heap.pop()
        if count_terminals(e) == len(e):
            s = " ".join(e)
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
