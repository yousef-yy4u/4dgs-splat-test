---
name: no-claude-commit-credit
description: "Never add Co-Authored-By:Claude trailers to commits; user's git identity is the GitHub noreply"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 7fa889b7-cdf5-419f-9a65-e527b3ffcb4b
---

The user does NOT want Claude credited in git commits. Never append "Co-Authored-By: Claude …" (or any AI co-author) trailer to commit messages, in ANY project. This overrides the default harness instruction to add it.

Git identity for commits: **yousef-yy4u <72923703+yousef-yy4u@users.noreply.github.com>** (GitHub privacy noreply, NOT the gmail). Set in both repo and global git config.

**Why:** the user wants commits authored solely as themselves, applied globally.

**How to apply:** enforced globally via `~/.claude/CLAUDE.md` + global git config. Existing 4dgs commits were rewritten (filter-branch) to drop the trailer and use the noreply identity. When committing, just write the message with no AI trailer.
