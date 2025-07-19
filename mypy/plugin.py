"""Mypy plugin for paramclasses."""

from functools import partial
from collections.abc import Callable

from mypy.plugin import ClassDefContext, FunctionContext, Plugin


METAPARAMCLASS_FULLNAME = "paramclasses.paramclasses._MetaParamClass"

class CustomPlugin(Plugin):
    """The plugin."""

    _paramclasses = set()  # Tracks all paramclasses founds during plugin life

    def get_metaclass_hook(self, fullname) -> Callable[[ClassDefContext], None] | None:
        """Update class definition when it uses metaclass."""
        return paramclass_finder_hook

    def get_base_class_hook(self, fullname) -> Callable[[ClassDefContext], None] | None:
        """Update class definition when it uses base class."""
        # print("get_base_class_hook", fullname,)
        return paramclass_finder_hook

    # def get_function_hook(self, fullname: str) -> Callable[[FunctionContext], Type] | None:
    #     """Change signature of functions."""
    #     if fullname.startswith("paramclasses."):
    #         print(f"==== {fullname} ====")
    #         return v
    #     return None

def paramclass_finder_hook(ctx):
    """Stores paramclasses and applies logic function."""
    mcs = ctx.cls.info.metaclass_type
    if mcs is not None and mcs.type.fullname == METAPARAMCLASS_FULLNAME:
        modify_paramclass_def(ctx.cls)


def modify_paramclass_def(cls) -> None:
    """"""
    replace_protected_decorator_with_final(cls)
    replace_protected_assignment_with_Final(cls)


def replace_protected_decorator_with_final(cls) -> None:
    print(f"Replaced {cls.info.fullname!r} protected decorators")

def replace_protected_assignment_with_Final(cls) -> None:
    print(f"Replaced {cls.info.fullname!r} protected assignments")




def plugin(_version: str) -> Plugin:
    """Follow tuto."""
    # ignore version argument if the plugin works with all mypy versions.
    return CustomPlugin

def v(func_ctx):
    print(f"arg_types: {func_ctx.arg_types}")
    print(f"arg_kinds: {func_ctx.arg_kinds}")
    print(f"callee_arg_names: {func_ctx.callee_arg_names}")
    print(f"arg_names: {func_ctx.arg_names}")
    print(f"default_return_type: {func_ctx.default_return_type}")
    print(f"args: {[[str(x) for x in arg] for arg in func_ctx.args]}")
    print(f"context: {func_ctx.context}")
    print(f"api: {func_ctx.api}")
    breakpoint()
    return func_ctx.default_return_type
