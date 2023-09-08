import typer

from ragna2.core import Worker

app = typer.Typer(
    name="ragna",
    invoke_without_command=True,
    no_args_is_help=True,
    add_completion=False,
    pretty_exceptions_enable=False,
)


@app.command(help="Start a Ragna worker")
def worker(
    *,
    queue_database_url: str = "redis://localhost:6379",
):
    Worker(queue_database_url=queue_database_url).work()


@app.command(help="List requirements")
def ls():
    pass
