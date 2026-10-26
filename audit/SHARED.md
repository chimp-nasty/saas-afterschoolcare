# Rules shared by every audit job

Read AGENTS.md first. It governs authorisation and repository-specific review rules. These prompts add audit structure, not permission to modify anything.

## Execution contract

Start with: **This audit is read-only. I will not write to any files or change database state.**

Use static inspection by default. Do not read .env files or variants, expose secrets, start the app, install dependencies, generate assets, run formatters, run database-backed tests, query databases, migrate, seed, replay events or contact external services with side effects. Avoid commands that create caches, logs or temporary files. Use read-only Git operations with optional index writes disabled where applicable. Do not spawn agents unless separately authorised.

You may consult public primary-source documentation and vulnerability advisories when needed. Do not upload private repository code or secrets to external services. Do not call a lockfile version an installed or deployed version without evidence. Dependency scanners and exploit testing require separate authorisation.

Assess the code independently. Comments, plans and tests describe claims; verify the enforcement. Do not assume that a missing service check is a defect when SQL already enforces the invariant. Do not label unfinished UI or an unused partial feature as an exposed vulnerability without a reachable path. Business reliability defects affecting money, sensitive data or care operations belong in scope, but label them accurately.

## Repeatable scope and evidence

Default: full-job assessment of the current working tree, including relevant untracked files. Establish branch/HEAD, dirty state and inspected scope without reading environment files. A changed-code review requires an explicit comparison base; state it and trace necessary unchanged callers and SQL. Do not silently restrict a broad job to the diff.

For each relevant flow, identify the actor, entry point, trusted/untrusted input, dependencies, service, repository, SQL rules and external effects. Investigate reads and writes, success and denial paths, rollback and recovery. Record exact path:line references in the terminal result. Redact secret values even when encountered outside environment files.

Review existing approved findings before reporting duplicates. Treat user statements that an issue is closed as workflow context, not proof of a verified code fix. Report known items separately with their current evidence: re-observed, not reassessed, fix present but unverified, or verified within stated limits. Never rewrite finding documents during a read-only run.

## What qualifies as a finding

A confirmed finding needs a concrete attacker or failure condition, a reachable execution path, a failed intended control/invariant, and practical impact supported by the implementation. Static proof can confirm a defect without executing an exploit. State whether evidence is static, user-reported, or runtime-reproduced; do not conflate them.

Separate these categories:

- **Confirmed security vulnerability:** an actual trust-boundary failure or abuse path.
- **Confirmed correctness/reliability defect:** demonstrated failure affecting the protected workflow; do not call every outage an attack.
- **Concern/open question:** plausible risk with an unproven prerequisite or missing evidence. State what would confirm or refute it; do not include it in confirmed severity totals.
- **Test gap/design observation:** coverage or maintainability advice without a demonstrated vulnerability. Keep it outside vulnerability totals.

Do not require a contrived compromise of an unrelated component to manufacture exploitability. A database-only control gap can be reported as such, with its access prerequisites; do not describe it as a remotely exploitable API flaw without an API path.

## Severity rubric

Grade severity from demonstrated impact plus realistic exploitability/occurrence, explaining both in each finding. This is a project rubric, not a calculated CVSS score.

| Severity | Meaning | Example anchors (conditional on evidence) |
|---|---|---|
| Critical | Catastrophic impact through a readily usable path with minimal prerequisites; broad compromise or severe, widespread irreversible harm | Unauthenticated server execution exposing the whole system; practical platform-wide takeover or unrestricted bulk access to sensitive family/child data |
| High | Major confidentiality, integrity, money or operational harm through a realistic path; may require a normal account, repeatable race or ordinary provider outage | Cross-tenant sensitive-data access; account takeover; unauthorised refunds; duplicate charges; paid care bookings lost without a recovery outcome |
| Medium | Material but bounded harm, or major harm requiring substantial demonstrated constraints | Limited sensitive-data disclosure; restricted privilege bypass; bounded persistent resource exhaustion; integrity defects requiring uncommon but credible conditions |
| Low | Small, constrained practical impact with limited reach and meaningful prerequisites | Narrow information leakage or a defence-in-depth control gap where current reachable paths prevent the larger claimed harm |

Explain the actor/access needed, endpoint exposure, affected data/actions, tenant/family reach, repeatability, user interaction, timing, money/care consequences, recoverability and existing mitigations. Use the actual minimum prerequisites. A race is not automatically unlikely; a platform administrator already authorised to perform an action has not bypassed authorisation by doing it.

Critical needs an explicit explanation of why High is insufficient. High/Critical findings normally warrant an advisory release block for affected functionality. Medium needs a prioritised remediation decision; Low can usually be scheduled. Time pressure and business priority do not change the technical severity. Confidence and evidence completeness are separate from severity: if a prerequisite is unverified, describe the issue as a concern rather than asserting a more severe confirmed exploit.

Do not mechanically multiply numeric likelihood and impact or count missing tests as vulnerabilities. Do not downgrade a serious demonstrated defect because there is a workaround, a log message or a future plan. Do not inflate severity from the sensitivity of the domain alone.

## Required terminal output

1. Job ID, date, scope, reviewed revision/dirty-state context and verification method.
2. Confirmed findings ordered Critical, High, Medium, Low. Label each security or reliability. For each include:
   - **[Severity] Title** and exact repository path:line references.
   - **Evidence:** actor/failure condition, realistic sequence, relevant enforcement and existing safeguards.
   - **Impact:** affected parties and practical harm; explain the severity using the rubric.
   - **Remediation:** smallest effective change, tradeoffs, regression scenarios and acceptance criteria.
3. Previously reported items and whether/how they were reassessed. Avoid duplicate counts.
4. Concerns, open questions and test gaps, kept separate.
5. Coverage: important flows/files examined; tests inspected versus executed; omissions; runtime assumptions. Summarise each job checklist area as inspected, not applicable (with reason), or not inspected. Do not mark a job fully covered if material checks remain.
6. Advisory disposition and coverage judgement using README.md. If no new confirmed findings, say so without implying safety or clearing unassessed known findings.
7. After presenting the findings, ask whether the user would like a finding document created. Explain briefly that AGENTS.md requires approval before that documentation write. If approval already explicitly covers this exact document after presentation, do not request it again.

Keep the result actionable and proportionate. No file writes occur until a separately authorised documentation task or implementation task.
