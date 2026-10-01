---
name: jev
description: "Calibrated, typed decisions from TypeSafe's Jev model through the `jev` CLI: a yes/no probability (noul), a pick-one classification with per-option probabilities and confidence (choice), or a position on a rubric you define (score). ~250 ms, $0.042 per million input tokens, same input gives the same answer. Use when a judgment REPEATS over many items you should not read into context (classify, filter, rank, dedupe, triage hundreds of notes, emails, transcript segments, log lines, RSS items, findings, PRs); when you need a CALIBRATED probability rather than your own vibe before acting; when a script or Cue needs a semantic if-statement that runs unattended; or to independently VERIFY your own output (does the source support this claim, does the draft break a stated rule, does this untrusted text carry an instruction aimed at an agent, is this tool call risky). Triggers: 'jev', 'typesafe', 'gut check', 'calibrated', 'second opinion', 'classify these', 'score these', 'rank these', 'filter these', 'which of these', 'triage', 'rerank', 'guardrail', 'prompt injection check', 'is this a ...', 'how severe', 'which team/category/bucket'. NOT for generation, math, counting, date arithmetic, multi-hop reasoning, or one small item you can judge in a glance."
metadata:
  short-description: Calibrated yes/no, pick-one and rubric-score decisions via the jev CLI
  cost: one shell call, ~250 ms and under $0.0001 per request; rank/batch cost cents per thousand items
  applies-when: the decision repeats over many items, must be a calibrated probability, runs unattended in a tool or cron job, or checks your own output with an independent model
  do-not-use-when: generating or rewriting text, arithmetic, counting, dates, chained reasoning, or a single item you can judge yourself faster than a shell call
  fallback: judge it yourself; use grep or a regex for exact-match questions
---

# Jev: Calibrated Decisions for Agents

Jev is TypeSafe's "System One" model. It takes a **state** (text or JSON) and typed **questions**, and returns typed answers with calibrated probabilities.

- CLI is on PATH as `jev` and healthy (`jev doctor`).
- Always run `jev guide` on first call in a session.
- Use `jev ask`, `jev yes`, `jev pick`, `jev rate`, `jev rank`, `jev batch` to classify, verify, triage, and filter.
