from typing import Union, cast

from exllamav2 import (
    ExLlamaV2,
    ExLlamaV2Cache_Q4,
    ExLlamaV2Config,
    ExLlamaV2Tokenizer,
)
from exllamav2.generator import (
    ExLlamaV2DynamicGenerator,
    ExLlamaV2DynamicGeneratorAsync,
    ExLlamaV2DynamicJobAsync,
    ExLlamaV2Sampler,
)

from ragna.core import Assistant


class Exl2Assistant(Assistant):
    """Exl2Assistant - example to instantiate and run inference in process"""

    @classmethod
    def display_name(cls) -> str:
        return "Ragna/Exl2Assistant"

    # TODO; known needs: - pytorch, pytorch-cuda, [cuda-nvcc, rich, ninja, packaging, flash-attn] for paged attention batching, exllamav2
    # @classmethod
    # def requirements(cls, protocol: HttpStreamingProtocol) -> list[Requirement]:
    #     streaming_requirements: dict[HttpStreamingProtocol, list[Requirement]] = {
    #         HttpStreamingProtocol.SSE: [PackageRequirement("httpx_sse")],
    #     }
    # return streaming_requirements.get(protocol, [])

    def __init__(
        self,
    ) -> None:
        self._stream = False
        self._paged = False
        self._max_seq_length = 8192
        self._max_new_tokens = 512
        self._model_directory = ""
        self._load()

    def _load(self):
        self._config = ExLlamaV2Config(self._model_directory)
        self._config.prepare()
        self._config.max_seq_len = self._max_seq_length
        self._model = ExLlamaV2(self._config)
        self._cache = ExLlamaV2Cache_Q4(
            self._model, lazy=True, max_seq_len=self._config.max_seq_len
        )
        self._model.load_autosplit(self._cache)
        self._tokenizer = ExLlamaV2Tokenizer(self._config)
        self.settings = ExLlamaV2Sampler.Settings()
        self.settings.temperature = 0.35
        self.settings.top_k = 50
        self.settings.top_p = 0.8
        self.settings.token_repetition_penalty = 1.05

    def _render_prompt(self, prompt: Union[str, list[Message]]) -> str:
        """
        Ingests ragna messages-list or a single string prompt and converts to assistant-appropriate format.

        Returns:
            Single string containing full rendered chat history with formatting tokens

        Llama3 style prompt compile

        Currently Assuming Enums:
            SYSTEM = "system"
            USER = "user"
            ASSISTANT = "assistant"
        """
        if isinstance(prompt, str):
            system_prompt = "You are an unbiased, helpful assistant."
            texts = [
                f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n{system_prompt}<|eot_id|>\n"
            ]
            texts.append(
                f"<|start_header_id|>user<|end_header_id|>\n\n{prompt}<|eot_id|>\n<|start_header_id|>assistant<|end_header_id|>"
            )
            return "".join(texts)
        else:
            system_prompt = [i["content"] for i in prompt if i["role"] == "system"]
            if len(system_prompt) == 0:
                system_prompt = "You are an unbiased, helpful assistant."
            else:
                system_prompt = system_prompt[0]
            texts = [
                f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n{system_prompt}<|eot_id|>\n"
            ]
            for i in prompt:
                if i["role"] == "user":
                    texts.append(
                        f'<|start_header_id|>user<|end_header_id|>\n\n{i["content"]}<|eot_id|>\n<|start_header_id|>assistant<|end_header_id|>'
                    )
                elif i["role"] == "assistant":
                    if i["content"][-10:] == "<|eot_id|>":
                        texts.append(f'{i["content"]}\n')
                    elif i["content"][-12:] == "<|eot_id|>\n":
                        texts.append(f'{i["content"]}')
                    else:
                        texts.append(f'{i["content"]}<|eot_id|>\n')
                else:
                    pass
            return "".join(texts)

    async def generate(self, prompt: Union[str, list[Message]]) -> str:
        """
        Primary method for calling assistant inference, either as a one-off request from anywhere in ragna, or as part of self.answer()
        This method should be called for tasks like pre-processing, agentic tasks, or any other user-defined calls.

        Args:
            prompt: Either a single prompt string or a list of ragna messages

        Returns:
            async streamed inference response string chunks
        """
        full_prompt = self._render_prompt(prompt)

        self._generator = ExLlamaV2DynamicGenerator(
            model=self._model,
            cache=self._cache,
            tokenizer=self._tokenizer,
            gen_settings=self.settings,
            paged=self._paged,
        )
        outputs = self._generator.generate(
            prompt=full_prompt,
            max_new_tokens=self._max_new_tokens,
            stop_conditions=["</s>", "<|eot_id|>", self._tokenizer.eos_token_id],
            completion_only=True,
        )
        yield outputs

    async def answer(self, messages: list[Message]) -> AsyncIterator[str]:
        prompt, sources = (message := messages[-1]).content, message.sources
        full_prompt = self._render_prompt(prompt)
        input_ids = self._tokenizer.encode(full_prompt)
        # examples at https://github.com/turboderp/exllamav2/blob/master/examples/inference_stream.py
        # and         https://github.com/turboderp/exllamav2/blob/master/examples/inference_async.py
        if self._stream:
            self._generator = ExLlamaV2DynamicGeneratorAsync(
                model=self._model,
                cache=self._cache,
                tokenizer=self._tokenizer,
                paged=self._paged,
                gen_settings=self.settings,
            )
            job = ExLlamaV2DynamicJobAsync(
                generator=self._generator,
                input_ids=input_ids,
                max_new_tokens=self._max_new_tokens,
                token_healing=True,
                stop_conditions=["</s>", "<|eot_id|>", self._tokenizer.eos_token_id],
                completion_only=True,
            )
            async for result in job:
                text_chunk = result.get("text", "")
                if not result["eos"]:
                    yield cast(str, text_chunk)
            await self._generator.close()
        else:
            yield [i async for i in self.generate(prompt)][0]
