"""Package implementing `ParamClass`.

Exposed API:
    IMPL:
        To access defaults and protected of a paramclass.
    MISSING:
        Sentinel object better representing missing value.
    ParamClass:
        Parameter-holding class with robust subclassing protection.
    ProtectedError:
        Don't assign or delete protected attributes.
    RawParamClass:
        `ParamClass` without `set_params`, `params`, `missing_params`.
    isparamclass:
        Check if `cls` is a paramclass.
    protected:
        Decorator to make read-only, including in subclasses.
"""

__all__ = [
    "IMPL",
    "MISSING",
    "ParamClass",
    "ProtectedError",
    "RawParamClass",
    "isparamclass",
    "protected",
]

from .paramclasses import (
    IMPL,
    MISSING,
    ParamClass,
    ProtectedError,
    RawParamClass,
    isparamclass,
    protected,
)
