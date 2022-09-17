import random

from grammar import Alts, Seq, Rep, Opt, Sym, Production, State, Expr

count = 0
maximum = 100

# alts
def alts(self: Alts, productions: list[Production], state: State) -> list[str]:
    choice = random.choice(self.vals)
    return gen_random(choice, productions, state)


# seq
def seq(self: Seq, productions: list[Production], state: State) -> list[str]:
    return gen_random(self.car, productions, state) + gen_random(
        self.cdr, productions, state
    )


# rep
def rep(self: Rep, productions: list[Production], state: State) -> list[str]:
    L = []
    if count < 100:
        for _ in range(random.randint(0, 2)):
            L += gen_random(self.val, productions, state)
    return L


# opt
def opt(self: Opt, productions: list[Production], state: State):
    L = []
    if count < 100:
        for _ in range(random.randint(0, 1)):
            L += gen_random(self.val, productions, state)
    return L


# sym
def sym(self: Sym, productions: list[Production], state: State) -> list[str]:
    if self.isterminal(state):
        if self.value[0] == '"':
            return [self.value[1:-1]]
        else:
            return [self.value]
    else:
        for p in productions:
            if p.lhs == self.value:
                return gen_random(p.rhs, productions, state)
        assert False, f"unknown symbol: {self.value}"


def gen_random(e: Expr, productions: list[Production], state) -> list[str]:
    global count
    count += 1
    if isinstance(e, Alts):
        return alts(e, productions, state)
    elif isinstance(e, Seq):
        return seq(e, productions, state)
    elif isinstance(e, Rep):
        return rep(e, productions, state)
    elif isinstance(e, Opt):
        return opt(e, productions, state)
    elif isinstance(e, Sym):
        return sym(e, productions, state)
    else:
        raise Exception(f"unknown expr: {e}")


def gen(
    e: Expr, productions: list[Production], state, max: int, subs: list[str]
) -> str:
    global count, maximum
    count = 0
    maximum = max
    L = gen_random(e, productions, state)
    s = " ".join(x.strip() for x in L)
    for sub in subs:
        before, after = sub.split(":")
        s = s.replace(before, after)
    return s
