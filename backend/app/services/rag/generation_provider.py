from typing import Protocol


class GenerationProviderError(RuntimeError):
    pass


class GenerationProvider(Protocol):
    model: str

    async def generate(
            self,
            *,
            system_prompt: str,
            user_prompt: str,
    ) -> str:
        ...