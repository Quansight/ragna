from __future__ import annotations

import abc
import os
from typing import Annotated

import pydantic

import ragna
from ragna.core import Assistant, EnvVarRequirement, Requirement, Source


class ApiAssistant(Assistant):
    _API_KEY_ENV_VAR: str

    @classmethod
    def requirements(cls) -> list[Requirement]:
        return [EnvVarRequirement(cls._API_KEY_ENV_VAR)]

    def __init__(self) -> None:
        import httpx

        self._client = httpx.AsyncClient(
            headers={"User-Agent": f"{ragna.__version__}/{self}"},
            timeout=60,
        )
        self._api_key = os.environ[self._API_KEY_ENV_VAR]

    async def answer(
        self,
        prompt: str,
        sources: list[Source],
        *,
        max_new_tokens: Annotated[
            int,
            pydantic.Field(
                title="Maximum new tokens",
                description=(
                    "Maximum number of new tokens to generate. "
                    "If you experience truncated answers, increase this value. "
                    "However, be aware that longer answers also incur a higher cost."
                ),
                gt=0,
            ),
        ] = 256,
    ) -> str:
        return await self._call_api(prompt, sources, max_new_tokens=max_new_tokens)

    @abc.abstractmethod
    async def _call_api(
        self, prompt: str, sources: list[Source], *, max_new_tokens: int
    ) -> str:
        ...
