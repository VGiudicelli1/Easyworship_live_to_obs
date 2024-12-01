from tkinter import Canvas
from input import Input
from output import Output
from transform import Transform
from widget import Widget, STATUS_BUSY, STATUS_RUN, STATUS_STOP, STATUS_ERROR
from i_flow import i_Flow


class i_Widget:
    _widget: Widget
    _canvas: Canvas
    _tkid_tem_onoff: int
    _tkids_input: list[tuple[int, int]]
    _tkids_output: list[tuple[int, int]]
    _tkid_rect: int
    _tkid_text: int
    _x: float
    _y: float
    _w: float
    _h: float
    _scan_mark: tuple[float, float]
    _tag_UID: str

    def __init__(self, widget: Widget, canvas: Canvas):
        self._widget = widget
        self._canvas = canvas
        self._tag_UID = "widget_uid_" + str(widget._UID)

        self._x = 20
        self._y = 30
        self._w = 100
        self._h = 120

        self._draw()
        self._widget.link_callback(self.update)

    def is_in(self, x: float, y: float) -> bool:
        return self._x <= x <= self._x + self._w and self._y <= y <= self._y + self._h

    def scan_mark(self, x: float, y: float):
        self._scan_mark = (x, y)

    def scan_dragto(self, x: float, y: float, gain: float = 10.0):
        dx = (x - self._scan_mark[0]) * gain
        dy = (y - self._scan_mark[1]) * gain
        self._x += dx
        self._y += dy
        self._scan_mark = (x, y)
        self._canvas.move(self._tag_UID, dx, dy)
        self._update_flows()

    def _draw(self):
        self._tkid_rect = self._canvas.create_rectangle(
            0, 0, 0, 0, width=1, tags=["widget", self._tag_UID]
        )
        self._tkid_text = self._canvas.create_text(
            0, 0, anchor="center", tags=["widget", self._tag_UID], fill="black"
        )
        self._tkid_tem_onoff = self._canvas.create_oval(
            0, 0, 0, 0, width=0, tags=["widget", self._tag_UID]
        )

        self._tkids_input = []
        self._tkids_output = []

        self.update()

    def update(self):
        # content
        self._canvas.itemconfig(
            self._tkid_text,
            text=self._widget._name,
        )

        color = {
            STATUS_BUSY: "orange",
            STATUS_RUN: "green",
            STATUS_STOP: "gray",
            STATUS_ERROR: "red",
        }
        self._canvas.itemconfig(
            self._tkid_tem_onoff,
            fill=(
                color[self._widget._status]
                if self._widget._status in color
                else "white"
            ),
        )

        if isinstance(self._widget, Input):
            self._canvas.itemconfig(self._tkid_rect, fill="#DAE8FC", outline="#6C8EBF")
        elif isinstance(self._widget, Transform):
            self._canvas.itemconfig(self._tkid_rect, fill="#FFF2CC", outline="#D6B656")
        elif isinstance(self._widget, Output):
            self._canvas.itemconfig(self._tkid_rect, fill="#D5E8D4", outline="#82B366")
        else:
            self._canvas.itemconfig(self._tkid_rect, fill="white", outline="black")

        self._canvas.itemconfig(
            self._tkid_rect, width=2 if self._widget._selected else 1
        )

        # coords
        self._canvas.coords(
            self._tkid_rect,
            self._x,
            self._y,
            self._x + self._w,
            self._y + self._h,
        )

        self._canvas.coords(
            self._tkid_tem_onoff,
            self._x + self._w - 20,
            self._y + 10,
            self._x + self._w - 10,
            self._y + 20,
        )
        self._canvas.coords(
            self._tkid_text,
            self._x + self._w / 2,
            self._y + 15,
        )

        for liste, tkids, left in [
            (self._widget._inputs.keys(), self._tkids_input, True),
            (self._widget._outputs.keys(), self._tkids_output, False),
        ]:
            liste: list[str]
            tkids: list[tuple[int, int]]
            left: bool
            n = len(liste)
            for i, name in enumerate(liste):
                if i >= len(tkids):
                    tkids.append(
                        [
                            self._canvas.create_polygon(
                                0,
                                0,
                                0,
                                0,
                                0,
                                0,
                                fill="#FFFFFF",
                                outline="#000000",
                                tags=["widget", self._tag_UID],
                            ),
                            self._canvas.create_text(
                                0,
                                0,
                                anchor="w" if left else "e",
                                tags=["widget", self._tag_UID],
                                fill="black",
                            ),
                        ]
                    )

                x = self._x if left else self._x + self._w
                y = self._y + self._h * 0.2 + self._h * 0.8 / n * (i + 0.5)
                self._canvas.coords(
                    tkids[i][0], x - 10, y - 10, x - 10, y + 10, x + 10, y
                )
                self._canvas.coords(tkids[i][1], (x + 10) if left else (x - 10), y)
                self._canvas.itemconfig(tkids[i][1], text=name)
            while len(tkids) > len(liste):
                for id in tkids.pop():
                    self._canvas.delete(id)

        self._update_flows()

    def _update_flows(self):
        # tkid_outputs + flows
        # i_flow.set_xy_begin
        for tkid, flow in zip(
            self._tkids_output,
            self._widget._outputs.values(),
        ):
            i_flow = i_Flow.get_from_UID(flow.get_UID(), self._canvas)
            c = self._canvas.coords(tkid[0])
            i_flow.set_xy_begin([c[4], c[5]])

        # tkid_inputs + flows
        # group by flow
        # tkids_inputs + i_flows
        # l_coords + i_flows
        # i_flow.set_lxy_end
        # TODO
        id_flow__l_xy: dict[int, list[tuple[float, float]]] = {}
        for (tkid, _), (flow, _) in zip(
            self._tkids_input,
            self._widget._inputs.values(),
        ):
            id = flow.get_UID()
            if not id in id_flow__l_xy:
                id_flow__l_xy[id] = []
            c = self._canvas.coords(tkid)
            id_flow__l_xy[id].append(
                (
                    (c[0] + c[2]) / 2,
                    (c[1] + c[3]) / 2,
                )
            )
        for id_flow, l_xy in id_flow__l_xy.items():
            i_flow = i_Flow.get_from_UID(id_flow, self._canvas)
            i_flow.set_lxy_end(self._widget.get_UID(), l_xy)

        # cas input retire/changé: preview inputs without currents inputs ==> update
        # TODO


if __name__ == "__main__":
    from app import run_as_main_file

    run_as_main_file()
