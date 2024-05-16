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
`document = ragna.core.LocalDocument`. Internally, this is roughly treated as
`from ragna.core import LocalDocument`.

You can inject your own objects here and do not need to rely on the defaults by Ragna.
To do so, make sure that the module the object is defined in is on
[Python's search path](https://docs.python.org/3/library/sys.html#sys.path). There are
multiple ways to achieve this, e.g.:

- Install your module as part of a package in your current environment.
- Set the [`PYTHONPATH`](https://docs.python.org/3/using/cmdline.html#envvar-PYTHONPATH)
  environment variable to include the directory your module is located in.

## Environment variables

All configuration options can be set or overridden by environment variables by using the
`RAGNA_` prefix. For example, `document = ragna.core.LocalDocument` in the configuration
file is equivalent to setting `RAGNA_DOCUMENT=ragna.core.LocalDocument`.

For configuration options in subsections, the subsection name needs to be appended to
the prefix, e.g. `RAGNA_API_`. The value needs to be in JSON format. For example

```toml
[api]
origins = [
    "http://localhost:31477",
]
```

is equivalent to `RAGNA_API_ORIGINS='["http://localhost:31477"]'`.

## Configuration options

### `local_root`

Local root directory Ragna uses for storing files. See [ragna.local_root][].

### `authentication`

[ragna.deploy.Authentication][] class to use for authenticating users.

### `document`

[ragna.core.Document][] class to use to upload and read documents.

### `source_storages`

[ragna.core.SourceStorage][]s to be available for the user to use.

### `assistants`

[ragna.core.Assistant][]s to be available for the user to use.

### `api`

#### `hostname`

Hostname the REST API will be bound to.

#### `port`

Port the REST API will be bound to.

#### `root_path`

A path prefix handled by a proxy that is not seen by the REST API, but is seen by
external clients.

#### `url`

URL of the REST API to be accessed by the web UI. Make sure to include the
[`root_path`](#root_path) if set.

#### `origins`

[CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS) origins that are allowed
to connect to the REST API. The URL of the web UI is required for it to function.

#### `database_url`

URL of a SQL database that will be used to store the Ragna state. See
[SQLAlchemy documentation](https://docs.sqlalchemy.org/en/20/core/engines.html#database-urls)
on how to format the URL.

### `ui`

#### `hostname`

Hostname the web UI will be bound to.

#### `port`

Port the web UI will be bound to.

#### `origins`

[CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS) origins that are allowed
to connect to the web UI.
