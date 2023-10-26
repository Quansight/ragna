# Basics of the REST API

Ragna was designed to help you quickly build custom RAG and LLM powered web
applications. You can leverage the built-in REST API (which is consistent with the
Python API designed for experimentation) for application development.

This tutorial walks you through basic steps of using the REST API for creating a chat
service.

## Step 1: Setup RAG configuration

Ragna workflows starts with a configuration. You can select the components like the
assistant (LLM) and source storage (vector database) and set options like the API
endpoint and cache location.

To quickly try out Ragna, you can use the `demo` configuration:

```py
config = Config.demo()
```

It includes the `RagnaDemoAssistant` and `RagnaDemoSourceStorage`.

Learn more in [How to set configuration](../how-tos/set-configuration.md).

## Step 2: Start and connect to the API

You can use the [`ragna api`](../references/cli.md#ragna-api) command to start the REST
API from you terminal. The command includes a `--config` option where you can chose your
preferred configuration.

This tutorial is using the `demo` configuration, so you can start the API using the
built-in `demo` config option:

```bash
ragna api --config demo
```

Once started, use the displayed URL to connect to the running API. By default, Ragna
starts the API at [http://127.0.0.1/31476](http://127.0.0.1/31476). You can set a
different URL in the configuration stage as well.

This tutorial uses [`httpx`](https://github.com/encode/httpx), a HTTP client for Python
to demonstrate the REST API. However, feel free to use the language or library of your
choice!

Let's connect to the API with an `AsyncClient`:

```py
client = httpx.AsyncClient(base_url=config.api.url)
```

<!-- TODO: Add note about async preference -->

## Step 3: Authentication

The REST requires authentication into your user session, with a username and password,
before you can use Ragna.

For demonstration or exploration alone, you set the password as an environment variable
and use that for demo authentication:

```bash
export RAGNA_DEMO_AUTHENTICATION_PASSWORD="*****"
```

And, use this password with any username.

```py
USERNAME = "Ragnvaldr"

token = (
    await client.post(
        "/token",
        data={
            "username": USERNAME,
            "password": "*****",
        },
    )
).json()

client.headers["Authorization"] = f"Bearer {token}"
```

<!-- Note: "Ragnvaldr" means advice/counsel/ruler in Old Norse. Using this as the username instead of "Ragna" to not overload the term.-->

!!! tip

    Alternatively, you can make sure the username and password provided are identical.
    This approach will also successfully authenticate you.

## Step 4: Upload documents

Once authenticated, you can use the different Ragna components!

Let's start with uploading a document that can provide relevant context to the
Assistants (LLM)s.

### Create a document (optional)

```py
path = "document.txt"

with open(path, "w") as file:
    file.write("Ragna is an open-source RAG orchestration app.")
```

### Request upload information

```py
response = await client.get("/document", params={"name": path.name})
document_info = response.json()
```

### Upload

```py
response = await client.post(
    document_info["url"],
    data=document_info["data"],
    files={"file": open(path, "rb")},
)
```

## Step 5: Select source storage and assistant

You can now select the source storage (vector database) and assistant (Large Language
Model) you want to use for the chat.

View options available as per your configuration:

```py
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

Select your preferred options. As per the demo configuration, the following snippet
selects the `RagnaDemoSourceStorage` and `RagnaDemoAssistant`.

```py
SOURCE_STORAGE = components["source_storages"][0]["title"]
ASSISTANT = components["assistants"][0]["title"]
```

## Step 6: Create the chat

With selection and setup complete, you can start a Ragna chat.

### Create a new chat

```py
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

```py
CHAT_ID = chat["id"]

response = await client.post(f"/chats/{CHAT_ID}/prepare")
chat = response.json()
```

### Share prompts and get answers

```py
response = await client.post(
    f"/chats/{CHAT_ID}/answer", params={"prompt": "What is Ragna?"}
)
answer = response.json()

print(answer["message"])
```

## Additional helpful features

### List available chats

```py
response = await client.get("/chats")
chats = response.json()

print(chats)
```

### Delete chats

```py
await client.delete(f"/chats/{CHAT_ID}")
```
