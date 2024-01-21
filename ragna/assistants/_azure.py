from typing import cast
import os

from ragna.core import RagnaException, Source, EnvVarRequirement, Requirement

from ._api import ApiAssistant


class AzureApiAssistant(ApiAssistant):
    _API_KEY_ENV_VAR = "AZURE_OPENAI_API_KEY"
    _MODEL: str
    _CONTEXT_SIZE: int

    @classmethod
    def requirements(cls) -> list[Requirement]:
        return [
            EnvVarRequirement(cls._API_KEY_ENV_VAR),
            EnvVarRequirement("AZURE_OPENAI_API_BASE"),
            EnvVarRequirement("AZURE_OPENAI_API_VERSION"),
        ]

    @classmethod
    def display_name(cls) -> str:
        return f"AzureOpenAI/{cls._MODEL}"

    @property
    def max_input_size(self) -> int:
        return self._CONTEXT_SIZE

    def _make_system_content(self, sources: list[Source]) -> str:
        instruction = (
            "You are an helpful assistants that answers user questions given the context below. "
            "If you don't know the answer, just say so. Don't try to make up an answer. "
            "Only use the sources below to generate the answer."
        )
        return instruction + "\n\n".join(source.content for source in sources)

    async def _call_api(
        self, prompt: str, sources: list[Source], *, max_new_tokens: int
    ) -> str:
        base=os.environ["AZURE_OPENAI_API_BASE"]
        version=os.environ["AZURE_OPENAI_API_VERSION"]
        response = await self._client.post(
            f"{base}/openai/deployments/{self._MODEL}/completions?api_version={version}",
            headers={
                "Content-Type": "application/json",
                "api-key": self._api_key,
            },
            json={
                "messages": [
                    {
                        "role": "system",
                        "content": self._make_system_content(sources),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                "model": self._MODEL,
                "temperature": 0.0,
                "max_tokens": max_new_tokens,
            },
        )
        if response.is_error:
            raise RagnaException(
                status_code=response.status_code, response=response.json()
            )
        return cast(str, response.json()["choices"][0]["message"]["content"])


class AzureGpt35Turbo(AzureApiAssistant):
    """[OpenAI GPT-3.5](https://platform.openai.com/docs/models/gpt-3-5)

    !!! info "Required environment variables"

        - `AZURE_OPENAI_API_KEY`
        - `AZURE_OPENAI_API_BASE`
        - `AZURE_OPENAI_API_VERSION`
    """

    _MODEL = "gpt35-turbo"
    _CONTEXT_SIZE = 16_384


AzureGpt35Turbo.__doc__ = "OOPS"


class AzureGpt4(AzureApiAssistant):
    """[OpenAI GPT-4](https://platform.openai.com/docs/models/gpt-4)

    !!! info "Required environment variables"

        - `AZURE_OPENAI_API_KEY`
        - `AZURE_OPENAI_API_BASE`
        - `AZURE_OPENAI_API_VERSION`
    """

    _MODEL = "gpt-4"
    _CONTEXT_SIZE = 8_192
