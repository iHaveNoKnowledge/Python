# AGENTS.md — autopageMKII (project-local)

## TypeSafe skill (`typesafe-ai`) — installed

Skill source (project-local, installed via `npx skills add typesafe-ai/skills --skill typesafe-ai -a opencode -y`):

- `.agents/skills/typesafe-ai/SKILL.md` — full rules. Read it before building any AI judgment feature.
- Upstream fallback: https://raw.githubusercontent.com/typesafe-ai/skills/main/skills/typesafe-ai/SKILL.md

## TypeSafe rules (apply to this project)

1. **Live docs are source of truth.** Before writing/changing any integration, read the current pages:
   index https://docs.typesafe.ai/llms.txt, then the relevant concept/primitive/API/SDK page as Markdown
   (append `.md` to a docs URL, e.g. https://docs.typesafe.ai/concepts/how-to-build-with-system-one.md).
   Never invent version-dependent API details; if live docs are unreachable, say so and use stdlib HTTP only.
2. **Auth: `TYPESAFE_API_KEY` env var only.** Never commit keys. The key is set at Windows User level
   (`[System.Environment]::GetEnvironmentVariable("TYPESAFE_API_KEY","User")`) — new shells pick it up;
   current shell: `$env:TYPESAFE_API_KEY = [System.Environment]::GetEnvironmentVariable("TYPESAFE_API_KEY","User")`.
   API: `Authorization: Bearer $TYPESAFE_API_KEY` against `https://api.typesafe.ai/v1/systemone`. No key file in repo.
3. **Design judgments per skill:** code owns workflow; model supplies semantic judgment. Keep known rules,
   exact lookups, and execution in code. One narrow judgment per question; ask independent questions together
   in one request. Primitives: `choice` = one of a defined set, `noul` = P(yes) per label, `score` = position
   on ordered concrete levels. Always include a no-match outcome when nothing may fit; use `other`.
4. **This project's fit:** `openjev_name_matcher.py` (local 1.6 GB NLI rerank of Thai customer dropdown names)
   is the canonical TypeSafe candidate — replace/optionally back it with a `choice` + `other` selection over
   `functions/` + `order_display_manager.py` flows. See `typesafe_name_matcher.py` (stdlib-only, fail-safe:
   substring first, TypeSafe rerank on ambiguity, fallback to legacy on any error). Thresholds must be
   evaluated on project data; cookbook numbers are examples, not rules.
5. **Verify:** test representative Thai-name cases end-to-end; on failure inspect exact state/questions/answers
   separately (missing evidence vs model error vs code error vs service failure). Keep credentials server-side.
