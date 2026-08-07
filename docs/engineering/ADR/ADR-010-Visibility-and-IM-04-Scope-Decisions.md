# ADR-010: Problem Visibility, Technician Ticket Visibility, and IM-04 Scope

**Status:** ACCEPTED
**Date:** 2026-08-07
**Related:** ADR-009 (Problem Management architecture), [DESIGN_PM-02_PROBLEM_MANAGEMENT.md](../DESIGN_PM-02_PROBLEM_MANAGEMENT.md) §7, [ITSM_ROADMAP.md](../ITSM_ROADMAP.md) P0 item 3

These three decisions were requested twice during the ITSM program (once during PM-02's design, once
during IM-03) and left unanswered both times, blocking PM-03 (Problem Management UI) and further Incident
Management work. They were given explicitly by the repository owner and are recorded here verbatim plus
the technical shape chosen to implement each, so a future session doesn't have to re-derive intent from
chat history.

## Decision 1 — Problem Visibility

**Given:** Requesters cannot access Problem records at all. Technician access follows RBAC. Manager/Admin
access follows permissions.

**Implementation shape chosen:** `get_problem_queryset(user)` in `security/policies.py`, structurally
identical to the existing `get_ticket_queryset(user)`:

| Role | Ticket rule (existing) | Problem rule (this ADR) |
|---|---|---|
| Administrator | all tickets | all problems |
| Manager | department-scoped (`department__in=managed_departments`) | department-scoped, same field |
| Technician | assigned only (`assigned_to=user`) | assigned only, same field — "according to RBAC" is read as "the same RBAC shape already established for Tickets," since `Problem` was built to mirror `Ticket` throughout (ADR-009) |
| Requester | own tickets (`created_by=user`) | **`Problem.objects.none()`** — explicit, unconditional |

## Decision 2 — Technician Ticket Visibility

**Given:** Technicians may view tickets assigned to them, and unassigned tickets within permitted queues.
Purpose: queue-based self-assignment.

**Implementation shape chosen, with a gap flagged rather than silently resolved:** there is no existing
"queue" or "technician's department" concept in the data model. `Department.managers` is a `ManyToMany`
to `User` (how a Manager's department scope is determined) — there is no equivalent
`Department.technicians` or any other field that would let the system determine which "permitted queue"
a given Technician belongs to.

Given the explicit instruction not to redesign models without approval, this ADR does **not** invent a new
field to scope "permitted queues" narrower than "all unassigned tickets." The rule implemented is:

```
Technician sees: Q(assigned_to=user) | Q(assigned_to__isnull=True)
```

i.e., tickets assigned to them, plus every unassigned ticket system-wide — not scoped to a department or
other queue concept, because none exists to scope against. **If department- or queue-scoped visibility is
actually wanted, that requires a new field (e.g. a `Department.technicians` M2M mirroring `managers`) and
is its own follow-up decision**, not assumed here.

## Decision 3 — IM-04 Scope: implement all three

**Given:** build Work Notes, Attachments, and Requester Confirmation, with the requirements listed below.
Implementation shape for each is recorded here since the original request specified behavior, not schema.

### Work Notes
- Requirement: internal technician communication, separate from requester comments, requesters cannot view.
- Shape chosen: new `TicketHistory.EVENT_WORK_NOTE` event type (adding a choice to an existing
  `choices=` list — no migration required, `event_type` has no DB-level check constraint). A new
  `TicketService.add_work_note()` mirrors `add_comment()` but records this event type.
  `TicketDetailView` filters history entries of this type out of what's rendered to any user who lacks
  `service_desk.change_ticket` (the same permission that already gates the Workflow panel) — Requesters
  hold only `view_ticket`/`add_ticket` (per `create_roles.py`), so they never see work notes.

### Attachments
- Requirement: secure uploads, permission controlled, linked to ticket lifecycle.
- Shape chosen: a new `TicketAttachment` model (FK to `Ticket`, `file` `FileField`, `uploaded_by` FK user,
  `uploaded_at` auto timestamp, `description` optional) rather than a single `FileField` on `Ticket` —
  supports multiple files per ticket with individual upload audit metadata, and reuses the already-present
  but previously-unused `TicketHistory.EVENT_ATTACHMENT` event type to record each upload in the ticket's
  audit trail ("linked to ticket lifecycle"). Storage uses the already-configured `MEDIA_ROOT`/`MEDIA_URL`
  (SEC-01) — no new dependency. "Secure" is implemented as: upload/view scoped through the same
  RBAC-scoped ticket queryset as everything else (permission controlled), plus a file size cap and a
  file-extension allowlist (executable/script extensions rejected) — a conservative baseline, not a full
  antivirus/content-scanning pipeline, which was not requested and would need its own decision.

### Requester Confirmation
- Requirement: closure workflow `Resolved → Waiting for requester confirmation → Closed`.
- Shape chosen: new `Ticket` status `awaiting_confirmation`, inserted into `TicketService.STATUS_FLOW`
  between `resolved` and `closed`:
  `resolved → [awaiting_confirmation]`, `awaiting_confirmation → [closed]` (replacing the old
  `resolved → [closed]` direct edge). `TicketService.close_ticket()` now requires
  `status == "awaiting_confirmation"` instead of `"resolved"`. A new business rule lives in
  `TicketService.change_status()` itself (the single real choke point for every transition, including the
  one `close_ticket()` delegates to): the `awaiting_confirmation → closed` transition additionally requires
  the acting user to be the ticket's `created_by` — enforced at the service layer so it can't be bypassed
  through any view that reaches `change_status` directly, not just the dedicated close action.
  `TicketCloseView`'s permission mixin changes from `TicketChangePermissionMixin` (`change_ticket` —
  Technician/Manager/Admin) to `TicketViewPermissionMixin` (`view_ticket`, which Requesters hold), since
  the real gate is now "are you the requester," enforced in the service layer, not "do you have staff
  permissions."
  **Not built, flagged rather than assumed:** a reject/dispute path back to `in_progress` if the requester
  isn't satisfied. The given diagram only shows the confirm-forward path; a rejection path is a distinct
  decision this ADR does not make.

## Consequences

- PM-03 (Problem Management UI) is unblocked by Decision 1 and proceeds next.
- IM-04 requires one migration (`TicketAttachment` model, `Ticket.STATUS_CHOICES` addition — Django
  migrations do track `choices=` changes as a state operation even though no DB constraint changes, so
  `makemigrations` is expected to generate one for the status addition too).
- Decision 2's "all unassigned tickets, unscoped" interpretation should be revisited if it turns out to be
  too broad in practice — flagged in [ROADMAP.md](../ROADMAP.md) as a follow-up, not treated as final.

## Approval

**Status: ACCEPTED.** Given directly by the repository owner. Implementation proceeds per
[ITSM_ROADMAP.md](../ITSM_ROADMAP.md)'s execution order: record (this document) → PM-03 → IM-04.
