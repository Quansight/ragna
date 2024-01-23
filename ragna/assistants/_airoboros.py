from ragna.core import Assistant, PackageRequirement, Source


class Airoboros(Assistant):
    @classmethod
    def display_name(cls):
        return "TheBloke/Airoboros-L2-7B-2.2-GPTQ"

    @classmethod
    def requirements(cls):
        return [
            PackageRequirement("torch"),
            PackageRequirement("optimum"),
            PackageRequirement("auto-gptq"),
        ]

    @classmethod
    def is_available(cls):
        requirements_available = super().is_available()
        if not requirements_available:
            return False

        import torch

        return torch.cuda.is_available()

    def __init__(self, config):
        super().__init__(config)

        from auto_gptq import AutoGPTQForCausalLM
        from transformers import AutoTokenizer

        self.tokenizer = AutoTokenizer.from_pretrained(str(self), use_fast=True)
        self.model = AutoGPTQForCausalLM.from_quantized(
            str(self),
            device_map="auto",
            use_triton=False,
            use_safetensors=True,
            trust_remote_code=False,
            inject_fused_attention=False,
        )

    @property
    def max_input_size(self) -> int:
        # FIXME
        return 1024

    def answer(
        self, prompt: str, sources: list[Source], *, max_new_tokens: int = 256
    ) -> str:
        template = """
        A chat about the content of documents.
        Only use the content listed below to answer any questions from the user.
        Do not make up information.
        If you can't answer a question based on the information you are given, just say so.

        {sources}
        
        USER: {prompt}
        ASSISTANT: 
        """
        templated_prompt = template.format(
            sources="- " + "\n - ".join(source.content for source in sources),
            prompt=prompt,
        )
        input_ids = self.tokenizer(
            templated_prompt, return_tensors="pt"
        ).input_ids.cuda()
        output_ids = self.model.generate(
            inputs=input_ids,
            do_sample=False,
            max_new_tokens=max_new_tokens,
        )
        output = self.tokenizer.decode(output_ids[0])
        return output.rsplit("ASSISTANT:", 1)[-1].replace("</s>", "").strip()


assert Airoboros.is_available()
