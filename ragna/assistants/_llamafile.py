import os
from functools import cached_property

from ._http_api import HttpStreamingProtocol
from ._openai import OpenaiLikeHttpApiAssistant


class LlamafileAssistant(OpenaiLikeHttpApiAssistant):
    """[llamafile](https://github.com/Mozilla-Ocho/llamafile)

    To use this assistant, start the llamafile server manually. By default, the server
    is expected at `http://localhost:8080`. This can be changed with the
    `RAGNA_LLAMAFILE_BASE_URL` environment variable.

    !!! info "Required packages"

        - `httpx_sse`
    """

    _API_KEY_ENV_VAR = None
    _STREAMING_PROTOCOL = HttpStreamingProtocol.SSE
    _MODEL = None

    @classmethod
    def display_name(cls) -> str:
        return "llamafile"

    @cached_property
    def _url(self) -> str:
        base_url = os.environ.get("RAGNA_LLAMAFILE_BASE_URL", "http://localhost:8080")
        return f"{base_url}/v1/chat/completions"
