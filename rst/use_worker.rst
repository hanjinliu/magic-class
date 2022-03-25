===============
Multi-threading
===============

Multi-threading is an important idea in GUI development. If you want to
implement background execution or progress bar, you'll usually have to
rely on multi-threading.

Since ``magic-class >= 0.6.1``, a helper class ``thread_worker`` is available.
It makes multi-threaded implementation much easier, without rewriting the
existing single-threaded code. To use it, you have to install ``superqt``.

.. code-block::

    pip install superqt

Then it is available in:

.. code-block:: python

    from magicclass.qthreading import thread_worker

.. note::

    It is named after the ``thread_worker`` function originally defined in
    ``superqt`` and ``napari``, which create a new function that will return
    a "worker" of the original function.

    .. code-block:: python

        from napari.utils import thread_worker

        @thread_worker
        def func():
            # do something

        worker = func()  # worker is ready to run the original "func"
        worker.start()  # the original "func" actually get called

    On the other hand, ``magic-class``'s ``thread_worker`` is a class. It
    returns a ``thread_worker`` object instead of a new function. A
    ``thread_worker`` object will create a function that will start a worker
    every time it is accessed via ``self.func``. Although they are designed
    differently, they share very similar API.


Basic Usage
-----------

Decorate the methods you want to be multi-threaded and that's it!

.. code-block:: python

    import time
    from magicclass import magicclass
    from magicclass.qthreading import thread_worker

    @magicclass
    class Main:
        @thread_worker
        def func(self):
            for i in range(10):
                time.sleep(0.2)  # time consuming function
                print(i)

    ui = Main()
    ui.show()

During execution of ``func``, the GUI window will not get frozen because
function is running in another thread.

.. note::

    If you are running functions programatically, GUI window will be disabled as
    usual. This is because the ``run`` method of ``QRunnable`` is called in the
    main thread, otherwise the second line of code will be executed *before* the
    first line of code actually finishes. This behavior is important to keep
    manual and programatical execution consistent.

If decorated method is a generator, worker will iterate over it until it ends.
In the following example:

.. code-block:: python

    import time
    from magicclass import magicclass
    from magicclass.qthreading import thread_worker

    @magicclass
    class Main:
        @thread_worker
        def func(self):
            for i in range(3):
                print(i)
                yield i

    ui = Main()
    ui.show()

after you click the "func" button you'll get output like this.

.. code-block::

    0
    1
    2

Connect Callbacks
-----------------

Just like ``superqt`` and ``napari``, you can connect callback functions to
``thread_worker`` objects. There are six types of callbacks.

* ``started`` ... called when worker started.
* ``returned`` ... called when worker returned some values.
* ``errored`` ... called when worker raised an error.
* ``yielded`` ... called when worker yielded values.
* ``finished`` ... called when worker finished.
* ``aborted`` ... called when worker was aborted by some reasons.

Following example shows how you can update widget every 0.3 second.

.. code-block:: python

    import time
    from magicclass import magicclass, vfield
    from magicclass.qthreading import thread_worker

    @magicclass
    class Main:
        yielded_value = vfield(str)
        returned_value = vfield(str)

        @thread_worker
        def func(self, n: int = 10):
            for i in range(n):
                yield str(i)
                time.sleep(0.3)
            return "finished"

        @func.yielded.connect
        def _on_yield(self, value):
            self.yielded_value = value

        @func.returned.connect
        def _on_return(self, value):
            self.returned_value = value

    ui = Main()
    ui.show()

Use Progress Bar
----------------

Just like ``napari``, you can use the embeded progress bar to display the progress
of the current function call using ``progress=...`` argument. Same options are
available in ``magic-class`` but you can choose which progress bar to use.

1. If the main window does not have ``magicgui.widgets.ProgressBar`` widget, a popup
   progress bar widget will be created. ``napari``'s progress bar will be used instead
   if it is available.

    .. code-block:: python

        @magicclass
        class Main:
            @thread_worker(progress={"total": 10})
            def func(self):
            for i in range(10):
                time.sleep(0.1)

2. If the main window has at least one ``magicgui.widgets.ProgressBar`` widget, the
   first one will be used.

    .. code-block:: python

        @magicclass
        class Main:
            pbar = field(ProgressBar)
            @thread_worker(progress={"total": 10})
            def func(self):
            for i in range(10):
                time.sleep(0.1)

3. If "pbar" option is given, progress bar specified by this option will be used.

    .. code-block:: python

        @magicclass
        class Main:
            pbar1 = field(ProgressBar)
            pbar2 = field(ProgressBar)

            @thread_worker(progress={"total": 10, "pbar": pbar1})
            def func(self):
                for i in range(10):
                    time.sleep(0.1)
