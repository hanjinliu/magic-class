=======================
Set Choices Dynamically
=======================

Choices in magicgui
-------------------

Some ``magicgui`` widgets, such as ``ComboBox`` and ``Select``, support ``"choices"`` option.
This option no only accept static choices like ``choices=["a", "b", "c"]`` but choices that
can be dynamically changed are also supported by giving a choice-getter function.

.. code-block:: python

    from magicgui.widgets import ComboBox
    import random

    def _get_choices(widget=None):
        # prepare choices randomly.
        return random.choices([1, 2, 3, 4], k=2)

    wdt = ComboBox(choices=_get_choices)

In the example above, choices of the ``ComboBox`` widget are defined by the ``_get_choices``
function and will be resampled when ``reset_choices`` is called.

If you want to create ``FunctionGui`` with dynamic choices, your code will look like this.

.. code-block:: python

    from magicgui import magicgui

    @magicgui(a={"choices": _get_choices})
    def func(a):
        """do something"""

To resample choices, you only have to call the ``reset_choices`` method on the parent widget.

.. code-block:: python

    func.reset_choices()

Use Methods
-----------

Similar to the ``"bind"`` option, you can set method defined in a magic-class to ``"choices"``
option (See :doc:`use_bind`). Magic-class will call it as an instance method every time
choices need resetting. A choices option should be set using ``set_options`` wrapper as usual.

Following example is a simple file explorer made of ``magicclass``. Since you have to reset
choices every time current directory is changed, the ``"chocies"`` options is very important.

.. code-block:: python

    import os
    from magicclass import magicclass, set_options

    RETURN = "../"

    @magicclass
    class Main:
        def __init__(self):
            self._cd = os.getcwd()  # get current directory

        def _get_files(self, w=None):
            return os.listdir(self._cd) + [RETURN]

        @set_options(f={"choices": _get_files})
        def set_directory(self, f: str):
            if f == RETURN:
                self._cd = os.path.dirname(self._cd)  # move back to the parent directory
            else:
                self._cd = os.path.join(self._cd, f)  # go to new directory
            self.reset_choices()

        def show_current_directory(self):
            print(self._cd)


Choices in MagicField
---------------------

Unlike the ``"bind"`` option, ``"choices"`` option is sometimes useful in ``MagicField``
(if you are not familiar with fields, see :doc:`use_field`). Methods defined in a magic class
can also be used in ``MagicField`` object.

Following example is a file explorer similar to the previous one but defined using ``MagicField``.

.. code-block:: python

    import os
    from magicclass import magicclass, set_options, field
    from magicgui.widgets import RadioButtons

    RETURN = "../"

    @magicclass
    class Main:
        def _get_files(self, w=None):
            return os.listdir(self.cd.value) + [RETURN]

        cd = field(os.getcwd(), enabled=False)
        files = field(RadioButtons, options={"choices": _get_files})

        def goto(self):
            f = self.files.value
            if f == RETURN:
                self.cd.value = os.path.dirname(self.cd.value)  # move back to the parent directory
            else:
                self.cd.value = os.path.join(self.cd.value, f)  # go to new directory
            self.reset_choices()
