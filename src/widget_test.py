from widget import Widget, STATUS_RUN, STATUS_STOP


class Widget_Test(Widget):
    def __init__(self):
        super().__init__("Widget Test")

        self.add_param("param_1", "default_value_1", self._on_param_change)
        self.add_param("param_2", "default_value_2", self._on_param_change)
        self.add_option("option_1", True, self._on_option_change)
        self.add_option("option_2", False, self._on_option_change)

        self.update()

    def _on_param_change(self, key, value):
        print(key, value)
        self._display_all()

    def _on_option_change(self, key, value):
        print(key, value)
        self._display_all()

    def _display_all(self):
        print(
            f"""
State:
  - param_1: {self.read_param("param_1")}
  - param_2: {self.read_param("param_2")}
  - option_1: {self.read_option("option_1")}
  - option_2: {self.read_option("option_2")}
"""
        )

    def start(self):
        self.set_status(STATUS_RUN)

    def stop(self):
        self.set_status(STATUS_STOP)


class Widget_Test2(Widget):
    def __init__(self):
        super().__init__("Widget Test2")

        self.add_param("param_1", "default_value_1", self._on_param_change)
        self.add_option("option_1", True, self._on_option_change)
        self.add_option("option_2534", False, self._on_option_change)

        self.update()

    def _on_param_change(self, key, value):
        print(key, value)
        self._display_all()

    def _on_option_change(self, key, value):
        print(key, value)
        self._display_all()

    def _display_all(self):
        print(
            f"""
State:
  - param_1: {self.read_param("param_1")}
  - option_1: {self.read_option("option_1")}
  - option_2534: {self.read_option("option_2534")}
"""
        )

    def start(self):
        self.set_status(STATUS_RUN)

    def stop(self):
        self.set_status(STATUS_STOP)


if __name__ == "__main__":
    from app import run_as_main_file

    run_as_main_file()
