from typing import List

from scanner import Scanner

from grammar import (
    Production,
    Alts,
    Sym,
    Opt,
    Rep,
    Expr,
    Parens,
    Lambda,
    Cons,
    Spec,
)


class Parser:
    def __init__(self, scanner: Scanner):
        self.scanner = scanner

    def _error(self, msg: str):
        raise Exception(msg + " at " + str(self.scanner.peek()))

    def parse(self) -> Spec:
        s = self.spec()
        self.scanner.match("EOF")
        return s

    def spec(self) -> Spec:
        preamble: List[str] = []
        while self.scanner.peek().kind in {"CODE"}:
            tmp = self.scanner.match("CODE")
            preamble.append(tmp.value.strip())
        g: list[Production] = self.grammar()
        _spec_: Spec = Spec(preamble, g)
        return _spec_

    # grammar -> production { production }
    def grammar(self) -> list[Production]:
        prods = [self.production()]
        while self.scanner.peek().kind in {"ID"}:
            p = self.production()
            prods.append(p)
        return prods

    # production -> ID ":" alternation "."
    def production(self) -> Production:
        lhs = self.scanner.match("ID")
        self.scanner.match(":")
        rhs = self.alternation()
        self.scanner.match(".")
        return Production(lhs.value, rhs)

    # alternation -> sequence { "|" sequence }
    def alternation(self) -> Expr:
        vals: list[Cons] = [self.sequence()]
        while self.scanner.peek().kind in {"|"}:
            self.scanner.match("|")
            s = self.sequence()
            vals.append(s)
        if len(vals) == 1:
            return vals[0]
        return Alts(vals)

    # sequence -> term { term }
    def sequence(self) -> Cons:
        prologue: List[str] = []
        while self.scanner.peek().kind in {"CODE"}:
            tok = self.scanner.match("CODE")
            prologue.append(tok.value.strip())
        t = self.term()
        ret = Cons(t, Lambda())
        ret.prologue = prologue
        last = ret
        while self.scanner.peek().kind in {"ID", "STR", "[", "{", "(", "@"}:
            t = self.term()
            s = Cons(t, Lambda())
            last.cdr = s
            last = s
        if self.scanner.peek().kind in {"="}:
            self.scanner.match("=")
            tok = self.scanner.match("CODE")
            ret.code = tok.value.strip()
        return ret

    # term -> [ "@" ] "(" alternation ")" | "{" alternation "}" | "[" alternation "]" | ID | STR
    def term(self) -> Expr:
        flag: bool = False
        if self.scanner.peek().kind in {"@"}:  # @ is a prefix
            self.scanner.match("@")
            flag = True
        if self.scanner.peek().kind in {"("}:
            self.scanner.match("(")
            v = Parens(self.alternation())
            self.scanner.match(")")
        elif self.scanner.peek().kind in {"{"}:
            self.scanner.match("{")
            v = Rep(self.alternation())
            self.scanner.match("}")
        elif self.scanner.peek().kind in {"["}:
            self.scanner.match("[")
            v = Opt(self.alternation())
            self.scanner.match("]")
        elif self.scanner.peek().kind in {"ID"}:
            v = Sym(self.scanner.match("ID").value)
        elif self.scanner.peek().kind in {"STR"}:
            v = Sym(self.scanner.match("STR").value)
        else:
            self._error("syntax error")
            assert False
        if self.scanner.peek().kind in {"!"}:
            self.scanner.match("!")
            v.simple = True
        if self.scanner.peek().kind in {"'"}:
            self.scanner.match("'")
            tok = self.scanner.match("ID")
            v.name = tok.value
        stmts: List[str] = []
        while self.scanner.peek().kind in {"CODE"}:
            tok = self.scanner.match("CODE")
            stmts.append(tok.value.strip())
        v.stmts = stmts
        v.keep = flag
        return v


# Token: ID
# Token: STR
# Token: ")"
# Token: "["
# Token: "|"
# Token: ":"
# Token: "}"
# Token: "]"
# Token: "{"
# Token: "("
