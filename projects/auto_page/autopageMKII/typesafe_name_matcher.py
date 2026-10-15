"""TypeSafe-backed customer-name matcher for autopageMKII (stdlib only, fail-safe).

Replaces/backs `openjev_name_matcher.py`'s local 1.6 GB NLI rerank with a TypeSafe
`choice` judgment: no torch, no 30 s model load, works wherever TYPESAFE_API_KEY is set.

Policy (code owns workflow, model supplies the semantic judgment):
  1. substring/exact rule first (fast + deterministic, same normalization as openjev matcher),
  2. TypeSafe `choice` only on ambiguity (0 hits or >1 hit),
  3. any error / low confidence -> legacy fallback (first substring hit, else -1/'none').

Auth: TYPESAFE_API_KEY env var only. Never put the key in this file or the repo.
API: POST https://api.typesafe.ai/v1/systemone with Authorization: Bearer <key>.
"""

from __future__ import annotations

import json
import os
import urllib.request

from openjev_name_matcher import normalize_thai_company

API_URL = "https://api.typesafe.ai/v1/systemone"
MODEL = os.getenv("TYPESAFE_MODEL", "jev-latest")
MIN_CONFIDENCE = float(os.getenv("TYPESAFE_MIN_CONFIDENCE", "0.60"))
TIMEOUT = float(os.getenv("TYPESAFE_TIMEOUT_S", "20"))


def _api_key() -> str:
    return os.environ.get("TYPESAFE_API_KEY", "").strip()


def _choose_via_typesafe(desire_name: str, candidates: list[str], branch_num: str = "") -> tuple[int, float, float]:
    """Return (best_idx, p_best, confidence). Raises on any API/parse problem."""
    key = _api_key()
    if not key:
        raise RuntimeError("TYPESAFE_API_KEY is not set")
    options: dict[str, str | None] = {
        f"opt{i}": f"Dropdown entry: {c}" for i, c in enumerate(candidates)
    }
    options["other"] = "None of the candidates is the requested customer (no match)."
    state = {
        "desire_name": desire_name.strip(),
        "branch_num": (branch_num or "").strip(),
        "candidates": candidates,
    }
    body = {
        "model": MODEL,
        "state": state,
        "questions": {
            "pick": {
                "type": "choice",
                "instructions": (
                    "Which `candidates` entry is the same customer as `desire_name` "
                    "(same company allowing Thai abbreviations, missing prefixes/suffixes like "
                    "บริษัท/บจก./จำกัด, and branch differences)? If `branch_num` is given, the branch "
                    "must also be consistent with the entry. Choose `other` when nothing fits."
                ),
                "criteria": options,
            }
        },
    }
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    ans = payload["answers"]["pick"]
    probs: dict[str, float] = ans.get("probabilities", {})
    best = ans["choice"]
    conf = float(ans.get("confidence", 0.0))
    if best == "other":
        return -1, float(probs.get("other", 0.0)), conf
    idx = int(best.replace("opt", ""))
    return idx, float(probs.get(best, 0.0)), conf


def pick_customer_index(desire_name: str, candidates: list[str], branch_num: str = "") -> tuple[int, str]:
    """Pick dropdown index. Returns (idx, via) with via in substring/typesafe/none.

    Fail-safe: never raises for API problems; falls back to legacy substring behavior.
    """
    norm_desire = normalize_thai_company(desire_name)
    norm_cands = [normalize_thai_company(c) for c in candidates]
    sub_hits = [i for i, n in enumerate(norm_cands) if norm_desire and norm_desire in n]
    if len(sub_hits) == 1:
        return sub_hits[0], "substring"

    pool = sub_hits if sub_hits else list(range(len(candidates)))
    if norm_desire and _api_key():
        try:
            sub_cands = [candidates[i] for i in pool]
            best_rel, _p, conf = _choose_via_typesafe(desire_name, sub_cands, branch_num)
            if best_rel >= 0 and conf >= MIN_CONFIDENCE:
                return pool[best_rel], "typesafe"
        except Exception:
            pass  # fall through to legacy fallback

    if sub_hits:
        return sub_hits[0], "substring"
    return -1, "none"
