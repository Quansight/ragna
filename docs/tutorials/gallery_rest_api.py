"""
# REST API

Ragna was designed to help you quickly build custom RAG powered web
applications. For this you can leverage the built-in
[REST API](../../references/deploy.md).

This tutorial walks you through basic steps of using Ragna's REST API.
"""

# %%
# ## Step 1: Start the REST API
#
# Ragnas REST API is normally started from a terminal with
#
# ```bash
# $ ragna deploy
# ```
#
# For this tutorial we use our helper that does the equivalent just from Python.
#
# !!! note
#
#     By default, the REST API is started from the `ragna.toml` configuration file in
#     the current working directory. If you don't have a configuration file yet, you can
#     run
#
#     ```bash
#     $ ragna init
#     ```
#
#     to start an interactive wizard that helps you create one. The config that we'll
#     be using for this tutorial is equivalent of picking the first option the wizard
#     offers you, i.e. using only demo components.

import ragna._docs as ragna_docs

from ragna.deploy import Config

config = Config()

ragna_deploy = ragna_docs.RagnaDeploy(config=config)

# %%
# Let's make sure the REST API is started correctly and can be reached.

import httpx

client = httpx.Client(base_url=f"http://{config.hostname}:{config.port}")
client.get("/health").raise_for_status()


# %%
# ## Step 2: Authentication
#
# In order to use Ragna's REST API, we need to authenticate first. This is handled by
# the [ragna.deploy.Auth][] class, which can be overridden through the config. By
# default, [ragna.deploy.NoAuth][] is used. By hitting the `/login` endpoint, we get a
# session cookie, which is later used to authorize our requests.

client.get("/login", follow_redirects=True)
dict(client.cookies)

# %%
# !!! note
#
#     In a regular deployment, you'll have login through your browser and create an API
#     key in your profile page. The API key is used as
#     [bearer token](https://swagger.io/docs/specification/authentication/bearer-authentication/)
#     and can be set with
#
#     ```python
#     httpx.Client(..., headers={"Authorization": f"Bearer {RAGNA_API_KEY}"})
#     ```

# %%
# ## Step 3: Uploading documents
#
# Before we start with the upload process, let's first have a look what kind of
# documents are supported.

import json

response = client.get("/api/components").raise_for_status()
print(json.dumps(response.json(), indent=2))

# %%
# For simplicity, let's use a demo document with some information about Ragna

from pathlib import Path

print(ragna_docs.SAMPLE_CONTENT)

document_path = Path.cwd() / "ragna.txt"

with open(document_path, "w") as file:
    file.write(ragna_docs.SAMPLE_CONTENT)

# %%
# The upload process in Ragna consists of two parts:
#
# 1. Register the document in Ragna's database. This returns the document ID, which is
#    needed for the upload.

response = client.post(
    "/api/documents", json=[{"name": document_path.name}]
).raise_for_status()
documents = response.json()
print(json.dumps(documents, indent=2))

# %%
# 2. Perform the upload through a
# [multipart request](https://swagger.io/docs/specification/describing-request-body/multipart-requests/)
# with the following parameters:
#
# - The field is `documents` for all entries
# - The field name is the ID of the document returned by step 1.
# - The field value is the binary content of the document.

client.put(
    "/api/documents",
    files=[("documents", (documents[0]["id"], open(document_path, "rb")))],
)

# %%
# ## Step 4: Select a source storage and assistant
#
# The configuration we are using only supports demo components for the source storage
# and assistant and so we pick them here.

from ragna import source_storages, assistants

source_storage = source_storages.RagnaDemoSourceStorage.display_name()
assistant = assistants.RagnaDemoAssistant.display_name()

print(f"{source_storage=}, {assistant=}")

# %%
# ## Step 5: Start chatting
#
# Now that we have uploaded a document, and selected a source storage and assistant to
# be used, we can create a new chat.

response = client.post(
    "/api/chats",
    json={
        "name": "Tutorial REST API",
        "input": [document["id"] for document in documents],
        "source_storage": source_storage,
        "assistant": assistant,
    },
).raise_for_status()
chat = response.json()
print(json.dumps(chat, indent=2))

# %%
# As can be seen by the `"prepared": false` value in the `chat` JSON object we still
# need to prepare it.

client.post(f"/api/chats/{chat['id']}/prepare").raise_for_status()

# %%
# Finally, we can get answers to our questions.

response = client.post(
    f"/api/chats/{chat['id']}/answer",
    json={"prompt": "What is Ragna?"},
).raise_for_status()
answer = response.json()
print(json.dumps(answer, indent=2))

# %%

print(answer["content"])

# %%
# Before we close the tutorial, let's terminate the REST API and have a look at what
# would have printed in the terminal if we had started it with the `ragna deploy`
# command.

ragna_deploy.terminate()
