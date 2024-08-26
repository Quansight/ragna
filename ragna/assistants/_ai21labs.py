from typing import AsyncIterator, cast

from ragna.core import Message, Source

from ._http_api import HttpApiAssistant


class Ai21LabsAssistant(HttpApiAssistant):
    _API_KEY_ENV_VAR = "AI21_API_KEY"
    _STREAMING_PROTOCOL = None
    _MODEL_TYPE: str

    @classmethod
    def display_name(cls) -> str:
        return f"AI21Labs/jurassic-2-{cls._MODEL_TYPE}"

    def _make_system_content(self, sources: list[Source]) -> str:
        instruction = (
            "You are a helpful assistant that answers user questions given the context below. "
            "If you don't know the answer, just say so. Don't try to make up an answer. "
            "Only use the sources below to generate the answer."
        )
        return instruction + "\n\n".join(source.content for source in sources)

    async def answer(
        self, messages: list[Message], *, max_new_tokens: int = 256
    ) -> AsyncIterator[str]:
        # See https://docs.ai21.com/reference/j2-chat-api#chat-api-parameters
        # See https://docs.ai21.com/reference/j2-complete-api-ref#api-parameters
        # See https://docs.ai21.com/reference/j2-chat-api#understanding-the-response
        prompt, sources = (message := messages[-1]).content, message.sources
        async with self._call_api(
            "POST",
            f"https://api.ai21.com/studio/v1/j2-{self._MODEL_TYPE}/chat",
            headers={
                "accept": "application/json",
                "content-type": "application/json",
                "authorization": f"Bearer {self._api_key}",
            },
            json={
                "numResults": 1,
                "temperature": 0.0,
                "maxTokens": max_new_tokens,
                "messages": [
                    {
                        "text": prompt,
                        "role": "user",
                    }
                ],
                "system": self._make_system_content(sources),
            },
        ) as stream:
            async for data in stream:
                yield cast(str, data["outputs"][0]["text"])


# The Jurassic2Mid assistant receives a 500 internal service error from the remote
# server. See https://github.com/Quansight/ragna/pull/303
# TODO: Reinstate when the remote server is fixed
# class Jurassic2Mid(Ai21LabsAssistant):
#     """[AI21 Labs Jurassic-2 Mid](https://docs.ai21.com/docs/jurassic-2-models)
#
#     !!! info "Required environment variables"
#
#         - `AI21_API_KEY`
#     """
#
#     _MODEL_TYPE = "mid"


class Jurassic2Ultra(Ai21LabsAssistant):
    """[AI21 Labs Jurassic-2 Ultra](https://docs.ai21.com/docs/jurassic-2-models)

    !!! info "Required environment variables"

        - `AI21_API_KEY`
    """

    _MODEL_TYPE = "ultra"
