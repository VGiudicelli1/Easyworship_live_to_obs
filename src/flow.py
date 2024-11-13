from collections.abc import Callable


class Flow:
    _value: str
    _callback: dict[int, Callable[[str], None]]

    def __init__(self, value: str = ""):
        self._value = value
        self._callback = {}

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
