"""Test de fumée de l'exécutable construit : il démarre, sert la page et s'arrête.

python packaging/smoke.py CHEMIN_DE_L_EXECUTABLE
"""

import socket
import subprocess
import sys
import tempfile
import time
import urllib.request


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def main(exe: str) -> int:
    port = free_port()
    with tempfile.TemporaryDirectory() as config:
        process = subprocess.Popen(
            [exe, "--headless", "--serve", "--host", "localhost", "--web-port", str(port)]
            + ["--config-dir", config],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    break
                try:
                    url = "http://127.0.0.1:%d/" % port
                    with urllib.request.urlopen(url, timeout=2) as response:  # noqa: S310
                        page = response.read().decode("utf-8")
                    for name in ("index.css", "index.js"):
                        with urllib.request.urlopen(url + name, timeout=2):  # noqa: S310
                            pass
                    if "<html" in page.lower():
                        print("OK : la page est servie par l'exécutable")
                        return 0
                except OSError:
                    time.sleep(0.5)
            print("ÉCHEC : la page n'est pas servie", file=sys.stderr)
            if process.poll() is not None:
                print(process.stderr.read(), file=sys.stderr)
            return 1
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(10)
                except subprocess.TimeoutExpired:
                    process.kill()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
