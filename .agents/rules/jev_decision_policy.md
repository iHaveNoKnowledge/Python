# Jev Usage Policy

Always leverage `jev` CLI for calibrated probabilistic decisions, independent output verification, and large-scale triaging/ranking per `AGENTS.md`.

## Mandatory Triggers:
1. **Output Verification**: Verify code/drafts against stated rules and constraints using `jev yes` or `jev ask`.
2. **Ambiguity & Triage**: When classifying error logs, classifying items, or choosing between multiple non-trivial alternatives.
3. **Semantic Pre-checks**: When gating actions with confidence thresholds (e.g. read-only ~0.6, destructive ~0.9).
