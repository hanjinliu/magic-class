import re

shared_docs = {
    "x": """
        x : array-like
            X data.""",
    "y": """
        y : array-like
            Y data.""",
    "face_color": """
        face_color: str or array-like, optional
            Face color of plot. Graphic object will be filled with this color.""",
    "edge_color": """
        edge_color: str or array-like, optional
            Edge color of plot.""",
    "color": """
        color: str or array-like, optional
            Set face color and edge color at the same time.""",
    "name": """
        name: str, optional
            Object name of the plot item.""",
    "lw": """
        lw: float, default is 1.0
            Line width of edge.""",
    "ls": """
        ls: str, default is "-"
            Line style of edge. One of "-", "--", ":" or "-.".""",
    "symbol": """
        symbol: str, optional
            Symbol style. Currently supports circle ("o"), cross ("+", "x"), star ("*"),
            square ("s", "D") triangle ("^", "<", "v", ">") and others that ``pyqtgraph``
            supports.""",
}


def write_docs(func):
    doc = func.__doc__
    if doc is not None:
        summary, params, rest = _split_doc(doc)
        for key, value in shared_docs.items():
            value = value.strip()
            params = re.sub("{" + key + "}", value, params)
        doc = _merge_doc(summary, params, rest)
        func.__doc__ = doc
    return func


def _split_doc(doc: str):
    summary, other = doc.split("Parameters\n")
    params, rest = other.split("Returns\n")
    return summary, params, rest


def _merge_doc(summary, params, rest):
    return summary + "Parameters\n" + params + "Returns\n" + rest
