
## Branch discipline
Codex must only work on the branch explicitly named in the task prompt.
Before editing, run:
git branch --show-current

If the current branch does not match the requested branch, stop and report.

Do not create or use codex/* branches unless explicitly requested.
Preferred workflow:
1. User creates a named branch locally.
2. User pushes it.
3. Codex works only on that branch.
4. PR targets the stated base branch.
