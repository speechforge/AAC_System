> **Superseded palette:** the app now shares the landing/login ivory + violet theme. See `indic-generative-aac/DESIGN_RULES.md` and `frontend/studio-theme.css`. The blue values below are historical.

# Indic AAC Studio visual system

Source: local UI/UX Pro Max 2.15.0, installed from /home/linux/Documents/uiux_skill/ui-ux-pro-max-skill. The searches supported restrained flat web-app styling, accessibility and React form guidance. Their hero/conversion patterns were not a fit for an AAC board and were not adopted. System fonts replace remote-only font dependencies for native Indic-script support and offline operation.

Use a calm #f3f6f8 canvas, white surfaces, #203448 text and #526477 secondary text. Dark mode pairs #131d27 canvas with #1b2937 surfaces and #f2f6fa text. Use 8/12/16px spacing, 12–16px panel corners, and one subtle shadow. Reserve strong emphasis for the main sentence action. User-selectable button palettes retain their existing light/dark contrast pairs and affect buttons only.

The former pinned core grid above Quick Express is removed. A history-icon button sits immediately after the My Words pin in the header toolbar. History opens an account-scoped conversation drawer with speech replay, dates, bookmarks, keyboard focus trapping and dismissal. Core concepts remain in the symbol database. AAC symbols remain user selectable (including emoji), because they are communication content. Structural controls and the brand use SVGs. Headers retain English branding, four languages, settings and the far-right account dropdown. Account activity stays inside Profile settings. No recorded demo gallery is inserted into the live AAC board.

Phone quick phrases use a keyboard-focusable horizontal strip with a visible scrollbar; their order is fixed. Cards, controls and fields have at least 44px targets. Support narrow phone, tablet, landscape, desktop, keyboard focus, contrast modes and reduced motion. Voice/accessibility popups retain their compact upper-right placement and mouse/touch dismissal behavior.

The /welcome landing page uses one viewport with no page scrolling: a warm ivory canvas, one violet Login action, pastel language bubbles, illustrated message cards and a compact feature strip. Transform-based animation supports pause and reduced-motion preferences. Anonymous visitors enter here before choosing Login or Create an account. Login and signup open as separate focused screens with a matching violet identity and the same pastel multilingual communication-board illustration, visible field labels, local account support, Google sign-in, password visibility control and progressive disclosure for shared demo credentials. Real Google sign-in needs the user/provider; simulated UI checks do not establish a live provider login.

The communicator fills one viewport. Desktop uses a message pane beside a vocabulary pane; phones stack these panes. Only bounded panel contents scroll. Keep category navigation and main actions reachable, with labels on AI Polish & Speak and an accessible message-type selector. Never hide content by merely clipping the whole document.

Visual motion has a shared device preference in `aac_motion_v1`: enabled by default, normal speed 1×, eight rates from .25× to 2×. Animate panel entrances, short fades and stable hover emphasis; avoid moving communication targets on hover. Respect reduced motion.

History uses one date heading per day, separated message/time typography, an Export CSV action and hover-out dismissal without a cross. My Words emoji selection is a searchable, keyboard-accessible inline region using bundled data, with incremental browsing and focus returned to the word input after selection.

The left composition pane has no vertical scrolling. Keep its actions visible, use horizontal sentence/prediction ribbons, and place secondary actions/saved phrases in the ellipsis menu. Generated output replaces composition in the same pane; Back to message restores editing. Native keyboards appear as bounded popups. All pages share `/static/favicon.svg`. The welcome header is text-only branding without a logo mark.
