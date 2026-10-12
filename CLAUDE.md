# Instructions for Claude

General rules (ask before deploy/AWS/git, no-indent commands) live in `~/.claude/CLAUDE.md` and apply to all projects.

## Project context

- [PLAN.md](PLAN.md) is the roadmap and decision log. Read it first, and keep its checkboxes and "Current focus" line updated.
- Lambdas use the Python standard library only (`urllib`, plus `boto3` from the runtime). Local scripts in `scripts/` use `requests` (python.org Python on macOS fails SSL with `urllib`).
