"""Redis-backed account data and revocable sessions, independent of model loading."""
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import sys
import time
import unicodedata
import uuid
from typing import Literal

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / '.runtime/python'))
import redis
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

LANGUAGES = Literal['en', 'hi', 'gu', 'mr']
COOKIE = 'aac_session'
GUEST_COOKIE = 'aac_personal_profile'
PREFIX = 'aac:v1:'
PROJECT_ID = os.getenv('AAC_FIREBASE_PROJECT_ID', 'indicaacsystemnaacl2026')
GUEST_SESSION_SECONDS = 7 * 86400
PROFILE_SECONDS = 365 * 86400


def redis_connection():
    url = os.getenv('AAC_REDIS_URL')
    local = ROOT / '.runtime/redis/connection.json'
    if not url and local.exists():
        url = json.loads(local.read_text())['url']
    return redis.Redis.from_url(url or 'redis://127.0.0.1:6380/0', decode_responses=True,
                               socket_connect_timeout=1, socket_timeout=2)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def normalized(text):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFC', text)).strip()


def validate_native(text, language):
    text = normalized(text)
    if language == 'en':
        if not re.search(r'[A-Za-z]', text) or re.search(r'[\u0900-\u0aff]', text):
            raise HTTPException(422, 'Use English text for the English language list.')
        return text
    native = r'[\u0a80-\u0aff]' if language == 'gu' else r'[\u0900-\u097f]'
    if not re.search(native, text) or re.search(r'[A-Za-z]', text):
        raise HTTPException(422, 'Use the selected language\'s native script.')
    return text


class SessionStore:
    def __init__(self, client=None):
        self.redis = client if client is not None else redis_connection()

    def session_key(self, token):
        return PREFIX + 'session:' + digest(token)

    def create(self, owner, service, lifetime, old_token=None):
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        now = time.time()
        session = dict(owner=owner, service=service, csrf=csrf, created_at=now,
                       expires_at=now + lifetime)
        with self.redis.pipeline() as tx:
            if old_token:
                tx.delete(self.session_key(old_token))
            tx.set(self.session_key(token), json.dumps(session), ex=lifetime)
            tx.execute()
        return token, session

    def read(self, token):
        if not token or len(token) > 128:
            raise HTTPException(401, 'Session missing or expired. Sign in again.')
        raw = self.redis.get(self.session_key(token))
        if not raw:
            raise HTTPException(401, 'Session missing or expired. Sign in again.')
        session = json.loads(raw)
        if session['expires_at'] <= time.time():
            self.redis.delete(self.session_key(token))
            raise HTTPException(401, 'Session expired.')
        return session

    def data_key(self, session, language, name):
        return PREFIX + 'account:' + session['owner'] + ':' + language + ':' + name

    def record(self, session, event):
        """One atomic script: retries count once; recents/frequencies remain bounded."""
        text = validate_native(event.text, event.language)
        key = self.data_key(session, event.language, event.kind)
        dedup = self.data_key(session, event.language, 'event:' + digest(event.event_id))
        item = dict(id=event.event_id, text=text, language=event.language, created_at=time.time())
        script = '''
        if not redis.call('SET', KEYS[1], '1', 'NX', 'EX', 604800) then return 0 end
        if ARGV[1] == 'word' then
            redis.call('ZINCRBY', KEYS[2], 1, ARGV[2])
            redis.call('ZREMRANGEBYRANK', KEYS[2], 0, -1001)
        else
            redis.call('LPUSH', KEYS[2], ARGV[3])
            redis.call('LTRIM', KEYS[2], 0, 99)
        end
        return 1
        '''
        created = self.redis.eval(script, 2, dedup, key, event.kind, text, json.dumps(item, ensure_ascii=False))
        return bool(created)

    def frequent(self, session, language, limit=20):
        return [dict(word=word, count=int(count), language=language)
                for word, count in self.redis.zrevrange(self.data_key(session, language, 'word'),
                                                       0, limit - 1, withscores=True)]

    def recent(self, session, language):
        return [json.loads(x) for x in self.redis.lrange(self.data_key(session, language, 'conversation'), 0, 49)]

    def bookmark(self, session, text, language):
        text = validate_native(text, language)
        bookmark_id = 'bm_' + digest(language + '\0' + text)[:24]
        item = dict(id=bookmark_id, text=text, language=language, created_at=time.time())
        key = self.data_key(session, language, 'bookmarks')
        script = '''
        local previous = redis.call('HGET', KEYS[1], ARGV[1])
        if previous then return previous end
        redis.call('HSET', KEYS[1], ARGV[1], ARGV[2])
        redis.call('ZADD', KEYS[2], ARGV[3], ARGV[1])
        local stale = redis.call('ZRANGE', KEYS[2], 0, -101)
        for _, id in ipairs(stale) do
            redis.call('HDEL', KEYS[1], id)
            redis.call('ZREM', KEYS[2], id)
        end
        return ARGV[2]
        '''
        return json.loads(self.redis.eval(script, 2, key, key + ':order', bookmark_id,
                                         json.dumps(item, ensure_ascii=False), item['created_at']))

    def bookmarks(self, session, language):
        key = self.data_key(session, language, 'bookmarks')
        ids = self.redis.zrevrange(key + ':order', 0, 99)
        if not ids:
            return []
        return [json.loads(item) for item in self.redis.hmget(key, ids) if item]

    def delete_bookmark(self, session, language, bookmark_id):
        key = self.data_key(session, language, 'bookmarks')
        with self.redis.pipeline() as tx:
            tx.hdel(key, bookmark_id)
            tx.zrem(key + ':order', bookmark_id)
            removed, _ = tx.execute()
        return bool(removed)

    def dashboard(self, session, language):
        # Pipeline avoids one network round trip per section (bookmarks are bounded).
        with self.redis.pipeline(transaction=False) as tx:
            tx.lrange(self.data_key(session, language, 'conversation'), 0, 49)
            tx.zrevrange(self.data_key(session, language, 'word'), 0, 19, withscores=True)
            tx.hgetall(self.data_key(session, language, 'bookmarks'))
            recent, frequent, bookmarks = tx.execute()
        return dict(language=language, service=session['service'],
                    recent_conversations=[json.loads(x) for x in recent],
                    frequent_words=[dict(word=w, count=int(n), language=language) for w, n in frequent],
                    bookmarks=sorted((json.loads(x) for x in bookmarks.values()),
                                     key=lambda x: x['created_at'], reverse=True))


store = SessionStore()
router = APIRouter(prefix='/api', tags=['Accounts and personal data'])


def get_store():
    return store


def same_origin(request: Request):
    origin = request.headers.get('origin')
    if origin and origin != str(request.base_url).rstrip('/'):
        raise HTTPException(403, 'Cross-origin account changes are not allowed.')


def require_session(request: Request, db=Depends(get_store)):
    try:
        return db.read(request.cookies.get(COOKIE))
    except redis.RedisError:
        raise HTTPException(503, 'Personal storage is unavailable. Please retry.')


def require_write(request: Request, session=Depends(require_session)):
    same_origin(request)
    if not secrets.compare_digest(request.headers.get('x-csrf-token', ''), session['csrf']):
        raise HTTPException(403, 'Invalid session control token.')
    return session


def public_session(session):
    return dict(profile_id=digest(session['owner']), service=session['service'],
                csrf_token=session['csrf'], expires_at=session['expires_at'], username=session.get('username'))


def set_session_cookie(response, request, token, lifetime):
    response.set_cookie(COOKIE, token, max_age=lifetime, httponly=True,
                        secure=request.url.scheme == 'https', samesite='lax', path='/')
    response.headers['Cache-Control'] = 'no-store'


@router.post('/session/guest')
def guest_session(request: Request, response: Response, db=Depends(get_store)):
    same_origin(request)
    profile = request.cookies.get(GUEST_COOKIE)
    if not profile or not re.fullmatch(r'[A-Za-z0-9_-]{43}', profile):
        profile = secrets.token_urlsafe(32)
    owner = 'guest:' + digest(profile)
    old_token = request.cookies.get(COOKIE)
    try:
        existing = db.read(old_token)
    except HTTPException:
        existing = None
    if existing and existing['owner'] == owner and existing['service'] == 'personal':
        response.headers['Cache-Control'] = 'no-store'
        return public_session(existing)
    token, session = db.create(owner, 'personal', GUEST_SESSION_SECONDS, old_token)
    response.set_cookie(GUEST_COOKIE, profile, max_age=PROFILE_SECONDS, httponly=True,
                        secure=request.url.scheme == 'https', samesite='lax', path='/')
    set_session_cookie(response, request, token, GUEST_SESSION_SECONDS)
    return public_session(session)


class GoogleLogin(BaseModel):
    id_token: str = Field(min_length=20, max_length=16384)


def verify_google_token(token):
    from google.oauth2.id_token import verify_firebase_token
    from google.auth.transport.requests import Request as GoogleRequest
    try:
        claims = verify_firebase_token(token, GoogleRequest(), audience=PROJECT_ID,
                                       clock_skew_in_seconds=180)
        if (claims.get('iss') != 'https://securetoken.google.com/' + PROJECT_ID
                or claims.get('firebase', {}).get('sign_in_provider') != 'google.com'
                or not claims.get('sub') or claims.get('exp', 0) <= time.time()):
            raise ValueError('Invalid Google identity')
        return claims
    except Exception as exc:
        from google.auth.exceptions import TransportError
        if isinstance(exc, TransportError):
            raise HTTPException(503, 'Cannot reach Google to verify sign-in. Check the server internet connection and retry.')
        message = str(exc).lower()
        if 'too early' in message:
            detail = 'The server clock differs too much from Google. Synchronize the computer clock and retry.'
        elif 'expired' in message:
            detail = 'Your Google sign-in has expired. Please sign in again.'
        elif 'audience' in message or 'issuer' in message:
            detail = 'The Google account token belongs to a different Firebase project. Check the frontend and backend Firebase configuration.'
        else:
            detail = 'Google sign-in could not be verified. Please retry Continue with Google.'
        # Never write identity tokens or exception strings containing them to logs.
        import logging
        logging.getLogger(__name__).warning('Google verification rejected (%s)', type(exc).__name__)
        raise HTTPException(401, detail)


@router.post('/session/google')
def google_session(body: GoogleLogin, request: Request, response: Response, db=Depends(get_store)):
    same_origin(request)
    claims = verify_google_token(body.id_token)
    lifetime = max(1, min(3600, int(claims['exp'] - time.time())))
    token, session = db.create('google:' + digest(claims['sub']), 'google', lifetime,
                               request.cookies.get(COOKIE))
    db.redis.set(PREFIX + 'google-user:' + digest(claims['sub']), json.dumps({
        'name': claims.get('name'), 'email': claims.get('email'), 'last_login': time.time()}))
    set_session_cookie(response, request, token, lifetime)
    return public_session(session)


@router.get('/session')
def session_info(response: Response, session=Depends(require_session)):
    response.headers['Cache-Control'] = 'no-store'
    return public_session(session)


@router.delete('/session')
def logout(request: Request, response: Response, session=Depends(require_write), db=Depends(get_store)):
    db.redis.delete(db.session_key(request.cookies[COOKIE]))
    response.delete_cookie(COOKIE, path='/')
    return {'status': 'signed_out'}


class Activity(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()), min_length=8, max_length=128, pattern=r'^[A-Za-z0-9_-]+$')
    kind: Literal['word', 'conversation']
    text: str = Field(min_length=1, max_length=2000)
    language: LANGUAGES


class Bookmark(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    language: LANGUAGES


@router.post('/personal/activity')
def activity(body: Activity, session=Depends(require_write), db=Depends(get_store)):
    if body.kind == 'word' and len(body.text) > 100:
        raise HTTPException(422, 'A frequent-word entry is limited to 100 characters.')
    return {'recorded': db.record(session, body)}


@router.get('/personal/dashboard')
def dashboard(language: LANGUAGES, response: Response, session=Depends(require_session), db=Depends(get_store)):
    response.headers['Cache-Control'] = 'no-store'
    return db.dashboard(session, language)


@router.get('/personal/recent-conversations')
def recent(language: LANGUAGES, session=Depends(require_session), db=Depends(get_store)):
    return {'items': db.recent(session, language)}


@router.get('/personal/frequent-words')
def frequent(language: LANGUAGES, session=Depends(require_session), db=Depends(get_store)):
    return {'items': db.frequent(session, language)}


@router.get('/personal/bookmarks')
def bookmarks(language: LANGUAGES, session=Depends(require_session), db=Depends(get_store)):
    return {'items': db.bookmarks(session, language)}


@router.post('/personal/bookmarks')
def add_bookmark(body: Bookmark, session=Depends(require_write), db=Depends(get_store)):
    return db.bookmark(session, body.text, body.language)


@router.delete('/personal/bookmarks/{bookmark_id}')
def delete_bookmark(bookmark_id: str, language: LANGUAGES, session=Depends(require_write), db=Depends(get_store)):
    if not re.fullmatch(r'bm_[0-9a-f]{24}', bookmark_id):
        raise HTTPException(422, 'Invalid bookmark ID.')
    if not db.delete_bookmark(session, language, bookmark_id):
        raise HTTPException(404, 'Bookmark not found.')
    return {'status': 'removed'}


async def storage_error(request: Request, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=503,
                        content={"detail": "Personal storage is unavailable. Please retry."},
                        headers={"Cache-Control": "no-store"})


def install(app):
    app.include_router(router)

    @app.middleware('http')
    async def private_cache_control(request, call_next):
        response = await call_next(request)
        if request.url.path.startswith(('/api/session', '/api/personal/')):
            response.headers['Cache-Control'] = 'no-store'
        return response

    app.add_exception_handler(redis.RedisError, storage_error)
