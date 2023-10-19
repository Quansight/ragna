# Ragna 101: Minimal RAG+LLM chat in Python

Ragna's Python API is the best place to get started with Ragna and understand it's key components.
It's also the best way to continue experimenting with different LLMs and configurations for your particular use case.

In this tutorial, you will build your first RAG chat application in a Jupyter Notebook.

## Preliminary setup

Make sure you have Ragna and JupyterLab (or Notebook) installed in your working environment.

```bash
ragna --version

jupyter lab --version
```

Start JupyterLab:

```
jupyter lab
```

And, launch a new notebook.

## Step 1: Setup RAG configuration

The first step is to setup the configuration for components like the storage, api, assistant, and more. You can set this using a `config.toml` file, learn more in the [how-to guide for setting configuration](../how-tos/set-configuration.md).

For this minimal tutorial on basics, start with the default configuration:

```python
from ragna import Config

config = Config()
config
```

<!-- Link to API Ref. for Config() when available -->

## Step 2: Select an assistant (LLM)

Pick the Large Language Model you want to use as your chat assistant.

Ragna has the following built-in options:

* **`RagnaDemoAssistant`** - This is not actually an LLM, and will not provide useful answers. It's a demo (toy) assistant so that you can quickly setup and use Ragna.
* **OpenAI's `Gpt35Turbo16k` and `Gpt4`** - You will need an [OpenAI API key](https://platform.openai.com/docs/quickstart/account-setup) and set the `OPENAI_API_KEY` environment variable to use these assistants.

Pick the demo assistant for this tutorial:

```py
from ragna.assistant import RagnaDemoAssistant
```

## Step 3: Upload relevant documents

The RAG framework is powerful because it can maintain context from the information sources that you provide.
In Ragna, you can use text files to share this information.

Create a `demo_document.txt` and add some relevant text to it, for example:

```py
document_path = "demo_document.txt"

with open(document_path, "w") as file:
    file.write("Ragna is an open-source RAG orchestration app.\n")
```

## Step 4: Select source storage

The sources and information (in our case the `demo_document.txt`) need be to stored in a vector database[^1], and similar to assistants, Ragna has a few built-in options:

* `RagnaDemoSourceStorage` - Not an actual database, but stores tokens and sources in as objects in memory. It provides a quick way to try out Ragna.
* `Chroma` - Learn more in the [official website](https://www.trychroma.com/)
* `LanceDB` - Learn more in the [official website](https://lancedb.com/)

[^1]: Vector databases are databases at can effectively store [embeddings (represented as vectors)](https://platform.openai.com/docs/guides/embeddings/what-are-embeddings) that are created by deep learning models. Learn more in [this blog post by Cloudflare](https://www.cloudflare.com/en-gb/learning/ai/what-is-vector-database/).

You select the demo source storage:

```py
from ragna.source_storages import RagnaDemoSourceStorage,
```

## Step 5: Start a chat

That's all the setup, you can now use Ragna to create a chat app.

### Create a `Rag` object with your configuration

```py
rag =  Rag(config)
```

### Start an async chat

Ragna chats are asynchronous for better performance in real-world scenarios. You can check out [Python's asyncio documentation](https://docs.python.org/3/library/asyncio.html) for more information. In practice, you don't need to understand all the details, only use the `async` and `await` keywords with the function definition and call respectively.

You can provide your assistant, document, and source storage selections to the `rag.chat` function, and share your prompt (question to the LLM) using `.answer()`:

```py
async with rag.chat(
    documents=[document_path],
    source_storage=RagnaDemoSourceStorage,
    assistant=RagnaDemoAssistant,
) as new_chat:
    prompt = "What is Ragna?"
    answer = await new_chat.answer(prompt)

print(answer)
```

## Complete example script

Putting together all the sections in this tutorial in a Python script:

```python
import asyncio

from ragna import Rag
from ragna.assistant import RagnaDemoAssistant
from ragna.source_storage import RagnaDemoSourceStorage


async def main():
    rag = Rag()

    path = "ragna.txt"
    with open(document_path, "w") as file:
    file.write("Ragna is an open-source RAG orchestration app.\n")

    async with rag.chat(
        documents=[document_path],
        source_storage=RagnaDemoSourceStorage,
        assistant=RagnaDemoAssistant,
    ) as new_chat:
        prompt = "What is Ragna?"
        answer = await new_chat.answer(prompt)

    print(answer)


# This is only needed when running module as script.
# If inside a notebook, the code inside the main function can be run directly.
if __name__ == "__main__":
    asyncio.run(main())
```

A Jupyter notebook corresponding to this tutorial is available in the [`examples` directory in the GitHub repository](https://github.com/Quansight/ragna/blob/main/examples/python_api/python_api.ipynb).
