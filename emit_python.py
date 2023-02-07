from collections import defaultdict

from typing import TextIO, List, Dict, Set, Tuple

from grammar import (
    Alts,
    Rep,
    Opt,
    Sym,
    Production,
    State,
    Expr,
    Parens,
    Lambda,
    Cons,
    Spec,
)


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

    def epilogue(self, x, indent: str):
        for stmt in x.stmts:
            self.file.write(f"{indent}{stmt}\n")
        if x.name and x.target:
            self.file.write(f"{indent}{x.target} = {x.name}")

    def alts(self, x: Alts, indent: str):
        assert x.name is None
        if self.verbose:
            self.file.write(x.dump0(indent, "# Alts:") + "\n")
        cond = "if"
        counted = defaultdict(int)
        for v in x.vals:
            for t in v.predict:
                counted[t] += 1

        for v in x.vals:
            ambiguous = {t for t in v.predict if counted[t] > 1}
            if ambiguous:
                print(f"{indent}# AMBIGUOUS lookahead(s): {ambiguous}")
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
        if x.prologue:
            self.file.write(f"{indent}{x.prologue}\n")
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
            print(f"{indent}# AMBIGUOUS lookahead(s): {ambiguous}")
        if x.name and not x.simple:
            self.file.write(f"{indent}{x.name} = []\n")
        vs = set_repr(x.val.first)
        self.file.write(f"{indent}while self.current() in {vs}:\n")
        indented = indent + x.indentation
        self.emit(x.val, indented)
        if x.name and not x.simple:
            self.file.write(f"{indented}{x.name}.append({x.element})\n")
        self.epilogue(x, indent)

    def opt(self, x: Opt, indent: str):
        ambiguous = x.val.predict.intersection(x.follow)
        if ambiguous:
            print(f"{indent}# AMBIGUOUS lookahead(s): {ambiguous}")
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
        if x.isterminal(self.state):
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
        else:
            raise Exception(f"unknown expr: {e}")

    def prod(self, p: Production, indent: str, state: State):
        indented = indent * 2
        self.file.write(f"{indent}# {p.lhs} -> {p.rhs.__repr__()}\n")
        if self.verbose:
            self.file.write(
                f"{indent}# {p.lhs}: nullable {state.nullable[p.lhs]}, first {state.first[p.lhs]}, follow {state.follow[p.lhs]}\n"
            )
        self.file.write(f"{indent}def {self.prefix}{p.lhs}(self):\n")
        var = f"_{p.lhs}_"
        self.emit(p.rhs, indented)
        self.file.write(f"{indented}return {var}\n")

    def emit_parser(self, state):
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
