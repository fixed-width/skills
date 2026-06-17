---
name: glass-drive
description: Use when driving a native GUI app through the glass MCP tools (glass_start, glass_screenshot, glass_diff, glass_click, glass_drag, glass_a11y_snapshot, glass_wait_*, glass_logs) to build, observe, interact with, or debug it — especially a canvas / game / custom-rendered / no-accessibility app you must verify by pixels, mouse, and stdout logs instead of the accessibility tree.
---

# Driving glass

## Overview

glass drives a GUI app as an external black box. **Verify with cheap text first; spend an
image only to diagnose.** And **never trust a tool's `ok` — confirm every action by an
app-side signal** (a stdout log line, or a `glass_diff` change). A returned `ok` means
"glass sent it," not "the app acted on it": synthetic input can still no-op.

## When to use

- Any task using `glass_start`/`glass_screenshot`/`glass_diff`/`glass_click`/… against an
  x11 or wayland session.
- Especially **canvas / game / custom-rendered / no-a11y apps**, where the accessibility tree
  is absent or partial and verification must go through pixels, the mouse, and logs.

## The loop

```
glass_start  →  glass_wait_stable {include_image:false}  →  act (mouse/keys)
           →  text glass_diff + glass_wait_for_log  →  (image ONLY to diagnose why)
```

This text-first spine carried the overwhelming majority of verification across multi-hour
dogfood runs; image-returning calls were under ~15% of glass calls. Reach for an image only
when a number or log can't tell you *why* something looks wrong.

## Quick reference

| Need | Do this | Not this |
|---|---|---|
| Did something change / land? | `glass_wait_stable {include_image:false}` → text `glass_diff` (read `changed_pct` **and `bbox`**) | full-window `glass_screenshot` |
| Wait for a state | `glass_wait_for_log` / `glass_wait_for_region` / `glass_wait_for_element` | poll with screenshots |
| A line may already be buffered | `glass_wait_for_log {contains:"…", cursor:0}` (or `glass_logs {cursor:0}`) | bare `wait_for_log` — its default is future-only, so it times out on an already-printed line (the timeout result now hints at this) |
| Settle a UI with animation | `glass_wait_stable {stability_region:{…}}` (the part you care about) | whole-window settle (an animated affordance never settles) |
| Read color/shape/position | `glass_screenshot {region:{…}}` (tight crop) | full-window screenshot |
| Address a widget | a11y `#id` if the tree exposes it; **else** `glass_click` at its rendered pixel coords | assume a11y works everywhere |
| Known input sequence | `glass_do [click,type,settle]` + `then:{screenshot}` | many separate round-trips |
| Multi-window | `glass_list_windows` → `glass_select_window {id}` → `glass_window {op:"geometry"}` | guessing which window is active |
| Clipboard | `glass_clipboard_set`/`get` for the plumbing; for app→clipboard, drive the app's Copy action then `glass_clipboard_get` | assuming a key chord delivered |

## Key patterns

- **Confirm by signal, not by `ok`.** Gate each action on its app-side effect: a
  `glass_wait_for_log {contains:"…"}`, or a `glass_diff` delta. An **absent** log line is a
  valid result (it's how you prove a true-negative). `glass_wait_for_log` takes `contains`
  (literal substring, **not** regex); pass `cursor:0` (or thread the previous response's
  cursor) when the line may already be buffered.
- **Read the diff `bbox`, not just `changed_pct`.** A "clean" canvas can show a big
  `changed_pct` that's entirely chrome/selection drift — the `bbox` localizes it (e.g.
  `h:21` at `y:1` = toolbar row only ⇒ canvas unchanged), and its start matches the action's
  coordinate within ~1px, so `bbox.x` alone is a precise positional assertion. Prefer a
  same-session before/after baseline over a cross-task one — baselines don't persist across
  `glass_start`.
- **Probe a11y once, early; fall back to pixels.** Call `glass_a11y_snapshot` first. If it
  errors or is partial (a custom canvas, or some secondary windows), address those parts by
  mouse + pixel coords + logs. Don't build a plan on semantic addressing before you've
  confirmed it works for the part you need.
- **Address interactive elements by `name`, not `role`.** Some toolkits (Jetpack Compose)
  split an element's accessible *name*, its actable *role*, and its clickability across
  separate parent/child/sibling nodes — so a `glass_wait_for_element {name, role:"Button"}`
  filter misses a button that `{name}` alone finds (the name sits on one node, the Button
  role and `focusable` state on its parent/sibling). Filter by `name` (plus a state like
  `enabled`), not `role`, unless a snapshot confirms the toolkit merges name + role onto one
  node.
- **Mouse clicks are the most reliable input; build verification around mouse-driven widgets.**
  Keyboard, pointer-modifiers, and drags can land or not depending on the app — always confirm
  by signal (see Caveats).
- **High-contrast colors when a diff must be tight.** A dark stroke on a dark theme barely
  diffs; a saturated color diffs much stronger.
- **Pace drags with `duration_ms`** (≥ 200) so frame-based UIs sample the path; a too-short
  drag can yield too few points to register a stroke.

## Common mistakes

- **Trusting a returned `ok`.** Confirm by log or diff.
- **Full-window screenshot to check one corner.** The biggest avoidable token sink — use a
  region crop or, better, a text diff/log.
- **Polling with screenshots** instead of a `glass_wait_for_*` (they return text and time out
  softly to `{matched:false}`).
- **Trusting `glass_doctor`'s a11y check as proof the app has a tree** — it means the registry
  is up, not that the target app publishes one. Probe with a real snapshot.
- **Reading `glass_wait_stable {settled:true}` as "the app is idle."** A tiny continuous
  animation repaints every frame yet can read as settled (its per-frame change is below the
  whole-window threshold). Scope with `stability_region`.

## Caveats to verify around

General and app-agnostic — confirm per app rather than assuming:

- **Confirm input landed — `ok` only means glass sent it.** Keyboard and pointer-modifier
  delivery especially can depend on focus and the app's own input handling, so an input can
  no-op while glass returns `ok`. Gate every input on an app-side signal; if one never lands
  after a retry or two, report it as *unverifiable via glass for this app* rather than assuming
  the app failed. Disambiguate with a known-good input (a mouse click that still logs): clicks
  working while keys don't ⇒ it's input delivery, not the app.
- **`settled:true` ≠ idle.** A small continuous animation can read as settled. Scope the wait
  to the region you care about with `stability_region`, and assert an affordance IS animating
  with `glass_wait_for_region {until:"changes"}`.
- **a11y coverage varies by toolkit — probe, don't assume.** Custom-painted canvases have no
  semantics, and some toolkits don't expose secondary/child windows in the tree. Where a11y is
  blind, drive by pixels + behavioral (log) checks.
- **Re-select after a window may have closed.** After an action that can close the active
  window, `glass_list_windows` + `glass_select_window` a live one before the next op.
