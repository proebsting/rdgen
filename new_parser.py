from grammar import (
    Production,
    Alts,
    Seq,
    Sym,
    Opt,
    Rep,
    Expr,
    Parens,
    Lambda,
    Cons,
    Spec,
)

from scanner import Scanner


class Parser:
    def __init__(self, scanner: Scanner):
        self.scanner = scanner

    def error(self, msg: str):
        raise Exception(msg + " at " + str(self.scanner.peek()))

    def match(self, kind: str):
        if self.current() == kind:
            return self.scanner.consume()
        else:
            self.error(f"expected {kind}")

    def current(self):
        return self.scanner.peek().kind

    def parse(self):
        v = self._spec()
        self.match("EOF")
        return v

    # spec -> { code } grammar
    def _spec(self):
        preamble = []
        while self.current() in {"CODE"}:
            _tmp_preamble_4340530192 = self._code()
            preamble.append(_tmp_preamble_4340530192)
        g = self._grammar()
        _spec_ = Spec(preamble, g)
        return _spec_

    # grammar -> production { production }
    def _grammar(self):
        p = self._production()
        L = []
        while self.current() in {"ID"}:
            _tmp_L_4340531056 = self._production()
            L.append(_tmp_L_4340531056)
        _grammar_ = [p] + L
        return _grammar_

    # production -> id ":" alternation "."
    def _production(self):
        lhs = self._id()
        self.match(":")
        rhs = self._alternation()
        self.match(".")
        _production_ = Production(lhs, rhs)
        return _production_

    # alternation -> sequence { "|" sequence }
    def _alternation(self):
        x = self._sequence()
        L = []
        while self.current() in {"|"}:
            self.match("|")
            _tmp_L_4340527600 = self._sequence()
            L.append(_tmp_L_4340527600)
        _alternation_ = Alts([x] + L) if L else x
        return _alternation_

    # sequence -> { code } term { term } [ "=" code ]
    def _sequence(self):
        prologue = []
        while self.current() in {"CODE"}:
            _tmp_prologue_4340527888 = self._code()
            prologue.append(_tmp_prologue_4340527888)
        t = self._term()
        ret = last = Cons(t, Lambda())
        ret.prologue = prologue
        while self.current() in {"(", "@", "[", "{", "ID", "STR"}:
            t = self._term()
            last.cdr = Cons(t, last.cdr)
            last = last.cdr
        code = None
        if self.current() in {"="}:
            self.match("=")
            code = self._code()
        ret.code = code or None
        _sequence_ = ret
        return _sequence_

    # term -> [ "@" ] base [ "!" ] [ "'" id ] { code }
    def _term(self):
        at = None
        if self.current() in {"@"}:
            at = self.match("@")
        t = self._base()
        simple = None
        if self.current() in {"!"}:
            simple = self.match("!")
        name = None
        if self.current() in {"'"}:
            self.match("'")
            name = self._id()
        stmts = []
        while self.current() in {"CODE"}:
            _tmp_stmts_4340812288 = self._code()
            stmts.append(_tmp_stmts_4340812288)
        t.keep = at is not None
        t.simple = simple is not None
        t.name = name or None
        t.stmts = stmts
        _term_ = t
        return _term_

    # base -> "(" alternation ")" | "{" alternation "}" | "[" alternation "]" | id | str
    def _base(self):
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
        elif self.current() in {"ID"}:
            id = self._id()
            _base_ = Sym(id)
        elif self.current() in {"STR"}:
            s = self._str()
            _base_ = Sym(s)
        else:
            self.error("syntax error")
            assert False
        return _base_

    # code -> CODE
    def _code(self):
        c = self.match("CODE")
        _code_ = c.value.strip()
        return _code_

    # id -> ID
    def _id(self):
        id = self.match("ID")
        _id_ = id.value
        return _id_

    # str -> STR
    def _str(self):
        id = self.match("STR")
        _str_ = id.value
        return _str_
