import inspect
from qtpy.QtWidgets import QApplication

APPLICATION = None

def iter_members(cls:type, exclude_prefix:str="_") -> str:
    """
    Iterate over all the members in the order of source code line number. 
    """    
    members = filter(lambda x: not x[0].startswith(exclude_prefix),
                     inspect.getmembers(cls)
                     )
    return map(lambda x: x[0], sorted(members, key=get_line_number))

def check_collision(cls0:type, cls1:type):
    """
    Check if two classes have name collisions.
    """    
    mem0 = set(iter_members(cls0, exclude_prefix="__"))
    mem1 = set(iter_members(cls1, exclude_prefix="__"))
    collision = mem0 & mem1
    if collision:
        raise AttributeError(f"Collision: {collision}")

def get_line_number(member) -> int:
    """
    Get the line number of a member function in the source code.
    """    
    try:
        n = member[1].__code__.co_firstlineno
    except AttributeError:
        n = -1
    return n

def gui_qt():
    """
    Call "%gui qt" magic,
    """    
    try:
        from IPython import get_ipython
    except ImportError:
        get_ipython = lambda: False

    shell = get_ipython()
    
    if shell and shell.active_eventloop != "qt":
        shell.enable_gui("qt")
    return None

def get_app():
    """
    Get QApplication. This is important when using Jupyter.
    """    
    gui_qt()
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    global APPLICATION
    APPLICATION = app
    return app

def exec_app():
    """
    Execute QApplication. This function must be called right after showing some QWidget.
    """    
    app = QApplication.instance()
    app.exec_()
    return None