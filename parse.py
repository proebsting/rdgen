from grammar import (
    Production,
    Value,
    Alts,
    Sym,
    Opt,
    Rep,
    Parens,
    Lambda,
    Cons,
    Spec,
    Break,
    Expr,
    Continue,
    OnePlus,
    Sequence,
)

from typing import NoReturn
from scanner import Scanner, Token


class Parser:
    def __init__(self, scanner: Scanner):
        self.scanner: Scanner = scanner

    def error(self, msg: str) -> NoReturn:
        raise Exception(msg + " at " + str(self.scanner.peek()))

    def match(self, kind: str) -> Token:
        if self.current() == kind:
            return self.scanner.consume()
        else:
            self.error(f"expected {kind}")

    def current(self) -> str:
        return self.scanner.peek().kind

    def parse(self):
        v = self._spec()
        self.match("EOF")
        return v

    def _spec(self) -> Spec:
        # spec -> { code }'preamble grammar'g =«Spec(preamble,g)»
        preamble: list[str]
        preamble = []
        while self.current() in {"CODE"}:
            preamble_element_ = self._code()
            preamble.append(preamble_element_)
        g = self._grammar()
        _spec_ = Spec(preamble, g)
        return _spec_

    def _grammar(self) -> list[Production]:
        # grammar -> production'p { production }'prods =«[p]+prods»
        prods: list[Production]
        p = self._production()
        prods = []
        while self.current() in {"ID"}:
            prods_element_ = self._production()
            prods.append(prods_element_)
        _grammar_ = [p] + prods
        return _grammar_

    def _production(self) -> Production:
        # production -> id'lhs ":" alternation'rhs "." =«Production(lhs, rhs)»
        lhs = self._id()
        self.match(":")
        rhs = self._alternation()
        self.match(".")
        _production_ = Production(lhs, rhs)
        return _production_

    def _alternation(self) -> Alts | Sequence:
        # alternation -> sequence'x { "|" =sequence }'seqs =«Alts([x]+seqs) if seqs else x»
        seqs: list[Sequence]
        x = self._sequence()
        seqs = []
        while self.current() in {"|"}:
            self.match("|")
            seqs_element_ = self._sequence()
            seqs.append(seqs_element_)
        _alternation_ = Alts([x] + seqs) if seqs else x
        return _alternation_

    def _sequence(self) -> Sequence:
        # sequence -> term't «ret = last = Cons(t, Lambda())» { term't «last.cdr = Cons(t, last.cdr)» «last = last.cdr» }! =«Sequence(ret)»
        t = self._term()
        ret = last = Cons(t, Lambda())
        while self.current() in {
            "(",
            "=",
            "[",
            "break",
            "continue",
            "{",
            "{+",
            "CODE",
            "ID",
            "STR",
        }:
            t = self._term()
            last.cdr = Cons(t, last.cdr)
            last = last.cdr
        _sequence_ = Sequence(ret)
        return _sequence_

    def _term(self) -> Expr:
        # term -> [ "=" ]'at =base't [ "!" ]'simple [ "'" =id ]'name «t.keep   = at is not None» «t.simple = simple is not None» «t.name   = name or None»
        at = None
        if self.current() in {"="}:
            at = self.match("=")
        t = self._base()
        _term_ = t
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
        return _term_

    def _base(self) -> Expr:
        # base -> "(" alternation'v ")" =«Parens(v)» | "{" alternation'v "}" =«Rep(v)» | "[" alternation'v "]" =«Opt(v)» | "{+" alternation'v "+}" =«OnePlus(v)» | id'id =«Sym(id)» | str's =«Sym(s)» | code'code =«Value(code)» | "break" =«Break()» | "continue" =«Continue()»
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
        elif self.current() in {"ID"}:
            id = self._id()
            _base_ = Sym(id)
        elif self.current() in {"STR"}:
            s = self._str()
            _base_ = Sym(s)
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
            self.error("syntax error")
        return _base_

    def _code(self) -> str:
        # code -> CODE'c =«c.value.strip()»
        c = self.match("CODE")
        _code_ = c.value.strip()
        return _code_

    def _id(self) -> str:
        # id -> ID'id =«id.value»
        id = self.match("ID")
        _id_ = id.value
        return _id_

    def _str(self) -> str:
        # str -> STR'id =«id.value»
        id = self.match("STR")
        _str_ = id.value
        return _str_
