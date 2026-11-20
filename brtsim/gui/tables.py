"""Tables that show and edit lists of the scenario."""

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, Signal
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QTableView, QTableWidget, QTableWidgetItem

OPTIONAL_INT = "optional int"  # an integer, or nothing


def format_time(seconds):
    """A time of the day given in seconds, as HH:MM:SS."""
    seconds = int(seconds)
    return f"{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


def parse_time(text):
    """The seconds of a time written as HH:MM, HH:MM:SS or directly in seconds."""
    parts = str(text).strip().split(":")
    if len(parts) == 1:
        return int(parts[0])
    if len(parts) not in (2, 3):
        raise ValueError("a time is written as HH:MM:SS")
    hours, minutes, *rest = (int(part) for part in parts)
    seconds = rest[0] if rest else 0
    if not (0 <= minutes < 60 and 0 <= seconds < 60 and hours >= 0):
        raise ValueError("a time is written as HH:MM:SS")
    return hours * 3600 + minutes * 60 + seconds


class Column:
    """A column of a table: how the value of an item is read, written and checked.

    get(item) gives the value and set(item, value) stores it, a column without set is read only.
    kind is the type of the value: str, int, float, bool or OPTIONAL_INT.
    check(item, value) gives the reason why a value is not accepted, or None.
    show(value) gives the text to display, parse(text) the value of a text.
    """

    def __init__(self, title, get, set=None, kind=str, check=None, tip="", show=None, parse=None):
        self.title = title
        self.get = get
        self.set = set
        self.kind = kind
        self.check = check
        self.tip = tip
        self.show = show
        self.parse = parse

    def convert(self, value):
        if self.parse is not None:
            return self.parse(value)
        if self.kind is int:
            number = float(value)
            if number != int(number):
                raise ValueError("an integer is expected")
            return int(number)
        if self.kind is float:
            return float(value)
        if self.kind == OPTIONAL_INT:
            return None if str(value).strip() == "" else int(float(value))
        return str(value).strip()

    def text(self, value):
        if self.show is not None:
            return self.show(value)
        if value is None:
            return ""
        if isinstance(value, float):
            return f"{value:.6g}"
        return str(value)


class ItemTableModel(QAbstractTableModel):
    """A table with one row per item of a list of the scenario and the given columns."""

    rejected = Signal(str)  # a value was not accepted, with the reason

    def __init__(self, document, items, columns, parent=None):
        super().__init__(parent)
        self.document = document
        self.items = items  # a function that gives the current list of items
        self.columns = columns

    def refresh(self):
        self.beginResetModel()
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.items())

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.columns)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal:
            if role == Qt.DisplayRole:
                return self.columns[section].title
            if role == Qt.ToolTipRole:
                return self.columns[section].tip or None
        elif role == Qt.DisplayRole:
            return section + 1
        return None

    def flags(self, index):
        column = self.columns[index.column()]
        flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        if column.set is not None:
            flags |= Qt.ItemIsUserCheckable if column.kind is bool else Qt.ItemIsEditable
        return flags

    def data(self, index, role=Qt.DisplayRole):
        column = self.columns[index.column()]
        value = column.get(self.items()[index.row()])
        if column.kind is bool:
            if role == Qt.CheckStateRole:
                return Qt.Checked if value else Qt.Unchecked
            return None
        if role == Qt.DisplayRole:
            return column.text(value)
        if role == Qt.EditRole:
            return column.text(value) if column.show is not None or value is None else value
        if role == Qt.TextAlignmentRole and column.kind in (int, float, OPTIONAL_INT):
            return int(Qt.AlignRight | Qt.AlignVCenter)
        if role == Qt.ToolTipRole:
            return column.tip or None
        return None

    def setData(self, index, value, role=Qt.EditRole):
        column = self.columns[index.column()]
        item = self.items()[index.row()]
        if column.set is None:
            return False
        if column.kind is bool:
            if role != Qt.CheckStateRole:
                return False
            value = value in (Qt.Checked, Qt.Checked.value, True)
        elif role != Qt.EditRole:
            return False
        else:
            try:
                value = column.convert(value)
            except (ValueError, TypeError) as error:
                self.rejected.emit(f"{column.title}: {error}")
                return False
        if value == column.get(item):
            return True
        problem = column.check(item, value) if column.check else None
        if problem:
            self.rejected.emit(f"{column.title}: {problem}")
            return False
        with self.document.edit():
            column.set(item, value)
        # other columns of the row may depend on the value
        self.dataChanged.emit(self.index(index.row(), 0), self.index(index.row(), len(self.columns) - 1))
        return True


def table_view(model, stretch_last=True):
    view = QTableView()
    view.setModel(model)
    view.setAlternatingRowColors(True)
    view.setSelectionBehavior(QAbstractItemView.SelectRows)
    view.setSelectionMode(QAbstractItemView.SingleSelection)
    view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
    view.horizontalHeader().setStretchLastSection(stretch_last)
    view.verticalHeader().setDefaultSectionSize(24)
    return view


def fill_table(widget: QTableWidget, frame, decimals=2):
    """Shows a pandas table in a read only table widget."""
    widget.clear()
    widget.setRowCount(len(frame.index))
    widget.setColumnCount(len(frame.columns))
    widget.setHorizontalHeaderLabels([str(column) for column in frame.columns])
    widget.setVerticalHeaderLabels([str(label) for label in frame.index])
    for row in range(len(frame.index)):
        for column in range(len(frame.columns)):
            value = frame.iat[row, column]
            text = f"{value:,.{decimals}f}" if isinstance(value, float) else str(value)
            item = QTableWidgetItem(text)
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            widget.setItem(row, column, item)
    widget.resizeColumnsToContents()
