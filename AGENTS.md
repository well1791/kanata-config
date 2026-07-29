# AGENTS.md

# kanata-config — conventions for editing this keymap

This repo is a [kanata](https://github.com/jtroo/kanata) keyboard-remapping config. These
notes are for anyone (human or agent) editing it.

## Architecture

`config.kbd` is the single entry point. It defines the global config (`defcfg`), source
layout (`defsrc`), shared `defvar`s and `defalias`es, then `(include _<module>.kbd)` for
each of the six modules.

### The co-location rule (critical)

kanata resolves `(include ...)` paths **relative to `config.kbd`**. Every `_*.kbd` file
**must live in the same directory** as `config.kbd`. Do not move them into subdirectories.

### The module contract

kanata uses a single global namespace, so module ordering and the names each module
needs/provides matter. Every module's header block states:

- **needs** — `defvar` names and `defalias` names it consumes (defined elsewhere)
- **provides** — layer names (`L_*`) and alias names it defines for others to use

When adding a module or alias, update its header's needs/provides. When renaming an alias or
var, search all modules — it's a flat namespace with no imports.

## Naming conventions

| Prefix | Meaning | Example |
|---|---|---|
| `ch_*` | positional chord token | `ch_hrl` (home-row-left) |
| `L_*` | layer name | `L_ALPHA`, `L_NUMS` |
| `sw_*` | layer-switch alias | `sw_al` → `(layer-switch L_ALPHA)` |
| `os_*` | one-shot alias | `os_nums` (one-shot into `L_NUMS`) |
| `al_*` / `pl_*` | alpha/plain chord aliases | `al_hrl`, `pl_sil` |
| `na_*` | navigation chord aliases | `na_up`, `na_lt` |
| `ns_*` | numbers chord aliases | `ns_hi`, `ns_tm` |
| `ff_*` | function-key chord aliases | `ff_hi`, `ff_tr` |

Chord tokens encode **position**: `t`/`h`/`b` (top/home/bottom row) × `i`/`m`/`r`/`p`/`s`
(index/middle/ring/pinky/extra) × `l`/`r` (left/right). e.g. `ch_hrl` = home-row-left
(the `a` position).

## Validation loop

After any change:

1. `kanata --cfg config.kbd --check` — parse + semantic check (catches undefined aliases,
   duplicate chords, etc.).
2. `systemctl --user restart kanata.service` — apply. (The `_media.kbd` `restart_kanata`
   alias does this from a chord.)
3. Type-test the affected layer.

## Rules

- `.kbd` files are **not templated** and contain **no secrets/PII**. Keep it that way.
- Keep all files co-located (see co-location rule above).
- One concern per module (alpha, nav, nums, ff, media, go). Add new keys to the relevant
  module, or create a new `_*.kbd` module and `(include ...)` it from `config.kbd`.
- Prefer extending existing chord groups over inventing new ones.
