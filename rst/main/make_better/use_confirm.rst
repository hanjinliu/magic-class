====================
Pre-run Confirmation
====================

.. code-block:: python

    from magicclass import magicclass, confirm

    @magicclass
    class A:
        @confirm(condition="0<= ratio <=1")
        def func(self, ratio: float):
            ...

TODO
