from input import Input
from watchdog.events import FileSystemEventHandler
from flow import Flow
import os
from watchdog.observers import Observer
from watchdog.observers.api import BaseObserver
from widget import STATUS_RUN, STATUS_STOP


class MyHandler(FileSystemEventHandler):
    _path: str = ""
    _flow: Flow

    def __init__(self, path: str, flow: Flow):
        super().__init__()
        self._path = path
        self._flow = flow

    def set_path(self, path: str):
        self._path = path

    def read_file_content(self) -> str:
        try:
            with open(self._path, "r") as file:
                return "".join(file.readlines())
        except:
            return ""

    def start(self):
        self._flow.set(self.read_file_content())

    def stop(self):
        self._flow.set("")

    def on_modified(self, event):
        if event.src_path == self._path:
            self._flow.set(self.read_file_content())

    def on_moved(self, event):
        if self._path in [event.src_path, event.dest_path]:
            self._flow.set(self.read_file_content())

    def on_created(self, event):
        if event.src_path == self._path:
            self._flow.set(self.read_file_content())

    def on_deleted(self, event):
        if event.src_path == self._path:
            self._flow.set("")


class Input_File(Input):
    _path: str
    _event_handler: MyHandler
    _observer: BaseObserver

    def __init__(self, name: str = "Input_File"):
        super().__init__(name)

        self._path = os.path.abspath("")
        self.add_param(
            "path",
            "path",
            self._path,
            lambda key, val: self.set_path(val),
        )
        self.new_output("data")

        self._event_handler = MyHandler(
            self._path,
            self.get_output("data"),
        )

        self.update()

    def set_path(self, path: str):
        abspath = os.path.abspath(path)
        if self._path == abspath:
            return
        self._path = abspath
        self._event_handler.set_path(abspath)
        if self.is_started():
            self.stop()
            self.start()

    def start(self):
        self._observer = Observer()
        self._observer.schedule(
            self._event_handler,
            path=os.path.dirname(self._path),
            recursive=True,
        )
        self._observer.start()

        self._event_handler.start()

        self.set_status(STATUS_RUN)

    def stop(self):
        self._observer.stop()
        self._event_handler.stop()
        self.set_status(STATUS_STOP)


if __name__ == "__main__":
    from app import run_as_main_file

    run_as_main_file()
