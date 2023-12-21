"""
# Python API

"""

# %%
# Let's create a document

from pathlib import Path

document_path = Path.cwd() / "ragna.txt"
with open(document_path, "w") as file:
    file.write("Ragna is awesome!\n")

# %%
# Let's ask a question
#
# !!! note
#
#     We can write default markdown here!

from ragna import Rag, assistants, source_storages

rag = Rag()
async with rag.chat(
    documents=[document_path],
    source_storage=source_storages.RagnaDemoSourceStorage,
    assistant=assistants.RagnaDemoAssistant,
) as chat:
    answer = await chat.answer("?")
print(answer)
