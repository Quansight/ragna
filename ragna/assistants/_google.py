from typing import AsyncIterator

from ragna._compat import anext
from ragna.core import PackageRequirement, Requirement, Source

from ._api import ApiAssistant


# ijson does not support reading from an (async) iterator, but only from file-like
# objects, i.e. https://docs.python.org/3/tutorial/inputoutput.html#methods-of-file-objects.
# See https://github.com/ICRAR/ijson/issues/44 for details.
# ijson actually doesn't care about most of the file interface and only requires the
# read() method to be present.
class AsyncIteratorReader:
    def __init__(self, ait: AsyncIterator[bytes]) -> None:
        self._ait = ait

    async def read(self, n: int) -> bytes:
        # n is usually used to indicate how many bytes to read, but since we want to
        # return a chunk as soon as it is available, we ignore the value of n. The only
        # exception is n == 0, which is used by ijson to probe the return type and
        # set up decoding.
        if n == 0:
            return b""
        return await anext(self._ait, b"")  # type: ignore[call-arg]


class GoogleApiAssistant(ApiAssistant):
    _API_KEY_ENV_VAR = "GOOGLE_API_KEY"
    _MODEL: str
    _CONTEXT_SIZE: int

    @classmethod
    def requirements(cls) -> list[Requirement]:
        return [
            *super().requirements(),
            PackageRequirement("ijson"),
        ]

    @classmethod
    def display_name(cls) -> str:
        return f"Google/{cls._MODEL}"

    @property
    def max_input_size(self) -> int:
        return self._CONTEXT_SIZE

    def _instructize_prompt(self, prompt: str, sources: list[Source]) -> str:
        # https://ai.google.dev/docs/prompt_best_practices#add-contextual-information
        return "\n".join(
            [
                "Answer the prompt using only the pieces of context below.",
                "If you don't know the answer, just say so. Don't try to make up additional context.",
                f"Prompt: {prompt}",
                *[f"\n{source.content}" for source in sources],
            ]
        )

    async def _call_api(
        self, prompt: str, sources: list[Source], *, max_new_tokens: int
    ) -> AsyncIterator[str]:
        import ijson

        async with self._client.stream(
            "POST",
            f"https://generativelanguage.googleapis.com/v1beta/models/{self._MODEL}:streamGenerateContent",
            params={"key": self._api_key},
            headers={"Content-Type": "application/json"},
            json={
                "contents": [
                    {"parts": [{"text": self._instructize_prompt(prompt, sources)}]}
                ],
                # https://ai.google.dev/docs/safety_setting_gemini
                "safetySettings": [
                    {"category": f"HARM_CATEGORY_{category}", "threshold": "BLOCK_NONE"}
                    for category in [
                        "HARASSMENT",
                        "HATE_SPEECH",
                        "SEXUALLY_EXPLICIT",
                        "DANGEROUS_CONTENT",
                    ]
                ],
                # https://ai.google.dev/tutorials/rest_quickstart#configuration
                "generationConfig": {
                    "temperature": 0.0,
                    "maxOutputTokens": max_new_tokens,
                },
            },
        ) as response:
            await self._assert_api_call_is_success(response)

            async for chunk in ijson.items(
                AsyncIteratorReader(response.aiter_bytes(1024)),
                "item.candidates.item.content.parts.item.text",
            ):
                yield chunk


class GeminiPro(GoogleApiAssistant):
    """[Google Gemini Pro](https://ai.google.dev/models/gemini)

    !!! info "Required environment variables"

        - `GOOGLE_API_KEY`

    !!! info "Required packages"

        - `ijson`
    """

    _MODEL = "gemini-pro"
    _CONTEXT_SIZE = 30_720


class GeminiUltra(GoogleApiAssistant):
    """[Google Gemini Ultra](https://ai.google.dev/models/gemini)

    !!! info "Required environment variables"

        - `GOOGLE_API_KEY`

    !!! info "Required packages"

        - `ijson`
    """

    _MODEL = "gemini-ultra"
    _CONTEXT_SIZE = 30_720
