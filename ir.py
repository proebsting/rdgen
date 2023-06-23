from typing import Set, List, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class Guard:
    predict: Set[str]


@dataclass
class Decl:
    name: str


class Stmt:
    pass


@dataclass
class Copy(Stmt):
    lhs: str
    rhs: str


def mkCopy(lhs: str, rhs: str) -> Optional[Copy]:
    if lhs == rhs:
        return None
    return Copy(lhs, rhs)


@dataclass
class Sequence(Stmt):
    decls: List[Decl]
    stmts: List[Stmt]


@dataclass
class Terminal(Stmt):
    lhs: Optional[str]
    term: str


@dataclass
class NonTerminal(Stmt):
    lhs: Optional[str]
    nonterm: str


@dataclass
class Loop(Stmt):
    top: Optional[Guard]
    body: List[Stmt]
    bottom: Optional[Guard]


@dataclass
class Guarded:
    guard: Guard
    body: List[Stmt]


@dataclass
class ParseError:
    message: str


@dataclass
class SelectAlternative(Stmt):
    guardeds: List[Guarded]
    error: Optional[ParseError]


@dataclass
class Corn(Stmt):
    value: str


@dataclass
class AssignNull(Stmt):
    lhs: str


@dataclass
class AssignEmptyList(Stmt):
    lhs: str


@dataclass
class AppendToList(Stmt):
    lhs: str
    value: str


class Break(Stmt):
    pass


class Continue(Stmt):
    pass


class Empty(Stmt):
    pass


@dataclass
class Warning(Stmt):
    message: str


@dataclass
class Verbose(Stmt):
    message: str


@dataclass
class Comment(Stmt):
    message: str


@dataclass
class Return(Stmt):
    value: Optional[str]


@dataclass
class Function:
    name: str
    body: List[Stmt]


@dataclass
class Program:
    start_nonterminal: str
    prologue: List[str]
    functions: List[Function]
    pragmas: Dict[str, Any]
