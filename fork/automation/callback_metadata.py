"""Bounded callback outcomes preserving the deployed automation UI contract.

Only newly supplied task_outcome is sanitized. Existing metadata and the real
FinishTool response keep their established contract.
"""

from __future__ import annotations

import json
import math
import re
import unicodedata
from typing import Any


MAX_OUTCOME_BYTES = 8192
MAX_SUMMARY_CHARS = 1024
MAX_STRING_CHARS = 512
MAX_DEPTH = 4
MAX_ITEMS = 20
MAX_NODES = 128
_STATUSES = frozenset({"success", "partial_success", "blocked", "failed", "unknown"})
_DROP = object()
_SENSITIVE = re.compile(
    r"token|secret|password|passwd|authorization|authentication|credential|cookie|"
    r"apikey|sessionkey|privatekey|accesskey|signingkey|encryptionkey|"
    r"error|exception|traceback|stacktrace|stdout|stderr|headers|rawresponse|rawbody"
)
_ASSIGNMENT = re.compile(
    r"""(?ix)(?<![\w.-])(["']?[\w.-]*(?:token|secret|password|passwd|authorization|credential|cookie|api[_-]?key|session[_-]?key|private[_-]?key)[\w.-]*["']?\s*[:=]\s*)(?:"[^"\n]*"|'[^'\n]*'|[^\s,;&]+)"""  # noqa: E501
)
_AUTH = re.compile(r"(?i)\b(?:Bearer|Basic)\s+[A-Za-z0-9._~+/=-]+")
_URL_USERINFO = re.compile(r"(?i)(\b[a-z][a-z0-9+.-]*://)[^\s/@]+@")
_KNOWN_TOKEN = re.compile(
    r"\b(?:gh[pousr]_[A-Za-z0-9_]{8,}|github_pat_[A-Za-z0-9_]{8,}|"
    r"sk-[A-Za-z0-9_-]{8,}|AKIA[A-Z0-9]{16}|"
    r"eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)\b"
)
_PRIVATE_KEY = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?(?:-----END [A-Z ]*PRIVATE KEY-----|$)",
    re.DOTALL,
)


def _safe_text(value: str, limit: int) -> str:
    value = value[: max(limit * 4, 4096)]
    if "Traceback (most recent call last)" in value:
        return "[REDACTED]"
    value = _PRIVATE_KEY.sub("[REDACTED]", value)
    value = _URL_USERINFO.sub(r"\1[REDACTED]@", value)
    value = _AUTH.sub("[REDACTED]", value)
    value = _ASSIGNMENT.sub(r"\1[REDACTED]", value)
    value = _KNOWN_TOKEN.sub("[REDACTED]", value)
    value = "".join(
        c for c in value if c in "\n\t" or not unicodedata.category(c).startswith("C")
    )
    return value[:limit]


def _safe_key(key: Any) -> str | None:
    if not isinstance(key, str) or not key or len(key) > 64:
        return None
    normalized = unicodedata.normalize("NFKC", key)
    compact = re.sub(r"[^a-z0-9]", "", normalized.lower())
    if compact == "key" or _SENSITIVE.search(compact):
        return None
    clean = _safe_text(normalized, 64)
    return clean if clean == normalized else None


def _sanitize(value: Any, depth: int, budget: list[int]) -> Any:
    if budget[0] <= 0 or depth > MAX_DEPTH:
        return _DROP
    budget[0] -= 1
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, str):
        return _safe_text(value, MAX_STRING_CHARS)
    if isinstance(value, int):
        return value if value.bit_length() <= 64 else _DROP
    if isinstance(value, float):
        return value if math.isfinite(value) else _DROP
    if isinstance(value, dict):
        result = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= MAX_ITEMS or budget[0] <= 0:
                break
            key = _safe_key(key)
            if key is None:
                continue
            clean = _sanitize(item, depth + 1, budget)
            if clean is not _DROP:
                result[key] = clean
        return result
    if isinstance(value, (list, tuple)):
        result = []
        for item in value[:MAX_ITEMS]:
            clean = _sanitize(item, depth + 1, budget)
            if clean is not _DROP:
                result.append(clean)
        return result
    return _DROP


def normalize_task_outcome(task_outcome: dict[str, Any]) -> dict[str, Any]:
    """Bound explicit business metadata without deriving facts from run status."""
    status = task_outcome.get("status")
    summary = task_outcome.get("outcome_summary")
    outcome = {
        "status": status
        if isinstance(status, str) and status in _STATUSES
        else "unknown",
        "outcome_summary": _safe_text(summary, MAX_SUMMARY_CHARS)
        if isinstance(summary, str)
        else "",
    }
    while len(json.dumps(outcome, allow_nan=False).encode("utf-8")) > MAX_OUTCOME_BYTES:
        outcome["outcome_summary"] = outcome["outcome_summary"][:-64]
    budget = [MAX_NODES]
    for index, (key, value) in enumerate(task_outcome.items()):
        if index >= MAX_ITEMS or budget[0] <= 0:
            break
        key = _safe_key(key)
        if key is None or key in ("status", "outcome_summary"):
            continue
        clean = _sanitize(value, 1, budget)
        if clean is _DROP:
            continue
        outcome[key] = clean
        if (
            len(json.dumps(outcome, allow_nan=False).encode("utf-8"))
            > MAX_OUTCOME_BYTES
        ):
            del outcome[key]
    return outcome


def merge_callback_metadata(
    existing: dict[str, Any] | None,
    task_outcome: dict[str, Any] | None,
    finish_tool_response: Any = None,
) -> dict[str, Any]:
    """Merge flat callback outcome, retaining real finish and ownership metadata."""
    metadata = dict(existing or {})
    if finish_tool_response is not None:
        metadata["finish_tool_response"] = finish_tool_response
    if task_outcome is not None:
        response = metadata.get("finish_tool_response")
        if isinstance(response, dict):
            response = dict(response)
        elif isinstance(response, str):
            response = {"message": response}
        elif response is not None:
            response = {"response": response}
        else:
            response = {}
        response.update(normalize_task_outcome(task_outcome))
        metadata["finish_tool_response"] = response
    return metadata
