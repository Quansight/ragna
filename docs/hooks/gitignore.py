from pathlib import Path

import pathspec

HERE = Path(__file__).parent
DOCS_ROOT = HERE.parent

with open(DOCS_ROOT / ".gitignore") as file:
    GITIGNORE = pathspec.PathSpec.from_lines(
        pathspec.patterns.GitWildMatchPattern,
        (
            line
            for line in file
            if not (len((line_ := line.strip())) == 0 or line_.startswith("#"))
        ),
    )


def on_serve(server, config, builder):
    # This hook is a hack since mkdocs doesn't allow to exclude files from triggering
    # a rebuild while being watched. We need this behavior, because we otherwise get
    # stuck in an infinite loop whenever something triggers a rebuild: our other hooks
    # create files inside the watched directory, which triggers the hooks again, which
    # creates the files again ...

    def callback_wrapper(callback):
        def wrapper(event):
            if GITIGNORE.match_file(
                Path(event.src_path).relative_to(config.docs_dir).as_posix()
            ):
                return

            return callback(event)

        return wrapper

    handler = (
        next(
            handler
            for watch, handler in server.observer._handlers.items()
            if watch.path == config.docs_dir
        )
        .copy()
        .pop()
    )

    # The callback getting wrapped can be found at
    # https://github.com/mkdocs/mkdocs/blob/828f4685f29dd9e986f18306d58d1cb383d00222/mkdocs/livereload/__init__.py#L142-L148
    handler.on_any_event = callback_wrapper(handler.on_any_event)
