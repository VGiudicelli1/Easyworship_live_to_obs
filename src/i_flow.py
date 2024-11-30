from __future__ import annotations
from flow import Flow


class i_Flow:
    __UID_objects: dict[int, i_Flow] = {}
    _flow: Flow

    @staticmethod
    def get_from_UID(UID: int) -> i_Flow:
        if not UID in i_Flow.__UID_objects:
            i_Flow(Flow.get_from_UID(UID))
        return i_Flow.__UID_objects[UID]

    def __init__(self, flow: Flow):
        self._flow = flow
        if flow.get_UID() in i_Flow.__UID_objects:
            raise ValueError
        i_Flow.__UID_objects[flow.get_UID()] = self

    def set_xy_begin(self, x: float, y: float):
        pass

    def draw_to(self, x: float, y: float):
        pass
