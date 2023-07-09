from ir import *
from typing import TextIO
from collections import defaultdict


def term_repr(s: str) -> str:
    return s.replace('"', "").__repr__()


def set_repr(s: set[str]) -> str:
    return "{" + ", ".join(term_repr(w) for w in sorted(s)) + "}"


def mk_guard(guard: Optional[Guard]) -> str:
    if not guard:
        return "True"
    return f"self.current() in {set_repr(guard.predict)}"


class Emitter:
    program: Program
    file: TextIO
    verbose: bool
    prefix: str
    indent: str
    types: Dict[str, Dict[str, str]]
    current: Dict[str, str]

    def __init__(
        self,
        program: Program,
        file: TextIO,
        verbose: bool,
    ) -> None:
        self.program: Program = program
        self.file: TextIO = file
        self.verbose: bool = verbose
        self.prefix = "_"
        self.indent = "    "
        self.process_pragmas()

    def emit_stmts(self, stmts: List[Stmt], indent: str) -> None:
        if not stmts:
            s = f"{indent}pass"
            self.emit(s)
            return
        for s in stmts:
            self.stmt(s, indent)

    def process_pragmas(self) -> None:
        self.types = defaultdict(dict, self.program.pragmas)

    def emit(self, *vals: str) -> None:
        s: str = " ".join(vals)
        print(s, file=self.file)

    def stmt(self, s: Stmt, indent: str) -> None:
        indent1: str = indent + self.indent
        indent2: str = indent + self.indent * 2
        match s:
            case Copy(lhs, rhs):
                assert lhs != rhs
                self.emit(f"{indent}{lhs} = {rhs}")
            case Sequence(decls, stmts):
                cmt: str = ", ".join(d.name for d in decls)
                if self.verbose and cmt:
                    self.emit(f"{indent}# VERBOSE: locals: {cmt}")
                for d in decls:
                    if d.name in self.current:
                        self.emit(f"{indent}{d.name}: {self.current[d.name]}")
                self.emit_stmts(stmts, indent)
            case Terminal(lhs, term):
                tgt: str = f"{lhs} = " if lhs else ""
                self.emit(f"{indent}{tgt}self.match({term_repr(term)})")
            case NonTerminal(lhs, nonterm):
                tgt: str = f"{lhs} = " if lhs else ""
                self.emit(f"{indent}{tgt}self.{self.prefix}{nonterm}()")
            case Loop(top, body, bottom):
                t: str = mk_guard(top)
                b: str = mk_guard(bottom)
                self.emit(f"{indent}while {t}:")
                self.emit_stmts(body, indent1)
                if bottom:
                    self.emit(f"{indent1}if not ({b}):")
                    self.emit(f"{indent2}break")
            case SelectAlternative(guardeds, error):
                test = "if"
                for g in guardeds:
                    self.emit(f"{indent}{test} {mk_guard(g.guard)}:")
                    test = "elif"
                    self.emit_stmts(g.body, indent1)
                if error:
                    self.emit(f"{indent}else:")
                    self.emit(
                        f"{indent1}self.error({term_repr(error.message)})"
                    )
            case Corn(value):
                self.emit(f"{indent}{value}")
            case Break():
                self.emit(f"{indent}break")
            case Continue():
                self.emit(f"{indent}continue")
            case Empty():
                pass
            case AssignNull(lhs):
                self.emit(f"{indent}{lhs} = None")
            case AssignEmptyList(lhs):
                self.emit(f"{indent}{lhs} = []")
            case AppendToList(lhs, value):
                self.emit(f"{indent}{lhs}.append({value})")
            case Return(value):
                self.emit(f"{indent}return {value}")
            case Warning(message):
                self.emit(f"{indent}# WARNING: {message}")
            case Comment(message):
                self.emit(f"{indent}# {message}")
            case Verbose(message):
                if self.verbose:
                    self.emit(f"{indent}# VERBOSE: {message}")
            case _:
                raise Exception(f"unhandled statement {s}")

    def function(self, f: Function) -> None:
        rettype: str = (
            self.types[f.name]["return"]
            if "return" in self.types[f.name]
            else ""
        )
        retdecl: str = f"->{rettype}" if rettype else ""
        self.emit(f"{self.indent}def {self.prefix}{f.name}(self){retdecl}:")
        self.current = self.types[f.name]
        if rettype:
            self.emit(f"{self.indent * 2}_{f.name}_: {rettype}")
        self.emit_stmts(f.body, self.indent * 2)
        self.emit()

    def emit_program(self) -> None:
        prologue: str = f"""
from typing import NoReturn
from scanner import Scanner, Token
import sys
class Parser:
    def __init__(self, scanner:Scanner, debug:bool=False):
        self.scanner:Scanner = scanner
        self.debug:bool = debug

    def error(self, msg: str)->NoReturn:
        complete:str = msg + " at " + str(self.scanner.peek())
        print(complete, file=sys.stderr)
        if self.debug:
            raise Exception(complete)
        else:
            sys.exit(1)

    def match(self, kind: str)->Token:
        if self.current() == kind:
            return self.scanner.consume()
        else:
            self.error(f"expected {{kind}}")

    def current(self)->str:
        return self.scanner.peek().kind

    def parse(self):
        v = self.{self.prefix}{self.program.start_nonterminal}()
        self.match("EOF")
        return v
"""

        for p in self.program.prologue:
            self.emit(p)

        self.emit(prologue)

        for f in self.program.functions:
            self.function(f)
