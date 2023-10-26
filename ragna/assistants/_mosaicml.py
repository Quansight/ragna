from typing import cast

from ragna.core import RagnaException, Source

from ._api import ApiAssistant


class MosaicmlApiAssistant(ApiAssistant):
    _API_KEY_ENV_VAR = "MOSAICML_API_KEY"
    _MODEL: str
    _CONTEXT_SIZE: int

    @classmethod
    def display_name(cls) -> str:
        return f"MosaicML/{cls._MODEL}"

    @property
    def max_input_size(self) -> int:
        return self._CONTEXT_SIZE

    def _instructize_prompt(self, prompt: str, sources: list[Source]) -> str:
        # See https://huggingface.co/mosaicml/mpt-7b-instruct#formatting
        instruction = (
            "Use the following pieces of context to answer the question at the end. "
            "If you don't know the answer, just say so. Don't try to make up an answer.\n"
        )
        instruction += "\n\n".join(source.content for source in sources)
        return f"{instruction}### Instruction: {prompt}\n### Response:"

    def _call_api(
        self, prompt: str, sources: list[Source], *, max_new_tokens: int
    ) -> str:
        instruction = self._instructize_prompt(prompt, sources)
        # https://docs.mosaicml.com/en/latest/inference.html#text-completion-requests
        response = self._client.post(
            f"https://models.hosted-on.mosaicml.hosting/{self._MODEL}/v1/predict",
            headers={
                "Authorization": f"{self._api_key}",
                "Content-Type": "application/json",
            },
            json={
                "inputs": [instruction],
                "parameters": {"temperature": 0.0, "max_new_tokens": max_new_tokens},
            },
        )
        if response.is_error:
            raise RagnaException(
                status_code=response.status_code, response=response.json()
            )
        return cast(str, response.json()["outputs"][0]).replace(instruction, "").strip()


class Mpt7bInstruct(MosaicmlApiAssistant):
    """[MPT-7B-Instruct](https://docs.mosaicml.com/en/latest/inference.html#text-completion-models)

    !!! info "Required environment variables"

        - `MOSAICML_API_KEY`
    """

    # https://huggingface.co/mosaicml/mpt-7b-instruct#model-description
    _MODEL = "mpt-7b-instruct"
    _CONTEXT_SIZE = 2048


class Mpt30bInstruct(MosaicmlApiAssistant):
    """[MPT-30B-Instruct](https://docs.mosaicml.com/en/latest/inference.html#text-completion-models)

    !!! info "Required environment variables"

        - `MOSAICML_API_KEY`
    """

    # https://huggingface.co/mosaicml/mpt-30b-instruct#model-description
    _MODEL = "mpt-30b-instruct"
    _CONTEXT_SIZE = 8_192
