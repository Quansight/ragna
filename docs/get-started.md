# Get started

## Installation

<!-- TODO -->


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
