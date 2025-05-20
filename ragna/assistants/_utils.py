import itertools

from ragna.core import Message, Source


def unpack_prompts_and_sources(
    messages: list[Message],
) -> tuple[list[str], list[Source]]:
    return [message.content for message in messages if message.role != "system"], list(
        set(
            itertools.chain.from_iterable(
                message.sources for message in messages if message.role != "system"
            )
        )
    )
