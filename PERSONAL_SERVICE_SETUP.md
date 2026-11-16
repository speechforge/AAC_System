# Google and personal account storage

All implementation, local Redis binaries, dependencies, database files, logs and reports live in this checkout. The existing IndicF5 checkpoint and Gujarati reference remain in use.

## Account behavior

- **Personal account:** each browser profile receives a random, HttpOnly guest-profile cookie. A revocable session provides access to that profile. Ending a session revokes its token; reconnecting in the same browser restores that personal profile's records. Clearing the profile cookie creates a new personal identity.
- **Google account:** the browser exchanges its Firebase Google ID token with the backend. The backend verifies the token signature, audience, issuer, expiry and Google provider before creating a session. User IDs supplied directly by the browser are never trusted. Google data follows the verified account across browsers connected to this AAC backend.
- Accounts have independent recent conversations, frequent words and bookmarks. English, English, English, Hindi, Gujarati and Marathi each have separate lists. Signing in or out never merges guest data into Google data or another Google account.
- Recent conversations retain the last 100 entries, with 50 returned by the API. The dashboard shows five. Word counts retain up to 1,000 distinct words per account/language. Bookmarks retain up to 100 distinct sentences per account/language.
- Word selections increment counts atomically. Generated sentences and quick phrases enter recent conversations. Repeated requests with the same event ID count only once for seven days. Frequent words are ranked first in that account's word suggestions without fabricating probability scores.
- Guest sessions expire after seven days; Google sessions last at most one hour and never beyond their verified ID token's expiry. Firebase token refresh renews the backend session. Logout deletes the session in Redis. Mutations require a session-bound CSRF token and same-origin requests. Session cookies are HttpOnly/SameSite=Lax and become Secure over HTTPS.

## Running locally

The current environment is `/home/linux/miniconda3/envs/taac_env/bin/python`.

```bash
# First-time dependencies (Ubuntu; downloads/extracts packages without sudo)
bash indic-generative-aac/scripts/setup_personal_storage.sh

# Prepare the local English-trained speech model (IndicF5 weights already exist)
/home/linux/miniconda3/envs/taac_env/bin/python indic-generative-aac/scripts/setup_speech_models.py

# Start AAC plus local Redis
/home/linux/miniconda3/envs/taac_env/bin/python indic-generative-aac/backend/run_local.py start

# Status / stop AAC
/home/linux/miniconda3/envs/taac_env/bin/python indic-generative-aac/backend/run_local.py status
/home/linux/miniconda3/envs/taac_env/bin/python indic-generative-aac/backend/run_local.py stop
```

Open http://localhost:8000/ . API documentation: http://localhost:8000/docs .

Redis listens only on `127.0.0.1:6380`, with a randomly generated password. Its connection file and configuration have mode 0600. AOF persistence uses `appendfsync everysec`; a power failure can lose approximately the last second of writes. Files reside in `.runtime/redis/data`. The launcher leaves Redis running when AAC stops, so sessions and records remain available. `.runtime/` is ignored by Git. For a separately managed Redis instance, set `AAC_REDIS_URL` in the server environment.

The existing frontend Firebase project is `indicaacsystemnaacl2026`. Google sign-in must be enabled in that Firebase project, and `localhost` must be an authorized domain. `AAC_FIREBASE_PROJECT_ID` can configure the matching backend audience. No service-account private key is needed to verify Firebase ID tokens. Live Google login requires the user's interactive sign-in; automated account-isolation tests mock token verification, while rejection paths exercise issuer/provider/expiry controls.

## API

| Route | Purpose |
| --- | --- |
| `POST /api/session/guest` | Connect/reconnect the browser's personal profile |
| `POST /api/session/google` | Verify `{id_token}` and connect a Google account |
| `GET /api/session` | Current service, opaque profile ID, CSRF token and expiry |
| `DELETE /api/session` | Revoke the current session |
| `GET /api/personal/dashboard?language=gu` | All three account lists in one request |
| `POST /api/personal/activity` | `{event_id, kind: word/conversation, text, language}` |
| `GET /api/personal/recent-conversations?language=mr` | Recent conversations |
| `GET /api/personal/frequent-words?language=mr` | Frequent words/counts |
| `GET/POST /api/personal/bookmarks` | Read `?language=gu`, or save `{text, language}` |
| `DELETE /api/personal/bookmarks/{id}?language=gu` | Remove one account/language bookmark |

Send the CSRF token as `X-CSRF-Token` for personal mutations/logout. The browser sends the HttpOnly session cookie automatically. Missing/expired sessions return 401; CSRF/origin violations return 403; Redis failures return 503. No memory-only or browser-global fallback silently reports a successful save.

The previous shared browser cache is archived under `aac_legacy_shared_cache_v1` before preferences are rewritten. Existing Firestore data is not deleted. Legacy shared bookmarks are deliberately not automatically imported into any account, because their ownership cannot be established from that shared cache. New bookmarks use Redis. Custom word grids are now browser-cached separately by the backend's opaque profile ID, rather than mixed between accounts; these custom grids are not yet synchronized through Redis.

## Verification

```bash
/home/linux/miniconda3/envs/taac_env/bin/python -m unittest discover -s indic-generative-aac/backend -p test_personal_service.py -v
/home/linux/miniconda3/envs/taac_env/bin/python -m unittest discover -s indic-generative-aac/backend -p test_gu_mr_support.py -v
/home/linux/miniconda3/envs/taac_env/bin/python -m unittest discover -s indic-generative-aac/backend -p test_tts_contract.py -v
/home/linux/miniconda3/envs/taac_env/bin/python -m unittest discover -s indic-generative-aac/backend -p test_redis_durability.py -v
/home/linux/miniconda3/envs/taac_env/bin/python indic-generative-aac/tests/benchmark_personalization.py
```

Account tests use a random key prefix in Redis database 15 and delete only their own keys. The durability test restarts a separate temporary Redis process and verifies both language lists and the session survive. It never restarts the application Redis instance. The benchmark uses fresh guest accounts and removes its own records afterward.

Browser verification uses local Playwright and Chrome:

```bash
npm install --prefix .runtime/browser playwright@1.51.1
node indic-generative-aac/tests/browser/personal-storage.cjs
```

The browser test stubs speech only inside its browser context to focus on account storage. Real IndicF5 is verified separately. Browser screenshots and test reports live in `.runtime/reports`.

The personalization benchmark consists of four controlled Gujarati/Marathi cases: after three selections of a target word, it should rank first for that account. This improves from 0/4 with the shared predictor to 4/4 with personalized counts. This is not a held-out language-model accuracy or speech-quality measurement. The existing corpus remains English/Hindi, with native board-label localization for Gujarati/Marathi. No claim of retraining the language or speech model is made.
