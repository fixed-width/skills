---
name: terse-comments
description: Use when comments read like prose — multi-sentence justifications, a sentence restating the one before, comments longer than the code they guard. Use when a codebase feels over-commented but not wrong, when reviewing a diff whose comments argue rather than inform, or before writing a comment longer than one sentence. Any language, config and build files included.
---

# Terse comments

## Overview

A comment carries **one fact the reader cannot get from the code, in one sentence.**

One fact is the rule. The sentence count is a consequence, not a target to punctuate toward.

Prose comments are usually true; they bury the fact in argument until readers stop reading comments at all.

## The recipe

Three kinds earn more. Nothing else does.

| Kind | What it does |
|---|---|
| **Hazard** | Names the wrong edit someone already made — "do not simplify back to a substring match; it matched inside unrelated words." |
| **External fact** | A platform behaviour, upstream bug or format quirk not derivable from this codebase, what it breaks, and where to verify it. |
| **API doc** | The doc comment on a public item — docstring, `///`, `/** */` — what it does, its parameters, its return. |

## Checking a comment

Split at every `.` `;` `:` `—` and `, and` — one sentence is not exempt. Of every piece after the one carrying the fact, any yes and it goes:

- Restates the piece before it at greater length?
- Defends the choice against an objection the code does not invite?
- Explains a decision with no consequence either way?
- Addressed to a reviewer, "chosen over X because…", when X was never plausible?

## The edit

**Cut the argument, keep the fact; do not delete.** Losing the fact is worse than the padding.

```rust
// Before — the fact, then a sentence defending it:
// A missing version is recorded, not fatal. No check asserts on it, so aborting
// would discard the whole report.

// NOT an edit — one full stop became a colon:
// A missing version is recorded, not fatal: no check asserts on it, so aborting
// would discard the whole report.

// After:
// A missing version is recorded, not fatal — no check asserts on it.
```

## Verifying a sweep

The diff must contain only comment lines. Prove it — `MARKER` is the language's comment prefixes, plus any block continuation (` * `):

```bash
git diff -U0 | rg '^[+-]' | rg -v '^[+-]{3}' | rg -v '^[+-]\s*(MARKER)' | rg -v '^[+-]\s*$'
```

Empty, or you changed code. Score by words removed — pipe the `-` and `+` sides to `wc -w` separately — never by comment-line count. Near-parity means you repunctuated.

## Common mistakes

- **Repunctuating instead of rewriting.** A colon in place of a full stop keeps every word it was hiding.
- **Cutting a hazard for its length.** Length is not the signal; naming a trap is.
- **Cutting the fact, or the whole comment.** If you cannot restate the point in one sentence, leave it as it stands.
- **Sweeping comments and code together.** Comments alone, so the diff proves it.
- **Trusting praise.** Reviewers reward thorough comments; "explains why" and "worth its length" differ.
