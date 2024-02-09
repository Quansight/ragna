"""
# Streaming


"""
from typing import Iterator

# %%

from ragna import Rag, assistants, source_storages

chat = Rag().chat(
    documents=["ragna.txt"],
    source_storage=source_storages.RagnaDemoSourceStorage,
    assistant=assistants.RagnaDemoAssistant,
)
await chat.prepare()

# %%

answer = await chat.answer("What is Ragna?")

print(answer)

# %%
# Looks like a string, but is actually a Message object

print(type(answer))
print(type(answer.content))

# %%
# If we want to stream, we need to pass `stream=True`

answer = await chat.answer("What is Ragna?", stream=True)
try:
    answer.content
except RuntimeError as error:
    print(error)

# %%
# we could read() the message, but that is what happens when we don't pass stream=True
# so let's iterate

chunks = [chunk async for chunk in answer]
print(chunks)
print(len(chunks))

# %%
# Well, that was not not really successful. We ended up with a single chunk that
# contained everything. This happens because `RagnaDemoAssistant` doesn't support
# streaming (and it really doesn't due to the instant response).
# TODO: include list of all builtin assistants that support streaming
# So, for testing, let's
# write an assistant that can stream
# TODO: include link to tutorial on how to write a custom assistant

from ragna.core import Assistant
import random
import time


class DemoStreamingAssistant(Assistant):
    @property
    def max_input_size(self) -> int:
        return 0

    def answer(self, prompt, sources) -> Iterator[str]:
        for chunk in f"Your prompt was '{prompt}'.".split():
            # Simulate a small delay between the generation of each chunk
            time.sleep(random.random())
            yield chunk


chat = Rag().chat(
    documents=["ragna.txt"],
    source_storage=source_storages.RagnaDemoSourceStorage,
    assistant=DemoStreamingAssistant,
)
await chat.prepare()

# %%

answer = await chat.answer("What is Ragna?", stream=True)

chunks = [chunk async for chunk in answer]
print(chunks)
print(len(chunks))

# %%

from helpers import foo

foo()
