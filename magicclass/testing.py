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


def click_all(ui):
    # TODO
    ...
