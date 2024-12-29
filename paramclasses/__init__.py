"""Package implementing `ParamClass`.

Exposed API:
    ParamClass:
        Parameter-holding class with robust subclassing protection.
    ProtectedError:
        Don't assign or delete protected attributes.
    isparamclass:
        Check if `cls` is a paramclass.
    protected:
        Decorator to make read-only, including in subclasses.
"""

__all__ = ["ParamClass", "ProtectedError", "isparamclass", "protected"]

from .paramclasses import ParamClass, ProtectedError, isparamclass, protected
