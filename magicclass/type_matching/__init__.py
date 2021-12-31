"""
Enable type matching of tuple/list types in magicgui.
Annotations such as ``tuple[int, str]`` and ``list[float]`` can be
converted into TupleEdit or ListEdit. Type matching will be enabled 
just by importing them like:

>>> from magicclass.type_matching import tuple_type  # enable tuple
>>> from magicclass.type_matching import list_type  # enable list

"""