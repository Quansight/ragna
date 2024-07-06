"""
# REST API

Ragna was designed to help you quickly build custom RAG powered web
applications. For this you can leverage the built-in
[REST API](../../references/rest-api.md).

This tutorial walks you through basic steps of using Ragnas REST API.
"""

# %%
# ## Step 1: Start the REST API
#
# Ragnas REST API is normally started from a terminal with
#
# ```bash
# $ ragna api
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

rest_api = ragna_docs.RestApi()
_ = rest_api.start(config)

# %%
# Let's make sure the REST API is started correctly and can be reached.

import httpx

client = httpx.Client(base_url=config.api.url)
client.get("/").raise_for_status()


# %%
# ## Step 2: Authentication
#
# In order to use Ragnas REST API, we need to authenticate first. To forge an API token
# we send a request to the `/token` endpoint. This is processed by the
# [`Authentication`][ragna.deploy.Authentication], which can be overridden through the
# config. For this tutorial, we use the default
# [ragna.deploy.RagnaDemoAuthentication][], which requires a matching username and
# password.

username = password = "Ragna"

response = client.post(
    "/token",
    data={"username": username, "password": password},
).raise_for_status()
token = response.json()

# %%
# We set the API token on our HTTP client so we don't have to manually supply it for
# each request below.

client.headers["Authorization"] = f"Bearer {token}"


# %%
# ## Step 3: Uploading documents
#
# Before we start with the upload process, let's first have a look what kind of
# documents are supported.

import json

response = client.get("/components").raise_for_status()
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
# 1. Announce the file to be uploaded. Under the hood this pre-registers the document
#    in Ragnas database and returns information about how the upload is to be performed.
#    This is handled by the [ragna.core.Document][] class. By default,
#    [ragna.core.LocalDocument][] is used, which uploads the files to the local file
#    system.
# 2. Perform the actual upload with the information from step 1.

response = client.post(
    "/document", json={"name": document_path.name}
).raise_for_status()
document_upload = response.json()
print(json.dumps(response.json(), indent=2))

# %%
# The returned JSON contains two parts: the document object that we are later going to
# use to create a chat as well as the upload parameters.
# !!! note
#
#     The `"token"` in the response is *not* the Ragna REST API token, but rather a
#     separate one to perform the document upload.
#
# We perform the actual upload with the latter now.

document = document_upload["document"]

parameters = document_upload["parameters"]
client.request(
    parameters["method"],
    parameters["url"],
    data=parameters["data"],
    files={"file": open(document_path, "rb")},
).raise_for_status()

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
    "/chats",
    json={
        "name": "Tutorial REST API",
        "documents": [document],
        "source_storage": source_storage,
        "assistant": assistant,
        "params": {},
    },
).raise_for_status()
chat = response.json()
print(json.dumps(chat, indent=2))

# %%
# As can be seen by the `"prepared"` field in the `chat` JSON object we still need to
# prepare it.

client.post(f"/chats/{chat['id']}/prepare").raise_for_status()

# %%
# Finally, we can get answers to our questions.

response = client.post(
    f"/chats/{chat['id']}/answer",
    json={"prompt": "What is Ragna?"},
).raise_for_status()
answer = response.json()
print(json.dumps(answer, indent=2))

# %%

print(answer["content"])

# %%
# Before we close the tutorial, let's stop the REST API and have a look at what would
# have printed in the terminal if we had started it with the `ragna api` command.

rest_api.stop()
