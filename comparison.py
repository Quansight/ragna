import asyncio
import itertools
from pprint import pprint

from tqdm import tqdm
from tqdm.asyncio import tqdm_asyncio

from ragna import Rag, assistants, source_storages

SOURCE_STORAGES = [
    source_storages.Chroma,
    source_storages.LanceDB,
]
ASSISTANTS = [
    assistants.Gpt35Turbo16k,
    assistants.Gpt4,
]


async def main():
    rag = Rag()

    # Pre-load all components to enable a fair comparison
    for component in itertools.chain(SOURCE_STORAGES, ASSISTANTS):
        rag._load_component(component)

    document = "ragna.txt"
    with open(document, "w") as file:
        file.write("Ragna is an open source RAG orchestration framework\n")

    prompt = "What is Ragna?"

    experiments = make_experiments(rag=rag, prompt=prompt, document=document)
    pprint(
        {name: await experiment for name, experiment in tqdm(experiments.items())},
        sort_dicts=False,
    )

    experiments = make_experiments(rag=rag, prompt=prompt, document=document)
    pprint(
        dict(zip(experiments.keys(), await tqdm_asyncio.gather(*experiments.values()))),
        sort_dicts=False,
    )


def make_experiments(*, rag, document, prompt):
    return {
        f"{source_storage.display_name()} / {assistant.display_name()}": answer(
            rag=rag,
            documents=[document],
            source_storage=source_storage,
            assistant=assistant,
            prompt=prompt,
        )
        for source_storage, assistant in itertools.product(SOURCE_STORAGES, ASSISTANTS)
    }


async def answer(*, rag, documents, source_storage, assistant, prompt):
    chat = rag.chat(
        documents=documents, source_storage=source_storage, assistant=assistant
    )
    await chat.prepare()
    return (await chat.answer(prompt)).content


if __name__ == "__main__":
    asyncio.run(main())
