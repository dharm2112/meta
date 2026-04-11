"""LiteLLM proxy-based review agent for the offline PR review environment.

All API calls are throttled via the shared ``global_rate_limiter`` (10 RPM
sliding-window) before hitting the network, and retried with full exponential
backoff + jitter on rate-limit errors.

Rate-limiting strategy
======================
* ``global_rate_limiter.acquire()`` is called once before every chat-completion
  request.  Because all agent instances share the same singleton, the limiter
  has a global view of API usage — even when multiple tasks run back-to-back.
* On a 429 / RateLimitError the agent additionally waits for the
  ``Retry-After`` header value (when present) before falling back to
  exponential backoff: ``min(base * 2^attempt, 60) + random jitter``.
* Max retries has been raised to 5 for production resilience.

Token optimisation
==================
* ``max_tokens`` reduced from 512 → 256.  The model returns a single compact
  JSON object per call; 256 tokens is more than enough.
* The system prompt is concise; ``_slim_obs`` / ``_slim_state`` strip fields
  the model doesn't need.
"""

from __future__ import annotations

import json
import logging
import os
import random
import time
from typing import Any, Dict, Optional

try:
    from openai import OpenAI, RateLimitError as OpenAIRateLimitError
except ImportError:
    OpenAI = None  # type: ignore[assignment,misc]
    OpenAIRateLimitError = Exception  # type: ignore[assignment,misc]

try:
    from rate_limiter import global_rate_limiter
except ImportError:
    from backend.rate_limiter import global_rate_limiter

logger = logging.getLogger(__name__)

# ── System prompt ─────────────────────────────────────────────────────────────
# Kept deliberately short to minimise input-token usage.
SYSTEM_PROMPT = """\
You are a senior software engineer reviewing a pull request.

You receive the current observation (PR metadata, diffs, files) and state
(actions taken so far, step count). Respond with exactly ONE JSON action.

Available actions:
- {"action_type": "inspect_diff", "path": "<file>"}
- {"action_type": "inspect_file", "path": "<file>"}
- {"action_type": "comment",      "text": "<review comment>"}
- {"action_type": "approve",      "text": "<reason>"}   (terminal)
- {"action_type": "reject",       "text": "<reason>"}   (terminal)
- {"action_type": "escalate",     "text": "<reason>"}   (terminal)

Strategy: inspect diffs → comment on the bug → make a final decision.
IMPORTANT: Respond with ONLY the JSON object. No markdown, no explanation.
"""

# ── Retry / backoff configuration ─────────────────────────────────────────────
_MAX_RETRIES: int = 5          # attempts after the first failure
_BASE_BACKOFF: float = 2.0     # seconds for attempt 0 backoff
_MAX_BACKOFF: float = 60.0     # backoff ceiling


class LiteLLMReviewAgent:
    """Uses the LiteLLM proxy (OpenAI-compatible API) to decide review actions.

    All calls are pre-throttled by the shared ``global_rate_limiter`` and
    retried on transient / rate-limit failures using exponential backoff.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> None:
        if OpenAI is None:
            raise ImportError("Install the openai package: pip install openai>=1.0")

        self.client = OpenAI(
            api_key=api_key or os.environ.get("API_KEY"),
            base_url=base_url or os.environ.get("API_BASE_URL"),
        )
        self.model = model or os.environ.get("MODEL_NAME", "gpt-4o-mini")

    # ── Public interface ──────────────────────────────────────────────────────

    def act(self, observation: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
        """Choose the next review action given the current observation and state.

        Args:
            observation: Raw env observation dict (will be slimmed internally).
            state:       Raw env state dict (will be slimmed internally).

        Returns:
            A valid action dict, e.g. ``{"action_type": "reject", "text": "..."}``.

        Raises:
            RuntimeError:  If all retries are exhausted without a successful call.
        """
        user_content = json.dumps(
            {"observation": _slim_obs(observation), "state": _slim_state(state)},
            indent=2,
        )

        last_error: Optional[Exception] = None

        for attempt in range(_MAX_RETRIES + 1):
            try:
                # Acquire a rate-limit slot before every network call
                logger.debug(
                    "[LiteLLMAgent] Acquiring rate-limit slot (attempt %d)…",
                    attempt + 1,
                )
                global_rate_limiter.acquire()

                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_content},
                    ],
                    temperature=0.0,
                    max_tokens=256,  # Reduced from 512; actions are compact JSON
                )

                raw = (response.choices[0].message.content or "{}").strip()

                # Strip markdown code fences if the model wrapped its response
                if raw.startswith("```"):
                    raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

                action = json.loads(raw)
                if "action_type" not in action:
                    raise ValueError(f"Model returned invalid action: {raw!r}")

                logger.info("[LiteLLMAgent] Action: %s", action.get("action_type"))
                return action

            except Exception as exc:
                last_error = exc
                if attempt == _MAX_RETRIES:
                    break  # All retries exhausted

                backoff = self._compute_backoff(attempt, exc)
                logger.warning(
                    "[LiteLLMAgent] Call failed (attempt %d/%d): %s — retrying in %.1fs",
                    attempt + 1,
                    _MAX_RETRIES + 1,
                    exc,
                    backoff,
                )
                time.sleep(backoff)

        raise RuntimeError(
            f"LiteLLMReviewAgent: all {_MAX_RETRIES + 1} attempts failed. "
            f"Last error: {last_error}"
        ) from last_error

    # ── Retry helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _compute_backoff(attempt: int, exc: Exception) -> float:
        """Return how many seconds to sleep before the next retry.

        For rate-limit errors the ``Retry-After`` response header is honoured
        when available.  Otherwise, full exponential backoff with jitter is used.
        """
        # Try to extract Retry-After header from the exception
        retry_after = _extract_retry_after(exc)
        if retry_after is not None:
            logger.info(
                "[LiteLLMAgent] Respecting Retry-After: %.0fs", retry_after
            )
            return retry_after

        # Exponential backoff with uniform jitter
        exponential = min(_BASE_BACKOFF * (2 ** attempt), _MAX_BACKOFF)
        jitter = random.uniform(0.1, 1.0)
        return exponential + jitter


# ── Backward compatibility alias ──────────────────────────────────────────────
GroqReviewAgent = LiteLLMReviewAgent


# ── Observation / state slimming ──────────────────────────────────────────────

def _slim_obs(obs: Dict[str, Any]) -> Dict[str, Any]:
    """Return only the fields the model needs to make a decision.

    Stripping unused fields (large diffs, full file contents already seen)
    keeps the input token count low and reduces cost / latency.
    """
    return {
        "task_id":         obs.get("task_id"),
        "difficulty":      obs.get("difficulty"),
        "summary":         obs.get("summary"),
        "issue_title":     obs.get("issue_title"),
        # issue_body is often large; include only the first 500 chars
        "issue_body":      (obs.get("issue_body") or "")[:500] or None,
        "changed_files":   obs.get("changed_files"),
        "available_files": obs.get("available_files"),
        "available_actions": obs.get("available_actions"),
        "latest_event":    obs.get("latest_event"),
    }


def _slim_state(state: Dict[str, Any]) -> Dict[str, Any]:
    """Return a compact state representation for the model."""
    return {
        "current_step":    state.get("current_step"),
        "max_steps":       state.get("max_steps"),
        "inspected_diffs": state.get("inspected_diffs"),
        "inspected_files": state.get("inspected_files"),
        # Only include action_type + path, not full text (saves tokens)
        "actions_taken": [
            {
                "step":        a["step"],
                "action_type": a["action_type"],
                "path":        a.get("path"),
            }
            for a in state.get("actions_taken", [])
        ],
    }


# ── Utility ───────────────────────────────────────────────────────────────────

def _extract_retry_after(exc: Exception) -> Optional[float]:
    """Attempt to read the ``Retry-After`` header from an API exception.

    The openai SDK (v1+) attaches the raw ``httpx.Response`` to rate-limit
    errors.  We try several paths so that this works across SDK versions.
    """
    # openai SDK v1+: RateLimitError carries a .response attribute
    response = getattr(exc, "response", None)
    if response is not None:
        headers = getattr(response, "headers", {})
        value = headers.get("Retry-After") or headers.get("retry-after")
        if value is not None:
            try:
                return float(value)
            except (ValueError, TypeError):
                pass

    # Some wrappers surface it directly on the exception
    direct = getattr(exc, "retry_after", None)
    if direct is not None:
        try:
            return float(direct)
        except (ValueError, TypeError):
            pass

    return None
