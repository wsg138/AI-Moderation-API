from __future__ import annotations

import hashlib
import hmac
import ipaddress
import re
import unicodedata

_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_IPV4_RE = re.compile(r"(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)")
_IPV6_CANDIDATE_RE = re.compile(
    r"(?<![0-9A-Fa-f:])[0-9A-Fa-f]{0,4}:[0-9A-Fa-f:]{2,}(?![0-9A-Fa-f:])"
)
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?1[ .-]?)?(?:\(?\d{3}\)?[ .-]?)\d{3}[ .-]?\d{4}(?!\d)")
_BEARER_RE = re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{12,}\b", re.IGNORECASE)
_DISCORD_TOKEN_RE = re.compile(
    r"\b(?:mfa\.)?[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{20,}\b"
)
_SECRET_ASSIGN_RE = re.compile(
    r"(?i)\b(api[_-]?key|token|password|passwd|secret)\s*[:=]\s*[^\s,;]{8,}"
)
_ZERO_WIDTH_RE = re.compile("[\u200b-\u200f\u2060\ufeff]")
_WS_RE = re.compile(r"\s+")


def pseudonymize(sender: str, run_key: bytes) -> str:
    digest = hmac.new(run_key, sender.encode("utf-8", "replace"), hashlib.sha256).hexdigest()
    return f"user_{digest[:12]}"


def _redact_ipv6(match: re.Match[str]) -> str:
    candidate = match.group(0)
    try:
        address = ipaddress.ip_address(candidate)
    except ValueError:
        return candidate
    return "<IP>" if address.version == 6 else candidate


def redact_text(text: str) -> str:
    value = text
    replacements = (
        (_BEARER_RE, "<TOKEN>"),
        (_DISCORD_TOKEN_RE, "<TOKEN>"),
        (_SECRET_ASSIGN_RE, r"\1=<TOKEN>"),
        (_EMAIL_RE, "<EMAIL>"),
        (_PHONE_RE, "<PHONE>"),
        (_IPV4_RE, "<IP>"),
    )
    for pattern, replacement in replacements:
        value = pattern.sub(replacement, value)
    return _IPV6_CANDIDATE_RE.sub(_redact_ipv6, value)


def normalized_text(text: str) -> str:
    value = unicodedata.normalize("NFKC", text).casefold()
    value = _ZERO_WIDTH_RE.sub("", value)
    return _WS_RE.sub(" ", value).strip()


def family_fingerprint(text: str) -> str:
    value = normalized_text(text)
    value = re.sub(r"[^a-z0-9]+", "", value)
    value = re.sub(r"(.)\1{2,}", r"\1\1", value)
    return hashlib.sha256(value.encode()).hexdigest()[:20]


def stable_hash(*parts: str) -> str:
    joined = "\x1f".join(parts).encode("utf-8", "replace")
    return hashlib.sha256(joined).hexdigest()
