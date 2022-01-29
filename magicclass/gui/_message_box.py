from __future__ import annotations
from qtpy.QtWidgets import QMessageBox, QTextEdit, QDialog, QVBoxLayout

class QtTracebackDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Traceback")
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # prepare text edit
        self._text = QTextEdit(self)
        self._text.setReadOnly(True)
        self._text.setFontFamily("Consolas")
        layout.addWidget(self._text)
    
    def setText(self, text: str):
        self._text.setText(text)
        

class QtErrorMessageBox(QMessageBox):        
    def __init__(self, title: str, text: str, parent):
        super().__init__(QMessageBox.Critical, 
                         str(title),
                         str(text),
                         QMessageBox.Ok | QMessageBox.Help,
                         parent=parent)
        
        self.traceback_button = self.button(QMessageBox.Help)
        self.traceback_button.setText("Show trackback")
        
    def exec_(self):
        returned = super().exec_()
        if returned == QMessageBox.Help:
            import traceback
            tb = traceback.format_exc()
            dlg = QtTracebackDialog(self)
            dlg.setText(tb)
            dlg.exec_()
        return returned
    
    @classmethod
    def raise_(cls, e: Exception, parent=None):
        self = cls(type(e).__name__, e, parent)
        self.exec_()