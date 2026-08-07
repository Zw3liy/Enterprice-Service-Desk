# Engineering Workflow

## Permanent AI / Engineer Workflow

Every engineering session in this repository — AI-assisted or human — follows this sequence. It exists so
that no session skips repository assessment and jumps straight to editing code from assumptions or
half-remembered chat context. Documentation is the source of truth (see
[SESSION_STATE.md](SESSION_STATE.md)); this sequence is how a session actually consumes it.

```
Repository Assessment
        |
        v
Read SESSION_STATE.md
        |
        v
Read ROADMAP.md
        |
        v
Read ADRs (docs/engineering/ADR/)
        |
        v
Inspect git status
        |
        v
Design
        |
        v
Approval
        |
        v
Implementation
        |
        v
Testing
        |
        v
Documentation Update
        |
        v
Commit
        |
        v
Update SESSION_STATE.md
        |
        v
Wait for Push Approval
```

Notes on specific steps:

- **Read SESSION_STATE.md / ROADMAP.md / ADRs first, always** — even if the task seems small or
  self-contained. `SESSION_STATE.md` is what tells you whether the working tree is already clean, whether
  there are unpushed commits, and what the current milestone actually is; skipping it risks redoing or
  contradicting work already in flight.
- **Inspect git status** before any design work — confirm branch, confirm clean tree, confirm nothing
  from a prior session is stranded uncommitted.
- **Design → Approval** happens *before* implementation for anything beyond a trivial, already-approved
  fix. Don't write code on the strength of a design nobody has signed off on.
- **Testing** means the checks listed in `SESSION_STATE.md` under "Required Checks Before Commit"
  (`manage.py check`, `manage.py test`, migration/import/URL/template verification) — not a subset.
- **Documentation Update** happens in the *same* change as the code, not as a follow-up someday. If the
  change alters architecture, add or update an ADR in the same pass.
- **Commit** happens only after the above, and only with explicit approval for that specific commit.
- **Update SESSION_STATE.md** is not optional cleanup — an out-of-date handoff document actively misleads
  the next session. Do this before ending the session, not "next time."
- **Wait for Push Approval** — the workflow ends here by default. See "Pushes require explicit approval"
  below; nothing in this sequence authorizes a push on its own, including reaching the end of it.

## Commits are local by default

Creating a commit in this repository only writes it to the local branch. It does **not** publish it
anywhere by itself.

## Pushes require explicit approval

Nothing in this repository should push to `origin` — or any remote — without an explicit, current
instruction to do so. A prior approval to commit is not an approval to push; a prior approval to push once
does not carry forward to later commits. Ask each time.

## Automatic push hooks are intentionally disabled

This repository previously had a `post-commit` hook at `.git/hooks/post-commit` containing:

```sh
#!/bin/sh
git push origin HEAD
```

This caused **every commit to be pushed to `origin` automatically**, silently, with no way for a commit
to stay local — discovered when commit `7180078` ("FIX-01: Restore Service Desk views and recover
application startup") was pushed despite an explicit "Do NOT push" instruction on that task.

As of this milestone, the hook is disabled:

- Renamed from `.git/hooks/post-commit` to `.git/hooks/post-commit.disabled`. Git looks up hooks by exact
  filename, so a file named `post-commit.disabled` is never invoked — this is the operative disabling
  mechanism.
- The original content is preserved unmodified in `post-commit.disabled` — nothing was deleted. Restore it
  by renaming it back to `post-commit` if automatic pushing is ever wanted again (not recommended given the
  workflow rule above).
- An attempt was also made to strip the file's executable bit as a second safeguard. On this filesystem
  (Windows via Git Bash / OneDrive-backed mount), `chmod` does not persist a non-executable mode — `ls -la`
  and `stat` continue to report `0755` regardless. This is a filesystem limitation, not a failed action, and
  it doesn't weaken the disable: the filename-based lookup above is what actually stops Git from running it.

**How to re-check this is still disabled:** confirm no file named exactly `post-commit` exists in
`.git/hooks/`:
```
ls .git/hooks/post-commit 2>&1   # should report "No such file or directory"
```

If a future session finds `.git/hooks/post-commit` present again, treat it as a workflow violation to flag
before committing anything, not something to silently work around.
