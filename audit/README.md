# Repeatable backend security audits

These are reusable audit jobs, not saved audit results or implementation authorisation. Each job can run independently against the current code. Run the full sequence for a broad assessment; rerun individual jobs after relevant changes or incidents.

## How to run

Ask an agent, for example:

> Run audit/03-authorisation-and-isolation.md. Read AGENTS.md and audit/SHARED.md first. Perform the job against the current working tree, follow affected callers and database enforcement, and present the result in the terminal. This is read-only: do not write files or change database state.

For a targeted change:

> Run audit/05-workflows-and-concurrency.md in change-review mode against <explicit base commit or branch>. Include relevant working-tree and untracked changes, trace their impact into unchanged code, and state coverage limits. Follow AGENTS.md and audit/SHARED.md. No file writes or database changes.

For a full review:

> Run audit jobs 00 through 08 sequentially, following AGENTS.md and audit/SHARED.md. Report each job's findings and coverage in the terminal, then continue. Do not write reports, run modifying checks, or change database state. Finish with the cross-cutting assessment and ask whether I want a finding document created.

Do not interpret a job invocation as permission to implement recommendations, run database-backed tests, or spawn other agents. A job can span sessions; explicitly state unfinished coverage rather than silently truncating it.

## Jobs

| Job | Focus | Useful rerun triggers |
|---|---|---|
| [00](00-surface-and-trust-map.md) | Surface, identities, assets and trust boundaries | New domain, integration, hosting model or broad review |
| [01](01-request-boundary.md) | HTTP exposure, middleware and request handling | Routes, proxies, middleware, cookies or API hosting changes |
| [02](02-identity-and-sessions.md) | Credentials, tokens, login and session lifecycle | Authentication, invitations, password resets or kiosk pairing changes |
| [03](03-authorisation-and-isolation.md) | Permissions, ownership, RLS and SQL privileges | Roles, permission grants, schema or new data access paths |
| [04](04-input-files-and-output.md) | Injection, uploads, URLs and content safety | Forms, file handling, storage, templates or outbound URL changes |
| [05](05-workflows-and-concurrency.md) | State transitions, races and integrity | Booking rules, capacity, attendance, pickup, medical or transaction changes |
| [06](06-integrations-and-recovery.md) | Provider trust, webhooks, retries and recovery | Stripe, email, storage or background work changes and outages |
| [07](07-data-abuse-and-deployment.md) | Sensitive data, resource abuse, dependencies and infrastructure | Logging, caches, retention, dependencies or deployment changes |
| [08](08-cross-cutting-and-retest.md) | Interactions, consolidated risk and fix reassessment | Full review completion, incident follow-up or proposed fixes |

Start with 00 for a first full audit, then 01 through 07 and finish with 08. On individual reruns, rebuild the relevant part of the map rather than requiring a saved report. Inspect approved documents in docs/codex-findings/ for context, but recheck their claims against current code.

## What a result means

Every run uses the [shared evidence, severity and reporting rules](SHARED.md). Confirmed findings are listed from Critical to Low. Concerns, questions and test gaps are separate and do not inflate the vulnerability count.

Report two independent judgements:

- **Disposition:** Blocked by confirmed Critical/High findings; findings require prioritisation (Medium/Low only); or no confirmed findings in the reviewed scope. Add known unresolved findings separately so a clean rerun does not conceal them. These are advisory conclusions, not deployment approval.
- **Coverage:** Complete for the declared job scope, partial, or blocked, with the important omissions. Static coverage never means runtime verification.

Do not assign a percentage security score, letter grade or overall claim that the backend is safe. A narrow audit with no findings is not stronger evidence than a broad audit that finds and explains a real problem. Compare reruns using the same scope, evidence and unresolved findings, not raw finding counts.

## Saving results

Audit runs remain read-only. Present the completed findings in the terminal first, then ask whether the user wants a document in docs/codex-findings/. Create it only after explicit approval for that document, as a separate documentation task. Do not automatically create logs, inventories, reports, caches or status files under audit/ or elsewhere.
