"""openjev name matcher — เอา D:/openjev มาช่วยเลือกชื่อลูกค้าใน dropdown.

ที่มา: D:/openjev/openjev เป็น local NLI cross-encoder
  premise + hypothesis -> [contradiction, entailment, neutral]
  มี API: predict / predict_hypotheses / rerank / grade (ดู modeling_openjev.py)

ใช้ตรงไหนของบอท:
  แทน/เสริม `select_cus_name_from_lis` ที่ปัจจุบันใช้ substring + regex
  ตัดคำนำหน้า (บริษัท/บจก./จำกัด) ซึ่งเปราะกับชื่อย่อ สะกดต่าง สาขาย่อย
  เปลี่ยนเป็น: premise = ชื่อ+สาขาที่ต้องการ, candidates = cus_found_names_list
  เลือก entailment สูงสุด ถ้าต่ำกว่า threshold -> fallback logic เดิม / add_new_customer

ออกแบบให้ fail-safe:
  - lazy import torch/transformers เฉพาะตอนใช้ (บอทยังรันได้ถ้ายังไม่ลง)
  - ถ้าโหลดโมเดลไม่ได้ -> fallback วิธีเดิม 100%
  - ไม่ผ่าน MCP (import ตรงเร็วกว่า เหมาะกับ Selenium loop)
"""

from __future__ import annotations

import os
import re
import sys
from typing import Optional

OPENJEV_DIR = r"D:\openjev\openjev"
# checkpoint แนะนำ: ตัวเล็กสุดก่อน (เร็วสุด) — weights 0.8B โหลดไว้แล้ว (~1.6GB)
# ส่วน 4B-v2 มี model.safetensors 8.6GB (ต้องมี GPU, CPU ช้ามาก)
DEFAULT_CHECKPOINT = os.getenv("OPENJEV_PATH", OPENJEV_DIR)
DEFAULT_SUBFOLDER = os.getenv("OPENJEV_SUBFOLDER", "qwen3.5-0.8b-nli-v2s-long")

ENTAIL_THRESHOLD = float(os.getenv("OPENJEV_ENTAIL_THRESHOLD", "0.60"))
OPENJEV_ENABLED = os.getenv("OPENJEV_ENABLED", "1") == "1"

_SHARED_MATCHER: OpenJevNameMatcher | None = None


def get_shared_matcher() -> OpenJevNameMatcher | None:
    """คืน matcher ตัวเดียวทั้ง process (โหลดโมเดลครั้งเดียว ~30วิครั้งแรก).

    คืน None ถ้าปิดด้วย OPENJEV_ENABLED=0 (บอทใช้ logic เดิม 100%).
    ตัว model จริงยัง lazy-load ตอนใช้ครั้งแรก ไม่ได้โหลดตอน import.
    """
    global _SHARED_MATCHER
    if not OPENJEV_ENABLED:
        return None
    if _SHARED_MATCHER is None:
        _SHARED_MATCHER = OpenJevNameMatcher()
    return _SHARED_MATCHER

_PREFIX_RE = re.compile(r"^(บริษัท|บจก\.?|หจก\.?|หสม\.?|ห้างหุ้นส่วนจำกัด|ห้างหุ้นส่วนสามัญ)\s*")
_SUFFIX_RE = re.compile(r"จำกัด(\s*มหาชน)?$")


def normalize_thai_company(name: str) -> str:
    name = _PREFIX_RE.sub("", name or "")
    name = _SUFFIX_RE.sub("", name)
    return name.replace(" ", "").replace("\n", "").strip()


class OpenJevNameMatcher:
    def __init__(self, path: str = DEFAULT_CHECKPOINT, subfolder: str | None = DEFAULT_SUBFOLDER):
        self.path = path
        self.subfolder = subfolder
        self._model = None
        self._load_error: Optional[str] = None

    def _load(self):
        if self._model is not None or self._load_error is not None:
            return self._model
        try:
            if OPENJEV_DIR not in sys.path:
                sys.path.insert(0, OPENJEV_DIR)
            from modeling_openjev import OpenJevCrossEncoder  # lazy: ต้องมี torch+transformers

            self._model = OpenJevCrossEncoder(self.path, subfolder=self.subfolder)
        except Exception as err:  # ตั้งใจกว้าง: โหลดไม่ได้ = fallback เงียบ
            self._load_error = str(err)
            self._model = None
        return self._model

    @property
    def available(self) -> bool:
        return self._load() is not None

    @property
    def load_error(self) -> Optional[str]:
        self._load()
        return self._load_error

    def rerank_candidates(self, premise: str, candidates: list[str]) -> tuple[int, float, list[float]]:
        """คืน (best_idx, entail_prob, entail_probs ทั้งหมด). ถ้าโมเดลไม่พร้อม -> raise."""
        model = self._load()
        if model is None:
            raise RuntimeError(f"openjev unavailable: {self._load_error}")
        hypotheses = [f"The correct customer is: {c}" for c in candidates]
        probs = model.predict_hypotheses(premise, hypotheses)  # [[con, ent, neu], ...]
        entails = [float(row[1]) for row in probs]
        best = max(range(len(entails)), key=lambda i: entails[i])
        return best, entails[best], entails


def pick_customer_index(
    desire_name: str,
    candidates: list[str],
    branch_num: str = "",
    is_branched: bool = False,
    has_branch_code: bool = False,
    matcher: Optional[OpenJevNameMatcher] = None,
) -> tuple[int, str]:
    """เลือก index ของชื่อลูกค้า คืน (idx, via).

    via = 'substring' | 'openjev' | 'none'
    นโยบาย (จากผลเทสต์จริง: openjev 0.8B ภาษาไทยยังแม่นไม่พอแซง exact match):
    1. substring ก่อน — เจอตรงตัวตัวเดียวจบเลย (เร็ว + แม่นสุด)
    2. openjev เป็นตัวช่วยเฉพาะเคสกำกวม: ไม่เจอเลย หรือเจอหลายตัว
    3. ไม่เจอเลย -> (-1, 'none') แล้ว caller ไป add_new_customer ต่อ
    """
    norm_desire = normalize_thai_company(desire_name)
    norm_cands = [normalize_thai_company(re.search(r"[^-]-(.*)", c).group(1) if re.search(r"[^-]-(.*)", c) else c)
                  for c in candidates]

    def branch_ok(i: int) -> bool:
        if is_branched and has_branch_code and branch_num:
            return branch_num in candidates[i]
        return True

    sub_hits = [i for i, name in enumerate(norm_cands)
                if norm_desire and norm_desire in name and branch_ok(i)]
    if len(sub_hits) == 1:
        return sub_hits[0], "substring"

    # กำกวม (0 หรือ >1 ตัว): ให้ openjev ช่วย rerank
    pool = sub_hits if sub_hits else list(range(len(candidates)))
    if matcher is not None and matcher.available and norm_desire:
        try:
            premise = f"Customer needed: {desire_name.strip()}"
            if branch_num:
                premise += f", branch {branch_num}"
            sub_cands = [candidates[i] for i in pool]
            best_rel, ent, _ = matcher.rerank_candidates(premise, sub_cands)
            if ent >= ENTAIL_THRESHOLD and branch_ok(pool[best_rel]):
                return pool[best_rel], "openjev"
        except Exception:
            pass

    if sub_hits:
        return sub_hits[0], "substring"  # กำกวมแต่ openjev ไม่มั่นใจ -> ตัวแรกเหมือนเดิม
    return -1, "none"
