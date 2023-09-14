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
from ragna.llm import RagnaDemoLlm
from ragna.source_storage import RagnaDemoSourceStorage


async def main():
    rag = Rag()

    path = "ragna.txt"
    with open(path, "w") as file:
        file.write("Ragna is an OSS RAG app with Python and REST API.\n")

    chat = await rag.start_new_chat(
        documents=[path],
        source_storage=RagnaDemoSourceStorage,
        llm=RagnaDemoLlm,
    )

    print(await chat.answer("What is Ragna?"))


# This is only needed when running inside a regular editor.
# When running inside a notebook, the code inside the main function can be run directly
if __name__ == "__main__":
    asyncio.run(main())
```
