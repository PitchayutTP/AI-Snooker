"""Local account authentication. Opaque, revocable sessions in HttpOnly cookies."""
import hashlib
import hmac
import os
import re
import secrets
import threading
import time
from collections import defaultdict, deque

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError
from .database import Base, DB, Profile, now
from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

COOKIE = 'snooker_session'
TTL = 12 * 60 * 60
ORIGINS = {'http://localhost:5173', 'http://127.0.0.1:5173',
           'http://localhost:8000', 'http://127.0.0.1:8000'}
router = APIRouter(prefix='/api/auth')


class Account(Base):
    __tablename__ = 'accounts'
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    profile_id: Mapped[int] = mapped_column(ForeignKey('profiles.id'), unique=True)
    created_at: Mapped[str] = mapped_column(String(40), default=now)


class AuthSession(Base):
    __tablename__ = 'auth_sessions'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey('accounts.id'), index=True)
    expires_at: Mapped[int] = mapped_column(Integer)


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=2**17,
                            r=8, p=1, maxmem=256*1024*1024, dklen=32)
    return f'scrypt${salt}${digest.hex()}'


DUMMY_HASH = hash_password('unused-dummy-password')


def verify_password(password, encoded):
    try:
        _, salt, _ = encoded.split('$')
        return hmac.compare_digest(hash_password(password, salt), encoded)
    except (ValueError, TypeError):
        return False


def token_digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def identity(token):
    if not token or len(token) > 256:
        return None
    with DB() as db:
        session = db.get(AuthSession, token_digest(token))
        if not session or session.expires_at <= int(time.time()):
            return None
        account = db.get(Account, session.account_id)
        profile = db.get(Profile, account.profile_id)
        return {'id': account.id, 'username': account.username, 'profile_id': profile.id,
                'display_name': profile.display_name, 'dominant_hand': profile.dominant_hand}


class LoginInput(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=1, max_length=128)

    @field_validator('username')
    @classmethod
    def normalize(cls, value):
        value = value.strip().lower()
        if not re.fullmatch(r'[a-z0-9_.-]{3,50}', value):
            raise ValueError('ชื่อผู้ใช้ต้องเป็น a-z, 0-9, จุด ขีดกลาง หรือขีดล่าง 3–50 ตัว')
        return value


class RegisterInput(LoginInput):
    password: str = Field(min_length=12, max_length=128)
    display_name: str = Field(min_length=1, max_length=100)
    dominant_hand: str = 'RIGHT'

    @field_validator('display_name')
    @classmethod
    def name(cls, value):
        if not value.strip():
            raise ValueError('กรุณาระบุชื่อที่แสดง')
        return value.strip()

    @field_validator('dominant_hand')
    @classmethod
    def hand(cls, value):
        if value not in ('LEFT', 'RIGHT'):
            raise ValueError('มือถนัดไม่ถูกต้อง')
        return value


_attempts = defaultdict(deque)
_limit_lock = threading.Lock()


def limit(request):
    # One local process: bound expensive password hashing and repeated guesses.
    key = request.client.host if request.client else 'local'
    stamp = time.monotonic()
    with _limit_lock:
        for old in list(_attempts):
            while _attempts[old] and _attempts[old][0] < stamp - 60:
                _attempts[old].popleft()
            if not _attempts[old]: del _attempts[old]
        queue = _attempts[key]
        if len(queue) >= 10:
            raise HTTPException(429, 'ลองหลายครั้งเกินไป กรุณารอ 1 นาที', headers={'Retry-After': '60'})
        queue.append(stamp)


def issue(response, account_id, previous_token):
    token = secrets.token_urlsafe(32)
    with DB.begin() as db:
        db.execute(delete(AuthSession).where(AuthSession.expires_at <= int(time.time())))
        if previous_token:
            db.execute(delete(AuthSession).where(AuthSession.token_hash == token_digest(previous_token)))
        db.add(AuthSession(token_hash=token_digest(token), account_id=account_id,
                           expires_at=int(time.time()) + TTL))
    response.set_cookie(COOKIE, token, max_age=TTL, httponly=True, samesite='strict',
                        secure=os.getenv('COOKIE_SECURE') == '1', path='/')
    response.headers['Cache-Control'] = 'no-store'
    return identity(token)


@router.post('/register', status_code=201)
def register(body: RegisterInput, request: Request, response: Response):
    limit(request)
    if request.cookies.get(COOKIE) and identity(request.cookies.get(COOKIE)):
        raise HTTPException(409, 'ออกจากระบบก่อนสร้างบัญชีใหม่')
    password_hash = hash_password(body.password)
    try:
        with DB.begin() as db:
            profile = Profile(display_name=body.display_name, dominant_hand=body.dominant_hand)
            db.add(profile); db.flush()
            account = Account(username=body.username, password_hash=password_hash, profile_id=profile.id)
            db.add(account); db.flush()
            account_id = account.id
    except IntegrityError:
        raise HTTPException(409, 'ชื่อผู้ใช้นี้ถูกใช้แล้ว') from None
    return issue(response, account_id, request.cookies.get(COOKIE))


@router.post('/login')
def login(body: LoginInput, request: Request, response: Response):
    limit(request)
    if identity(request.cookies.get(COOKIE)):
        raise HTTPException(409, 'ออกจากระบบก่อนเปลี่ยนบัญชี')
    with DB() as db:
        account = db.scalar(select(Account).where(Account.username == body.username))
        valid = verify_password(body.password, account.password_hash if account else DUMMY_HASH)
        if not account or not valid:
            raise HTTPException(401, 'ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง')
        account_id = account.id
    return issue(response, account_id, request.cookies.get(COOKIE))


@router.get('/me')
def me(request: Request):
    user = identity(request.cookies.get(COOKIE))
    if not user: raise HTTPException(401, 'กรุณาเข้าสู่ระบบ')
    return user


@router.post('/logout')
def logout(request: Request, response: Response):
    from .main import operation_lock
    from .runtime import runtime
    user = identity(request.cookies.get(COOKIE))
    with operation_lock:
        if user and runtime.owner_profile_id == user['profile_id']:
            if runtime.session_id:
                raise HTTPException(409, 'กรุณาจบรอบฝึกก่อนออกจากระบบ')
            runtime.stop()
            runtime.owner_profile_id = None
    token = request.cookies.get(COOKIE)
    if token:
        with DB.begin() as db:
            db.execute(delete(AuthSession).where(AuthSession.token_hash == token_digest(token)))
    response.delete_cookie(COOKIE, path='/')
    return {'ok': True}
