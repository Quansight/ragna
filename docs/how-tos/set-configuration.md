# Set configuration

Ragna's configuration includes setting the LLM, source storage, API endpoint, UI port, and more. Your chat will use these configurations by default when provided.

## Create `config.toml`

Storing your Ragna configuration in a file is recommended approach for any serious use.
It's a convenient way to make and keep track of changes.

You can set the following parameters:

<!-- TODO: Add descriptions for each config options as comments
Alternatively, link to API reference when available & if it provides enough context.
-->

```toml
local_cache_root = "/home/<user>/.cache/ragna"

[rag]
queue_url = "memory"
document = "ragna_s3_document.S3Document"
source_storages = ["ragna.source_storages.RagnaDemoSourceStorage"]
assistants = ["ragna.assistants.RagnaDemoAssistant"]

[api]
url = "http://127.0.0.1:31476"
database_url = "memory"
upload_token_secret = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
upload_token_ttl = 300

[ui]
url = "http://127.0.0.1:31477"
```

## Create config using the file

```py
from ragna import Config

config_path ="path-to-config-file"
config = Config.from_file(config_path)
```

## Override configuration for a chat

The `Rag.chat()` function also allows you to set certain RAG-specific configurations like `document` and `assistants`.

<!-- TODO: Add clarification for how this is different -->
