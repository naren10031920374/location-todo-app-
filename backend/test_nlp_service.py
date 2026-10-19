"""Tests for nlp_service. The HTTP call is mocked, so no API key or network is needed."""
import pytest
import requests

import nlp_service


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


def chat_payload(content):
    return {"choices": [{"message": {"content": content}}]}


@pytest.fixture(autouse=True)
def configured(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)


def mock_post(monkeypatch, response=None, exc=None):
    calls = []

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        if exc:
            raise exc
        return response

    monkeypatch.setattr(nlp_service.requests, "post", fake_post)
    return calls


def test_request_uses_groq_defaults_and_bearer_key(monkeypatch):
    calls = mock_post(monkeypatch, FakeResponse(payload=chat_payload("other")))
    nlp_service.classify_todo_category("anything")
    call = calls[0]
    assert call["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert call["headers"]["Authorization"] == "Bearer test-key"
    assert call["json"]["model"] == nlp_service.DEFAULT_MODEL
    assert call["json"]["messages"][0]["role"] == "user"


def test_env_overrides_base_url_and_model(monkeypatch):
    monkeypatch.setenv("LLM_BASE_URL", "https://example.test/v1/")
    monkeypatch.setenv("LLM_MODEL", "my-model")
    calls = mock_post(monkeypatch, FakeResponse(payload=chat_payload("other")))
    nlp_service.classify_todo_category("anything")
    assert calls[0]["url"] == "https://example.test/v1/chat/completions"
    assert calls[0]["json"]["model"] == "my-model"


def test_groq_api_key_fallback(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY")
    monkeypatch.setenv("GROQ_API_KEY", "groq-key")
    calls = mock_post(monkeypatch, FakeResponse(payload=chat_payload("other")))
    nlp_service.classify_todo_category("anything")
    assert calls[0]["headers"]["Authorization"] == "Bearer groq-key"


def test_missing_key_on_hosted_provider_fails_without_calling_api(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY")
    calls = mock_post(monkeypatch, FakeResponse(payload=chat_payload("other")))
    assert nlp_service.classify_todo_category("x") is None
    assert nlp_service.suggest_stores_for_item("x") == []
    assert "not configured" in nlp_service.parse_todo_text("x")["error"]
    assert calls == []


def test_local_server_needs_no_key(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY")
    monkeypatch.setenv("LLM_BASE_URL", "http://localhost:11434/v1")
    calls = mock_post(monkeypatch, FakeResponse(payload=chat_payload("pharmacy")))
    assert nlp_service.classify_todo_category("aspirin") == "pharmacy"
    assert "Authorization" not in calls[0]["headers"]


def test_parse_todo_text_extracts_json_from_chatty_reply(monkeypatch):
    reply = 'Sure! Here you go:\n{"items": ["milk", "eggs"], "store": "Walmart", "date": "tomorrow", "category": "groceries"}\nHope that helps.'
    mock_post(monkeypatch, FakeResponse(payload=chat_payload(reply)))
    result = nlp_service.parse_todo_text("milk and eggs from Walmart tomorrow")
    assert result["items"] == ["milk", "eggs"]
    assert result["store"] == "Walmart"


def test_parse_todo_text_reports_bad_json(monkeypatch):
    mock_post(monkeypatch, FakeResponse(payload=chat_payload("{not valid json}")))
    assert "Failed to parse JSON" in nlp_service.parse_todo_text("x")["error"]


def test_parse_todo_text_reports_no_json(monkeypatch):
    mock_post(monkeypatch, FakeResponse(payload=chat_payload("I cannot do that")))
    assert nlp_service.parse_todo_text("x")["error"] == "No JSON found in response"


def test_http_error_is_reported_not_raised(monkeypatch):
    mock_post(monkeypatch, FakeResponse(status_code=429))
    assert nlp_service.parse_todo_text("x")["error"] == "LLM error: HTTP 429"
    assert nlp_service.classify_todo_category("x") is None
    assert nlp_service.suggest_stores_for_item("x") == []


def test_connection_error_is_reported_not_raised(monkeypatch):
    mock_post(monkeypatch, exc=requests.exceptions.ConnectionError("boom"))
    assert "connection error" in nlp_service.parse_todo_text("x")["error"]
    assert nlp_service.classify_todo_category("x") is None


def test_unexpected_response_shape(monkeypatch):
    mock_post(monkeypatch, FakeResponse(payload={"unexpected": True}))
    assert "unexpected response format" in nlp_service.parse_todo_text("x")["error"]


@pytest.mark.parametrize("reply,expected", [
    ("groceries", "groceries"),
    ("  Pharmacy.\n", "pharmacy"),
    ('"hardware"', "hardware"),
    ("a made up category", "other"),
])
def test_classify_normalizes_reply(monkeypatch, reply, expected):
    mock_post(monkeypatch, FakeResponse(payload=chat_payload(reply)))
    assert nlp_service.classify_todo_category("x") == expected


def test_suggest_stores_parses_array_and_filters_non_strings(monkeypatch):
    mock_post(monkeypatch, FakeResponse(payload=chat_payload('Stores: ["Walmart", "Target", 5]')))
    assert nlp_service.suggest_stores_for_item("milk") == ["Walmart", "Target"]


def test_suggest_stores_bad_reply_returns_empty(monkeypatch):
    mock_post(monkeypatch, FakeResponse(payload=chat_payload("no list here")))
    assert nlp_service.suggest_stores_for_item("milk") == []
