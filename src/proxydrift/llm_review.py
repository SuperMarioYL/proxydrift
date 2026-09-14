"""One OpenAI-compatible request that turns flagged windows into an audit narrative.

The statistical audit in :mod:`proxydrift.divergence` stands alone — no
key, no model, no network.  When a key IS present, this module makes a
single chat-completions call to a domestic (国产) model so the flagged
windows read as a short Chinese narrative instead of bare numbers:

* **GLM-4 series** on 智谱开放平台 (``ZHIPU_API_KEY``) — the primary
  reviewer, default model ``glm-4.6``;
* **DeepSeek** (``DEEPSEEK_API_KEY``) — the drop-in alternative, default
  model ``deepseek-flash`` (``deepseek-v4-pro`` via
  ``PROXYDRIFT_DEEPSEEK_MODEL`` for deeper narrative).

Provider selection is automatic from whichever key is set (GLM first),
with ``PROXYDRIFT_LLM_PROVIDER=glm|deepseek`` to force one and
``PROXYDRIFT_GLM_MODEL`` / ``PROXYDRIFT_DEEPSEEK_MODEL`` to override the
model names.  No key configured → the caller skips the narrative and the
audit stands alone; a transport or API failure raises
:class:`LLMReviewError`, which the CLI reports as a skip — never as a
failed audit.

The division of responsibility is hard: the model only *describes* the
statistical shape of windows the engine already flagged.  It is
instructed never to issue causal conclusions, and the
``correlational heuristic — not a causal verdict`` label is stamped by
:mod:`proxydrift.report` in code around whatever text comes back — the
model cannot alter it.
"""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from .align import AlignedStreams
from .divergence import CORRELATIONAL_VERDICT, DivergenceFlag

__all__ = [
    "DEFAULT_TIMEOUT",
    "PROVIDERS",
    "LLMReviewError",
    "ReviewResult",
    "ProviderConfig",
    "resolve_provider",
    "request_narrative",
    "review_flags",
]

DEFAULT_TIMEOUT = 30.0


@dataclass(frozen=True)
class ProviderConfig:
    """One OpenAI-compatible chat-completions endpoint."""

    key: str  # provider id, e.g. "glm"
    label: str  # human-facing name, e.g. "GLM"
    base_url: str
    model: str
    model_env: str  # env var overriding the model name
    key_env: str  # env var carrying the API key


PROVIDERS: dict[str, ProviderConfig] = {
    "glm": ProviderConfig(
        key="glm",
        label="GLM",
        base_url="https://open.bigmodel.cn/api/paas/v4",
        model="glm-4.6",
        model_env="PROXYDRIFT_GLM_MODEL",
        key_env="ZHIPU_API_KEY",
    ),
    "deepseek": ProviderConfig(
        key="deepseek",
        label="DeepSeek",
        base_url="https://api.deepseek.com",
        model="deepseek-flash",
        model_env="PROXYDRIFT_DEEPSEEK_MODEL",
        key_env="DEEPSEEK_API_KEY",
    ),
}


class LLMReviewError(RuntimeError):
    """The narrative request failed; the message is bilingual (zh + en)."""


@dataclass(frozen=True)
class ReviewResult:
    """The narrative text plus the short model label shown beside it."""

    narrative: str
    source: str  # e.g. "GLM glm-4.6"


def resolve_provider(
    env: Mapping[str, str] | None = None,
) -> tuple[ProviderConfig, str] | None:
    """Pick the reviewer from the environment; ``None`` when no key is set.

    ``PROXYDRIFT_LLM_PROVIDER`` forces a provider (its key must still be
    present); otherwise the first provider with a key wins, GLM first —
    it is the primary reviewer.
    """
    env = os.environ if env is None else env
    forced = env.get("PROXYDRIFT_LLM_PROVIDER", "").strip().lower()
    if forced:
        if forced not in PROVIDERS:
            raise LLMReviewError(
                f"PROXYDRIFT_LLM_PROVIDER={forced!r} 无法识别，"
                f"可选 {'/'.join(PROVIDERS)} / unknown provider "
                f"{forced!r}, expected one of {'/'.join(PROVIDERS)}"
            )
        order: list[str] = [forced]
    else:
        order = list(PROVIDERS)  # dict order: glm first, deepseek second
    for key in order:
        provider = PROVIDERS[key]
        if env.get(provider.key_env, "").strip():
            return provider, env[provider.key_env].strip()
    return None


def request_narrative(
    aligned: AlignedStreams,
    flags: Sequence[DivergenceFlag],
    provider: ProviderConfig,
    api_key: str,
    *,
    model: str | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> ReviewResult:
    """Make the one chat-completions request; raises :class:`LLMReviewError`."""
    if not flags:
        raise LLMReviewError(
            "没有已亮旗窗口，无需叙事 / no flagged windows, nothing to narrate"
        )
    model = model or provider.model
    system = (
        "你是 ProxyDrift 的审计叙事助手。ProxyDrift 对齐 Agent 决策流与延迟到达的"
        "真实结果流，在「代理上行、结果下行、反相关」的窗口亮旗。"
        f"每条旗标的判定标签固定为「{CORRELATIONAL_VERDICT}」，由代码盖章，你不能更改。"
        "你的任务：把下面已亮旗窗口的统计形状写成 2 到 3 段简体中文，供人工复核。"
        "只描述窗口内两条流的统计关系（方向、相对幅度、相关系数、嫌疑动作的分布），"
        "并提示读者去复核该窗口的运营上下文。"
        "禁止给出因果结论；禁止使用「因为」「导致」「罪魁」式的因果断言；"
        "禁止建议处罚、回滚或改判；禁止编造窗口外的数据。"
    )
    user = _prompt_body(aligned, flags)
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.2,
        "max_tokens": 800,
    }

    import httpx  # deferred: a terminal-only audit never imports it

    url = provider.base_url.rstrip("/") + "/chat/completions"
    try:
        response = httpx.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
        )
        response.raise_for_status()
        body = response.json()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:200]
        raise LLMReviewError(
            f"{provider.label} 返回 {exc.response.status_code}：{detail} / "
            f"{provider.label} responded {exc.response.status_code}: {detail}"
        ) from exc
    except httpx.HTTPError as exc:
        raise LLMReviewError(
            f"{provider.label} 请求失败（{exc}）/ "
            f"{provider.label} request failed ({exc})"
        ) from exc
    try:
        content = body["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, AttributeError, TypeError) as exc:
        raise LLMReviewError(
            f"{provider.label} 响应结构异常 / {provider.label} "
            "returned an unexpected response shape"
        ) from exc
    if not content:
        raise LLMReviewError(
            f"{provider.label} 返回空叙事 / {provider.label} returned empty text"
        )
    return ReviewResult(narrative=content, source=f"{provider.label} {model}")


def review_flags(
    aligned: AlignedStreams,
    flags: Sequence[DivergenceFlag],
    *,
    env: Mapping[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> ReviewResult | None:
    """High-level entry: pick the provider from ``env`` and narrate ``flags``.

    Returns ``None`` when no API key is configured (the audit stands
    alone).  Raises :class:`LLMReviewError` when a configured request
    fails — callers degrade gracefully around it.
    """
    resolved = resolve_provider(env)
    if resolved is None:
        return None
    provider, api_key = resolved
    env = os.environ if env is None else env
    model = env.get(provider.model_env, "").strip() or None
    return request_narrative(
        aligned, flags, provider, api_key, model=model, timeout=timeout
    )


def _prompt_body(
    aligned: AlignedStreams, flags: Sequence[DivergenceFlag]
) -> str:
    """Compact, factual dump of the aligned join and every flag."""
    lines = [
        f"对齐 join：lag = {aligned.lag_days} 天，"
        f"已对齐决策日 {len(aligned.pairs)} 天，覆盖率缺口 {len(aligned.gaps)} 天。",
        f"已亮旗窗口 {len(flags)} 个：",
    ]
    for index, flag in enumerate(flags, start=1):
        first_day, last_day = flag.window
        suspects = (
            "、".join(flag.suspect_action_ids)
            if flag.suspect_action_ids
            else "无"
        )
        lines.append(
            f"{index}. 窗口 {first_day.isoformat()} 至 {last_day.isoformat()}"
            f"（{(last_day - first_day).days + 1} 天）："
            f"代理趋势 {flag.proxy_trend:+.2f} σ/天，"
            f"结果趋势 {flag.outcome_trend:+.2f} σ/天，"
            f"窗口相关系数 {flag.corr:.2f}，"
            f"嫌疑动作（按代理质量占比排序）：{suspects}。"
        )
    lines.append(
        "请用 2 到 3 段简体中文描述这些窗口的统计形状与值得人工复核的点。"
    )
    return "\n".join(lines)
