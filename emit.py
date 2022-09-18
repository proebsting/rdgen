from collections import Counter
from typing import TextIO
from sys import stderr

from grammar import Alts, Seq, Rep, Opt, Sym, Production, State, Expr


def term_repr(s: str) -> str:
    return s.replace('"', "").__repr__()


def set_repr(s: set[str]) -> str:
    return "{" + ", ".join(term_repr(w) for w in sorted(s)) + "}"


class Emitter:
    def __init__(
        self, grammar: list[Production], state: State, file: TextIO, verbose: bool
    ):
        self.grammar = grammar
        self.state = state
        self.file = file
        self.verbose = verbose

    def alts(self, a: Alts, indent: str):
        counts = Counter(s for v in a.vals for s in v.predict)
        for i, v in enumerate(a.vals):
            ambiguous = {s for s in v.predict if counts[s] > 1}
            if ambiguous:
                self.file.write(
                    f"{indent}# AMBIGUOUS LOOKAHEADS: {set_repr(ambiguous)}:\n"
                )
            if i == 0:
                cond = "if"
            else:
                cond = "elif"
            self.file.write(
                f"{indent}{cond} self.scanner.peek().kind in {set_repr(v.predict)}:\n"
            )
            self.emit(v, indent + a.indentation)
        self.file.write(f"{indent}else:\n")
        self.file.write(f"{indent+a.indentation}self._error('syntax error')\n")

    def seq(self, s: Seq, indent: str):
        self.emit(s.car, indent)
        self.emit(s.cdr, indent)

    def rep(self, r: Rep, indent: str):
        indented = indent + r.indentation
        inter = r.val.first.intersection(r.follow)
        if inter:
            self.file.write(f"{indent}# AMBIGUOUS: with lookahead {set_repr(inter)}\n")
        if r.val.nullable:
            self.file.write(f"{indent}# AMBIGUOUS: Nullable Repetition\n")
        self.file.write(
            f"{indent}while self.scanner.peek().kind in {set_repr(r.val.first)}:\n"
        )
        self.emit(r.val, indented)

    def opt(self, o: Opt, indent: str):
        indented = indent + o.indentation
        inter = o.val.first.intersection(o.follow)
        if inter:
            self.file.write(f"{indent}# AMBIGUOUS: with lookahead {set_repr(inter)}\n")
        if o.val.nullable:
            self.file.write(f"{indent}# AMBIGUOUS: Nullable Optional\n")
        self.file.write(
            f"{indent}if self.scanner.peek().kind in {set_repr(o.val.first)}:\n"
        )
        self.emit(o.val, indented)

    def sym(self, s: Sym, indent: str):
        if s.isterminal(self.state):
            self.file.write(f"{indent}self.scanner.match({term_repr(s.value)})\n")
        else:
            self.file.write(f"{indent}self.{s.value}()\n")

    def prod(self, p: Production, indent: str):
        indented = indent * 2
        self.file.write(f"{indent}# {p.lhs} -> {p.rhs.__repr__()}\n")
        self.file.write(f"{indent}def {p.lhs}(self):\n")
        self.emit(p.rhs, indented)

    def emit(self, e: Expr, indent: str):
        if isinstance(e, Alts):
            self.alts(e, indent)
        elif isinstance(e, Seq):
            self.seq(e, indent)
        elif isinstance(e, Rep):
            self.rep(e, indent)
        elif isinstance(e, Opt):
            self.opt(e, indent)
        elif isinstance(e, Sym):
            self.sym(e, indent)
        else:
            raise Exception(f"unknown expr: {e}")

    def emit_parser(self):
        prologue = f"""
from scanner import Scanner
class Parser:
    def __init__(self, scanner: Scanner):
        self.scanner = scanner

    def _error(self, msg: str):
        raise Exception(msg + " at " + str(self.scanner.peek()))

    def _parse(self):
        self.{self.grammar[0].lhs}()
        self.scanner.match("EOF")
"""

        self.file.write(prologue)

        for p in self.grammar:
            self.prod(p, "    ")

        if self.verbose:
            for t in sorted(self.state.terms):
                self.file.write(f"# Token: {t}\n")
