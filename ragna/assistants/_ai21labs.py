from typing import Any, AsyncIterator, Union, cast

from ragna.core import Message, MessageRole, Source

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

    def _render_prompt(self, prompt: Union[str, list[Message]]) -> Union[str, list]:
        """
        Ingests ragna messages-list or a single string prompt and converts to assistant-appropriate format.

        Returns:
            ordered list of dicts with 'text' and 'role' keys
        """
        if isinstance(prompt, str):
            messages = [Message(content=prompt, role=MessageRole.USER)]
        else:
            messages = prompt
        return [
            {"role": message.role.value, "content": message.content}
            for message in messages
            if message.role is not MessageRole.SYSTEM
        ]

    async def generate(
        self,
        prompt: Union[str, list[Message]],
        *,
        system_prompt: str = "You are a helpful assistant.",
        max_new_tokens: int = 256,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Primary method for calling assistant inference, either as a one-off request from anywhere in ragna, or as part of self.answer()
        This method should be called for tasks like pre-processing, agentic tasks, or any other user-defined calls.

        Args:
            prompt: Either a single prompt string or a list of ragna messages
            system_prompt: System prompt string
            max_new_tokens: Max number of completion tokens (default 256_

        Returns:
            async streamed inference response string chunks
        """
        # See https://docs.ai21.com/reference/j2-chat-api#chat-api-parameters
        # See https://docs.ai21.com/reference/j2-complete-api-ref#api-parameters
        # See https://docs.ai21.com/reference/j2-chat-api#understanding-the-response

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
                "messages": self._render_prompt(prompt),
                "system": system_prompt,
            },
        ) as stream:
            async for data in stream:
                yield data

    async def answer(
        self, messages: list[Message], *, max_new_tokens: int = 256
    ) -> AsyncIterator[str]:
        message = messages[-1]
        async for data in self.generate(
            [message],
            system_prompt=self._make_system_content(message.sources),
            max_new_tokens=max_new_tokens,
        ):
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
