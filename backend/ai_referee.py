"""AI referee: judges a freelancer deliverable against the deal brief.

Primary path: free, no-key Pollinations text API
    GET https://text.pollinations.ai/<urlencoded prompt>
which is asked to return a strict JSON verdict.

Pluggable override: set AI_API_URL (and optionally AI_API_KEY) to point at
any OpenAI-compatible endpoint, e.g.:
    AI_API_URL=https://api.openai.com
    AI_API_KEY=sk-...
The module then POSTs to {AI_API_URL}/v1/chat/completions with model from
AI_MODEL (default "gpt-4o-mini").

Fallback: if the AI call fails for any reason, a transparent local heuristic
runs instead and clearly labels itself as a fallback in the reasons list.

Returns: {"decision": "APPROVE"|"REQUEST_CHANGES", "confidence": 0-100,
          "reasons": [...], "source": "pollinations"|"nebius"|"openai-compatible"|"fallback"}

Nebius mode (for the Nebius x NVIDIA hackathon):
    AI_API_URL=https://api.tokenfactory.nebius.com/v1
    AI_API_KEY=v1....   (Token Factory key, keep in .env, never commit)
    AI_MODEL=nvidia/nemotron-3-super-120b-a12b
The AI referee then runs on an NVIDIA open model served by Nebius.
"""
import json
import os
import re
import urllib.parse

import requests

POLLINATIONS_BASE = "https://text.pollinations.ai/"
TIMEOUT = 45

SYSTEM_PROMPT = (
    "You are an impartial escrow referee. Compare the freelancer's deliverable "
    "against the client's brief and decide whether the payment held in escrow "
    "should be released.\n\n"
    "Respond with ONLY a single JSON object, no markdown fences, no commentary, "
    "in exactly this shape:\n"
    '{"decision": "APPROVE" or "REQUEST_CHANGES", '
    '"confidence": <integer 0-100>, '
    '"reasons": ["<short reason>", ...]}\n\n'
    'Rules: APPROVE only if the deliverable clearly addresses the core '
    "requirements of the brief. REQUEST_CHANGES if anything essential is "
    "missing, vague, or mismatched. Be specific in reasons: cite which brief "
    "requirement is met or unmet."
)


def _parse_verdict(text):
    """Robustly extract the JSON verdict from model output."""
    text = (text or "").strip()
    if not text:
        raise ValueError("empty AI response")
    try:
        return json.loads(text)
    except ValueError:
        pass
    # Strip markdown fences if present
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.S).strip()
    try:
        return json.loads(text)
    except ValueError:
        pass
    # Last resort: grab the first {...} block
    m = re.search(r"\{.*\}", text, re.S)
    if m:
        return json.loads(m.group(0))
    raise ValueError("no JSON object found in AI response")


def _normalize(raw, source):
    decision = str(raw.get("decision", "")).strip().upper()
    if decision not in ("APPROVE", "REQUEST_CHANGES"):
        raise ValueError(f"invalid decision: {raw.get('decision')!r}")
    try:
        confidence = int(raw.get("confidence", 0))
    except (TypeError, ValueError):
        confidence = 0
    confidence = max(0, min(100, confidence))
    reasons = raw.get("reasons") or []
    if isinstance(reasons, str):
        reasons = [reasons]
    reasons = [str(r).strip() for r in reasons if str(r).strip()][:8]
    if not reasons:
        reasons = ["No detailed reasons returned by the model."]
    return {
        "decision": decision,
        "confidence": confidence,
        "reasons": reasons,
        "source": source,
    }


def _call_pollinations(prompt):
    url = POLLINATIONS_BASE + urllib.parse.quote(prompt, safe="")
    r = requests.get(url, timeout=TIMEOUT)
    r.raise_for_status()
    return r.text


def _call_openai_compatible(system, user):
    base = os.environ.get("AI_API_URL", "").rstrip("/")
    key = os.environ.get("AI_API_KEY", "")
    model = os.environ.get("AI_MODEL", "gpt-4o-mini")
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    r = requests.post(
        f"{base}/v1/chat/completions",
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
        },
        headers=headers,
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    message = r.json()["choices"][0]["message"]
    # Reasoning models (e.g. NVIDIA Nemotron served on Nebius Token Factory)
    # may put the answer in reasoning_content and leave content empty.
    return message.get("content") or message.get("reasoning_content") or ""


def _fallback(brief, description, link, error):
    """Transparent local heuristic used only when the AI API is unreachable."""
    stop = {
        "the", "a", "an", "and", "or", "of", "to", "in", "for", "with", "on",
        "is", "are", "be", "this", "that", "it", "as", "by", "from", "at",
        "please", "will", "should", "must", "need", "needs",
    }
    brief_words = {w for w in re.findall(r"[a-z]{3,}", brief.lower()) if w not in stop}
    desc_words = {w for w in re.findall(r"[a-z]{3,}", description.lower()) if w not in stop}
    overlap = brief_words & desc_words
    coverage = len(overlap) / max(1, len(brief_words))
    score = coverage + (0.15 if link else 0) + (0.1 if len(description) > 120 else 0)
    decision = "APPROVE" if score >= 0.45 else "REQUEST_CHANGES"
    confidence = int(max(5, min(95, 30 + coverage * 60)))
    reasons = [
        "[fallback heuristic — the AI API was unreachable, so this verdict "
        f"is keyword-based, not a real AI judgement (error: {error})]",
        f"Brief/deliverable keyword coverage: {coverage:.0%} "
        f"({len(overlap)}/{max(1, len(brief_words))} key terms match).",
    ]
    if link:
        reasons.append("A deliverable link was provided.")
    else:
        reasons.append("No deliverable link was provided.")
    reasons.append(
        "Fallback verdicts are conservative: re-run the AI check once "
        "network access is available for a real judgement."
    )
    return {
        "decision": decision,
        "confidence": confidence,
        "reasons": reasons,
        "source": "fallback",
    }


def judge_deliverable(brief, deliverable_description, deliverable_link=""):
    """Judge a deliverable against the brief. Returns verdict dict."""
    user = (
        f"CLIENT BRIEF:\n{brief}\n\n"
        f"FREELANCER DELIVERABLE DESCRIPTION:\n{deliverable_description}\n\n"
        f"DELIVERABLE LINK: {deliverable_link or '(none provided)'}\n\n"
        "Give your verdict as the JSON object described above."
    )
    try:
        if os.environ.get("AI_API_URL"):
            raw_text = _call_openai_compatible(SYSTEM_PROMPT, user)
            if "nebius" in os.environ.get("AI_API_URL", "").lower():
                source = "nebius"
            else:
                source = "openai-compatible"
        else:
            raw_text = _call_pollinations(SYSTEM_PROMPT + "\n\n" + user)
            source = "pollinations"
        return _normalize(_parse_verdict(raw_text), source)
    except Exception as e:  # network down, bad JSON, bad shape -> fallback
        return _fallback(brief, deliverable_description, deliverable_link, str(e)[:160])
