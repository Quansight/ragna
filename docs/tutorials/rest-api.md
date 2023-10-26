# Basics of the REST API

Ragna was designed to help you quickly build custom RAG-powered web applications. You
can leverage the built-in REST API, which is consistent with the Python API for
application development.

This tutorial walks you through basic steps in the REST API for creating a chat service.

## Step 1: Setup RAG configuration

Your Ragna workflow starts with a configuration. You can select the components like the
assistant (LLM) and source storage (vector database) and set options like the API
endpoint and cache location.

To quickly try out Ragan, you can select the the `demo` configuration. It includes the
`RagnaDemoAssistant` and `RagnaDemoSourceStorage`.

```py
config = Config.demo()
```

Learn more in [Set configuration](../how-tos/set-configuration.md).

## Step 2: Start and connect to the API

You can use the command [`ragna api`](../references/cli.md#ragna-api) to start the REST
API from you terminal. The command includes a `--config` option where you can set your
configuration.

This tutorial is using the `demo` configuration, so you can start the API using the
built-in `demo` config option.

```bash
ragna api --config demo
```

You can connect to the running API using the URL. By default, Ragna starts the API at
http://127.0.0.1/31476. The URL to use can be set in the configuration as well.

This tutorial uses [HTTPX], a http client for Python. You can use the language or
library of your choice.

```py
client = httpx.AsyncClient(base_url=config.api.url)
```

## Step 3: Authenticate

You can authenticate your user session with a username and password.

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

## Step 4: Upload documents

Once authenticated, you can use the different Ragna components.

Let's start with uploading some documents that can provide relevant context to the
Assistants (LLM)s.

### Create a document (optional)

```py
path = "document.txt"

with open(path, "w") as file:
    file.write("Ragna is an open-source RAG orchestration app.")
```

### Request upload information

```py
response = await client.get("/document", params={"user": USER, "name": path.name})
document_info = response.json()
```

### Upload

```py
response = await client.post(
    document_info["url"],
    data=document_info["data"],
    files={"file": open(path, "rb")},
)
assert response.is_success
```

## Step 5: Select components - source storage (vector database) and assistant (Large Language Model)

```py
response = await client.get("/components", params={"user": USER})
components = response.json()
```

```py
SOURCE_STORAGE = components["source_storages"][0]["title"]
ASSISTANT = components["assistants"][0]["title"]
```

## Step 6: Create the chat

## Create a new chat

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

response = await client.post(f"/chats/{CHAT_ID}/prepare", params={"user": USER})
chat = response.json()
```

### Use the chat with prompts

```py
response = await client.post(
    f"/chats/{CHAT_ID}/answer", params={"user": USER, "prompt": "What is Ragna?"}
)
answer = response.json()
pprint(answer["message"], sort_dicts=False)
```

## More features

### List available chats

```py
response = await client.get("/chats", params={"user": USER})
chats = response.json()
pprint(chats, sort_dicts=True)
```

### Delete chats

```py
await client.delete(f"/chats/{CHAT_ID}", params={"user": USER})
```
