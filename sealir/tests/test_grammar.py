from collections.abc import Generator

from sealir import ase, grammar


class Val(grammar.Rule):
    pass


class Num(Val):
    value: int


class BinOp(Val):
    lhs: ase.SExpr
    rhs: ase.SExpr


class Add(BinOp): ...


class Sub(BinOp): ...


class Mul(BinOp): ...


class CalcGrammar(grammar.Grammar):
    start = Val


def test_calculator() -> None:

    assert Num.__match_args__ == ("value",)
    assert Add.__match_args__ == ("lhs", "rhs")
    assert Sub.__match_args__ == ("lhs", "rhs")
    assert Mul.__match_args__ == ("lhs", "rhs")

    assert Mul._rules is Val._rules

    assert Val._rules == {
        "Val": Val,
        "Num": Num,
        "BinOp": BinOp,
        "Add": Add,
        "Sub": Sub,
        "Mul": Mul,
    }

    with ase.Tape() as tp:
        grm = CalcGrammar(tp)
        a = grm.write(Num(value=123))
        b = grm.write(Num(value=321))
        c = grm.write(Add(lhs=a, rhs=a))
        d = grm.write(Sub(lhs=c, rhs=b))
        e = grm.write(Mul(lhs=b, rhs=d))

    assert c.lhs.value == a.value

    class Calc(grammar.TreeRewriter[int]):
        def rewrite_Num(self, orig: grammar.NamedSExpr, value: int) -> int:
            return value

        def rewrite_Add(
            self, orig: grammar.NamedSExpr, lhs: int, rhs: int
        ) -> int:
            return lhs + rhs

        def rewrite_Sub(
            self, orig: grammar.NamedSExpr, lhs: int, rhs: int
        ) -> int:
            return lhs - rhs

        def rewrite_Mul(
            self, orig: grammar.NamedSExpr, lhs: int, rhs: int
        ) -> int:
            return lhs * rhs

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
        grm = CalcGrammar(tp)
        a = grm.write(Num(value=123))
        b = grm.write(Num(value=321))
        c = grm.write(Add(lhs=a, rhs=a))
        d = grm.write(Sub(lhs=c, rhs=b))
        e = grm.write(Mul(lhs=b, rhs=d))

    def calc(
        sexpr: ase.SExpr, state: ase.TraverseState
    ) -> Generator[ase.SExpr, int, int]:
        match sexpr:
            case Num(value=int(value)):
                return value
            case Add(lhs=lhs, rhs=rhs):
                return (yield lhs) + (yield rhs)
            case Sub(lhs=lhs, rhs=rhs):
                return (yield lhs) - (yield rhs)
            case Mul(lhs=lhs, rhs=rhs):
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


class _VarargVal(grammar.Rule):
    pass


class Grouped(_VarargVal):  # new root
    head: str
    vargs: tuple[ase.value_type, ...]


class Tuple(_VarargVal):
    args: tuple[ase.SExpr, ...]


def test_vararg():
    class VarargGrammar(grammar.Grammar):
        start = _VarargVal | Val

    assert VarargGrammar.start._rules["Grouped"] is Grouped

    with VarargGrammar(ase.Tape()) as grm:
        n1 = grm.write(Num(123))
        g1 = grm.write(Grouped(head="heading", vargs=(n1, 1321)))
        g2 = grm.write(Grouped(head="heading2", vargs=(123, g1)))
        t1 = grm.write(Tuple((g1, g2)))

    print(grm._tape.dump())
    assert g1._head == "Grouped"

    assert g1._args == ("heading", n1, 1321)
    assert g2._args == ("heading2", 123, g1)
    assert g2.vargs == (123, g1)

    match g2:
        case Grouped(head=head, vargs=(v1, v2)):
            pass
    assert head == "heading2"
    assert v1 == 123
    assert v2 == g1
    match v2:
        case Grouped(head="heading", vargs=vargs):
            pass
    assert vargs == (n1, 1321)

    assert t1.args == (g1, g2)


def test_three_grammar():

    class Another(grammar.Rule):  # new root
        value: ase.SExpr

    class ThreeGrammar(grammar.Grammar):
        start = _VarargVal | Val | Another

    with ThreeGrammar(ase.Tape()) as grm:
        n1 = grm.write(Num(123))
        g1 = grm.write(Grouped(head="a", vargs=(n1,)))
        a1 = grm.write(Another(value=g1))

    assert ThreeGrammar.start._combined == (_VarargVal, Val, Another)
