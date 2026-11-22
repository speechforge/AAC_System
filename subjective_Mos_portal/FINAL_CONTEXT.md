# MOS portal handoff — 17 November 2026

Public listener URL: https://aac-mos-portal.indic-aac-speech-study-2026.workers.dev/

Public admin URL: https://aac-mos-portal.indic-aac-speech-study-2026.workers.dev/admin

Local URLs: http://localhost:8011/ and http://localhost:8011/admin.

Admin username is `mos_admin`. The password is defined in `.state/ADMIN_CREDENTIALS.txt` (0600); a salted scrypt hash is in `.state/config.json`. No password is present in the public assets, source manifest, or this handoff. `scripts/admin_password.py` can change it interactively and revoke admin sessions.

## Delivered

A standalone FastAPI/SQLite portal with registration, a saved random 20-trial order, native audio playback, whole-clip rating controls, 1–5 integer scores, idempotent saves, participant resume, and completion. The exact requested ten participant columns are persisted in SQLite and `.data/participants.csv`; raw scores are in `.data/ratings.csv`. Admin authentication protects identifying data, language MOS, file summaries, individual progress, inclusion/exclusion audit and CSV exports. No historical participants from the prompt/reference were imported into the new study.

Twenty newly generated mono 24 kHz PCM WAVs are in `audio/`, five per language. English uses F5-TTS; Gujarati/Hindi/Marathi use IndicF5. Their manifests report cache misses and default voices for every clip. Native-reader/human audio-quality review remains pending; no human MOS result is claimed.

The layout adapts the supplied reference's summary cards, participant selector, distributions, file results and exports, with the existing AAC ivory/violet identity. The reference was read on 10.100.59.83 at `/home/linux/Documents/vocoder_leaderboard_Mos` and its installed SpeechEvalKit `gui.py`; only source reference was read. SSH credentials were not saved in this project.

## Hosting and persistence

A Cloudflare Worker (`aac-mos-portal`) supplies the stable public HTTPS address. Worker deployment `1ae60902-b766-4f86-9619-4599bbc061ff`, version `3d8580cb-309b-4a9c-889f-af5e2a00c68e`, was enabled at 100%. KV contains only the current tunnel address. The Worker holds a secret origin key; it does not store participant responses. The supervised local connector posts authenticated routing updates after tunnel restarts. Its actual internal address changed during the restart check while the public URL stayed unchanged.

The origin server, local machine and connector must remain running. The setup is not a claim of independent cloud persistence/uptime. Workers/KV and account-less tunnel limits still apply; there is no named custom-domain tunnel because the connected account had no domain zones. A temporary outage keeps the local response database intact. Startup commands and boot-time limitations are in README.md.

The portal process is detached on localhost:8011; the internet connector is detached separately. The main AAC server remains on localhost:8000 with neural TTS and Redis ready. The isolated QA server on 8012 was stopped after testing. The previous accepted AAC repository commit `3501e98e855d028d3dd8620bedbf09fe4dba0f4f` and its tracked GUI/backend files were not modified by this new directory. No new GitHub push was requested for this portal.

## Verification and evidence

- Eight backend tests passed: registration/schema, all 20 assignments, strict scores and playback requirements, retry/concurrent-save idempotency, resume/persistence, language statistics and explicit exclusions, partial-session filtering, private routes/origin checks, CSV safety and validation. Unit playback timing uses an explicit fixture.
- Worker contract checks passed for authenticated origin updates, allowed origin validation, fixed-host URL construction, range/cookie streaming, and an unavailable-origin response.
- `tests/browser.cjs` passed against isolated `.state/qa-data`: 20 real native Audio playbacks, 20 saved scores, five per language, resume after reload, admin login, per-language MOS, exclusion, correct participant CSV columns, and mobile overflow checks. Those scripted scores and screenshot values are QA fixtures, not participant research results.
- `tests/public_check.py` passed from a separate machine over the live HTTPS address: public form and 20-file health, administrator authentication, Secure cookies, blocked unauthenticated exports, exact participant CSV schema, logout and authenticated route updates. No participant or score was created.
- `tests/public_browser.cjs` passed over the deployed HTTPS hostname: participant form, 320 px layout, real admin sign-in, Secure/HttpOnly cookie, CSV download and logout. No participant or score was created. Initial local Cloudflare routing had a TLS handshake issue on one resolved IPv4 address; this browser run used the other resolved IPv4 with full certificate and hostname verification. A later ordinary local HTTPS request also returned healthy JSON. No TLS verification was disabled.
- Final observed live counts were **0 participants / 0 ratings**; all synthetic response fixtures are separate. `.data/portal.sqlite3`, `.state/config.json` and `.state/ADMIN_CREDENTIALS.txt` were 0600 and ignored by Git.
- `scripts/backup.py` produced a consistent SQLite snapshot and CSVs derived from that snapshot under `.data/backups/20261117T074623Z`, with SHA-256 records. Use it again for later real data.
- Evidence JSON and desktop/mobile screenshots are in `evidence/`. Public admin screenshots show the empty live study. Files named `*-qa*` and `browser-qa.json` are synthetic functional tests.

Current method: primary MOS is the arithmetic mean of completed non-excluded sessions. Listener-level 2,000-resample percentile bootstrap CIs use seed 20261117 and are not displayed for insufficient/incomplete listener groups. The source file manifest is `SOURCE_SHA256.json`. The public origin and resource IDs are in `config/deployment.json`. Private configuration/data are deliberately outside that manifest.


## Participant instructions update

The participant pages no longer display researcher/admin links or the study footer. Mother-tongue selection is disabled until the listener presses “I understand”; the server also requires acknowledgement for new registration. Instructions explicitly ask for naturalness/robotic-sound ratings without requiring language fluency or specialist language knowledge (1 = very unnatural/robotic, 5 = very natural/human-like). The saved per-listener shuffle remains intact, including on resume. Nine backend tests cover the checkpoint and independent randomized orders. The MOS server and connector were restarted; the separate main AAC service and saved response data were preserved. The Cloudflare account has only this Worker; its account subdomain was replaced to remove the personal name from the public URL. Existing study records were not reset.
