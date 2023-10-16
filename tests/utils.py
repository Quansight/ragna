import contextlib

import socket


@contextlib.contextmanager
def timeout_after(seconds=5, *, message=""):
    yield
    # def timeout():
    #     print(f"Timeout after {seconds:.1f} seconds: {message}")
    #     # os._exit(1)
    #
    # timer = threading.Timer(seconds, timeout)
    # timer.start()
    # try:
    #     yield
    # finally:
    #     timer.cancel()


def get_available_port():
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]
