from collections.abc import Generator

from sealir import ase


def test_bottom():
    tape = ase.Tape()
    assert tape._read_token(0) is None


def test_basic():
    with ase.Tape() as tp:
        a = tp.expr("num", 1)
        b = tp.expr("num", 2)
        c = tp.expr("add", a, b)
        d = tp.expr("sub", a, a)

    assert ase.pretty_str(c) == "(add (num 1) (num 2))"
    assert c._head == "add"
    assert c._args[0]._head == "num"
    assert c._args[0]._args == (1,)
    assert c._args[1]._head == "num"
    assert c._args[1]._args == (2,)

    parent_of_a = list(ase.walk_parents(a))
    assert parent_of_a[0] == c
    assert parent_of_a[0] != a
    assert parent_of_a[0] != b
    assert parent_of_a[1] == d

    for p in parent_of_a:
        assert ase.contains(p, a)


def test_copy_tree():
    with ase.Tape() as tp:
        tp.expr("num", 0)
        a = tp.expr("num", 1)
        b = tp.expr("num", 2)
        tp.expr("num", 3)
        tp.expr("add", a, b)
        d = tp.expr("sub", a, a)
        e = tp.expr("mul", b, d)

    new_tree = ase.Tape()
    new_e = ase.copy_tree_into(e, new_tree)

    assert len(new_tree._heap) < len(tp._heap)
    assert len(new_tree._tokens) < len(tp._tokens)

    assert new_e != e
    assert ase.pretty_str(new_e) == ase.pretty_str(e)


def test_apply_bottomup():
    with ase.Tape() as tp:
        a = tp.expr("num", 1)
        b = tp.expr("num", 2)
        c = tp.expr("sub", a, a)
        d = tp.expr("add", c, b)
        e = tp.expr("mul", b, c)
        f = tp.expr("div", e, d)

    buffer = []

    class BufferVisitor(ase.TreeVisitor):
        def visit(self, expr: ase.SExpr):
            buffer.append(expr)

    bv = BufferVisitor()
    ase.apply_bottomup(e, bv, reachable=None)

    # It is expected the visitor will see every S-expr in the Tape.
    # Regardless of whether it is reachable from the root S-expr.
    # But it will not go further then that (exclude `f`)
    assert buffer == [a, b, c, d, e]

    # Rerun with computed reachability
    buffer.clear()
    ase.apply_bottomup(e, bv)
    assert buffer == [a, b, c, e]


def test_calculator():
    with ase.Tape() as tp:
        a = tp.expr("num", 123)
        b = tp.expr("num", 321)
        c = tp.expr("add", a, a)
        d = tp.expr("sub", c, b)
        e = tp.expr("mul", b, d)

    class Calc(ase.TreeVisitor):
        def __init__(self):
            self.memo = {}

        def visit(self, expr: ase.SExpr):
            head = expr._head
            args = expr._args
            if head == "num":
                self.memo[expr] = args[0]
            elif head == "add":
                self.memo[expr] = self.memo[args[0]] + self.memo[args[1]]
            elif head == "sub":
                self.memo[expr] = self.memo[args[0]] - self.memo[args[1]]
            elif head == "mul":
                self.memo[expr] = self.memo[args[0]] * self.memo[args[1]]
            else:
                raise AssertionError("unknown op")

    calc = Calc()
    ase.apply_bottomup(e, calc)
    result = calc.memo[e]

    def expected():
        a = 123
        b = 321
        c = a + a
        d = c - b
        e = b * d
        return e

    assert expected() == result


def test_calculator_traverse():
    with ase.Tape() as tp:
        a = tp.expr("num", 123)
        b = tp.expr("num", 321)
        c = tp.expr("add", a, a)
        d = tp.expr("sub", c, b)
        e = tp.expr("mul", b, d)

    def calc(
        sexpr: ase.SExpr, state: ase.TraverseState
    ) -> Generator[ase.SExpr, int, int]:
        match sexpr:
            case ase.BasicSExpr("num", (int(value),)):
                return value
            case ase.BasicSExpr(
                "add", (ase.BasicSExpr() as lhs, ase.BasicSExpr() as rhs)
            ):
                return (yield lhs) + (yield rhs)
            case ase.BasicSExpr(
                "sub", (ase.BasicSExpr() as lhs, ase.BasicSExpr() as rhs)
            ):
                return (yield lhs) - (yield rhs)
            case ase.BasicSExpr(
                "mul", (ase.BasicSExpr() as lhs, ase.BasicSExpr() as rhs)
            ):
                return (yield lhs) * (yield rhs)
            case _:
                raise AssertionError(sexpr)

    memo = ase.traverse(e, calc)
    result = memo[e]

    def expected():
        a = 123
        b = 321
        c = a + a
        d = c - b
        e = b * d
        return e

    assert expected() == result
