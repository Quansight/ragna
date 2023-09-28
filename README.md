# Ragna

## Local install

```bash
$ conda env create --file environment.yaml
$ conda activate ragna-dev
$ pip install --editable '.[complete]'
$ ragna --version
$ ragna ls
```

## Minimal example

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

## Documentation

Ragna uses Sphinx to build it's documentation.

You can contribute to the documentation at `docs/source`,
and start a development build that auto-refreshes on new changes with:

```bash
sphinx-autobuild docs/source docs/build/html
```

which serves the docs website at [http://127.0.0.1:8000](http://127.0.0.1:8000).
