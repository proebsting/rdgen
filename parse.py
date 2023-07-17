from grammar import (
    mkAlts,
    mkSequence,
    Production,
    Infinite,
    Value,
    Alts,
    Sym,
    Opt,
    Rep,
    Parens,
    Spec,
    Break,
    Expr,
    Continue,
    OnePlus,
    Sequence,
)
from scanner import Scanner, Token

from typing import NoReturn, Set
import sys


class ParseErrorException(Exception):
    msg: str
    token: Token
    expected: Set[str]

    def __init__(self, msg: str, token: Token, expected: Set[str]):
        self.msg = msg
        self.token = token
        self.expected = expected

    def __str__(self):
        return f"ParseError: expected {self.expected} at {self.token}"


class Parser:
    def __init__(self, scanner: Scanner, debug: bool = False):
        self.scanner: Scanner = scanner
        self.debug: bool = debug

    def error(self, msg: str, expected: Set[str]) -> NoReturn:
        current: Token = self.scanner.peek()
        complete: str = msg + " at " + str(current)
        print(complete, file=sys.stderr)
        if self.debug:
            raise ParseErrorException(complete, current, expected)
        else:
            sys.exit(1)

    def match(self, kind: str) -> Token:
        if self.current() == kind:
            return self.scanner.consume()
        else:
            self.error(f"expected {kind}", {kind})

    def current(self) -> str:
        return self.scanner.peek().kind

    def parse(self):
        v = self._spec()
        self.match("EOF")
        return v

    def _spec(self) -> Spec:
        # spec -> { code }'preamble grammar'grammar =«Spec(preamble,grammar)»
        _spec_: Spec
        preamble: list[str]
        preamble = []
        while self.current() in {"CODE"}:
            preamble_element_ = self._code()
            preamble.append(preamble_element_)
        grammar = self._grammar()
        _spec_ = Spec(preamble, grammar)
        return _spec_

    def _grammar(self) -> list[Production]:
        # grammar -> {+ production +}
        _grammar_: list[Production]
        _grammar_ = []
        while True:
            _grammar__element_ = self._production()
            _grammar_.append(_grammar__element_)
            if not (self.current() in {"ID"}):
                break
        return _grammar_

    def _production(self) -> Production:
        # production -> id'lhs ":" alternation'rhs "." =«Production(lhs, rhs)»
        _production_: Production
        lhs = self._id()
        self.match(":")
        rhs = self._alternation()
        self.match(".")
        _production_ = Production(lhs, rhs)
        return _production_

    def _alternation(self) -> Alts | Sequence:
        # alternation -> {* =sequence [ break ] "|" *}'seqs =«mkAlts(seqs)»
        _alternation_: Alts | Sequence
        seqs: list[Sequence]
        seqs = []
        while True:
            seqs_element_ = self._sequence()
            seqs.append(seqs_element_)
            if self.current() in {")", "*}", "+}", ".", "]", "}"}:
                break
            self.match("|")
        _alternation_ = mkAlts(seqs)
        return _alternation_

    def _sequence(self) -> Sequence:
        # sequence -> { term }'ts =«mkSequence(ts)»
        _sequence_: Sequence
        ts: list[Expr]
        ts = []
        while self.current() in {
            "(",
            "=",
            "[",
            "break",
            "continue",
            "{",
            "{*",
            "{+",
            "CODE",
            "ID",
            "STR",
        }:
            ts_element_ = self._term()
            ts.append(ts_element_)
        _sequence_ = mkSequence(ts)
        return _sequence_

    def _term(self) -> Expr:
        # term -> [ "=" ]'at base't [ "!" ]'simple [ "'" =id ]'name «t.keep   = at is not None» «t.simple = simple is not None» «t.name   = name or None» =«t»
        _term_: Expr
        at = None
        if self.current() in {"="}:
            at = self.match("=")
        t = self._base()
        simple = None
        if self.current() in {"!"}:
            simple = self.match("!")
        name = None
        if self.current() in {"'"}:
            self.match("'")
            name = self._id()
        t.keep = at is not None
        t.simple = simple is not None
        t.name = name or None
        _term_ = t
        return _term_

    def _base(self) -> Expr:
        # base -> "(" alternation'v ")" =«Parens(v)» | "{" alternation'v "}" =«Rep(v)» | "[" alternation'v "]" =«Opt(v)» | "{+" alternation'v "+}" =«OnePlus(v)» | "{*" alternation'v "*}" =«Infinite(v)» | id'id =«Sym(id)» | string'string =«Sym(string)» | code'code =«Value(code)» | "break" =«Break()» | "continue" =«Continue()»
        _base_: Expr
        if self.current() in {"("}:
            self.match("(")
            v = self._alternation()
            self.match(")")
            _base_ = Parens(v)
        elif self.current() in {"{"}:
            self.match("{")
            v = self._alternation()
            self.match("}")
            _base_ = Rep(v)
        elif self.current() in {"["}:
            self.match("[")
            v = self._alternation()
            self.match("]")
            _base_ = Opt(v)
        elif self.current() in {"{+"}:
            self.match("{+")
            v = self._alternation()
            self.match("+}")
            _base_ = OnePlus(v)
        elif self.current() in {"{*"}:
            self.match("{*")
            v = self._alternation()
            self.match("*}")
            _base_ = Infinite(v)
        elif self.current() in {"ID"}:
            id = self._id()
            _base_ = Sym(id)
        elif self.current() in {"STR"}:
            string = self._string()
            _base_ = Sym(string)
        elif self.current() in {"CODE"}:
            code: str
            code = self._code()
            _base_ = Value(code)
        elif self.current() in {"break"}:
            self.match("break")
            _base_ = Break()
        elif self.current() in {"continue"}:
            self.match("continue")
            _base_ = Continue()
        else:
            self.error(
                "syntax error",
                {
                    '"["',
                    '"break"',
                    '"continue"',
                    '"{+"',
                    "ID",
                    "STR",
                    '"{"',
                    '"("',
                    "CODE",
                    '"{*"',
                },
            )
        return _base_

    def _code(self) -> str:
        # code -> CODE'c =«c.value.strip()»
        _code_: str
        c = self.match("CODE")
        _code_ = c.value.strip()
        return _code_

    def _id(self) -> str:
        # id -> ID'id =«id.value»
        _id_: str
        id = self.match("ID")
        _id_ = id.value
        return _id_

    def _string(self):
        # string -> STR'id =«id.value»
        id = self.match("STR")
        _string_ = id.value
        return _string_
