from typing import Set, Any, Callable
import operator


class Expr:
    _observers: Set["Expr"]
    _value: Any

    def _create(self):
        if not hasattr(self, "_observers"):
            self._observers = set()

    def __init__(self):
        self._observers = set()

    def add_observer(self, observer: "Expr"):
        self._create()
        self._observers.add(observer)

    def remove_observer(self, observer: "Expr"):
        self._create()
        self._observers.remove(observer)

    def notify(self):
        self._create()
        for observer in self._observers:
            observer.recompute()

    def recompute(self):
        tmp = self.compute()
        if tmp != self._value:
            self._value = tmp
            self.notify()

    def compute(self) -> Any:
        raise NotImplementedError(
            f"{self.__class__.__name__}.compute() not implemented"
        )

    def get_value(self):
        return self._value

    def __or__(self, right: Any) -> "Expr":
        e = mkExpr(right)
        return BinaryExpr(operator.or_, self, e)

    def __and__(self, right: Any) -> "Expr":
        e = mkExpr(right)
        return BinaryExpr(operator.and_, self, e)

    # def __getitem__(self, right: Any) -> "Expr":
    #     e = mkExpr(right)
    #     return BinaryExpr(operator.getitem, self, e)


def mkExpr(x: Any) -> Expr:
    if isinstance(x, Expr):
        return x
    else:
        return Constant(x)


class Function(Expr):
    def __init__(self, fn: Callable[[Any], Any], *args: Expr):
        self.fn = fn
        self.args = args
        for arg in args:
            arg.add_observer(self)
        self._value = self.compute()

    def compute(self):
        args = [arg.get_value() for arg in self.args]
        return self.fn(*args)


class BinaryExpr(Expr):
    def __init__(self, op: Callable[[Any, Any], Any], left: Expr, right: Expr):
        self.op = op
        self.left = left
        self.right = right
        self.left.add_observer(self)
        self.right.add_observer(self)
        self._value = self.compute()

    def compute(self):
        left = self.left.get_value()
        right = self.right.get_value()
        return self.op(left, right)


class Gate(Expr):
    def __init__(self, gate: Expr, true_value: Expr, false_value: Expr):
        self.gate = gate
        self.true_value = true_value
        self.false_value = false_value
        self.true_value.add_observer(self)
        self.false_value.add_observer(self)
        self.gate.add_observer(self)
        self._value = self.compute()

    def compute(self):
        if self.gate.get_value():
            return self.true_value.get_value()
        else:
            return self.false_value.get_value()


class Indirect(Expr):
    def __init__(self, expr: Expr):
        self.expr = expr
        self._value = None
        self.expr.add_observer(self)
        self._value = self.compute()

    def compute(self):
        return self.expr.get_value()

    def replace(self, expr: Expr):
        self.expr.remove_observer(self)
        self.expr = expr
        self.expr.add_observer(self)
        self.recompute()

    def __ior__(self, right: Any) -> "Indirect":
        self.replace(self.expr | right)
        return self

    def __ixor__(self, right: Any) -> "Indirect":  # ugly hack
        e = mkExpr(right)
        self.replace(e)
        return self


class Constant(Expr):
    def __init__(self, value: Any):
        self._value = value


class Undefined(Expr):
    def __init__(self, value: Any):
        self._value = value
