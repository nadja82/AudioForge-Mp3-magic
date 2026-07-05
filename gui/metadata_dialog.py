from __future__ import annotations
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout

FIELDS = [("title","Titel"),("artist","Artist"),("album","Album"),("albumartist","Album Artist"),("genre","Genre"),("date","Jahr/Datum"),("tracknumber","Track-Nr."),("comment","Kommentar")]

class MetadataDialog(QDialog):
    def __init__(self, tags: dict[str, str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Metadaten bearbeiten"); self.setMinimumWidth(460); self.apply_to_all = False
        self.edits: dict[str, QLineEdit] = {}
        layout = QVBoxLayout(self)
        hint = QLabel("Leere Felder bleiben leer. Mit ‘Auf alle anwenden’ werden diese Werte für alle Dateien übernommen."); hint.setWordWrap(True); layout.addWidget(hint)
        form = QFormLayout()
        for key, label in FIELDS:
            edit = QLineEdit(tags.get(key, "")); self.edits[key] = edit; form.addRow(label + ":", edit)
        layout.addLayout(form)
        row = QHBoxLayout(); btn = QPushButton("Auf alle anwenden"); btn.clicked.connect(self._accept_all); row.addWidget(btn); row.addStretch(1); layout.addLayout(row)
        box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel); box.accepted.connect(self.accept); box.rejected.connect(self.reject); layout.addWidget(box)
    def _accept_all(self) -> None:
        self.apply_to_all = True; self.accept()
    def values(self) -> dict[str, str]:
        return {k: e.text().strip() for k, e in self.edits.items()}
