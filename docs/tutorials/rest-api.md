# Basics of the REST API

Ragna was designed to help you quickly build custom RAG and LLM powered web
applications. You can leverage the built-in [REST API](../references/rest-api.md) (which
is consistent with the [Python API](../references/python-api.md) designed for
experimentation) for application development.

This tutorial walks you through basic steps of using the REST API for creating a chat
service.

## Step 1: Setup RAG configuration

Ragna workflows start with a configuration. You can select components like the assistant
(LLM) and source storage (vector database) and set options like the API endpoint and
cache location.

Use the CLI wizard and pick the first option to generate a basic configuration file:

```bash
ragna init
```

Create a configuration using the file:

```python
from ragna import Config

config = Config.from_file("ragna.toml")
```

Learn more in [How to set configuration](../how-tos/set-configuration.md).

## Step 2: Start and connect to the API

You can use the [`ragna api`](../references/cli.md#ragna-api) command to start the REST
API from your terminal. The command includes a `--config` option where you can chose
your preferred configuration.

The `ragna.toml` file generated by the CLI wizard will be used by default:

```bash
ragna api
```

Once started, use the displayed URL to connect to the running API. By default, Ragna
starts the API at [http://127.0.0.1/31476](http://127.0.0.1/31476). You can set a
different URL in the configuration stage as well.

This tutorial uses [`httpx`](https://github.com/encode/httpx), an HTTP client for Python
to demonstrate the REST API. However, feel free to use the language or library of your
choice!

Let's connect to the API with an `AsyncClient`:

```python
import httpx

client = httpx.AsyncClient(base_url=config.api.url)
```

<!-- TODO: Add note about async preference -->

## Step 3: Authentication

The REST API requires authenticating your user session with a username and password
before you can use Ragna.

For demonstration purposes, set the password as an environment variable and use that for
demo authentication:

```bash
export RAGNA_DEMO_AUTHENTICATION_PASSWORD="my_password"
```

And use this password with any username.

```py
USERNAME = "Ragnvaldr"

token = (
    await client.post(
        "/token",
        data={
            "username": USERNAME,
            "password": "my_password",
        },
    )
).json()

client.headers["Authorization"] = f"Bearer {token}"
```

<!-- Note: "Ragnvaldr" means advice/counsel/ruler in Old Norse. Using this as the username instead of "Ragna" to not overload the term.-->

!!! tip

    Alternatively, you can make the username and password identical.
    This approach will also successfully authenticate you.

## Step 4: Upload documents

Once authenticated, you can use the different Ragna components!

Let's start with uploading a document that can provide relevant context to the
Assistants (LLMs).

### Create a document (optional)

```python
path = "document.txt"

with open(path, "w") as file:
    file.write("Ragna is an open-source RAG orchestration app.")
```

### Request upload information

```python
response = await client.get("/document", params={"name": path.name})
document_info = response.json()
```

### Upload

```python
response = await client.post(
    document_info["url"],
    data=document_info["data"],
    files={"file": open(path, "rb")},
)
```

## Step 5: Select source storage and assistant

You can now select the source storage (vector database) and assistant (LLM) you want to
use for the chat.

View options available based on your configuration:

```python
response = await client.get("/components")
components = response.json()

# `components` has the following structure:
#
# {'documents': ['.pdf', '.txt'],
#  'source_storages': [{'properties': {},
#                       'required': [],
#                       'title': 'Ragna/DemoSourceStorage',
#                       'type': 'object'}],
#  'assistants': [{'properties': {},
#                  'title': 'Ragna/DemoAssistant',
#                  'type': 'object'}]}
```

Select your preferred options. For the demo, the following snippet selects the
`RagnaDemoSourceStorage` and `RagnaDemoAssistant`.

```python
SOURCE_STORAGE = components["source_storages"][0]["title"]
ASSISTANT = components["assistants"][0]["title"]
```

## Step 6: Create the chat

With selection and setup complete, you can now start a Ragna chat.

### Create a new chat

```python
response = await client.post(
    "/chats",
    json={
        "name": "My Ragna-based chat",
        "documents": [document],
        "source_storage": SOURCE_STORAGE,
        "assistant": ASSISTANT,
        "params": {},
    },
)
chat = response.json()
```

### Prepare the chat

```python
CHAT_ID = chat["id"]

response = await client.post(f"/chats/{CHAT_ID}/prepare")
chat = response.json()
```

### Share prompts and get answers

```python
response = await client.post(
    f"/chats/{CHAT_ID}/answer", params={"prompt": "What is Ragna?"}
)
answer = response.json()

print(answer["message"])
```

## Additional helpful features

### List available chats

```python
response = await client.get("/chats")
chats = response.json()

print(chats)
```

### Delete chats

```python
await client.delete(f"/chats/{CHAT_ID}")
```