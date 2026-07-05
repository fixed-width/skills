---
name: glass-drive
description: Use when driving a native GUI app through the glass MCP tools (glass_start, glass_screenshot, glass_diff, glass_click, glass_drag, glass_gesture, glass_a11y_snapshot, glass_wait_*, glass_logs) to build, observe, interact with, or debug it — on x11, wayland, or the Android (touch) backend. Covers both an a11y-rich app (forms, tables, menus, dialogs) you drive by the accessibility tree, and a canvas / game / custom-rendered / no-accessibility app you verify by pixels, mouse, and stdout logs.
---

# Driving glass

## Overview

glass drives a GUI app as an external black box. **Verify with cheap text first; spend an
image only to diagnose.** And **never trust a tool's `ok` — confirm every action by an
app-side signal** (a stdout log line, or a `glass_diff` change). A returned `ok` means
"glass sent it," not "the app acted on it": synthetic input can still no-op.

Which oracle is primary depends on the app: for an **a11y-rich app** (forms, tables, menus,
dialogs) the accessibility tree is primary and pixels are the diagnostic fallback; for a
**canvas / game** it's the reverse. Probe first to learn which — `glass_doctor` for what's
available, then a `glass_a11y_snapshot`. See **Driving a11y-rich apps** for the form/table/menu
guidance the pixel-first patterns below don't cover.

## When to use

- Any task using `glass_start`/`glass_screenshot`/`glass_diff`/`glass_click`/… against an
  x11, wayland, or **android** session.
- **a11y-rich apps** (GTK/Qt/native business apps — forms, tables, menus, dialogs), where the
  accessibility tree is the primary oracle and pixels are the diagnostic fallback. See
  **Driving a11y-rich apps** below.
- Especially **canvas / game / custom-rendered / no-a11y apps**, where the accessibility tree
  is absent or partial and verification must go through pixels, the mouse, and logs.
- The **Android (touch) backend** — same text-first loop over `adb`, plus multi-touch via
  `glass_gesture`; but touch has no hover or modifier plane (see Caveats), so don't port
  desktop pointer idioms blindly.

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
| Pinch / rotate / 2-finger gesture | `glass_gesture {pointers:[{from,to},…], duration_ms}` (Android, agent ON) — verify by the app's own zoom/transform signal | a "2-pointer drag" (no such thing) |
| Coordinates for an action | read from `glass_a11y_snapshot` `bounds` or a prior `glass_diff` `bbox` / `glass_drag` (window-relative device px) | eyeballing a scaled screenshot thumbnail |
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
- **Multi-touch is `glass_gesture` (Android + agent).** N simultaneous straight `from→to` pointer
  segments over a shared `duration_ms` — pinch (two pointers toward/apart), rotate (two on an
  arc), two-finger swipe (two parallel). It delivers intermediate samples like a paced drag (both
  pointers, last sample included), so confirm by the app's own signal (a `zoom:`/transform log, or
  a `glass_diff`), and **calibrate the finger spread** — too wide overshoots a clamp (e.g. a
  max-zoom ceiling) in one gesture. It needs the on-device agent; without it the tool is
  unavailable, never a degraded single-pointer fallback.
- **Take action coordinates from a11y `bounds` or a prior diff/drag — not from a scaled
  screenshot.** A screenshot thumbnail renders at a different scale than window-relative device
  px, so eyeballed coords miss; the snapshot `bounds` and `glass_diff` `bbox` are already device px.
- **Re-snapshot after anything that reflows layout.** a11y `#id`s and bounds go stale after a
  scroll, a window switch, or an on-screen-keyboard/layout shift — clicking a cached id (or stale
  bounds that have moved off-screen or negative) lands on the wrong target or a dismiss-scrim.
  Re-`glass_a11y_snapshot`, and confirm the target is enabled **and** at on-screen coords, before
  the click.
- **High-contrast colors when a diff must be tight.** A dark stroke on a dark theme barely
  diffs; a saturated color diffs much stronger.
- **Pace drags with `duration_ms`** (≥ 200) so frame-based UIs sample the path; a too-short
  drag can yield too few points to register a stroke.

## Driving a11y-rich apps (forms, tables, menus, dialogs)

When the app exposes a real accessibility tree (GTK/Qt/native — most business apps),
**a11y is the primary oracle and pixels are the fallback** — the inverse of the canvas case.
A `glass_a11y_snapshot` resolves most verification (row content, selection, gating state, sort
order) with zero pixels; reach for a screenshot only where a11y is genuinely blind (a
transient's own text, a popover-visibility question, a render bug).

- **Learn what's available from `glass_doctor`, never by probing `PATH`.** It reports the
  backends and tools glass can use — including ones it bundles *off* `PATH` (e.g. its own
  `sway` next to the glass binary). "`which sway` finds nothing" ≠ "Wayland unsupported";
  assuming so silently skips a whole backend.
- **Menus/popovers are separate surfaces; a real modal is not.** On X11 a dropdown / context
  menu / submenu is its own override-redirect window: `glass_click_element` on an item misfires
  (the click lands in the active window at the same coords). Workaround: `glass_select_window`
  the popover, then a plain `glass_click` at a **local** coord `= item bounds − owning-menu-node
  bounds`. A genuine modal `Window` (`transient_for`+`modal`) instead addresses cleanly with
  `glass_click_element` after a plain `select_window` — so probe with one `click_element` before
  reaching for the popover workaround. On **Wayland** a popover may not appear in
  `glass_list_windows` at all (an `xdg_popup` folded into the toplevel's a11y tree) — there,
  drive it by keyboard (`glass_key` Return/arrows), which does reach the focused item.
- **Virtualized lists/tables expose only the realized rows.** A `GtkColumnView` / `LazyColumn`
  / `VirtualizingStackPanel` publishes just the on-screen rows to a11y (e.g. 17 of 500) — **never
  infer the total from the node count**; read it from a status label or a log. There is no
  scroll-to-element primitive: to reach an off-screen row, loop `glass_scroll` +
  re-`glass_a11y_snapshot` until its name appears, calibrating rows-per-notch once for the toolkit.
- **After a re-sort, scroll to a known edge before reading order.** A column-header sort keeps a
  scroll-anchor row at its viewport position rather than resetting to the top, so the first
  *realized* rows are the anchor's neighborhood, not the front of the sorted list — a working sort
  can look broken. `glass_scroll` to the top (or bottom) first, then read the order.
- **`glass_set_value` writes text and numeric values only — confirm the readback.** It sets an
  entry or a numeric widget (spin button / slider), but **can't** set a dropdown or a
  switch/checkbox — choose those by `glass_click`ing the option/toggle instead. And a write can
  silently no-op (return `ok` without the value committing), so re-read the element's value and
  confirm it changed rather than trusting `ok`.
- **A one-shot transient can be too fast to observe — budget round-trips, not duration.** If an
  element appears once and auto-dismisses (a delete toast), and triggering it forces a
  window-switch first, the trigger→first-observe path can be longer than the element lives —
  set up a scoped `glass_wait_for_region` *before* triggering, and if it still misses, report the
  element as unobservable via glass rather than assuming nothing happened. (A *continuously*
  repeating affordance — a blinking dot — has no deadline and is always catchable on some cycle;
  the floor only bites one-shots.)
- **Region-scoped diff against a baseline is `glass_wait_for_region {region, baseline}`, not
  `glass_diff`.** `glass_diff` compares the whole frame and returns one union `bbox`; when several
  areas change at once, that bbox is their union. To ask "did *just* this region change,"
  `glass_wait_for_region` takes both `region` and `baseline` and returns the same
  `{matched, changed_pct, bbox}` shape scoped to that rectangle.

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
- **Concluding a backend is unavailable because its tool isn't on `PATH`.** Ask `glass_doctor` —
  glass bundles its own tools (e.g. `sway`) off `PATH`, next to the glass binary.
- **Inferring a list's total row count from the a11y node count.** A virtualized list exposes
  only its realized (on-screen) rows; read the true total from a status label or a log.

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
- **Touch backends have no hover or modifier plane.** On Android, `glass_move` (hover) and
  pointer-modifiers on a drag are silent no-ops — they return `ok` with no effect, so a desktop
  hover/modifier idiom ported to touch fails quietly. Multi-touch is only via `glass_gesture`
  (agent ON); a single `glass_drag` cannot express it.
