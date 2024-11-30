from output import Output
from widget import STATUS_RUN, STATUS_STOP
import socketio
import eventlet.wsgi
from concurrent.futures.thread import ThreadPoolExecutor
import socket


class Output_Web(Output):
    _path: str
    _sio: socketio.Server
    _app: socketio.WSGIApp
    _message: None | str
    _server_running: bool

    def __init__(self, name: str = "Output_Web"):
        super().__init__(name)
        self.new_input("data", self._execute)
        self.add_param("port", "8000", lambda key, val: ())

        self._sio = socketio.Server(
            cors_allowed_origins="*",
            async_mode="eventlet",
        )
        self._app = socketio.WSGIApp(
            self._sio,
            static_files={
                "/": "public/",
            },
        )

        self.new_output("uri")

        @self._sio.event
        def connect(sid: str, envir):
            self._sio.emit("data", self.read_input("data"), to=sid)

        self._message = None
        self._server_running = False

    def _execute(self, val=None):
        if not self.is_started():
            return
        self._message = self.read_input("data")
        print(f"execute: <{self._message}>")

    def start(self):
        def run_server():
            pool = eventlet.GreenPool(1)

            def run():
                try:
                    self._outputs["uri"].set(
                        f"http://{socket.gethostname()}:{int(self.read_param("port"))}/"
                    )
                    print(self._outputs["uri"].get())
                    eventlet.wsgi.server(
                        eventlet.listen(
                            (socket.gethostname(), int(self.read_param("port")))
                        ),
                        self._app,
                    )
                except:
                    pass

            server = pool.spawn(run)

            self.set_status(STATUS_RUN)

            self._server_running = True
            while self._server_running:
                eventlet.sleep(0)
                if self._message is not None:
                    self._sio.emit("data", f"{self._message}")
                    print(f"emit: <{self._message}>")
                    self._message = None

            print("stopping")
            pool.resize(0)
            server.kill()
            print("server stopped")
            self._outputs["uri"].set("")
            self.set_status(STATUS_STOP)

        ThreadPoolExecutor(1).submit(run_server)
        self._execute()

    def stop(self):
        self._server_running = False


if __name__ == "__main__":
    from app import run_as_main_file

    run_as_main_file()
