import tkinter as tk
from constants import *
from interfaceSelectedWidget import InterfaceSelectedWidget
from input_file import Input_File
from output_file import Output_File
from output_web import Output_Web
from widget import STATUS_STOP, Widget
from i_widget import i_Widget
from widget_test import Widget_Test, Widget_Test2

# from transform import Transform


class App:
    _fen: tk.Tk
    _can_process: tk.Canvas
    _frame_selected: InterfaceSelectedWidget
    _frame_main: tk.Frame

    _widgets: list[Widget]
    _i_widgets: list[i_Widget]

    _dragging_object: tk.Canvas | i_Widget

    _quiting: bool
    _tkid_version: int

    def __init__(self, master: tk.Widget | None = None):
        self._widgets = []
        self._i_widgets = []
        self._quiting = False

        self._fen = tk.Tk(master)
        self._fen.title(APP_NAME)
        self._fen.geometry("900x500")

        self._can_process = tk.Canvas(
            self._fen,
            background="#DDDDDD",
            highlightthickness=0,
        )
        self._can_process.place(relx=0, rely=0, relheight=1, relwidth=0.8)
        self._tkid_version = self._can_process.create_text(
            0, 0, text=f"github: {GITHUB}\tversion: {VERSION}", anchor="se"
        )
        self._fen.after(1, self._update_coords_version)
        self._fen.bind("<Configure>", self._update_coords_version)

        self._frame_selected = InterfaceSelectedWidget(self._fen)
        self._frame_selected.place(relx=0.8, rely=0, relheight=0.9, relwidth=0.2)
        self._frame_selected.set_selectedWidget(Widget.NULL)

        self._frame_main = tk.Frame(self._fen)
        self._frame_main.place(relx=0.8, rely=0.9, relheight=0.1, relwidth=0.2)

        btn_recall = tk.Button(self._frame_main, text="recall")
        btn_recall.place(relx=0 / 3, rely=0, relwidth=1 / 3, relheight=1)

        btn_save = tk.Button(self._frame_main, text="save")
        btn_save.place(relx=1 / 3, rely=0, relwidth=1 / 3, relheight=1)

        btn_quit = tk.Button(self._frame_main, text="quit", command=self.quit)
        btn_quit.place(relx=2 / 3, rely=0, relwidth=1 / 3, relheight=1)

        self._can_process.bind("<ButtonPress-1>", self.on_click)
        self._can_process.bind("<B1-Motion>", self.on_motion)

        # add items for tests
        inp = Input_File("test.txt")
        inp.set_param("path", "./src/test.txt")
        i_inp = i_Widget(inp, self._can_process)
        inp.set_on(True)
        self._widgets.append(inp)
        self._i_widgets.append(i_inp)

        out = Output_File("test2.txt")
        out.set_param("path", "./src/test_out.txt")
        out.link_input("data", inp.get_output("data"))
        i_out = i_Widget(out, self._can_process)
        i_out._x += 150
        out.set_on(True)
        self._widgets.append(out)
        self._i_widgets.append(i_out)

        out2 = Output_Web("WEB")
        out2.link_input("data", inp.get_output("data"))
        i_out2 = i_Widget(out2, self._can_process)
        i_out2._x += 150
        i_out2._y += 200
        i_out2.update()
        out2.set_on(True)
        self._widgets.append(out2)
        self._i_widgets.append(i_out2)

        test = Widget_Test()
        i_test = i_Widget(test, self._can_process)
        i_test._x += 300
        i_test.update()
        self._widgets.append(test)
        self._i_widgets.append(i_test)

        test2 = Widget_Test2()
        i_test2 = i_Widget(test2, self._can_process)
        i_test2._x += 300
        i_test2._y += 200
        i_test2.update()
        self._widgets.append(test2)
        self._i_widgets.append(i_test2)

    def on_click(self, event: tk.Event):
        if self._quiting:
            return
        self._dragging_object = self._can_process
        selectedWidget = Widget.NULL
        for i_w in self._i_widgets[::-1]:
            if i_w.is_in(
                self._can_process.canvasx(event.x),
                self._can_process.canvasy(event.y),
            ):
                self._dragging_object = i_w
                selectedWidget = i_w._widget
                break
        self._frame_selected.set_selectedWidget(selectedWidget)
        self._dragging_object.scan_mark(event.x, event.y)

    def on_motion(self, event: tk.Event):
        if self._quiting:
            return
        self._dragging_object.scan_dragto(event.x, event.y, 1)
        self._update_coords_version()

    def _update_coords_version(self, *args, **kwargs):
        self._can_process.coords(
            self._tkid_version,
            self._can_process.canvasx(self._can_process.winfo_width()),
            self._can_process.canvasy(self._can_process.winfo_height()),
        )

    def quit(self):
        if self._quiting:
            return
        self._quiting = True

        def disabled_childs(widget: tk.Widget):
            try:
                widget.configure(state=tk.DISABLED)
            except tk._tkinter.TclError:
                pass
            for child in widget.children.values():
                disabled_childs(child)

        def quit():
            one_alive = False
            for w in self._widgets:
                one_alive |= w._status != STATUS_STOP
                w.set_on(False)

            if one_alive:
                self._fen.after(100, quit)
            else:
                self._fen.quit()
                pass

        disabled_childs(self._fen)
        quit()

    def run(self):
        try:
            self._fen.mainloop()
        except tk._tkinter.TclError:
            pass
        try:
            self._fen.destroy()
        except tk._tkinter.TclError:
            pass


def run_as_main_file():
    print("--- begin ---")
    app = App()
    app.run()
    print("---  end  ---")


if __name__ == "__main__":
    run_as_main_file()
