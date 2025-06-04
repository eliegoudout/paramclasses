from mypy.plugin import Plugin, MethodSigContext, FunctionContext
from mypy.types import CallableType, Type

class MyPlugin(Plugin):
    def get_function_hook(self, fullname: str) -> Callable[[FunctionContext], Type] | None:
        # print(f"[get_function_hook] → {fullname}")
        if fullname == "test.f":
            return lambda _ctx: int
        return None


    def get_function_signature_hook(self, *a, **kw):
        """is used to adjust the signature of a function.
        """
        # fullname = a[0]
        # if fullname.startswith("paramclasses") or fullname.startswith("mwe"):
        #     print(f"[get_function_signature_hook] → {a}, {kw}")

    def get_method_hook(self, *a, **kw):
        """is the same as get_function_hook() but for methods instead of module level functions.
        """
        # print(f"[get_method_hook] → {a}, {kw}")

    def get_method_signature_hook(self, *a, **kw):
        """is used to adjust the signature of a method. This includes special Python methods except __init__() and __new__(). For example in this code:

    from ctypes import Array, c_int

    x: Array[c_int]
    x[0] = 42

    mypy will call get_method_signature_hook("ctypes.Array.__setitem__") so that the plugin can mimic the ctypes auto-convert behavior.
        """
        # fullname = a[0]
        # if fullname.startswith("paramclasses") or fullname.startswith("mwe"):
        #     print(f"[get_method_signature_hook] → {a}, {kw}")

    def get_attribute_hook(self, *a, **kw):
        """overrides instance member field lookups and property access (not method calls). This hook is only called for fields which already exist on the class. Exception: if __getattr__ or __getattribute__ is a method on the class, the hook is called for all fields which do not refer to methods.
        """
        # print(f"[get_attribute_hook] → {a}, {kw}")

    def get_class_attribute_hook(self, *a, **kw):
        """is similar to above, but for attributes on classes rather than instances. Unlike above, this does not have special casing for __getattr__ or __getattribute__.
        """
        # print(f"[get_class_attribute_hook] → {a}, {kw}")

    def get_class_decorator_hook(self, *a, **kw):
        """can be used to update class definition for given class decorators. For example, you can add some attributes to the class to match runtime behaviour:

    from dataclasses import dataclass

    @dataclass  # built-in plugin adds `__init__` method here
    class User:
        name: str

    user = User(name='example')  # mypy can understand this using a plugin
        """
        # print(f"[get_class_decorator_hook] → {a}, {kw}")

    def get_metaclass_hook(self, *a, **kw):
        """is similar to above, but for metaclasses.
        """
        # # print(f"[get_metaclass_hook] → {a}, {kw}")

    def get_base_class_hook(self, *a, **kw):
        """is similar to above, but for base classes.
        """
        # # print(f"[get_base_class_hook] → {a}, {kw}")

    def get_dynamic_class_hook(self, *a, **kw):
        """can be used to allow dynamic class definitions in mypy. This plugin hook is called for every assignment to a simple name where right hand side is a function call:

    from lib import dynamic_class

    X = dynamic_class('X', [])

    For such definition, mypy will call get_dynamic_class_hook("lib.dynamic_class"). The plugin should create the corresponding mypy.nodes.TypeInfo object, and place it into a relevant symbol table. (Instances of this class represent classes in mypy and hold essential information such as qualified name, method resolution order, etc.)
        """
        # print(f"[get_dynamic_class_hook] → {a}, {kw}")

    def get_customize_class_mro_hook(self, *a, **kw):
        """can be used to modify class MRO (for example insert some entries there) before the class body is analyzed.
        """
        # print(f"[get_customize_class_mro_hook] → {a}, {kw}")

    def get_additional_deps(self, *a, **kw):
        """can be used to add new dependencies for a module. It is called before semantic analysis. For example, this can be used if a library has dependencies that are dynamically loaded based on configuration information.
        """
        # print(f"[get_additional_deps] → {a}, {kw}")
        return ()

    def report_config_data(self, *a, **kw):
        """"""
        # print(f"[report_config_data] → {a}, {kw} ")

def plugin(version):
    return MyPlugin