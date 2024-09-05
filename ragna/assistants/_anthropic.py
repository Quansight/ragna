from typing import AsyncIterator, Union, cast

from ragna.core import (
    Message,
    MessageRole,
    PackageRequirement,
    RagnaException,
    Requirement,
    Source,
)

from ._http_api import HttpApiAssistant, HttpStreamingProtocol


class AnthropicAssistant(HttpApiAssistant):
    _API_KEY_ENV_VAR = "ANTHROPIC_API_KEY"
    _STREAMING_PROTOCOL = HttpStreamingProtocol.SSE
    _MODEL: str

    @classmethod
    def _extra_requirements(cls) -> list[Requirement]:
        return [PackageRequirement("httpx_sse")]

    @classmethod
    def display_name(cls) -> str:
        return f"Anthropic/{cls._MODEL}"

    def _instructize_system_prompt(self, sources: list[Source]) -> str:
        # See https://docs.anthropic.com/claude/docs/system-prompts
        # See https://docs.anthropic.com/claude/docs/long-context-window-tips#tips-for-document-qa
        instruction = (
            f"I'm going to give you {len(sources)} document(s). "
            f"Read the document(s) carefully because I'm going to ask you a question about them. "
            f"If you can't answer the question with just the given document(s), just say so. "
            "Don't try to make up an answer.\n\n"
        )
        # See https://docs.anthropic.com/claude/docs/long-context-window-tips#structuring-long-documents

        return (
            instruction
            + "<documents>"
            + "\n".join(f"<document>{source.content}</document>" for source in sources)
            + "</documents>"
        )

    def _render_prompt(self, prompt: Union[str, list[Message]]) -> list[dict]:
        """
        Ingests ragna messages-list or a single string prompt and converts to assistant-appropriate format.

        Returns:
            ordered list of dicts with 'content' and 'role' keys
        """
        if isinstance(prompt, str):
            messages = [Message(content=prompt, role=MessageRole.USER)]
        else:
            messages = prompt

        messages = [
            {"content": i["content"], "role": i["role"]}
            for i in messages
            if i["role"] != "system"
        ]
        return messages

    async def generate(
        self,
        prompt: Union[str, list[Message]],
        *,
        system_prompt: str = "You are a helpful assistant.",
        max_new_tokens: int = 256,
    ) -> AsyncIterator[str]:
        """
        Primary method for calling assistant inference, either as a one-off request from anywhere in ragna, or as part of self.answer()
        This method should be called for tasks like pre-processing, agentic tasks, or any other user-defined calls.

        Args:
            prompt: Either a single prompt string or a list of ragna messages
            system_prompt: System prompt string
            max_new_tokens: Max number of completion tokens (default 256)

        Returns:
            async streamed inference response string chunks
        """
        # See https://docs.anthropic.com/claude/reference/messages_post
        # See https://docs.anthropic.com/claude/reference/streaming

        async with self._call_api(
            "POST",
            "https://api.anthropic.com/v1/messages",
            headers={
                "accept": "application/json",
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
                "x-api-key": self._api_key,
            },
            json={
                "model": self._MODEL,
                "system": system_prompt,
                "messages": self._render_prompt(prompt),
                "max_tokens": max_new_tokens,
                "temperature": 0.0,
                "stream": True,
            },
        ) as stream:
            async for data in stream:
                # See https://docs.anthropic.com/claude/reference/messages-streaming#raw-http-stream-response
                if "error" in data:
                    raise RagnaException(data["error"].pop("message"), **data["error"])
                elif data["type"] == "message_stop":
                    break
                elif data["type"] != "content_block_delta":
                    continue

                yield cast(str, data["delta"].pop("text"))

    async def answer(
        self, messages: list[Message], *, max_new_tokens: int = 256
    ) -> AsyncIterator[str]:
        prompt, sources = (message := messages[-1]).content, message.sources
        system_prompt = self._instructize_system_prompt(sources)
        yield self.generate(
            prompt=prompt, system_prompt=system_prompt, max_new_tokens=max_new_tokens
        )


class ClaudeOpus(AnthropicAssistant):
    """[Claude 3 Opus](https://docs.anthropic.com/claude/docs/models-overview)

    !!! info "Required environment variables"

        - `ANTHROPIC_API_KEY`

    !!! info "Required packages"

        - `httpx_sse`
    """

    _MODEL = "claude-3-opus-20240229"


class ClaudeSonnet(AnthropicAssistant):
    """[Claude 3 Sonnet](https://docs.anthropic.com/claude/docs/models-overview)

    !!! info "Required environment variables"

        - `ANTHROPIC_API_KEY`

    !!! info "Required packages"

        - `httpx_sse`
    """

    _MODEL = "claude-3-sonnet-20240229"


class ClaudeHaiku(AnthropicAssistant):
    """[Claude 3 Haiku](https://docs.anthropic.com/claude/docs/models-overview)

    !!! info "Required environment variables"

        - `ANTHROPIC_API_KEY`

    !!! info "Required packages"

        - `httpx_sse`
    """

    _MODEL = "claude-3-haiku-20240307"
