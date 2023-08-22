from ragna.extensions import hookimpl, Source

from ._llm_api import LlmApi


class MosaicmlLlmApi(LlmApi):
    _API_KEY_ENV_VAR = "MOSAICML_API_KEY"
    _MODEL: str
    _CONTEXT_SIZE: int

    @classmethod
    def display_name(cls):
        return f"Mosaic/{cls._MODEL}"

    @property
    def context_size(self) -> int:
        return self._CONTEXT_SIZE

    def _instructize_prompt(self, prompt: str, sources: list[Source]) -> str:
        # See https://huggingface.co/mosaicml/mpt-7b-instruct#formatting
        instruction = (
            "Use the following pieces of context to answer the question at the end. "
            "If you don't know the answer, just say so. Don't try to make up an answer.\n"
        )
        instruction += "\n\n".join(source.text for source in sources)
        return f"{instruction}### Instruction: {prompt}\n### Response:"

    def _call_api(self, prompt: str, sources: list[Source], *, max_new_tokens: int):
        import requests

        instruction = self._instructize_prompt(prompt, sources)
        # https://docs.mosaicml.com/en/latest/inference.html#text-completion-requests
        response = requests.post(
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
        if not response.ok:
            self._failed_api_call(
                status_code=response.status_code, response=response.json()
            )
        return response.json()["outputs"][0].replace(instruction, "").strip()


class MosaicmlMpt7bInstructLlm(MosaicmlLlmApi):
    # I couldn't find anything official
    # https://huggingface.co/mosaicml/mpt-7b-instruct#model-description
    _MODEL = "mpt-7b-instruct"
    _CONTEXT_SIZE = 2048


@hookimpl(specname="ragna_llm")
def mosaicml_mpt_7b_instruct_llm():
    return MosaicmlMpt7bInstructLlm


class MosaicmlMpt30bInstructLlm(MosaicmlLlmApi):
    # https://docs.mosaicml.com/en/latest/inference.html#text-completion-models
    _MODEL = "mpt-30b-instruct"
    _CONTEXT_SIZE = 8_192


@hookimpl(specname="ragna_llm")
def mosaicml_mpt_30b_instruct_llm():
    return MosaicmlMpt30bInstructLlm
