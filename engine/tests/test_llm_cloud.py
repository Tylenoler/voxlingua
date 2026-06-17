"""
Tests for llm/cloud.py — CloudLLMClient with mocked HTTP calls.
"""

from unittest.mock import MagicMock, patch

import pytest

from llm.cloud import CloudLLMClient, get_llm_client, set_llm_client


@pytest.fixture
def mock_openai_response():
    """Simulate a successful OpenAI chat completion response."""
    mock = MagicMock()
    mock.choice = MagicMock()
    mock.choice.message.content = "Hello! How can I help you today?"
    mock.choices = [mock.choice]
    return mock


@pytest.fixture(autouse=True)
def _reset_global_client():
    """Reset the global LLM client after each test."""
    yield
    # Don't mess with module state; just ensure tests are clean


class TestCloudLLMClient:
    def test_init_requires_api_key(self):
        """Without API key, should raise ValueError."""
        with patch.dict("os.environ", clear=True):
            with pytest.raises(ValueError, match="API key not found"):
                CloudLLMClient()

    def test_init_with_env_var(self):
        """API key from env var should succeed."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test123"}):
            client = CloudLLMClient()
            assert client.model == "gpt-4o-mini"
            assert client.provider == "openai"

    def test_init_with_custom_params(self):
        """Custom provider/model should be stored."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test123"}):
            client = CloudLLMClient(
                provider="openai",
                model="gpt-4o",
                temperature=0.5,
                max_tokens=1024,
            )
            assert client.model == "gpt-4o"
            assert client.temperature == 0.5
            assert client.max_tokens == 1024

    def test_chat_basic(self, mock_openai_response):
        """chat() should return the model's response text."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test123"}):
            client = CloudLLMClient()
            client._client = MagicMock()
            client._client.chat.completions.create.return_value = mock_openai_response

            messages = [{"role": "user", "content": "Hello"}]
            reply = client.chat(messages, scene="daily_chat")
            assert reply == "Hello! How can I help you today?"

    def test_chat_includes_system_prompt(self, mock_openai_response):
        """chat() prepends the scene system prompt."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test123"}):
            client = CloudLLMClient()
            client._client = MagicMock()
            client._client.chat.completions.create.return_value = mock_openai_response

            client.chat([{"role": "user", "content": "Hi"}], scene="daily_chat")

            call_kwargs = client._client.chat.completions.create.call_args
            sent_messages = call_kwargs[1]["messages"]
            assert sent_messages[0]["role"] == "system"
            assert "New Yorker" in sent_messages[0]["content"]

    def test_chat_passes_parameters(self, mock_openai_response):
        """chat() forwards temperature and max_tokens."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test123"}):
            client = CloudLLMClient(temperature=0.3, max_tokens=256)
            client._client = MagicMock()
            client._client.chat.completions.create.return_value = mock_openai_response

            client.chat([{"role": "user", "content": "Hi"}])

            call_kwargs = client._client.chat.completions.create.call_args
            assert call_kwargs[1]["temperature"] == 0.3
            assert call_kwargs[1]["max_tokens"] == 256

    def test_is_available_returns_true(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test123"}):
            client = CloudLLMClient()
            client._client = MagicMock()
            client._client.models.list.return_value = True
            assert client.is_available() is True

    def test_is_available_returns_false_on_error(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test123"}):
            client = CloudLLMClient()
            client._client = MagicMock()
            client._client.models.list.side_effect = Exception("Network error")
            assert client.is_available() is False


class TestGlobalClient:
    def test_set_and_get(self):
        """set_llm_client() then get_llm_client() returns the same instance."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test123"}):
            client = CloudLLMClient()
            set_llm_client(client)
            retrieved = get_llm_client()
            assert retrieved is client

    def test_get_with_prior_set(self):
        """get_llm_client() returns the pre-set client."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test123"}):
            client = CloudLLMClient(model="gpt-4o")
            set_llm_client(client)
            assert get_llm_client().model == "gpt-4o"
