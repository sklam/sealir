from __future__ import annotations

from typing import TypeVar, Generic, Any, Union

from sealir import ase


T = TypeVar("T")


class _PassThru:
    def __repr__(self) -> str:
        return "<PassThru>"


class TreeRewriter(Generic[T], ase.TreeVisitor):

    PassThru = _PassThru()

    memo: dict[ase.Expr, Union[T, ase.Expr]]

    flag_save_history = True

    def __init__(self):
        self.memo = {}

    def visit(self, expr: ase.Expr) -> None:
        res = self._dispatch(expr)
        if res is self.PassThru:
            res = expr
        self.memo[expr] = res
        # Logic for save history
        if self.flag_save_history:
            if res is not expr and isinstance(res, ase.Expr):
                # Insert code that maps replacement back to old
                cls = type(self)
                ase.expr(
                    ".md.rewrite",
                    f"{cls.__module__}.{cls.__qualname__}",
                    res,
                    expr,
                )

    def _dispatch(self, orig: ase.Expr) -> Union[T, ase.Expr]:
        head = orig.head
        args = orig.args
        updated = False

        def _lookup(val):
            nonlocal updated
            if isinstance(val, ase.Expr):
                updated = True
                return self.memo[val]
            else:
                return val

        args = tuple(_lookup(arg) for arg in args)
        fname = f"rewrite_{head}"
        fn = getattr(self, fname, None)
        if fn is not None:
            return fn(orig, *args)
        else:
            return self.rewrite_generic(orig, args, updated)

    def rewrite_generic(
        self, orig: ase.Expr, args: tuple[Any, ...], updated: bool
    ) -> Union[T, ase.Expr]:
        """Default implementation will automatically create a new node if
        children are updated; otherwise, returns the original expression if
        its children are unmodified.
        """
        if updated:
            return ase.expr(orig.head, *args)
        else:
            return orig
