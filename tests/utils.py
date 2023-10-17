import contextlib
import functools
import socket
import subprocess
import sys
import threading


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


def timeout_after(seconds=5, *, message=None):
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            msg = f"Timeout after {seconds:.1f} seconds"
            if message is not None:
                msg = f"{msg}: {message}"

            result = TimeoutError(msg)

            def target():
                nonlocal result
                try:
                    result = fn(*args, **kwargs)
                except Exception as exc:
                    result = exc

            thread = threading.Thread(target=target)
            thread.daemon = True

            thread.start()
            thread.join(seconds)

            if isinstance(result, Exception):
                raise result

            return result

        return wrapper

    return decorator


def get_available_port():
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]
