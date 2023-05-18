from magicclass import MagicTemplate, abstractapi, get_function_gui
from magicclass._gui.mgui_ext import PushButtonPlus, Action


class MockConfirmation:
    """Class used for confirmation test."""

    def __init__(self):
        self.text = None
        self.gui = None

    def __call__(self, text, gui):
        self.text = text
        self.gui = gui

    @property
    def value(self):
        return self.text, self.gui

    def assert_value(self, text=None, gui=None):
        if text is None and gui is None:
            assert self.text is not None and self.gui is not None
        elif text is None:
            assert self.gui is gui
        elif gui is None:
            assert self.text == text
        else:
            assert self.value == (text, gui)

    def assert_not_called(self):
        assert self.text is None and self.gui is None


def _iter_method_with_button(ui):
    for child in ui:
        if isinstance(child, (PushButtonPlus, Action)):
            method = getattr(ui, child.name)
            if callable(method) and not isinstance(method, abstractapi):
                yield method
        if isinstance(child, MagicTemplate):
            yield from _iter_method_with_button(child)


def assert_function_gui_buildable(ui: MagicTemplate):
    """Assert that all methods in ``ui`` can be built into GUI."""

    for method in _iter_method_with_button(ui):
        get_function_gui(method)
