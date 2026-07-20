---
name: glass-drive
description: Use when driving, automating, or debugging a running native GUI application — desktop (X11, Wayland, Windows, macOS), an Android emulator, or an iOS Simulator — through the glass MCP tools (glass_start, glass_screenshot, glass_diff, glass_click, glass_type, glass_a11y_snapshot, glass_click_element, glass_set_value, glass_scroll_to_element, glass_wait_*, glass_logs, glass_gesture). Use it whenever a task means launching an app and interacting with its real UI, even if the user never says the word "glass" — filling in a form or preferences dialog end to end, clicking or typing into widgets, checking that a button becomes enabled or a field updates after an action, walking through a screen to read its accessibility labels, reaching a row in a long virtualized list, performing a pinch or multi-touch gesture, observing a second window without stealing focus, confirming a UI change actually landed, or cutting the token cost of screenshot-heavy verification. Use it too when glass itself seems to misbehave — a click returns ok but nothing happens in the app, an accessibility snapshot is empty or reports "accessibility unavailable", a wait_for_* times out. Covers a11y-rich apps (forms, tables, menus, dialogs) driven by the accessibility tree, and canvas / game / custom-rendered apps verified by pixels, mouse, and stdout logs. Not for browser or web automation (Playwright, Puppeteer, Selenium), and not for editing glass's own source code.
---

# Driving glass

## Overview

glass drives a GUI app as an external black box. Two habits carry most of the value:

**Verify with cheap text first; spend an image only to diagnose.** The observe tools
(`glass_diff`, the `glass_wait_for_*` family, `glass_wait_stable {include_image:false}`)
return text, so routine checks between screenshots cost no vision tokens.

**Never trust a returned `ok` — confirm by an app-side signal.** An `ok` means "glass sent
it," not "the app acted on it": synthetic input can no-op while the call still succeeds.
Gate each action on a stdout log line, a `glass_diff` delta, or an a11y state change.

Which oracle is primary depends on the app. For an **a11y-rich app** (forms, tables, menus,
dialogs) the accessibility tree is primary and pixels are the diagnostic fallback; for a
**canvas / game** it's the reverse. Probe once, early, to learn which — `glass_doctor` for
what's available, then a `glass_a11y_snapshot`.

## When to use

- Any task using `glass_start` / `glass_screenshot` / `glass_diff` / `glass_click` / … against
  an X11, Wayland, Windows, macOS, Android, or iOS session.
- **a11y-rich apps** (GTK/Qt/WinUI/AppKit business apps), where the accessibility tree is the
  primary oracle. See **Driving a11y-rich apps**.
- Especially **canvas / game / custom-rendered / no-a11y apps**, where the tree is absent or
  partial and verification must go through pixels, the mouse, and logs.
- **Touch backends** (Android, iOS) — the same text-first loop, but touch has no hover and no
  modifier plane, so don't port desktop pointer idioms blindly. See **Platform differences**.

## Decide about the accessibility tree at launch

On **Linux**, the a11y tools work only if you launched the app with `glass_start {a11y:true}`,
which spawns a private AT-SPI bus. It is opt-in because it costs extra processes, and there is
no fallback to an ambient bus. Without it:

- `glass_a11y_snapshot` / `glass_a11y_marks` / `glass_wait_for_element` / `glass_scroll_to_element`
  fail with `accessibility unavailable: … relaunch the app with a11y:true`.
- `glass_click_element` / `glass_set_value` fail with `no accessibility snapshot yet`.

Recovering costs a `glass_stop` and a relaunch, so if the app might expose a tree, pass
`a11y:true` up front — an unused private bus is cheaper than a restart mid-task.

Everywhere else the flag is ignored: the tree is there when the app publishes one. On **iOS**
it additionally requires `idb_companion`; without it the backend degrades to observe-only
(capture, logs, and clipboard keep working) and the a11y and input tools return `Unsupported`.

## The loop

```
glass_start {a11y:true on Linux if you may want the tree}
   →  glass_a11y_snapshot  (probe: does this app expose a tree at all?)
   →  act  (glass_click_element / glass_click / glass_type / glass_do)
   →  confirm by text  (glass_wait_for_log | glass_diff | glass_wait_for_element)
   →  image ONLY to diagnose why something looks wrong
```

Reach for an image when a number or a log line can't tell you *why* — not to check whether
something happened.

## Quick reference

| Need | Do this | Not this |
|---|---|---|
| Did something change / land? | `glass_wait_stable {include_image:false}` → `glass_diff` (read `changed_pct` **and `bbox`**) | full-window `glass_screenshot` |
| Did *only* this part change? | `glass_diff {name, region}` — scopes the compare, and `bbox` becomes region-relative | whole-frame diff, then squinting at a union `bbox` |
| Wait for a state | `glass_wait_for_element` / `glass_wait_for_region` / `glass_wait_for_log` | poll with screenshots |
| A log line may already be buffered | `glass_wait_for_log {contains:"…", cursor:0}` | bare `wait_for_log` — it matches only *future* lines, so it times out on a line already printed |
| Settle a UI with animation | `glass_wait_stable {stability_region:{…}}` | whole-window settle (an animated affordance never settles) |
| Read color / shape / position | `glass_screenshot {region:{…}}` — vision cost scales with pixel *area* | a full-window shot of a large window to inspect one corner |
| Read a widget's current value | `glass_wait_for_element {name, value_contains}` or `{condition:"checked"}` | `glass_a11y_snapshot` — its lines carry role/name/states, **not** values |
| Address a widget | a11y `#id` if the tree exposes it; **else** `glass_click` at its rendered pixel coords | assume a11y works everywhere |
| Pick an element visually | `glass_a11y_marks` — numbered boxes + legend, and it caches the snapshot so `#id`s work after | eyeballing an unannotated screenshot |
| Reach an off-screen row | `glass_scroll_to_element {name, x, y}` — aim `x,y` at the scrollable container | hand-rolling a scroll + re-snapshot loop |
| Re-read the tree after acting | `glass_click_element {id, return:"snapshot"}` | a separate `glass_a11y_snapshot` round-trip |
| Observe a *second* window | `window_id` on `glass_screenshot` / `glass_wait_stable` / `glass_wait_for_region` | `glass_select_window` (it retargets every later op) |
| Known input sequence | `glass_do [click,type,settle]` + `then:{screenshot}` | many separate round-trips |
| Extract an app's text | `glass_do` `ctrl+a` then `ctrl+c`, then `glass_clipboard_get` | OCR a screenshot |
| Pinch / rotate / 2-finger gesture | `glass_gesture {pointers:[{from,to},…], duration_ms}` (Android + agent) | a "2-pointer drag" (no such thing) |
| Coordinates for an action | a11y `bounds`, or a prior `glass_diff` `bbox` (both window-relative device px) | eyeballing a scaled screenshot thumbnail |
| Multi-window | `glass_list_windows` → `glass_select_window {id}` → `glass_window {op:"geometry"}` | guessing which window is active |

## Key patterns

- **Confirm by signal, not by `ok`.** An **absent** log line is a valid result — it's how you
  prove a true negative. `glass_wait_for_log` takes `contains` (a literal substring, **not** a
  regex); pass `cursor:0`, or thread the previous response's `cursor`, when the line may
  already be buffered. Read `glass_logs {cursor:0}` once to learn the app's log vocabulary before
  you guess a substring — an app that echoes a right-click prints `button=3`, not `right`.
- **Read the diff `bbox`, not just `changed_pct`.** A "clean" canvas can show a big
  `changed_pct` that is entirely chrome or selection drift — the `bbox` localizes it (`h:21` at
  `y:1` = toolbar row only ⇒ canvas unchanged). Its start matches the action's coordinate within
  ~1px, so `bbox.x` alone is a precise positional assertion. Baselines don't survive a
  `glass_start`, so prefer a same-session before/after pair.
- **Probe a11y once, early; fall back to pixels.** If `glass_a11y_snapshot` errors or comes back
  partial (a custom canvas, or some secondary windows), address those parts by mouse + pixel
  coords + logs. Don't build a plan on semantic addressing before you've confirmed it works for
  the part you need.
- **Select by `name`, not `role` — in every selector.** Toolkits routinely split an element's
  accessible *name*, its actable *role*, and its clickability across separate parent/child/sibling
  nodes: Jetpack Compose puts the name and the `Button` role on different nodes, and a
  `GtkListView` row's name lives on its inner `Label`, not the `ListItem`. So a `role` filter
  quietly excludes the very node that carries the name. This bites hardest on the searching tools —
  `glass_scroll_to_element {name:"Row 060", role:"ListItem"}` sweeps the whole list and returns a
  confident `{matched:false}`, which reads exactly like "no such row." Filter by `name` (plus a
  state like `enabled`, or `value_contains`) and add `role` only once a snapshot shows the toolkit
  merges them onto one node.
- **Let glass run the loops you'd otherwise hand-roll.** `glass_scroll_to_element` replaces
  scroll-then-snapshot polling; `return:"snapshot"` folds the re-read into the action that
  invalidated it; `window_id` observes another window without retargeting; `glass_do` collapses a
  known input sequence into one call. Each removes a round-trip *and* a chance to act on a stale
  tree.
- **Re-snapshot after anything that reflows layout.** a11y `#id`s and bounds go stale after a
  scroll, a window switch, or a keyboard/layout shift; clicking a cached id lands on the wrong
  target. `return:"snapshot"` is the cheap way to stay current. glass will tell you when it
  notices — `element #N changed since the snapshot; re-snapshot`.
- **Take action coordinates from a11y `bounds` or a prior `diff` `bbox`.** A screenshot renders at
  a different scale than window-relative device px, so eyeballed coordinates miss.
- **Mouse clicks are the most reliable input.** Keyboard, pointer-modifiers, and drags can land or
  not depending on the app. When you need a known-good input to disambiguate, use a click.
- **Pace drags with `duration_ms`** (≥ 200) so frame-based UIs sample the path; too short a drag
  yields too few points to register a stroke.
- **High-contrast colors when a diff must be tight.** A dark stroke on a dark theme barely diffs;
  a saturated color diffs much stronger.
- **Ask `glass_doctor` what's available — never probe `PATH`.** glass resolves its external tools
  by its own order (an env override, then `PATH`, then its data dir, then next to the glass
  binary), and it version-gates some of them. So `which sway` finding nothing doesn't mean
  Wayland is unsupported, and finding something doesn't mean it qualifies.

## Driving a11y-rich apps (forms, tables, menus, dialogs)

Here the tree is the primary oracle and pixels are the fallback — the inverse of the canvas case.
A `glass_a11y_snapshot` resolves most verification (row content, selection, gating state, sort
order) with zero pixels; reach for a screenshot only where a11y is genuinely blind — a
transient's own text, a popover-visibility question, a render bug.

- **A snapshot tells you what an element *is*, not what it holds.** Each line is
  `#id Role "name" (x,y wxh) [states]` — role, name, bounds, and states like `checked` or `enabled`,
  but **not** a text field's text or a spin button's number. To read a value back, ask
  `glass_wait_for_element {name:"Field", value_contains:"glass"}` or
  `{name:"Active", condition:"checked"}`, which return the matched element and double as the
  confirm-by-signal step. Besides `checked`/`unchecked`, `condition` takes `appears`/`disappears`,
  `enabled`/`disabled`, `selected`/`unselected`, `expanded`/`collapsed`, `focused`, and
  `visible`/`hidden` — so most gating/selection/disclosure states are a single wait, not a snapshot
  scan. Note that a combo box's *name* is its current selection, so a dropdown is the one case where
  the snapshot does show you the value.
- **`glass_click_element` handles popovers for you.** A dropdown or context menu is often its own
  window whose origin the element's bounds don't reflect; glass detects that and routes the click
  into it. If it can't map the popover to a window it says so —
  `element #N is inside a popover glass could not map to a window; select_window it and click by
  coordinate` — and only then do you `glass_select_window` the popover and `glass_click` at a
  local coord (`item bounds − owning-menu-node bounds`). Don't reach for that workaround first.
- **`glass_set_value` covers more than text.** It sets a text field, a number for a spin button or
  slider, a boolean for a switch/checkbox/toggle (any of `true/false`, `on/off`, `1/0`, `yes/no` —
  idempotent), and a dropdown by option label (it opens the popup and picks the option). Each error
  it can return names its own remedy: `AxElementNotEditable` (the a11y projection exposes no writable
  value — focus with `glass_click`, then `glass_type`/`glass_key`), `AxValueNotApplied` (the write
  reported success but the value didn't change — a read-only projection; use keystrokes),
  `AxValueNotBoolean` (a non-boolean sent to a switch/checkbox), and `AxElementChanged` (re-snapshot).
- **Virtualized lists expose only the realized rows.** A `GtkColumnView` / `LazyColumn` /
  `VirtualizingStackPanel` publishes just the on-screen rows (e.g. 17 of 500) — **never infer the
  total from the node count**; read it from a status label or a log. To reach an off-screen row,
  `glass_scroll_to_element {name}`: it sweeps one direction, reverses if needed, and returns a
  soft `{matched:false}` rather than erroring. **Aim its `x`,`y` at the scrollable container** —
  the default anchor is the window *center*, and if that lands on some other widget the wheel
  goes nowhere, the tree never changes, and you get a fast, confident `{matched:false}` that reads
  exactly like "no such row." Two further limits: a container holding a *continuously repainting*
  node (a clock, a progress bar) never looks "unchanged", so the sweep runs to `timeout_ms`
  instead of reversing (pass the `direction` the target actually lies in); and a very long list
  may need a larger `timeout_ms` or `step`.
- **After a re-sort, scroll to a known edge before reading order.** A column-header sort keeps a
  scroll-anchor row at its viewport position rather than resetting to the top, so the first
  *realized* rows are the anchor's neighborhood, not the front of the sorted list — a working sort
  can look broken. Scroll to the top (or bottom) first, then read the order.
- **A one-shot transient can be too fast to observe.** If an element appears once and auto-dismisses
  (a delete toast), set up a scoped `glass_wait_for_region` *before* triggering it. When the toast
  lives in another window, observe with `window_id` rather than `glass_select_window` — a window
  switch can cost more round-trips than the element lives. If it still misses, report the element as
  unobservable via glass rather than assuming nothing happened. (A *continuously* repeating
  affordance — a blinking dot — has no deadline and is catchable on some cycle.)

## Platform differences

The loop and the patterns are the same everywhere; these are the places a backend will surprise you.

| | Linux (X11/Wayland) | Windows | macOS | Android | iOS |
|---|---|---|---|---|---|
| a11y tree | needs `a11y:true` at start | ✓ | ✓ | ✓ (companion sharpens Compose) | needs `idb_companion` |
| hover (`glass_move`) | ✓ | ✓ | ✓ | `ok`, does nothing | does nothing (`Unsupported` without companion) |
| pointer `modifiers` | ✓ | ✓ | ✓ | silently dropped | silently dropped |
| `glass_gesture` | – | – | – | ✓ on-device agent only | – |
| window resize / move | ✓ | ✓ | ✓ | – (fullscreen) | – (fullscreen) |
| clipboard | ✓ | ✓ | ✓, except a hardened-runtime app | on-device agent only | ✓ (Simulator's own) |

- **Touch backends have no hover and no modifier plane.** A desktop hover or modifier idiom ported
  to Android/iOS fails *quietly* — `glass_move` and `modifiers` are accepted and dropped. Build
  touch verification around taps.
- **Multi-touch is `glass_gesture`, Android only, and needs the on-device agent.** N simultaneous
  straight `from→to` segments over a shared `duration_ms` — pinch (two pointers toward/apart),
  rotate (two on an arc), two-finger swipe (two parallel). Everywhere else it refuses rather than
  degrading to a single pointer, and a `glass_drag` cannot express it. Confirm by the app's own
  signal (a `zoom:` log, a diff), and **calibrate the finger spread** — too wide overshoots a clamp
  (a max-zoom ceiling) in one gesture.
- **An iOS switch toggles on a swipe, not a tap.** A `UISwitch` does not actuate on a center tap
  (the underlying tooling's own tap no-ops too) — it flips on a short swipe across the control. Use
  `glass_set_value` for iOS toggles: it reads the current state and does the trailing-edge swipe for
  you (idempotent), where a pixel `glass_click` on the switch would silently do nothing.

## Common mistakes

- **Trusting a returned `ok`.** Confirm by log, diff, or a11y state.
- **Full-window screenshot to check one corner.** The biggest avoidable token sink — use a region
  crop, or better a text diff or log. The rule is *pixel area*, not "always crop": on a small window
  one frame can answer several questions more cheaply than several crops.
- **Polling with screenshots** instead of a `glass_wait_for_*` (they return text and time out
  softly to `{matched:false}`, so branch on that rather than retrying blindly).
- **Calling an a11y tool on Linux without having started the app with `a11y:true`** — and reading
  the resulting error as "this app has no tree."
- **Trusting `glass_doctor`'s a11y check as proof the app has a tree.** It means the registry is
  up, not that the target app publishes one. Probe with a real snapshot.
- **Reading `glass_wait_stable {settled:true}` as "the app is idle."** A tiny continuous animation
  repaints every frame yet can read as settled, because its per-frame change is below the
  whole-window threshold. Scope it with `stability_region`.
- **Concluding a backend is unavailable because its tool isn't on `PATH`.** Ask `glass_doctor`.
- **Inferring a list's total row count from the a11y node count.** Virtualized lists expose only
  their realized rows.

## Caveats to verify around

General and app-agnostic — confirm per app rather than assuming:

- **Confirm input landed.** Keyboard and pointer-modifier delivery can depend on focus and the
  app's own input handling, so an input can no-op while glass returns `ok`. If one never lands
  after a retry or two, report it as *unverifiable via glass for this app* rather than assuming the
  app failed. Disambiguate with a known-good input: if clicks log and keys don't, it's input
  delivery, not the app.
- **`settled:true` ≠ idle.** Scope the wait with `stability_region`, and assert an affordance IS
  animating with `glass_wait_for_region {until:"changes"}`.
- **a11y coverage varies by toolkit — probe, don't assume.** Custom-painted canvases have no
  semantics, and some toolkits don't expose secondary or child windows. Where a11y is blind, drive
  by pixels plus behavioral (log) checks.
- **Re-select after a window may have closed.** After an action that can close the active window,
  `glass_list_windows` and `glass_select_window` a live one before the next op.
