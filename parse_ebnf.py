from scanner import Scanner

from grammar import Production, Alts, Seq, Sym, Opt, Rep, Expr


class Parser:
    def __init__(self, scanner: Scanner):
        self.scanner = scanner

    def _error(self, msg: str):
        raise Exception(msg + " at " + str(self.scanner.peek()))

    def _parse(self):
        self.grammar()

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
        vals = [self.sequence()]
        while self.scanner.peek().kind in {"|"}:
            self.scanner.match("|")
            s = self.sequence()
            vals.append(s)
        if len(vals) == 1:
            return vals[0]
        return Alts(vals)

    # sequence -> term { term }
    def sequence(self) -> Expr:
        ret = self.term()
        while self.scanner.peek().kind in {"ID", "STR", "[", "{", "("}:
            t = self.term()
            ret = Seq(ret, t)
        return ret

    # term -> "(" alternation ")" | "{" alternation "}" | "[" alternation "]" | ID | STR
    def term(self) -> Expr:
        if self.scanner.peek().kind in {"("}:
            self.scanner.match("(")
            v = self.alternation()
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
