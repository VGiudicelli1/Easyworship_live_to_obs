from input import Input

# path: input | param

# output: file content

# status: stop | busy | run


from watchdog.events import FileSystemEventHandler
from flow import Flow
import os
from watchdog.observers import Observer
from watchdog.observers.api import BaseObserver

# import abc

from widget import STATUS_BUSY, STATUS_RUN, STATUS_STOP


class MyHandler(FileSystemEventHandler):
    path: str = ""
    flow: Flow

    def __init__(self, path, flow: Flow):
        super().__init__()
        self.path = path
        self.flow = flow

    def read_file_content(self) -> str:
        try:
            with open(self.path, "r") as file:
                return "".join(file.readlines())
        except:
            return ""

    def start(self):
        self.flow.set(self.read_file_content())

    def stop(self):
        self.flow.set("")

    def on_modified(self, event):
        if event.src_path == self.path:
            self.flow.set(self.read_file_content())

    def on_moved(self, event):
        if self.path in [event.src_path, event.dest_path]:
            self.flow.set(self.read_file_content())

    def on_created(self, event):
        if event.src_path == self.path:
            self.flow.set(self.read_file_content())

    def on_deleted(self, event):
        if event.src_path == self.path:
            self.flow.set("")


class Input_File(Input):
    path: str
    event_handler: MyHandler
    observer: BaseObserver

    def __init__(self, name: str):
        super().__init__(name)

        self.path = os.path.abspath("")
        self._outputs["data"] = Flow()

        self.add_param("path", self.path, lambda key, val: self.set_path(val))

        self.event_handler = MyHandler(self.path, self._outputs["data"])

        self.update()

    def set_path(self, path: str):
        abspath = os.path.abspath(path)
        if self.path == abspath:
            return
        self.path = abspath
        self.event_handler.path = abspath
        if self.is_started():
            self.stop()
            self.start()

    def start(self):
        self.observer = Observer()
        self.observer.schedule(
            self.event_handler,
            path=os.path.dirname(self.path),
            recursive=True,
        )
        self.observer.start()

        self.event_handler.start()

        self.set_status(STATUS_RUN)

    def stop(self):
        self.observer.stop()
        self.event_handler.stop()
        self.set_status(STATUS_STOP)


if __name__ == "__main__":
    from app import run_as_main_file

    run_as_main_file()
