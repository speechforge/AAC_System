"""Local password accounts stored alongside personal data in persistent Redis."""
import hashlib
import json
import re
import secrets
import time
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
import personal_service as personal

router = APIRouter(prefix='/api/auth', tags=['Login and signup'])
DEMO_USERNAME = 'demo'
DEMO_PASSWORD = 'AACdemo@2026'


def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    value = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()
    return salt + ':' + value


def key(username):
    return personal.PREFIX + 'user:' + username.strip().casefold()


def seed_demo(db):
    if not db.redis.exists(key(DEMO_USERNAME)):
        db.redis.set(key(DEMO_USERNAME), json.dumps({'username': DEMO_USERNAME, 'name': 'Demo User',
            'password_hash': password_hash(DEMO_PASSWORD), 'created_at': time.time()}), nx=True)


def throttle(request, db):
    address = request.client.host if request.client else 'local'
    k = personal.PREFIX + 'auth-rate:' + personal.digest(address)
    with db.redis.pipeline() as tx:
        tx.incr(k); tx.expire(k, 600, nx=True)
        count, _ = tx.execute()
    if count > 20:
        raise HTTPException(429, 'Too many account attempts. Please retry in 10 minutes.')


class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)


class Signup(Credentials):
    name: str = Field(min_length=1, max_length=80)


def signed_in(username, request, response, db):
    token, session = db.create('local:' + username, 'local', personal.GUEST_SESSION_SECONDS,
                                request.cookies.get(personal.COOKIE))
    session['username'] = username
    db.redis.set(db.session_key(token), json.dumps(session), ex=personal.GUEST_SESSION_SECONDS)
    personal.set_session_cookie(response, request, token, personal.GUEST_SESSION_SECONDS)
    return personal.public_session(session)


@router.post('/signup')
def signup(body: Signup, request: Request, response: Response, db=Depends(personal.get_store)):
    personal.same_origin(request); throttle(request, db)
    username = body.username.strip().casefold()
    if not re.fullmatch(r'[a-z0-9][a-z0-9_.@+-]{2,63}', username):
        raise HTTPException(422, 'Use 3–64 English letters, numbers, or . _ @ + - for your username.')
    seed_demo(db)
    record = dict(username=username, name=body.name.strip() or username,
                  password_hash=password_hash(body.password), created_at=time.time())
    if not db.redis.set(key(username), json.dumps(record), nx=True):
        raise HTTPException(409, 'This username is already registered. Please sign in.')
    return signed_in(username, request, response, db)


@router.post('/login')
def login(body: Credentials, request: Request, response: Response, db=Depends(personal.get_store)):
    personal.same_origin(request); throttle(request, db); seed_demo(db)
    username = body.username.strip().casefold()
    raw = db.redis.get(key(username))
    # Perform the same expensive operation even for an unknown username.
    saved = json.loads(raw)['password_hash'] if raw else '00' * 16 + ':' + '00' * 64
    if not secrets.compare_digest(password_hash(body.password, saved.split(':')[0]), saved):
        raise HTTPException(401, 'Username or password is incorrect.')
    return signed_in(username, request, response, db)
