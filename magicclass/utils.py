import inspect

def iter_members(cls:type, exclude_prefix:str="_") -> str:
    for name, _ in inspect.getmembers(cls):
        if name.startswith(exclude_prefix):
            continue
        yield name

def check_collision(cls0:type, cls1:type):
    mem0 = set(iter_members(cls0, exclude_prefix="__"))
    mem1 = set(iter_members(cls1, exclude_prefix="__"))
    collision = mem0 & mem1
    if collision:
        raise AttributeError(f"Collision: {collision}")
        