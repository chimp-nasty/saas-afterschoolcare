# Job 08: Cross-cutting review and fix reassessment

Follow AGENTS.md and audit/SHARED.md. Read-only. This job can consolidate a broad audit or reassess a specific proposed fix.

## Cross-cutting mode

- Review findings and coverage from the completed jobs, using current conversation evidence and approved documents if available. If past results are unavailable, state that limitation rather than inventing a completed audit history.
- Follow interactions: identity to host binding to RLS; upload to storage to browser rendering; payment to local transaction to capacity expiry; account deactivation to caches/sessions; email delivery to rollback/retry.
- Look for inconsistent controls across alternate endpoints, duplicated workflows, background tasks and trusted functions. Check whether one component's mitigation assumes a guarantee another component does not provide.
- Consolidate duplicate root causes while retaining distinct impact paths. Re-evaluate severity using actual prerequisites and safeguards. Keep previously reported unresolved issues visible without counting them as new.
- Report remaining unaudited material areas and the highest-value next verification. Do not produce an overall backend clearance from incomplete jobs.

## Fix reassessment mode

- Identify the exact original finding and proposed fix revision. Read the current implementation and relevant tests; do not rely on the agent's completion claim.
- Re-trace the original triggering sequence and adjacent denial, retry, concurrency, rollback and recovery paths. Check alternate call sites and SQL effects.
- Classify the result as still present, partially addressed, no longer evident by static inspection, or runtime-verified within explicit evidence. Static inspection is not test execution; a changed assertion is not proof of repaired behaviour.
- Identify regressions introduced by the fix and missing acceptance criteria. Do not edit the original finding/status during the audit. Any approved documentation update is separate.

## Deliver

Use SHARED.md. Present confirmed findings from Critical to Low, explicit known-item status, separate concerns, advisory disposition and coverage judgement. Summarise root causes and remediation order without inventing a numerical security score. After the terminal summary, follow the finding-document approval workflow.
