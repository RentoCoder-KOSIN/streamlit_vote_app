import os
import json
import pandas as pd
import datetime
import secrets
import bcrypt
import qrcode
import io
import hashlib

DATA_FILE = 'votes.csv'
CODES_FILE = 'codes.csv'
SETTINGS_FILE = 'settings.json'
AUTH_FILE = 'auth.json'
ELIGIBLE_FILE = 'eligible_ids.csv'


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


# votes

def load_votes():
    return pd.read_csv(DATA_FILE)


def save_votes(df):
    df.to_csv(DATA_FILE, index=False)


# codes

def load_codes():
    return pd.read_csv(CODES_FILE)


def save_codes(df):
    df.to_csv(CODES_FILE, index=False)


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
    return new_df


def verify_code(code):
    df = load_codes()
    match = df[df['code'] == code]
    if len(match) == 0:
        return False, 'コードが見つかりません'
    row = match.iloc[0]
    if row['used']:
        return False, 'このコードは既に使用されています'
    return True, ''


def mark_code_used(code, voter_id):
    df = load_codes()
    idx = df.index[df['code'] == code]
    if len(idx) == 0:
        return False
    i = idx[0]
    df.at[i, 'used'] = True
    df.at[i, 'used_by'] = voter_id
    df.at[i, 'used_at'] = datetime.datetime.now().isoformat()
    save_codes(df)
    return True


# settings

def get_settings():
    with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_settings(settings):
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f)


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
        return False
    df = pd.concat([df, pd.DataFrame([[h, datetime.datetime.now().isoformat(), note]], columns=['student_id_hash', 'added_at', 'note'])], ignore_index=True)
    save_eligible_df(df)
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
    return added


# QR

def make_qr_image_bytes(code: str) -> bytes:
    img = qrcode.make(code)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf.read()
