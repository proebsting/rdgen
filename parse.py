from .grammar import (
    TopCode,
    TopPragma,
    TopLevel,
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
from .scanner import Token

from typing import NoReturn, Iterable, Iterator


class ParseErrorException(Exception):
    msg: str
    token: Token
    expected: set[str]

    def __init__(self, msg: str, current: Token, expected: set[str]):
        self.msg = msg
        self.current = current
        self.expected = expected

    def __str__(self):
        return f"Parse error {self.msg} at {self.current}:  Expected {self.expected}"


class Parser:
    scanner: Iterator[Token]
    _current: Token

    def __init__(
        self,
        scanner: Iterable[Token],
    ):
        self.scanner: Iterator[Token] = iter(scanner)
        self._current = next(self.scanner)

    def error(self, msg: str, expected: set[str]) -> NoReturn:
        raise ParseErrorException(msg, self._current, expected)

    def match(self, kind: str) -> Token:
        if self.current() == kind:
            prev: Token = self._current
            try:
                self._current = next(self.scanner)
            except StopIteration:
                pass
            return prev
        else:
            self.error("", {kind})

    def current(self) -> str:
        return self._current.kind

    def parse(self) -> Spec:
        v: Spec = self._spec()
        self.match("EOF")
        return v

    def _spec(self) -> Spec:
        # spec -> grammar'grammar =«Spec(grammar)»
        _spec_: Spec
        grammar = self._grammar()
        _spec_ = Spec(grammar)
        return _spec_

    def _grammar(self) -> list[TopLevel]:
        # grammar -> { production | code'code =«TopCode(code)» | pragma'pragma =«TopPragma(pragma)» }
        _grammar_: list[TopLevel]
        _grammar_ = []
        while self.current() in {"CODE", "ID", "PRAGMA"}:
            if self.current() in {"ID"}:
                _grammar__element_ = self._production()
                _grammar_.append(_grammar__element_)
            elif self.current() in {"CODE"}:
                code = self._code()
                _grammar__element_ = TopCode(code)
                _grammar_.append(_grammar__element_)
            elif self.current() in {"PRAGMA"}:
                pragma = self._pragma()
                _grammar__element_ = TopPragma(pragma)
                _grammar_.append(_grammar__element_)
            else:
                self.error("syntax error", {"CODE", "ID", "PRAGMA"})
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
                    "(",
                    "[",
                    "break",
                    "continue",
                    "{",
                    "{*",
                    "{+",
                    "CODE",
                    "ID",
                    "STR",
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

    def _pragma(self) -> str:
        # pragma -> PRAGMA'p =«p.value»
        _pragma_: str
        p = self.match("PRAGMA")
        _pragma_ = p.value
        return _pragma_
