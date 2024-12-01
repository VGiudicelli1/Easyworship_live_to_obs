from widget import Widget
import tkinter as tk
from flow import Flow
from tkinter import filedialog as fd


class Option(tk.Frame):
    _value: tk.BooleanVar
    _chkbutton: tk.Checkbutton
    _lbl_name: tk.Label

    def __init__(self, master: tk.Widget):
        super().__init__(master)

        self._value = tk.BooleanVar(self)
        self._chkbutton = tk.Checkbutton(self, variable=self._value)
        self._chkbutton.place(relx=0.1, rely=0.5, anchor="center")

        self._lbl_name = tk.Label(self)
        self._lbl_name.place(relx=0.2, rely=0, relheight=1, relwidth=0.8)
        self._lbl_name.bind(
            "<Button>",
            lambda event: self._value.set(not self._value.get()),
        )

    def set_name(self, name: str):
        self._lbl_name.config(text=name)

    def set_value(self, value: bool):
        self._value.set(value)

    def get_value(self) -> bool:
        return self._value.get()


class Param(tk.Frame):
    _value: tk.StringVar
    _input: tk.Entry
    _lbl_name: tk.Label
    _type: str

    def __init__(self, master: tk.Widget):
        super().__init__(master)

        self._value = tk.StringVar(self)
        self._input = tk.Entry(self, textvariable=self._value)
        self._input.place(relx=0.4, rely=0, relheight=1, relwidth=0.6)

        self._lbl_name = tk.Label(self)
        self._lbl_name.place(relx=0, rely=0, relheight=1, relwidth=0.4)

        self._type = "str"

    def set_name(self, name: str):
        self._lbl_name.config(text=name)

    def set_type(self, type_: str):
        self._type = type_
        if type_ == "path":

            def select_file(e: None):
                filetypes = (
                    ("text files", "*.txt"),
                    ("All files", "*.*"),
                )

                path = fd.askopenfilename(
                    title="Open a file",
                    initialdir=self._value.get(),
                    filetypes=filetypes,
                )
                if path:
                    self._value.set(path)

            self._input.bind("<Button-1>", select_file)
        else:
            self._input.bind("<Button-1>", lambda e: ())

    def set_value(self, value: str):
        self._value.set(value)

    def get_value(self) -> str:
        return self._value.get()


class FlowOut(tk.Frame):
    _flow: Flow
    _linked_id: int | None
    _lbl_flow: tk.Label

    def __init__(self, master: tk.Widget, name: str, flow: Flow):
        super().__init__(master)

        self._flow = flow
        self._linked_id = None

        lbl_name = tk.Label(self, text=name)
        lbl_name.place(relx=0, rely=0, relheight=1, relwidth=0.3)

        self._lbl_flow = tk.Label(self)
        self._lbl_flow.place(relx=0.3, rely=0, relheight=1, relwidth=0.7)
        self._lbl_flow.bind(
            "<Button>",
            lambda event: (self.clipboard_clear(), self.clipboard_append(flow.get())),
        )
        self._lbl_flow.config(cursor="circle")

    def update_flow(self, value):
        self._lbl_flow.config(text=value)

    def place(self, **kwargs):
        if self._linked_id is None:
            self._linked_id = self._flow.link(self.update_flow)
        return super().place(**kwargs)

    def place_forget(self):
        if self._linked_id is not None:
            self._flow.unlink(self._linked_id)
            self._linked_id = None
        return super().place_forget()


dY = 30


class InterfaceSelectedWidget:
    _frame: tk.Frame
    _frame_content: tk.Frame
    _widget: Widget
    _widget_callback_id: int

    _label_type: tk.Label
    _label_name: tk.Label
    _button_start: tk.Button
    _button_save: tk.Button

    _options: dict[str, Option]
    _param: dict[str, Param]
    _flows: dict[str, FlowOut]
    _place_info: dict[str, any]

    _name: tk.StringVar

    def __init__(self, master: tk.Widget):
        self._frame = tk.Frame(master)
        self._widget = Widget.NULL
        self._widget_callback_id = -1

        frame_head = tk.Frame(self._frame)
        frame_head.place(relx=0, rely=0, relwidth=1, relheight=0.12)

        self._frame_content = tk.Frame(self._frame)
        self._frame_content.place(relx=0, rely=0.12, relwidth=1, relheight=0.88)

        self._name = tk.StringVar(self._frame)
        self._name.trace_add(
            "write", lambda a, b, c: self._widget.set_name(self._name.get())
        )

        self._label_type = tk.Label(frame_head)
        self._label_type.place(relx=0, rely=0, relwidth=1, relheight=0.5)
        self._label_name = tk.Entry(frame_head, textvariable=self._name)
        self._label_name.place(relx=0, rely=0.5, relheight=0.5, relwidth=0.6)
        self._button_start = tk.Button(frame_head, text="start", command=self.start)
        self._button_start.place(relx=0.6, rely=0.5, relwidth=0.4, relheight=0.5)

        self._button_save = tk.Button(
            self._frame_content, text="Save", command=self._save_options_params
        )
        self._button_save.place(relx=0, rely=0, height=dY, relwidth=1)

        self._options = {}
        self._param = {}
        self._flows = {}
        self._place_info = {}

    def start(self):
        self._widget.set_on(not self._widget.get_on())

    def place(self, **kwargs):
        self._frame.place(**{**self._place_info, **kwargs})
        self._place_info = self._frame.place_info()

    def _save_options_params(self):
        for key in self._widget._options:
            self._widget.set_option(key, self._options[key].get_value())
        for key in self._widget._params:
            self._widget.set_param(key, self._param[key].get_value())

    def set_selectedWidget(self, widget: Widget):
        def make_full_key(key: str) -> str:
            return f"{widget._UID}-{key}"

        try:
            self._widget.unlink_callback(self._widget_callback_id)
        except:
            pass
        self._widget.set_selected(False)
        self._widget = widget
        self._widget.set_selected(True)

        if self._widget is Widget.NULL:
            self._frame.place_forget()
        else:
            self.place()

        self._name.set(widget.get_name())
        self._button_start.config(text="stop" if widget.get_on() else "start")
        self._label_type.config(text=str(widget.__class__.__name__))

        y = 0

        for key, option in self._options.items():
            if not key in widget._options:
                option.place_forget()
        for key, param in self._param.items():
            if not key in widget._params:
                param.place_forget()
        for key, flow in self._flows.items():
            if not make_full_key(key) in widget._outputs:
                flow.place_forget()

        self._frame.update()
        self._frame_content.update()

        for key in widget._options:
            if not key in self._options:
                self._options[key] = Option(self._frame_content)

            self._options[key].set_name(key)
            self._options[key].set_value(widget.read_option(key))
            self._options[key].place(relx=0, y=y, relwidth=1, height=dY)
            y += dY

        for key in widget._params:
            if not key in self._param:
                self._param[key] = Param(self._frame_content)

            self._param[key].set_name(key)
            self._param[key].set_type(widget.get_param_type(key))
            self._param[key].set_value(widget.read_param(key))
            self._param[key].place(relx=0, y=y, relwidth=1, height=dY)
            y += dY

        self._button_save.place(relx=0, y=y, relwidth=1, height=dY)
        y += dY

        for key, flow in widget._outputs.items():
            full_key = make_full_key(key)
            if not full_key in self._flows:
                self._flows[full_key] = FlowOut(self._frame_content, key, flow)

            self._flows[full_key].update_flow(flow.get())
            self._flows[full_key].place(relx=0, y=y, relwidth=1, height=dY)
            y += dY

        self._widget_callback_id = self._widget.link_callback(
            lambda: self.set_selectedWidget(self._widget)
        )

        self._frame.update()
        self._frame_content.update()


if __name__ == "__main__":
    from app import run_as_main_file

    run_as_main_file()
