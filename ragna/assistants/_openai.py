import abc
from functools import cached_property
from typing import (
    Any,
    AsyncContextManager,
    AsyncIterator,
    Optional,
    Union,
    cast,
)

from ragna.core import Message, MessageRole, Source

from ._http_api import HttpApiAssistant, HttpStreamingProtocol


class OpenaiLikeHttpApiAssistant(HttpApiAssistant):
    _MODEL: Optional[str]

    @property
    @abc.abstractmethod
    def _url(self) -> str: ...

    def _make_system_content(self, sources: list[Source]) -> str:
        # See https://github.com/openai/openai-cookbook/blob/main/examples/How_to_format_inputs_to_ChatGPT_models.ipynb
        instruction = (
            "You are an helpful assistants that answers user questions given the context below. "
            "If you don't know the answer, just say so. Don't try to make up an answer. "
            "Only use the sources below to generate the answer."
        )
        return instruction + "\n\n".join(source.content for source in sources)

    def _render_prompt(
        self, prompt: Union[str, list[Message]], system_prompt: str
    ) -> list[dict]:
        """
        Ingests ragna messages-list or a single string prompt and converts to assistant-appropriate format.

        Returns:
            ordered list of dicts with 'content' and 'role' keys
        """
        if isinstance(prompt, str):
            messages = [Message(content=prompt, role=MessageRole.USER)]
        else:
            messages = prompt
        system_message = [{"role": "system", "content": system_prompt}]
        messages = [
            {"role": i["role"], "content": i["content"]}
            for i in prompt
            if i["role"] != "system"
        ]
        return system_message.extend(messages)

    async def generate(
        self,
        prompt: Union[str, list[Message]],
        *,
        system_prompt: str = "You are a helpful assistant.",
        max_new_tokens: int = 256,
    ) -> AsyncContextManager[AsyncIterator[dict[str, Any]]]:
        """
        Primary method for calling assistant inference, either as a one-off request from anywhere in ragna, or as part of self.answer()
        This method should be called for tasks like pre-processing, agentic tasks, or any other user-defined calls.

        Args:
            prompt: Either a single prompt string or a list of ragna messages
            system_prompt: System prompt string
            max_new_tokens: Max number of completion tokens (default 256)

        Returns:
            yield call to self._call_api with formatted headers and json
        """
        messages = self._render_prompt(prompt, system_prompt)

        headers = {
            "Content-Type": "application/json",
        }
        if self._api_key is not None:
            headers["Authorization"] = f"Bearer {self._api_key}"

        json_ = {
            "messages": messages,
            "temperature": 0.0,
            "max_tokens": max_new_tokens,
            "stream": True,
        }
        if self._MODEL is not None:
            json_["model"] = self._MODEL

        yield self._call_api("POST", self._url, headers=headers, json=json_)

    def _call_openai_api(
        self, prompt: str, sources: list[Source], *, max_new_tokens: int = 256
    ) -> AsyncContextManager[AsyncIterator[dict[str, Any]]]:
        system_prompt = self._make_system_content(sources)

        yield self.generate(
            prompt=prompt, system_prompt=system_prompt, max_new_tokens=max_new_tokens
        )

    async def answer(
        self, messages: list[Message], *, max_new_tokens: int = 256
    ) -> AsyncIterator[str]:
        prompt, sources = (message := messages[-1]).content, message.sources
        async with self._call_openai_api(
            prompt, sources, max_new_tokens=max_new_tokens
        ) as stream:
            async for data in stream:
                choice = data["choices"][0]
                if choice["finish_reason"] is not None:
                    break
                yield cast(str, choice["delta"]["content"])


class OpenaiAssistant(OpenaiLikeHttpApiAssistant):
    _API_KEY_ENV_VAR = "OPENAI_API_KEY"
    _STREAMING_PROTOCOL = HttpStreamingProtocol.SSE

    @classmethod
    def display_name(cls) -> str:
        return f"OpenAI/{cls._MODEL}"

    @cached_property
    def _url(self) -> str:
        return "https://api.openai.com/v1/chat/completions"


class Gpt35Turbo16k(OpenaiAssistant):
    """[OpenAI GPT-3.5](https://platform.openai.com/docs/models/gpt-3-5)

    !!! info "Required environment variables"

        - `OPENAI_API_KEY`

    !!! info "Required packages"

        - `httpx_sse`
    """

    _MODEL = "gpt-3.5-turbo-16k"


class Gpt4(OpenaiAssistant):
    """[OpenAI GPT-4](https://platform.openai.com/docs/models/gpt-4)

    !!! info "Required environment variables"

        - `OPENAI_API_KEY`

    !!! info "Required packages"

        - `httpx_sse`
    """

    _MODEL = "gpt-4"
