from typing import cast
import boto3
import json
from ragna.core import RagnaException, Source

from ._api import ApiAssistant


class AmazonBedrockAssistant(ApiAssistant):
    _API_KEY_ENV_VAR = "AWS_ACCESS_KEY_ID"
    _MODEL: str
    _CONTEXT_SIZE: int

    @classmethod
    def display_name(cls) -> str:
        return f"AmazonBedRock/{cls._MODEL}"

    @property
    def max_input_size(self) -> int:
        return self._CONTEXT_SIZE

    def _instructize_prompt(self, prompt: str, sources: list[Source]) -> str:
        instruction = (
            "\n\nHuman: "
            "Use the following pieces of context to answer the question at the end. "
            "If you don't know the answer, just say so. Don't try to make up an answer.\n"
        )

        instruction += "\n\n".join(source.content for source in sources)
        return f"{instruction}\n\nQuestion: {prompt}\n\nAssistant:"

    def _call_api(
        self, prompt: str, sources: list[Source], *, max_new_tokens: int
    ) -> str:
        bedrock = boto3.client(service_name='bedrock-runtime',
                               region_name='eu-central-1')
        # See https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_InvokeModel.html
        prompt_config = {
            "prompt": self._instructize_prompt(prompt, sources),
            "max_tokens_to_sample": max_new_tokens,
            "temperature": 0.0
            }
        
        try:
            response = bedrock.invoke_model(
            body=json.dumps(prompt_config),
            modelId=f"anthropic.{self._MODEL}"
            )
        
            response_body = json.loads(response.get("body").read())
        
            return cast(str, response_body.get("completion"))
        except Exception as e:
            raise ValueError(f"Error raised by inference endpoint: {e}")
    


class AmazonBedRockClaude(AmazonBedrockAssistant):
    """[Amazon Bedrock Claud v2](https://eu-central-1.console.aws.amazon.com/bedrock/home?region=eu-central-1#/providers?model=anthropic.claude-v2)

    !!! info "AWS credentials required. Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables"
    

    """

    _MODEL = "claude-v2"
    _CONTEXT_SIZE = 100_000

class AmazonBedRockClaudev1(AmazonBedrockAssistant):
    """[Amazon Bedrock Claud v1](https://eu-central-1.console.aws.amazon.com/bedrock/home?region=eu-central-1#/providers?model=anthropic.claude-v2)

    !!! info "AWS credentials required. Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables"
    

    """

    _MODEL = "claude-instant-v1"
    _CONTEXT_SIZE = 100_000
    