from widget import Widget, STATUS_RUN, STATUS_STOP


class Widget_Test(Widget):
    def __init__(self):
        super().__init__("Widget Test")

        self.add_param("param_1", "default_value_1", self.on_param_change)
        self.add_param("param_2", "default_value_2", self.on_param_change)
        self.add_option("option_1", True, self.on_option_change)
        self.add_option("option_2", False, self.on_option_change)

        self.update()

    def on_param_change(self, key, value):
        print(key, value)
        self.display_all()

    def on_option_change(self, key, value):
        print(key, value)
        self.display_all()

    def display_all(self):
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

        self.add_param("param_1", "default_value_1", self.on_param_change)
        self.add_option("option_1", True, self.on_option_change)
        self.add_option("option_2534", False, self.on_option_change)

        self.update()

    def on_param_change(self, key, value):
        print(key, value)
        self.display_all()

    def on_option_change(self, key, value):
        print(key, value)
        self.display_all()

    def display_all(self):
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
