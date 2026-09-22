"""Jev billing gate — ช่วยตัดสินใจออกบิลด้วย TypeSafe System One.

หลักการ (ตาม docs.typesafe.ai):
- Jev ไม่ใช่ text-generation: ส่ง state + typed questions ได้คำตอบ typed + probabilities + confidence
- ถามหลายข้อใน 1 request (parallel): Choice + Noul + Score
- โค้ดเป็นคนตัดสินใจสุดท้าย (deterministic policy) ไม่ใช่โมเดล

ใช้กับออเดอร์แบบ Shopee/Lazada ในโปรเจกต์นี้:
  billingName, billingAddr, billingAddr2 (ตำบล), billingAddr3 (จังหวัด),
  billingAddr4 (อำเภอ), billingAddr5 (รหัสไปรษณีย์), taxCode, billingPhone

Env:
  TYPESAFE_API_KEY  (ขอที่ https://console.typesafe.ai/)
  TYPESAFE_MODEL    (default: jev-latest)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

# pip install typesafe-sdk
from typesafe_sdk import Choice, Noul, Score, TypeSafeClient

MODEL = os.getenv("TYPESAFE_MODEL", "jev-latest")

# --- thresholds รวมไว้ที่เดียว เพื่อให้รีวิวง่าย ---
AUTO_ISSUE_MIN_NOUL = 0.80   # address_complete ต้อง >= นี้ถึงออกบิลอัตโนมัติ
REVIEW_MIN_NOUL = 0.50       # ต่ำกว่านี้ = skip/hold ทันที
AUTO_ISSUE_MIN_CONF = 0.60   # confidence ของ Choice ต้อง >= นี้ถึง auto
MAX_STATE_CHARS = 8000       # bound payload ก่อนส่ง (Jev ไม่ควรรับ history ทั้งก้อน)


@dataclass
class BillingDecision:
    action: str  # issue_now | hold_review | skip_invalid
    address_complete: float
    risk_score: float
    confidence: float
    reason: str


def _bounded_state(order: dict[str, Any]) -> dict[str, Any]:
    """ตัด state ให้สั้น ส่งเฉพาะฟิลด์ที่ต้องใช้ตัดสินใจ."""
    keys = [
        "orderNumber", "billingName", "billingAddr", "billingAddr2",
        "billingAddr3", "billingAddr4", "billingAddr5",
        "taxCode", "billingPhone", "customerName",
        "ประเภทใบกำกับภาษี", "หมายเหตุจากผู้ซื้อ", "บันทึก",
    ]
    state = {k: str(order.get(k, ""))[:1000] for k in keys}
    # bound รวม
    blob = str(state)
    if len(blob) > MAX_STATE_CHARS:
        # ตัดที่อยู่ยาวก่อนเป็นอันดับแรก
        state["billingAddr"] = state["billingAddr"][:2000]
    return state


def decide_bill(order: dict[str, Any]) -> BillingDecision:
    """ถาม Jev 3 ข้อใน 1 call แล้วรวมผลด้วย policy ในโค้ด."""
    state = _bounded_state(order)

    with TypeSafeClient() as client:
        resp = client.system_one(
            state=state,
            questions={
                "billing_action": Choice(
                    instructions=(
                        "ออเดอร์นี้ควรออกบิลเลย, พักไว้ให้คนรีวิว, หรือข้ามเพราะข้อมูลใช้ไม่ได้? "
                        "issue_now = ที่อยู่+ภาษีครบพร้อมออกบิล, "
                        "hold_review = ไม่แน่ใจต้องให้คนดู, "
                        "skip_invalid = ที่อยู่/ภาษีผิดชัดเจนออกบิลไม่ได้"
                    ),
                    criteria={
                        "issue_now": None,
                        "hold_review": None,
                        "skip_invalid": None,
                    },
                ),
                "address_complete": Noul(
                    instructions=(
                        "ที่อยู่สำหรับออกใบกำกับภาษีครบถ้วนหรือไม่? "
                        "ต้องมีชื่อผู้รับ, ที่อยู่, ตำบล/แขวง, อำเภอ/เขต, จังหวัด, รหัสไปรษณีย์"
                    ),
                ),
                "billing_risk": Score(
                    instructions="ความเสี่ยงถ้าออกบิลผิด (ที่อยู่มั่ว, ภาษีผิด, ต้อง reprint)?",
                    criteria=["เสี่ยงต่ำ", "เสี่ยงกลาง", "เสี่ยงสูง"],
                ),
            },
            model=MODEL,
        )

    choice = resp.choices["billing_action"]
    noul = resp.nouls["address_complete"]
    score = resp.scores["billing_risk"]

    action = str(choice.choice)
    conf = float(choice.confidence or 0.0)
    addr_p = float(noul.noul)
    risk = float(score.score)  # 0=ต่ำ .. 2=สูง

    # --- deterministic policy: โค้ดคุม ไม่ใช่โมเดล ---
    if action == "skip_invalid" or addr_p < REVIEW_MIN_NOUL:
        final = "skip_invalid"
        reason = f"skip: addr_p={addr_p:.2f} action={action}"
    elif action == "issue_now" and addr_p >= AUTO_ISSUE_MIN_NOUL and conf >= AUTO_ISSUE_MIN_CONF and risk < 1.0:
        final = "issue_now"
        reason = f"auto: addr_p={addr_p:.2f} conf={conf:.2f} risk={risk:.2f}"
    else:
        final = "hold_review"
        reason = f"review: action={action} addr_p={addr_p:.2f} conf={conf:.2f} risk={risk:.2f}"

    return BillingDecision(
        action=final,
        address_complete=addr_p,
        risk_score=risk,
        confidence=conf,
        reason=reason,
    )


if __name__ == "__main__":
    # ทดสอบแบบไม่ใช้ key จริงไม่ได้ — ต้อง export TYPESAFE_API_KEY ก่อน
    demo = {
        "orderNumber": "123456",
        "billingName": "บจก. ตัวอย่าง",
        "billingAddr": "123 ถนนสุขุมวิท",
        "billingAddr2": "คลองเตย",
        "billingAddr3": "กรุงเทพมหานคร",
        "billingAddr4": "คลองเตย",
        "billingAddr5": "10110",
        "taxCode": "0105557001234",
        "billingPhone": "02-123-4567",
        "ประเภทใบกำกับภาษี": "เต็มรูป",
    }
    if not os.getenv("TYPESAFE_API_KEY"):
        print("ตั้ง TYPESAFE_API_KEY ก่อนรัน (ขอที่ https://console.typesafe.ai/)")
    else:
        print(decide_bill(demo))
