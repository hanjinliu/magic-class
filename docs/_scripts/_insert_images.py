from __future__ import annotations

import re
from pathlib import Path
from textwrap import dedent
import mkdocs_gen_files
from qtpy.QtWidgets import QApplication
from magicgui.widgets import Widget

DOCS = Path(__file__).parent.parent
PATTERN = re.compile(r"``` ?python\n.+?\n```\n\n!\[.*?\]\(.+?\)", re.DOTALL)
MKIMAGE = re.compile(r"!\[.*?\]\((.+?)\)")

def _refresh():
    for w in QApplication.topLevelWidgets():
        w.close()
        w.deleteLater()
    QApplication.processEvents()

class CodeInfo:
    def __init__(self, code: str, dest: str):
        self.code = code
        self.dest = dest

    @classmethod
    def from_string(self, s: str) -> CodeInfo | None:
        # "s" is a string of the form:
        # ``` python
        # ...
        # ui = A()
        # ui.show()
        # ```
        #
        # ![](result.png)
        lines = s.splitlines()
        line0 = lines[0]
        if not line0.startswith("``` python"):
            return None
        lines_filt = []
        for _l in lines[1:]:
            if _l.strip() == "ui.show()":
                continue
            if _l.startswith("``` python"):
                lines_filt.clear()
                continue
            lines_filt.append(_l)

        code, *rest = "\n".join(lines_filt).split("```")
        if len(rest) != 1:
            raise ValueError(s)
        dest = next(MKIMAGE.finditer(rest[0].strip())).group(1)
        if "images_autogen" not in dest:
            return None
        return CodeInfo(code.strip(), dest.split("images_autogen")[-1][1:])

    def save_images(self, ns: dict) -> None:
        try:
            exec(self.code, ns, ns)
        except NameError as e:
            e.args = (f"{e}\n\ncaused by:\n{self.code}",)
            raise e

        if "ui" not in ns:
            widget_name = self.code.rsplit("\n", 1)[1]
            ui = ns.pop(widget_name)
        else:
            ui = ns.pop("ui")
        if not isinstance(ui, Widget):
            raise TypeError(f"{ui} is not a magicgui widget")
        ui.min_width = 200
        ui.show(run=False)
        ui.native.activateWindow()

        path = f"images_autogen/{self.dest}"
        with mkdocs_gen_files.FilesEditor.current().open(path, "wb") as f:
            ui.native.grab().save(f.name)
        ui.close()
        _refresh()

def main() -> None:
    for mdfile in sorted(DOCS.rglob("*.md"), reverse=True):
        md = mdfile.read_text()
        ns = {}
        for code in PATTERN.finditer(md):
            code = dedent(code.group(0))
            info = CodeInfo.from_string(code)
            if info is None:
                continue
            info.save_images(ns)
        _refresh()

main()
