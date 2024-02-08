"""
# Ragna 101: Minimal RAG+LLM chat in Python

Ragna's [Python API](../../references/python-api.md) is the best place to get started with
Ragna and understand its key components. It's also the best way to continue
experimenting with different LLMs and configurations for your particular use case.

In this tutorial, you will build your first RAG chat application.
"""

# %%
# ## Step 1: Select relevant documents
#
# The RAG framework is powerful because it can maintain context from the information
# sources that you provide. In Ragna, you can use text files to share this information.
#
# Create a `ragna.txt` and add some relevant text to it, for example:

path = "ragna.txt"

with open(path) as file:
    print(file.read())

# %%
# ## Step 2: Select source storage
#
# The sources and information (in our case the `ragna.txt`) need be to stored in a
# vector database.
#
# !!! info
#
#     Vector databases can effectively store
#     [embeddings (represented as vectors)](https://platform.openai.com/docs/guides/embeddings/what-are-embeddings)
#     created by deep learning models. Learn more in
#     [this blog post by Cloudflare](https://www.cloudflare.com/en-gb/learning/ai/what-is-vector-database/).
#
# Ragna has a few built-in options:
#
# - **`RagnaDemoSourceStorage`** - Not an actual database. Instead stores tokens and
#   sources as objects in memory. It provides a quick way to try out Ragna.
# - **`Chroma`** - Learn more in the [official website](https://www.trychroma.com/)
# - **`LanceDB`** - Learn more in the [official website](https://lancedb.com/)
# %%

from ragna.source_storages import RagnaDemoSourceStorage

# %%
# ## Step 3: Select an assistant (LLM)
#
# Pick the Large Language Model you want to use as your chat assistant.
#
# Similar to source storages, Ragna has the following built-in options:
#
# - **`RagnaDemoAssistant`** - Not an actual LLM. Instead replies with your prompt and a
#   static message. It provides a quick way to setup and use Ragna.
# - **OpenAI's `Gpt35Turbo16k` and `Gpt4`**
# - **MosaicML's `Mpt7bInstruct` and `Mpt30bInstruct`**
# - **Anthropic's `ClaudeInstant` and `Claude`**
#
# Pick the demo assistant for this tutorial:

from ragna.assistants import RagnaDemoAssistant

# %%
# !!! note
#
#     You need to [get API keys](../../references/faq.md#where-do-i-get-api-keys-for-the-builtin-assistants)
#     and set relevant environment variables to use the other supported assistants.
#
# ## Step 4: Start chatting
#
# Ragna chats are asynchronous for better performance in real-world scenarios. You can
# check out
# [Python's asyncio documentation](https://docs.python.org/3/library/asyncio.html) for
# more information. In practice, you don't need to understand all the details, only use
# the `async` and `await` keywords with the function definition and call respectively.
#
# You can provide your assistant, document, and source storage selections to the
# `rag.chat` function, and share your prompt (question to the LLM) using `.answer()`:
from ragna import Rag

async with Rag().chat(
    documents=[path],
    source_storage=RagnaDemoSourceStorage,
    assistant=RagnaDemoAssistant,
) as chat:
    prompt = "What is Ragna?"
    answer = await chat.answer(prompt)

print(answer)
