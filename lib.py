import os
import json
import pandas as pd
import datetime
import secrets
import bcrypt
import qrcode
import io
import hashlib
import logging
import csv
from typing import Any
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DATA_FILE = DATA_DIR / 'votes.csv'
CODES_FILE = DATA_DIR / 'codes.csv'
SETTINGS_FILE = DATA_DIR / 'settings.json'
AUTH_FILE = DATA_DIR / 'auth.json'
ELIGIBLE_FILE = DATA_DIR / 'eligible_ids.csv'

LOG_FILE = DATA_DIR / 'app.log'
EVENTS_FILE = DATA_DIR / 'events.csv'
MAIL_FILE = DATA_DIR / 'mail.log'


def init_files():
    # votes
    if not os.path.exists(DATA_FILE):
        df = pd.DataFrame(columns=['method', 'voter_id', 'candidate', 'timestamp'])
        df.to_csv(DATA_FILE, index=False)
    # codes
    if not os.path.exists(CODES_FILE):
        df = pd.DataFrame(columns=['code', 'issued_at', 'used', 'used_by', 'used_at'])
        df.to_csv(CODES_FILE, index=False)
    # settings
    if not os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump({'start': None, 'end': None}, f)
    # auth
    if not os.path.exists(AUTH_FILE):
        # default password: admin123 (hashed)
        hashed = hash_password('admin123')
        with open(AUTH_FILE, 'w', encoding='utf-8') as f:
            json.dump({'password_hash': hashed}, f)
    # eligible voters file
    if not os.path.exists(ELIGIBLE_FILE):
        df = pd.DataFrame(columns=['student_id_hash', 'added_at', 'note'])
        df.to_csv(ELIGIBLE_FILE, index=False)

    # initialize logging after files
    init_logging()


def init_logging():
    """Initialize logging to file and ensure events CSV exists."""
    try:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s', handlers=[logging.FileHandler(LOG_FILE, encoding='utf-8'), logging.StreamHandler()])
        # ensure events csv exists
        if not os.path.exists(EVENTS_FILE):
            with open(EVENTS_FILE, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['timestamp', 'level', 'event', 'details'])
        logging.info('Logging initialized')
    except Exception as e:
        # fall back to basic config
        logging.basicConfig(level=logging.INFO)
        logging.exception('Failed to init logging: %s', e)


def mask(s: str, show: int = 4) -> str:
    """Mask a string for logging to avoid exposing full secrets."""
    if s is None:
        return ''
    s = str(s)
    if len(s) <= show*2:
        return s[:show] + '*' * max(0, len(s) - show)
    return s[:show] + '...' + s[-show:]


def log_event(level: str, event: str, details: Any = ''):
    ts = datetime.datetime.now().isoformat()
    msg = f"{event} - {details}"
    lvl = level.upper()
    if lvl == 'INFO':
        logging.info(msg)
    elif lvl == 'WARNING':
        logging.warning(msg)
    elif lvl == 'ERROR':
        logging.error(msg)
    else:
        logging.debug(msg)
    try:
        with open(EVENTS_FILE, 'a', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([ts, lvl, event, str(details)])
    except Exception:
        logging.exception('Failed to write to events csv')


# votes

def load_votes():
    return pd.read_csv(DATA_FILE)


def save_votes(df):
    df.to_csv(DATA_FILE, index=False)
    log_event('INFO', 'save_votes', f'rows={len(df)}')


# codes

def load_codes():
    return pd.read_csv(CODES_FILE)


def save_codes(df):
    df.to_csv(CODES_FILE, index=False)
    log_event('INFO', 'save_codes', f'rows={len(df)}')


def generate_codes(n):
    df = load_codes()
    new = []
    for _ in range(n):
        code = secrets.token_urlsafe(6)
        issued_at = datetime.datetime.now().isoformat()
        new.append({'code': code, 'issued_at': issued_at, 'used': False, 'used_by': '', 'used_at': ''})
    new_df = pd.DataFrame(new)
    df = pd.concat([df, new_df], ignore_index=True)
    save_codes(df)
    log_event('INFO', 'generate_codes', f'created={len(new_df)}')
    return new_df


def verify_code(code):
    df = load_codes()
    match = df[df['code'] == code]
    if len(match) == 0:
        log_event('WARNING', 'verify_code_failed', f'code={mask(code)} reason=not_found')
        return False, 'コードが見つかりません'
    row = match.iloc[0]
    if row['used']:
        log_event('WARNING', 'verify_code_failed', f'code={mask(code)} reason=used')
        return False, 'このコードは既に使用されています'
    log_event('INFO', 'verify_code_ok', f'code={mask(code)}')
    return True, ''


def mark_code_used(code, voter_id):
    df = load_codes()
    idx = df.index[df['code'] == code]
    if len(idx) == 0:
        log_event('ERROR', 'mark_code_used_failed', f'code={mask(code)} voter_id={voter_id}')
        return False
    i = idx[0]
    df.at[i, 'used'] = True
    df.at[i, 'used_by'] = voter_id
    df.at[i, 'used_at'] = datetime.datetime.now().isoformat()
    save_codes(df)
    log_event('INFO', 'mark_code_used', f'code={mask(code)} used_by={voter_id}')
    return True


# settings

def get_settings():
    with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_settings(settings):
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f)
    log_event('INFO', 'save_settings', settings)


def voting_open():
    s = get_settings()
    if not s.get('start') or not s.get('end'):
        return True  # デフォルトで常に開く
    now = datetime.datetime.now()
    start = datetime.datetime.fromisoformat(s['start'])
    end = datetime.datetime.fromisoformat(s['end'])
    return start <= now <= end


# auth

def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except Exception:
        return False


def get_password_hash():
    with open(AUTH_FILE, 'r', encoding='utf-8') as f:
        j = json.load(f)
    return j.get('password_hash')


def set_password(pw: str):
    hashed = hash_password(pw)
    with open(AUTH_FILE, 'w', encoding='utf-8') as f:
        json.dump({'password_hash': hashed}, f)
    log_event('INFO', 'set_password', 'admin password changed')

# eligible voters

def hash_student_id(student_id: str) -> str:
    return hashlib.sha256(student_id.encode()).hexdigest()


def load_eligible_df():
    return pd.read_csv(ELIGIBLE_FILE)


def save_eligible_df(df):
    df.to_csv(ELIGIBLE_FILE, index=False)


def is_eligible(student_id: str) -> bool:
    """Accept raw student_id (string) or a pre-hashed string. Return True if student is eligible."""
    h = student_id
    # if looks like hex of sha256 (64 chars), assume already hashed
    if len(student_id) != 64 or not all(c in '0123456789abcdef' for c in student_id.lower()):
        h = hash_student_id(student_id)
    df = load_eligible_df()
    return h in df['student_id_hash'].values


def add_eligible_raw(student_id: str, note: str = ''):
    df = load_eligible_df()
    h = hash_student_id(student_id)
    if h in df['student_id_hash'].values:
        log_event('WARNING', 'add_eligible_duplicate', h)
        return False
    df = pd.concat([df, pd.DataFrame([[h, datetime.datetime.now().isoformat(), note]], columns=['student_id_hash', 'added_at', 'note'])], ignore_index=True)
    save_eligible_df(df)
    log_event('INFO', 'add_eligible', h)
    return True


def remove_eligible_hash(student_hash: str):
    df = load_eligible_df()
    df = df[df['student_id_hash'] != student_hash]
    save_eligible_df(df)
    return True


def import_eligible_from_list(raw_list):
    df = load_eligible_df()
    added = 0
    for sid in raw_list:
        h = hash_student_id(sid.strip())
        if h not in df['student_id_hash'].values:
            df = pd.concat([df, pd.DataFrame([[h, datetime.datetime.now().isoformat(), 'imported']], columns=['student_id_hash', 'added_at', 'note'])], ignore_index=True)
            added += 1
    save_eligible_df(df)
    log_event('INFO', 'import_eligible', f'added={added}')
    return added


# QR

def make_qr_image_bytes(code: str) -> bytes:
    img = qrcode.make(code)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    log_event('INFO', 'make_qr_image', f'code={mask(code)}')
    return buf.read()
