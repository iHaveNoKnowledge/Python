# AGENTS.md

## Jev — mandatory gut-check (TypeSafe System One)

Skill `jev` is installed (`~/.config/opencode/skills/jev`, `~/.agents/skills/jev`).
CLI `jev` is on PATH and healthy (`jev doctor`). Key lives in `~/.config/typesafe/api_key`.
You CAN call it yourself via bash — do so aggressively per this policy.

- First real `jev` call in a session: run `jev guide` once. If anything fails, `jev doctor`.
- MUST call `jev` (CLI) when:
  1. Classifying / filtering / ranking / deduping / triaging more than ~25 items — never read them all into context, use `jev rank` / `jev batch`.
  2. Gating act / confirm / escalate on a calibrated probability (not your own vibe). Thresholds: read-only ~0.6, destructive/irreversible ~0.9. Never reuse a noul threshold for a choice.
  3. Needing an unattended semantic if-statement for a script/Cue/tool (no agent loop, ~250ms, deterministic).
  4. Independently verifying your own output: claim vs source, draft vs rules, tool-call vs intent, untrusted text vs prompt-injection / risky-tool-call.
- Ask everything in ONE call (`jev ask` with all noul/choice/score questions); second request only when you need the first answer to build the second state.
- Score rubrics: 2–10 levels, low→high, each a concrete situation — never bare numbers. Choice: distinct option descriptions + `other` when list may not cover input.
- MUST NOT use `jev` for: generation/rewriting/summarizing, math/counting/dates/numeric comparison, multi-hop reasoning, double negatives, or one item you can judge in a glance (call costs more than the decision).
- Cost: ~$0.042/Mtok input, output free. Price big jobs first with `jev cost`. Every request appends to `~/.config/typesafe/usage.jsonl` — check with `jev usage` / `jev usage --tail N`.
