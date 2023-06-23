from collections import defaultdict

from typing import TextIO, Dict

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
)

from analysis import State


def term_repr(s: str) -> str:
    return s.replace('"', "").__repr__()


def set_repr(s: set[str]) -> str:
    return "{" + ", ".join(term_repr(w) for w in sorted(s)) + "}"


class Emitter:
    def __init__(
        self,
        spec: Spec,
        state: State,
        file: TextIO,
        verbose: bool,
    ):
        self.spec = spec
        self.state = state
        self.file = file
        self.verbose = verbose
        self.prefix = "_"

    def epilogue(self, x: Expr, indent: str) -> None:
        for stmt in x.stmts:
            self.file.write(f"{indent}{stmt}\n")
        if x.name and x.target:
            self.file.write(f"{indent}{x.target} = {x.name}")

    def alts(self, x: Alts, indent: str):
        assert x.name is None
        if self.verbose:
            self.file.write(x.dump0(indent, "# Alts:") + "\n")
        cond = "if"
        counted: Dict[str, int] = defaultdict(int)
        for v in x.vals:
            for t in v.predict:
                counted[t] += 1

        for v in x.vals:
            ambiguous = {t for t in v.predict if counted[t] > 1}
            if ambiguous:
                self.file.write(
                    f"{indent}# AMBIGUOUS lookahead(s): {ambiguous}\n"
                )
            self.file.write(
                f"{indent}{cond} self.current() in {set_repr(v.predict)}:\n"
            )
            self.emit(v, indent + x.indentation)
            cond = "elif"
        self.file.write(f"{indent}else:\n")
        self.file.write(f"{indent+x.indentation}self.error('syntax error')\n")
        self.file.write(f"{indent+x.indentation}assert False\n")
        self.epilogue(x, indent)

    def cons(self, x: Cons, indent: str):
        assert x.name is None
        if self.verbose:
            self.file.write(x.dump0(indent, "# Cons:") + "\n")
        for stmt in x.prologue:
            self.file.write(f"{indent}{stmt}\n")
        self.emit(x.car, indent)
        self.emit(x.cdr, indent)
        if x.target:
            tgt = x.target
        else:
            tgt = "_"
        if x.code:
            self.file.write(f"{indent}{tgt} = {x.code}\n")
        elif x.at_term:
            if x.at_term != tgt:
                self.file.write(f"{indent}{tgt} = {x.at_term}\n")
        elif x.tuple:
            vs = ", ".join(x.tuple)
            self.file.write(f"{indent}{tgt} = ({vs})\n")
        elif x.dict:
            vs = ", ".join([f'"{n}" : {n}' for n in x.dict])
            self.file.write(f"{indent}{tgt} = {{ {vs} }}\n")
        elif x.singleton:
            if x.singleton != tgt:
                self.file.write(f"{indent}{tgt} = {x.singleton}\n")
        elif x.target:
            self.file.write(f"{indent}{tgt} = None # default?\n")

    def rep(self, x: Rep, indent: str):
        ambiguous = x.val.predict.intersection(x.follow)
        if ambiguous:
            self.file.write(f"{indent}# AMBIGUOUS lookahead(s): {ambiguous}\n")
        if x.name and not x.simple:
            self.file.write(f"{indent}{x.name} = []\n")
        vs = set_repr(x.val.first)
        self.file.write(f"{indent}while self.current() in {vs}:\n")
        indented = indent + x.indentation
        self.emit(x.val, indented)
        if x.name and not x.simple:
            self.file.write(f"{indented}{x.name}.append({x.element})\n")
        self.epilogue(x, indent)

    def oneplus(self, x: OnePlus, indent: str):
        ambiguous = x.val.predict.intersection(x.follow)
        if ambiguous:
            self.file.write(f"{indent}# AMBIGUOUS lookahead(s): {ambiguous}\n")
        if x.name and not x.simple:
            self.file.write(f"{indent}{x.name} = []\n")
        vs = set_repr(x.val.first)
        self.file.write(f"{indent}while True:\n")
        indented = indent + x.indentation
        self.emit(x.val, indented)
        if x.name and not x.simple:
            self.file.write(f"{indented}{x.name}.append({x.element})\n")
        self.file.write(f"{indent}if self.current() not in {vs}:\n")
        self.file.write(f"{indented}break\n")
        self.epilogue(x, indent)

    def _break(self, x: Break, indent: str):
        if self.verbose:
            self.file.write(x.dump0(indent, "# Break:") + "\n")
        self.file.write(f"{indent}break\n")

    def _continue(self, x: Continue, indent: str):
        if self.verbose:
            self.file.write(x.dump0(indent, "# Continue:") + "\n")
        self.file.write(f"{indent}continue\n")

    def opt(self, x: Opt, indent: str):
        ambiguous = x.val.predict.intersection(x.follow)
        if ambiguous:
            self.file.write(f"{indent}# AMBIGUOUS lookahead(s): {ambiguous}\n")
        if self.verbose:
            self.file.write(x.dump0(indent, "# Opt:") + "\n")
        if x.name and not x.simple:
            self.file.write(f"{indent}{x.name} = None\n")
        vs = set_repr(x.val.first)
        self.file.write(f"{indent}if self.current() in {vs}:\n")
        self.emit(x.val, indent + x.indentation)
        self.epilogue(x, indent)

    def sym(self, x: Sym, indent: str):
        if self.verbose:
            self.file.write(x.dump0(indent, "# Sym:") + "\n")
        tgt = f"{x.name} = " if x.name else ""
        if x.value in self.state.terms:
            cmd = f"{tgt}self.match({term_repr(x.value)})"
        else:
            cmd = f"{tgt}self.{self.prefix}{x.value}()"
        self.file.write(f"{indent}{cmd}\n")
        self.epilogue(x, indent)

    def parens(self, x: Parens, indent: str):
        self.emit(x.e, indent)
        self.epilogue(x, indent)

    def emit(self, e: Expr, indent: str):
        if isinstance(e, Alts):
            self.alts(e, indent)
        elif isinstance(e, Cons):
            self.cons(e, indent)
        elif isinstance(e, Rep):
            self.rep(e, indent)
        elif isinstance(e, Opt):
            self.opt(e, indent)
        elif isinstance(e, Sym):
            self.sym(e, indent)
        elif isinstance(e, Parens):
            self.parens(e, indent)
        elif isinstance(e, Lambda):
            pass
        elif isinstance(e, Break):
            self._break(e, indent)
        elif isinstance(e, Continue):
            self._continue(e, indent)
        elif isinstance(e, OnePlus):
            self.oneplus(e, indent)
        else:
            raise Exception(f"unknown expr: {e}")

    def prod(self, p: Production, indent: str, state: State) -> None:
        indented = indent * 2
        self.file.write(f"{indent}# {p.lhs} -> {p.rhs.__repr__()}\n")
        if self.verbose:
            self.file.write(
                f"{indent}# {p.lhs}: nullable {state.syms_nullable[p.lhs].get_value()}, first {state.syms_first[p.lhs].get_value()}, follow {state.syms_follow[p.lhs].get_value()}\n"
            )
        self.file.write(f"{indent}def {self.prefix}{p.lhs}(self):\n")
        var = f"_{p.lhs}_"
        self.emit(p.rhs, indented)
        self.file.write(f"{indented}return {var}\n")

    def emit_parser(self, state: State):
        prologue = f"""
class Parser:
    def __init__(self, scanner):
        self.scanner = scanner

    def error(self, msg: str):
        raise Exception(msg + " at " + str(self.scanner.peek()))

    def match(self, kind: str):
        if self.current() == kind:
            return self.scanner.consume()
        else:
            self.error(f"expected {{kind}}")

    def current(self):
        return self.scanner.peek().kind

    def parse(self):
        v = self.{self.prefix}{self.spec.productions[0].lhs}()
        self.match("EOF")
        return v
"""

        for s in self.spec.preamble:
            self.file.write(s + "\n")

        self.file.write(prologue)

        for p in self.spec.productions:
            self.prod(p, "    ", state)

        if self.verbose:
            for t in sorted(self.state.terms):
                self.file.write(f"# Token: {t}\n")
