"""Standalone 20-clip AAC listening study. All participant data stays on the local disk."""
from __future__ import annotations

import csv
import hashlib
import hmac
import io
import json
import math
import os
from pathlib import Path
import random
import secrets
import sqlite3
import statistics
import threading
import time
from collections import defaultdict, deque
from contextlib import contextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, StrictInt

ROOT = Path(__file__).resolve().parent
LANGUAGES = {'en': 'English', 'gu': 'ગુજરાતી · Gujarati', 'hi': 'हिन्दी · Hindi', 'mr': 'मराठी · Marathi'}
PARTICIPANT_COLUMNS = ['participant_id', 'name', 'email', 'age', 'gender', 'mother_tongue', 'organization', 'registered_iso', 'is_excluded', 'trials_completed']
RATING_COLUMNS = ['participant_id', 'clip_id', 'language', 'score', 'rated_iso', 'trial_index', 'listen_count', 'listened_seconds', 'is_excluded']
GENDERS = ['Female', 'Male', 'Non-binary', 'Self-describe', 'Prefer not to say']


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def token_hash(value):
    return hashlib.sha256(value.encode()).hexdigest()


def password_hash(password, salt):
    return hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()


def settings(root):
    directory = root / '.state'
    directory.mkdir(mode=0o700, exist_ok=True)
    path = directory / 'config.json'
    if not path.exists():
        password = secrets.token_urlsafe(18)
        salt = secrets.token_hex(16)
        value = {'admin_username': 'mos_admin', 'admin_salt': salt,
                 'admin_password_hash': password_hash(password, salt),
                 'origin_key': secrets.token_urlsafe(32), 'public_origin': ''}
        path.write_text(json.dumps(value, indent=2) + '\n')
        path.chmod(0o600)
        credentials = directory / 'ADMIN_CREDENTIALS.txt'
        credentials.write_text('Admin URL: /admin\nUsername: mos_admin\nPassword: ' + password + '\n')
        credentials.chmod(0o600)
    return json.loads(path.read_text())


def csv_value(value):
    # Keep the original text in SQLite; prevent formula execution in spreadsheet exports.
    if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@')):
        return "'" + value
    return value


def csv_text(columns, rows):
    output = io.StringIO(newline='')
    writer = csv.writer(output)
    writer.writerow(columns)
    for row in rows:
        writer.writerow([csv_value(row.get(key, '')) for key in columns])
    return output.getvalue()


class Store:
    def __init__(self, directory):
        self.directory = directory
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.path = directory / 'portal.sqlite3'
        self.lock = threading.RLock()
        with self.connect() as db:
            db.executescript('''
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS participants (
                participant_id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                age INTEGER NOT NULL, gender TEXT NOT NULL, mother_tongue TEXT NOT NULL,
                organization TEXT NOT NULL, registered_iso TEXT NOT NULL, is_excluded INTEGER NOT NULL DEFAULT 0,
                trials_completed INTEGER NOT NULL DEFAULT 0, resume_salt TEXT NOT NULL, resume_hash TEXT NOT NULL,
                consent_iso TEXT NOT NULL, exclusion_reason TEXT NOT NULL DEFAULT '', completed_iso TEXT
            );
            CREATE TABLE IF NOT EXISTS trials (
                participant_id TEXT NOT NULL REFERENCES participants(participant_id), clip_id TEXT NOT NULL,
                position INTEGER NOT NULL, score INTEGER CHECK(score BETWEEN 1 AND 5), rated_iso TEXT,
                play_started REAL, play_ended REAL, play_count INTEGER NOT NULL DEFAULT 0,
                listened_seconds REAL NOT NULL DEFAULT 0,
                PRIMARY KEY(participant_id, clip_id), UNIQUE(participant_id, position)
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY, role TEXT NOT NULL, participant_id TEXT,
                csrf TEXT NOT NULL, expires REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS audit (
                id INTEGER PRIMARY KEY, at_iso TEXT NOT NULL, action TEXT NOT NULL,
                participant_id TEXT, reason TEXT NOT NULL
            );
            ''')
            self.snapshot(db)
        self.path.chmod(0o600)

    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('PRAGMA busy_timeout=15000')
        return db

    @contextmanager
    def write(self):
        with self.lock:
            db = self.connect()
            try:
                db.execute('BEGIN IMMEDIATE')
                yield db
                db.commit()
                self.snapshot(db)
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()

    def participant_rows(self, db):
        return [dict(row) for row in db.execute('SELECT ' + ','.join(PARTICIPANT_COLUMNS) + ' FROM participants ORDER BY registered_iso')]

    def rating_rows(self, db):
        query = '''SELECT t.participant_id,t.clip_id,t.score,t.rated_iso,t.position+1 AS trial_index,
                   t.play_count AS listen_count,t.listened_seconds,p.is_excluded
                   FROM trials t JOIN participants p USING(participant_id)
                   WHERE t.score IS NOT NULL ORDER BY t.rated_iso'''
        return [dict(row) for row in db.execute(query)]

    def snapshot(self, db):
        rows = self.rating_rows(db)
        for row in rows:
            row['language'] = row['clip_id'].split('-')[0]
        for filename, columns, data in [('participants.csv', PARTICIPANT_COLUMNS, self.participant_rows(db)),
                                         ('ratings.csv', RATING_COLUMNS, rows)]:
            target = self.directory / filename
            temporary = self.directory / (filename + '.tmp')
            temporary.write_text(csv_text(columns, data), encoding='utf-8')
            temporary.chmod(0o600)
            os.replace(temporary, target)


def summarize(values):
    return {'mos': round(statistics.mean(values), 5) if values else None,
            'std': round(statistics.stdev(values), 5) if len(values) > 1 else None, 'n': len(values)}


def participant_ci(means):
    if len(means) < 2:
        return None
    rng = random.Random(20261117)
    n = len(means)
    samples = sorted(sum(rng.choices(means, k=n)) / n for _ in range(2000))
    return [round(samples[49], 5), round(samples[1949], 5)]


class Registration(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=5, max_length=180)
    age: StrictInt = Field(ge=1, le=120)
    gender: str = Field(max_length=40)
    mother_tongue: str = Field(min_length=1, max_length=80)
    organization: str = Field(min_length=1, max_length=150)
    consent: bool
    instructions_understood: bool = False


class Resume(BaseModel):
    participant_id: str = Field(min_length=5, max_length=60)
    code: str = Field(min_length=5, max_length=60)


class Login(BaseModel):
    username: str = Field(max_length=80)
    password: str = Field(max_length=200)


class Playback(BaseModel):
    clip_id: str = Field(max_length=20)
    event: str
    listened_seconds: float = Field(default=0, ge=0, le=600, allow_inf_nan=False)


class Rating(BaseModel):
    clip_id: str = Field(max_length=20)
    score: StrictInt = Field(ge=1, le=5)


class Exclusion(BaseModel):
    excluded: bool
    reason: str = Field(default='', max_length=500)


def create_app(root=ROOT, data_directory=None):
    root = Path(root)
    settings(root)
    clips = json.loads((root / 'config/stimuli.json').read_text())
    if len(clips) != 20 or any(sum(c['language'] == lang for c in clips) != 5 for lang in LANGUAGES):
        raise RuntimeError('Provision exactly five WAV files in each of the four languages before starting.')
    catalog = {clip['id']: clip for clip in clips}
    if len(catalog) != 20:
        raise RuntimeError('Stimulus IDs must be unique.')
    for clip in clips:
        path = root / 'audio' / clip['file']
        if path.parent != root / 'audio' or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != clip['sha256']:
            raise RuntimeError('Missing or altered stimulus: ' + clip['id'])
    store = Store(Path(data_directory or os.getenv('MOS_DATA_DIR')) if (data_directory or os.getenv('MOS_DATA_DIR')) else root / '.data')
    app = FastAPI(title='AAC Speech Listening Study', docs_url=None, redoc_url=None, openapi_url=None)
    app.state.store = store
    app.state.catalog = catalog
    attempts = defaultdict(deque)
    limit_lock = threading.Lock()

    def throttle(request, category, limit):
        key = (category, request.headers.get('x-mos-client-ip') or request.headers.get('cf-connecting-ip') or request.client.host)
        with limit_lock:
            current = time.time()
            if len(attempts) > 5000:
                for old in list(attempts):
                    if not attempts[old] or attempts[old][-1] < current - 900:
                        attempts.pop(old, None)
            queue = attempts[key]
            while queue and queue[0] < current - 900:
                queue.popleft()
            if len(queue) >= limit:
                raise HTTPException(429, 'Too many attempts. Please wait 15 minutes and try again.')
            queue.append(current)

    @app.middleware('http')
    async def protect(request, call_next):
        cfg = settings(root)
        host = request.url.hostname or ''
        local = host in ('127.0.0.1', 'localhost', 'testserver')
        if not local and not hmac.compare_digest(request.headers.get('x-mos-origin-key', ''), cfg['origin_key']):
            return JSONResponse({'detail': 'Use the study portal link.'}, status_code=403)
        if request.method not in ('GET', 'HEAD', 'OPTIONS'):
            origin = request.headers.get('origin')
            allowed = {cfg.get('public_origin', ''), 'http://127.0.0.1:8011', 'http://localhost:8011', 'http://testserver'}
            if local:
                allowed.add(str(request.base_url).rstrip('/'))
            if origin and origin not in allowed:
                return JSONResponse({'detail': 'Unrecognized request origin.'}, status_code=403)
            if request.headers.get('content-type', '').split(';')[0] != 'application/json':
                return JSONResponse({'detail': 'Send a JSON request.'}, status_code=415)
            if int(request.headers.get('content-length', '0') or 0) > 16384:
                return JSONResponse({'detail': 'Request is too large.'}, status_code=413)
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; media-src 'self'; connect-src 'self'; frame-ancestors 'none'; form-action 'self'; base-uri 'none'"
        response.headers['Cache-Control'] = 'no-store' if not request.url.path.startswith('/static/') else 'public,max-age=3600'
        return response

    def session(request, role):
        token = request.cookies.get('mos_admin' if role == 'admin' else 'mos_listener', '')
        with store.connect() as db:
            row = db.execute('SELECT * FROM sessions WHERE token_hash=? AND role=? AND expires>?', (token_hash(token), role, time.time())).fetchone()
            if row is None:
                raise HTTPException(401, 'Please sign in again.' if role == 'admin' else 'Please register or resume your session.')
            if role == 'participant':
                person = db.execute('SELECT * FROM participants WHERE participant_id=?', (row['participant_id'],)).fetchone()
                if person['is_excluded']:
                    raise HTTPException(403, 'Your session is paused. Please contact the study administrator.')
        return dict(row)

    def admin_session(request, write=False):
        row = session(request, 'admin')
        if write and not hmac.compare_digest(request.headers.get('x-csrf-token', ''), row['csrf']):
            raise HTTPException(403, 'Refresh the administrator page and try again.')
        return row

    def issue(db, response, role, participant_id, request):
        token = secrets.token_urlsafe(32)
        csrf = secrets.token_urlsafe(24)
        lifespan = 8 * 3600 if role == 'admin' else 30 * 86400
        db.execute('DELETE FROM sessions WHERE expires<?', (time.time(),))
        db.execute('INSERT INTO sessions VALUES(?,?,?,?,?)', (token_hash(token), role, participant_id, csrf, time.time() + lifespan))
        secure = request.headers.get('x-forwarded-proto') == 'https' or request.url.scheme == 'https'
        response.set_cookie('mos_admin' if role == 'admin' else 'mos_listener', token, max_age=lifespan,
                            httponly=True, secure=secure, samesite='lax', path='/')
        return csrf

    def listener_state(participant_id):
        with store.connect() as db:
            person = dict(db.execute('SELECT * FROM participants WHERE participant_id=?', (participant_id,)).fetchone())
            trial = db.execute('SELECT * FROM trials WHERE participant_id=? AND score IS NULL ORDER BY position LIMIT 1', (participant_id,)).fetchone()
            language_progress = {lang: dict(db.execute('SELECT COUNT(*) AS completed FROM trials WHERE participant_id=? AND clip_id LIKE ? AND score IS NOT NULL', (participant_id, lang + '-%')).fetchone())['completed'] for lang in LANGUAGES}
        current = None
        if trial:
            clip = catalog[trial['clip_id']]
            current = {'id': clip['id'], 'language': clip['language'], 'language_label': LANGUAGES[clip['language']],
                       'duration': clip['duration_seconds'], 'position': trial['position'] + 1,
                       'played': trial['play_ended'] is not None, 'audio_url': '/api/audio/' + clip['id']}
        return {'participant': {key: person[key] for key in PARTICIPANT_COLUMNS}, 'current': current,
                'total': 20, 'language_progress': language_progress, 'completed': person['trials_completed'] == 20}

    @app.get('/')
    def index():
        return FileResponse(root / 'static/index.html')

    @app.get('/admin')
    @app.get('/admin/login')
    @app.get('/admin/dashboard')
    def admin_page():
        return FileResponse(root / 'static/admin.html')

    @app.get('/api/health')
    def health():
        return {'status': 'ok', 'stimuli': len(clips), 'languages': {lang: 5 for lang in LANGUAGES}, 'storage': 'local SQLite', 'schema_version': 1}

    @app.post('/api/register')
    def register(body: Registration, request: Request, response: Response):
        throttle(request, 'register', 120)
        values = {key: getattr(body, key).strip() if isinstance(getattr(body, key), str) else getattr(body, key) for key in ('name', 'email', 'age', 'gender', 'mother_tongue', 'organization')}
        import re
        if not body.instructions_understood:
            raise HTTPException(400, 'Read the listening instructions and press I understand before registering.')
        if not body.consent or values['gender'] not in GENDERS or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', values['email']):
            raise HTTPException(400, 'Enter a valid email, gender, and consent selection.')
        if any(not values[key] for key in ('name', 'mother_tongue', 'organization')):
            raise HTTPException(400, 'Please complete every field.')
        participant_id = 'AAC-' + secrets.token_hex(5).upper()
        code = '-'.join(''.join(secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(4)) for _ in range(2))
        salt = secrets.token_hex(16)
        timestamp = now_iso()
        order = list(catalog)
        random.SystemRandom().shuffle(order)
        try:
            with store.write() as db:
                db.execute('''INSERT INTO participants(participant_id,name,email,age,gender,mother_tongue,organization,registered_iso,resume_salt,resume_hash,consent_iso)
                              VALUES(?,?,?,?,?,?,?,?,?,?,?)''', (participant_id, values['name'], values['email'].casefold(), values['age'], values['gender'], values['mother_tongue'], values['organization'], timestamp, salt, password_hash(code, salt), timestamp))
                db.executemany('INSERT INTO trials(participant_id,clip_id,position) VALUES(?,?,?)', [(participant_id, clip, index) for index, clip in enumerate(order)])
                issue(db, response, 'participant', participant_id, request)
        except sqlite3.IntegrityError:
            raise HTTPException(409, 'A registration already exists for this email. Use your participant ID and return code to resume.')
        return {**listener_state(participant_id), 'return_code': code}

    @app.post('/api/resume')
    def resume(body: Resume, request: Request, response: Response):
        throttle(request, 'resume', 60)
        with store.write() as db:
            row = db.execute('SELECT * FROM participants WHERE participant_id=?', (body.participant_id.strip().upper(),)).fetchone()
            if row is None or not hmac.compare_digest(password_hash(body.code.strip().upper(), row['resume_salt']), row['resume_hash']):
                raise HTTPException(401, 'Participant ID or return code is incorrect.')
            if row['is_excluded']:
                raise HTTPException(403, 'Your session is paused. Please contact the study administrator.')
            issue(db, response, 'participant', row['participant_id'], request)
        return listener_state(row['participant_id'])

    @app.get('/api/me')
    def me(request: Request):
        return listener_state(session(request, 'participant')['participant_id'])

    @app.post('/api/leave')
    def leave(request: Request, response: Response):
        token = request.cookies.get('mos_listener', '')
        with store.write() as db:
            db.execute('DELETE FROM sessions WHERE token_hash=?', (token_hash(token),))
        response.delete_cookie('mos_listener', path='/')
        return {'saved': True}

    @app.get('/api/audio/{clip_id}')
    def audio(clip_id: str, request: Request):
        person = session(request, 'participant')['participant_id']
        with store.connect() as db:
            row = db.execute('SELECT 1 FROM trials WHERE participant_id=? AND clip_id=?', (person, clip_id)).fetchone()
        if not row or clip_id not in catalog:
            raise HTTPException(404, 'Audio sample not found.')
        return FileResponse(root / 'audio' / catalog[clip_id]['file'], media_type='audio/wav')

    @app.post('/api/playback')
    def playback(body: Playback, request: Request):
        person = session(request, 'participant')['participant_id']
        with store.write() as db:
            trial = db.execute('SELECT * FROM trials WHERE participant_id=? AND score IS NULL ORDER BY position LIMIT 1', (person,)).fetchone()
            if not trial or trial['clip_id'] != body.clip_id:
                raise HTTPException(409, 'This sample is no longer current. Refresh your session.')
            if body.event == 'started':
                # Retain a completed first listen when the listener chooses to replay.
                db.execute('UPDATE trials SET play_started=?,play_count=play_count+1 WHERE participant_id=? AND clip_id=?', (time.time(), person, body.clip_id))
            elif body.event == 'ended':
                duration = catalog[body.clip_id]['duration_seconds']
                if trial['play_started'] is None or time.time() - trial['play_started'] < duration * .85 - .2 or body.listened_seconds < duration * .9:
                    raise HTTPException(400, 'Listen to the complete sample before rating it.')
                db.execute('UPDATE trials SET play_ended=?,listened_seconds=MAX(listened_seconds,?) WHERE participant_id=? AND clip_id=?', (time.time(), body.listened_seconds, person, body.clip_id))
            else:
                raise HTTPException(400, 'Invalid playback event.')
        return {'played': body.event == 'ended'}

    @app.post('/api/rate')
    def rate(body: Rating, request: Request):
        person = session(request, 'participant')['participant_id']
        with store.write() as db:
            existing = db.execute('SELECT * FROM trials WHERE participant_id=? AND clip_id=?', (person, body.clip_id)).fetchone()
            if existing is None:
                raise HTTPException(404, 'Sample not assigned.')
            if existing['score'] is not None:
                if existing['score'] != body.score:
                    raise HTTPException(409, 'This rating has already been saved.')
            else:
                current = db.execute('SELECT clip_id FROM trials WHERE participant_id=? AND score IS NULL ORDER BY position LIMIT 1', (person,)).fetchone()
                if current['clip_id'] != body.clip_id or existing['play_ended'] is None:
                    raise HTTPException(400, 'Listen to the current sample in full before submitting a score.')
                db.execute('UPDATE trials SET score=?,rated_iso=? WHERE participant_id=? AND clip_id=?', (body.score, now_iso(), person, body.clip_id))
                db.execute('UPDATE participants SET trials_completed=trials_completed+1 WHERE participant_id=?', (person,))
                db.execute('UPDATE participants SET completed_iso=? WHERE participant_id=? AND trials_completed=20', (now_iso(), person))
        return listener_state(person)

    @app.post('/api/admin/login')
    def login(body: Login, request: Request, response: Response):
        throttle(request, 'admin', 10)
        cfg = settings(root)
        valid_password = hmac.compare_digest(password_hash(body.password, cfg['admin_salt']), cfg['admin_password_hash'])
        if not hmac.compare_digest(body.username.encode(), cfg['admin_username'].encode()) or not valid_password:
            raise HTTPException(401, 'Username or password is incorrect.')
        with store.write() as db:
            csrf = issue(db, response, 'admin', None, request)
        return {'username': cfg['admin_username'], 'csrf': csrf}

    @app.get('/api/admin/me')
    def admin_me(request: Request):
        row = admin_session(request)
        return {'username': settings(root)['admin_username'], 'csrf': row['csrf']}

    @app.post('/api/admin/logout')
    def logout(request: Request, response: Response):
        row = admin_session(request, True)
        with store.write() as db:
            db.execute('DELETE FROM sessions WHERE token_hash=?', (row['token_hash'],))
        response.delete_cookie('mos_admin', path='/')
        return {'signed_out': True}

    def analysis(include_partial=False, include_excluded=False, participant_id=''):
        with store.connect() as db:
            people = store.participant_rows(db)
            ratings = store.rating_rows(db)
        selected = {p['participant_id'] for p in people if (include_excluded or not p['is_excluded']) and (include_partial or p['trials_completed'] == 20) and (not participant_id or p['participant_id'] == participant_id)}
        ratings = [dict(row, language=catalog[row['clip_id']]['language']) for row in ratings if row['participant_id'] in selected]
        by_person = defaultdict(list)
        for row in ratings:
            by_person[row['participant_id']].append(row['score'])
        language_rows = []
        for lang, label in LANGUAGES.items():
            rows = [row for row in ratings if row['language'] == lang]
            groups = defaultdict(list)
            for row in rows:
                groups[row['participant_id']].append(row['score'])
            means = [statistics.mean(values) for values in groups.values()]
            language_rows.append({'language': lang, 'label': label, **summarize([row['score'] for row in rows]),
                                  'participants': len(groups), 'ci95': participant_ci(means) if all(len(values) == 5 for values in groups.values()) else None, 'files': 5})
        files = [{**clip, **summarize([row['score'] for row in ratings if row['clip_id'] == clip['id']])} for clip in clips]
        means = [statistics.mean(values) for values in by_person.values()]
        return {'counts': {'registered': len(people), 'completed': sum(p['trials_completed'] == 20 for p in people),
                           'in_progress': sum(p['trials_completed'] < 20 for p in people), 'excluded': sum(p['is_excluded'] for p in people),
                           'ratings_all': sum(p['trials_completed'] for p in people), 'included_participants': len(by_person)},
                'overall': {**summarize([row['score'] for row in ratings]), 'ci95': participant_ci(means) if all(len(values) == 20 for values in by_person.values()) else None},
                'languages': language_rows, 'participants': people, 'files': files,
                'distribution': {str(score): sum(row['score'] == score for row in ratings) for score in range(1, 6)},
                'filters': {'include_partial': include_partial, 'include_excluded': include_excluded, 'participant_id': participant_id},
                'method': 'MOS is the arithmetic mean of selected ratings. Default: completed, non-excluded sessions. 95% percentile bootstrap intervals resample listener means (2,000 resamples, seed 20261117); not shown for fewer than two listeners or incomplete listener groups.'}

    @app.get('/api/admin/dashboard')
    def dashboard(request: Request, include_partial: bool = False, include_excluded: bool = False, participant_id: str = ''):
        admin_session(request)
        return analysis(include_partial, include_excluded, participant_id)

    @app.get('/api/admin/participants/{participant_id}')
    def participant_detail(participant_id: str, request: Request):
        admin_session(request)
        with store.connect() as db:
            person = db.execute('SELECT * FROM participants WHERE participant_id=?', (participant_id,)).fetchone()
            if not person:
                raise HTTPException(404, 'Participant not found.')
            rows = [dict(row) for row in db.execute('SELECT clip_id,position,score,rated_iso,play_count,listened_seconds FROM trials WHERE participant_id=? ORDER BY position', (participant_id,))]
        return {'participant': {key: person[key] for key in PARTICIPANT_COLUMNS + ['completed_iso', 'exclusion_reason']},
                'trials': [dict(row, language=catalog[row['clip_id']]['language'], text=catalog[row['clip_id']]['text']) for row in rows]}

    @app.post('/api/admin/participants/{participant_id}/exclusion')
    def exclusion(participant_id: str, body: Exclusion, request: Request):
        admin_session(request, True)
        if body.excluded and not body.reason.strip():
            raise HTTPException(400, 'Record a reason for excluding a listener.')
        with store.write() as db:
            if not db.execute('SELECT 1 FROM participants WHERE participant_id=?', (participant_id,)).fetchone():
                raise HTTPException(404, 'Participant not found.')
            db.execute('UPDATE participants SET is_excluded=?,exclusion_reason=? WHERE participant_id=?', (int(body.excluded), body.reason.strip(), participant_id))
            db.execute('INSERT INTO audit(at_iso,action,participant_id,reason) VALUES(?,?,?,?)', (now_iso(), 'exclude' if body.excluded else 'include', participant_id, body.reason.strip()))
        return {'saved': True}

    @app.get('/api/admin/export/{kind}')
    def export(kind: str, request: Request, include_partial: bool = False, include_excluded: bool = False, participant_id: str = ''):
        admin_session(request)
        with store.connect() as db:
            if kind == 'participants':
                columns, rows = PARTICIPANT_COLUMNS, store.participant_rows(db)
            elif kind == 'ratings':
                columns = RATING_COLUMNS
                rows = [dict(row, language=catalog[row['clip_id']]['language']) for row in store.rating_rows(db)]
            elif kind == 'audit':
                columns = ['at_iso', 'action', 'participant_id', 'reason']
                rows = [dict(row) for row in db.execute('SELECT * FROM audit ORDER BY id')]
            elif kind in ('languages', 'files'):
                data = analysis(include_partial, include_excluded, participant_id)
                rows = data['languages' if kind == 'languages' else 'files']
                columns = ['language', 'participants', 'n', 'mos', 'std', 'ci95'] if kind == 'languages' else ['id', 'language', 'text', 'engine', 'sha256', 'n', 'mos', 'std']
            else:
                raise HTTPException(404, 'Unknown export.')
        content = '\ufeff' + csv_text(columns, rows)
        return Response(content, media_type='text/csv; charset=utf-8', headers={'Content-Disposition': f'attachment; filename="aac_mos_{kind}.csv"'})

    app.mount('/static', StaticFiles(directory=root / 'static'), name='static')
    return app


app = create_app()
