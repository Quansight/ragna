import logging
import sys

import structlog


def get_logger(**initial_values):
    dev_friendly = sys.stderr.isatty()

    processors = [
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.add_log_level,
        structlog.processors.CallsiteParameterAdder(
            parameters=[
                structlog.processors.CallsiteParameter.PATHNAME,
                structlog.processors.CallsiteParameter.LINENO,
            ]
        ),
    ]
    if dev_friendly:
        processors.extend(
            [
                structlog.processors.ExceptionPrettyPrinter(),
                structlog.dev.ConsoleRenderer(),
            ]
        )
    else:
        processors.extend(
            [
                structlog.processors.dict_tracebacks,
                structlog.processors.JSONRenderer(),
            ]
        )

    return structlog.wrap_logger(
        logger=structlog.PrintLogger(),
        cache_logger_on_first_use=True,
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        processors=processors,
        **initial_values,
    )
