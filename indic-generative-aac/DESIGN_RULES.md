# Indic AAC Studio: global design rules

One look across every page: landing, sign-in, sign-up, the AAC studio, evaluation, speech-check, photo credits.
Source of truth: `frontend/studio-theme.css` (tokens + rules) and `frontend/studio-core.js` (behaviour). Every HTML page loads both **last** in `<head>`.

## Theme (taken from the landing + login pages)
| Role | Light | Dark |
|---|---|---|
| Canvas `--paper` | #faf8f3 ivory | #16131f |
| Surface `--surface` | #fffefa | #211d2d |
| Primary `--violet` | #6044be | #7a62d6 |
| Accents | peach #efa06b, sage #668065 | same, softened |
| Text `--ink` / `--muted` | #25283b / #626273 | #f3f0fa / #c3bdd3 |

Rules
1. Colour comes only from the tokens. No raw hex in new code. Legacy `--studio-*`, `--auth-*` and Tailwind `brand-*` classes are remapped to the tokens.
2. One primary action per screen, violet with the 4px "pressed" shadow. Everything else is outlined or tinted.
3. Cards: 23px radius, `--shadow-m`. Controls: 10-14px radius. Targets are at least 44px (56px in Large-touch).
4. Focus ring is always a 3px violet outline. Never remove it.
5. Text contrast stays at 4.5:1 or better. Colour is never the only signal (use icon, label or shape too).
6. System fonts only (native Indic scripts, offline). Wording: short, literal, kind. No sarcasm, idioms or countdowns.

## Motion
1. Every page fades up on load; internal navigation fades out first (`html.is-leaving`). Cards/features use `.reveal` (staggered).
2. Hover lifts 2-3px; press scales to .97 or drops the 3D shadow. Communication tiles never move on hover in a way that shifts neighbours.
3. All durations come from `--motion-*` (`motion.js`): speed 0.25x-2x and On/Off. Never hard-code a duration.
4. `prefers-reduced-motion`, motion Off and the **Calm** profile all disable animation everywhere.

## Comfort profiles (`window.AACComfort`, shared by all pages, saved on device)
- **Standard**, **Calm** (desaturated, flat, no animation, no backdrop), **Focus** (no decoration), **Large touch** (125% text, 56px targets).
- Switches: *Easy-to-read text* (wider letter/word/line spacing, left aligned) and *Ignore accidental double taps* (450 ms guard).

## Required functions in the AAC system
Communication: symbol board (4 languages), sentence builder, next-word prediction, Speak and Stop audio, with user-reviewed Polish suggestions, quick phrases (help, water, toilet, pain), My Words, bookmarks, history with CSV export, personal/cloned voice, speech speed.
Emotional and sensory support (Support Hub, one tap, spoken aloud): **How I feel** (8 feelings), **What I need** (too loud, too bright, too crowded, quiet place, break, move, more time, no touching), **My day** (visual routine with First/Then), **Calm corner** (paced breathing).
Access: day/night/high-contrast, card size, text scale, grayscale, symbol style (emoji, line, photo, text), button colours, animation speed, comfort profiles, keyboard and screen-reader support.
Accounts: local + Google sign-in, per-account data.

Checklist for any new page or feature: loads `studio-theme.css` + `studio-core.js`; uses tokens; has the favicon, thumbnail meta (`thumbnail.png`), manifest; works with Calm and reduced motion; targets are at least 44px; strings exist in en/hi/gu/mr.

Phase 1 overrides: communication tiles and the working area have no decorative motion. Speak uses only the visible committed text and its message language; Polish never automatically speaks or commits. See docs/aac-redesign/FINAL_CONTEXT.md at the repository root for scope and evidence.
