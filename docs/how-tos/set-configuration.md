# Set configuration

Ragna's configuration includes setting the LLM, source storage, API endpoint, UI port,
and more. Your chat will use these configurations by default when provided.

## Create a configuration file

Storing your Ragna configuration in a file is the recommended approach for any serious
workflows. Ragna includes a CLI wizard to walk you through the process of creating this
file.

Run the following command, and answer the questions when prompted:

```bash
ragna init
```

![ragna config executed in the terminal showing questions and selections of the form: Which of the following statements describes best what you want to do? I want to try Ragna and its builtin components; How do you want to select the components? I want to manually select the builtin components I want to use. This continues to allow selecting the [Chroma] source storage and the [OpenAI/gpt-4] assistant.](images/ragna-config-wizard.png)

At the end, this will create a `ragna.toml` file based on your choices.

Here's an example configuration file:

```toml
local_cache_root = "/Users/<username>/.cache/ragna"

[core]
queue_url = "/Users/<username>/.cache/ragna/queue"
document = "ragna.core.LocalDocument"
source_storages = ["ragna.source_storages.Chroma"]
assistants = ["ragna.assistants.Gpt4"]

[api]
url = "http://127.0.0.1:31476"
database_url = "sqlite:////Users/<username>/.cache/ragna/ragna.db"
authentication = "ragna.core.RagnaDemoAuthentication"
upload_token_secret = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
upload_token_ttl = 300

[ui]
url = "http://127.0.0.1:31477"
```

## Set configuration using the file

You can use `ragna.toml` for setting configurations in your applications:

<!--
Using `py``` instesd of `python`` allows for syntax highlighting without doctesting.
This is a work around until https://github.com/koaning/mktestdocs/issues/7 is implemented.
-->

```py
from ragna import Config

config_path ="path-to-config-file"
config = Config.from_file(config_path)
```

!!! note

    In the Python API, the `Rag.chat()` function also allows you to set certain RAG-specific configurations like `document` and `assistants`.
