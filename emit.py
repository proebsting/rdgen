from typing import TextIO, Optional, List

from grammar import (
    Alts,
    Seq,
    Rep,
    Opt,
    Sym,
    Production,
    Expr,
    Parens,
    Lambda,
    Cons,
)

from analysis import State


def term_repr(s: str) -> str:
    return s.replace('"', "").__repr__()


def set_repr(s: set[str]) -> str:
    return "{" + ", ".join(term_repr(w) for w in sorted(s)) + "}"


def lhs(L: List[str]) -> str:
    return " = ".join(L)


class Emitter:
    def __init__(
        self,
        grammar: list[Production],
        state: State,
        file: TextIO,
        verbose: bool,
    ):
        self.grammar = grammar
        self.state = state
        self.file = file
        self.verbose = verbose
        self.prefix = "_"

    def alts(self, x: Alts, indent: str, target: Optional[str]):
        assert x.name is None
        if self.verbose:
            self.file.write(x.dump0(indent, "# Alts:") + "\n")
        for i, v in enumerate(x.vals):
            # TODO: warn about ambiguous lookahead
            if i == 0:
                cond = "if"
            else:
                cond = "elif"
            self.file.write(
                f"{indent}{cond} self.scanner.peek().kind in {set_repr(v.predict)}:\n"
            )
            self.emit(v, indent + x.indentation, target)
        self.file.write(f"{indent}else:\n")
        self.file.write(f"{indent+x.indentation}self.error('syntax error')\n")
        for stmt in x.stmts:
            self.file.write(f"{indent}{stmt}\n")

    def cons(self, x: Cons, indent: str, target: Optional[str]):
        assert x.name is None
        if self.verbose:
            self.file.write(x.dump0(indent, "# Cons:") + f" {target}\n")
        if x.prologue:
            self.file.write(f"{indent}{x.prologue}\n")
        assign: str | None = self.create_assignment(x, indent, target)
        self.emit(x.car, indent, None)
        self.emit(x.cdr, indent, None)
        if assign:
            self.file.write(assign)

    # in order, the value of a sequence is
    # 1. whatever =<<code>> produces
    # 2. the single @term
    # 3. a tuple of multiple @terms
    # 4. a dictionary of all the named terms
    # 5. the value of the singleton term
    # 6. None
    def create_assignment(
        self, x: Cons, indent: str, target: Optional[str]
    ) -> str | None:
        """this has side effects!"""
        assign: Optional[str] = None
        if target:
            if x.code is not None:
                assign = f"{indent}{target} = {x.code}\n"
            else:
                p: Seq = x
                names: List[str] = []
                keeps: List[Expr] = []
                while isinstance(p, Cons):
                    if p.car.name:
                        names.append(p.car.name)
                    if p.car.keep:
                        keeps.append(p.car)
                    p = p.cdr
                if len(keeps) > 0:
                    if len(keeps) == 1:
                        k = keeps[0]
                        if k.name:
                            assign = f"{indent}{target} = {k.name}\n"
                        else:
                            k.name = target
                    else:
                        knames: List[str] = []
                        for i, k in enumerate(keeps):
                            if not k.name:
                                k.name = f"_tmp{i}"  # must fix
                            knames.append(k.name)
                        vs = ", ".join(knames)
                        assign = f"{indent}{target} = ({vs})\n"
                elif len(names) > 0:
                    vs = ", ".join([f'"{n}" : {n}' for n in names])
                    assign = f"{indent}{target} = {{ {vs} }}\n"
                elif isinstance(x.cdr, Lambda):
                    assert x.car.name is None
                    x.car.name = target
                else:
                    assign = f"{indent}{target} = None # No indication of what to do!!!!!!\n"
        else:
            if x.code is not None:
                assign = f"{indent}_ = {x.code} # For side-effects???\n"
        return assign

    def rep(self, x: Rep, indent: str, target: Optional[str]):
        # TODO: warn about ambiguous lookahead
        if self.verbose:
            self.file.write(x.dump0(indent, "# Rep:") + "\n")
        if x.name:
            tgt = x.name
        else:
            tgt = target
        if tgt and not x.simple:
            self.file.write(f"{indent}{tgt} = []\n")
        self.file.write(
            f"{indent}while self.scanner.peek().kind in {set_repr(x.val.first)}:\n"
        )
        indented = indent + x.indentation
        if x.simple:
            self.emit(x.val, indented, tgt)
        else:
            tmp = "tmp"
            self.emit(x.val, indented, tmp)
            if tgt:
                self.file.write(f"{indented}{tgt}.append({tmp})\n")
        for stmt in x.stmts:
            self.file.write(f"{indent}{stmt}\n")
        if x.name and target:
            self.file.write(f"{indent}{target} = {x.name}")

    def opt(self, x: Opt, indent: str, target: Optional[str]):
        # TODO: warn about ambiguous lookahead
        if self.verbose:
            self.file.write(x.dump0(indent, "# Opt:") + "\n")
        if x.name:
            tgt = x.name
        else:
            tgt = target
        if tgt and not x.simple:
            self.file.write(f"{indent}{tgt} = None\n")
        self.file.write(
            f"{indent}if self.scanner.peek().kind in {set_repr(x.val.first)}:\n"
        )
        indented = indent + x.indentation
        self.emit(x.val, indented, tgt)
        for stmt in x.stmts:
            self.file.write(f"{indent}{stmt}\n")
        if x.name and target:
            self.file.write(f"{indent}{target} = {x.name}")

    def sym(self, x: Sym, indent: str, target: Optional[str]):
        if self.verbose:
            self.file.write(x.dump0(indent, "# Sym:") + "\n")
        tgt = ""
        if x.name:
            tgt = f"{x.name} = "
        elif target:
            tgt = f"{target} = "

        if x.value in self.state.terms:
            cmd = f"{tgt}self.match({term_repr(x.value)})"
        else:
            cmd = f"{tgt}self.{self.prefix}{x.value}()"
        self.file.write(f"{indent}{cmd}\n")
        for stmt in x.stmts:
            self.file.write(f"{indent}{stmt}\n")
        if x.name and target:
            self.file.write(f"{indent}{target} = {x.name}")

    def parens(self, x: Parens, indent: str, target: Optional[str]):
        if x.name:
            tgt = x.name
        else:
            tgt = target
        self.emit(x.e, indent, tgt)
        for stmt in x.stmts:
            self.file.write(f"{indent}{stmt}\n")
        if x.name and target:
            self.file.write(f"{indent}{target} = {x.name}")

    def prod(self, p: Production, indent: str, state: State):
        indented = indent * 2
        self.file.write(f"{indent}# {p.lhs} -> {p.rhs.__repr__()}\n")
        if self.verbose:
            self.file.write(
                f"{indent}# {p.lhs}: nullable {state.syms_nullable[p.lhs]}, first {state.syms_first[p.lhs]}, follow {state.syms_follow[p.lhs]}\n"
            )
        self.file.write(f"{indent}def {self.prefix}{p.lhs}(self):\n")
        var = f"_{p.lhs}_"
        self.emit(p.rhs, indented, var)
        self.file.write(f"{indented}return {var}\n")

    def emit(self, e: Expr, indent: str, target: Optional[str]):
        if isinstance(e, Alts):
            self.alts(e, indent, target)
        elif isinstance(e, Cons):
            self.cons(e, indent, target)
        elif isinstance(e, Rep):
            self.rep(e, indent, target)
        elif isinstance(e, Opt):
            self.opt(e, indent, target)
        elif isinstance(e, Sym):
            self.sym(e, indent, target)
        elif isinstance(e, Parens):
            self.parens(e, indent, target)
        elif isinstance(e, Lambda):
            pass
        else:
            raise Exception(f"unknown expr: {e}")

    def emit_parser(self, state: State):
        prologue = f"""
class Parser:
    def __init__(self, scanner):
        self.scanner = scanner

    def error(self, msg: str):
        raise Exception(msg + " at " + str(self.scanner.peek()))

    def match(self, kind: str):
        return self.scanner.match(kind)

    def parse(self):
        self.{self.prefix}{self.grammar[0].lhs}()
        self.scanner.match("EOF")
"""

        self.file.write(prologue)

        for p in self.grammar:
            self.prod(p, "    ", state)

        if self.verbose:
            for t in sorted(self.state.terms):
                self.file.write(f"# Token: {t}\n")
