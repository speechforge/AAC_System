# Responsive AAC interface and playback settings

Open http://localhost:8000/ and refresh with Ctrl+Shift+R after updating this checkout. Changes are limited to this project.

## Brand and layout

The header and footer always display **Indic AAC Studio** in English, with `lang="en"` and `translate="no"`. The language selector still translates communication words and interface controls.

The header wraps into touch-sized rows on narrow screens. Category controls, quick phrases and predictions wrap instead of extending offscreen. Action buttons and the message-type selector have explicit narrow-screen layouts. Settings scroll inside the viewport, support Escape, trap keyboard focus while open, and restore focus on closing. Browser pinch zoom is enabled. The accessibility trigger is in the header rather than floating over Speak or other actions.

Outer panel padding is reduced. Standard communication cards use larger text (16–17 px at the normal text scale) and larger symbols; compact/large density choices remain available. Cards wrap long labels instead of truncating them to one line. Custom-word removal is a separate button below its word card, rather than an overlay on the symbol.

## Button colors and contrast

Preferences offers 12 muted palettes: Sky, Sage, Teal, Lavender, Rose, Peach, Sand, Olive, Slate, Cocoa, Mauve and Blue. Each has a light/dark foreground/background pair. The palette changes **buttons only**; panel and page surfaces remain neutral. Dark mode and high contrast remain separate controls. Selection uses an outline/underline or inverted foreground/background as well as color.

The browser regression measured a minimum text contrast ratio of **8.36:1** for the normal and selected communication controls across all 12 palettes in light/dark modes. Foreground/background colors change together without a transition that could temporarily hide text. This is a measured color check, not a claim of complete accessibility certification.

## Motor planning and symbol styles

The ten core words always use the same five-column, two-row order at the top of the communication interface. Changing categories, language, symbol appearance or adding personal words does not reorder them. Predictions and frequent words remain separate from the core grid. Category density changes do not resize/reorder the core grid.

Five appearances are available: emoji symbols, simple SVG line drawings, high-contrast drawings, real photos, and text-only communication buttons. Word labels remain visible. Core words, category navigation, word cards, quick phrases, predictions and selected-word controls use the chosen appearance.

Five concrete food/drink photos are bundled locally (water, milk, rice, roti and fruit). The credits and source licenses are at `/static/photos/credits.html`. Words without a photo use a drawing; no unrelated category photo is substituted. Preferences allows uploading a JPG/PNG/WebP photo for any board or personal word. Photos are resized on the device, their original metadata is discarded, and they are cached per account on that device. They are not uploaded or synchronized to another account/device.

## Session playback speed

Preferences offers **0.25×, 0.50×, 0.75×, 1×, 1.25×, 1.50×, 1.75×, 2× and 3×**. The accessibility panel uses the same setting. Word speech, quick phrases, generated sentence audio and replay all use this value, with pitch preservation requested from the browser. Changing the setting also updates currently playing audio.

Speed is stored in `sessionStorage`, scoped to the current account session in that tab. Reloading within a valid session retains it. Signing out, ending a session, switching accounts, or reconnecting after expiry resets it to 1×. Button colors and appearance remain device preferences; personal photos remain account-scoped. The separate speech-quality diagnostic page intentionally stays at 1× to provide a neutral listening comparison.

## Verification

```bash
node indic-generative-aac/tests/browser/responsive-accessibility.cjs
node indic-generative-aac/tests/browser/english-support.cjs
node indic-generative-aac/tests/browser/personal-storage.cjs
```

The browser regression checks 320, 390, 600, 768, 1024 and 1440 px widths, all four languages, stable core positions, theme contrast, all five styles, photo upload/reload, and every speed on word/generated/replay playback. It checks session speed restoration/reset. Synthesis responses and the Audio object are intercepted only inside that browser test; this verifies UI playback routing without repeatedly running the neural models.

Reports and screenshots are in `.runtime/ui-review` and `.runtime/reports`. Tests use Chromium viewport emulation; physical iOS/Android hardware was not available for this check. The existing local speech engines and Redis account service were not changed by this UI work.

## Compact settings sidebar

Button colors use an expandable picker with twelve 44 px circular swatches, localized accessible names and a check mark on the selected color. Symbol appearance, session playback speed, display, card size and AI architecture each use a dropdown. Display offers day/night and high contrast in either mode; all previous boolean combinations remain available. Personal photo upload is inside an expandable section.

On desktops with a mouse and hover support, leaving the sidebar closes it. Native dropdown menus do not close it when the browser reports no related page target. On touch devices it remains open until the user taps outside, closes it, or chooses Save & Close. Escape, focus containment and focus restoration are retained. Dropdown selection saves through the existing preference/session mechanisms.

Targeted interaction check: `node indic-generative-aac/tests/browser/compact-settings.cjs`. The desktop and touch checks cover color geometry, all dropdown state changes, 9 available speeds, panel width, outside dismissal, Escape and no browser JavaScript errors.
