
import pytest

from paramclasses import ParamClass, protected


@pytest.mark.mypy_testing
def test_a():
    """Test identified cases (no test for now)."""
    class A(ParamClass):
        x1: int = 0
        x2: int = protected(0)  # Should PASS
        x3: int = protected(None)  # Should FAIL (None)
        x4 = protected(0)

        @protected  # Should PASS
        @property
        def y(self) -> int:
            return self.x1 + self.x2 + self.x4  # Should PASS

        @protected
        def z(self) -> int:
            return self.x1 + self.x2 + self.x4  # Should PASS

        @property
        def t(self) -> int:
            y: int = self.y  # Should PASS
            z: int = self.z()  # Should PASS
            return y + z

    A(x1=None)  # Should FAIL (None)
    A(0)  # Should FAIL (signature)
    A(y=0)  # Should FAIL (signature)
    A(x2=0)  # Should FAIL (Final)
    a = A()
    A.x1 = None  # Should FAIL (None)
    a.x1 = None  # Should FAIL (None)
    A.x2 = 0  # Should FAIL (Final)
    a.x2 = 0  # Should FAIL (Final)
    A.x4 = 0  # Should FAIL (Final)
    a.x4 = 0  # Should FAIL (Final)
    A.y = lambda: 0  # Should FAIL (final)
    a.y = lambda: 0  # Should FAIL (read-only property)
    A.z = 0  # Should FAIL (final)
    a.z = 0  # Should FAIL (final)
