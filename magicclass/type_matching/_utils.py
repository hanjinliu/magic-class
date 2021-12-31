# from magicgui/type_map.py
def is_subclass(obj, superclass):
    """Safely check if obj is a subclass of superclass."""
    try:
        return issubclass(obj, superclass)
    except Exception:
        return False