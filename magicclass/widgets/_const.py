from __future__ import annotations

import sys

if sys.platform == "win32":
    FONT = "Consolas"
elif sys.platform == "darwin":
    FONT = "Menlo"
else:
    FONT = "Monospace"
