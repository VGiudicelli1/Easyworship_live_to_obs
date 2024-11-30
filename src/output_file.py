from output import Output
from widget import STATUS_RUN, STATUS_STOP
import os


class Output_File(Output):
    """
    Options:
        empty_on_stop: clear file if status is stop (default: True)
        delete_on_stop: delete file if status is stop (default: False)
        rename_on_pathChange: rename file on path change (True) or create an new file (default True)
    """

    _path: str

    def __init__(self, name: str = "Output_File"):
        super().__init__(name)
        self.new_input("data", self._execute)

        self._path = ""

        self.add_option("empty_on_stop", True, lambda key, val: ())
        self.add_option("delete_on_stop", False, lambda key, val: ())
        self.add_option("rename_on_pathChange", True, lambda key, val: ())
        self.add_param("path", "path", "", lambda key, val: self._set_path(val))

    def _write(self, value: str):
        try:
            with open(self._path, "w") as file:
                file.write(value)
        except:
            pass

    def _set_path(self, new_path: str):
        if self.read_option("rename_on_pathChange"):
            try:
                os.rename(self._path, new_path)
            except:
                pass
        else:
            try:
                with open(new_path, "w") as f_w:
                    with open(self._path, "r") as f_r:
                        f_w.write(f_r.read())
            except:
                pass
        self._path = new_path

    def _execute(self, _val=None):
        if not self.is_started():
            return
        self._write(self._inputs["data"][0].get())

    def start(self):
        self.set_status(STATUS_RUN)

        self._execute()

    def stop(self):
        if self.read_option("empty_on_stop"):
            self._write("")
        if self.read_option("delete_on_stop"):
            try:
                os.remove(self._path)
            except:
                pass

        self.set_status(STATUS_STOP)


if __name__ == "__main__":
    from app import run_as_main_file

    run_as_main_file()
