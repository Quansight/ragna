from typing import AsyncIterator, cast

from ragna.core import RagnaException, Source

from ._api import ApiAssistant


class Ai21LabsAssistant(ApiAssistant):
    _API_KEY_ENV_VAR = "AI21_API_KEY"
    _MODEL_TYPE: str
    _CONTEXT_SIZE: int = 8_192

    @classmethod
    def display_name(cls) -> str:
        return f"AI21Labs/jurassic-2-{cls._MODEL_TYPE}"

    @property
    def max_input_size(self) -> int:
        return self._CONTEXT_SIZE

    def _make_system_content(self, sources: list[Source]) -> str:
        instruction = (
            "You are a helpful assistant that answers user questions given the context below. "
            "If you don't know the answer, just say so. Don't try to make up an answer. "
            "Only use the sources below to generate the answer."
        )
        return instruction + "\n\n".join(source.content for source in sources)

    async def _call_api(
        self, prompt: str, sources: list[Source], *, max_new_tokens: int
    ) -> AsyncIterator[str]:
        response = await self._client.post(
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
        )

        if response.is_error:
            raise RagnaException(
                status_code=response.status_code, response=response.json()
            )

        yield cast(str, response.json()["outputs"][0]["text"])


class Jurassic2Mid(Ai21LabsAssistant):
    """[AI21 Labs Jurassic-2 Mid](https://docs.ai21.com/docs/jurassic-2-models)

    !!! info "Required environment variables"

        - `AI21LABS_API_KEY`
    """

    _MODEL_TYPE = "mid"


class Jurassic2Ultra(Ai21LabsAssistant):
    """[AI21 Labs Jurassic-2 Ultra](https://docs.ai21.com/docs/jurassic-2-models)

    !!! info "Required environment variables"

        - `AI21LABS_API_KEY`
    """

    _MODEL_TYPE = "ultra"
