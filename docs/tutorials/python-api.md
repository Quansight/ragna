# Ragna 101: Minimal RAG+LLM chat in Python

Ragna's Python API is the best place to get started with Ragna and understand it's key
components. It's also the best way to continue experimenting with different LLMs and
configurations for your particular use case.

In this tutorial, you will build your first RAG chat application in a Jupyter Notebook.

## Preliminary setup

Make sure you have Ragna and JupyterLab (or Notebook) installed in your working
environment.

```bash
ragna --version

jupyter lab --version
```

Start JupyterLab:

```bash
jupyter lab
```

And, launch a new notebook.

## Step 1: Setup RAG configuration

The first step is to setup the configuration for components like the source storage
(vector database), API, assistant (LLM), and more. You can set this using a
`config.toml` file, learn more in the
[how-to guide for setting configuration](../how-tos/set-configuration.md).

For this minimal tutorial on basics, start with the default configuration:

```python
from ragna import Config

config = Config()
config
```

Learn more in [Set configuration](../how-tos/set-configuration.md).

## Step 2: Upload relevant documents

The RAG framework is powerful because it can maintain context from the information
sources that you provide. In Ragna, you can use text files to share this information.

Create a `ragna.txt` and add some relevant text to it, for example:

```python
path = "ragna.txt"

with open(path, "w") as file:
    file.write("Ragna is an open-source RAG orchestration app.\n")
```

## Step 3: Select source storage

The sources and information (in our case the `demo_document.txt`) need be to stored in a
vector database[^1], and similar to assistants, Ragna has a few built-in options:

- `RagnaDemoSourceStorage` - Not an actual database, but stores tokens and sources in as
  objects in memory. It provides a quick way to try out Ragna.
- `Chroma` - Learn more in the [official website](https://www.trychroma.com/)
- `LanceDB` - Learn more in the [official website](https://lancedb.com/)

[^1]:
    Vector databases are databases at can effectively store
    [embeddings (represented as vectors)](https://platform.openai.com/docs/guides/embeddings/what-are-embeddings)
    that are created by deep learning models. Learn more in
    [this blog post by Cloudflare](https://www.cloudflare.com/en-gb/learning/ai/what-is-vector-database/).

You select the demo source storage:

```python
from ragna.source_storages import RagnaDemoSourceStorage
```

## Step 4: Select an assistant (LLM)

Pick the Large Language Model you want to use as your chat assistant.

Ragna has the following built-in options:

- **`RagnaDemoAssistant`** - This is not actually an LLM, and will not provide useful
  answers. It's a demo (toy) assistant so that you can quickly setup and use Ragna.
- **OpenAI's `Gpt35Turbo16k` and `Gpt4`**
- **MosaicML's `Mpt7bInstruct` and `Mpt30bInstruct`**
- **Anthropic's `ClaudeInstant` and `Claude`**

Pick the demo assistant for this tutorial:

```python
from ragna.assistants import RagnaDemoAssistant
```

!!! note The RagnaDemoAssistant is not an assistant(LLM), instead it replies with the
your prompt and a static message. It is only to understand the Ragna API. You need to
get API keys and set relevant environment variables to use the supported assistants.

## Step 5: Start a chat

That's all the setup, you can now use Ragna to create a chat app.

### Create a `Rag` object with your configuration

```python
from ragna.core import Rag

rag =  Rag(config)
```

!!! note

    Setting the default configuration is not required.
    If you create the instance with no configuration: `rag = Rag()`,
    the default configuration is applied by default.
    This tutorial includes setting config because it's an important component of Ragna.

### Start an async chat

Ragna chats are asynchronous for better performance in real-world scenarios. You can
check out
[Python's asyncio documentation](https://docs.python.org/3/library/asyncio.html) for
more information. In practice, you don't need to understand all the details, only use
the `async` and `await` keywords with the function definition and call respectively.

You can provide your assistant, document, and source storage selections to the
`rag.chat` function, and share your prompt (question to the LLM) using `.answer()`:

```python

async def main():
    async with rag.chat(
        documents=[path],
        source_storage=RagnaDemoSourceStorage,
        assistant=RagnaDemoAssistant,
    ) as chat:
        prompt = "What is Ragna?"
        answer = await chat.answer(prompt)

    print(answer)
```

## Complete example script

Putting together all the sections in this tutorial in a Python script:

```python
import asyncio

from ragna import Rag
from ragna.assistants import RagnaDemoAssistant
from ragna.source_storages import RagnaDemoSourceStorage


async def main():
    rag = Rag()

    path = "ragna.txt"

    with open(path, "w") as file:
        file.write("Ragna is an open-source RAG orchestration app.\n")

    async with rag.chat(
        documents=[path],
        source_storage=RagnaDemoSourceStorage,
        assistant=RagnaDemoAssistant,
    ) as chat:
        prompt = "What is Ragna?"
        answer = await chat.answer(prompt)

    print(answer)


# This is only needed when running module as script.
# If inside a notebook, the code inside the main function can be run directly.
if __name__ == "__main__":
    asyncio.run(main())
```

A Jupyter notebook corresponding to this tutorial is available in the
[`examples` directory in the GitHub repository](https://github.com/Quansight/ragna/blob/main/examples/python_api/python_api.ipynb).
