import json
from typing import AsyncIterator, cast
from xml.etree import ElementTree

from ragna.core import PackageRequirement, RagnaException, Requirement, Source

from ._api import ApiAssistant


class AnthropicApiAssistant(ApiAssistant):
    _API_KEY_ENV_VAR = "ANTHROPIC_API_KEY"
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
        plural = len(sources) > 1
        instruction = (
            f"I'm going to give you {len(sources)} document{'s' if plural else ''}. "
            f"Read the document{'s' if plural else ''} carefully because I'm going to ask you a question about {'them' if plural else 'it'}. "
            f"If you can't answer the question with just the given document{'s' if plural else ''}, just say so. "
            "Don't try to make up an answer."
        )
        # See https://docs.anthropic.com/claude/docs/long-context-window-tips#structuring-long-documents
        documents = ElementTree.Element("documents")
        for idx, source in enumerate(sources, start=1):
            doc_elmnt = ElementTree.SubElement(
                documents,
                "document",
                attrib={"index": str(idx)},
            )
            ElementTree.SubElement(doc_elmnt, "id").text = source.id
            ElementTree.SubElement(doc_elmnt, "document_content").text = source.content
        return instruction + ElementTree.tostring(documents, encoding="unicode")

    async def _call_api(
        self, prompt: str, sources: list[Source], *, max_new_tokens: int
    ) -> AsyncIterator[str]:
        import httpx_sse

        # See https://docs.anthropic.com/claude/reference/messages_post
        # See https://docs.anthropic.com/claude/reference/streaming
        async with httpx_sse.aconnect_sse(
            self._client,
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
                "system": self._instructize_system_prompt(sources),
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_new_tokens,
                "temperature": 0.0,
                "stream": True,
            },
        ) as event_source:
            await self._assert_api_call_is_success(event_source.response)

            async for sse in event_source.aiter_sse():
                data = json.loads(sse.data)
                # See https://docs.anthropic.com/claude/reference/messages-streaming#raw-http-stream-response
                if "error" in data:
                    raise RagnaException(data["error"].pop("message"), **data["error"])
                elif data["type"] == "message_stop":
                    break
                elif data["type"] != "content_block_delta":
                    continue

                yield cast(str, data["delta"].pop("text"))


class ClaudeOpus(AnthropicApiAssistant):
    """[Claude 3 Opus](https://docs.anthropic.com/claude/docs/models-overview)

    !!! info "Required environment variables"

        - `ANTHROPIC_API_KEY`

    !!! info "Required packages"

        - `httpx_sse`
    """

    _MODEL = "claude-3-opus-20240229"


class ClaudeSonnet(AnthropicApiAssistant):
    """[Claude 3 Sonnet](https://docs.anthropic.com/claude/docs/models-overview)

    !!! info "Required environment variables"

        - `ANTHROPIC_API_KEY`

    !!! info "Required packages"

        - `httpx_sse`
    """

    _MODEL = "claude-3-sonnet-20240229"


class ClaudeHaiku(AnthropicApiAssistant):
    """[Claude 3 Haiku](https://docs.anthropic.com/claude/docs/models-overview)

    !!! info "Required environment variables"

        - `ANTHROPIC_API_KEY`

    !!! info "Required packages"

        - `httpx_sse`
    """

    _MODEL = "claude-3-haiku-20240307"
