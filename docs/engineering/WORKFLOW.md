# Git Workflow

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
