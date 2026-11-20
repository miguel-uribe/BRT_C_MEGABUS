"""The scenario being edited: its file, whether it has unsaved changes and the history to undo them."""

from contextlib import contextmanager
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from .. import model

HISTORY_SIZE = 100


class Document(QObject):
    changed = Signal()  # the scenario was edited
    reloaded = Signal()  # the scenario was replaced by another one: a file was opened or a change was undone

    def __init__(self, scenario=None, path=None):
        super().__init__()
        self.scenario = scenario or model.Scenario(name="New scenario", length=1000, lanes=1)
        self.path = Path(path) if path else None
        self.dirty = False
        self._undo = []
        self._redo = []

    @contextmanager
    def edit(self):
        """Every change to the scenario is made inside this block, so that it can be undone."""
        before = model.to_dict(self.scenario)
        yield
        self._undo.append(before)
        del self._undo[:-HISTORY_SIZE]
        self._redo.clear()
        self.dirty = True
        self.changed.emit()

    def can_undo(self):
        return bool(self._undo)

    def can_redo(self):
        return bool(self._redo)

    def undo(self):
        if self._undo:
            self._redo.append(model.to_dict(self.scenario))
            self._restore(self._undo.pop())

    def redo(self):
        if self._redo:
            self._undo.append(model.to_dict(self.scenario))
            self._restore(self._redo.pop())

    def _restore(self, snapshot):
        self.scenario = model.from_dict(snapshot)
        self.dirty = True
        self.reloaded.emit()
        self.changed.emit()

    def open(self, path):
        scenario = model.load(path)  # raises before anything is replaced
        self.scenario = scenario
        self.path = Path(path)
        self.dirty = False
        self._undo.clear()
        self._redo.clear()
        self.reloaded.emit()
        self.changed.emit()

    def save(self, path=None):
        path = Path(path) if path else self.path
        if path is None:
            raise ValueError("The scenario has no file yet")
        model.save(self.scenario, path)
        self.path = path
        self.dirty = False
        self.changed.emit()
