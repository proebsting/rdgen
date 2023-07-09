from typing import Optional, List, Callable, Any, Set

# from analysis import State


class Expr:
    indentation: str = "    "
    first: set[str] = set()
    nullable: bool = False
    follow: set[str] = set()
    predict: set[str]

    # code generation directives
    name: Optional[str] = None
    keep: bool = False
    simple: bool = False

    keep0: bool = False  # default keep

    # inherited target for computed value
    target: Optional[str] = None

    def visit(
        self,
        pre: Callable[["Expr", Any], None],
        post: Callable[["Expr", Any], None],
        arg: Any,
    ) -> None:
        raise NotImplementedError(
            f"{self.__class__.__name__}.visit() not implemented"
        )

    def __repr__(self) -> str:
        s = self.basic_repr()
        return self.decorate(s)

    def basic_repr(self) -> str:
        assert False, (
            "Expr.basic_repr() not implemented for " + self.__class__.__name__
        )

    def dump(self, indent: str) -> None:
        assert False, (
            "Expr.dump() not implemented for " + self.__class__.__name__
        )

    def decorate(self, s: str) -> str:
        if self.keep:
            s = f"={s}"
        if self.simple:
            s = f"{s}!"
        if self.name:
            s = f"{s}'{self.name}"
        return s

    def nameOf(self) -> str:
        return self.__class__.__name__

    def dump0(self) -> str:
        name = self.nameOf()
        s = f"{name}: nullable: {self.nullable} first: {self.first} follow: {self.follow} predict: {self.predict}"
        if self.name:
            s += f" name: {self.name}"
        if self.keep:
            s += f" keep: {self.keep}"
        # if isinstance(self, Sequence):
        #     if self.code:
        #         s += f" code: {self.code}"
        return s

    def dump_flat(self, indent: str):
        if isinstance(self, Cons):
            self.car.dump_flat(indent)
            self.cdr.dump_flat(indent)
        else:
            self.dump(indent)


class Seq0(Expr):
    pass


class Sequence(Expr):
    def __init__(self, seq: "Cons") -> None:
        self.seq: Cons = seq

        # possible inferred values for the sequence
        self.at_term: Optional[str] = None
        self.tuple: Optional[List[str]] = None
        self.dict: Optional[List[str]] = None
        self.singleton: Optional[str] = None

    def visit(
        self,
        pre: Callable[[Expr, Any], None],
        post: Callable[[Expr, Any], None],
        arg: Any = None,
    ) -> None:
        pre(self, arg)
        self.seq.visit(pre, post, arg)
        post(self, arg)

    def basic_repr(self):
        L: list[str] = []
        repr_seq(self.seq, L)
        return " ".join(L)

    def dump(self, indent: str) -> None:
        self.seq.dump(indent)

    def filter(self, f: Callable[["Cons"], bool]) -> List["Cons"]:
        s = self
        L: List[Cons] = []
        while isinstance(s, Cons):
            if f(s):
                L.append(s)
            s = s.cdr
        return L


class Lambda(Seq0):
    def __init__(self):
        pass

    def visit(
        self,
        pre: Callable[[Expr, Any], None],
        post: Callable[[Expr, Any], None],
        arg: Any = None,
    ) -> None:
        pre(self, arg)
        post(self, arg)

    def basic_repr(self) -> str:
        return ""

    def dump(self, indent: str) -> None:
        # print(self.dump0(indent, "Lambda"))
        pass


class Parens(Expr):
    def __init__(self, e: Expr):
        self.e = e

    def visit(
        self,
        pre: Callable[[Expr, Any], None],
        post: Callable[[Expr, Any], None],
        arg: Any = None,
    ) -> None:
        pre(self, arg)
        self.e.visit(pre, post, arg)
        post(self, arg)

    def basic_repr(self):
        return f"({self.e.__repr__()})"

    def dump(self, indent: str):
        print(indent, self.dump0())
        self.e.dump(indent + "  ")


class Alts(Expr):
    def __init__(self, vals: list["Sequence"]):
        self.vals: List["Sequence"] = vals
        self.warnings: list[str | None]

    def visit(
        self,
        pre: Callable[[Expr, Any], None],
        post: Callable[[Expr, Any], None],
        arg: Any = None,
    ):
        pre(self, arg)
        for v in self.vals:
            v.visit(pre, post, arg)
        post(self, arg)

    def basic_repr(self):
        return f'{" | ".join(repr(v) for v in self.vals)}'

    def dump(self, indent: str):
        print(indent, self.dump0())
        for i, v in enumerate(self.vals):
            print(f"{indent}#{i}:")
            v.dump(indent + "  ")


def repr_seq(e: Expr, lis: list[str]):
    if isinstance(e, Cons):
        repr_seq(e.car, lis)
        repr_seq(e.cdr, lis)
    elif isinstance(e, Lambda):
        pass
    # elif isinstance(e, Alts):
    #     L.append(f"( {repr(e)} )")
    else:
        lis.append(e.__repr__())


class Cons(Seq0):
    dict: Optional[List[str]]

    def __init__(self, car: Expr, cdr: Seq0):
        self.car: Expr = car
        self.cdr: Seq0 = cdr

    def visit(
        self,
        pre: Callable[[Expr, Any], None],
        post: Callable[[Expr, Any], None],
        arg: Any = None,
    ):
        pre(self, arg)
        self.car.visit(pre, post, arg)
        self.cdr.visit(pre, post, arg)
        post(self, arg)

    def basic_repr(self):
        L: list[str] = []
        repr_seq(self, L)
        return " ".join(L)

    def dump(self, indent: str):
        print(indent, self.dump0())
        self.car.dump(indent + "  ")
        self.cdr.dump(indent)


class Sym(Expr):
    def __init__(self, value: str):
        self.value = value

    def visit(
        self,
        pre: Callable[[Expr, Any], None],
        post: Callable[[Expr, Any], None],
        arg: Any = None,
    ):
        pre(self, arg)
        post(self, arg)

    def basic_repr(self):
        return self.value

    def nameOf(self) -> str:
        return f"Sym({self.value})"

    # def isterminal(self, state: State) -> bool:
    #     if self.value in state.nonterms:
    #         return False
    #     else:
    #         state.terms.add(self.value)
    #         return True

    def dump(self, indent: str) -> None:
        print(indent, self.dump0())


class Value(Expr):
    def __init__(self, value: str):
        self.value = value

    def visit(
        self,
        pre: Callable[[Expr, Any], None],
        post: Callable[[Expr, Any], None],
        arg: Any = None,
    ):
        pre(self, arg)
        post(self, arg)

    def basic_repr(self) -> str:
        return f"«{self.value}»"

    def dump(self, indent: str) -> None:
        print(indent, self.dump0())


class Loop(Expr):
    pass


class Rep(Loop):
    def __init__(self, val: Expr):
        self.val = val
        self.element: Optional[str] = None

    def visit(
        self,
        pre: Callable[[Expr, Any], None],
        post: Callable[[Expr, Any], None],
        arg: Any = None,
    ):
        pre(self, arg)
        self.val.visit(pre, post, arg)
        post(self, arg)

    def basic_repr(self):
        return "{" + f" {self.val.__repr__()} " + "}"

    def dump(self, indent: str):
        print(indent, self.dump0())
        self.val.dump(indent + "  ")


class Opt(Expr):
    def __init__(self, val: Expr):
        self.val = val

    def visit(
        self,
        pre: Callable[[Expr, Any], None],
        post: Callable[[Expr, Any], None],
        arg: Any = None,
    ):
        pre(self, arg)
        self.val.visit(pre, post, arg)
        post(self, arg)

    def basic_repr(self):
        return f"[ {self.val.__repr__()} ]"

    def dump(self, indent: str):
        print(indent, self.dump0())
        self.val.dump(indent + "  ")


class Exit(Expr):
    pass


class Break(Exit):
    def __init__(self):
        pass

    def basic_repr(self):
        return "break"

    def visit(
        self,
        pre: Callable[[Expr, Any], None],
        post: Callable[[Expr, Any], None],
        arg: Any = None,
    ):
        pre(self, arg)
        post(self, arg)

    def dump(self, indent: str):
        print(indent, self.dump0())


class Continue(Exit):
    def __init__(self):
        pass

    def basic_repr(self):
        return "continue"

    def visit(
        self,
        pre: Callable[[Expr, Any], None],
        post: Callable[[Expr, Any], None],
        arg: Any = None,
    ):
        pre(self, arg)
        post(self, arg)

    def dump(self, indent: str):
        print(indent + self.dump0())


class OnePlus(Loop):
    def __init__(self, val: Expr):
        self.val = val
        self.element: Optional[str] = None

    def basic_repr(self):
        return f"{{+ {self.val.__repr__()} +}}"

    def visit(
        self,
        pre: Callable[[Expr, Any], None],
        post: Callable[[Expr, Any], None],
        arg: Any = None,
    ):
        pre(self, arg)
        self.val.visit(pre, post, arg)
        post(self, arg)

    def dump(self, indent: str):
        print(indent + self.dump0())
        self.val.dump(indent + "  ")


class Infinite(Loop):
    def __init__(self, val: Expr):
        self.val = val
        self.element: Optional[str] = None

    def basic_repr(self):
        return f"{{* {self.val.__repr__()} *}}"

    def visit(
        self,
        pre: Callable[[Expr, Any], None],
        post: Callable[[Expr, Any], None],
        arg: Any = None,
    ):
        pre(self, arg)
        self.val.visit(pre, post, arg)
        post(self, arg)

    def dump(self, indent: str):
        print(indent + self.dump0())
        self.val.dump(indent + "  ")


class Production:
    def __init__(self, lhs: str, rhs: Expr):
        self.lhs: str = lhs
        self.rhs: Expr = rhs

    def dump(self):
        print(self.lhs, " -> ")
        self.rhs.dump("  ")


class Spec:
    def __init__(self, preamble: List[str], productions: list[Production]):
        self.preamble = preamble
        self.productions = productions
        self.nonterms: Set[str] = set(p.lhs for p in productions)

    def dump(self):
        for p in self.preamble:
            print(p)
        for p in self.productions:
            p.dump()
