from __future__ import annotations
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from widget import Widget


class Flow:
    __UID_MAX: int = 0
    __UID_Objects: dict[int, Flow] = {}
    _UID: int

    _value: str
    _callback: dict[int, Callable[[str], None]]
    _master: Widget

    @staticmethod
    def get_from_UID(UID: int) -> Flow:
        return Flow.__UID_Objects[UID]

    def get_UID(self) -> int:
        return self._UID

    def __init__(self, master: Widget, value: str = ""):
        Flow.__UID_MAX += 1
        self._UID = Flow.__UID_MAX
        Flow.__UID_Objects[self._UID] = self

        self._value = value
        self._master = master
        self._callback = {}

    def get_master(self) -> Widget:
        return self._master

    def set(self, value: str):
        if self._value == value:
            return
        self._value = value
        for cb in self._callback.values():
            cb(value)

    def get(self) -> str:
        return self._value

    def link(self, cb: Callable[[str], None]) -> int:
        id = hash(cb)
        while id in self._callback:
            id += 1
        self._callback[id] = cb
        return id

    def unlink(self, id: int) -> Callable[[str], None]:
        cb = self._callback[id]
        del self._callback[id]
        return cb


if __name__ == "__main__":
    from app import run_as_main_file

    run_as_main_file()
