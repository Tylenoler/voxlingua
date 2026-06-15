# Cloud LLM client for VoxLingua

import os
from typing import Optional

from openai import OpenAI


DEFAULT_SCENE_PROMPTS = {
    "daily_chat": (
        "You are a friendly New Yorker having a casual conversation. "
        "You speak naturally with a warm, conversational tone. "
        "Keep responses concise (1-3 sentences). "
        "If the user makes a minor pronunciation error, naturally repeat the"
        " correct word in your response without making it obvious."
        " The user is practicing English. Talk in English only."
    ),
}


class CloudLLMClient:
    """Client for cloud LLM API (OpenAI / Anthropic / compatible)."""

    def __init__(
        self,
        provider: str = "openai",
        model: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        temperature: float = 0.8,
        max_tokens: int = 512,
    ):
        self.provider = provider
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

        # Read API key from env if not provided
        api_key = api_key or os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise ValueError(
                "LLM API key not found. Set LLM_API_KEY or OPENAI_API_KEY"
                " environment variable."
            )

        if provider == "openai":
            kwargs = {"api_key": api_key}
            if endpoint:
                kwargs["base_url"] = endpoint
            self._client = OpenAI(**kwargs)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

    def chat(
        self,
        messages: list[dict],
        scene: str = "daily_chat",
    ) -> str:
        """Send a chat request and return the response text."""
        system_prompt = DEFAULT_SCENE_PROMPTS.get(scene, DEFAULT_SCENE_PROMPTS["daily_chat"])

        full_messages = [{"role": "system", "content": system_prompt}] + messages

        if self.provider == "openai":
            response = self._client.chat.completions.create(
                model=self.model,
                messages=full_messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            return response.choices[0].message.content or ""

        raise ValueError(f"Unsupported provider: {self.provider}")

    def is_available(self) -> bool:
        """Check if the LLM service is reachable."""
        try:
            if self.provider == "openai":
                self._client.models.list()
            return True
        except Exception:
            return False


# Global client (lazy init, set up when API key is configured)
_llm_client: Optional[CloudLLMClient] = None


def get_llm_client() -> CloudLLMClient:
    """Get or create the global LLM client."""
    global _llm_client
    if _llm_client is None:
        _llm_client = CloudLLMClient()
    return _llm_client


def set_llm_client(client: CloudLLMClient):
    global _llm_client
    _llm_client = client
