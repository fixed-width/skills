---
name: terse-comments
description: Use when comments read like prose — multi-sentence justifications, a sentence restating the one before, comments longer than the code they guard. Use when a codebase feels over-commented but not wrong, when reviewing a diff whose comments argue rather than inform, or before writing a comment longer than one sentence. Any language, config and build files included.
---

# Terse comments

## Overview

A comment carries **one fact the reader cannot get from the code, in one sentence.**

Prose comments are usually true; they bury that fact in argument until readers stop expecting comments to be worth reading.

## The recipe

Three kinds earn more. Nothing else does.

| Kind | What it does |
|---|---|
| **Hazard** | Names the wrong edit someone already made — "do not simplify back to a substring match; it matched inside unrelated words." The instruction is the point. |
| **External fact** | A platform behaviour, upstream bug or format quirk not derivable from this codebase, and where to verify it. |
| **API doc** | The doc comment on a public item — docstring, `///`, `/** */` — what it does, its parameters, its return. |

## Checking a comment

Of every sentence after the first — any yes, it goes:

- Restates the sentence before it at greater length?
- Defends the choice against an objection the code does not invite?
- Explains a decision with no consequence either way?
- Addressed to a reviewer, "chosen over X because…", when X was never plausible?

## The edit

**Rewrite to one sentence; do not delete.** Losing the fact is worse than the padding.

```rust
// Before — the fact, then two sentences defending it:
// A missing version is recorded, not fatal. No check asserts on it — the report carries
// it so a reader can tell which build ran — so aborting would throw away every check's
// evidence over a missing label.

// After — same fact, no argument:
// A missing version is recorded, not fatal: no check asserts on it, so aborting would
// throw away every check's evidence over a missing label.
```

## Verifying a sweep

The diff must contain only comment lines. Prove it — `MARKER` is the language's comment prefixes, plus any block continuation (` * `):

```bash
git diff -U0 | rg '^[+-]' | rg -v '^[+-]{3}' | rg -v '^[+-]\s*(MARKER)' | rg -v '^[+-]\s*$'
```

Empty, or you changed code. Do not score by comment-line count — a file can net zero while both its comments shrink; use the `+`/`-` delta.

## Common mistakes

- **Cutting a hazard for its length.** Length is not the signal; naming a trap is.
- **Cutting the fact with the padding.** If you cannot restate the point in one sentence, leave it.
- **Sweeping comments and code together.** Comments alone, so the diff proves it.
- **Trusting praise.** Reviewers reward thorough comments; "explains why" and "worth its length" differ.
