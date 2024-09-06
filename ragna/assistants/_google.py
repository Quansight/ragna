from typing import Any, AsyncIterator, Union

from ragna.core import Message, MessageRole, Source

from ._http_api import HttpApiAssistant, HttpStreamingProtocol


class GoogleAssistant(HttpApiAssistant):
    _API_KEY_ENV_VAR = "GOOGLE_API_KEY"
    _STREAMING_PROTOCOL = HttpStreamingProtocol.JSON
    _MODEL: str

    @classmethod
    def display_name(cls) -> str:
        return f"Google/{cls._MODEL}"

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

    def _render_prompt(self, prompt: Union[str, list[Message]]) -> list[dict]:
        if isinstance(prompt, str):
            messages = [Message(content=prompt, role=MessageRole.USER)]
        else:
            messages = prompt
        return [
            {"parts": [{"text": message.content}]}
            for message in messages
            if message.role is not MessageRole.SYSTEM
        ]

    async def generate(
        self, prompt: Union[str, list[Message]], *, max_new_tokens: int = 256
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Primary method for calling assistant inference, either as a one-off request from anywhere in ragna, or as part of self.answer()
        This method should be called for tasks like pre-processing, agentic tasks, or any other user-defined calls.

        Args:
            prompt: Either a single prompt string or a list of ragna messages
            max_new_tokens: Max number of completion tokens (default 256)

        Returns:
            async streamed inference response string chunks
        """
        # See https://ai.google.dev/api/generate-content#v1beta.models.streamGenerateContent
        async with self._call_api(
            "POST",
            f"https://generativelanguage.googleapis.com/v1beta/models/{self._MODEL}:streamGenerateContent",
            params={"key": self._api_key},
            headers={"Content-Type": "application/json"},
            json={
                "contents": self._render_prompt(prompt),
                # https://ai.google.dev/docs/safety_setting_gemini
                "safetySettings": [
                    {
                        "category": f"HARM_CATEGORY_{category}",
                        "threshold": "BLOCK_NONE",
                    }
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
            parse_kwargs=dict(item="item"),
        ) as stream:
            async for data in stream:
                yield data

    async def answer(
        self, messages: list[Message], *, max_new_tokens: int = 256
    ) -> AsyncIterator[str]:
        message = messages[-1]
        async for data in self.generate(
            self._instructize_prompt(message.content, message.sources),
            max_new_tokens=max_new_tokens,
        ):
            yield data["candidates"][0]["content"]["parts"][0]["text"]


class GeminiPro(GoogleAssistant):
    """[Google Gemini Pro](https://ai.google.dev/models/gemini)

    !!! info "Required environment variables"

        - `GOOGLE_API_KEY`

    !!! info "Required packages"

        - `ijson`
    """

    _MODEL = "gemini-pro"


class GeminiUltra(GoogleAssistant):
    """[Google Gemini Ultra](https://ai.google.dev/models/gemini)

    !!! info "Required environment variables"

        - `GOOGLE_API_KEY`

    !!! info "Required packages"

        - `ijson`
    """

    _MODEL = "gemini-ultra"
