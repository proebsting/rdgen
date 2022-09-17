from collections import Counter

from grammar import Alts, Seq, Rep, Opt, Sym, Production, State, Expr


# alts
def alts(self, indent: str, state: State) -> list[str]:
    counts = Counter(s for v in self.vals for s in v.predict)
    ret: list[str] = []
    for i, v in enumerate(self.vals):
        ambiguous = {s for s in v.predict if counts[s] > 1}
        if ambiguous:
            ret.append(f"{indent}# AMBIGUOUS LOOKAHEADS: {set_repr(ambiguous)}:")
        if i == 0:
            cond = "if"
        else:
            cond = "elif"
        ret += [f"{indent}{cond} self.scanner.peek().kind in {set_repr(v.predict)}:"]
        ret += emit(v, indent + self.indentation, state)
    ret += [f"{indent}else:"]
    ret += [f"{indent+self.indentation}self.error('syntax error')"]
    return ret


# seq
def seq(self, indent: str, state: State) -> list[str]:
    ret = emit(self.car, indent, state) + emit(self.cdr, indent, state)
    return ret


# rep
def rep(self, indent: str, state: State) -> list[str]:
    indented = indent + self.indentation
    ret = []
    if self.val.nullable:
        ret.append(f"{indent}# AMBIGUOUS: Nullable Rep")
    ret.append(f"{indent}while self.scanner.peek().kind in {set_repr(self.val.first)}:")
    ret += emit(self.val, indented, state)
    return ret


# opt
def opt(self, indent: str, state: State):
    indented = indent + self.indentation
    ret = []
    if self.val.nullable:
        ret.append(f"{indent}# AMBIGUOUS: Nullable Rep")
    ret.append(f"{indent}if self.scanner.peek().kind in {set_repr(self.val.first)}:")
    ret += emit(self.val, indented, state)
    return ret


# sym
def sym(self, indent: str, state: State) -> list[str]:
    if self.isterminal(state):
        return [f"{indent}self.scanner.match({term_repr(self.value)})"]
    else:
        return [f"{indent}self.{self.value}()"]


# prod
def prod(self, indent: str, state: State):
    indented = indent * 2
    return [
        f"{indent}# {self.lhs} -> {self.rhs.__repr__()}",
        f"{indent}def {self.lhs}(self):",
    ] + emit(self.rhs, indented, state)


def term_repr(s: str) -> str:
    return s.replace('"', "").__repr__()


def set_repr(s: set[str]) -> str:
    return "{" + ", ".join(term_repr(w) for w in sorted(s)) + "}"


def emit(e: Expr, indent: str, state: State) -> list[str]:
    if isinstance(e, Alts):
        return alts(e, indent, state)
    elif isinstance(e, Seq):
        return seq(e, indent, state)
    elif isinstance(e, Rep):
        return rep(e, indent, state)
    elif isinstance(e, Opt):
        return opt(e, indent, state)
    elif isinstance(e, Sym):
        return sym(e, indent, state)
    else:
        raise Exception(f"unknown expr: {e}")


prologue = """
from scanner import Scanner
class Parser:
    def __init__(self, scanner: Scanner):
        self.scanner = scanner

    def error(self, msg: str):
        raise Exception(msg + " at " + str(self.scanner.peek()))
"""


def emit_parser(g: list[Production], state: State):
    print(prologue)

    for p in g:
        for line in prod(p, "    ", state):
            print(line)

    for t in sorted(state.terms):
        print("# Token:", t)
