import numpy as np

def convert_color_code(c):
    if not isinstance(c, str):
        c = np.asarray(c) * 255
    return c