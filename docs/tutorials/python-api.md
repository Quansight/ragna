# Ragna 101: Minimal RAG+LLM chat in Python

Ragna's Python API is the best place to get started with Ragna and understand it's key components. It's also the best way to continue experimenting with different LLMs and configurations for your particular use case.

In this tutorial you will build your first RAG chat application in a Jupyter Notebook.

An example notebook corresponding to this tutorial is available at ....

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

## Step 1: Setup RAG configuration

The first step is to setup a configuration for Ragna.

You can set this using a config.

You can start with the `demo_config`:

```python
from ragna import demo_config
```

<!-- Link to API Ref. for Config() when available -->

## Step 2: Select an LLM (assistant)

```py
from ragna.assistant import (
    RagnaDemoAssistant,
    OpenaiGpt35Turbo16kAssistant,
    OpenaiGpt4Assistant,
)
```

## Upload relevant documents

## Select source storage

## Start a chat

## Complete minimal example

```python
import asyncio

from ragna import Rag
from ragna.assistant import RagnaDemoAssistant
from ragna.source_storage import RagnaDemoSourceStorage


async def main():
    rag = Rag()

    path = "ragna.txt"
    with open(path, "w") as file:
        file.write("Ragna is an OSS RAG app with Python and REST API.\n")

    async with await rag.new_chat(
        documents=[path],
        source_storage=RagnaDemoSourceStorage,
        assistant=RagnaDemoAssistant,
    ) as chat:
        print(await chat.answer("What is Ragna?"))


# This is only needed when running module as script.
# If inside a notebook, the code inside the main function can be run directly.
if __name__ == "__main__":
    asyncio.run(main())
```
