"""
# Python API

"""

# %%
# Let's look at the config

from ragna import Config

config = Config.demo()
print(config)

# %%
# Let's create a document

from pathlib import Path

document_path = Path.cwd() / "ragna.txt"
with open(document_path, "w") as file:
    file.write("Ragna is awesome!\n")

# %%
# Let's ask a question
import asyncio

from ragna.assistants import RagnaDemoAssistant

from ragna.core import Rag
from ragna.source_storages import RagnaDemoSourceStorage


async def answer():
    rag = Rag(config)
    chat = rag.chat(
        documents=[document_path],
        source_storage=RagnaDemoSourceStorage,
        assistant=RagnaDemoAssistant,
    )
    async with chat:
        return await chat.answer("?")


answer = asyncio.run(answer())
print(answer)
