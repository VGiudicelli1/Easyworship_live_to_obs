from __future__ import annotations
from flow import Flow

from tkinter import Canvas


class i_Flow:
    __UID_objects: dict[int, i_Flow] = {}
    _flow: Flow
    _xy_begin: tuple[float, float]
    _tkid_segments: dict[int, list[int]]
    _canvas: Canvas

    @staticmethod
    def get_from_UID(UID: int, canvas: Canvas) -> i_Flow:
        if not UID in i_Flow.__UID_objects:
            i_Flow(Flow.get_from_UID(UID), canvas)
        return i_Flow.__UID_objects[UID]

    def __init__(self, flow: Flow, canvas: Canvas):
        self._flow = flow
        self._canvas = canvas
        if flow.get_UID() in i_Flow.__UID_objects:
            raise ValueError
        i_Flow.__UID_objects[flow.get_UID()] = self

        self._xy_begin = (None, None)
        self._tkid_segments = {}

    def set_xy_begin(self, xy: tuple[float, float]):
        self._xy_begin = xy
        for tkid_segments in self._tkid_segments.values():
            for tkid_segment in tkid_segments:
                c = self._canvas.coords(tkid_segment)
                self._canvas.coords(
                    tkid_segment, self._xy_begin[0], self._xy_begin[1], c[2], c[3]
                )

    def set_lxy_end(self, id_widget: int, l_xy: list[tuple[float, float]]):
        # todo
        for tkid_segment in l_xy:
            c = self._canvas.coords(tkid_segment)
            self._canvas.coords(
                tkid_segment, self._xy_begin[0], self._xy_begin[1], c[2], c[3]
            )
