# Job 05: Business workflows, concurrency and integrity

Follow AGENTS.md and audit/SHARED.md. Read-only. Include reliability failures that compromise money, data or care operations, and label them separately from security abuse.

## Check

- Booking creation/resumption/cancellation/reinstatement, capacity and uniqueness; attendance and pickup checks; staff shifts; medical review resets; document approval/retention and any other implemented stateful workflow.
- Required preconditions and allowed transitions in services and SQL. Check side doors through alternate endpoints, bulk changes, privileged functions and cross-owner foreign keys.
- Transaction ownership, nested transactional methods, commits before/after external effects, rollback semantics, RLS restoration and response construction after commit.
- Lock ordering, check-then-write races, partial updates, retry handling, concurrent duplicate requests and idempotency scope. Trace constraints and triggers before recommending application-level duplication.
- Mixed/partial group outcomes, deletion/deactivation, edits that invalidate existing approvals, stale reads/caches, and how failures recover after a crash.
- Location timezone, date-only versus timestamp semantics, expiry/cutoff windows and clock sources. Check boundaries around session start, midnight and relevant DST changes.

## Adversarial scenarios

Two families take the last place; same request arrives twice; cancellation races payment; pickup permission changes between check and collection; an approved medical/document record changes; an external action succeeds before local rollback; a process restarts halfway through a workflow.

## Deliver

Use SHARED.md. Give a concrete request/interleaving or failure sequence for race claims. State whether the database already serialises or rejects it. Include the recovery outcome and regression acceptance criteria, not just the happy-path fix.
