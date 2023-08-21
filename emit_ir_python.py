from .ir import *
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
                    all: set[str] = set(
                        x for g in guardeds for x in g.guard.predict
                    )
                    self.emit(f"{indent}else:")
                    self.emit(
                        f"{indent1}self.error({repr(error.message)}, {set_repr(all)})"
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
            tname = f"_{f.name}_"
            # self.emit(f"{self.indent * 2}{tname}: {rettype}")
            if not tname in self.types[f.name]:
                self.types[f.name][tname] = rettype
        self.emit_stmts(f.body, self.indent * 2)
        self.emit()

    def emit_program(self) -> None:
        prologue: str = f"""
from typing import NoReturn, Iterable, Iterator

class ParseErrorException(Exception):
    msg: str
    token: Token
    expected: set[str]

    def __init__(self, msg: str, current: Token, expected: set[str]):
        self.msg = msg
        self.current = current
        self.expected = expected

    def __str__(self) -> str:
        return f"Parse error {{self.msg}} at {{self.current}}:  Expected {{self.expected}}"



class Parser:
    scanner:Iterator[Token]
    _current:Token

    def __init__(
        self,
        scanner: Iterable[Token],
    ):
        self.scanner: Iterator[Token] = iter(scanner)
        self._current = next(self.scanner)
    

    def error(self, msg: str, expected: set[str]) -> NoReturn:
        raise ParseErrorException(msg, self._current, expected)

    def match(self, kind: str)->Token:
        if self.current() == kind:
            prev: Token = self._current
            try:
                self._current = next(self.scanner)
            except StopIteration:
                pass
            return prev
        else:
            self.error("", {{kind}})

    def current(self)->str:
        return self._current.kind

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
