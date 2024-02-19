# Configuration reference

Ragna uses [TOML](https://toml.io/en/) as language for its configuration file. The
`ragna` CLI defaults to `ragna.toml` in the current working directory. This behavior can
be overritten in two ways:

1. The `RAGNA_CONFIG` environment variable.
2. The `-c` / `--config` option of the `ragna` CLI subcommands.

The CLI option takes precedence over the environment variable.

There are two main ways to generate a configuration file:

1. Running `ragna init` in a terminal starts an interactive wizard that guides you
   through the generation. The example configuration below is the result of choosing the
   first option the wizard offers you.
2. The configuration can also be created programmatically from Python. The example
   configuration below is the result of the following snippet.

   ```python
   from ragna.deploy import Config

   config = Config()
   config.to_file("ragna.toml")
   ```

## Example

```toml
{{ config }}
```

## Referencing Python objects

Some configuration options reference Python objects, e.g.
`document = ragna.core.LocalDocument`. You can inject your own objects here and do not
need to rely on the defaults by Ragna. To do so, make sure that the module the object is
defined in is on the
[`PYTHONPATH`](https://docs.python.org/3/using/cmdline.html#envvar-PYTHONPATH). The
`document` configuration mentioned before internally is roughly treated as
`from ragna.core import LocalDocument`.

## Environment variables

All configuration options can be set or overritten by environment variables by using the
`RAGNA_` prefix. For example, `document = ragna.core.LocalDocument` in the configuration
file is equivalent to setting `RAGNA_DOCUMENT=ragna.core.LocalDocument`.

For configuration options in subsections, the subsection name needs to be appended to
the prefix, e.g. `RAGNA_COMPONENTS_`. The value needs to be in JSON format. For example

```toml
[components]
assistants = [
    "ragna.assistants.RagnaDemoAssistant",
]
```

is equivalent to
`RAGNA_COMPONENTS_ASSISTANTS='["ragna.assistants.RagnaDemoAssistant"]'`.

## Configuration options

### `local_cache_root`

### `document`

[ragna.core.Document][] class to use to upload and read documents.

### `authentication`

[ragna.deploy.Authentication][] class to use for authenticating users.

### `components`

#### `source_storages`

[ragna.core.SourceStorage][]s to be available for the user to use.

#### `assistants`

[ragna.core.Assistant][]s to be available for the user to use.

### `api`

#### `url`

1. Hostname and port the REST API server will be bound to.
2. URL of the REST API to be accessed by the web UI.

#### `origins`

[CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS) origins that are allowed
to connect to the REST API. The URL of the web UI is required for it to function.

#### `database_url`

URL of a SQL database that will be used to store the Ragna state. See
[SQLAlchemy documentation](https://docs.sqlalchemy.org/en/20/core/engines.html#database-urls)
on how to format the URL.

#### `root_path`

A path prefix handled by a proxy that is not seen by the REST API, but is seen by
external clients.

### `ui`

#### `url`

Hostname and port the web UI server will be bound to.

#### `origins`

[CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS) origins that are allowed
to connect to the web UI.
