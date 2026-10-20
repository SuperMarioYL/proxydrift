"""Tests for the optional GLM/DeepSeek narrative review.

Focus: the degradation contract — a narrative failure (transport error,
non-JSON body, unexpected payload shape) must surface as
:class:`proxydrift.llm_review.LLMReviewError` so the CLI can skip the
narrative and keep the statistical audit standing — plus provider
selection from the environment.
"""

from __future__ import annotations

import json

import httpx
import pytest

from proxydrift.align import align_streams
from proxydrift.demo_data import build_demo_replay
from proxydrift.divergence import audit
from proxydrift.llm_review import (
    LLMReviewError,
    PROVIDERS,
    request_narrative,
    resolve_provider,
    review_flags,
)


def _aligned_with_flags():
    replay = build_demo_replay()
    aligned = align_streams(replay.proxy_events, replay.outcome_events, lag_days=7)
    flags = audit(replay.proxy_events, replay.outcome_events, lag_days=7)
    return aligned, flags


class _FakeResponse:
    """Minimal stand-in for httpx.Response."""

    def __init__(self, *, status_code=200, body=None, json_error=None, text=""):
        self.status_code = status_code
        self._body = body
        self._json_error = json_error
        self.text = text

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"error {self.status_code}",
                request=httpx.Request("POST", "https://unit.test"),
                response=httpx.Response(self.status_code),
            )

    def json(self):
        if self._json_error is not None:
            raise self._json_error
        return self._body


@pytest.fixture()
def fake_post(monkeypatch):
    """Replace httpx.post; the deferred import resolves to the same module."""
    calls = {}

    def _install(response):
        def _post(url, **kwargs):
            calls["url"] = url
            calls["kwargs"] = kwargs
            return response

        monkeypatch.setattr(httpx, "post", _post)
        return calls

    return _install


class TestNarrativeDegradation:
    def test_non_json_200_body_raises_llm_review_error(self, fake_post):
        """A 200 response carrying a non-JSON body (gateway/proxy page) must
        degrade to LLMReviewError — never an escaping JSONDecodeError."""
        fake_post(
            _FakeResponse(
                json_error=json.JSONDecodeError("Expecting value", "<html>502</html>", 0),
                text="<html>gateway error</html>",
            )
        )
        aligned, flags = _aligned_with_flags()
        with pytest.raises(LLMReviewError):
            request_narrative(aligned, flags, PROVIDERS["glm"], "key")

    def test_unexpected_payload_shape_raises_llm_review_error(self, fake_post):
        fake_post(_FakeResponse(body={"error": "no choices here"}))
        aligned, flags = _aligned_with_flags()
        with pytest.raises(LLMReviewError):
            request_narrative(aligned, flags, PROVIDERS["glm"], "key")

    def test_valid_response_returns_narrative(self, fake_post):
        calls = fake_post(
            _FakeResponse(
                body={"choices": [{"message": {"content": "窗口统计形状……"}}]}
            )
        )
        aligned, flags = _aligned_with_flags()
        result = request_narrative(aligned, flags, PROVIDERS["glm"], "key")
        assert result.narrative == "窗口统计形状……"
        assert result.source == "GLM glm-4.6"
        assert calls["kwargs"]["headers"]["Authorization"] == "Bearer key"


class TestProviderSelection:
    def test_no_key_returns_none(self, monkeypatch):
        env = {"PATH": "/usr/bin"}
        assert resolve_provider(env) is None

    def test_glm_key_wins_by_default(self):
        env = {"ZHIPU_API_KEY": " glm-key ", "DEEPSEEK_API_KEY": "ds-key"}
        provider, api_key = resolve_provider(env)
        assert provider.key == "glm"
        assert api_key == "glm-key"  # stripped

    def test_forced_provider_is_honoured(self):
        env = {"PROXYDRIFT_LLM_PROVIDER": "deepseek", "DEEPSEEK_API_KEY": "ds"}
        assert resolve_provider(env)[0].key == "deepseek"

    def test_unknown_forced_provider_raises(self):
        with pytest.raises(LLMReviewError, match="PROXYDRIFT_LLM_PROVIDER"):
            resolve_provider({"PROXYDRIFT_LLM_PROVIDER": "openai", "OPENAI_API_KEY": "x"})


class TestReviewFlagsContract:
    def test_no_key_configured_stands_alone(self):
        aligned, flags = _aligned_with_flags()
        assert review_flags(aligned, flags, env={}) is None

    def test_no_flags_with_key_set_raises_llm_review_error(self, fake_post):
        aligned, _ = _aligned_with_flags()
        env = {"ZHIPU_API_KEY": "key"}
        with pytest.raises(LLMReviewError):
            review_flags(aligned, [], env=env)
