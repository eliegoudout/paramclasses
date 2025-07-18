"""Mypy plugin for paramclasses."""

from mypy.plugin import Plugin


class CustomPlugin(Plugin):
    """The plugin."""

    def get_function_hook(self, fullname: str) -> type | None:
        """Change signature of functions."""
        if fullname == "paramclasses.paramclasses.foo":
            return bool
        return None


def plugin(_version: str) -> Plugin:
    """Follow tuto."""
    # ignore version argument if the plugin works with all mypy versions.
    return CustomPlugin
