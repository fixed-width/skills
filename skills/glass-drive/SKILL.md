---
name: glass-drive
description: Use when driving, automating, or debugging a running native GUI app via the glass MCP tools — desktop (X11, Wayland, Windows, macOS), an Android emulator, or an iOS Simulator. Reach for it when a task means launching an app and working its real UI even if "glass" is never said — filling a form/dialog, clicking or typing widgets, checking a button enables or a field updates, reading accessibility labels, reaching a row in a long virtualized list, a pinch/multi-touch gesture, observing a second window without stealing focus, confirming a change actually landed, or cutting the token cost of screenshot-heavy verification. Also when glass seems to misbehave — a click returns ok but nothing happens, an a11y snapshot is empty or "accessibility unavailable", a wait_for_* times out. Covers a11y-tree-driven apps (forms, tables, menus, dialogs) and canvas/game/no-a11y apps (pixels, mouse, logs). Not for browser/web automation (Playwright, Puppeteer, Selenium) or editing glass's own source.
---

# Driving glass

## Overview

glass drives a GUI app as an external black box. Two habits carry most of the value:

**Verify with cheap text first; spend an image only to diagnose.** `glass_diff`, the
`glass_wait_for_*` family, and `glass_wait_stable {include_image:false}` return text, so routine
checks between screenshots cost no vision tokens. Reach for an image only when a number or a log line
can't tell you *why* something looks wrong — not to check *whether* something happened.

**Never trust a returned `ok` — confirm by an app-side signal.** An `ok` means "glass sent it," not
"the app acted on it": synthetic input can no-op while the call still succeeds. Gate each action on a
stdout log line, a `glass_diff` delta, or an a11y state change.

Which oracle is primary depends on the app: for an **a11y-rich app** (forms, tables, menus, dialogs)
the accessibility tree leads and pixels are the fallback; for a **canvas / game** it's the reverse.
Probe once, early — `glass_doctor` for what's available, then a `glass_a11y_snapshot`.

## When to use

- Any task using `glass_start` / `glass_screenshot` / `glass_diff` / `glass_click` / … against an
  X11, Wayland, Windows, macOS, Android, or iOS session.
- **a11y-rich apps** (GTK/Qt/WinUI/AppKit business apps) — the accessibility tree is the primary
  oracle. See **Driving a11y-rich apps**.
- **canvas / game / custom-rendered / no-a11y apps** — the tree is absent or partial; verify through
  pixels, the mouse, and logs.
- **Touch backends** (Android, iOS) — same text-first loop, but touch has no hover and no modifier
  plane, so don't port desktop pointer idioms blindly. See **Platform differences**.

## Decide about the accessibility tree at launch

On **Linux**, the a11y tools work only if you launched with `glass_start {a11y:true}`, which spawns a
private AT-SPI bus — opt-in (extra processes), with no fallback to an ambient bus. Without it,
`glass_a11y_snapshot` / `glass_a11y_marks` / `glass_wait_for_element` / `glass_scroll_to_element` fail
(`accessibility unavailable: … relaunch the app with a11y:true`), and `glass_click_element` /
`glass_set_value` fail (`no accessibility snapshot yet`). Recovering costs a `glass_stop` + relaunch,
so pass `a11y:true` up front if the app might expose a tree — an unused private bus is cheaper than a
mid-task restart.

Everywhere else the flag is ignored: the tree is there when the app publishes one. On **iOS** it
additionally needs `idb_companion`; without it the backend degrades to observe-only (capture, logs,
clipboard keep working; a11y and input tools return `Unsupported`).

## The loop

```
glass_start {a11y:true on Linux if you may want the tree}
   →  glass_a11y_snapshot  (probe: does this app expose a tree at all?)
   →  act  (glass_click_element / glass_click / glass_type / glass_do)
   →  confirm by text  (glass_wait_for_log | glass_diff | glass_wait_for_element)
   →  image ONLY to diagnose why something looks wrong
```

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

- **Confirm by signal, not by `ok`.** An **absent** log line is a valid result — how you prove a true
  negative. `glass_wait_for_log` takes `contains` (a literal substring, not a regex); pass `cursor:0`
  (or thread the previous `cursor`) when the line may already be buffered. Read `glass_logs
  {cursor:0}` once to learn the app's vocabulary — an app echoing a right-click prints `button=3`,
  not `right`.
- **Read the diff `bbox`, not just `changed_pct`.** A "clean" canvas can show a big `changed_pct`
  that is entirely chrome or selection drift; the `bbox` localizes it (`h:21` at `y:1` = toolbar row
  only ⇒ canvas unchanged), and its start matches the action's coordinate within ~1px, so `bbox.x` is
  a precise positional assertion. Baselines don't survive a `glass_start` — prefer a same-session
  before/after pair.
- **Probe a11y once, early; fall back to pixels.** Coverage varies by toolkit: custom canvases have
  no semantics, and some toolkits don't expose secondary/child windows. If `glass_a11y_snapshot`
  errors or comes back partial, drive those parts by mouse + pixel coords + logs — don't plan on
  semantic addressing before confirming it works for the part you need.
- **Select by `name`, not `role` — in every selector.** Toolkits split an element's *name*, its
  *role*, and its clickability across sibling/child nodes (Jetpack Compose puts the name and `Button`
  role on different nodes; a `GtkListView` row's name lives on its inner `Label`, not the
  `ListItem`), so a `role` filter can exclude the very node carrying the name. This bites the
  searching tools hardest — `glass_scroll_to_element {name:"Row 060", role:"ListItem"}` sweeps the
  whole list and returns a confident `{matched:false}` that reads like "no such row." Filter by
  `name` (plus a state or `value_contains`); add `role` only once a snapshot shows them merged.
- **Let glass run the loops you'd hand-roll.** `glass_scroll_to_element` replaces scroll-then-
  snapshot polling; `return:"snapshot"` folds the re-read into the action that invalidated it;
  `window_id` observes another window without retargeting; `glass_do` collapses a known sequence into
  one call. The `glass_wait_for_*` family times out *softly* to `{matched:false}` — branch on that,
  don't retry blindly.
- **Re-snapshot after anything that reflows layout.** a11y `#id`s and bounds go stale after a scroll,
  window switch, or keyboard/layout shift; clicking a cached id lands wrong. `return:"snapshot"` is
  the cheap way to stay current — and glass warns you (`element #N changed since the snapshot;
  re-snapshot`).
- **Mouse clicks are the most reliable input.** Keyboard, pointer-modifiers, and drags may or may not
  land depending on the app; use a click when you need a known-good input to disambiguate (clicks log
  but keys don't ⇒ input delivery, not the app). If an input never lands after a retry or two, report
  it *unverifiable via glass for this app* rather than assuming the app failed.
- **Pace drags with `duration_ms`** (≥ 200) so frame-based UIs sample the path; too short yields too
  few points to register a stroke. Use **high-contrast colors** when a diff must be tight — a dark
  stroke on a dark theme barely diffs.
- **After an action that can close the active window**, `glass_list_windows` + `glass_select_window`
  a live one before the next op.
- **Ask `glass_doctor` what's available — never probe `PATH`.** glass resolves external tools by its
  own order (env override, `PATH`, data dir, then next to the binary) and version-gates some, so
  `which sway` finding nothing doesn't mean Wayland is unsupported, and finding something doesn't mean
  it qualifies.

## Driving a11y-rich apps (forms, tables, menus, dialogs)

Here the tree is the primary oracle and pixels the fallback — the inverse of the canvas case. A
`glass_a11y_snapshot` resolves most verification (row content, selection, gating, sort order) with
zero pixels; screenshot only where a11y is blind — a transient's own text, a popover-visibility
question, a render bug.

- **A snapshot says what an element *is*, not what it holds.** Each line is
  `#id Role "name" (x,y wxh) [states]` — role, name, bounds, states like `checked`/`enabled` — but
  **not** a text field's text or a spin button's number. Read a value back with `glass_wait_for_element
  {name, value_contains}` or `{name, condition:"checked"}`, which returns the element and doubles as
  the confirm-by-signal step. `condition` also takes `appears`/`disappears`, `enabled`/`disabled`,
  `unchecked`, `selected`/`unselected`, `expanded`/`collapsed`, `focused`, `visible`/`hidden`. (A
  combo box's *name* is its current selection — the one case a snapshot shows a value.)
- **Web content inside the app you're driving arrives under a `Document` element.** A browser page or
  an embedded web view publishes its own elements as that `Document`'s children — address them like
  any other element in the tree; an `<iframe>` is a nested `Document` wherever the platform exposes it.
- **A `Document` with no children can mean the web engine hasn't published its tree yet, or that the
  page is empty.** The snapshot says which in its own notice: on a not-yet-published tree, take a
  fresh `glass_a11y_snapshot` after a moment before falling back to pixels; a notice describing a
  placeholder for content the app hasn't exposed means the engine won't publish under this launch —
  drive that area by pixels instead. On **iOS** there is nothing to disclose: a `WKWebView`'s page
  contributed no element at all through `idb` — no `Document`, and so no notice — so a web screen
  there reads as an ordinary short tree and only `glass_screenshot` shows it (read 2026-08-24).
- **`glass_click_element` handles popovers for you.** A dropdown or context menu is often its own
  window whose origin the element's bounds don't reflect; glass detects that and routes the click in.
  If it can't map the popover (`element #N is inside a popover glass could not map to a window;
  select_window it and click by coordinate`), only *then* `glass_select_window` the popover and
  `glass_click` at a local coord (`item bounds − owning-menu-node bounds`).
- **`glass_set_value` covers more than text.** A text field, a number for a spin/slider, a boolean
  for a switch/checkbox/toggle (`true/false`, `on/off`, `1/0`, `yes/no` — idempotent), or a dropdown
  by option label (it opens the popup and picks). Each error names its remedy: `AxElementNotEditable`
  (no writable a11y value — focus with `glass_click`, then `glass_type`/`glass_key`),
  `AxValueNotApplied` (write succeeded but nothing changed — read-only projection, use keystrokes),
  `AxValueNotBoolean` (a non-boolean sent to a switch/checkbox), `AxElementChanged` (re-snapshot).
- **Virtualized lists expose only the realized rows.** A `GtkColumnView` / `LazyColumn` /
  `VirtualizingStackPanel` publishes just the on-screen rows (17 of 500) — **never infer the total
  from the node count**; read it from a status label or log. Reach an off-screen row with
  `glass_scroll_to_element {name}` (it sweeps, reverses, and returns a soft `{matched:false}`), and
  **aim its `x`,`y` at the scrollable container** — the default anchor is the window *center*, and if
  that lands on another widget the wheel goes nowhere and you get a fast, false `{matched:false}`. A
  container with a *continuously repainting* node (a clock) never looks "unchanged", so the sweep runs
  to `timeout_ms` instead of reversing — pass the `direction`; a very long list may need a bigger
  `timeout_ms` or `step`.
- **After a re-sort, scroll to a known edge before reading order.** A column-header sort keeps the
  scroll-anchor row at its viewport position rather than resetting to the top, so the first *realized*
  rows are its neighborhood, not the front of the sorted list — a working sort can look broken.
- **A one-shot transient can be too fast to catch.** Set up a scoped `glass_wait_for_region` *before*
  triggering it (a delete toast); if it lives in another window, observe with `window_id`, not a
  `glass_select_window` switch that can cost more round-trips than the element lives. If it still
  misses, report it *unobservable via glass* rather than assuming nothing happened. (A *continuously*
  repeating affordance has no deadline — catchable on some cycle.)

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

- **Touch backends have no hover and no modifier plane.** `glass_move` and pointer `modifiers` are
  accepted and *silently dropped* on Android/iOS — build touch verification around taps.
- **Multi-touch is `glass_gesture` — Android only, on-device agent required.** N simultaneous straight
  `from→to` segments over a shared `duration_ms` (pinch = two toward/apart, rotate = two on an arc,
  two-finger swipe = two parallel). Elsewhere it refuses rather than degrading, and a `glass_drag`
  can't express it. Confirm by the app's own signal (a `zoom:` log, a diff), and **calibrate the
  finger spread** — too wide overshoots a clamp (a max-zoom ceiling) in one gesture.
- **An iOS switch toggles on a swipe, not a tap.** A `UISwitch` doesn't actuate on a center tap; use
  `glass_set_value` (it reads state and does the trailing-edge swipe, idempotent) — a pixel
  `glass_click` on it does nothing.

## Common mistakes

- Trusting a returned `ok` instead of an app-side signal.
- A full-window screenshot to read one corner — the biggest avoidable token sink; crop, diff, or log
  instead (though on a *small* window one frame can answer several questions more cheaply than several
  crops).
- Polling with screenshots instead of a `glass_wait_for_*`.
- Reading an a11y error as "this app has no tree" when you forgot `a11y:true`, or trusting
  `glass_doctor`'s a11y check as proof of one — probe with a real snapshot.
- Reading `glass_wait_stable {settled:true}` as "idle" (scope with `stability_region`; assert motion
  with `glass_wait_for_region {until:"changes"}`).
- Inferring a list's total row count from the realized node count.
