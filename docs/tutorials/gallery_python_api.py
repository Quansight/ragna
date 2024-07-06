"""
# Python API

The [Python API](../../references/python-api.md) is the best place to get started with
Ragna and understand its key components. It's also the best way to continue
experimenting with components and configurations for your particular use case.

This tutorial walks you through basic steps of using Ragnas Python API.
"""

# %%
# ## Step 1: Select relevant documents
#
# Ragna uses the RAG technique to answer questions. The context in which the questions
# will be answered comes from documents that you provide. For this tutorial, let's use a
# sample document that includes some information about Ragna.

from pathlib import Path

import ragna._docs as ragna_docs

print(ragna_docs.SAMPLE_CONTENT)

document_path = Path.cwd() / "ragna.txt"

with open(document_path, "w") as file:
    file.write(ragna_docs.SAMPLE_CONTENT)

# %%
# !!! tip
#
#     Ragna supports the following document types:
#
#     - [`.txt`][ragna.core.PlainTextDocumentHandler]
#     - [`.md`][ragna.core.PlainTextDocumentHandler]
#     - [`.pdf`][ragna.core.PdfDocumentHandler]
#     - [`.docx`][ragna.core.DocxDocumentHandler]
#     - [`.pptx`][ragna.core.PptxDocumentHandler]

# %%
# ## Step 2: Select a source storage
#
# To effectively retrieve the relevant content of the documents, it needs to be stored
# in a [`SourceStorage`][ragna.core.SourceStorage]. In a regular use case this is a
# vector database, but any database with text search capabilities can be used. For this
# tutorial, we are going to use a demo source storage for simplicity.

from ragna.source_storages import RagnaDemoSourceStorage

# %%
# !!! tip
#
#     Ragna has builtin support for the following source storages:
#
#     - [ragna.source_storages.Chroma][]
#     - [ragna.source_storages.LanceDB][]

# %%
# ## Step 3: Select an assistant
#
# Now that we have a way to retrieve relevant sources for a given user prompt, we now
# need something to actually provide an answer. This is performed by an
# [`Assistant`][ragna.core.Assistant], which is Ragnas abstraction around Large Language
# Models (LLMs). For this tutorial, we are going to use a demo assistant for simplicity.

from ragna.assistants import RagnaDemoAssistant

# %%
# !!! tip
#
#     Ragna has builtin support for the following assistants:
#
#     - [Anthropic](https://www.anthropic.com/)
#       - [ragna.assistants.ClaudeOpus][]
#       - [ragna.assistants.ClaudeSonnet][]
#       - [ragna.assistants.ClaudeHaiku][]
#     - [Cohere](https://cohere.com/)
#       - [ragna.assistants.Command][]
#       - [ragna.assistants.CommandLight][]
#     - [Google](https://ai.google.dev/)
#       - [ragna.assistants.GeminiPro][]
#       - [ragna.assistants.GeminiUltra][]
#     - [OpenAI](https://openai.com/)
#       - [ragna.assistants.Gpt35Turbo16k][]
#       - [ragna.assistants.Gpt4][]
#     - [AI21 Labs](https://www.ai21.com/)
#       - [ragna.assistants.Jurassic2Ultra][]
#     - [llamafile](https://github.com/Mozilla-Ocho/llamafile)
#       - [ragna.assistants.LlamafileAssistant][]
#     - [Ollama](https://ollama.com/)
#       - [ragna.assistants.OllamaGemma2B][]
#       - [ragna.assistants.OllamaLlama2][]
#       - [ragna.assistants.OllamaLlava][]
#       - [ragna.assistants.OllamaMistral][]
#       - [ragna.assistants.OllamaMixtral][]
#       - [ragna.assistants.OllamaOrcaMini][]
#       - [ragna.assistants.OllamaPhi2][]
#
#     !!! note
#
#         To use some of the builtin assistants, you need to
#         [procure API keys](../../references/faq.md#where-do-i-get-api-keys-for-the-builtin-assistants)
#         first and set the corresponding environment variables.

# %%
# ## Step 4: Start chatting
#
# We now have all parts to start a chat.

from ragna import Rag

chat = Rag().chat(
    documents=[document_path],
    source_storage=RagnaDemoSourceStorage,
    assistant=RagnaDemoAssistant,
)

# %%
# Before we can ask a question, we need to [`prepare`][ragna.core.Chat.prepare] the chat, which under the hood
# stores the documents we have selected in the source storage.

_ = await chat.prepare()

# %%
# !!! note
#
#     Ragna chats are asynchronous for better performance in real-world scenarios. You
#     can check out
#     [Python's asyncio documentation](https://docs.python.org/3/library/asyncio.html)
#     for more information. In practice, you don't need to understand all the details,
#     only use the `async` and `await` keywords with the function definition and call
#     respectively.

# %%
# Finally, we can get an [`answer`][ragna.core.Chat.answer] to a question.

print(await chat.answer("What is Ragna?"))
