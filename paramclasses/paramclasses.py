"""Implements `ParamClass`."""

__all__ = [
    "DEFAULT",
    "MISSING",
    "PROTECTED",
    "ParamClass",
    "ProtectedError",
    "isparamclass",
    "protected",
]

from abc import ABCMeta
from collections.abc import Collection
from dataclasses import dataclass
from itertools import chain
from reprlib import recursive_repr
from types import MappingProxyType
from typing import cast, final
from warnings import warn


@dataclass(frozen=True)
class _MissingType:
    repr: str = "..."

    def __repr__(self) -> str:
        return self.repr


DEFAULT = "__paramclass_default_"  # would-be-mangled on purpose
PROTECTED = "__paramclass_protected_"  # would-be-mangled on purpose
MISSING = _MissingType("?")  # Sentinel object better representing missing value


@dataclass(frozen=True)
class _ProtectedType:
    val: object

    # See github.com/eliegoudout/paramclasses/issues/3
    def __new__(cls, *_: object, **__: object):  # noqa: ANN204  # No `Self` in 3.10
        return super().__new__(cls)


def protected(val: object) -> _ProtectedType:
    """Make read-only with this decorator, including in subclasses.

    Should always be the outtermost decorator. Protection doesn't apply
    to annotations.
    """
    return _ProtectedType(val)


def _unprotect(val: object) -> tuple[object, bool]:
    """Unwrap protected value, recursively if needed."""
    if isinstance(val, _ProtectedType):
        return _unprotect(val.val)[0], True
    return val, False


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
        msg = "`_MetaParamClass' attributes are frozen"
        raise ProtectedError(msg)

    def __delattr__(*_: object, **__: object) -> None:
        msg = "`_MetaParamClass' attributes are frozen"
        raise ProtectedError(msg)


def _assert_unprotected(attr: str, protected: Collection) -> None:
    """Assert that `attr not in protected`."""
    if attr in protected:
        msg = f"Attribute '{attr}' is protected"
        raise ProtectedError(msg)


def _assert_valid_param(attr: str) -> None:
    """Assert that `attr` is authorized as parameter name."""
    if attr.startswith("__") and attr.endswith("__"):
        msg = f"Double dunder parameters ('{attr}') are forbidden"
        raise AttributeError(msg)


def _dont_assign_missing(attr: str, val: object) -> None:
    """Forbid assigning the special 'missing value'."""
    if val is MISSING:
        msg = f"Assigning special missing value (attribute '{attr}') is forbidden"
        raise ValueError(msg)


@final
class _MetaParamClass(ABCMeta, metaclass=_MetaFrozen):
    """Specifically implemented as ParamClass metaclass.

    Implements class-level protection behaviour and parameters
    identification, with default values. Also subclasses `ABCMeta` to
    be compatible with its functionality.
    """

    def __new__(mcs, name: str, bases: tuple, namespace: dict[str, object]) -> type:  # noqa: N804
        """Most of `_MetaParamClass` logic.

        It essentially does the following.
            1. Retrieves parameters and protected attributes from bases.
            2. Inspects `namespace` and its `__annotations__` to infer
                new parameters and newly protected attributes.
        """
        protected_special = [DEFAULT, PROTECTED, "__dict__"]
        # # Bases: default, protected
        default: dict = {}
        protected_dict_bases: dict = {}
        for base in bases[::-1]:
            default |= getattr(base, DEFAULT, {})
            # Previous bases protected coherence
            for attr, val_protected in protected_dict_bases.items():
                val = getattr(base, attr, MISSING)
                if val is not val_protected and val is not MISSING:
                    msg = f"Incoherent protection inheritance for attribute '{attr}'"
                    raise ProtectedError(msg)
            for attr in getattr(base, PROTECTED, []):
                if attr in protected_dict_bases or attr in protected_special:
                    continue
                protected_dict_bases[attr] = getattr(base, attr)

        # # Namespace: handle slots, protect, store parameters
        protected = set(chain(protected_dict_bases, protected_special))

        # Cannot slot protected
        slots = cast(tuple, namespace.get("__slots__", ()))
        protected_then_slotted = protected & set(slots)
        if protected_then_slotted:
            msg = f"Cannot slot already protected attributes: {protected_then_slotted}"
            raise ProtectedError(msg)

        # Unwrap decorator and identify new protected
        protected_new = []
        namespace_final = {}
        for attr, val_potentially_protected in namespace.items():
            _assert_unprotected(attr, protected)
            val, was_protected = _unprotect(val_potentially_protected)
            _dont_assign_missing(attr, val)
            namespace_final[attr] = val
            if was_protected:
                protected_new.append(attr)

        # Store new parameters and default
        annotations: dict = cast(dict, namespace.get("__annotations__", {}))
        for attr in annotations:
            _assert_unprotected(attr, protected)
            _assert_valid_param(attr)
            default[attr] = namespace_final.get(attr, MISSING)

        # Update namespace
        namespace_final[DEFAULT] = MappingProxyType(default)
        namespace_final[PROTECTED] = frozenset(chain(protected, protected_new))

        return super().__new__(mcs, name, bases, namespace_final)

    def __getattribute__(cls, attr: str) -> object:
        """Handle descriptor parameters."""
        vars_cls = super().__getattribute__("__dict__")

        # Special case `__dict__`
        if attr == "__dict__":
            return vars_cls

        # Not a parameter, normal look-up
        if attr not in vars_cls[DEFAULT]:
            return super().__getattribute__(attr)

        # Parameters bypass descriptor
        for vars_base in chain((vars_cls,), map(vars, cls.__mro__[1:])):
            if attr in vars_base:
                return vars_cls[attr]

        # Not found
        msg = f"type object '{cls.__name__}' has no attribute '{attr}'"
        raise AttributeError(msg)

    def __setattr__(cls, attr: str, val_potentially_protected: object) -> None:
        """Handle protection, missing value."""
        _assert_unprotected(attr, getattr(cls, PROTECTED))
        val, was_protected = _unprotect(val_potentially_protected)
        _dont_assign_missing(attr, val)
        if was_protected:
            warn(
                f"Cannot protect attribute '{attr}' after class creation. Ignored",
                stacklevel=2,
            )
        return super().__setattr__(attr, val)

    def __delattr__(cls, attr: str) -> None:
        """Handle protection."""
        _assert_unprotected(attr, getattr(cls, PROTECTED))
        return super().__delattr__(attr)


class ParamClass(metaclass=_MetaParamClass):
    """Parameter-holding class with robust subclassing protection.

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
        _on_param_will_be_set: Call before parameter assignment.
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
        missing_params (tuple[str]): Parameters without value.
    """

    # ========================= Subclasses may override these ==========================
    #
    def _on_param_will_be_set(self, attr: str, future_val: object) -> None:
        """Call before parameter assignment."""

    def __post_init__(self, *args: object, **kwargs: object) -> None:
        """Init logic, after parameters assignment."""

    @recursive_repr()
    def __repr__(self) -> str:
        """Show all non-default or missing, e.g. `A(x=1, z=?)`."""
        params_str = ", ".join(
            f"{attr}={getattr(self, attr, MISSING)!r}"
            for attr, val_default in getattr(self, DEFAULT).items()
            if (val_default is MISSING) or (getattr(self, attr, MISSING) != val_default)
        )
        return f"{type(self).__name__}({params_str})"

    # ==================================================================================

    @protected
    def set_params(self, **param_values: object) -> None:
        """Set multiple parameter values at once via keywords."""
        wrong = set(param_values) - set(getattr(self, DEFAULT))
        if wrong:
            msg = f"Invalid parameters: {wrong}. Operation cancelled"
            raise AttributeError(msg)

        for attr, val in param_values.items():
            setattr(self, attr, val)

    @protected  # type: ignore[prop-decorator]  # mypy is fooled
    @property
    def params(self) -> dict[str, object]:
        """Current parameter dict for instance."""
        return {attr: getattr(self, attr, MISSING) for attr in getattr(self, DEFAULT)}

    @protected  # type: ignore[prop-decorator]  # mypy is fooled
    @property
    def missing_params(self) -> tuple[str]:
        """Parameters without value."""
        return tuple(
            attr
            for attr in getattr(self, DEFAULT)
            if not hasattr(self, attr) or getattr(self, attr) is MISSING
        )

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
        vars_self = super().__getattribute__("__dict__")

        # Special case `__dict__`, which is protected
        if attr == "__dict__":  # To save a few statements
            if attr in vars_self:
                del vars_self[attr]
            return vars_self

        # Remove attr from `vars(self)` if protected -- should not be there!
        if attr in vars_self and attr in getattr(cls, PROTECTED):
            del vars_self[attr]

        # Not a parameter, normal look-up
        if attr not in getattr(cls, DEFAULT):
            return super().__getattribute__(attr)

        # Parameters bypass descriptor
        # https://docs.python.org/3/howto/descriptor.html#invocation-from-an-instance
        if attr in vars_self:
            return vars_self[attr]

        for base in cls.__mro__:
            if attr in vars(base):
                return vars(base)[attr]

        # Not found
        msg = f"'{cls.__name__}' object has no attribute '{attr}'"
        raise AttributeError(msg)

    @protected  # type: ignore[override]  # mypy is fooled
    def __setattr__(self, attr: str, val_potentially_protected: object) -> None:
        """Handle protection, missing value, descriptor parameters.

        Also call the `_on_param_will_be_set()` callback when `attr` is
        a parameter key.
        """
        # Handle protection, missing value
        _assert_unprotected(attr, getattr(self, PROTECTED))
        val, was_protected = _unprotect(val_potentially_protected)
        _dont_assign_missing(attr, val)
        if was_protected:
            warn(
                f"Cannot protect attribute '{attr}' on instance assignment. Ignored",
                stacklevel=2,
            )

        # Handle callback, descriptor parameters
        if attr in getattr(self, DEFAULT):
            self._on_param_will_be_set(attr, val)
            vars(self)[attr] = val
        else:
            super().__setattr__(attr, val)

    @protected  # type: ignore[override]  # mypy is fooled
    def __delattr__(self, attr: str) -> None:
        """Handle protection, descriptor parameters."""
        # Handle protection
        _assert_unprotected(attr, getattr(self, PROTECTED))

        # Handle descriptor parameters
        if attr in getattr(self, DEFAULT):
            del vars(self)[attr]
        else:
            super().__delattr__(attr)


def isparamclass(cls: type) -> bool:
    """Check if `cls` is a paramclass."""
    # Should have same metaclass
    if type(cls) is not type(ParamClass):
        return False

    # Should inherit from `ParamClass`
    return any(Parent is ParamClass for Parent in cls.__mro__)
