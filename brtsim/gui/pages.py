"""The pages of the main window where the scenario is edited."""

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QPointF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..model import Phase
from .tables import OPTIONAL_INT, Column, ItemTableModel, format_time, parse_time, table_view

NO_SERVICE_HEADWAY = 1000000  # the headway of a service without buses


class Page(QWidget):
    """A page of the main window. It shows the scenario of the document, which may be replaced at any time."""

    title = ""
    message = Signal(str)  # something to tell the user, such as the reason why a value was not accepted

    def __init__(self, document):
        super().__init__()
        self.document = document
        document.reloaded.connect(self.refresh)

    @property
    def scenario(self):
        return self.document.scenario

    def refresh(self):
        """Shows the scenario again, after it was replaced."""

    def table(self, items, columns):
        model = ItemTableModel(self.document, items, columns, self)
        model.rejected.connect(self.message)
        return model, table_view(model)


def heading(text, detail=""):
    label = QLabel(f"<h2>{text}</h2>" + (f"<p>{detail}</p>" if detail else ""))
    label.setWordWrap(True)
    return label


# ---------------------------------------------------------------------------------------------
class ServicesPage(Page):
    title = "Services"

    def __init__(self, document):
        super().__init__(document)

        def frequency(service):
            return 0.0 if service.headway >= NO_SERVICE_HEADWAY else 3600 / service.headway

        def set_frequency(service, value):
            service.headway = NO_SERVICE_HEADWAY if value == 0 else max(1, round(3600 / value))

        def stops(service):
            return sum(1 for station in self.scenario.stations for bay in station.bays if service.name in bay.services)

        columns = [
            Column("Service", lambda service: service.name),
            Column(
                "Headway (s)",
                lambda service: service.headway,
                lambda service, value: setattr(service, "headway", value),
                kind=int,
                check=lambda service, value: None if value > 0 else "the headway must be positive",
                tip="The seconds between two buses of the service",
            ),
            Column(
                "Buses per hour",
                frequency,
                set_frequency,
                kind=float,
                check=lambda service, value: None if value >= 0 else "the frequency must not be negative",
                show=lambda value: f"{value:.2f}",
                tip="The frequency of the service, zero for a service without buses",
            ),
            Column(
                "Biarticulated (%)",
                lambda service: service.biarticulated_percent,
                lambda service, value: setattr(service, "biarticulated_percent", value),
                kind=int,
                check=lambda service, value: None if 0 <= value <= 100 else "a percentage between 0 and 100 is expected",
                tip="The percentage of the buses of the service that are biarticulated",
            ),
            Column(
                "First bus (s)",
                lambda service: service.offset,
                lambda service, value: setattr(service, "offset", value),
                kind=OPTIONAL_INT,
                check=lambda service, value: None if value is None or value >= 0 else "the offset must not be negative",
                show=lambda value: "random" if value is None else str(value),
                tip="The time of the first bus, counted within the headway. Leave it empty for a random time in each simulation",
            ),
            Column("Stops", stops, kind=int),
            Column("Start cell", lambda service: service.start_x, kind=int),
            Column("End cell", lambda service: service.end_x, kind=int),
            Column("Changes into", lambda service: service.becomes or ""),
        ]
        self.model, view = self.table(lambda: self.scenario.services, columns)
        layout = QVBoxLayout(self)
        layout.addWidget(heading("Services", "The frequency of each service. The path and the stops of the services are part of the network."))
        layout.addWidget(view, 1)

    def refresh(self):
        self.model.refresh()


# ---------------------------------------------------------------------------------------------
class FleetPage(Page):
    title = "Fleet"

    def __init__(self, document):
        super().__init__(document)

        def check_name(depot, value):
            if not value:
                return "a name is needed"
            if any(other.name == value for other in self.scenario.depots if other is not depot):
                return f"there is already a depot named {value}"
            return None

        columns = [
            Column("Depot", lambda depot: depot.name, lambda depot, value: setattr(depot, "name", value), check=check_name),
            Column(
                "Initial buses",
                lambda depot: depot.initial_buses,
                lambda depot, value: setattr(depot, "initial_buses", value),
                kind=int,
                check=lambda depot, value: None if value >= 0 else "the number of buses must not be negative",
                tip="The buses parked at the depot when the simulation starts",
            ),
            Column("Buses leave at cell", lambda depot: depot.origin, kind=int, tip="The services starting at this cell take their buses from the depot"),
            Column("Buses return at cell", lambda depot: depot.end, kind=int, tip="The buses of the services ending at this cell are parked at the depot"),
        ]
        self.model, view = self.table(lambda: self.scenario.depots, columns)
        self.total = QLabel()
        layout = QVBoxLayout(self)
        layout.addWidget(heading("Fleet", "The buses available at each depot when the simulation starts."))
        layout.addWidget(view, 1)
        layout.addWidget(self.total)
        document.changed.connect(self.update_total)
        self.update_total()

    def update_total(self):
        self.total.setText(f"Total fleet: <b>{sum(depot.initial_buses for depot in self.scenario.depots)}</b> buses")

    def refresh(self):
        self.model.refresh()
        self.update_total()


# ---------------------------------------------------------------------------------------------
class TrafficLightsPage(Page):
    title = "Traffic lights"

    def __init__(self, document):
        super().__init__(document)
        self.names = QListWidget()
        self.names.setMaximumWidth(160)
        self.names.currentRowChanged.connect(self.show_traffic_light)

        self.offset = QSpinBox()
        self.offset.setRange(0, 100000)
        self.offset.setSuffix(" s")
        self.offset.setMaximumWidth(120)
        self.offset.setToolTip("The time already elapsed in the first phase when the simulation starts")
        self.offset.editingFinished.connect(self.set_offset)
        self.cycle = QLabel()
        self.signals = QLabel()
        self.signals.setWordWrap(True)

        self.phases = ItemTableModel(document, lambda: self.current.phases if self.current else [], [], self)
        self.phases.rejected.connect(self.message)
        self.phases_view = table_view(self.phases, stretch_last=False)
        add = QPushButton("Add phase")
        add.clicked.connect(self.add_phase)
        remove = QPushButton("Remove phase")
        remove.clicked.connect(self.remove_phase)

        form = QFormLayout()
        form.addRow("Offset:", self.offset)
        form.addRow("Cycle:", self.cycle)
        form.addRow("Signals:", self.signals)
        buttons = QHBoxLayout()
        buttons.addWidget(add)
        buttons.addWidget(remove)
        buttons.addStretch()
        detail = QWidget()
        right = QVBoxLayout(detail)
        right.addLayout(form)
        right.addWidget(QLabel("Phases, in order. A direction is in green when it is checked:"))
        right.addWidget(self.phases_view)
        right.addLayout(buttons)

        splitter = QSplitter()
        splitter.addWidget(self.names)
        splitter.addWidget(detail)
        splitter.setStretchFactor(1, 1)
        layout = QVBoxLayout(self)
        layout.addWidget(heading("Traffic lights", "The phases of each traffic light. Their positions are part of the network."))
        layout.addWidget(splitter, 1)
        document.changed.connect(self.update_cycle)
        self.refresh()

    @property
    def current(self):
        row = self.names.currentRow()
        lights = self.scenario.traffic_lights
        return lights[row] if 0 <= row < len(lights) else None

    def refresh(self):
        row = max(self.names.currentRow(), 0)
        self.names.blockSignals(True)
        self.names.clear()
        self.names.addItems([tl.name for tl in self.scenario.traffic_lights])
        self.names.blockSignals(False)
        if self.scenario.traffic_lights:
            self.names.setCurrentRow(min(row, len(self.scenario.traffic_lights) - 1))
        self.show_traffic_light()

    def show_traffic_light(self, *_):
        tl = self.current
        self.phases.beginResetModel()
        columns = []
        if tl is not None:
            columns.append(
                Column(
                    "Duration (s)",
                    lambda phase: phase.duration,
                    lambda phase, value: setattr(phase, "duration", value),
                    kind=int,
                    check=lambda phase, value: None if value > 0 else "the duration must be positive",
                )
            )
            for number, direction in enumerate(tl.directions):
                columns.append(
                    Column(
                        f"Green {direction}",
                        lambda phase, number=number: phase.green[number],
                        lambda phase, value, number=number: phase.green.__setitem__(number, value),
                        kind=bool,
                    )
                )
        self.phases.columns = columns
        self.phases.endResetModel()
        self.offset.setEnabled(tl is not None)
        self.offset.blockSignals(True)
        self.offset.setValue(tl.offset if tl else 0)
        self.offset.blockSignals(False)
        if tl is not None:
            heads = [f"{head.direction} at cell {head.x}, lane {head.lane}" for head in tl.heads]
            self.signals.setText("; ".join(heads) if heads else "not placed in the network")
        else:
            self.signals.setText("")
        self.update_cycle()

    def update_cycle(self):
        tl = self.current
        self.cycle.setText(f"{sum(phase.duration for phase in tl.phases)} s in {len(tl.phases)} phases" if tl else "")

    def set_offset(self):
        tl = self.current
        if tl is not None and tl.offset != self.offset.value():
            with self.document.edit():
                tl.offset = self.offset.value()

    def add_phase(self):
        tl = self.current
        if tl is None:
            return
        row = self.phases_view.currentIndex().row()
        row = len(tl.phases) if row < 0 else row + 1
        self.phases.beginInsertRows(QModelIndex(), row, row)
        with self.document.edit():
            tl.phases.insert(row, Phase(30, [False] * len(tl.directions)))
        self.phases.endInsertRows()

    def remove_phase(self):
        tl = self.current
        row = self.phases_view.currentIndex().row()
        if tl is None or row < 0:
            self.message.emit("Select the phase to remove")
            return
        if len(tl.phases) == 1:
            self.message.emit("A traffic light needs at least one phase")
            return
        self.phases.beginRemoveRows(QModelIndex(), row, row)
        with self.document.edit():
            del tl.phases[row]
        self.phases.endRemoveRows()


# ---------------------------------------------------------------------------------------------
class ProfilePlot(QWidget):
    """The demand profile as a curve."""

    def __init__(self, document):
        super().__init__()
        self.document = document
        self.setMinimumHeight(180)
        document.changed.connect(self.update)
        document.reloaded.connect(self.update)

    def paintEvent(self, event):
        demand = self.document.scenario.demand
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), self.palette().base())
        left, top, right, bottom = 70, 12, 16, 28
        width, height = self.width() - left - right, self.height() - top - bottom
        if len(demand.times) < 2 or width <= 0 or height <= 0:
            painter.drawText(self.rect(), Qt.AlignCenter, "The profile needs at least two points")
            return
        first, last = demand.times[0], demand.times[-1]
        highest = max(max(demand.rates), 1e-9)
        points = QPolygonF(
            [
                QPointF(left + width * (time - first) / (last - first), top + height * (1 - rate / highest))
                for time, rate in zip(demand.times, demand.rates)
            ]
        )
        text = self.palette().text().color()
        painter.setPen(QPen(text.lighter(250) if text.lightness() < 128 else text.darker(250), 1))
        painter.drawRect(left, top, width, height)
        painter.setPen(QPen(QColor("#1f77b4"), 2))
        painter.drawPolyline(points)
        painter.setPen(text)
        painter.drawText(4, top + 10, f"{highest:,.0f}")
        painter.drawText(4, top + height, "0")
        painter.drawText(4, top + height // 2, "pass/h")
        painter.drawText(left, self.height() - 8, format_time(first))
        painter.drawText(left + width - 55, self.height() - 8, format_time(last))


class DestinationsModel(QAbstractTableModel):
    """The probability of each destination, in columns, for each origin, in rows."""

    rejected = Signal(str)

    def __init__(self, document, parent=None):
        super().__init__(parent)
        self.document = document

    @property
    def names(self):
        return [station.name for station in self.document.scenario.stations]

    def refresh(self):
        self.beginResetModel()
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.names)

    columnCount = rowCount

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role in (Qt.DisplayRole, Qt.ToolTipRole):
            return self.names[section]
        return None

    def flags(self, index):
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable

    def value(self, index):
        names = self.names
        return self.document.scenario.demand.destinations.get(names[index.row()], {}).get(names[index.column()], 0.0)

    def data(self, index, role=Qt.DisplayRole):
        value = self.value(index)
        if role == Qt.DisplayRole:
            return f"{value:.4f}" if value else ""
        if role == Qt.EditRole:
            return value
        if role == Qt.ToolTipRole:
            return f"From {self.names[index.row()]} to {self.names[index.column()]}: {value:.6g}"
        if role == Qt.TextAlignmentRole:
            return int(Qt.AlignRight | Qt.AlignVCenter)
        return None

    def setData(self, index, value, role=Qt.EditRole):
        if role != Qt.EditRole:
            return False
        try:
            value = float(value)
        except (ValueError, TypeError):
            self.rejected.emit("Destinations: a number is expected")
            return False
        if value < 0:
            self.rejected.emit("Destinations: a probability must not be negative")
            return False
        if value == self.value(index):
            return True
        origin, destination = self.names[index.row()], self.names[index.column()]
        with self.document.edit():
            row = self.document.scenario.demand.destinations.setdefault(origin, {})
            if value == 0:
                row.pop(destination, None)
            else:
                row[destination] = value
        self.dataChanged.emit(index, index)
        return True


class DemandPage(Page):
    title = "Demand"

    def __init__(self, document):
        super().__init__(document)
        tabs = QTabWidget()

        # the profile over time
        def check_time(row, value):
            times = self.scenario.demand.times
            if row > 0 and value <= times[row - 1]:
                return "the time must be later than the one of the previous row"
            if row < len(times) - 1 and value >= times[row + 1]:
                return "the time must be earlier than the one of the next row"
            return None

        self.profile, self.profile_view = self.table(
            lambda: range(len(self.scenario.demand.times)),
            [
                Column(
                    "Time",
                    lambda row: self.scenario.demand.times[row],
                    lambda row, value: self.scenario.demand.times.__setitem__(row, value),
                    kind=int,
                    check=check_time,
                    show=format_time,
                    parse=parse_time,
                    tip="The time of the day, as HH:MM:SS",
                ),
                Column(
                    "Passengers per hour",
                    lambda row: self.scenario.demand.rates[row],
                    lambda row, value: self.scenario.demand.rates.__setitem__(row, value),
                    kind=float,
                    check=lambda row, value: None if value >= 0 else "the number of passengers must not be negative",
                    show=lambda value: f"{value:.1f}",
                    tip="The passengers entering the system per hour at that time, the values between two rows are interpolated",
                ),
            ],
        )
        add = QPushButton("Add row")
        add.clicked.connect(self.add_point)
        remove = QPushButton("Remove row")
        remove.clicked.connect(self.remove_point)
        scale = QPushButton("Scale...")
        scale.setToolTip("Multiplies the passengers of every row by a factor")
        scale.clicked.connect(self.ask_scale)
        self.total = QLabel()
        buttons = QHBoxLayout()
        for button in (add, remove, scale):
            buttons.addWidget(button)
        buttons.addStretch()
        buttons.addWidget(self.total)
        profile = QWidget()
        layout = QVBoxLayout(profile)
        layout.addWidget(ProfilePlot(document))
        layout.addWidget(self.profile_view, 1)
        layout.addLayout(buttons)
        tabs.addTab(profile, "Passengers over time")

        # where the passengers enter
        def share(name):
            total = sum(self.scenario.demand.entries.values())
            return 100 * self.scenario.demand.entries.get(name, 0.0) / total if total > 0 else 0.0

        self.entries, entries_view = self.table(
            lambda: [station.name for station in self.scenario.stations],
            [
                Column("Station", lambda name: name),
                Column(
                    "Weight",
                    lambda name: self.scenario.demand.entries.get(name, 0.0),
                    lambda name, value: self.scenario.demand.entries.__setitem__(name, value),
                    kind=float,
                    check=lambda name, value: None if value >= 0 else "the weight must not be negative",
                    tip="The passengers enter at each station in proportion to its weight",
                ),
                Column("Share (%)", share, kind=float, show=lambda value: f"{value:.2f}"),
            ],
        )
        self.entries.dataChanged.connect(lambda *_: self.entries.refresh())  # the shares of all the rows change
        tabs.addTab(entries_view, "Entry stations")

        # where they go
        self.destinations = DestinationsModel(document, self)
        self.destinations.rejected.connect(self.message)
        destinations_view = table_view(self.destinations, stretch_last=False)
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.addWidget(QLabel("The destinations of the passengers entering at each station (rows), in proportion to the values of the row."))
        layout.addWidget(destinations_view)
        tabs.addTab(box, "Destinations")

        layout = QVBoxLayout(self)
        layout.addWidget(heading("Demand", "How many passengers enter the system, where they enter and where they go."))
        layout.addWidget(tabs, 1)
        document.changed.connect(self.update_total)
        self.update_total()

    def refresh(self):
        self.profile.refresh()
        self.entries.refresh()
        self.destinations.refresh()
        self.update_total()

    def update_total(self):
        demand = self.scenario.demand
        # the passengers entering during the simulation: the area under the profile
        start, end = self.scenario.initial_time, self.scenario.final_time
        total = 0.0
        if len(demand.times) >= 2:
            import numpy as np

            grid = np.arange(start, end + 1, 10)
            total = float(np.trapezoid(np.interp(grid, demand.times, demand.rates), grid)) / 3600
        elif demand.rates:
            total = demand.rates[0] * (end - start) / 3600
        self.total.setText(f"About <b>{total:,.0f}</b> passengers during the simulation")

    def add_point(self):
        demand = self.scenario.demand
        row = self.profile_view.currentIndex().row()
        if not demand.times:
            time, rate, row = self.scenario.initial_time, 0.0, 0
        elif row < 0 or row == len(demand.times) - 1:
            time, rate, row = demand.times[-1] + 600, demand.rates[-1], len(demand.times)
        else:
            if demand.times[row + 1] - demand.times[row] < 2:
                self.message.emit("There is no room for a row between these two times")
                return
            time = (demand.times[row] + demand.times[row + 1]) // 2
            rate = (demand.rates[row] + demand.rates[row + 1]) / 2
            row += 1
        with self.document.edit():
            demand.times.insert(row, time)
            demand.rates.insert(row, rate)
        self.profile.refresh()
        self.profile_view.selectRow(row)

    def remove_point(self):
        demand = self.scenario.demand
        row = self.profile_view.currentIndex().row()
        if row < 0:
            self.message.emit("Select the row to remove")
            return
        with self.document.edit():
            del demand.times[row]
            del demand.rates[row]
        self.profile.refresh()

    def ask_scale(self):
        factor, accepted = QInputDialog.getDouble(self, "Scale the demand", "Multiply the passengers by:", 1.0, 0.0, 1000.0, 3)
        if accepted:
            self.scale(factor)

    def scale(self, factor):
        demand = self.scenario.demand
        with self.document.edit():
            demand.rates[:] = [factor * rate for rate in demand.rates]
        self.profile.refresh()


# ---------------------------------------------------------------------------------------------
class ParametersPage(Page):
    title = "Parameters"

    def __init__(self, document):
        super().__init__(document)
        self.fields = []  # (widget, function that reads the value from the scenario)

        self.name = QLineEdit()
        self.name.editingFinished.connect(lambda: self.store_text(self.name, lambda: self.scenario.name, lambda value: setattr(self.scenario, "name", value)))
        self.start = QLineEdit()
        self.start.setToolTip("The time of the day when the simulation starts, as HH:MM:SS")
        self.start.editingFinished.connect(lambda: self.store_time(self.start, "initial_time"))
        self.end = QLineEdit()
        self.end.setToolTip("The time of the day when the simulation ends, as HH:MM:SS")
        self.end.editingFinished.connect(lambda: self.store_time(self.end, "final_time"))

        general = QGroupBox("Simulation")
        form = QFormLayout(general)
        form.addRow("Name:", self.name)
        form.addRow("Starts at:", self.start)
        form.addRow("Ends at:", self.end)
        form.addRow("Default speed limit:", self.number(lambda: self.scenario, "default_speed_kmh", 1, 200, " km/h", "The speed limit where the network does not give one"))

        def params():
            return self.scenario.params

        buses = QGroupBox("Buses")
        form = QFormLayout(buses)
        form.addRow("Capacity:", self.number(params, "bus_capacity", 1, 1000, " passengers"))
        form.addRow("Length, articulated:", self.number(lambda: BusLengths(params()), "articulated", 1, 100, " m"))
        form.addRow("Length, biarticulated:", self.number(lambda: BusLengths(params()), "biarticulated", 1, 100, " m"))
        form.addRow("Random braking probability:", self.number(params, "braking_probability", 0, 1, "", "The probability that a moving bus slows down in a time step", decimals=3))
        form.addRow("Random braking probability, stopped:", self.number(params, "braking_probability_stopped", 0, 1, "", "The probability that a stopped bus does not start in a time step", decimals=3))
        form.addRow("No lane changes after a stop:", self.number(params, "lane_change_penalty", 0, 600, " s"))
        form.addRow("Random first bus within:", self.number(params, "max_offset", 1, 86400, " s", "The services without a fixed time for their first bus get a random one, shorter than this"))

        stops = QGroupBox("Stops and passengers")
        form = QFormLayout(stops)
        form.addRow("Minimal time at a stop:", self.number(params, "dwell_base", 0, 600, " s"))
        form.addRow("Time per passenger:", self.number(params, "dwell_per_passenger", 0, 60, " s", "The time added for each passenger boarding or alighting", decimals=2))
        form.addRow("Maximal time at a stop:", self.number(params, "dwell_max", 1, 3600, " s"))
        form.addRow("Boarding rate:", self.number(params, "boarding_rate", 1, 100, "", "How sharply the probability of boarding falls when the bus is full"))
        form.addRow("Passengers enter every:", self.number(params, "insertion_period", 1, 3600, " s"))

        content = QWidget()
        layout = QVBoxLayout(content)
        for box in (general, buses, stops):
            layout.addWidget(box)
        layout.addStretch()
        scroll = QScrollArea()
        scroll.setWidget(content)
        scroll.setWidgetResizable(True)
        layout = QVBoxLayout(self)
        layout.addWidget(heading("Parameters", "The simulation window and the parameters of the model."))
        layout.addWidget(scroll, 1)
        self.refresh()

    def number(self, owner, attribute, low, high, suffix="", tip="", decimals=None):
        """An editor for a numeric attribute of the object given by owner()."""
        widget = QSpinBox() if decimals is None else QDoubleSpinBox()
        if decimals is not None:
            widget.setDecimals(decimals)
            widget.setSingleStep(10**-decimals * 10)
        widget.setRange(low, high)
        widget.setMaximumWidth(160)
        widget.setSuffix(suffix)
        widget.setToolTip(tip)

        def store():
            if getattr(owner(), attribute) != widget.value():
                with self.document.edit():
                    setattr(owner(), attribute, widget.value())

        widget.editingFinished.connect(store)
        self.fields.append((widget, lambda: getattr(owner(), attribute)))
        return widget

    def store_text(self, widget, get, set):
        value = widget.text().strip()
        if value and value != get():
            with self.document.edit():
                set(value)
        widget.setText(get())

    def store_time(self, widget, attribute):
        try:
            value = parse_time(widget.text())
        except ValueError as error:
            self.message.emit(f"Not a time: {error}")
            value = getattr(self.scenario, attribute)
        start = value if attribute == "initial_time" else self.scenario.initial_time
        end = value if attribute == "final_time" else self.scenario.final_time
        if end <= start:
            self.message.emit("The simulation must end after it starts")
        elif value != getattr(self.scenario, attribute):
            with self.document.edit():
                setattr(self.scenario, attribute, value)
        widget.setText(format_time(getattr(self.scenario, attribute)))

    def refresh(self):
        self.name.setText(self.scenario.name)
        self.start.setText(format_time(self.scenario.initial_time))
        self.end.setText(format_time(self.scenario.final_time))
        for widget, value in self.fields:
            widget.blockSignals(True)
            widget.setValue(value())
            widget.blockSignals(False)


class BusLengths:
    """The two lengths of the buses, which the scenario stores as a list."""

    def __init__(self, params):
        self.params = params

    articulated = property(lambda self: self.params.bus_lengths[0], lambda self, value: self.params.bus_lengths.__setitem__(0, value))
    biarticulated = property(lambda self: self.params.bus_lengths[1], lambda self, value: self.params.bus_lengths.__setitem__(1, value))


# ---------------------------------------------------------------------------------------------
class NetworkPage(Page):
    title = "Network"

    def __init__(self, document):
        super().__init__(document)
        self.summary = QLabel()
        self.summary.setWordWrap(True)

        def cells(station):
            return ", ".join(f"{bay.x} (lane {bay.lane})" for bay in station.bays)

        def services(station):
            return ", ".join(sorted({name for bay in station.bays for name in bay.services}))

        self.stations, view = self.table(
            lambda: self.scenario.stations,
            [
                Column("Station", lambda station: station.name),
                Column("Bays", lambda station: len(station.bays), kind=int),
                Column("Services", services),
                Column("Cells of the bays", cells),
            ],
        )
        layout = QVBoxLayout(self)
        layout.addWidget(heading("Network", "The lanes, stations, traffic lights and paths of the services. The network cannot be edited here yet."))
        layout.addWidget(self.summary)
        layout.addWidget(view, 1)
        document.changed.connect(self.update_summary)
        self.update_summary()

    def update_summary(self):
        scenario = self.scenario
        self.summary.setText(
            f"<b>{scenario.length:,}</b> cells of one meter in <b>{scenario.lanes}</b> lanes &nbsp;·&nbsp; "
            f"<b>{len(scenario.stations)}</b> stations with <b>{sum(len(station.bays) for station in scenario.stations)}</b> bays &nbsp;·&nbsp; "
            f"<b>{len(scenario.services)}</b> services &nbsp;·&nbsp; <b>{len(scenario.traffic_lights)}</b> traffic lights &nbsp;·&nbsp; "
            f"<b>{len(scenario.jumps)}</b> jumps"
        )

    def refresh(self):
        self.stations.refresh()
        self.update_summary()
