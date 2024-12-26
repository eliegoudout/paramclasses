"""To do."""

from paramclasses import ParamClass, protected


def test_trivial() -> None:
    """Test trivial example."""

    class A(ParamClass):
        x: ...
        y: int = 5
        z: property = property(lambda _: ...)

        @protected
        def f(self) -> int:
            return 6

    A()  # Should work
