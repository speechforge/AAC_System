# AAC Speech Lab — subjective MOS portal

A separate listening-study portal for the accepted Indic AAC Studio version. The original AAC website and its saved GitHub commit are unchanged.

Each participant rates **20 fixed WAV recordings: five English, five Gujarati, five Hindi, and five Marathi**, using **1 Bad, 2 Poor, 3 Fair, 4 Good, 5 Excellent**. This is a single-system speech listening study, not an objective MOS predictor or a multi-model leaderboard.

## Addresses and admin access

- Local listener portal: `http://localhost:8011/`
- Local administrator console: `http://localhost:8011/admin`
- Public Cloudflare address: see [`config/deployment.json`](config/deployment.json).
- Admin username: **`mos_admin`**.
- The generated admin password is saved privately in **`.state/ADMIN_CREDENTIALS.txt`**. It is not in frontend files, Git, or any public route. The server stores a salted scrypt password hash.

The public front door is a Cloudflare Worker. A supervised `cloudflared` connector forwards traffic to this machine's separate portal server. Only a tunnel address is stored in Cloudflare KV; participant details, sessions, ratings, and inclusion decisions remain on this machine. The machine, local portal process, and connector must remain running. This is not a claim of a standalone, continuously available cloud database or a production uptime guarantee. Tunnel reconnection can take time, and a changed origin can take about a minute to reach all KV caches.

## Data saved here

The live data directory is:

```text
subjective_Mos_portal/.data/
  portal.sqlite3       # Authoritative database; SQLite WAL and transactions
  participants.csv     # Automatically refreshed participant export
  ratings.csv          # Automatically refreshed raw rating export
  backups/             # Explicit consistent backups
```

The participant CSV columns match the requested format exactly:

```csv
participant_id,name,email,age,gender,mother_tongue,organization,registered_iso,is_excluded,trials_completed
```

- IDs are generated uniquely, timestamps are UTC ISO strings, and completion counts come from saved ratings.
- Registration collects name, email, age, gender, mother tongue, organization, and a participation-consent selection.
- Returning listeners use an opaque participant ID and private return code. The return code is displayed once, can be saved locally, and is hashed on the server. Existing browser sessions can resume automatically.
- Each listener receives a persisted, randomized permutation of all 20 recordings. Reloading does not reshuffle or discard saved responses.
- The browser requires a complete listen before enabling scores; the backend also checks playback state and elapsed time. These are practical controls, not proof against a malicious scripted listener.
- Ratings must be integers 1–5. Duplicate network retries cannot create extra ratings. At completion `trials_completed` is exactly 20.
- The historical participant rows provided in the request were used as a schema reference. They were **not imported as new subjects or mixed into this study**.
- Private state and live data are ignored by Git and have no public file-serving route. CSV exports require an authenticated administrator. Spreadsheet-formula escaping is applied to exported user-authored values; SQLite retains the original text.

## Admin dashboard

The structure follows the inspected SpeechEvalKit admin reference: participant selector, summary cards, score distribution, per-recording table, participant details, and exports. It is newly implemented here rather than copying the old service or its participant data.

The console provides:

- Overall MOS and language-wise MOS, rating counts, participant counts, standard deviations, and listener-level bootstrap confidence intervals where applicable.
- Participant name/email, demographics, organization, registration/completion timestamps, individual trial order and scores, and saved progress.
- Explicit include/exclude decisions with a required exclusion reason and an audit trail. Exclusion retains the raw records.
- Participants, ratings, language summary, file summary, and inclusion audit CSV downloads. Raw exports include incomplete/excluded records with flags. Summary exports follow the selected filters, including a selected participant.

Primary statistics default to **completed, non-excluded participants**. Optional checkboxes explicitly include incomplete or excluded sessions. MOS is the arithmetic mean of selected ratings. With complete sessions, each language has five ratings per listener, so listener weights are equal. A displayed 95% interval resamples listener means, with 2,000 percentile-bootstrap replicates and seed `20261117`; it is omitted for fewer than two listeners or incomplete groups. Repeated ratings within a listener are not treated as independent subjects for confidence intervals. No ratings means **—**, not a fabricated zero or a seeded score.

## Audio provenance

`config/stimuli.json` freezes clip IDs, language, authored text, engine, duration, sample rate, source endpoint, generation time, cache status, and SHA-256.

All 20 supplied files were generated specifically for this portal through the current AAC `/api/tts` service on 17 November 2026. Each returned `cache_hit: false`, `voice_source: default`, and the expected `f5tts` (English) or `indicf5` (Hindi/Gujarati/Marathi) kind. All are mono, 24 kHz, 16-bit PCM WAV. Durations are approximately 1.6–3.9 seconds. The portal verifies the file hashes before starting. Participant views show recording number and language, without the filename, model, or written transcript; the administrator can inspect the text.

Do not regenerate or replace audio while collecting this study. `scripts/prepare_audio.py` is a provisioning tool; it resumes valid existing files and requires the original AAC backend. Changing the stimulus set should start a new study/data directory. Authored Indic wording and output audio have not been described as native-reader or human-listener reviewed. Browser QA confirms real media playback events, not physically measured audible output or speech quality.

## Run locally

Use the existing verified Python environment:

```bash
# From the AAC checkout root:
/home/linux/miniconda3/envs/taac_env/bin/python subjective_Mos_portal/scripts/run.py start
/home/linux/miniconda3/envs/taac_env/bin/python subjective_Mos_portal/scripts/run.py status
```

For a separate environment, install `requirements.txt`. No TTS models or GPU are required for serving the already generated recordings.

```bash
# Serve over the configured Cloudflare front door:
/home/linux/miniconda3/envs/taac_env/bin/python subjective_Mos_portal/scripts/internet.py start

# Stop public access without removing data:
/home/linux/miniconda3/envs/taac_env/bin/python subjective_Mos_portal/scripts/internet.py stop

# Stop only the MOS server; this never stops the main AAC server:
/home/linux/miniconda3/envs/taac_env/bin/python subjective_Mos_portal/scripts/run.py stop
```

The connector executable is the official Cloudflare Linux AMD64 release in `.state/bin/cloudflared`; its version, source URL and checksum are recorded privately alongside it. Its logs and process IDs stay in `.state/`. The connector supervisor updates the authenticated origin-setting endpoint after a restart, preserving the public Worker address. It does not require storing a general Cloudflare API token on this machine.

To preserve data while the portal runs:

```bash
/home/linux/miniconda3/envs/taac_env/bin/python subjective_Mos_portal/scripts/backup.py
```

The script uses SQLite's online backup API and saves checksummed copies under `.data/backups/`. Keep that directory private. A fresh source checkout does not include existing listener records or administrator credentials. These processes are detached from the shell but are not installed as boot-time system services; after a machine reboot, start the local server and internet connector again with the commands above.

## Verification

```bash
# Eight backend tests, using isolated temporary databases and explicit playback timing fixtures:
/home/linux/miniconda3/envs/taac_env/bin/python -m unittest discover -s subjective_Mos_portal/tests -v

# Worker contract tests, including origin-update authentication, range/cookie forwarding and fixed-origin routing:
node subjective_Mos_portal/tests/worker.mjs

# Full browser flow against the isolated QA instance on port 8012:
node subjective_Mos_portal/tests/browser.cjs
```

The browser test uses the checkout's `.runtime/browser/node_modules/playwright` and `/usr/bin/google-chrome`. Set `MOS_DATA_DIR` when launching an isolated QA server; see `evidence/browser-qa.json`. Its 20 real audio playbacks, scripted ratings, example dashboard scores, and screenshots are **software QA fixtures, not human MOS results**. Synthetic listeners and ratings stay in `.state/qa-data`, never the live `.data` study. The first browser attempts exposed test-selector/CSP-harness issues; these were corrected without weakening the portal's production content security policy.

## Reference and methods

The read-only design/reference source was found on the supplied reference host under `/home/linux/Documents/vocoder_leaderboard_Mos` (capital `M`) and its installed `speechevalkit/gui.py`. No reference participant database was copied. The SSH password is not saved in this portal.

The labels follow the five-point listening-quality scale in [ITU-T P.800](https://www.itu.int/rec/T-REC-P.800-199608-I/en). This website alone does not establish full ITU-T procedural compliance. The fixed samples, listener selection, language familiarity, environment, exclusions, and testing method should accompany any reported research result.

### Live publication verification

The public form, admin login, Secure/HttpOnly cookie, CSV download, and logout were verified over the deployed HTTPS address. See `evidence/public-verification.json` (a separate machine using normal DNS) and `evidence/public-browser.json` (Chrome). No test participants were created in the live database. During initial Cloudflare provisioning, one locally resolved edge address had a TLS-handshake problem; the browser check selected the other resolved IPv4 address while retaining normal hostname/certificate verification. The connector now tries resolved addresses with normal TLS verification when updating its route. No certificate-verification bypass is used.

A connector restart was checked after deployment: the internal tunnel address changed while the public Worker address stayed the same. The source files and generated audio are retained here; `.state` and `.data` are intentionally private. The current accepted AAC GitHub snapshot remains unchanged because this portal was requested as a separate local directory, not as a replacement commit.

To start the isolated browser-QA instance before running `tests/browser.cjs`, use a separate terminal:

```bash
cd subjective_Mos_portal
MOS_DATA_DIR="$PWD/.state/qa-data" /home/linux/miniconda3/envs/taac_env/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8012 --no-access-log
```

Stop that QA process after testing. Its database is separate from the live study.


## Participant instructions update

The participant pages no longer display researcher/admin links or the study footer. Mother-tongue selection is disabled until the listener presses “I understand”; the server also requires acknowledgement for new registration. Instructions explicitly ask for naturalness/robotic-sound ratings without requiring language fluency or specialist language knowledge (1 = very unnatural/robotic, 5 = very natural/human-like). The saved per-listener shuffle remains intact, including on resume. Nine backend tests cover the checkpoint and independent randomized orders. The MOS server and connector were restarted; the separate main AAC service and saved response data were preserved. The Cloudflare account has only this Worker; its account subdomain was replaced to remove the personal name from the public URL. Existing study records were not reset.
