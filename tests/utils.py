import contextlib
import signal
import socket
import subprocess
import sys


@contextlib.contextmanager
def background_subprocess(
    *args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs
):
    process = subprocess.Popen(*args, stdout=stdout, stderr=stderr, **kwargs)
    try:
        yield process
    finally:
        process.kill()
        stdout, stderr = process.communicate()
        if stdout:
            sys.stdout.buffer.write(stdout)
            sys.stdout.flush()
        if stderr:
            sys.stderr.buffer.write(stderr)
            sys.stderr.flush()


@contextlib.contextmanager
def timeout_after(seconds=5, *, message=None):
    if not hasattr(signal, "SIGALRM"):
        raise RuntimeError(
            "Timeout is implemented using signal.SIGALRM, "
            "but the current platform doesn't support it. "
        )

    __tracebackhide__ = True

    class InternalTimeoutError(Exception):
        pass

    def handler(signum, frame):
        __tracebackhide__ = True
        raise InternalTimeoutError

    signal.signal(signal.SIGALRM, handler)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    except InternalTimeoutError:
        msg = f"Timeout after {seconds:.1f} seconds"
        if message is not None:
            msg = f"{msg}: {message}"
        raise TimeoutError(msg) from None
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, signal.SIG_DFL)


def get_available_port():
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]
