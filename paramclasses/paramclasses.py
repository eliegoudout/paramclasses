"""Implements `ParamClass`."""

__all__ = ["ParamClass", "ProtectedError", "protected"]

from abc import ABCMeta
from collections.abc import Collection
from dataclasses import dataclass
from itertools import chain
from reprlib import recursive_repr
from types import MappingProxyType
from typing import cast, final
from warnings import warn


@dataclass
class protected:  # noqa: N801 (decorator-like capitalization)
    """Decorator to make read-only, including in subclasses.

    Should always be the outtermost decorator. Protection doesn't apply
    to annotations.
    """

    val: object


def _unprotect(val: object) -> tuple[object, bool]:
    """Unwrap protected value, recursively if needed."""
    if isinstance(val, protected):
        return _unprotect(val.val)[0], True
    return val, False


@dataclass(frozen=True)
class _MissingType:
    repr: str = "..."

    def __repr__(self) -> str:
        return self.repr


class ProtectedError(AttributeError):
    """Don't assign or delete protected attributes."""


@final
class _MetaFrozen(type):
    """Make `_MetaParamClass` frozen with this metaclass.

    We take this precaution since its attributes `default`, `protected`
    and `missing` might be used on some occasions. While we're at it, we
    heuristically forbid `_MetaParamClass` subclassing (soft check).
    """

    def __new__(mcs, name: str, bases: tuple, namespace: dict[str, object]) -> type:  # noqa: N804
        if len(bases) != 1 or name != "_MetaParamClass" or bases[0] is not ABCMeta:
            msg = "`_MetaParamClass' cannot be subclassed"
            raise ProtectedError(msg)
        return super().__new__(mcs, name, bases, namespace)

    def __setattr__(*_: object, **__: object) -> None:
        raise ProtectedError

    def __delattr__(*_: object, **__: object) -> None:
        raise ProtectedError


@final
class _MetaParamClass(ABCMeta, metaclass=_MetaFrozen):
    """Specifically implemented as ParamClass metaclass.

    Implements class-level protection behaviour and parameters
    identification, with default values. Also subclasses `ABCMeta` to
    be compatible with its functionality.
    """

    default = "__paramclass_default_"  # would-be-mangled on purpose
    protected = "__paramclass_protected_"  # would-be-mangled on purpose
    missing = _MissingType("?")  # repr

    @staticmethod
    def assert_unprotected(attr: str, protected: Collection) -> None:
        """Assert that `attr not in protected`."""
        if attr in protected:
            msg = f"Attribute '{attr}' is protected"
            raise ProtectedError(msg)

    @staticmethod
    def assert_valid_param(attr: str) -> None:
        """Assert that `attr` is authorized as parameter name."""
        if attr.startswith("__") and attr.endswith("__"):
            msg = f"Double dunder parameters ('{attr}') are forbidden"
            raise AttributeError(msg)

    @classmethod
    def dont_assign_missing(mcs, attr: str, val: object) -> None:  # noqa: N804
        """Forbid assigning the special 'missing value'."""
        if val is mcs.missing:
            msg = f"Assigning special missing value (attribute '{attr}') is forbidden"
            raise ValueError(msg)

    def __new__(mcs, name: str, bases: tuple, namespace: dict[str, object]) -> type:  # noqa: N804
        """Most of `_MetaParamClass` logic.

        It essentially does the following.
            1. Retrieves parameters and protected attributes from bases.
            2. Inspects `namespace` and its `__annotations__` to infer
                new parameters and newly protected attributes.
        """
        protected_special = [mcs.default, mcs.protected, "__dict__"]
        # # Bases: default, protected
        default: dict = {}
        protected_dict_bases: dict = {}
        for base in bases[::-1]:
            default |= getattr(base, mcs.default, {})
            # Previous bases protected coherence
            for attr, val_protected in protected_dict_bases.items():
                val = getattr(base, attr, mcs.missing)
                if not (val is val_protected or val is mcs.missing):
                    msg = f"Incoherent protection inheritance for attribute '{attr}'"
                    raise ProtectedError(msg)
            for attr in getattr(base, mcs.protected, []):
                if attr in protected_dict_bases or attr in protected_special:
                    continue
                protected_dict_bases[attr] = getattr(base, attr)

        # # Namespace: handle slots, protect, store parameters
        protected = set(chain(protected_dict_bases, protected_special))

        # Cannot slot protected
        slots = cast(tuple, namespace.get("__slots__", ()))
        protected_then_slotted = protected & set(slots)
        if protected_then_slotted:
            msg = f"Cannot slot protected attributes: {list(protected_then_slotted)}"
            raise ProtectedError(msg)

        # Unwrap decorator and identify new protected
        protected_new = []
        namespace_final = {}
        for attr, val_potentially_protected in namespace.items():
            mcs.assert_unprotected(attr, protected)
            val, was_protected = _unprotect(val_potentially_protected)
            mcs.dont_assign_missing(attr, val)
            namespace_final[attr] = val
            if was_protected:
                protected_new.append(attr)

        # Store new parameters and default
        annotations: dict = cast(dict, namespace.get("__annotations__", {}))
        for attr in annotations:
            mcs.assert_unprotected(attr, protected)
            mcs.assert_valid_param(attr)
            default[attr] = namespace_final.get(attr, mcs.missing)

        # Update namespace
        namespace_final[mcs.default] = MappingProxyType(default)
        namespace_final[mcs.protected] = frozenset(chain(protected, protected_new))

        return super().__new__(mcs, name, bases, namespace_final)

    def __setattr__(cls, attr: str, val_potentially_protected: object) -> None:
        """Handle protection, missing value."""
        mcs = type(cls)
        mcs.assert_unprotected(attr, getattr(cls, mcs.protected))
        val, was_protected = _unprotect(val_potentially_protected)
        mcs.dont_assign_missing(attr, val)
        if was_protected:
            warn(
                f"Cannot protect attribute '{attr}' after class creation. Ignored",
                stacklevel=2,
            )
        return super().__setattr__(attr, val)

    def __delattr__(cls, attr: str) -> None:
        """Handle protection."""
        mcs = type(cls)
        mcs.assert_unprotected(attr, getattr(cls, mcs.protected))
        return super().__delattr__(attr)


class ParamClass(metaclass=_MetaParamClass):
    """Parameter-holding classes with robust subclassing protection.

    This is the base "paramclass". To define a "paramclass", simply
    subclass `ParamClass` or any of its subclasses, inheriting from its
    functionalities. When defining a "paramclass", use the `@protected`
    decorator to disable further setting and deleting on target
    attributes. The protection affects both the defined class and its
    future subclasses, as well as any of their instances. Also,
    `ParamClass` inherits from `ABC` functionalities

    A "parameter" is any attribute that was given an annotation during
    class definition, similar to `@dataclass`. For "parameters",
    get/set/delete interactions bypass descriptors mechanisms. For
    example, if `A.x` is a descriptor, `A().x is A.x`. This is similar
    to the behaviour of dataclasses and is extended to set/delete.

    Subclasses may wish to implement a callback on parameter-value
    modification with `_on_param_will_be_set()`, or to further customize
    instanciation (which is similar to keywords-only dataclasses') with
    `__post_init__()`.

    Unprotected methods:
        _on_param_will_be_set: Call before new parameter assignment.
        __post_init__: Init logic, after parameters assignment.
        __repr__: Show all non-default or missing, e.g. `A(x=1, y=?)`.

    Protected methods:
        set_params: Set multiple parameter values at once via keywords.
        __init__: Set parameters and call `__post_init__`.
        __getattribute__: Handle descriptor parameters.
        __setattr__: Handle protection, missing value, descriptor
            parameters.
        __delattr__: Handle protection, descriptor parameters.

    Protected properties:
        params (dict[str, object]): Current parameter dict for instance.
        missing_params (list[str]): Parameters without value.
    """

    # ========================= Subclasses may override these ==========================
    #
    def _on_param_will_be_set(self, attr: str, future_val: object) -> None:
        """Call before new parameter assignment."""

    def __post_init__(self, *args: object, **kwargs: object) -> None:
        """Init logic, after parameters assignment."""

    @recursive_repr()
    def __repr__(self) -> str:
        """Show all non-default or missing, e.g. `A(x=1, z=?)`."""
        mcs = type(type(self))
        params_str = ", ".join(
            f"{attr}={getattr(self, attr, mcs.missing)!r}"
            for attr, val_default in getattr(self, mcs.default).items()
            if (val_default is mcs.missing)
            or (getattr(self, attr, mcs.missing) != val_default)
        )
        return f"{type(self).__name__}({params_str})"

    # ==================================================================================

    @protected
    def set_params(self, **param_values: object) -> None:
        """Set multiple parameter values at once via keywords."""
        mcs = type(type(self))
        wrong = set(param_values) - set(getattr(self, mcs.default))
        if wrong:
            msg = f"Invalid parameters: {wrong}. Operation cancelled"
            raise AttributeError(msg)

        for attr, val in param_values.items():
            setattr(self, attr, val)

    @protected  # type: ignore[prop-decorator]  # mypy is fooled
    @property
    def params(self) -> dict[str, object]:
        """Current parameter dict for instance."""
        mcs = type(type(self))
        return {
            attr: getattr(self, attr, mcs.missing)
            for attr in getattr(self, mcs.default)
        }

    @protected  # type: ignore[prop-decorator]  # mypy is fooled
    @property
    def missing_params(self) -> list[str]:
        """Parameters without value."""
        mcs = type(type(self))
        return [
            attr
            for attr in getattr(self, mcs.default)
            if not hasattr(self, attr) or getattr(self, attr) is mcs.missing
        ]

    @protected  # type: ignore[misc]  # mypy is fooled
    def __init__(
        self,
        args: list | None = None,
        kwargs: dict | None = None,
        /,
        **param_values: object,
    ) -> None:
        """Set parameters and call `__post_init__`.

        Arguments:
            args (list | None): If not `None`, unpacked as positional
                arguments for `__post_init__`.
            kwargs (dict | None): If not `None`, unpacked as keyword
                arguments for `__post_init__`.
            **param_values (object): Assigned parameter values at
                instantiation.

        """
        self.set_params(**param_values)  # type: ignore[operator]  # mypy is fooled
        if args is None:
            args = []
        if kwargs is None:
            kwargs = {}
        self.__post_init__(*args, **kwargs)

    @protected  # type: ignore[override]  # mypy is fooled
    def __getattribute__(self, attr: str) -> object:
        """Handle descriptor parameters."""
        cls = type(self)
        mcs = type(cls)
        if attr not in getattr(cls, mcs.default):
            return super().__getattribute__(attr)

        # Handle descriptor parameters
        # https://docs.python.org/3/howto/descriptor.html#invocation-from-an-instance
        if attr in vars(self):
            return vars(self)[attr]
        for base in cls.__mro__:
            if attr in vars(base):
                return vars(base)[attr]
        msg = f"'{cls.__name__}' object has no attribute '{attr}'"
        raise AttributeError(msg)

    @protected  # type: ignore[override]  # mypy is fooled
    def __setattr__(self, attr: str, val_potentially_protected: object) -> None:
        """Handle protection, missing value, descriptor parameters.

        Also call the `_on_param_will_be_set()` callback when `attr` is
        a parameter key.
        """
        mcs = type(type(self))
        # Handle protection, missing value
        mcs.assert_unprotected(attr, getattr(self, mcs.protected))
        val, was_protected = _unprotect(val_potentially_protected)
        mcs.dont_assign_missing(attr, val)
        if was_protected:
            warn(
                f"Cannot protect attribute '{attr}' on instance assignment. Ignored",
                stacklevel=2,
            )

        # Handle callback, descriptor parameters
        if attr in getattr(self, mcs.default):
            self._on_param_will_be_set(attr, val)
            vars(self)[attr] = val
        else:
            super().__setattr__(attr, val)

    @protected  # type: ignore[override]  # mypy is fooled
    def __delattr__(self, attr: str) -> None:
        """Handle protection, descriptor parameters."""
        # Handle protection
        mcs = type(type(self))
        mcs.assert_unprotected(attr, getattr(self, mcs.protected))

        # Handle descriptor parameters
        if attr in getattr(self, mcs.default):
            del vars(self)[attr]
        else:
            super().__delattr__(attr)
