from sealir.lam import LamBuilder
from sealir.rvsdg import (
    EvalCtx,
    EvalLamState,
    lambda_evaluation,
    restructure_source,
)


def test_return_arg0():
    def udt(n: int, m: int) -> int:
        return n

    args = (12, 32)
    run(udt, args)


def test_return_arg1():
    def udt(n: int, m: int) -> int:
        return m

    args = (12, 32)
    run(udt, args)


def test_simple_add():
    def udt(n: int, m: int) -> int:
        a = n + m
        return a

    args = (12, 32)
    run(udt, args)


def test_inplace_add():
    def udt(n: int, m: int) -> int:
        a = n + m
        a += n
        return a

    args = (12, 32)
    run(udt, args)


def test_multi_assign():
    def udt(n: int, m: int) -> int:
        a = b = n + m
        return a, b

    args = (12, 32)
    run(udt, args)


def test_if_else_1():
    def udt(n: int, m: int) -> int:
        # basic min
        if n < m:
            out = n
        else:
            out = m
        return out

    args = (12, 32)
    run(udt, args)

    args = (32, 12)
    run(udt, args)


def test_if_else_2():
    def udt(n: int, m: int) -> int:
        if n < m:
            x = n
            y = m
        else:
            x = m
            y = n
        return x, y

    args = (12, 32)
    run(udt, args)

    args = (32, 12)
    run(udt, args)


def test_if_else_3():
    def udt(n: int, m: int) -> int:
        if m > n:
            a = b = m
        else:
            a = b = n
        return a, b

    args = (12, 32)
    run(udt, args)
    args = (32, 12)
    run(udt, args)


def test_if_else_hard():
    def udt(n: int, m: int) -> int:
        a = m + n
        c = a
        if m > n:
            a = b = n + m
        else:
            a = b = n * m
        c += a
        c *= b
        return c

    args = (12, 32)
    run(udt, args)

    args = (32, 12)
    run(udt, args)


# def sum1d(n: int) -> int:
#     c = 0
#     for i in range(n):
#         c += i
#     return c

# def sum1d(n: int) -> int:
#     c = 0
#     for i in range(n):
#         for j in range(i):
#             c += i * j
#             if c > 100:
#                 break
#     return c


# def sum1d(n: int) -> int:
#     c = 0
#     for i in range(n):
#         for j in range(i):
#             c += i + j
#     return c


def run(func, args):
    lam = restructure_source(func)

    # Prepare run
    lb = LamBuilder(lam.tape)

    ctx = EvalCtx.from_arguments(*args)
    with lam.tape:
        app_root = lb.app(lam, *ctx.make_arg_node())

    out = lb.format(app_root)
    print(out)

    memo = app_root.traverse(lambda_evaluation, EvalLamState(context=ctx))
    res = memo[app_root]
    print("result", res)
    got = res[1]

    assert got == func(*args)
    return got
