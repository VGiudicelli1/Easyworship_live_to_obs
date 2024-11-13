from flow import Flow
import abc
from typing import Callable

# constants
STATUS_STOP = 0
STATUS_BUSY = 1
STATUS_RUN = 2
STATUS_ERROR = 3


# class
class Widget(metaclass=abc.ABCMeta):
    __UID_MAX: int = 0
    _UID: int
    _on: bool
    _name: str
    _cb_change: dict[int, Callable[[], None]]
    _inputs: dict[str, tuple[Flow, int]]
    _outputs: dict[str, Flow]
    _status: int
    _options: dict[
        str,
        tuple[
            bool,
            Callable[[str, bool], None],
        ],
    ]
    _params: dict[
        str,
        tuple[
            str,
            Callable[[str, str], None],
        ],
    ]
    NULL: "NullWidget"

    def __init__(self, name: str):
        Widget.__UID_MAX += 1
        self._UID = Widget.__UID_MAX

        self._name = name
        self._on = False
        self._cb_change = {}
        self._outputs = {}
        self._inputs = {}
        self._options = {}
        self._params = {}

        self._status = STATUS_STOP

    def add_option(
        self,
        key: str,
        default: bool,
        callback: Callable[[str, bool], None],
    ):
        if key in self._options:
            raise ValueError
        self._options[key] = (default, callback)

    def set_option(self, key: str, value: bool):
        if not key in self._options:
            raise ValueError
        current, callback = self._options[key]
        if current == value:
            return
        self._options[key] = (value, callback)
        callback(key, value)

    def read_option(self, key: str) -> bool:
        return self._options[key][0]

    def add_param(
        self,
        key: str,
        default: str,
        callback: Callable[[str, str], None],
    ):
        if key in self._params:
            raise ValueError
        self._params[key] = (default + "", callback)

    def set_param(self, key: str, value: str):
        if not key in self._params:
            raise ValueError
        current, callback = self._params[key]
        if current == value:
            return
        self._params[key] = (value, callback)
        callback(key, value)

    def read_param(self, key: str) -> str:
        return self._params[key][0]

    def new_input(
        self,
        key: str,
        callback: Callable[[str], None],
        flow: Flow = None,
    ):
        if flow is None:
            flow = Flow()
        self._inputs[key] = [flow, flow.link(callback)]

    def link_input(self, key: str, flow: Flow):
        if not key in self._inputs:
            raise KeyError
        self._inputs[key] = [
            flow,
            flow.link(self._inputs[key][0].unlink(self._inputs[key][1])),
        ]

    def new_output(self, key: str, flow: Flow | None = None):
        self._outputs[key] = flow if flow is not None else Flow()

    def get_output(self, key: str) -> Flow:
        return self._outputs[key]

    def read_input(self, key: str) -> str:
        return self._inputs[key][0].get()

    def set_status(self, status: int):
        if self._status == status:
            return
        self._status = status
        self.update()

    def get_status(self) -> int:
        return self._status

    def set_name(self, name: str):
        if self._name == name:
            return
        self._name = name
        self.update()

    def get_name(self) -> str:
        return self._name

    def set_on(self, on: bool):
        if self._on == on:
            return
        self._on = on
        self.set_status(STATUS_BUSY)
        if on:
            self.start()
        else:
            self.stop()
        self.update()

    def get_on(self) -> bool:
        return self._on

    @abc.abstractmethod
    def start(self):
        raise NotImplemented

    @abc.abstractmethod
    def stop(self):
        raise NotImplemented

    def link_callback(self, cb: Callable[[], None]) -> int:
        id = hash(cb)
        while id in self._cb_change:
            id += 1
        self._cb_change[id] = cb
        return id

    def unlink_callback(self, id: int) -> Callable[[], None]:
        cb = self._cb_change[id]
        del self._cb_change[id]
        return cb

    def update(self):
        for cb in list(self._cb_change.values()):
            cb()

    def is_started(self) -> bool:
        return self._status != STATUS_STOP


class NullWidget(Widget):
    def __init__(self):
        super().__init__("NullWidget")

    def set_name(self, name):
        pass

    def set_on(self, on):
        pass

    def set_option(self, key, value):
        pass

    def set_param(self, key, value):
        pass

    def set_status(self, status):
        pass

    def link_callback(self, cb) -> int:
        return 0

    def unlink_callback(self, id):
        pass

    def new_input(self, key, callback, flow=None):
        pass

    def new_output(self, key, flow=None):
        pass

    def add_option(self, key, default, callback):
        pass

    def add_param(self, key, default, callback):
        pass

    def link_input(self, key, flow):
        pass

    def start(self):
        self.set_status(STATUS_RUN)

    def stop(self):
        self.set_status(STATUS_STOP)


Widget.NULL = NullWidget()

if __name__ == "__main__":
    from app import run_as_main_file

    run_as_main_file()
