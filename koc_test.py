"""YKS Koçu - Streamlit uygulaması.

Kurulum: pip install -r requirements.txt
API anahtarı: .streamlit/secrets.toml içine GEMINI_API_KEY = "..."
"""

from __future__ import annotations

import hashlib
import ast
from contextlib import contextmanager
import ipaddress
import io
import json
import html
import os
import re
import socket
import sqlite3
import time
import uuid
import hmac
from html.parser import HTMLParser
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

import requests
import streamlit as st
import pandas as pd
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

try:
    from google import genai
except ImportError:
    genai = None

try:
    from PIL import Image
except ImportError:
    Image = None

try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None


# Sayfa yapılandırması Streamlit komutları arasında ilk sırada olmalıdır.
st.set_page_config(page_title="ANKA · YKS Çalışma Stüdyosu", page_icon="🔥", layout="wide")

st.markdown("""
<style>
:root { --ink:#14233b; --muted:#68778e; --brand:#3858d6; --mint:#79e0bd; --gold:#ffce73; --line:#e4e9f1; --paper:#f5f7fb; }
html, body, [data-testid="stAppViewContainer"] { background-color:var(--paper); }
[data-testid="stAppViewContainer"] .main { color:var(--ink); font-family:Inter,'Segoe UI',Roboto,sans-serif; }
[data-testid="stMainBlockContainer"] { max-width:1320px; padding-top:1.8rem; padding-bottom:4rem; }
h1,h2,h3 { color:var(--ink); font-weight:700; letter-spacing:-.025em; }
h1 { font-size:2.15rem; } h2 { font-size:1.55rem; } h3 { font-size:1.15rem; }
p, label, [data-testid="stCaptionContainer"] { color:var(--muted); }
[data-testid="stSidebar"] { background:#14233b; border-right:1px solid #23334e; }
[data-testid="stSidebar"] * { color:#e8eef9; }
.side-brand { display:flex; align-items:center; gap:10px; margin:.3rem 0 1.35rem; font-weight:800; letter-spacing:.04em; color:#fff; }
.side-mark { display:grid; place-items:center; width:36px; height:36px; border-radius:12px; background:linear-gradient(135deg,#79e0bd,#9daeff); color:#14233b; font-weight:900; }
.side-nav-label { color:#8fa2bd; font-size:.68rem; font-weight:800; letter-spacing:.16em; margin:1.1rem 0 .45rem; }
[data-testid="stSidebar"] [data-testid="stRadio"] label { padding:.62rem .72rem; border-radius:10px; transition:background .15s ease; }
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover { background:#ffffff0c; }
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) { background:#ffffff15; color:#fff; }
[data-testid="stSidebar"] [data-testid="stRadio"] label p { color:inherit; font-weight:600; }
[data-testid="stSidebar"] [role="radiogroup"] { gap:3px; }
[data-testid="stSidebar"] [data-testid="stMetric"] { background:#1c2d49; border-color:#314462; }
[data-testid="stSidebar"] [data-testid="stMetricLabel"] p { color:#aab8ce; }
.stButton button,.stDownloadButton button { min-height:2.65rem; border-radius:11px; font-weight:650; transition:transform .16s ease, box-shadow .16s ease, background .16s ease; }
.stButton button { background:var(--brand); color:white; border:1px solid var(--brand); box-shadow:0 5px 14px #3858d622; }
.stButton button:hover { background:#2947c3; color:white; border-color:#2947c3; transform:translateY(-1px); box-shadow:0 8px 20px #3858d633; }
.stDownloadButton button { background:#e8edff; color:#2a45ae; border:1px solid #d7dfff; }
.stTextInput input,.stTextArea textarea,.stDateInput input,.stTimeInput input { border-radius:10px; border-color:var(--line); background:white; }
[data-testid="stMetric"] { background:white; border:1px solid var(--line); border-radius:15px; padding:15px 17px; box-shadow:0 3px 12px #23334e08; }
[data-testid="stMetricLabel"] p { font-size:.8rem; font-weight:600; letter-spacing:.025em; }
[data-testid="stMetricValue"] { color:var(--ink); font-weight:750; }
[data-testid="stTabs"] [data-baseweb="tab-list"] { gap:7px; background:#e9edf5; padding:6px; border-radius:14px; }
[data-testid="stTabs"] [data-baseweb="tab"] { height:42px; border-radius:10px; padding:0 15px; color:#5c6b83; font-weight:600; }
[data-testid="stTabs"] [aria-selected="true"] { background:white; color:var(--brand); box-shadow:0 2px 8px #14233b12; }
[data-testid="stExpander"] { background:white; border:1px solid var(--line); border-radius:12px; }
[data-testid="stChatMessage"] { border:1px solid var(--line); border-radius:15px; background:white; padding:1rem 1.2rem; }
[data-testid="stChatInput"] textarea { border-radius:15px; border-color:#d6deec; background:white; }
.hero-card { position:relative; overflow:hidden; display:flex; align-items:center; justify-content:space-between; gap:1.5rem; min-height:245px; padding:2rem 2.4rem; margin:.25rem 0 1.35rem; border-radius:24px; color:white; background:linear-gradient(115deg,#152741 0%,#223f70 57%,#3959d5 100%); box-shadow:0 18px 45px #1d37602a; }
.hero-card:after { content:''; position:absolute; width:280px; height:280px; border-radius:50%; right:16%; top:-190px; background:#79e0bd20; }
.hero-copy { position:relative; z-index:1; max-width:620px; }
.hero-eyebrow { color:#a9f1d8; text-transform:uppercase; font-size:.75rem; font-weight:750; letter-spacing:.15em; }
.hero-card h1 { color:white; font-size:clamp(2rem,4vw,3rem); line-height:1.08; margin:.55rem 0 .8rem; }
.hero-card p { color:#d0d9e9; font-size:1rem; max-width:520px; margin:0; }
.hero-pill { display:inline-flex; margin-top:1.25rem; padding:.48rem .8rem; border:1px solid #ffffff35; border-radius:999px; background:#ffffff12; color:#f2f6ff; font-size:.8rem; }
.hero-art { width:min(31%,300px); min-width:180px; position:relative; z-index:1; }
.section-kicker { color:var(--brand); font-size:.72rem; font-weight:750; text-transform:uppercase; letter-spacing:.13em; margin-bottom:.35rem; }
.soft-card { height:100%; padding:1.15rem 1.25rem; border:1px solid var(--line); border-radius:16px; background:white; box-shadow:0 4px 16px #1d2c4408; }
.soft-card h3 { margin:.25rem 0 .4rem; } .soft-card p { margin:0; font-size:.91rem; line-height:1.55; }
.mini-icon { display:inline-grid; place-items:center; width:38px; height:38px; border-radius:12px; background:#edf0ff; font-size:1.2rem; }
.empty-state { border:1px dashed #ccd5e4; border-radius:16px; padding:1.3rem; color:var(--muted); background:#ffffffa6; }
.week-empty { min-height:230px;display:flex;align-items:center;gap:1.2rem;padding:1.5rem;border:1px solid var(--line);border-radius:18px;background:linear-gradient(135deg,#fff,#f4f6fa);box-shadow:0 8px 25px #1d2c4408; }
.week-empty-copy strong { display:block;color:var(--ink);font-size:1.02rem;margin-bottom:.35rem; }
.week-empty-copy span { display:block;color:var(--muted);font-size:.88rem;line-height:1.55;max-width:300px; }
.study-heatmap { display:grid;grid-template-columns:repeat(14,minmax(16px,1fr));gap:7px;padding:.9rem;border:1px solid var(--line);border-radius:15px;background:linear-gradient(145deg,#fff,#f6f4f2); }
.heat-cell { display:block;width:18px;height:18px;border-radius:5px;background:#eee9e6;border:1px solid #d9d1cd; }
.study-heatmap .heat-cell { width:100%;height:auto;aspect-ratio:1; }
.heat-1 { background:#f6c7ad!important;border-color:#edb99b!important; } .heat-2 { background:#ee9978!important;border-color:#e58b69!important; }
.heat-3 { background:#d75b43!important;border-color:#c84c36!important; } .heat-4 { background:#842a27!important;border-color:#842a27!important; }
.heat-legend { display:flex;align-items:center;gap:6px;justify-content:flex-end;margin-top:8px;font-size:.73rem;color:var(--muted); }
.heat-legend .heat-cell { width:13px;height:13px;border-radius:4px; }
.week-bars { height:112px;display:flex;align-items:flex-end;gap:7px;padding:12px;border-radius:14px;background:linear-gradient(180deg,#f6f7fa,#eef1f6); }
.week-bars i { width:12px;border-radius:7px 7px 3px 3px;background:linear-gradient(180deg,#e48a56,#bb483d);opacity:.3; }
.calendar-day { min-height:148px;padding:.7rem;border:1px solid var(--line);border-radius:14px;background:linear-gradient(145deg,#fff,#f4f5f8);box-shadow:0 5px 16px #1d2c4408; }
.calendar-day.is-today { border-color:#da7650;box-shadow:0 0 0 2px #da765022; }
.calendar-day small,.calendar-day strong,.calendar-day span { display:block; }
.calendar-day small { color:var(--muted);font-size:.66rem;font-weight:800;text-transform:uppercase;letter-spacing:.08em; }
.calendar-day strong { color:var(--ink);font-size:1.35rem; }
.calendar-day span { color:var(--muted);font-size:.64rem;margin:.2rem 0 .45rem; }
.calendar-day ul { margin:0;padding-left:.8rem;color:var(--ink);font-size:.62rem;line-height:1.45; }
.calendar-day li { margin-bottom:.2rem; }
.calendar-day .calendar-quiet { color:var(--muted);list-style:none; }
.focus-timer-card { text-align:center;margin:1rem auto 1.5rem;padding:2.5rem 1rem;border:1px solid #e6cdbf;border-radius:28px;background:radial-gradient(circle at 50% 48%,#e7603c20,transparent 39%),linear-gradient(145deg,#202027,#17191f);box-shadow:0 20px 60px #120a0870; }
.focus-live { color:#ffb96d;font-size:.72rem;font-weight:800;letter-spacing:.18em; }
.focus-clock { margin:.35rem 0;font-size:clamp(4rem,12vw,7.5rem);font-weight:850;letter-spacing:-.07em;line-height:1.1;color:#fff6e9;text-shadow:0 0 36px #ff714355;font-variant-numeric:tabular-nums; }
.focus-subject { color:#d0c5bd;font-size:.95rem; }
@media(max-width:760px) { .week-empty { min-height:180px;padding:1rem;gap:.8rem; } .week-bars { gap:4px;padding:8px; } .week-bars i { width:8px; } }
@media(max-width:760px) { [data-testid="stMainBlockContainer"] { padding:1rem 1rem 3rem; } .hero-card { min-height:200px; padding:1.5rem; border-radius:19px; } .hero-art { width:26%; min-width:100px; } .hero-card h1 { font-size:2rem; } [data-testid="stTabs"] [data-baseweb="tab"] { padding:0 9px; font-size:.82rem; } }
@media(prefers-reduced-motion:reduce) { *, *:before, *:after { transition:none !important; scroll-behavior:auto !important; } }
</style>
""", unsafe_allow_html=True)

MEMORY_DIR = Path(__file__).resolve().parent / "yks_hafiza_kayitlari"
MAX_MEMORY_CHARS = 4000
MEMORY_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = MEMORY_DIR / "yks_kocu.sqlite3"


@contextmanager
def db_connect():
    connection = sqlite3.connect(DB_PATH, timeout=15)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db():
    with db_connect() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS records (
                id TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                type TEXT NOT NULL, title TEXT NOT NULL, created_at TEXT NOT NULL, content TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS records_user_created ON records(user_id, created_at);
            CREATE TABLE IF NOT EXISTS app_data (
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                key TEXT NOT NULL, value TEXT NOT NULL, PRIMARY KEY(user_id, key)
            );
            CREATE TABLE IF NOT EXISTS study_rooms (
                code TEXT PRIMARY KEY, owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                duration_minutes INTEGER NOT NULL, started_at REAL, created_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS study_room_members (
                room_code TEXT NOT NULL REFERENCES study_rooms(code) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                joined_at REAL NOT NULL, PRIMARY KEY(room_code,user_id)
            );
        """)


init_db()


def password_digest(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 310_000).hex()


def create_account(username: str, password: str):
    username = username.strip()
    if not re.fullmatch(r"[A-Za-z0-9_.-]{3,10}", username):
        return None, "Kullanıcı adı 3–10 karakter olmalı; İngilizce harf, rakam, nokta, tire veya alt çizgi kullanın."
    if not re.fullmatch(r"\d{4}", password):
        return None, "Parola tam olarak 4 rakamdan oluşmalı."
    salt = os.urandom(16).hex()
    try:
        with db_connect() as db:
            cur = db.execute("INSERT INTO users(username,password_hash,salt,created_at) VALUES(?,?,?,?)",
                             (username, password_digest(password, salt), salt, datetime.now().astimezone().isoformat()))
            user_id = cur.lastrowid
        # Eski sürümde aynı rumuzla oluşmuş JSONL hafızayı, yeni hesabın SQLite kaydına taşı.
        legacy_hash = hashlib.sha256(username.strip().casefold().encode("utf-8")).hexdigest()[:20]
        legacy_path = MEMORY_DIR / f"hafiza_{legacy_hash}.jsonl"
        if legacy_path.exists():
            with legacy_path.open("r", encoding="utf-8") as handle, db_connect() as db:
                for line in handle:
                    try:
                        old = json.loads(line)
                        db.execute("INSERT OR IGNORE INTO records(id,user_id,type,title,created_at,content) VALUES(?,?,?,?,?,?)",
                                   (old.get("id") or uuid.uuid4().hex[:12], user_id, old.get("type", "eski_kayit"),
                                    old.get("title", "Eski kayıt"), old.get("created_at", datetime.now().isoformat()), old.get("content", "")))
                    except (json.JSONDecodeError, AttributeError):
                        continue
        return user_id, None
    except sqlite3.IntegrityError:
        return None, "Bu kullanıcı adı zaten kayıtlı."


def authenticate(username: str, password: str):
    with db_connect() as db:
        row = db.execute("SELECT id,password_hash,salt FROM users WHERE username=? COLLATE NOCASE", (username.strip(),)).fetchone()
    if not row or not hmac.compare_digest(password_digest(password, row["salt"]), row["password_hash"]):
        return None
    return row["id"]


def account_backup(user_id: int) -> bytes:
    with db_connect() as db:
        user = db.execute("SELECT username,created_at FROM users WHERE id=?", (user_id,)).fetchone()
        records = [dict(row) for row in db.execute(
            "SELECT id,type,title,created_at,content FROM records WHERE user_id=? ORDER BY created_at", (user_id,)
        )]
        data = {row["key"]: json.loads(row["value"]) for row in db.execute(
            "SELECT key,value FROM app_data WHERE user_id=?", (user_id,)
        )}
    payload = {"format_version": 1, "username": user["username"], "created_at": user["created_at"],
               "exported_at": datetime.now().astimezone().isoformat(), "records": records, "app_data": data}
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def restore_account_backup(user_id: int, uploaded_file) -> tuple[bool, str]:
    """Restore this account's app data and notes from a validated local JSON backup."""
    try:
        if uploaded_file.size > 10 * 1024 * 1024:
            return False, "Yedek dosyası 10 MB sınırını aşıyor."
        payload = json.loads(uploaded_file.getvalue().decode("utf-8"))
        if not isinstance(payload, dict) or payload.get("format_version") != 1:
            return False, "Bu dosya tanınan ANKA yedek biçiminde değil."
        if payload.get("offline_kit") is True:
            events = payload.get("changes", [])
            if not isinstance(events, list) or len(events) > 5000:
                return False, "Çevrimdışı eşitleme dosyası geçersiz."
            tasks = read_user_json(user_id, "study_tasks", [])
            notes = read_user_json(user_id, "notes", [])
            sessions = read_user_json(user_id, "study_sessions", [])
            task_lookup = {str(item.get("id")): item for item in tasks if isinstance(item, dict)}
            applied = 0
            for event in events:
                if not isinstance(event, dict):
                    continue
                if event.get("type") == "task_done" and str(event.get("task_id")) in task_lookup:
                    task_lookup[str(event["task_id"])]["done"] = bool(event.get("done"))
                    if event.get("done"):
                        award_xp(user_id, f"task:{event['task_id']}", 10, "Çevrimdışı tamamlanan görev")
                    applied += 1
                elif event.get("type") == "note" and isinstance(event.get("text"), str) and event["text"].strip():
                    if not any(item.get("id") == event.get("id") for item in notes if isinstance(item, dict)):
                        notes.append({"id": str(event.get("id") or uuid.uuid4().hex[:12]), "created_at": datetime.now().astimezone().isoformat(timespec="minutes"), "text": event["text"][:2000]})
                        applied += 1
                elif event.get("type") == "study_session" and isinstance(event.get("minutes"), int):
                    if 1 <= event["minutes"] <= 600 and not any(item.get("id") == event.get("id") for item in sessions if isinstance(item, dict)):
                        sessions.append({"id": str(event.get("id") or uuid.uuid4().hex[:10]), "date": str(event.get("date", date.today().isoformat())),
                                         "minutes": event["minutes"], "subject": str(event.get("subject", "Diğer"))[:40], "note": "Çevrimdışı yardımcı"})
                        award_xp(user_id, f"session:{sessions[-1]['id']}", max(5, event["minutes"] // 5), "Çevrimdışı çalışma")
                        applied += 1
            write_user_json(user_id, "study_tasks", tasks)
            write_user_json(user_id, "notes", notes)
            write_user_json(user_id, "study_sessions", sessions)
            return True, f"Çevrimdışı değişiklikler içe aktarıldı: {applied} kayıt işlendi."
        app_data = payload.get("app_data", {})
        records = payload.get("records", [])
        if not isinstance(app_data, dict) or not isinstance(records, list):
            return False, "Yedek dosyasındaki kayıt yapısı geçersiz."
        if len(records) > 20000 or len(app_data) > 100:
            return False, "Yedekte beklenenden fazla kayıt var. Dosyayı kontrol edin."
        with db_connect() as db:
            for key, value in app_data.items():
                if not isinstance(key, str) or len(key) > 100:
                    continue
                encoded = json.dumps(value, ensure_ascii=False)
                db.execute("INSERT INTO app_data(user_id,key,value) VALUES(?,?,?) "
                           "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value",
                           (user_id, key, encoded))
            for item in records:
                if not isinstance(item, dict):
                    continue
                record_id = str(item.get("id") or uuid.uuid4().hex[:12])[:100]
                db.execute("INSERT INTO records(id,user_id,type,title,created_at,content) VALUES(?,?,?,?,?,?) "
                           "ON CONFLICT(id) DO UPDATE SET type=excluded.type,title=excluded.title,"
                           "created_at=excluded.created_at,content=excluded.content WHERE records.user_id=excluded.user_id",
                           (record_id, user_id, str(item.get("type", "eski_kayit"))[:100],
                            str(item.get("title", "Yedekten gelen kayıt"))[:300],
                            str(item.get("created_at", datetime.now().astimezone().isoformat()))[:100],
                            str(item.get("content", ""))[:MAX_MEMORY_CHARS]))
        return True, f"Yedek geri yüklendi: {len(records)} hafıza kaydı ve {len(app_data)} veri alanı işlendi."
    except (UnicodeDecodeError, json.JSONDecodeError, AttributeError, TypeError, ValueError) as exc:
        return False, f"Yedek okunamadı: {exc}"


def logout_user() -> None:
    # Aynı tarayıcıdan başka hesapla giriş yapılırken önceki hesabın arayüz önbelleğini temizle.
    for key in list(st.session_state.keys()):
        del st.session_state[key]


def configure_gemini() -> bool:
    """API anahtarını secrets veya ortam değişkeninden alıp Gemini'yi hazırlar."""
    if genai is None:
        st.error("Gemini paketi bulunamadı. `pip install google-genai` komutunu çalıştırın.")
        return False
    try:
        key = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
    except Exception:
        key = os.getenv("GEMINI_API_KEY")
    if not key:
        return False
    st.session_state.gemini_client = genai.Client(api_key=key)
    return True


def get_model():
    client = st.session_state.get("gemini_client")
    if client is None:
        raise RuntimeError("Gemini hazır değil. GEMINI_API_KEY ve google-genai kurulumunu kontrol edin.")
    return client


def load_memory(user_id: int) -> list[dict]:
    with db_connect() as db:
        return [dict(row) for row in db.execute(
            "SELECT id,type,title,created_at,content FROM records WHERE user_id=? ORDER BY created_at,id", (user_id,)
        )]


def save_memory(user_id: int, record_type: str, content: str, title: str = "") -> None:
    now = datetime.now().astimezone()
    record = {
        "id": hashlib.sha256(f"{now.isoformat()}-{os.urandom(8).hex()}".encode()).hexdigest()[:12],
        "type": record_type,
        "title": title.strip() or "Başlıksız kayıt",
        "created_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "content": content,
    }
    with db_connect() as db:
        db.execute("INSERT INTO records(id,user_id,type,title,created_at,content) VALUES(?,?,?,?,?,?)",
                   (record["id"], user_id, record["type"], record["title"], record["created_at"], content))


def delete_memory_record(user_id: int, record_id: str) -> None:
    with db_connect() as db:
        db.execute("DELETE FROM records WHERE user_id=? AND id=?", (user_id, record_id))


def memory_to_text(records: list[dict]) -> str:
    chunks = []
    for i, record in enumerate(records[-25:], start=1):
        chunks.append(
            f"KAYIT {i}\nTür: {record.get('type', 'bilinmiyor')}\n"
            f"Başlık: {record.get('title', 'Başlık yok')}\n"
            f"İçerik: {record.get('content', '')}"
        )
    return "\n\n".join(chunks)[-MAX_MEMORY_CHARS:]


def generate_text(prompt: str) -> str:
    response = get_model().models.generate_content(model="gemini-2.5-flash", contents=prompt)
    text = getattr(response, "text", None)
    if not text:
        raise RuntimeError("Yapay zekâ boş yanıt döndürdü. İsteği yeniden deneyin.")
    return text.strip()


def analyze_image(uploaded_file) -> str:
    if Image is None:
        raise RuntimeError("Görsel analizi için Pillow gerekli: `pip install pillow`.")
    uploaded_file.seek(0)
    image = Image.open(uploaded_file).convert("RGB")
    prompt = (
        "Bu bir YKS hazırlık sorusu. Önce soruyu doğru okuyup çözümünü adım adım anlat. "
        "Öğrencinin olası hatasını belirt, hata türünü dikkat/bilgi/süre olarak sınıflandır "
        "ve kısa bir pekiştirme ödevi öner. Görselde okunmayan yer varsa bunu açıkça söyle."
    )
    return generate_image_response(prompt, image)


def generate_image_response(prompt: str, image) -> str:
    from google.genai import types
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    response = get_model().models.generate_content(
        model="gemini-2.5-flash",
        contents=[prompt, types.Part.from_bytes(data=buffer.getvalue(), mime_type="image/jpeg")],
    )
    text = getattr(response, "text", None)
    if not text:
        raise RuntimeError("Görsel için yanıt alınamadı.")
    return text.strip()


def safe_calculate(expression: str) -> str:
    """JARVIS hesap makinesi: eval kullanmadan temel aritmetiği işler."""
    operations = {ast.Add: lambda a, b: a + b, ast.Sub: lambda a, b: a - b,
                  ast.Mult: lambda a, b: a * b, ast.Div: lambda a, b: a / b,
                  ast.Pow: lambda a, b: a ** b, ast.Mod: lambda a, b: a % b}

    def visit(node):
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return node.value
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = visit(node.operand)
            return value if isinstance(node.op, ast.UAdd) else -value
        if isinstance(node, ast.BinOp) and type(node.op) in operations:
            value = operations[type(node.op)](visit(node.left), visit(node.right))
            if abs(value) > 1e100:
                raise ValueError("Sonuç çok büyük")
            return value
        raise ValueError("Desteklenmeyen işlem")

    try:
        answer = visit(ast.parse(expression.replace(",", "."), mode="eval").body)
        return f"İşlemin sonucu: {answer:g}"
    except (ArithmeticError, SyntaxError, ValueError, OverflowError):
        return "Bu matematiksel ifadeyi hesaplayamadım. Örnek: hesapla 24 * (3 + 2)"


def read_user_json(user_id: int, name: str, default):
    with db_connect() as db:
        row = db.execute("SELECT value FROM app_data WHERE user_id=? AND key=?", (user_id, name)).fetchone()
    if not row:
        return default
    try:
        return json.loads(row["value"])
    except json.JSONDecodeError:
        return default


def write_user_json(user_id: int, name: str, payload) -> None:
    encoded = json.dumps(payload, ensure_ascii=False)
    with db_connect() as db:
        db.execute("INSERT INTO app_data(user_id,key,value) VALUES(?,?,?) "
                   "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value", (user_id, name, encoded))


def award_xp(user_id: int, event_id: str, points: int, label: str) -> None:
    """Award XP once per persisted study event, so reruns cannot double count."""
    events = read_user_json(user_id, "xp_events", [])
    if any(item.get("id") == event_id for item in events if isinstance(item, dict)):
        return
    events.append({"id": event_id, "points": max(0, int(points)), "label": label,
                   "date": date.today().isoformat()})
    write_user_json(user_id, "xp_events", events)


def xp_profile(user_id: int) -> dict:
    events = read_user_json(user_id, "xp_events", [])
    xp = sum(max(0, int(item.get("points", 0))) for item in events if isinstance(item, dict))
    ranks = [(0, "Közden Doğan"), (100, "Anka Yavrusu"), (300, "Alev Kanatlı"),
             (700, "Göklerin Anka'sı"), (1500, "Efsanevi Anka")]
    rank_index = max(index for index, (threshold, _) in enumerate(ranks) if xp >= threshold)
    threshold, title = ranks[rank_index]
    next_threshold = ranks[rank_index + 1][0] if rank_index + 1 < len(ranks) else threshold
    return {"xp": xp, "title": title, "next": next_threshold,
            "progress": 1.0 if next_threshold == threshold else (xp - threshold) / (next_threshold - threshold)}


def offline_kit_html(user_id: int) -> str:
    seed = {"tasks": read_user_json(user_id, "study_tasks", []),
            "questions": read_user_json(user_id, "wrong_questions", []),
            "notes": read_user_json(user_id, "notes", [])}
    seed_json = json.dumps(seed, ensure_ascii=False).replace("</", "<\\/")
    page = r'''<!doctype html><html lang="tr"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#17121f"><title>ANKA · Çevrimdışı çalışma</title>
<style>*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 80% 0,#522248,#12121a 48%);color:#f7eff8;font:16px system-ui,sans-serif}main{max-width:900px;margin:auto;padding:24px}header,.card{background:#211c2acc;border:1px solid #ffffff20;border-radius:20px;padding:20px;margin:14px 0;backdrop-filter:blur(14px)}h1{margin:0;color:#ffbe83}small,.muted{color:#c9bbce}button{background:linear-gradient(110deg,#9b43bd,#d34463);color:white;border:0;border-radius:12px;padding:11px 16px;font-weight:700;cursor:pointer}input,textarea{background:#15141c;color:#fff;border:1px solid #514257;border-radius:10px;padding:10px;width:100%;margin:6px 0}li{margin:10px 0}.timer{font-size:64px;font-weight:800;text-align:center;font-variant-numeric:tabular-nums}.row{display:flex;gap:10px;align-items:center}.row button{flex:none}</style>
<main><header><small>ANKA · YKS ÇALIŞMA STÜDYOSU</small><h1>Çevrimdışı çalışma kiti</h1><p class="muted">Bu tek dosya internet olmadan çalışır. Kayıtlar bu cihazın tarayıcı deposunda tutulur.</p></header>
<section class="card"><h2>Odak sayacı</h2><div class="timer" id="clock">25:00</div><div class="row"><button onclick="toggleTimer()" id="timerBtn">Başlat</button><button onclick="resetTimer()">Sıfırla</button><select id="subject"><option>Matematik</option><option>Türkçe</option><option>Fizik</option><option>Kimya</option><option>Biyoloji</option><option>Diğer</option></select></div></section>
<section class="card"><h2>Bugünkü plan</h2><ul id="tasks"></ul></section><section class="card"><h2>Yanlış soru tekrarların</h2><ul id="questions"></ul></section>
<section class="card"><h2>Çevrimdışı not</h2><textarea id="note" rows="3" placeholder="Notunu yaz..."></textarea><button onclick="saveNote()">Notu kaydet</button><ul id="notes"></ul></section>
<section class="card"><h2>Siteyle eşitle</h2><p class="muted">İnternet gelince değişiklik dosyasını indirip ANKA’daki “Yedekten geri yükle” alanına aktar. Eşitleme yalnızca bu dosyayı seçtiğinde yapılır.</p><button onclick="exportChanges()">Değişiklikleri JSON indir</button> <label><input type="file" id="importFile" accept="application/json" onchange="importChanges(event)">Değişiklik JSON’unu içe al</label></section></main>
<script>const SEED=__SEED__;const STORE='anka_offline_v1';let state=JSON.parse(localStorage.getItem(STORE)||'null')||{tasks:SEED.tasks,questions:SEED.questions,notes:SEED.notes,changes:[]};function save(){localStorage.setItem(STORE,JSON.stringify(state))}function el(tag,text){const n=document.createElement(tag);n.textContent=text;return n}function render(){const t=document.getElementById('tasks');t.replaceChildren();state.tasks.filter(x=>x.date===new Date().toISOString().slice(0,10)).forEach(x=>{const li=el('li','');const c=document.createElement('input');c.type='checkbox';c.checked=!!x.done;c.onchange=()=>{x.done=c.checked;state.changes.push({type:'task_done',task_id:x.id,done:x.done});save()};li.append(c,document.createTextNode(' '+[x.subject,x.topic,x.target].filter(Boolean).join(' · ')));t.append(li)});const q=document.getElementById('questions');q.replaceChildren();state.questions.filter(x=>!x.mastered).forEach(x=>q.append(el('li',[x.subject,x.topic,'Tekrar: '+(x.next_review||'belirlenmedi')].filter(Boolean).join(' · '))));const n=document.getElementById('notes');n.replaceChildren();state.notes.slice(-20).reverse().forEach(x=>n.append(el('li',typeof x==='string'?x:x.text||'')))}function saveNote(){const v=document.getElementById('note').value.trim();if(!v)return;const id=crypto.randomUUID();state.notes.push({id,text:v});state.changes.push({type:'note',id,text:v});document.getElementById('note').value='';save();render()}let left=1500,handle=null;function paint(){document.getElementById('clock').textContent=String(Math.floor(left/60)).padStart(2,'0')+':'+String(left%60).padStart(2,'0')}function toggleTimer(){if(handle){clearInterval(handle);handle=null;document.getElementById('timerBtn').textContent='Devam et';return}document.getElementById('timerBtn').textContent='Duraklat';handle=setInterval(()=>{left=Math.max(0,left-1);paint();if(!left){clearInterval(handle);handle=null;state.changes.push({type:'study_session',id:crypto.randomUUID(),date:new Date().toISOString().slice(0,10),minutes:25,subject:document.getElementById('subject').value});save();document.getElementById('timerBtn').textContent='Seans tamamlandı'}},1000)}function resetTimer(){if(handle)clearInterval(handle);handle=null;left=1500;paint();document.getElementById('timerBtn').textContent='Başlat'}function exportChanges(){const data={format_version:1,offline_kit:true,changes:state.changes};const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));a.download='anka-cevrimdisi-degisiklikler.json';a.click();URL.revokeObjectURL(a.href)}function importChanges(e){const f=e.target.files[0];if(!f)return;f.text().then(s=>{const d=JSON.parse(s);if(d.offline_kit&&Array.isArray(d.changes)){state.changes.push(...d.changes);save();alert('Değişiklikler içe alındı.');}}).catch(()=>alert('Dosya okunamadı.'))}render();paint();</script></html>'''
    return page.replace("const SEED=__SEED__;", f"const SEED={seed_json};")


def leaderboard_rows(current_user_id: int, friend_names: list[str]) -> list[dict]:
    """Return weekly study totals only for friends who explicitly opted in."""
    if not friend_names:
        return []
    placeholders = ",".join("?" for _ in friend_names)
    start_day = (date.today() - timedelta(days=6)).isoformat()
    end_day = date.today().isoformat()
    with db_connect() as db:
        rows = db.execute(f"SELECT u.id,u.username,d.value,y.value AS ypt_value FROM users u "
                           f"JOIN app_data consent ON consent.user_id=u.id AND consent.key='leaderboard_opt_in' AND consent.value='true' "
                           f"LEFT JOIN app_data d ON d.user_id=u.id AND d.key='study_sessions' "
                           f"LEFT JOIN app_data y ON y.user_id=u.id AND y.key='ypt_sessions' "
                           f"WHERE u.username COLLATE NOCASE IN ({placeholders})", tuple(friend_names)).fetchall()
    output = []
    for row in rows:
        try:
            sessions = json.loads(row["value"] or "[]")
        except (TypeError, json.JSONDecodeError):
            sessions = []
        try:
            ypt_sessions = json.loads(row["ypt_value"] or "[]")
        except (TypeError, json.JSONDecodeError):
            ypt_sessions = []
        minutes = sum(max(0, int(item.get("minutes", 0))) for item in sessions + ypt_sessions
                      if isinstance(item, dict) and start_day <= item.get("date", "") <= end_day)
        output.append({"Arkadaş": row["username"], "7 günlük çalışma": minutes})
    return sorted(output, key=lambda item: item["7 günlük çalışma"], reverse=True)


def create_study_room(user_id: int, duration: int) -> str:
    code = uuid.uuid4().hex[:6].upper()
    now = time.time()
    with db_connect() as db:
        db.execute("INSERT INTO study_rooms(code,owner_id,duration_minutes,started_at,created_at) VALUES(?,?,?,NULL,?)",
                   (code, user_id, int(duration), now))
        db.execute("INSERT INTO study_room_members(room_code,user_id,joined_at) VALUES(?,?,?)", (code, user_id, now))
    return code


def join_study_room(user_id: int, code: str) -> bool:
    now = time.time()
    with db_connect() as db:
        room = db.execute("SELECT code,created_at FROM study_rooms WHERE code=?", (code.strip().upper(),)).fetchone()
        if not room or now - room["created_at"] > 86400:
            return False
        db.execute("INSERT OR IGNORE INTO study_room_members(room_code,user_id,joined_at) VALUES(?,?,?)",
                   (room["code"], user_id, now))
    return True


def start_study_room(user_id: int, code: str) -> bool:
    with db_connect() as db:
        result = db.execute("UPDATE study_rooms SET started_at=? WHERE code=? AND owner_id=? AND started_at IS NULL",
                            (time.time(), code, user_id))
    return result.rowcount > 0


def get_study_room(user_id: int, code: str):
    with db_connect() as db:
        room = db.execute("SELECT r.* FROM study_rooms r JOIN study_room_members m ON m.room_code=r.code "
                          "WHERE r.code=? AND m.user_id=?", (code, user_id)).fetchone()
        if not room:
            return None, []
        members = db.execute("SELECT u.username FROM study_room_members m JOIN users u ON u.id=m.user_id "
                             "WHERE m.room_code=? ORDER BY m.joined_at", (code,)).fetchall()
    return dict(room), [row["username"] for row in members]


def create_new_chat(user_id: int) -> None:
    chats = read_user_json(user_id, "chats", [])
    chat = {"id": uuid.uuid4().hex[:12], "title": "Yeni sohbet", "messages": []}
    chats.append(chat)
    write_user_json(user_id, "chats", chats)
    st.session_state.active_chat = chat["id"]
    # Callback çalışırken selectbox henüz çizilmedi; yeni sohbeti aktif seç.
    st.session_state.chat_selector = chat["id"]


def render_reminders(user_id: int):
    reminders = read_user_json(user_id, "reminders", [])
    now = datetime.now().astimezone()
    for reminder in reminders:
        try:
            due = datetime.fromisoformat(reminder["due_at"])
            if due.tzinfo is None:
                due = due.astimezone()
            if not reminder.get("done") and due <= now:
                st.warning(f"⏰ Hatırlatma zamanı geldi: {reminder.get('text', '')}")
            else:
                st.write(f"{'✅' if reminder.get('done') else '⏰'} {due.astimezone():%d.%m.%Y %H:%M} — {reminder.get('text', '')}")
            if not reminder.get("done") and st.button("Tamamlandı", key=f"done_reminder_{reminder.get('id')}"):
                for item in reminders:
                    if item.get("id") == reminder.get("id"):
                        item["done"] = True
                write_user_json(user_id, "reminders", reminders)
                st.rerun()
        except (KeyError, ValueError):
            continue


if hasattr(st, "fragment"):
    render_reminders = st.fragment(run_every="30s")(render_reminders)


def scrape_link(url: str, max_chars: int = 6000):
    """HTTP(S) sayfasının metnini alır; özel ağ adreslerini ve yönlendirmeleri reddeder."""
    url = url.strip()
    if not re.match(r"^https?://", url, re.IGNORECASE):
        url = "https://" + url
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in {"http", "https"} or not host or host in {"localhost", "127.0.0.1", "::1"}:
        return None, "Geçerli ve herkese açık bir http(s) adresi girin."
    if host.endswith((".local", ".internal")):
        return None, "Yerel ağ adresleri okunamaz."
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)}
        if not addresses or any(not ipaddress.ip_address(address).is_global for address in addresses):
            return None, "Yerel veya özel ağ adresleri okunamaz."
    except (OSError, ValueError):
        return None, "Sunucu adresi çözümlenemedi."
    try:
        response = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; YKSKocu/1.0)"},
            timeout=(5, 12),
            allow_redirects=False,
        )
        if 300 <= response.status_code < 400:
            return None, "Güvenlik için yönlendiren bağlantılar takip edilmiyor; hedef adresi doğrudan girin."
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "").lower()
        if "pdf" in content_type or parsed.path.casefold().endswith(".pdf"):
            try:
                from pypdf import PdfReader
                reader = PdfReader(io.BytesIO(response.content))
                pdf_text = "\n".join((page.extract_text() or "") for page in reader.pages)
                pdf_text = pdf_text[:max_chars]
                return ({"title": Path(parsed.path).name or "PDF kaynak", "content": pdf_text}, None) if pdf_text.strip() else (None, "PDF içinde seçilebilir metin bulunamadı.")
            except ImportError:
                return None, "PDF okumak için pypdf yükleyin: pip install pypdf"
            except Exception as exc:
                return None, f"PDF okunamadı: {exc}"
        if "html" not in content_type and "text/plain" not in content_type:
            return None, "Bu bağlantı HTML/metin sayfası değil; okunamadı."
    except requests.RequestException as exc:
        return None, f"Link okunamadı: {exc}"
    if BeautifulSoup is not None:
        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.title.get_text(" ", strip=True) if soup.title else "Başlık bulunamadı"
        for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg"]):
            tag.decompose()
        page_text = soup.get_text("\n")
    else:
        parser = _PageTextExtractor()
        parser.feed(response.text)
        title = " ".join(parser.title_parts).strip() or "Başlık bulunamadı"
        page_text = "\n".join(parser.text_parts)
    lines = [line.strip() for line in page_text.splitlines() if line.strip()]
    content = "\n".join(lines)[:max_chars]
    if not content:
        return None, "Sayfadan okunabilir metin çıkarılamadı."
    return {"title": title, "content": content}, None


class _PageTextExtractor(HTMLParser):
    """BeautifulSoup yoksa standart kütüphane ile temel HTML metni çıkarımı."""
    OMIT_TAGS = {"script", "style", "nav", "footer", "header", "noscript", "svg"}
    BLOCK_TAGS = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "section"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.omit_depth = 0
        self.in_title = False
        self.title_parts = []
        self.text_parts = []

    def handle_starttag(self, tag, attrs):
        if self.omit_depth:
            self.omit_depth += 1
            return
        if tag in self.OMIT_TAGS:
            self.omit_depth = 1
            return
        if tag == "title":
            self.in_title = True
        if tag in self.BLOCK_TAGS:
            self.text_parts.append("\n")

    def handle_endtag(self, tag):
        if self.omit_depth:
            self.omit_depth -= 1
            return
        if tag == "title":
            self.in_title = False
        if tag in self.BLOCK_TAGS:
            self.text_parts.append("\n")

    def handle_data(self, data):
        if self.omit_depth or not data.strip():
            return
        text = data.strip()
        if self.in_title:
            self.title_parts.append(text)
        self.text_parts.append(text)


def summarize_resource(title: str, content: str) -> str:
    return generate_text(
        "Aşağıdaki eğitim kaynağını YKS öğrencisi için Türkçe özetle. Ana kavramları, önemli formülleri/kuralları "
        "ve 3 maddelik tekrar listesini ver. Kaynakta bulunmayan bilgi ekleme.\n"
        f"Başlık: {title}\nİçerik:\n{content[:12000]}"
    )


def generate_structured_plan(plan_text: str) -> dict:
    prompt = (
        "Aşağıdaki çalışma planını JSON'a dönüştür. Yalnızca geçerli JSON döndür. "
        'Şema: {"program":[{"gun":"Pazartesi","dersler":[{"ders":"Matematik",'
        '"sure":"2 saat","konu":"Fonksiyonlar","hedef":"20 soru"}]}]}.\n'
        "Her gün için dersler listesi oluştur. Metin:\n" + plan_text
    )
    raw = generate_text(prompt).strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.IGNORECASE)
    result = json.loads(raw)
    if not isinstance(result, dict) or not isinstance(result.get("program"), list):
        raise ValueError("Yapay zekâ beklenen program biçimini döndürmedi.")
    return result


def render_program_image(program_data: dict):
    if plt is None:
        raise RuntimeError("PNG üretmek için matplotlib gerekli: `pip install matplotlib`. ")
    days = program_data.get("program", [])
    if not days:
        raise ValueError("Program verisi boş.")
    rows = []
    for day in days:
        lessons = []
        for lesson in day.get("dersler", []):
            line = f"{lesson.get('ders', '')} ({lesson.get('sure', '')})"
            if lesson.get("konu"):
                line += f" — {lesson['konu']}"
            if lesson.get("hedef"):
                line += f"\nHedef: {lesson['hedef']}"
            lessons.append(line)
        rows.append([str(day.get("gun", "")), "\n\n".join(lessons) or "-"])
    fig, ax = plt.subplots(figsize=(11, max(4, len(rows) * 1.25)))
    ax.axis("off")
    table = ax.table(cellText=rows, colLabels=["Gün", "Program"], loc="center", cellLoc="left", colWidths=[.2, .8])
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 2.5)
    for (row, _), cell in table.get_celld().items():
        cell.set_text_props(wrap=True, va="center")
        if row == 0:
            cell.set_facecolor("#334e8c")
            cell.set_text_props(color="white", weight="bold", ha="center")
        else:
            cell.set_facecolor("#f3f6fb" if row % 2 else "white")
            cell.set_edgecolor("#dbe3ef")
    ax.set_title("Haftalık Çalışma Programı", fontsize=14, weight="bold", pad=14)
    fig.tight_layout()
    output = io.BytesIO()
    fig.savefig(output, format="png", dpi=180, bbox_inches="tight")
    plt.close(fig)
    output.seek(0)
    return output


def show_program_image(plan_text: str, key: str) -> None:
    try:
        with st.spinner("Program görselleştiriliyor..."):
            image = render_program_image(generate_structured_plan(plan_text))
        st.image(image, caption="Haftalık program", use_container_width=True)
        st.download_button("PNG olarak indir", image.getvalue(), "yks_programi.png", "image/png", key=f"download_{key}")
    except Exception as exc:
        st.error(f"Görsel oluşturulamadı: {exc}")


@st.cache_data(ttl=900, show_spinner=False)
def fetch_city_coordinates(city: str) -> tuple[float, float]:
    """Open-Meteo geocoder resolves any Turkish province by name."""
    response = requests.get("https://geocoding-api.open-meteo.com/v1/search",
                            params={"name": city, "count": 10, "language": "tr", "format": "json", "countryCode": "TR"}, timeout=8)
    response.raise_for_status()
    results = response.json().get("results", [])
    if not results:
        raise ValueError("Şehir bulunamadı")
    exact = next((item for item in results if item.get("name", "").casefold() == city.casefold()), results[0])
    return exact["latitude"], exact["longitude"]


@st.cache_data(ttl=900, show_spinner=False)
def fetch_weather(city: str, latitude: float, longitude: float) -> dict:
    """Open-Meteo hava durumu; API anahtarı istemez."""
    response = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={"latitude": latitude, "longitude": longitude,
                "current": "temperature_2m,relative_humidity_2m,apparent_temperature,wind_speed_10m,weather_code",
                "hourly": "temperature_2m,precipitation_probability",
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,sunrise,sunset",
                "timezone": "auto", "forecast_days": 1}, timeout=8)
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=900, show_spinner=False)
def fetch_headlines(topic: str) -> list[dict]:
    """Google News RSS başlıklarını getirir; içerik kaynağı haber yayıncısıdır."""
    from xml.etree import ElementTree
    response = requests.get("https://news.google.com/rss/search", params={"q": topic, "hl": "tr", "gl": "TR", "ceid": "TR:tr"},
                            headers={"User-Agent": "Mozilla/5.0 YKSStudio/1.0"}, timeout=8)
    response.raise_for_status()
    root = ElementTree.fromstring(response.content)
    return [{"title": item.findtext("title", "Başlık"), "link": item.findtext("link", "#"),
             "source": item.findtext("source", "Haber kaynağı"), "date": item.findtext("pubDate", "")}
            for item in root.findall(".//item")[:8]]


@st.cache_data(ttl=300, show_spinner=False)
def fetch_market(symbol: str) -> dict:
    """Yahoo Finance chart endpointinden gecikmeli piyasa özeti alır."""
    response = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
                            params={"range": "2d", "interval": "1d"},
                            headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
    response.raise_for_status()
    result = response.json()["chart"]["result"][0]
    meta = result["meta"]
    prices = [value for value in result["indicators"]["quote"][0]["close"] if value is not None]
    latest = meta.get("regularMarketPrice", prices[-1] if prices else 0)
    previous = meta.get("chartPreviousClose", prices[-2] if len(prices) > 1 else latest)
    return {"price": latest, "change": latest - previous, "currency": meta.get("currency", ""), "name": meta.get("shortName", symbol)}


def apply_home_scene(scene: str) -> None:
    settings = {"night": {"Salon ışığı": False, "Çalışma lambası": False, "Klima": False, "Güvenlik modu": True},
                "study": {"Salon ışığı": False, "Çalışma lambası": True, "Klima": False, "Güvenlik modu": False}}
    for name, enabled in settings[scene].items():
        st.session_state[f"home_device_{name}"] = enabled


def render_ypt_bridge(user_id: int) -> None:
    st.markdown("# ⏱️ YPT çalışma süresi")
    st.caption("YPT kayıtlarını buradaki ders ve gün grafikleriyle birlikte görüntüle.")
    local_rows = read_user_json(user_id, "study_sessions", [])
    ypt_rows = read_user_json(user_id, "ypt_sessions", [])
    today_key = date.today().isoformat()
    local_today = sum(int(row.get("minutes", 0)) for row in local_rows if row.get("date") == today_key)
    ypt_today = sum(int(row.get("minutes", 0)) for row in ypt_rows if row.get("date") == today_key)
    week_start = (date.today() - timedelta(days=6)).isoformat()
    local_week = sum(int(row.get("minutes", 0)) for row in local_rows if week_start <= row.get("date", "") <= today_key)
    ypt_week = sum(int(row.get("minutes", 0)) for row in ypt_rows if week_start <= row.get("date", "") <= today_key)
    summary = st.columns(4)
    summary[0].metric("Bugün · bu site", f"{local_today // 60} sa {local_today % 60:02d} dk")
    summary[1].metric("Bugün · YPT", f"{ypt_today // 60} sa {ypt_today % 60:02d} dk")
    summary[2].metric("7 gün · bu site", f"{local_week // 60} sa {local_week % 60:02d} dk")
    summary[3].metric("7 gün · YPT", f"{ypt_week // 60} sa {ypt_week % 60:02d} dk")

    with st.container(border=True):
        st.markdown("### 🔗 YPT verisini içeri aktar")
        st.write("YPT için herkese açık resmî bir veri senkronizasyon API'si bulamadım. Bu yüzden hesap parolanı isteyen veya özel uç noktaları kullanan bağlantı kurmuyorum. Uygulama CSV dışa aktarımı sunuyorsa dosyanı burada güvenle içe aktarabilirsin; dosyanın kendisi saklanmaz, yalnızca çalışma satırları hesabına kaydedilir.")
        st.link_button("Resmî YPT sitesini aç", "https://www.yeolpumta.com/")
        st.download_button("Örnek CSV şablonu indir", "date,subject,minutes\n2026-10-04,Matematik,45\n", "ypt_sablon.csv", "text/csv", key="ypt_csv_template")
        uploaded = st.file_uploader("YPT'den dışa aktarılan CSV dosyası", type=["csv"], key="ypt_csv_upload")
        if uploaded:
            try:
                frame = pd.read_csv(io.BytesIO(uploaded.getvalue()))
                if frame.empty or len(frame.columns) < 3:
                    st.warning("Dosyada tarih, ders ve çalışma süresi alanları bulunamadı. Başlık satırlı CSV şablonunu kullanabilirsin.")
                else:
                    headers = list(frame.columns)
                    normalized_headers = {str(col).casefold(): col for col in headers}
                    date_guess = next((i for i, col in enumerate(headers) if any(word in str(col).casefold() for word in ("date", "tarih", "day"))), 0)
                    subject_guess = next((i for i, col in enumerate(headers) if any(word in str(col).casefold() for word in ("subject", "ders", "course"))), min(1, len(headers)-1))
                    duration_guess = next((i for i, col in enumerate(headers) if any(word in str(col).casefold() for word in ("minute", "dakika", "duration", "time", "süre"))), len(headers)-1)
                    m1, m2, m3 = st.columns(3)
                    date_col = m1.selectbox("Tarih sütunu", headers, index=date_guess, key="ypt_date_column")
                    subject_col = m2.selectbox("Ders sütunu", headers, index=subject_guess, key="ypt_subject_column")
                    duration_col = m3.selectbox("Süre sütunu", headers, index=duration_guess, key="ypt_duration_column")
                    duration_unit = st.radio("Süre biçimi", ["Dakika", "Saat", "Saniye", "Saat:Dakika:Saniye"], horizontal=True, key="ypt_duration_unit")
                    st.dataframe(frame.head(8), use_container_width=True, hide_index=True)
                    if st.button("YPT çalışma kayıtlarını ekle", key="import_ypt_csv", use_container_width=True):
                        imported = list(ypt_rows)
                        known = {row.get("id") for row in imported}
                        added = 0
                        for _, row in frame.iterrows():
                            parsed_date = pd.to_datetime(row[date_col], errors="coerce")
                            raw_duration = str(row[duration_col]).strip()
                            try:
                                if duration_unit == "Saat:Dakika:Saniye":
                                    parts = [float(part) for part in raw_duration.split(":")]
                                    seconds = sum(part * (60 ** (len(parts)-index-1)) for index, part in enumerate(parts))
                                    minutes_value = int(round(seconds / 60))
                                else:
                                    numeric = float(raw_duration.replace(",", "."))
                                    multiplier = {"Dakika": 1, "Saat": 60, "Saniye": 1/60}[duration_unit]
                                    minutes_value = int(round(numeric * multiplier))
                            except (ValueError, TypeError):
                                continue
                            if pd.isna(parsed_date) or minutes_value <= 0:
                                continue
                            day_text = parsed_date.date().isoformat()
                            subject_text = str(row[subject_col]).strip() or "YPT çalışma"
                            signature = hashlib.sha256(f"{day_text}|{subject_text}|{minutes_value}".encode("utf-8")).hexdigest()[:20]
                            if signature in known:
                                continue
                            imported.append({"id": signature, "date": day_text, "subject": subject_text,
                                             "minutes": minutes_value, "source": "YPT", "note": "YPT CSV içe aktarımı"})
                            known.add(signature)
                            added += 1
                        write_user_json(user_id, "ypt_sessions", imported)
                        st.success(f"{added} yeni YPT oturumu aktarıldı. Aynı tarih, ders ve süreye sahip satırlar tekrar eklenmedi.")
                        st.rerun()
            except Exception:
                st.warning("CSV okunamadı. Dosyanın UTF-8 kodlamasında ve başlık satırlı olduğundan emin ol.")

    all_ypt = sorted(ypt_rows, key=lambda row: row.get("date", ""), reverse=True)
    if all_ypt:
        st.markdown("### 📚 İçe aktarılan YPT kayıtları")
        st.dataframe([{"Tarih": row.get("date"), "Ders": row.get("subject"), "Dakika": row.get("minutes")} for row in all_ypt[:100]],
                     use_container_width=True, hide_index=True)
        if st.button("İçe aktarılan YPT kayıtlarını sil", key="clear_ypt_imports"):
            write_user_json(user_id, "ypt_sessions", [])
            st.rerun()
    if not ypt_rows:
        st.info("YPT uygulaman CSV dışa aktarımı vermiyorsa ekran görüntüsü ya da örnek dosyayı paylaş; uygun aktarım biçimini birlikte netleştirelim. Şimdilik bu sitedeki seansların YPT toplamından ayrı tutuluyor.")


def render_world_panel() -> None:
    st.markdown("# 🌐 Dünya Paneli")
    st.caption("Tek ekranda bulunduğun şehir, gündem, finans ve akıllı yaşam.")
    provinces = ["Adana", "Adıyaman", "Afyonkarahisar", "Ağrı", "Amasya", "Ankara", "Antalya", "Artvin", "Aydın", "Balıkesir", "Bilecik", "Bingöl", "Bitlis", "Bolu", "Burdur", "Bursa", "Çanakkale", "Çankırı", "Çorum", "Denizli", "Diyarbakır", "Edirne", "Elazığ", "Erzincan", "Erzurum", "Eskişehir", "Gaziantep", "Giresun", "Gümüşhane", "Hakkâri", "Hatay", "Isparta", "Mersin", "İstanbul", "İzmir", "Kars", "Kastamonu", "Kayseri", "Kırklareli", "Kırşehir", "Kocaeli", "Konya", "Kütahya", "Malatya", "Manisa", "Kahramanmaraş", "Mardin", "Muğla", "Muş", "Nevşehir", "Niğde", "Ordu", "Rize", "Sakarya", "Samsun", "Siirt", "Sinop", "Sivas", "Tekirdağ", "Tokat", "Trabzon", "Tunceli", "Şanlıurfa", "Uşak", "Van", "Yozgat", "Zonguldak", "Aksaray", "Bayburt", "Karaman", "Kırıkkale", "Batman", "Şırnak", "Bartın", "Ardahan", "Iğdır", "Yalova", "Karabük", "Kilis", "Osmaniye", "Düzce"]
    top_left, top_right = st.columns([1.5, 1])
    with top_left:
        st.markdown("### ☁️ Hava durumu")
        city = st.selectbox("İl seç · Türkiye'nin 81 ili", provinces, key="world_weather_city")
    with top_right:
        st.markdown("### 🛰️ Sistem")
        st.metric("Kontrol paneli", "Çevrimiçi", help="Bağlantı gerektiren kartlar ihtiyaç halinde canlı veriyi getirir.")
    try:
        weather = fetch_weather(city, *fetch_city_coordinates(city))
        current, daily = weather["current"], weather["daily"]
        wx, forecast = st.columns([1, 1.6])
        with wx:
            st.markdown(f"<div style='min-height:225px;padding:1.5rem;border-radius:24px;background:radial-gradient(circle at 82% 18%,#ffc078aa,transparent 28%),linear-gradient(135deg,#b83529,#e16944 55%,#322f4a);color:white;box-shadow:0 18px 45px #7f302533'><div style='font-size:.9rem;letter-spacing:.12em;text-transform:uppercase;opacity:.85'>BUGÜN · {html.escape(city.upper())}</div><div style='font-size:4.4rem;font-weight:800;line-height:1.2'>{current['temperature_2m']}°</div><div style='font-size:1rem'>Hissedilen {current['apparent_temperature']}°C</div><div style='margin-top:1.2rem;opacity:.86'>☁ Nem %{current['relative_humidity_2m']} &nbsp; · &nbsp; 💨 {current['wind_speed_10m']} km/sa</div></div>", unsafe_allow_html=True)
        with forecast:
            st.markdown(f"#### {city} · günlük görünüm")
            st.metric("Yağış olasılığı", f"%{daily['precipitation_probability_max'][0]}", f"Günün en düşüğü {daily['temperature_2m_min'][0]}° · en yükseği {daily['temperature_2m_max'][0]}°")
            hours = weather.get("hourly", {})
            if hours.get("time"):
                current_hour = datetime.now().hour
                hour_rows = [{"Saat": datetime.fromisoformat(t).strftime("%H:%M"), "Sıcaklık °C": temp}
                             for t, temp in zip(hours["time"], hours["temperature_2m"]) if datetime.fromisoformat(t).hour >= current_hour]
                if hour_rows:
                    st.line_chart(pd.DataFrame(hour_rows).set_index("Saat"), height=185, color="#d64d36")
            st.caption(f"🌅 {daily['sunrise'][0][-5:]} gün doğumu  ·  🌇 {daily['sunset'][0][-5:]} gün batımı")
    except Exception:
        st.info("Hava durumu şu an alınamadı. İnternet bağlantısını kontrol edip biraz sonra tekrar deneyin.")

    st.markdown("### 📊 Piyasalar")
    market_items = [("S&P 500", "^GSPC"), ("NASDAQ", "^IXIC"), ("BIST 100", "XU100.IS"), ("Bitcoin", "BTC-USD"), ("Altın", "GC=F"), ("USD/TRY", "USDTRY=X")]
    market_cols = st.columns(3)
    for index, (label, symbol) in enumerate(market_items):
        with market_cols[index % 3]:
            try:
                item = fetch_market(symbol)
                change_pct = item["change"] / (item["price"] - item["change"]) * 100 if item["price"] != item["change"] else 0
                st.metric(label, f"{item['price']:,.2f} {item['currency']}", f"{item['change']:+,.2f} · %{change_pct:+.2f}")
            except Exception:
                st.metric(label, "Veri bekleniyor", help="Piyasa sağlayıcısına şu an erişilemiyor.")
    st.caption("Piyasa verileri gecikmeli olabilir; yatırım kararı için tek başına kullanma.")

    st.markdown("### 🗞️ Gündem")
    topic = st.selectbox("Haber akışı", ["Türkiye", "Teknoloji ve yapay zekâ", "Bilim", "Ekonomi", "Dünya"], key="world_news_topic")
    try:
        headlines = fetch_headlines(topic)
        if headlines:
            for row in headlines:
                title = html.escape(row["title"])
                source = html.escape(row["source"])
                href = html.escape(row["link"], quote=True)
                st.markdown(f"<div class='soft-card' style='margin:.45rem 0;padding:.9rem 1rem'><a href='{href}' target='_blank' style='color:inherit;text-decoration:none;font-weight:650'>{title}</a><div style='font-size:.8rem;opacity:.72;margin-top:.4rem'>{source} · {html.escape(row['date'])}</div></div>", unsafe_allow_html=True)
        else:
            st.info("Bu başlık için şu an haber bulunamadı.")
    except Exception:
        st.info("Haber akışı şu an alınamadı. Bağlantı geri geldiğinde yeniden deneyebilirsin.")

    st.markdown("### 🏠 Akıllı ev · arayüz demosu")
    st.caption("Cihazlar şimdilik yerel demo anahtarlarıdır; gerçek ev cihazı kontrolü için üretici hesabı veya Home Assistant bağlantısı gerekir.")
    device_cols = st.columns(4)
    devices = [("Salon ışığı", "💡", True), ("Çalışma lambası", "📚", True), ("Klima", "❄️", False), ("Güvenlik modu", "🛡️", False)]
    for column, (name, icon, default) in zip(device_cols, devices):
        with column:
            enabled = st.toggle(name, value=default, key=f"home_device_{name}")
            st.markdown(f"<div class='soft-card'><div style='font-size:1.7rem'>{icon}</div><b>{'Açık' if enabled else 'Kapalı'}</b><p>{name} · demo</p></div>", unsafe_allow_html=True)
    s1, s2, s3 = st.columns(3)
    with s1:
        st.button("🌙 İyi geceler", use_container_width=True, key="home_scene_night", on_click=apply_home_scene, args=("night",))
    with s2:
        st.button("📖 Ders modu", use_container_width=True, key="home_scene_study", on_click=apply_home_scene, args=("study",))
    with s3:
        st.link_button("🔎 Daha fazla teknoloji haberi", "https://news.google.com/topstories?hl=tr&gl=TR&ceid=TR:tr", use_container_width=True)


def navigate_to_view(view: str) -> None:
    """Switch the sidebar page from a dashboard shortcut before rerun."""
    st.session_state["active_view"] = view


@st.fragment(run_every="1s")
def render_shared_room(user_id: int, code: str) -> None:
    room, members = get_study_room(user_id, code)
    if not room:
        st.warning("Bu oda bulunamadı veya artık erişimin yok.")
        return
    st.markdown(f"### Ortak odak odası · `{html.escape(code)}`")
    st.caption("Katılımcılar: " + " · ".join(html.escape(name) for name in members))
    owner = int(room["owner_id"]) == user_id
    started_at = room.get("started_at")
    duration = int(room["duration_minutes"])
    if not started_at:
        st.info(f"Oda hazır · {duration} dakikalık odak. Oda sahibi sayacı başlatınca katılımcıların ekranında da aynı anda çalışır.")
        if owner and st.button("▶ Ortak sayacı başlat", key=f"start_shared_{code}"):
            start_study_room(user_id, code)
            st.rerun(scope="fragment")
        return
    remaining = max(0, duration * 60 - int(time.time() - float(started_at)))
    mins, secs = divmod(remaining, 60)
    st.markdown(f"<div class='focus-timer-card'><div class='focus-live'>● ORTAK ODAK · {len(members)} KİŞİ</div><div class='focus-clock'>{mins:02d}:{secs:02d}</div><div class='focus-subject'>{duration} dakikalık seans</div></div>", unsafe_allow_html=True)
    st.progress(1 - remaining / max(1, duration * 60), text="Ortak seans ilerlemesi")
    if remaining == 0:
        logs = read_user_json(user_id, "study_sessions", [])
        room_session_id = f"room:{code}:{user_id}"
        if not any(item.get("id") == room_session_id for item in logs if isinstance(item, dict)):
            logs.append({"id": room_session_id, "date": date.today().isoformat(), "minutes": duration,
                         "subject": "Ortak odak", "note": f"Ortak oda {code}"})
            write_user_json(user_id, "study_sessions", logs)
            award_xp(user_id, f"session:{room_session_id}", max(5, duration // 5), "Ortak odak seansı")
        st.success("Ortak seans tamamlandı ve çalışma geçmişine eklendi.")


def render_anka_social(user_id: int, username: str) -> None:
    st.markdown("# 🔥 AnkaXP · Arkadaş modu")
    profile = xp_profile(user_id)
    st.markdown(f"<div class='soft-card' style='border-left:4px solid #df5d66'><span class='section-kicker'>ANKA SEVİYESİ</span><h2>{profile['title']} · {profile['xp']} XP</h2><p>Çalışma oturumları, tamamlanan planlı görevler ve tekrar edilen yanlış sorular XP kazandırır.</p></div>", unsafe_allow_html=True)
    st.progress(profile["progress"], text=f"Sonraki seviye: {profile['next']} XP" if profile["next"] > profile["xp"] else "En yüksek seviye")
    st.markdown("### Rozet hedefleri")
    sessions = read_user_json(user_id, "study_sessions", [])
    wrongs = read_user_json(user_id, "wrong_questions", [])
    tasks = read_user_json(user_id, "study_tasks", [])
    badges = [("🔥 İlk odak", bool(sessions)), ("📚 10 oturum", len(sessions) >= 10),
              ("🧩 5 tekrar", sum(int(item.get("review_count", 0)) for item in wrongs) >= 5),
              ("✅ 10 görev", sum(bool(item.get("done")) for item in tasks) >= 10)]
    badge_cols = st.columns(4)
    for col, (badge, earned) in zip(badge_cols, badges):
        col.markdown(f"<div class='soft-card' style='text-align:center;opacity:{1 if earned else .48}'>{badge}<br><b>{'Açıldı' if earned else 'Kilitli'}</b></div>", unsafe_allow_html=True)

    st.divider()
    st.markdown("### Arkadaş çalışma tablosu")
    st.caption("Paylaşım kapalı başlar. Açınca yalnızca son 7 günlük toplam çalışma dakikan, eklediğin arkadaşların tablosunda görünür.")
    consent = bool(read_user_json(user_id, "leaderboard_opt_in", False))
    share = st.checkbox("Haftalık çalışma süremi arkadaşlarımla paylaş", value=consent, key="leaderboard_opt_in_widget")
    if share != consent:
        write_user_json(user_id, "leaderboard_opt_in", bool(share))
        st.rerun()
    friends = read_user_json(user_id, "friend_usernames", [])
    friends = friends if isinstance(friends, list) else []
    with st.form("friend_add_form", clear_on_submit=True):
        friend_name = st.text_input("Arkadaşının kullanıcı adı", max_chars=32)
        add_friend = st.form_submit_button("＋ Arkadaş ekle")
    if add_friend:
        with db_connect() as db:
            friend = db.execute("SELECT id,username FROM users WHERE username=? COLLATE NOCASE", (friend_name.strip(),)).fetchone()
        if not friend:
            st.error("Bu kullanıcı adıyla kayıtlı hesap bulunamadı.")
        elif int(friend["id"]) == user_id:
            st.info("Kendi hesabını arkadaş listene ekleyemezsin.")
        elif any(name.casefold() == friend["username"].casefold() for name in friends):
            st.info("Bu arkadaş zaten listende.")
        else:
            friends.append(friend["username"])
            write_user_json(user_id, "friend_usernames", friends)
            st.rerun()
    if friends:
        st.markdown("**Arkadaş listen**")
        for friend_name in friends:
            left, right = st.columns([4, 1])
            left.write(friend_name)
            if right.button("Kaldır", key=f"remove_friend_{friend_name}"):
                write_user_json(user_id, "friend_usernames", [name for name in friends if name != friend_name])
                st.rerun()
    if share:
        visible_names = friends + [username]
        ranking = leaderboard_rows(user_id, visible_names)
        if ranking:
            st.dataframe(pd.DataFrame(ranking).assign(Sıra=lambda frame: range(1, len(frame) + 1)).set_index("Sıra"), use_container_width=True)
            st.caption("YPT ile bu siteye aynı oturumu iki kez kaydettiysen toplam süre çift sayılabilir.")
        else:
            st.info("Henüz sen veya eklediğin arkadaşların paylaşımı açmadı.")
    else:
        st.info("Haftalık sıralamaya katılmak için paylaşım iznini aç.")

    st.divider()
    st.markdown("### Ortak Pomodoro odası")
    room_left, room_right = st.columns(2)
    with room_left:
        room_duration = st.selectbox("Seans süresi", [25, 45, 60], format_func=lambda value: f"{value} dakika", key="shared_room_duration")
        if st.button("Oda oluştur", key="create_shared_room", use_container_width=True):
            code = create_study_room(user_id, int(room_duration))
            write_user_json(user_id, "active_study_room", code)
            st.rerun()
    with room_right:
        with st.form("join_shared_room_form"):
            room_code_input = st.text_input("Arkadaşının oda kodu", max_chars=6).upper()
            join_room = st.form_submit_button("Odaya katıl", use_container_width=True)
        if join_room:
            if join_study_room(user_id, room_code_input):
                write_user_json(user_id, "active_study_room", room_code_input)
                st.rerun()
            else:
                st.error("Oda kodu bulunamadı veya odanın süresi dolmuş.")
    active_room = read_user_json(user_id, "active_study_room", "")
    if active_room:
        render_shared_room(user_id, active_room)
        if st.button("Odadan ayrıl", key="leave_shared_room"):
            with db_connect() as db:
                db.execute("DELETE FROM study_room_members WHERE room_code=? AND user_id=?", (active_room, user_id))
            write_user_json(user_id, "active_study_room", "")
            st.rerun()


def render_offline_kit(user_id: int) -> None:
    st.markdown("# 📦 Çevrimdışı çalışma")
    st.caption("İnternet olmadan açılan tek HTML dosyası: görevleri gör, Pomodoro çalıştır, not al ve yanlış sorularını oku.")
    st.download_button("⬇️ Çevrimdışı çalışma dosyasını indir", offline_kit_html(user_id),
                       file_name="anka-cevrimdisi-calisma.html", mime="text/html", use_container_width=True)
    st.info("Bu yardımcı PWA değildir; indirilen dosya cihazında yerel çalışır. Çevrimdışı eklediğin not ve çalışma kayıtlarını JSON olarak dışa aktarıp buradaki yedek alanından içe aktararak eşitleyebilirsin. Otomatik arka plan eşitlemesi bu Streamlit sürümünde yoktur.")


def render_dashboard(user_id: int, username: str) -> None:
    tasks = read_user_json(user_id, "study_tasks", [])
    focus_logs = read_user_json(user_id, "study_sessions", [])
    exam_results = read_user_json(user_id, "exam_results", [])
    ypt_logs = read_user_json(user_id, "ypt_sessions", [])
    daily_checkins = read_user_json(user_id, "daily_checkins", {})
    planned_exams = read_user_json(user_id, "exam_plan", [])
    records = load_memory(user_id)
    today = date.today()
    today_checkin = daily_checkins.get(today.isoformat(), {}) if isinstance(daily_checkins, dict) else {}
    today_name = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"][today.weekday()]
    safe_name = html.escape(username, quote=True)
    today_minutes = sum(int(item.get("minutes", 0)) for item in focus_logs if item.get("date") == today.isoformat())
    today_focus_label = f"{today_minutes // 60} sa {today_minutes % 60:02d} dk" if today_minutes >= 60 else f"{today_minutes} dk"
    ypt_today_minutes = sum(int(item.get("minutes", 0)) for item in ypt_logs if item.get("date") == today.isoformat())
    ypt_today_label = f"{ypt_today_minutes // 60} sa {ypt_today_minutes % 60:02d} dk" if ypt_today_minutes >= 60 else f"{ypt_today_minutes} dk"
    task_count = len(tasks)
    done_count = sum(bool(item.get("done")) for item in tasks)
    completion = round(100 * done_count / task_count) if task_count else 0
    latest_exam = max(exam_results, key=lambda item: item.get("date", ""), default=None)
    latest_net = f"{latest_exam.get('Toplam', 0):g}" if latest_exam else "—"
    future_exams = []
    for planned_exam in planned_exams:
        try:
            target_day = date.fromisoformat(planned_exam.get("date", ""))
            if target_day >= today:
                future_exams.append((target_day, planned_exam))
        except ValueError:
            continue
    nearest_exam = min(future_exams, key=lambda item: item[0]) if future_exams else None
    exam_countdown = f"{nearest_exam[1].get('name', 'Sınav')} · {max(0, (nearest_exam[0] - today).days)} gün kaldı" if nearest_exam else "Tarih ekle"
    resource_count = sum(item.get("type") in {"kaynak_linki", "kaynak_pdf"} for item in records)
    weekly_goal = max(60, int(read_user_json(user_id, "weekly_goal", 900)))
    week_minutes = sum(int(item.get("minutes", 0)) for item in focus_logs
                       if (today - timedelta(days=6)).isoformat() <= item.get("date", "") <= today.isoformat())
    study_dates = {item.get("date") for item in focus_logs if item.get("date")}
    streak_cursor = today if today.isoformat() in study_dates else today - timedelta(days=1)
    study_streak = 0
    while streak_cursor.isoformat() in study_dates:
        study_streak += 1
        streak_cursor -= timedelta(days=1)
    streak_badge = "İlk adım" if study_streak < 3 else "Bronz ritim" if study_streak < 7 else "Gümüş istikrar" if study_streak < 30 else "Altın disiplin"
    profile = xp_profile(user_id)
    review_items = read_user_json(user_id, "wrong_questions", [])
    review_due = sum(not item.get("mastered") and item.get("next_review", "") <= today.isoformat() for item in review_items)
    unfinished_today = [item for item in tasks if item.get("date") == today.isoformat() and not item.get("done")]
    if review_due:
        insight = f"Tekrar zamanı gelen {review_due} yanlış sorunu çözerek bilgini pekiştir."
    elif today_checkin and (int(today_checkin.get("energy", 3)) <= 2 or today_checkin.get("mood") in {"Yorgun", "Gergin"}):
        insight = "Bugün enerjini koru: kısa bir odak bloğu seç, ardından mola ver. İstikrar, yoğunluktan daha değerlidir."
    elif unfinished_today:
        task = unfinished_today[0]
        insight = f"Bugünkü önceliğin: {task.get('subject', 'Ders')} · {task.get('topic') or task.get('target') or 'planlı görev'}"
    elif latest_exam and len(exam_results) >= 2:
        prior_exam = sorted(exam_results, key=lambda item: item.get("date", ""))[-2]
        delta = float(latest_exam.get("Toplam", 0)) - float(prior_exam.get("Toplam", 0))
        insight = f"Son iki denemede toplam netin {'+' if delta >= 0 else ''}{delta:.2f} değişti. Bir sonraki adım için en düşük ders netine odaklan."
    else:
        insight = "İlk çalışma oturumunu kaydet; JARVIS haftalık ritmini ve sıradaki önceliğini oluşturmaya başlasın."

    st.markdown(f"""
    <section class="hero-card">
      <div class="hero-copy">
      <div class="hero-eyebrow">ANKA · KİŞİSEL YKS STÜDYOSU</div>
        <h1>Selam {safe_name}.<br>Bugün hedeflerine bir adım daha.</h1>
        <p>Planını sade tut, ilerlemeni gör ve sıradaki doğru işe odaklan. Küçük ama düzenli adımlar büyük fark yaratır.</p>
        <span class="hero-pill">✦ &nbsp; {today_name}, {today:%d.%m.%Y} &nbsp;·&nbsp; Bugünün çalışma alanı</span>
        <span class="hero-pill" style="margin-left:.45rem">🎓 &nbsp; {html.escape(exam_countdown)}</span>
      </div>
      <svg class="hero-art phoenix-hero" viewBox="0 0 300 220" role="img" aria-label="Kızıl ve mor alevlerden doğan Anka kuşu çizimi">
        <defs><linearGradient id="phoenixWing" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#ffc274"/><stop offset=".48" stop-color="#ff665f"/><stop offset="1" stop-color="#c878ff"/></linearGradient><radialGradient id="phoenixAura"><stop stop-color="#ff9970" stop-opacity=".45"/><stop offset="1" stop-color="#a443d3" stop-opacity="0"/></radialGradient></defs>
        <circle cx="154" cy="113" r="101" fill="url(#phoenixAura)"/><circle cx="154" cy="113" r="76" fill="#ffffff08" stroke="#ffffff25"/>
        <path d="M148 158c-21-16-37-36-43-66 20 17 37 23 53 24-10-27-6-52 11-78 4 30 16 49 36 62-1-27 10-50 34-68-7 40-1 68 20 92-24-7-43-17-56-31 7 26 2 49-14 70-7-23-18-39-34-48 0 18-2 32-7 43Z" fill="url(#phoenixWing)" opacity=".94"/>
        <path d="M146 91c-14-17-28-29-47-38 8 19 14 34 18 50-17-10-35-14-57-13 18 13 31 28 38 45-17-5-33-6-50-2 20 8 36 18 49 32-12 1-24 5-36 12 22 0 42 4 58 14M162 91c14-17 28-29 47-38-8 19-14 34-18 50 17-10 35-14 57-13-18 13-31 28-38 45 17-5 33-6 50-2-20 8-36 18-49 32 12 1 24 5 36 12-22 0-42 4-58 14" fill="none" stroke="url(#phoenixWing)" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M149 163c-10 11-18 22-24 35m38-35c10 11 18 22 24 35M154 68c-5-13-4-25 3-38 9 14 10 27 3 39" fill="none" stroke="#ffdc9c" stroke-width="5" stroke-linecap="round"/>
        <circle cx="153" cy="107" r="4" fill="#fff4d6"/><path d="m158 106 12 3-11 5" fill="#ffe0a4"/>
      </svg>
    </section>
    """, unsafe_allow_html=True)

    if read_user_json(user_id, "bulletin_seen_date", "") != today.isoformat():
        bulletin_city = st.session_state.get("world_weather_city", "Isparta")
        checkin_line = f"Bugünkü durumun: {html.escape(str(today_checkin.get('mood', 'Dengeli')))} · enerji {int(today_checkin.get('energy', 3))}/5." if today_checkin else "Günlük mod ve enerji yoklamasını tamamla, planını bugünkü ritmine uyduralım."
        st.markdown(f"<div class='soft-card' style='margin:.4rem 0 1rem;border-left:4px solid #e56754;background:linear-gradient(110deg,#21182a,#302035)!important;color:#fff'><span class='section-kicker' style='color:#ffbf80!important'>☀️ GÜNLÜK YKS BÜLTENİ</span><h3 style='color:#fff!important;margin:.45rem 0'>Günaydın {safe_name}.</h3><p style='color:#e3d7e7!important'>{html.escape(exam_countdown)} · Bugün planında <b style='color:#fff'>{len(unfinished_today)} görev</b> var. Bugün siteye {today_minutes} dakika çalışma kaydettin. {html.escape(bulletin_city)} için hava durumu aşağıdan yenilenebilir.</p><p style='color:#e3d7e7!important'>{checkin_line} Anka seviyesi: <b style='color:#ffc880'>{profile['title']}</b> · {profile['xp']} XP</p></div>", unsafe_allow_html=True)
        weather_col, close_col = st.columns([3, 1])
        with weather_col:
            with st.expander(f"🌦️ {bulletin_city} hava durumunu ekle"):
                try:
                    weather_data = fetch_weather(bulletin_city, *fetch_city_coordinates(bulletin_city))
                    weather_now = weather_data["current"]
                    st.metric(f"{bulletin_city} · şu an", f"{weather_now['temperature_2m']}°C",
                              f"Hissedilen {weather_now['apparent_temperature']}°C · nem %{weather_now['relative_humidity_2m']}")
                except Exception:
                    st.caption("Hava bilgisi şu an alınamıyor; şehir seçimini Dünya Paneli'nden değiştirebilirsin.")
        with close_col:
            if st.button("Bülteni kapat", key="dismiss_morning_bulletin", use_container_width=True):
                write_user_json(user_id, "bulletin_seen_date", today.isoformat())
                st.rerun()

    st.markdown('<div class="section-kicker">Bugün ve bu hafta</div>', unsafe_allow_html=True)
    st.markdown(f"<div class='soft-card' style='margin-bottom:1rem;border-left:4px solid #e16a48'><span class='section-kicker'>JARVIS İÇGÖRÜSÜ</span><p style='margin-top:.4rem'>{html.escape(insight)}</p></div>", unsafe_allow_html=True)
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Bugünkü odak", today_focus_label, help="Kaydettiğin çalışma oturumlarının toplamı")
    k2.metric("Plan ilerlemesi", f"%{completion}", help=f"{done_count}/{task_count} görev tamamlandı")
    k3.metric("Son deneme neti", latest_net, help=latest_exam.get("name", "Deneme") if latest_exam else "Henüz deneme sonucu eklenmedi")
    k4.metric("Kaynak arşivin", str(resource_count), help="PDF ve bağlantı kaynakları")
    extra_a, extra_b, extra_c, extra_d = st.columns(4)
    extra_a.metric("🎓 Sıradaki sınav", exam_countdown, help="Sınav tarihini Sınav Planlayıcı bölümünden ayarla")
    extra_b.metric("⏱️ YPT · bugün", ypt_today_label, help="İçe aktarılan YPT kayıtları; site oturumlarından ayrı gösterilir")
    extra_c.metric("📚 YPT · 7 gün", f"{sum(int(item.get('minutes', 0)) for item in ypt_logs if (today - timedelta(days=6)).isoformat() <= item.get('date', '') <= today.isoformat()) // 60} sa", help="Son yedi günde içe aktarılan YPT süresi")
    extra_d.metric("🔥 AnkaXP", f"{profile['xp']} XP", help=f"Seviye: {profile['title']}")
    streak_col, badge_col = st.columns([1, 3])
    streak_col.metric("🔥 Çalışma serisi", f"{study_streak} gün")
    badge_col.markdown(f"<div class='soft-card' style='padding:.85rem 1rem'><span class='section-kicker'>GELİŞİM ROZETİ</span><p style='margin-top:.3rem'>🏅 {streak_badge} · Her gün kısa bir oturum bile serini sürdürür.</p></div>", unsafe_allow_html=True)

    st.markdown("<div class='section-kicker' style='margin-top:1.2rem'>HIZLI ERİŞİM</div><h3 class='quick-access-title'>Bugün ne yapmak istersin?</h3>", unsafe_allow_html=True)
    shortcuts = st.columns(4)
    shortcut_items = [("🎯", "Odak seansı", "🎯 Odak Modu"), ("▶", "TYT kampı", "🎬 TYT Video Kampları"),
                      ("🎓", "Sınav hedefi", "🎓 Sınav Planlayıcı"), ("🌌", "Dünya paneli", "🌐 Dünya Paneli")]
    for shortcut_col, (icon, label, destination) in zip(shortcuts, shortcut_items):
        with shortcut_col:
            st.button(f"{icon}  {label}  →", key=f"shortcut_{destination}", use_container_width=True,
                      on_click=navigate_to_view, args=(destination,))

    left, right = st.columns([1.45, 1], gap="large")
    with left:
        st.markdown('<div class="section-kicker">Ritmini oluştur</div>', unsafe_allow_html=True)
        st.subheader("Bu haftaki çalışma süren")
        st.progress(min(1.0, week_minutes / weekly_goal), text=f"Haftalık hedef · {week_minutes // 60} sa {week_minutes % 60:02d} dk / {weekly_goal // 60} sa")
        with st.expander("Haftalık hedefi düzenle"):
            new_weekly_goal = st.number_input("Hedef (dakika)", min_value=60, max_value=4200, step=60,
                                              value=weekly_goal, key="weekly_goal_input")
            if st.button("Hedefi kaydet", key="save_weekly_goal"):
                write_user_json(user_id, "weekly_goal", int(new_weekly_goal))
                st.rerun()
        dates = [(today - timedelta(days=i)).isoformat() for i in reversed(range(7))]
        focus_by_date = {d: sum(int(item.get("minutes", 0)) for item in focus_logs if item.get("date") == d) for d in dates}
        labels = {d: f"{['Pzt','Sal','Çar','Per','Cum','Cmt','Paz'][date.fromisoformat(d).weekday()]} {date.fromisoformat(d).day}" for d in dates}
        if sum(focus_by_date.values()) == 0:
            placeholder_bars = "".join(f"<i style='height:{height}px'></i>" for height in [34, 54, 42, 72, 48, 62, 38])
            st.markdown(
                "<div class='week-empty'><div class='week-empty-copy'><strong>Haftanın ilk adımını atalım</strong>"
                "<span>Henüz çalışma oturumu yok. İlk oturumunu kaydettiğinde haftalık süre grafiğin burada görünecek.</span>"
                f"</div><div class='week-bars' aria-hidden='true'>{placeholder_bars}</div></div>",
                unsafe_allow_html=True,
            )
        else:
            import pandas as pd
            focus_frame = pd.DataFrame([{"Gün": labels[d], "Dakika": focus_by_date[d]} for d in dates])
            st.bar_chart(focus_frame, x="Gün", y="Dakika", color="#d45a42", height=230)
        with st.expander("📆 Son 4 haftanın çalışma haritası", expanded=True):
            heat_days = [today - timedelta(days=i) for i in reversed(range(28))]
            heat_counts = {day.isoformat(): sum(int(item.get("minutes", 0)) for item in focus_logs
                                                 if item.get("date") == day.isoformat()) for day in heat_days}
            max_heat = max(heat_counts.values(), default=0)
            heat_cells = []
            for day in heat_days:
                mins = heat_counts[day.isoformat()]
                intensity = 0 if mins == 0 else min(4, max(1, int(mins / max(1, max_heat) * 4 + .5)))
                heat_cells.append(f"<span title='{day:%d.%m.%Y}: {mins} dk' class='heat-cell heat-{intensity}'></span>")
            st.markdown("<div class='study-heatmap'>" + "".join(heat_cells) + "</div><div class='heat-legend'><span>Az</span><i class='heat-cell heat-0'></i><i class='heat-cell heat-1'></i><i class='heat-cell heat-2'></i><i class='heat-cell heat-3'></i><i class='heat-cell heat-4'></i><span>Çok</span></div>", unsafe_allow_html=True)
            st.caption("Renk yoğunluğu, o gün bu sitede kaydedilen çalışma dakikasını gösterir.")
        subject_minutes = {}
        for item in focus_logs:
            if (today - timedelta(days=6)).isoformat() <= item.get("date", "") <= today.isoformat():
                subject_minutes[item.get("subject", "Diğer")] = subject_minutes.get(item.get("subject", "Diğer"), 0) + int(item.get("minutes", 0))
        if subject_minutes:
            st.markdown("**Son 7 gün · derse göre süre**")
            subject_frame = pd.DataFrame([{"Ders": subject, "Dakika": minutes} for subject, minutes in sorted(subject_minutes.items(), key=lambda pair: pair[1], reverse=True)])
            st.bar_chart(subject_frame, x="Ders", y="Dakika", color="#b83e32", height=240)
        with st.form("focus_session_form", clear_on_submit=True):
            st.markdown("**Çalışma oturumu ekle**")
            f1, f2, f3 = st.columns([1.2, 1, 1])
            subject = f1.selectbox("Ders", ["Matematik", "Türkçe", "Fizik", "Kimya", "Biyoloji", "Tarih", "Coğrafya", "Diğer"], key="focus_subject")
            minutes = f2.number_input("Dakika", min_value=5, max_value=600, value=45, step=5, key="focus_minutes")
            focus_day = f3.date_input("Tarih", value=today, key="focus_date")
            note = st.text_input("Kısa not (isteğe bağlı)", placeholder="Paragraf denemesi, fonksiyon tekrarı…", key="focus_note")
            submitted = st.form_submit_button("+ Oturumu kaydet", use_container_width=True)
        if submitted:
            focus_logs.append({"id": uuid.uuid4().hex[:10], "date": focus_day.isoformat(), "minutes": int(minutes),
                               "subject": subject, "note": note.strip()})
            write_user_json(user_id, "study_sessions", focus_logs)
            award_xp(user_id, f"session:{focus_logs[-1]['id']}", max(5, int(minutes) // 5), "Çalışma oturumu")
            st.success("Çalışma oturumu kaydedildi.")
            st.rerun()

    with right:
        st.markdown('<div class="section-kicker">Sıradaki adım</div>', unsafe_allow_html=True)
        st.subheader("Bugünün görevleri")
        today_tasks = [item for item in tasks if item.get("date") == today.isoformat()]
        if today_tasks:
            for task_index, item in enumerate(today_tasks[:5]):
                label = " · ".join(part for part in [item.get("subject", "Ders"), item.get("topic", ""), item.get("target", "")] if part)
                state = "✓" if item.get("done") else "○"
                st.markdown(f"<div class='soft-card' style='margin-bottom:9px;padding:12px 15px'><b style='color:{'#1f9b75' if item.get('done') else '#c94355'}'>{state}</b> &nbsp; {html.escape(label)}</div>", unsafe_allow_html=True)
                if not item.get("done"):
                    task_actions = st.columns(2)
                    if task_actions[0].button("✓ Tamamlandı", key=f"dash_done_{item.get('id', task_index)}", use_container_width=True):
                        item["done"] = True
                        write_user_json(user_id, "study_tasks", tasks)
                        award_xp(user_id, f"task:{item.get('id', task_index)}", 10, "Planlı görev")
                        st.rerun()
                    if task_actions[1].button("Yarına taşı", key=f"dash_defer_{item.get('id', task_index)}", use_container_width=True):
                        item["date"] = (today + timedelta(days=1)).isoformat()
                        write_user_json(user_id, "study_tasks", tasks)
                        st.rerun()
        else:
            st.markdown("<div class='empty-state'>Bugün için planlanmış görev yok. Programını ekleyip görev listesine dönüştürebilirsin.</div>", unsafe_allow_html=True)
        with st.expander("☀️ Günlük enerji ve mod", expanded=not bool(today_checkin)):
            mood_options = ["Motive", "Dengeli", "Yorgun", "Gergin"]
            old_mood = today_checkin.get("mood", "Dengeli")
            mood_index = mood_options.index(old_mood) if old_mood in mood_options else 1
            with st.form("daily_checkin_form"):
                mood = st.radio("Bugün kendini nasıl hissediyorsun?", mood_options, index=mood_index, horizontal=True)
                energy = st.slider("Enerji düzeyi", min_value=1, max_value=5,
                                   value=max(1, min(5, int(today_checkin.get("energy", 3)))),
                                   help="1: çok düşük · 5: çok yüksek")
                checkin_submitted = st.form_submit_button("Günlük durumumu kaydet", use_container_width=True)
            if checkin_submitted:
                latest_checkins = read_user_json(user_id, "daily_checkins", {})
                if not isinstance(latest_checkins, dict):
                    latest_checkins = {}
                latest_checkins[today.isoformat()] = {"mood": mood, "energy": int(energy)}
                write_user_json(user_id, "daily_checkins", latest_checkins)
                st.rerun()
            if today_checkin:
                st.caption(f"Bugün kaydedilen durum: {today_checkin.get('mood', 'Dengeli')} · enerji {today_checkin.get('energy', 3)}/5")
        st.markdown('<div class="section-kicker" style="margin-top:1.4rem">Son hareketler</div>', unsafe_allow_html=True)
        if records:
            for item in reversed(records[-4:]):
                icon = {"soru_analizi": "🧩", "calisma_programi": "🗓️", "kaynak_linki": "🔗", "kaynak_pdf": "📄"}.get(item.get("type"), "✦")
                st.markdown(f"<div style='padding:9px 2px;border-bottom:1px solid #e4e9f1'><span>{icon}</span> &nbsp;<b>{html.escape(item.get('title','Kayıt'))}</b><br><small style='color:#8290a4'>{html.escape(item.get('created_at',''))}</small></div>", unsafe_allow_html=True)
        else:
            st.caption("Kayıtların burada listelenecek.")


@st.fragment(run_every="1s")
def render_focus_timer(user_id: int) -> None:
    state = st.session_state
    owner_ok = state.get("focus_timer_user") == user_id
    deadline = state.get("focus_timer_deadline") if owner_ok else None
    paused = owner_ok and state.get("focus_timer_paused", False)
    if not deadline and not paused:
        if state.pop("focus_timer_done", False):
            st.success("Odak oturumu tamamlandı ve çalışma geçmişine eklendi.")
        st.markdown("<div class='section-kicker'>ODAK SEANSI</div><h2>Bir işe odaklan. Gerisini sonra düşün.</h2>", unsafe_allow_html=True)
        with st.form("pomodoro_start_form"):
            subject = st.selectbox("Ders", ["Matematik", "Türkçe", "Fizik", "Kimya", "Biyoloji", "Tarih", "Coğrafya", "Diğer"], key="pomodoro_subject")
            duration = st.select_slider("Odak süresi", options=[15, 25, 35, 45, 60, 90], value=25, format_func=lambda value: f"{value} dk", key="pomodoro_duration")
            start = st.form_submit_button("▶ Odağı başlat", use_container_width=True)
        if start:
            state.focus_timer_user = user_id
            state.focus_timer_subject = subject
            state.focus_timer_duration = int(duration)
            state.focus_timer_remaining = int(duration) * 60
            state.focus_timer_deadline = time.time() + int(duration) * 60
            state.focus_timer_paused = False
            st.rerun(scope="fragment")
        st.caption("Sayaç çalışırken bu sekme açık kalsın. Tamamlanan seans çalışma geçmişine otomatik kaydedilir.")
        return

    target_seconds = int(state.get("focus_timer_duration", 25)) * 60
    remaining = int(state.get("focus_timer_remaining", 0)) if paused else max(0, int(state.focus_timer_deadline - time.time()))
    mins, secs = divmod(remaining, 60)
    st.markdown(
        f"<div class='focus-timer-card'><div class='focus-live'>● CANLI ODAK</div><div class='focus-clock'>{mins:02d}:{secs:02d}</div>"
        f"<div class='focus-subject'>{html.escape(state.get('focus_timer_subject', 'Ders'))} · {int(state.get('focus_timer_duration', 25))} dakikalık seans</div></div>",
        unsafe_allow_html=True,
    )
    st.progress(min(1.0, max(0.0, 1 - remaining / max(1, target_seconds))), text="Seans ilerlemesi")
    controls = st.columns(3)
    if paused:
        if controls[0].button("▶ Devam et", key="pomodoro_resume", use_container_width=True):
            state.focus_timer_deadline = time.time() + remaining
            state.focus_timer_paused = False
            st.rerun(scope="fragment")
    elif controls[0].button("Ⅱ Duraklat", key="pomodoro_pause", use_container_width=True):
        state.focus_timer_remaining = remaining
        state.focus_timer_deadline = None
        state.focus_timer_paused = True
        st.rerun(scope="fragment")
    if controls[1].button("Bitir ve kaydet", key="pomodoro_finish", use_container_width=True):
        elapsed_seconds = max(0, target_seconds - remaining)
        elapsed_minutes = max(1, int((elapsed_seconds + 59) // 60))
        logs = read_user_json(user_id, "study_sessions", [])
        logs.append({"id": uuid.uuid4().hex[:10], "date": date.today().isoformat(), "minutes": elapsed_minutes,
                     "subject": state.get("focus_timer_subject", "Ders"), "note": "Odak modu seansı"})
        write_user_json(user_id, "study_sessions", logs)
        award_xp(user_id, f"session:{logs[-1]['id']}", max(5, elapsed_minutes // 5), "Odak seansı")
        state.focus_timer_deadline = None
        state.focus_timer_paused = False
        state.focus_timer_done = True
        st.rerun()
    if controls[2].button("Sıfırla", key="pomodoro_reset", use_container_width=True):
        state.focus_timer_deadline = None
        state.focus_timer_paused = False
        state.focus_timer_remaining = 0
        st.rerun(scope="fragment")
    if not paused and remaining <= 0:
        logs = read_user_json(user_id, "study_sessions", [])
        logs.append({"id": uuid.uuid4().hex[:10], "date": date.today().isoformat(),
                     "minutes": int(state.get("focus_timer_duration", 25)),
                     "subject": state.get("focus_timer_subject", "Ders"), "note": "Odak modu tamamlandı"})
        write_user_json(user_id, "study_sessions", logs)
        award_xp(user_id, f"session:{logs[-1]['id']}", max(5, int(state.get("focus_timer_duration", 25)) // 5), "Odak seansı tamamlandı")
        state.focus_timer_deadline = None
        state.focus_timer_paused = False
        state.focus_timer_done = True
        st.rerun()


def phoenix_mark_svg(size: int = 36) -> str:
    """Small original line-art phoenix mark used throughout the interface."""
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 64 64" role="img" aria-label="Anka kuşu" '
            'xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="3.4" '
            'stroke-linecap="round" stroke-linejoin="round"><path d="M32 54c-3-10-2-19 1-28 1 8 5 12 10 15-1-11 4-18 11-24-1 13 3 21 7 26-5-1-9-2-13-5 1 7-1 13-5 18"/>'
            '<path d="M30 54c3-10 2-19-1-28-1 8-5 12-10 15 1-11-4-18-11-24 1 13-3 21-7 26 5-1 9-2 13-5-1 7 1 13 5 18"/>'
            '<path d="M32 28c-4-6-4-12 0-19 4 7 4 13 0 19Zm-8 30c3-3 5-6 8-10 3 4 5 7 8 10M26 59h12"/></svg>')


def phoenix_watermark_svg() -> str:
    """Large transparent phoenix line art for the ambient page background."""
    return '''<div class="phoenix-backdrop" aria-hidden="true"><svg viewBox="0 0 900 900" xmlns="http://www.w3.org/2000/svg">
    <defs><linearGradient id="wmWing" x1=".08" y1=".96" x2=".92" y2=".05"><stop stop-color="#ed4655"/><stop offset=".48" stop-color="#b54ed5"/><stop offset="1" stop-color="#7863ff"/></linearGradient><radialGradient id="wmCore"><stop stop-color="#f15b72" stop-opacity=".55"/><stop offset="1" stop-color="#8f41cb" stop-opacity="0"/></radialGradient></defs>
    <circle cx="472" cy="424" r="340" fill="url(#wmCore)"/>
    <g fill="none" stroke="url(#wmWing)" stroke-linecap="round" stroke-linejoin="round">
    <path stroke-width="12" d="M448 552C351 493 263 404 198 286c79 34 144 74 197 124C348 301 361 204 431 94c12 135 46 239 102 312 12-122 73-225 179-305-45 134-44 244 5 330-73-33-130-75-174-127 19 113-3 207-68 289-9-88-33-160-82-213-1 67-10 124-33 172Z"/>
    <path stroke-width="8" d="M429 476c-88-92-180-151-291-177 57 67 99 133 125 202-97-44-186-57-281-42 92 45 164 103 218 176-88-12-164-3-238 30 111 9 205 38 288 94-64 18-120 48-172 92 111-30 210-31 304-4m40-371c88-92 180-151 291-177-57 67-99 133-125 202 97-44 186-57 281-42-92 45-164 103-218 176 88-12 164-3 238 30-111 9-205 38-288 94 64 18 120 48 172 92-111-30-210-31-304-4"/>
    <path stroke-width="10" d="M420 595c-29 69-63 125-107 179m194-179c29 69 63 125 107 179M455 350c-33-55-37-112-11-177 47 59 63 119 40 181"/>
    </g><g fill="#ffd0a4"><circle cx="455" cy="386" r="8"/><path d="m465 384 31 8-29 12Z"/></g>
    <g fill="none" stroke="#f66b83" stroke-linecap="round"><path stroke-width="5" d="M227 168l-8-22m-28 54-18-15m534-18 8-22m28 54 18-15"/><path stroke-width="3" d="m288 104-6-15m326 15 6-15"/></g>
    </svg></div>'''


def render_login() -> None:
    theme_picker_columns = st.columns([1, 1, 1])
    theme_mode = theme_picker_columns[1].selectbox("Tema", ["Açık", "Koyu"], index=1, key="theme_mode", label_visibility="collapsed")
    background_path = Path(__file__).resolve().parent / "assets" / "login_mountains.png"
    background_rule = ""
    mountain_rules = ""
    if background_path.exists():
        import base64
        encoded_image = base64.b64encode(background_path.read_bytes()).decode("ascii")
        background_rule = f'background-image:linear-gradient(90deg,#0b1724a8,#10202b78),url("data:image/png;base64,{encoded_image}");'
    else:
        mountain_rules = '''
        [data-testid="stAppViewContainer"]:before { content:"";position:fixed;right:8vw;top:12vh;width:min(54vw,620px);height:min(54vw,620px);pointer-events:none;border-radius:50%;opacity:.57;background:radial-gradient(circle,#fff7d8 0 3%,#ffc859 4% 6%,#ef5038 7% 10%,#371d1d 11% 13%,transparent 14% 23%,#ff6a3b55 24% 25%,transparent 26%);filter:drop-shadow(0 0 50px #f04b2a88); }
        [data-testid="stAppViewContainer"]:after { content:"";position:fixed;inset:0;pointer-events:none;opacity:.32;background:repeating-linear-gradient(128deg,transparent 0 9%,#ffffff08 9.1% 9.25%,transparent 9.35% 18%),linear-gradient(145deg,transparent 35%,#c43e3024 35.2% 35.5%,transparent 35.7% 60%,#ffc75b16 60.2% 60.4%,transparent 60.6%); }
        '''
    auth_theme_css = ""
    if theme_mode == "Açık":
        auth_theme_css = '''
        [data-testid="stVerticalBlockBorderWrapper"] { background:#fffaf1df!important;border-color:#ffffffb0!important; }
        .auth-title { color:#241f20!important;text-shadow:none!important; }
        .auth-copy,[data-testid="stForm"] label,[data-testid="stForm"] p { color:#575258!important; }
        [data-testid="stForm"] input { background:#fffefa!important;border-color:#b7a99b!important;color:#27252a!important; }
        [data-testid="stForm"] input::placeholder { color:#77747a!important; }
        [data-testid="stForm"] button { background:linear-gradient(100deg,#b93d31,#d37035)!important;color:white!important; }
        [data-testid="stTabs"] [data-baseweb="tab-list"] { background:#eee6dd!important; }
        [data-testid="stTabs"] [data-baseweb="tab"] { color:#5c5351!important; }
        [data-testid="stTabs"] [aria-selected="true"] { background:white!important;color:#a53c31!important; }
        .auth-feature-strip span { background:#ffffffb8!important;border-color:#d8c9b9!important;color:#544944!important; }
        '''
    st.markdown(f'''<style>
    html,body,[data-testid="stAppViewContainer"] {{ background:#151417 !important; }}
    [data-testid="stAppViewContainer"] {{ background-image:radial-gradient(ellipse at 80% 30%,#a332292e,transparent 42%),linear-gradient(135deg,#13151b,#272022 58%,#16171c);{background_rule} background-position:center;background-size:cover;background-attachment:fixed; }}
    {mountain_rules}
    [data-testid="stMainBlockContainer"] {{ position:relative;z-index:2;max-width:520px!important;padding-top:7vh!important;padding-bottom:8vh!important; }}
    [data-testid="stSidebar"] {{ display:none; }}
    [data-testid="stVerticalBlockBorderWrapper"] {{ background:#14232fd9;border:1px solid #ffffff3b;border-radius:24px;padding:1.65rem 1.7rem 1.2rem;backdrop-filter:blur(20px);box-shadow:0 30px 90px #030a10a8; }}
    [data-testid="stForm"] {{ background:transparent;border:0;padding:0; }}
    [data-testid="stForm"] label,[data-testid="stForm"] p {{ color:#dbe5e8!important; }}
    [data-testid="stForm"] input {{ background:#10202bbd!important;border:1px solid #ffffff42!important;border-radius:999px!important;color:#fff!important;min-height:46px;padding-left:1rem; }}
    [data-testid="stForm"] input::placeholder {{ color:#aebdc5!important; }}
    [data-testid="stForm"] button {{ border-radius:999px!important;background:#f0f5f3!important;color:#182d30!important;border:0!important;font-weight:750!important;min-height:46px; }}
    [data-testid="stTabs"] [data-baseweb="tab-list"] {{ background:#ffffff0d!important;border:1px solid #ffffff1c; }}
    [data-testid="stTabs"] [data-baseweb="tab"] {{ color:#dbe4e8!important; }}
    [data-testid="stTabs"] [aria-selected="true"] {{ color:#142a30!important; }}
    .auth-brand {{ display:flex;align-items:center;justify-content:center;gap:.7rem;color:#fff8ee;font-size:.82rem;font-weight:850;letter-spacing:.17em;margin:.25rem 0 1rem;text-shadow:0 2px 15px #0008; }}
    .auth-brand span {{ display:grid;place-items:center;width:42px;height:42px;border-radius:15px;background:linear-gradient(145deg,#ffe39a,#ff9d50 48%,#dd4338);color:#381d1c;font-size:1.15rem;letter-spacing:0;box-shadow:0 0 28px #f1754666,inset 0 1px 0 #fff9; }}
    .auth-title {{ color:#fffaf5;font-size:clamp(1.7rem,4vw,2.15rem);font-weight:820;letter-spacing:-.045em;text-align:center;margin:.25rem 0 .45rem;text-shadow:0 3px 28px #ff684233; }}
    .auth-copy {{ color:#d4d1d0;text-align:center;font-size:.93rem;line-height:1.55;margin:0 0 .9rem; }}
    .auth-feature-strip {{ display:flex;flex-wrap:wrap;justify-content:center;gap:.42rem;margin:0 0 1.2rem; }}
    .auth-feature-strip span {{ padding:.37rem .58rem;border:1px solid #ffffff20;border-radius:999px;background:#ffffff09;color:#e9d8c9;font-size:.68rem;font-weight:650;letter-spacing:.015em; }}
    [data-testid="stForm"] [data-baseweb="input"] {{ border-radius:14px!important;background:#ffffff08!important;box-shadow:0 5px 18px #0002; }}
    [data-testid="stForm"] input {{ border-radius:14px!important; }}
    [data-testid="stForm"] input:focus {{ border-color:#ffb45d!important;box-shadow:0 0 0 2px #ffb45d33!important; }}
    [data-testid="stForm"] button {{ background:linear-gradient(100deg,#f2c56d,#fa8b4c 52%,#e44d42)!important;color:#261719!important;box-shadow:0 8px 24px #e1513d33,inset 0 1px 0 #ffffff90!important; }}
    [data-testid="stForm"] button:disabled {{ opacity:1!important;color:#512b22!important;filter:saturate(.78); }}
    [data-testid="stTabs"] [data-baseweb="tab-list"] {{ background:#ffffff0c!important;border:1px solid #ffffff1d;padding:5px!important; }}
    [data-testid="stTabs"] [data-baseweb="tab"] {{ border-radius:11px!important; }}
    [data-testid="stRadio"] [role="radiogroup"] {{ display:grid!important;grid-template-columns:1fr 1fr;gap:5px!important;padding:5px!important;border:1px solid #ffffff22;border-radius:14px;background:#ffffff0d; }}
    [data-testid="stRadio"] [role="radiogroup"] label {{ display:flex!important;justify-content:center;align-items:center;min-height:38px;margin:0!important;padding:.45rem .65rem!important;border-radius:10px!important;color:#d6dce3!important;font-weight:650!important; }}
    [data-testid="stRadio"] [role="radiogroup"] label:has(input:checked) {{ color:#36201d!important;background:linear-gradient(100deg,#f3d18a,#fa9c5b)!important;box-shadow:0 4px 14px #e1513d2a; }}
    [data-testid="stRadio"] [role="radiogroup"] label p {{ color:inherit!important; }}
    @media(max-width:600px) {{ [data-testid="stMainBlockContainer"]{{padding:3vh 1rem!important}} [data-testid="stVerticalBlockBorderWrapper"]{{padding:1.2rem!important;border-radius:20px}} }}
    {auth_theme_css}
    </style>''', unsafe_allow_html=True)
    st.markdown("""<style>
    html,body,[data-testid="stAppViewContainer"] { background:#110e19!important; }
    [data-testid="stAppViewContainer"] { background-image:radial-gradient(ellipse at 78% 20%,#8f42ba35,transparent 35%),radial-gradient(ellipse at 18% 84%,#e3444027,transparent 36%),linear-gradient(145deg,#100d17,#201324 52%,#17101b)!important; }
    [data-testid="stVerticalBlockBorderWrapper"] { background:linear-gradient(150deg,#251829e8,#17141eea)!important;border-color:#b46bba55!important;box-shadow:0 32px 100px #08050dba,0 0 55px #b2488b15!important; }
    .auth-brand { gap:.7rem;color:#fff7ff!important;letter-spacing:.13em!important; }
    .phoenix-brand-icon { display:grid;place-items:center;width:48px;height:48px;border-radius:17px;color:#ffe3bf;background:linear-gradient(145deg,#a148cf,#e54a50 72%,#f59e59);box-shadow:0 0 32px #e34c6852,inset 0 1px 0 #fff8; }
    .auth-title { text-shadow:0 0 30px #bf5bcb35!important; }
    [data-testid="stForm"] button { background:linear-gradient(100deg,#a04ac9,#d84464 58%,#f0784d)!important;color:#fff!important; }
    [data-testid="stRadio"] [role="radiogroup"] label:has(input:checked) { color:#fff!important;background:linear-gradient(100deg,#9748bd,#df4963 62%,#eb764b)!important; }
    [data-testid="stForm"] input:focus { border-color:#ca76dc!important;box-shadow:0 0 0 2px #bb54d43b!important; }
    </style>""", unsafe_allow_html=True)
    if theme_mode == "Açık":
        st.markdown("""<style>
        [data-testid="stAppViewContainer"] { background-image:radial-gradient(ellipse at 82% 22%,#a34cb22b,transparent 35%),radial-gradient(ellipse at 14% 82%,#e7434e22,transparent 38%),linear-gradient(145deg,#f8f4f8,#efe7f1)!important; }
        [data-testid="stVerticalBlockBorderWrapper"] { background:#fffafdE8!important;border-color:#d6b9dc!important;box-shadow:0 24px 70px #53244b28!important; }
        .auth-title { color:#2b1d33!important;text-shadow:none!important; }.auth-copy { color:#716579!important; }
        [data-testid="stForm"] label,[data-testid="stForm"] p { color:#4b3c51!important; }
        [data-testid="stForm"] input { background:#fffafd!important;color:#2d2033!important;border-color:#e3d3e7!important; }
        .auth-feature-strip span { background:#fbf5fc!important;color:#644a6a!important;border-color:#e8d9eb!important; }
        [data-testid="stRadio"] [role="radiogroup"] label { color:#624d68!important; }
        [data-testid="stTabs"] [data-baseweb="tab"] { color:#624d68!important; }
        </style>""", unsafe_allow_html=True)
    st.markdown(f'<div class="auth-brand"><span class="phoenix-brand-icon">{phoenix_mark_svg(30)}</span> YKS ÇALIŞMA STÜDYOSU</div>', unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown('<div class="auth-title">Hedefine hoş geldin</div><div class="auth-copy">YKS yolculuğunu planla, ilerlemeni takip et ve her gün küçük bir adım daha at.</div><div class="auth-feature-strip"><span>✦ Kişisel çalışma planı</span><span>◷ Günlük odak takibi</span><span>⌁ Güvenli hafıza</span></div>', unsafe_allow_html=True)
        auth_mode = st.radio("Hesap işlemi", ["Giriş yap", "Hesap oluştur"], horizontal=True,
                             label_visibility="collapsed", key="auth_mode")
        if auth_mode == "Giriş yap":
            with st.form("login_form"):
                username = st.text_input("Kullanıcı adı", placeholder="kullaniciadi", max_chars=32, key="login_username")
                password = st.text_input("Parola", type="password", placeholder="Parolan", max_chars=128, key="login_password")
                login = st.form_submit_button("Giriş yap  →", use_container_width=True)
            if login:
                user_id = authenticate(username, password)
                if user_id is None:
                    st.error("Kullanıcı adı veya parola hatalı.")
                else:
                    st.session_state.user_id = user_id
                    st.session_state.username = username.strip()
                    st.rerun()
        else:
            with st.form("register_form"):
                new_username = st.text_input("Kullanıcı adı", placeholder="3–10 karakter", max_chars=10, key="register_username")
                new_password = st.text_input("4 rakamlı parola", type="password", placeholder="Örn. 0427", max_chars=4, key="register_password", help="Tam 4 rakam girin. Başında sıfır olabilir.")
                confirm_password = st.text_input("Parolayı tekrar yaz", type="password", placeholder="4 rakamı tekrar girin", max_chars=4, key="register_password_confirm")
                register = st.form_submit_button("Hesap oluştur  →", use_container_width=True)
            if register:
                if new_password != confirm_password:
                    st.error("Parolalar eşleşmiyor.")
                else:
                    user_id, error = create_account(new_username, new_password)
                    if error:
                        st.error(error)
                    else:
                        st.session_state.user_id = user_id
                        st.session_state.username = new_username.strip()
                        st.rerun()
        st.caption("Parolan korunur · hesap verilerin bu çalışma alanında saklanır")

def main():
    if "user_id" not in st.session_state:
        st.session_state.user_id = None

    if st.session_state.user_id is None:
        render_login()
        st.stop()

    user_id = st.session_state.user_id
    api_ready = configure_gemini()
    with st.sidebar:
        st.markdown(f'<div class="side-brand"><span class="side-mark">{phoenix_mark_svg(25)}</span><span>ANKA <small style="display:block;color:#beaac9;font-weight:550;letter-spacing:.15em">YKS ÇALIŞMA STÜDYOSU</small></span></div>', unsafe_allow_html=True)
        safe_sidebar_name = html.escape(st.session_state.get("username", "Kullanıcı"), quote=True)
        st.markdown(f'<div class="sidebar-profile"><span class="sidebar-avatar">{safe_sidebar_name[:1].upper()}</span><span><b>{safe_sidebar_name}</b><small>Çalışma alanın aktif</small></span><i></i></div>', unsafe_allow_html=True)
        st.button("Çıkış yap", use_container_width=True, on_click=logout_user)
        st.download_button("⬇️ Hesap verilerimi yedekle", data=account_backup(user_id),
                           file_name=f"yks_kocu_yedek_{st.session_state.get('username', 'hesap')}.json",
                           mime="application/json", use_container_width=True)
        with st.expander("Yedekten geri yükle"):
            backup_upload = st.file_uploader("ANKA yedeği veya çevrimdışı değişiklik JSON'u", type=["json"], key="restore_backup_file")
            if backup_upload and st.button("Yedeği bu hesaba uygula", key="restore_backup_button", use_container_width=True):
                restored, restore_message = restore_account_backup(user_id, backup_upload)
                (st.success if restored else st.error)(restore_message)
                if restored:
                    st.rerun()
        unlocked_themes = ["Açık", "Koyu"]
        current_xp = xp_profile(user_id)["xp"]
        if current_xp >= 300:
            unlocked_themes.append("🔥 Alev Kanatlı")
        if current_xp >= 700:
            unlocked_themes.append("🌌 Kozmik Anka")
        theme_mode = st.selectbox("🎨 Tema", unlocked_themes, index=1, key="theme_mode")
        st.divider()

    if theme_mode != "Açık":
        theme_css = """
        :root { --ink:#f1f3f6; --muted:#aeb7c5; --brand:#ff5148; --mint:#ffb24c; --gold:#ffd36e; --line:#333a46; --paper:#11151c; }
        html,body,[data-testid="stAppViewContainer"] { background-color:#11151c!important; background-image:radial-gradient(ellipse at 78% 8%,#ff32221c,transparent 34%),radial-gradient(ellipse at 88% 14%,#ffc34a12,transparent 24%),linear-gradient(145deg,#10141b,#17191f 56%,#12151c)!important; background-attachment:fixed!important; }
        [data-testid="stAppViewContainer"] .main { color:#f1f3f6!important; }
        h1,h2,h3,h4,p,label,[data-testid="stCaptionContainer"] { color:var(--ink); }
        [data-testid="stSidebar"] { background:linear-gradient(165deg,#20191b,#12161e 62%,#19191a)!important; border-right:1px solid #59312d!important; }
        [data-testid="stSidebar"] * { color:#eceff4; }
        .side-nav-label { color:#ffae79!important; }
        [data-testid="stMetric"],.soft-card,[data-testid="stExpander"], [data-testid="stVerticalBlockBorderWrapper"] { background:#1a2029!important; border-color:#333b48!important; color:#f1f3f6!important; }
        [data-testid="stMetricValue"],.soft-card h3 { color:#f4f5f7!important; }
        .soft-card p,.empty-state { color:#b9c2cf!important; }
        .empty-state { background:#1a2029!important;border-color:#454d59!important; }
        .week-empty { background:linear-gradient(135deg,#1b212b,#171c24)!important;border-color:#353d49!important; }
        .week-empty-copy strong { color:#f1f3f6!important; }
        .week-empty-copy span { color:#aeb8c6!important; }
        .week-bars { background:linear-gradient(180deg,#252c36,#202630)!important; }
        .calendar-day { background:linear-gradient(145deg,#1b212a,#171c24)!important;border-color:#343c48!important; }
        .calendar-day small,.calendar-day span,.calendar-day .calendar-quiet { color:#aab4c2!important; }
        .calendar-day strong,.calendar-day ul { color:#e9edf3!important; }
        [data-testid="stForm"] { background:linear-gradient(145deg,#20252e,#191e26)!important;border:1px solid #343c48!important;border-radius:18px!important;padding:18px!important;box-shadow:0 12px 32px #05070c55!important; }
        .stTextInput input,.stTextArea textarea,.stDateInput input,.stTimeInput input,.stNumberInput input,.stSelectbox [data-baseweb="select"]>div { background:#171d26!important;color:#f1f3f6!important;border-color:#414957!important; }
        [data-testid="stTabs"] [data-baseweb="tab-list"] { background:#202630!important; }
        [data-testid="stTabs"] [data-baseweb="tab"] { color:#c0c8d3!important; }
        [data-testid="stTabs"] [aria-selected="true"] { background:#303844!important;color:#ffb24c!important; }
        [data-testid="stChatMessage"] { background:#1b222c!important;border-color:#343d4a!important; }
        [data-testid="stChatInput"] textarea { background:#171d26!important;color:#f1f3f6!important; }
        .stDownloadButton button { background:#302622!important;color:#ffd08b!important;border-color:#654638!important; }
        .hero-card { background:linear-gradient(115deg,#231719 0%,#52231f 55%,#9e382b 100%)!important;box-shadow:0 18px 45px #08090c88!important; }
        .hero-eyebrow { color:#ffd17d!important; }
        [data-testid="stSidebar"] [data-testid="stMetric"] { background:#251f22!important; }
        """
    else:
        theme_css = """
        :root { --ink:#202b3b; --muted:#687486; --brand:#b63e32; --mint:#397c70; --gold:#aa671e; --line:#e5ddd7; --paper:#f7f5f2; }
        html,body,[data-testid="stAppViewContainer"] { background-color:#f7f5f2!important; background-image:radial-gradient(ellipse at 82% 7%,#e9513512,transparent 33%),radial-gradient(ellipse at 91% 12%,#ffbf5912,transparent 23%),linear-gradient(145deg,#f8f6f3,#f2f0ee)!important; background-attachment:fixed!important; }
        [data-testid="stSidebar"] { background:linear-gradient(165deg,#292326,#171b22 70%,#202023)!important;border-right:1px solid #513331!important; }
        .side-mark { background:linear-gradient(135deg,#ffbd5b,#f26748)!important;color:#351d1b!important; }
        .side-nav-label { color:#ffbd90!important; }
        .stButton button { background:#a93b31!important;border-color:#a93b31!important; }
        .stButton button:hover { background:#872d27!important;border-color:#872d27!important; }
        .hero-card { background:linear-gradient(115deg,#252022 0%,#60302a 56%,#a44231 100%)!important; }
        .hero-eyebrow { color:#ffd17d!important; }
        .week-empty { background:linear-gradient(135deg,#fff,#f4f1ee)!important; }
        [data-testid="stForm"] { background:#fff!important;border:1px solid #e5ddd7!important;border-radius:18px!important;padding:18px!important;box-shadow:0 12px 30px #5430200c!important; }
        """
    st.markdown(f"<style>{theme_css}</style>", unsafe_allow_html=True)
    if theme_mode != "Açık":
        phoenix_theme_css = """
        :root { --ink:#f4eefa;--muted:#b5a8c0;--brand:#f05b61;--mint:#db8df0;--gold:#ffc578;--line:#3c2d45;--paper:#120e18; }
        html,body,[data-testid="stAppViewContainer"] { background:#120e18!important;background-image:radial-gradient(ellipse at 82% 0%,#9e3db927,transparent 38%),radial-gradient(ellipse at 8% 36%,#dc39431c,transparent 34%),linear-gradient(145deg,#110d18,#18121e 52%,#120f19)!important;background-attachment:fixed!important; }
        [data-testid="stAppViewContainer"] .main { color:#f4eefa!important; }
        h1,h2,h3,h4,p,label,[data-testid="stCaptionContainer"] { color:var(--ink); }
        [data-testid="stSidebar"] { background:linear-gradient(165deg,#211327,#17101d 60%,#100e17)!important;border-right:1px solid #6c355b!important; }
        [data-testid="stSidebar"] * { color:#f1eaf4; }
        [data-testid="stMetric"],.soft-card,[data-testid="stExpander"],[data-testid="stVerticalBlockBorderWrapper"] { background:linear-gradient(145deg,#211927,#1a1521)!important;border-color:#3c2d45!important;color:#f4eefa!important; }
        [data-testid="stMetricValue"],.soft-card h3 { color:#fff7ff!important; }
        .soft-card p,.empty-state { color:#bfb1c8!important; }
        .empty-state,.week-empty,.study-heatmap { background:linear-gradient(145deg,#211927,#1a1521)!important;border-color:#43314d!important; }
        .week-empty-copy strong { color:#fff5ff!important; }.week-empty-copy span { color:#b9a9c3!important; }
        .week-bars { background:linear-gradient(180deg,#2a2031,#211927)!important; }
        .calendar-day { background:linear-gradient(145deg,#211927,#1a1521)!important;border-color:#403049!important; }
        .calendar-day small,.calendar-day span,.calendar-day .calendar-quiet { color:#baaac5!important; }
        .calendar-day strong,.calendar-day ul { color:#f2eafa!important; }
        [data-testid="stForm"] { background:linear-gradient(145deg,#211927,#19141f)!important;border:1px solid #43314d!important;border-radius:20px!important;padding:20px!important;box-shadow:0 16px 42px #08050c75!important; }
        .stTextInput input,.stTextArea textarea,.stDateInput input,.stTimeInput input,.stNumberInput input,.stSelectbox [data-baseweb="select"]>div { background:#17121d!important;color:#f7effa!important;border-color:#493653!important; }
        [data-testid="stTabs"] [data-baseweb="tab-list"] { background:#211927!important; }[data-testid="stTabs"] [data-baseweb="tab"] { color:#c9bad2!important; }
        [data-testid="stTabs"] [aria-selected="true"] { background:#38223b!important;color:#ffa8bb!important; }
        [data-testid="stChatMessage"] { background:#211927!important;border-color:#43314d!important; }[data-testid="stChatInput"] textarea { background:#17121d!important;color:#f7effa!important; }
        .stDownloadButton button { background:#302039!important;color:#f3b7e5!important;border-color:#65466e!important; }
        """
    else:
        phoenix_theme_css = """
        :root { --ink:#271a30;--muted:#716579;--brand:#c94355;--mint:#9b4db1;--gold:#9b5b2b;--line:#e8dce9;--paper:#f8f4f8; }
        html,body,[data-testid="stAppViewContainer"] { background:#f8f4f8!important;background-image:radial-gradient(ellipse at 88% 2%,#a34cb215,transparent 34%),radial-gradient(ellipse at 3% 30%,#e7434e12,transparent 34%),linear-gradient(145deg,#fbf8fb,#f4eff6)!important;background-attachment:fixed!important; }
        [data-testid="stSidebar"] { background:linear-gradient(165deg,#26172e,#19121e 68%,#15101a)!important;border-right:1px solid #593153!important; }
        [data-testid="stSidebar"] * { color:#f3eaf7; }
        [data-testid="stMetric"],.soft-card,[data-testid="stExpander"],[data-testid="stVerticalBlockBorderWrapper"] { background:#fffafd!important;border-color:#eaddeb!important;color:#2b1d33!important; }
        [data-testid="stMetricValue"],.soft-card h3 { color:#291c31!important; }.soft-card p,.empty-state { color:#716579!important; }
        .empty-state,.week-empty,.study-heatmap { background:linear-gradient(145deg,#fffafd,#f7eff8)!important;border-color:#eaddeb!important; }
        .calendar-day { background:linear-gradient(145deg,#fffafd,#f7eff8)!important;border-color:#eaddeb!important; }
        [data-testid="stForm"] { background:#fffafd!important;border:1px solid #eaddeb!important;border-radius:20px!important;padding:20px!important;box-shadow:0 16px 42px #56335b0d!important; }
        .stTextInput input,.stTextArea textarea,.stDateInput input,.stTimeInput input,.stNumberInput input,.stSelectbox [data-baseweb="select"]>div { background:#fffafd!important;color:#2d2033!important;border-color:#e3d3e7!important; }
        """
    st.markdown(f"<style>{phoenix_theme_css}</style>", unsafe_allow_html=True)
    if theme_mode == "🔥 Alev Kanatlı":
        st.markdown("<style>:root{--brand:#f06b42!important;--mint:#ff9f5b!important;--gold:#ffd06e!important}.hero-card{background:radial-gradient(circle at 82% 48%,#f3a54746,transparent 31%),linear-gradient(112deg,#211315,#58211f 58%,#a43b2c)!important}.phoenix-backdrop{opacity:.13!important}</style>", unsafe_allow_html=True)
    elif theme_mode == "🌌 Kozmik Anka":
        st.markdown("<style>:root{--brand:#a85cf2!important;--mint:#62d7ee!important;--gold:#f6b95b!important}.hero-card{background:radial-gradient(circle at 82% 48%,#9d5fff55,transparent 34%),linear-gradient(112deg,#110e1d,#271744 57%,#49234f)!important}.phoenix-backdrop{opacity:.14!important}</style>", unsafe_allow_html=True)
    st.markdown("""<style>
    [data-testid="stAppViewContainer"] .main { position:relative; }
    [data-testid="stMainBlockContainer"] { position:relative; }
    .phoenix-backdrop { position:fixed;inset:0;z-index:0;pointer-events:none;display:flex;justify-content:flex-end;align-items:center;overflow:hidden;opacity:.075;mix-blend-mode:screen; }
    .phoenix-backdrop svg { width:min(74vw,900px);height:auto;transform:translate(13%,2%);filter:drop-shadow(0 0 30px #a844cd55); }
    .app-masthead { display:flex;align-items:center;justify-content:space-between;margin:-.55rem 0 1.2rem;padding:.7rem .95rem;border:1px solid #ffffff13;border-radius:15px;background:linear-gradient(100deg,#24182dba,#291621a8);color:#f6eefa;box-shadow:0 8px 30px #13091819; }
    .app-masthead-brand { display:flex;align-items:center;gap:.65rem;font-size:.74rem;font-weight:820;letter-spacing:.16em; }
    .app-masthead-mark { display:grid;place-items:center;width:34px;height:34px;border-radius:12px;background:linear-gradient(140deg,#a847ca,#dd475b 68%,#f08a53);color:white; }
    .app-masthead-date { color:#d0c1d9;font-size:.82rem; }
    .side-brand { gap:12px!important;letter-spacing:.1em!important;margin:.4rem 0 1.5rem!important; }
    .side-mark { width:43px!important;height:43px!important;border-radius:15px!important;background:linear-gradient(140deg,#a847ca,#dd475b 68%,#f08a53)!important;color:#fff!important;box-shadow:0 6px 24px #ce426245,inset 0 1px 0 #ffffff55; }
    .sidebar-profile { display:flex;align-items:center;gap:10px;padding:11px 12px;margin:.6rem 0 .45rem;border:1px solid #ffffff18;border-radius:15px;background:#ffffff09; }
    .sidebar-avatar { display:grid;place-items:center;flex:0 0 36px;height:36px;border-radius:12px;background:linear-gradient(140deg,#a847ca,#dd475b);font-weight:850;color:#fff; }
    .sidebar-profile b,.sidebar-profile small { display:block; }.sidebar-profile b { font-size:.87rem; }.sidebar-profile small { color:#bba8c5;font-size:.69rem;margin-top:2px; }.sidebar-profile i { margin-left:auto;width:8px;height:8px;border-radius:50%;background:#65d9a0;box-shadow:0 0 12px #65d9a0a8; }
    .side-nav-label { color:#d98be8!important;font-size:.67rem!important; }
    [data-testid="stSidebar"] [data-testid="stRadio"] label { border-radius:12px!important;margin:2px 0!important;padding:.7rem .8rem!important;transition:all .18s ease!important; }
    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) { background:linear-gradient(100deg,#a946c14a,#db455644)!important;box-shadow:inset 3px 0 #ef7a82,0 8px 22px #1009154d;color:#fff!important; }
    .hero-card { min-height:295px!important;padding:2.2rem 2.5rem!important;border:1px solid #e98ab13d!important;background:radial-gradient(ellipse at 83% 52%,#c445b944,transparent 34%),linear-gradient(112deg,#211427 0%,#421c35 47%,#832d3b 79%,#4b224f 100%)!important;box-shadow:0 22px 65px #35142c52, inset 0 1px 0 #ffffff12!important; }
    .hero-card { background:radial-gradient(ellipse at 84% 47%,#8b3fbd42,transparent 34%),radial-gradient(ellipse at 65% 100%,#de3a552a,transparent 42%),linear-gradient(112deg,#100e17 0%,#1d1425 40%,#30182f 73%,#191323 100%)!important; }
    .hero-card:after { width:410px!important;height:410px!important;right:3%!important;top:-62px!important;background:radial-gradient(circle,#b458e92e 0 18%,#e7526530 42%,#8f45bc1a 58%,transparent 71%)!important;filter:blur(2px); }
    .hero-card h1 { text-shadow:0 4px 36px #ff73762b; }.hero-card p { color:#e3d3e5!important; }.hero-eyebrow { color:#ffc880!important; }
    .hero-pill { background:#ffffff0d!important;border-color:#ffffff28!important;backdrop-filter:blur(10px); }
    .phoenix-hero { width:min(37%,350px)!important;min-width:220px!important;filter:drop-shadow(0 0 24px #e45b8a77);animation:phoenix-drift 7s ease-in-out infinite; }
    @keyframes phoenix-drift { 0%,100% { transform:translateY(0) rotate(-1deg); } 50% { transform:translateY(-7px) rotate(1deg); } }
    .section-kicker { color:#c65370!important; }.soft-card { border-radius:19px!important;transition:transform .18s ease,box-shadow .18s ease,border-color .18s ease!important; }
    .soft-card { position:relative;overflow:hidden;border-color:var(--line)!important;box-shadow:0 10px 30px #08050e14,inset 0 1px 0 #ffffff08!important; }
    .soft-card:before { content:"";position:absolute;left:0;top:0;width:34%;height:1px;background:linear-gradient(90deg,#b65be6,#ed5367,transparent);opacity:.65; }
    .soft-card:hover { transform:translateY(-2px);box-shadow:0 16px 38px #09050f55!important;border-color:#87529d!important; }
    [data-testid="stMetric"] { border-radius:18px!important;box-shadow:0 9px 28px #0a071222!important;transition:transform .18s ease,border-color .18s ease; }
    [data-testid="stMetric"]:hover { transform:translateY(-2px);border-color:#a34bbf!important; }
    .quick-access-title { margin:.1rem 0 .7rem!important;font-size:1.08rem!important;font-weight:720!important;letter-spacing:-.015em!important; }
    [data-testid="stMainBlockContainer"] [data-testid="stHeading"] h1 { font-size:clamp(1.8rem,3vw,2.4rem)!important;letter-spacing:-.045em!important; }
    [data-testid="stMainBlockContainer"] [data-testid="stHeading"] h2 { font-size:1.5rem!important;letter-spacing:-.03em!important; }
    [data-testid="stMainBlockContainer"] [data-testid="stHeading"] h2:after { content:"";display:block;width:40px;height:3px;margin-top:.45rem;border-radius:99px;background:linear-gradient(90deg,#ad4bc8,#e34a5b); }
    [data-testid="stDataFrame"] { border:1px solid var(--line);border-radius:15px;overflow:hidden; }
    [data-testid="stPlotlyChart"],[data-testid="stVegaLiteChart"],[data-testid="stArrowVegaLiteChart"] { border-radius:17px; }
    [data-testid="stAlert"] { border-radius:14px!important; }
    .stTextInput input:focus,.stTextArea textarea:focus,.stDateInput input:focus,.stNumberInput input:focus { border-color:#b866cf!important;box-shadow:0 0 0 2px #a34bbf35!important; }
    [data-testid="stSidebar"] [data-testid="stMetric"] { background:linear-gradient(140deg,#211629,#19131f)!important;border-color:#ffffff12!important; }
    [data-testid="stSidebar"] .stButton button,[data-testid="stSidebar"] .stDownloadButton button { background:#ffffff0d!important;border:1px solid #ffffff20!important;box-shadow:none!important;color:#f2eafa!important; }
    [data-testid="stSidebar"] .stButton button:hover,[data-testid="stSidebar"] .stDownloadButton button:hover { background:#9e4bb42e!important;border-color:#bd71c8!important; }
    [data-testid="stSidebar"] [data-testid="stSelectbox"] [data-baseweb="select"]>div { background:#1b1422!important;border-color:#4d3658!important;color:#f4eefa!important; }
    .stToggle [data-baseweb="switch"] div[role="switch"] { background:#61416e; }
    a { color:#d98be8; }
    .stLinkButton a { border-radius:12px!important; }
    .stButton button,.stDownloadButton button { border-radius:12px!important;background:linear-gradient(105deg,#a245c4,#d54362 68%,#ed7549)!important;color:#fff!important;border:0!important;box-shadow:0 7px 22px #9c356f2c!important; }
    .stButton button:hover,.stDownloadButton button:hover { filter:brightness(1.08);transform:translateY(-1px);box-shadow:0 11px 30px #9c356f45!important; }
    [data-testid="stProgressBar"] > div > div { background:linear-gradient(90deg,#a34bc7,#d84467,#f07c4c)!important; }
    .study-heatmap { border-radius:18px!important; }.calendar-day { border-radius:16px!important; }
    [data-testid="stMainBlockContainer"] { max-width:1460px!important;z-index:1; }
    @media(prefers-reduced-motion:reduce) { .phoenix-hero { animation:none!important; } }
    @media(max-width:760px) { .app-masthead { margin:0 0 1rem; }.app-masthead-date { display:none; }.hero-card { padding:1.4rem!important;min-height:235px!important; }.phoenix-hero { min-width:112px!important;width:30%!important; }.quick-access-title { font-size:1rem!important; }.study-heatmap { gap:4px;padding:.65rem; } }
    </style>""", unsafe_allow_html=True)
    st.markdown(f"<div class='app-masthead'><div class='app-masthead-brand'><span class='app-masthead-mark'>{phoenix_mark_svg(22)}</span> ANKA · YKS ÇALIŞMA STÜDYOSU</div><span class='app-masthead-date'>{datetime.now().strftime('%d.%m.%Y · %H:%M')}</span></div>", unsafe_allow_html=True)
    st.markdown(phoenix_watermark_svg(), unsafe_allow_html=True)
    if theme_mode == "Açık":
        st.markdown("<style>.phoenix-backdrop{opacity:.035;mix-blend-mode:multiply}.phoenix-backdrop svg{filter:drop-shadow(0 0 24px #8e48ad20)}</style>", unsafe_allow_html=True)

    if not api_ready:
        st.warning("Gemini API hazır değil. Kayıtlı veriler, notlar ve hesap makinesi kullanılabilir; AI özellikleri API anahtarı gerektirir.")

    records = load_memory(user_id)
    with st.sidebar:
        st.markdown("<div class='side-nav-label'>ÇALIŞMA ALANI</div>", unsafe_allow_html=True)
        active_view = st.radio("Bölümler", ["⌂ Genel Bakış", "📝 Soru Analizi", "🧭 Konu Haritası", "📅 Program", "🎓 Sınav Planlayıcı", "📈 İlerleme",
                                             "🎯 Odak Modu", "🎬 TYT Video Kampları", "🌐 Dünya Paneli", "⏱️ YPT Saatlerim", "🔥 AnkaXP & Arkadaş", "📦 Çevrimdışı çalışma", "🔗 Kaynak Arşivi", "🗂️ Hafıza", "🤖 JARVIS Araçları", "💬 Koçla Sohbet"],
                               label_visibility="collapsed", key="active_view")
        st.divider()
        st.markdown("<div class='side-nav-label'>DURUM</div>", unsafe_allow_html=True)
        st.markdown("🟢 **Yapay zekâ hazır**" if api_ready else "⚪ **Temel mod** · Yapay zekâ anahtarı ayarlı değil")
        st.metric("📂 Hafıza kaydı", len(records))

    if active_view == "⌂ Genel Bakış":
        render_dashboard(user_id, st.session_state.get("username", "Öğrenci"))
    if active_view == "🌐 Dünya Paneli":
        render_world_panel()
    if active_view == "⏱️ YPT Saatlerim":
        render_ypt_bridge(user_id)
    if active_view == "🔥 AnkaXP & Arkadaş":
        render_anka_social(user_id, st.session_state.get("username", "Öğrenci"))
    if active_view == "📦 Çevrimdışı çalışma":
        render_offline_kit(user_id)
    if active_view == "📝 Soru Analizi":
        st.subheader("Soru hata laboratuvarı")
        st.caption("Yanlış soruyu çözümle, hata türünü kaydet ve aralıklı tekrar kuyruğuna al.")
        uploaded = st.file_uploader("Sorunun fotoğrafını yükleyin", type=["png", "jpg", "jpeg"], key="question_image")
        if uploaded:
            st.image(uploaded, caption="Yüklenen soru", use_container_width=True)
        meta_a, meta_b = st.columns(2)
        mistake_subject = meta_a.selectbox("Ders", ["Matematik", "Türkçe", "Fizik", "Kimya", "Biyoloji", "Tarih", "Coğrafya"], key="mistake_subject")
        mistake_topic = meta_b.text_input("Konu", placeholder="Örn: Problemler", key="mistake_topic")
        error_kind = st.selectbox("Hata türü", ["Konu eksiği", "İşlem hatası", "Dikkat hatası", "Süre yetmedi", "Soruyu yanlış yorumladım"], key="mistake_kind")
        first_review = st.date_input("İlk tekrar tarihi", value=date.today() + timedelta(days=1), key="mistake_first_review")
        if st.button("🔍 Analiz et ve tekrar kuyruğuna kaydet", use_container_width=True):
            if not uploaded:
                st.warning("Önce bir soru fotoğrafı yükleyin.")
            else:
                try:
                    with st.spinner("Sorunuz inceleniyor..."):
                        analysis = analyze_image(uploaded)
                    st.session_state.last_analysis = analysis
                    save_memory(user_id, "soru_analizi", analysis, uploaded.name)
                    mistakes = read_user_json(user_id, "wrong_questions", [])
                    mistakes.append({"id": uuid.uuid4().hex[:10], "subject": mistake_subject,
                                     "topic": mistake_topic.strip() or uploaded.name, "error_kind": error_kind,
                                     "created_at": date.today().isoformat(), "next_review": first_review.isoformat(),
                                     "review_count": 0, "mastered": False, "confidence": 1, "analysis": analysis})
                    write_user_json(user_id, "wrong_questions", mistakes)
                    st.success("Analiz hafızaya alındı ve tekrar kuyruğuna eklendi.")
                except Exception as exc:
                    st.error(f"Soru analiz edilemedi: {exc}")
        if st.session_state.get("last_analysis"):
            st.markdown(st.session_state.last_analysis)
        st.divider()
        st.markdown("### Aralıklı tekrar kuyruğu")
        mistakes = read_user_json(user_id, "wrong_questions", [])
        due_mistakes = [item for item in mistakes if not item.get("mastered") and item.get("next_review", "") <= date.today().isoformat()]
        if not due_mistakes:
            st.markdown("<div class='empty-state'>Bugün için bekleyen tekrar yok. Yanlış sorularını kaydettiğinde uygun zamanda burada görünür.</div>", unsafe_allow_html=True)
        for mistake in due_mistakes:
            with st.container(border=True):
                st.markdown(f"**{html.escape(mistake.get('subject', 'Ders'))} · {html.escape(mistake.get('topic', 'Konu'))}**")
                st.caption(f"Hata türü: {mistake.get('error_kind', 'Belirtilmedi')} · Başarılı tekrar: {mistake.get('review_count', 0)} · Hâkimiyet: {mistake.get('confidence', 1)}/5")
                with st.expander("Çözüm analizini aç"):
                    st.markdown(mistake.get("analysis", ""))
                review_result = st.radio("Tekrar sonucu", ["Doğru çözdüm", "Yine zorlandım"], horizontal=True,
                                         key=f"review_result_{mistake['id']}")
                review_actions = st.columns(2)
                if review_actions[0].button("Tekrar ettim", key=f"review_done_{mistake['id']}", use_container_width=True):
                    intervals = [3, 7, 21]
                    if review_result == "Doğru çözdüm":
                        mistake["review_count"] = int(mistake.get("review_count", 0)) + 1
                        interval = intervals[min(mistake["review_count"] - 1, len(intervals) - 1)]
                        mistake["confidence"] = min(5, int(mistake.get("confidence", 1)) + 1)
                    else:
                        mistake["review_count"] = 0
                        interval = 1
                        mistake["confidence"] = max(1, int(mistake.get("confidence", 1)) - 1)
                    mistake["next_review"] = (date.today() + timedelta(days=interval)).isoformat()
                    write_user_json(user_id, "wrong_questions", mistakes)
                    if review_result == "Doğru çözdüm":
                        award_xp(user_id, f"review:{mistake['id']}:{mistake['review_count']}:{date.today().isoformat()}", 5, "Yanlış soruyu tekrar")
                    st.rerun()
                if review_actions[1].button("Artık biliyorum", key=f"review_mastered_{mistake['id']}", use_container_width=True):
                    mistake["mastered"] = True
                    write_user_json(user_id, "wrong_questions", mistakes)
                    award_xp(user_id, f"mastered:{mistake['id']}", 10, "Konu hâkimiyeti")
                    st.rerun()

    if active_view == "🧭 Konu Haritası":
        st.markdown("# 🧭 TYT · AYT konu haritası")
        st.caption("Kendi konu listenle eksiklerini gör, tekrar sırası belirle ve ilerlemeni kalıcı olarak takip et.")
        st.caption("Konu soru sayıları resmi bir ÖSYM sınıflaması değildir; son 5 kitapçığa bakıp kendi doğruladığın konu etiketlemesini gir.")
        st.link_button("MEB resmî öğretim programları", "https://tymm.meb.gov.tr/ogretim-programlari", help="Müfredat programlarını resmî MEB sayfasından kontrol et.")
        reference_cols = st.columns(5)
        reference_urls = [
            ("2026", "https://www.osym.gov.tr/2026-yuksekogretim-kurumlari-sinavi-2026yks-temel-soru-kitapciklari-ve-cevap-anahtarlari-yayimlandi"),
            ("2025", "https://www.osym.gov.tr/2025-yuksekogretim-kurumlari-sinavi-2025yks-temel-soru-kitapciklari-ve-cevap-anahtarlari-yayimlandi"),
            ("2024", "https://www.osym.gov.tr/2024yks-tyt-ayt-ve-ydt-temel-soru-kitapciklari-ve-cevap-anahtarlari"),
            ("2023", "https://www.osym.gov.tr/2023yks-tyt-ayt-ve-ydt-temel-soru-kitapciklari-ve-cevap-anahtarlari"),
            ("2022", "https://www.osym.gov.tr/2022yks-tyt-ayt-ve-ydt-temel-soru-kitapciklari-ve-cevap-anahtarlari"),
        ]
        for source_col, (source_year, source_url) in zip(reference_cols, reference_urls):
            source_col.link_button(f"{source_year} kitapçıkları", source_url, use_container_width=True)
        topic_rows = read_user_json(user_id, "topic_map", [])
        topic_rows = topic_rows if isinstance(topic_rows, list) else []
        with st.form("topic_map_add_form", clear_on_submit=True):
            topic_cols = st.columns([.65, .95, 1.4, 1.0, 1.1])
            exam_track = topic_cols[0].selectbox("Alan", ["TYT", "AYT"])
            topic_subject = topic_cols[1].selectbox("Ders", ["Matematik", "Geometri", "Türkçe", "Fizik", "Kimya", "Biyoloji", "Tarih", "Coğrafya", "Felsefe", "Din Kültürü"])
            topic_name = topic_cols[2].text_input("Konu", placeholder="Örn. Problemler · yaş problemleri")
            prerequisite = topic_cols[3].text_input("Ön koşul (isteğe bağlı)", placeholder="Temel işlemler")
            frequency_text = topic_cols[4].text_input("5 yıl soru sayısı", placeholder="0,2,1,0,3", help="Eski yıldan yeni yıla, virgülle ayrılmış kendi doğruladığın konu etiketlemesi.")
            topic_added = st.form_submit_button("＋ Konuyu haritaya ekle", use_container_width=True)
        if topic_added:
            if not topic_name.strip():
                st.warning("Haritaya eklemek için konu adı yaz.")
            elif any(row.get("track") == exam_track and row.get("subject") == topic_subject and row.get("topic", "").casefold() == topic_name.strip().casefold() for row in topic_rows):
                st.info("Bu konu haritanda zaten var.")
            else:
                try:
                    frequency_5y = [int(value.strip()) for value in frequency_text.split(",")] if frequency_text.strip() else []
                    if frequency_5y and (len(frequency_5y) != 5 or any(value < 0 for value in frequency_5y)):
                        raise ValueError
                except ValueError:
                    st.error("Soru dağılımı boş bırakılabilir veya 5 adet sıfır ya da pozitif tam sayı olmalı; örnek: 0,2,1,0,3")
                    st.stop()
                topic_rows.append({"id": uuid.uuid4().hex[:10], "track": exam_track, "subject": topic_subject,
                                   "topic": topic_name.strip(), "prerequisite": prerequisite.strip(), "status": "Başlanmadı",
                                   "frequency_5y": frequency_5y, "frequency_source": "Kullanıcı tarafından ÖSYM kitapçıklarından doğrulandı"})
                write_user_json(user_id, "topic_map", topic_rows)
                st.rerun()
        if topic_rows:
            filter_cols = st.columns(2)
            track_filter = filter_cols[0].selectbox("Sınav filtresi", ["Tümü", "TYT", "AYT"], key="topic_track_filter")
            subject_filter = filter_cols[1].selectbox("Ders filtresi", ["Tümü"] + sorted({row.get("subject", "Diğer") for row in topic_rows}), key="topic_subject_filter")
            visible_topics = [row for row in topic_rows if (track_filter == "Tümü" or row.get("track") == track_filter)
                             and (subject_filter == "Tümü" or row.get("subject") == subject_filter)]
            total_topics = len(visible_topics)
            mastered_topics = sum(row.get("status") == "Tamamlandı" for row in visible_topics)
            review_topics = sum(row.get("status") == "Tekrar" for row in visible_topics)
            topic_metrics = st.columns(3)
            topic_metrics[0].metric("Haritadaki konu", total_topics)
            topic_metrics[1].metric("Tamamlandı", mastered_topics)
            topic_metrics[2].metric("Tekrar sırası", review_topics)
            st.progress(mastered_topics / max(1, total_topics), text=f"Konu hâkimiyeti · %{round(100 * mastered_topics / max(1, total_topics))}")
            for row in visible_topics:
                with st.container(border=True):
                    topic_cols = st.columns([2.15, 1.1, 1.3, .48, 1.25])
                    prereq_text = f" · Önce: {html.escape(row.get('prerequisite'))}" if row.get("prerequisite") else ""
                    topic_cols[0].markdown(f"**{row.get('track', 'TYT')} · {html.escape(row.get('subject', 'Ders'))}**  \n{html.escape(row.get('topic', 'Konu'))}{prereq_text}")
                    frequency = row.get("frequency_5y", [])
                    if isinstance(frequency, list) and len(frequency) == 5:
                        total_frequency = sum(int(value) for value in frequency)
                        priority = "Yüksek öncelik" if total_frequency >= 10 else "Orta öncelik" if total_frequency >= 5 else "Temel takip"
                        topic_cols[0].caption(f"{date.today().year - 4}→{date.today().year}: " + " · ".join(str(value) for value in frequency) + f" = {total_frequency} · {priority}")
                    frequency_input = topic_cols[4].text_input("5 yıllık dağılım", value=",".join(str(value) for value in frequency) if isinstance(frequency, list) else "",
                                                               placeholder="0,1,2,0,3", key=f"topic_freq_{row.get('id')}", label_visibility="collapsed")
                    if frequency_input != (",".join(str(value) for value in frequency) if isinstance(frequency, list) else ""):
                        try:
                            new_frequency = [int(value.strip()) for value in frequency_input.split(",")] if frequency_input.strip() else []
                            if new_frequency and (len(new_frequency) != 5 or any(value < 0 for value in new_frequency)):
                                raise ValueError
                            row["frequency_5y"] = new_frequency
                            row["frequency_source"] = "Kullanıcı tarafından ÖSYM kitapçıklarından doğrulandı"
                            write_user_json(user_id, "topic_map", topic_rows)
                            st.rerun()
                        except ValueError:
                            st.warning("Dağılımı boş bırak veya beş sıfır/pozitif tam sayı gir.")
                    current_status = row.get("status", "Başlanmadı")
                    status_options = ["Başlanmadı", "Çalışılıyor", "Tekrar", "Tamamlandı"]
                    status_index = status_options.index(current_status) if current_status in status_options else 0
                    changed_status = topic_cols[1].selectbox("Durum", status_options, index=status_index, key=f"topic_status_{row.get('id')}", label_visibility="collapsed")
                    confidence = max(1, min(5, int(row.get("confidence", 3))))
                    new_confidence = topic_cols[2].select_slider("Hâkimiyet", options=[1, 2, 3, 4, 5], value=confidence, key=f"topic_conf_{row.get('id')}", label_visibility="collapsed")
                    if changed_status != current_status or int(new_confidence) != confidence:
                        row["status"] = changed_status
                        row["confidence"] = int(new_confidence)
                        write_user_json(user_id, "topic_map", topic_rows)
                        if changed_status == "Tamamlandı" and current_status != "Tamamlandı":
                            award_xp(user_id, f"topic_done:{row.get('id')}", 5, "Konu tamamlandı")
                        st.rerun()
                    if topic_cols[3].button("×", key=f"topic_delete_{row.get('id')}", help="Konuyu haritadan sil"):
                        write_user_json(user_id, "topic_map", [item for item in topic_rows if item.get("id") != row.get("id")])
                        st.rerun()
            if visible_topics:
                st.markdown("### Derslere göre konu hâkimiyeti")
                topic_summary = {}
                for row in visible_topics:
                    topic_summary.setdefault(row.get("subject", "Diğer"), []).append(int(row.get("confidence", 3)))
                topic_frame = pd.DataFrame([{"Ders": subject, "Ortalama hâkimiyet (1–5)": sum(scores) / len(scores)} for subject, scores in topic_summary.items()])
                st.bar_chart(topic_frame, x="Ders", y="Ortalama hâkimiyet (1–5)", color="#ba54c9")
        else:
            st.info("Haritan boş. Çalıştığın konuları yukarıdan ekledikçe eksik, tekrar ve tamamlanan başlıkların burada birikecek.")

    if active_view == "📅 Program":
        st.subheader("Çalışma programı")
        mode = st.radio("İşlem", ["Yapay zekâya program hazırlat", "Mevcut programımı kaydet"], horizontal=True)
        if mode.startswith("Yapay"):
            status = st.text_area("Hedefleriniz, günlük çalışma süreniz ve zorlandığınız dersler", height=130,
                                  placeholder="Örn: Sayısal öğrencisiyim, günde 4 saat çalışabilirim...")
            if st.button("🚀 Bana özel program hazırla", use_container_width=True):
                if not status.strip():
                    st.warning("Önce durumunuzu ve hedefinizi yazın.")
                else:
                    try:
                        exam_history = read_user_json(user_id, "exam_results", [])
                        recent_exam_text = "Henüz deneme sonucu kaydedilmedi."
                        if exam_history:
                            latest = max(exam_history, key=lambda item: item.get("date", ""))
                            recent_exam_text = ", ".join(f"{subject}: {float(latest.get(subject, 0)):.2f}/{maximum}" for subject, maximum in [("Türkçe", 40), ("Matematik", 40), ("Sosyal", 20), ("Fen", 20)])
                        mistake_history = read_user_json(user_id, "wrong_questions", [])
                        error_counts = {}
                        for mistake in mistake_history:
                            kind = mistake.get("error_kind", "Diğer")
                            error_counts[kind] = error_counts.get(kind, 0) + 1
                        common_errors = ", ".join(f"{kind}: {count}" for kind, count in sorted(error_counts.items(), key=lambda pair: pair[1], reverse=True)[:3]) or "Henüz yanlış soru örüntüsü yok."
                        prompt = ("Öğrencinin durumu:\n" + status + "\n\nSon deneme ders netleri:\n" + recent_exam_text +
                                  "\n\nYanlış sorularda görülen örüntüler:\n" + common_errors +
                                  "\n\nHafıza:\n" + memory_to_text(records) +
                                  "\n\nUygulanabilir 7 günlük YKS çalışma programı hazırla. Her gün ders, süre, konu ve ölçülebilir mini hedef olsun. "
                                  "Dengeli mola ve aralıklı tekrar zamanları ekle. Zayıf net gelen derslere öncelik ver, bilinen yanlış örüntülerine yönelik kısa alıştırmalar koy. Gerçekçi olmayan yoğunluk önermem.")
                        with st.spinner("Program hazırlanıyor..."):
                            plan = generate_text(prompt)
                        st.session_state.last_ai_plan = plan
                        save_memory(user_id, "calisma_programi", plan, "Yapay zekâ programı")
                    except Exception as exc:
                        st.error(f"Program hazırlanamadı: {exc}")
            if st.session_state.get("last_ai_plan"):
                st.markdown(st.session_state.last_ai_plan)
                if st.button("📊 Program görselini oluştur", key="image_ai", use_container_width=True):
                    show_program_image(st.session_state.last_ai_plan, "ai")
        else:
            plan = st.text_area("Haftalık planınızı yazın", height=160, placeholder="Pazartesi: Matematik 2 saat...")
            if st.button("💾 Programımı hafızaya kaydet", use_container_width=True):
                if not plan.strip():
                    st.warning("Önce programınızı yazın.")
                else:
                    save_memory(user_id, "calisma_programi", plan, "Mevcut program")
                    st.session_state.last_manual_plan = plan
                    st.success("Program hafızaya kaydedildi.")
            if st.session_state.get("last_manual_plan"):
                if st.button("📊 Program görselini oluştur", key="image_manual", use_container_width=True):
                    show_program_image(st.session_state.last_manual_plan, "manual")

    if active_view == "🎯 Odak Modu":
        st.markdown("# 🎯 Odak Modu")
        st.markdown("Bildirimleri kapat, tek ders seç ve seansını başlat. Sayaç tamamlandığında süre çalışma geçmişine eklenir.")
        render_focus_timer(user_id)
        st.markdown("### Son odak seansların")
        recent_focus = sorted(read_user_json(user_id, "study_sessions", []), key=lambda item: item.get("date", ""), reverse=True)[:7]
        if recent_focus:
            st.dataframe([{"Tarih": item.get("date"), "Ders": item.get("subject"), "Dakika": item.get("minutes"), "Not": item.get("note", "")} for item in recent_focus], use_container_width=True, hide_index=True)
        else:
            st.caption("İlk odak seansın burada görünecek.")

    if active_view == "🎬 TYT Video Kampları":
        st.markdown("# 🎬 TYT Video Kampları")
        st.caption("Seçili hocaların resmî YouTube kamplarını sayfadan ayrılmadan izle; ders numaranı kaydedip ilerlemeni takip et.")
        camps = {
            "Matematik · Rehber Matematik": {"key": "rehber_tyt_matematik", "title": "49 Günde TYT Matematik", "kind": "playlist", "id": "PLVoSZ0D0CB3pXrBmYoppjf2fwi3vqF-vY", "url": "https://www.youtube.com/playlist?list=PLVoSZ0D0CB3pXrBmYoppjf2fwi3vqF-vY", "note": "Resmî Rehber Matematik kamplarındaki 49 günlük TYT matematik listesi."},
            "Geometri · Rehber Matematik": {"key": "rehber_tyt_geometri", "title": "TYT + AYT Geometri kampı", "kind": "playlist", "id": "PLVoSZ0D0CB3o0kCERon9daQQTbyyin4Ne", "url": "https://www.youtube.com/playlist?list=PLVoSZ0D0CB3o0kCERon9daQQTbyyin4Ne", "note": "Rehber Matematik'in resmî geometri kamp oynatma listesi."},
            "Matematik · Eyüp B": {"key": "eyup_b_tyt_matematik", "title": "TYT Matematik · Eyüp B", "kind": "video", "id": "yh6xfXWRvVE", "url": "https://www.youtube.com/watch?v=yh6xfXWRvVE", "note": "Eyüp B Matematik Geometri kanalından TYT temel kavramlar dersi. Video içinden kanaldaki TYT serisine devam edebilirsin."},
            "Matematik · Bıyıklı Matematik": {"key": "biyikli_tyt_matematik", "title": "TYT Matematik kampı · Bıyıklı Matematik", "kind": "search", "url": "https://www.youtube.com/results?search_query=B%C4%B1y%C4%B1kl%C4%B1+Matematik+TYT+Matematik+Kamp%C4%B1", "note": "Bıyıklı Matematik'in TYT matematik kamp ve konu anlatımlarını YouTube'da aç."},
            "Matematik · Mert Hoca": {"key": "mert_hoca_tyt_matematik", "title": "TYT Matematik kampı · Mert Hoca", "kind": "search", "url": "https://www.youtube.com/results?search_query=Mert+Hoca+TYT+Matematik+Kamp%C4%B1", "note": "Mert Hoca'nın TYT kamp serilerine YouTube'dan ulaş."},
            "Türkçe · Rüştü Hoca": {"key": "rustu_tyt_turkce", "title": "49 Günde TYT Türkçe kamp başlangıcı", "kind": "video", "id": "8u62QLBnFqY", "url": "https://www.youtube.com/watch?v=8u62QLBnFqY", "note": "Rehber Matematik ve Rüştü Hoca'nın ortak TYT Matematik–Türkçe kamp duyurusu."},
            "Türkçe · Kadir Gümüş": {"key": "kadir_gumus_tyt_turkce", "title": "TYT Türkçe kampı · Kadir Gümüş", "kind": "search", "url": "https://www.youtube.com/results?search_query=Kadir+G%C3%BCm%C3%BC%C5%9F+TYT+T%C3%BCrk%C3%A7e+Kamp%C4%B1", "note": "Benim Hocam / Kadir Gümüş TYT Türkçe ders ve kamp videoları."},
            "Fizik · VIP Fizik": {"key": "vip_tyt_fizik", "title": "2026 TYT Fizik kampı", "kind": "playlist", "id": "PL9mxuVBieFNHWQSftkoEu7cuEefE39qSB", "url": "https://www.youtube.com/playlist?list=PL9mxuVBieFNHWQSftkoEu7cuEefE39qSB", "note": "VIP Fizik'in resmî bağlantı sayfasındaki TYT kamp oynatma listesi."},
            "Fizik · Özcan Aykın": {"key": "ozcan_aykin_tyt_fizik", "title": "55 Günde TYT Fizik kampı", "kind": "video", "id": "7aVrdQ7uSQ4", "url": "https://www.youtube.com/watch?v=7aVrdQ7uSQ4", "note": "Özcan Aykın Fizik kanalındaki kampın ilk dersi. Oynatıcıdan serinin devamına geçebilirsin."},
            "Fizik · Fizikfinito": {"key": "fizikfinito_tyt_fizik", "title": "TYT Fizik kampı · Fizikfinito", "kind": "search", "url": "https://www.youtube.com/results?search_query=Fizikfinito+TYT+Fizik+Kamp%C4%B1", "note": "Fizikfinito'nun TYT fizik kamp ve konu anlatımlarını YouTube'da aç."},
            "Fizik · Altuğ Güneş": {"key": "altug_gunes_tyt_fizik", "title": "TYT Fizik kampı · Altuğ Güneş", "kind": "search", "url": "https://www.youtube.com/results?search_query=Altu%C4%9F+G%C3%BCne%C5%9F+TYT+Fizik+Kamp%C4%B1", "note": "Altuğ Güneş'in TYT fizik kamp videolarını YouTube'da aç."},
            "Fizik · Fizikle Barış": {"key": "fizikle_baris_tyt_fizik", "title": "TYT Fizik kampı · Fizikle Barış", "kind": "search", "url": "https://www.youtube.com/results?search_query=Fizikle+Bar%C4%B1%C5%9F+TYT+Fizik+Kamp%C4%B1", "note": "Fizikle Barış'ın TYT fizik kamp serilerine YouTube'dan ulaş."},
            "Kimya · Kimya Adası": {"key": "kimya_adasi_tyt", "title": "34 Günde TYT Kimya kampı · 2027", "kind": "video", "id": "X72KNgNUjp8", "url": "https://www.youtube.com/watch?v=X72KNgNUjp8", "note": "Kimya Adası'nın kamp açılış dersi; açıklamasında 34 günlük TYT kamp oynatma listesi yer alıyor."},
            "Kimya · Kimya Dersleri / Sinan İhtiyaroğlu": {"key": "sinan_tyt_kimya", "title": "29 Günde TYT Kimya kampı", "kind": "playlist", "id": "PLVFnE9wUPer0", "url": "https://www.youtube.com/playlist?list=PLVFnE9wUPer0", "note": "Kimya Dersleri kanalının 2027 TYT için yayınladığı 29 günlük kamp listesi."},
            "Kimya · Görkem Şahin": {"key": "gorkem_sahin_tyt_kimya", "title": "TYT Kimya kampı · Görkem Şahin", "kind": "search", "url": "https://www.youtube.com/results?search_query=G%C3%B6rkem+%C5%9Eahin+TYT+Kimya+Kamp%C4%B1", "note": "Görkem Şahin'in Benim Hocam kanalındaki TYT kimya ders ve kamp videoları."},
            "Coğrafya · Benim Hocam / Bayram Meral": {"key": "bayram_meral_tyt_cografya", "title": "TYT Coğrafya genel tekrar kampı", "kind": "video", "id": "PupoOcwg6pA", "url": "https://www.youtube.com/watch?v=PupoOcwg6pA", "note": "Benim Hocam kanalındaki 2026 TYT Coğrafya genel tekrar kamp videosu."},
            "Coğrafya · Coğrafyanın Kodları": {"key": "cografyanin_kodlari_tyt", "title": "TYT Coğrafya kampı · Coğrafyanın Kodları", "kind": "search", "url": "https://www.youtube.com/results?search_query=Co%C4%9Frafyan%C4%B1n+Kodlar%C4%B1+TYT+Co%C4%9Frafya+Kamp%C4%B1", "note": "Coğrafyanın Kodları kanalındaki TYT coğrafya kamp serileri."},
            "Biyoloji · Dr. Biyoloji": {"key": "dr_biyoloji_tyt", "title": "TYT Birebir Biyoloji Kampı", "kind": "video", "id": "b5dOFdWNDLs", "url": "https://www.youtube.com/watch?v=b5dOFdWNDLs", "note": "Dr. Biyoloji kanalının TYT Birebir Biyoloji Kampı videosu; video açıklamasında kamp oynatma listesi bulunuyor."},
            "Biyoloji · Selin Hoca": {"key": "selin_hoca_tyt_biyoloji", "title": "TYT Biyoloji kampı · Selin Hoca", "kind": "search", "url": "https://www.youtube.com/results?search_query=Selin+Hoca+TYT+Biyoloji+Kamp%C4%B1+2026", "note": "Selin Hoca'nın resmî sitesinde YKS 2026 kampı ve TYT Biyoloji içerikleri bulunuyor; YouTube'da kamp videolarını aç."},
            "Tarih · Ramazan Yetgin": {"key": "ramazan_yetgin_tyt_tarih", "title": "TYT Tarih kampı · Ramazan Yetgin", "kind": "search", "url": "https://www.youtube.com/results?search_query=Ramazan+Yetgin+TYT+Tarih+Kamp%C4%B1", "note": "Benim Hocam / Ramazan Yetgin TYT tarih kamp ve tekrar videoları."},
            "Felsefe · Benim Hocam": {"key": "benim_hocam_tyt_felsefe", "title": "TYT Felsefe kampı · Benim Hocam", "kind": "search", "url": "https://www.youtube.com/results?search_query=Benim+Hocam+TYT+Felsefe+Kamp%C4%B1", "note": "TYT felsefe ve din kültürü konu anlatımı ile tekrar videoları."},
        }
        selected_camp = st.selectbox("Ders ve hoca", list(camps), key="selected_tyt_camp")
        camp = camps[selected_camp]
        st.markdown(f"### {html.escape(camp['title'])}")
        st.caption(camp["note"])
        if camp["kind"] == "playlist":
            embed_src = f"https://www.youtube-nocookie.com/embed/videoseries?list={camp['id']}"
            st.components.v1.iframe(embed_src, height=490, scrolling=False)
        elif camp["kind"] == "video":
            st.components.v1.iframe(f"https://www.youtube-nocookie.com/embed/{camp['id']}", height=430, scrolling=False)
        else:
            st.info("Bu öğretmenin güncel kamp videolarını YouTube aramasında görüntüle. Seçtiğin video YouTube'da açılır.")
        st.link_button("YouTube'da aç", camp["url"], use_container_width=True)
        progress = read_user_json(user_id, "camp_progress", {})
        watched = progress.get(camp["key"], [])
        lesson_cols = st.columns([1, 2])
        lesson_number = lesson_cols[0].number_input("İzlediğin son ders", min_value=1, max_value=300, value=1, step=1, key=f"camp_lesson_{camp['key']}")
        lesson_cols[1].caption(f"Bu kampta {len(watched)} ders ilerleme kaydın var.")
        if st.button("✓ Bu dersi tamamlandı olarak kaydet", key=f"save_camp_{camp['key']}"):
            if int(lesson_number) not in watched:
                watched.append(int(lesson_number))
            progress[camp["key"]] = sorted(watched)
            write_user_json(user_id, "camp_progress", progress)
            st.success(f"{lesson_number}. ders ilerlemene eklendi.")
            st.rerun()

    if active_view == "🎓 Sınav Planlayıcı":
        st.markdown("# 🎓 Sınav Planlayıcı")
        st.caption("TYT, AYT, MSÜ veya kendi deneme hedefin için tarih ve net hedefi belirle. Tarihler senin girdiğin kişisel plan olarak saklanır.")
        planned = read_user_json(user_id, "exam_plan", [])
        exam_results_for_plan = read_user_json(user_id, "exam_results", [])
        nearest = None
        for item in planned:
            try:
                exam_day = date.fromisoformat(item.get("date", ""))
                if exam_day >= date.today() and (nearest is None or exam_day < nearest[0]):
                    nearest = (exam_day, item)
            except ValueError:
                continue
        if nearest:
            countdown_days = (nearest[0] - date.today()).days
            st.markdown(f"<div style='padding:1.6rem 1.8rem;border-radius:22px;background:radial-gradient(circle at 88% 10%,#ffbc5a55,transparent 27%),linear-gradient(115deg,#211d20,#6d302b 60%,#b84432);color:#fff;box-shadow:0 18px 45px #832d2828'><div style='font-size:.75rem;letter-spacing:.15em;color:#ffd08b;font-weight:800'>SIRADAKİ HEDEF</div><div style='font-size:1.65rem;font-weight:780;margin:.35rem 0'>{html.escape(nearest[1].get('name','Sınav'))}</div><div style='font-size:1rem;opacity:.88'>{nearest[0]:%d %B %Y} · {countdown_days} gün kaldı</div></div>", unsafe_allow_html=True)
        st.markdown("### Yeni sınav hedefi")
        with st.form("exam_planner_form", clear_on_submit=True):
            ex1, ex2, ex3 = st.columns([1.2, 1, 1])
            exam_type = ex1.selectbox("Sınav türü", ["YKS · TYT", "YKS · AYT", "MSÜ", "Kurum denemesi", "Kişisel hedef"], key="planner_exam_type")
            target_date = ex2.date_input("Hedef tarih", value=date.today() + timedelta(days=30), key="planner_exam_date")
            target_net = ex3.number_input("Toplam net hedefi", min_value=0.0, max_value=120.0, value=0.0, step=1.0, help="İsteğe bağlı; boş bırakmak için 0 seç.", key="planner_target_net")
            exam_title = st.text_input("Hedefe vereceğin ad", placeholder="Örn. Yaz TYT denemesi", key="planner_exam_title")
            save_exam = st.form_submit_button("＋ Sınav hedefini ekle", use_container_width=True)
        if save_exam:
            if target_date < date.today():
                st.warning("Hedef tarihi bugün veya gelecekte olmalı.")
            else:
                planned.append({"id": uuid.uuid4().hex[:10], "name": exam_title.strip() or exam_type,
                                "type": exam_type, "date": target_date.isoformat(), "target_net": float(target_net)})
                write_user_json(user_id, "exam_plan", planned)
                st.success("Sınav hedefi kaydedildi.")
                st.rerun()
        if planned:
            st.markdown("### Planındaki sınavlar")
            for item in sorted(planned, key=lambda row: row.get("date", "")):
                try:
                    exam_day = date.fromisoformat(item.get("date", ""))
                except ValueError:
                    continue
                days_left = (exam_day - date.today()).days
                with st.container(border=True):
                    item_col, goal_col, del_col = st.columns([2.1, 1.4, .65])
                    item_col.markdown(f"**{html.escape(item.get('name','Sınav'))}**  \n{html.escape(item.get('type',''))} · {exam_day:%d.%m.%Y}")
                    if days_left >= 0:
                        goal_col.metric("Geri sayım", f"{days_left} gün")
                    else:
                        goal_col.metric("Durum", "Tarih geçti")
                    target = float(item.get("target_net", 0) or 0)
                    if target > 0 and exam_results_for_plan:
                        latest_plan_net = max(exam_results_for_plan, key=lambda row: row.get("date", "")).get("Toplam", 0)
                        goal_col.caption(f"Son deneme {float(latest_plan_net):g} / {target:g} net")
                        st.progress(min(1.0, max(0.0, float(latest_plan_net) / target)), text="Son deneme / hedef net")
                    if del_col.button("Sil", key=f"delete_exam_goal_{item.get('id')}", use_container_width=True):
                        write_user_json(user_id, "exam_plan", [row for row in planned if row.get("id") != item.get("id")])
                        st.rerun()
        else:
            st.markdown("<div class='empty-state'>Henüz sınav hedefi eklemedin. Tarihi belirlediğinde ana ekranda geri sayımı göreceksin.</div>", unsafe_allow_html=True)

    if active_view == "📈 İlerleme":
        st.markdown("# 📈 İlerleme Merkezi")
        st.caption("Çalışma düzenini ve deneme gelişimini tek görünümde incele.")
        progress_sessions = read_user_json(user_id, "study_sessions", [])
        progress_ypt = read_user_json(user_id, "ypt_sessions", [])
        progress_exams = read_user_json(user_id, "exam_results", [])
        progress_tasks = read_user_json(user_id, "study_tasks", [])
        today = date.today()
        completed_tasks = sum(bool(item.get("done")) for item in progress_tasks)
        progress_metrics = st.columns(4)
        progress_metrics[0].metric("Site · bugün", f"{sum(int(x.get('minutes',0)) for x in progress_sessions if x.get('date') == today.isoformat())} dk")
        progress_metrics[1].metric("YPT · bugün", f"{sum(int(x.get('minutes',0)) for x in progress_ypt if x.get('date') == today.isoformat())} dk")
        progress_metrics[2].metric("Tamamlanan görev", f"{completed_tasks}/{len(progress_tasks)}")
        progress_metrics[3].metric("Kayıtlı deneme", str(len(progress_exams)))
        span = st.selectbox("Grafik dönemi", [7, 30, 90], format_func=lambda value: f"Son {value} gün", key="progress_span")
        cutoff = today - timedelta(days=span-1)
        days = [cutoff + timedelta(days=index) for index in range(span)]
        site_by_day = {day.isoformat(): 0 for day in days}
        ypt_by_day = {day.isoformat(): 0 for day in days}
        for item in progress_sessions:
            if item.get("date") in site_by_day:
                site_by_day[item["date"]] += int(item.get("minutes", 0))
        for item in progress_ypt:
            if item.get("date") in ypt_by_day:
                ypt_by_day[item["date"]] += int(item.get("minutes", 0))
        trend = pd.DataFrame([{"Tarih": day.strftime("%d.%m"), "Bu site (dk)": site_by_day[day.isoformat()],
                               "YPT içe aktarımı (dk)": ypt_by_day[day.isoformat()]} for day in days])
        st.markdown("### Günlük çalışma süresi")
        if sum(site_by_day.values()) + sum(ypt_by_day.values()):
            st.area_chart(trend.set_index("Tarih"), color=["#bb4033", "#edaa73"], height=300)
        else:
            st.info("Bu dönemde henüz süre yok. Odak seansı veya YPT aktarımı eklediğinde grafik burada oluşacak.")
        recent_subjects = {}
        for label, rows in (("Bu site", progress_sessions), ("YPT", progress_ypt)):
            for item in rows:
                if cutoff.isoformat() <= item.get("date", "") <= today.isoformat():
                    key = (item.get("subject", "Diğer"), label)
                    recent_subjects[key] = recent_subjects.get(key, 0) + int(item.get("minutes", 0))
        subject_box, activity_box = st.columns([1, 1.2])
        with subject_box:
            st.markdown("### Derslere göre toplam")
            if recent_subjects:
                subject_frame = pd.DataFrame([{"Ders": subject, "Kaynak": source, "Dakika": minutes}
                                              for (subject, source), minutes in recent_subjects.items()])
                st.bar_chart(subject_frame, x="Ders", y="Dakika", color="Kaynak", height=300)
            else:
                st.caption("Ders dağılımı için önce çalışma kaydı ekle.")
        with activity_box:
            st.markdown("### 5 haftalık çalışma ısı haritası")
            heat_days = [today - timedelta(days=index) for index in reversed(range(35))]
            heat_dates = {day.isoformat() for day in heat_days}
            combined_day_minutes = {day: 0 for day in heat_dates}
            for item in progress_sessions + progress_ypt:
                if item.get("date") in combined_day_minutes:
                    combined_day_minutes[item["date"]] += int(item.get("minutes", 0))
            peak = max(combined_day_minutes.values(), default=0)
            cells = []
            for day in heat_days:
                amount = combined_day_minutes[day.isoformat()]
                level = 0 if amount == 0 else min(4, max(1, int(amount / max(1, peak) * 4 + .5)))
                cells.append(f"<span title='{day:%d.%m.%Y}: {amount} dk' class='heat-cell heat-{level}'></span>")
            st.markdown("<div class='study-heatmap'>" + "".join(cells) + "</div>", unsafe_allow_html=True)
            st.caption("YPT içe aktarılan ve bu sitede kaydedilen süreler toplam görünür; aynı oturumu ikisine birden kaydettiysen iki kez sayılır.")
        st.divider()
        st.subheader("Çalışma planı ve deneme takibi")
        programs = [row for row in load_memory(user_id) if row.get("type") == "calisma_programi"]
        if programs:
            chosen = st.selectbox("Görev listesine aktarılacak program", programs,
                                  format_func=lambda item: f"{item.get('title')} · {item.get('created_at')}",
                                  key="program_for_tasks")
            if st.button("Programı haftalık görevlere dönüştür", key="make_tasks"):
                try:
                    structured = generate_structured_plan(chosen["content"])
                    tasks = []
                    day_names = ["pazartesi", "salı", "çarşamba", "perşembe", "cuma", "cumartesi", "pazar"]
                    today_index = date.today().weekday()
                    for day_index, day in enumerate(structured.get("program", [])[:7]):
                        day_label = str(day.get("gun", ""))
                        normalized_day = day_label.casefold().strip()
                        named_index = next((i for i, name in enumerate(day_names) if name == normalized_day), None)
                        offset = (named_index - today_index) % 7 if named_index is not None else day_index
                        task_date = (date.today() + timedelta(days=offset)).isoformat()
                        for lesson in day.get("dersler", []):
                            tasks.append({"id": uuid.uuid4().hex[:10], "date": task_date,
                                          "day": day_label, "subject": lesson.get("ders", "Ders"),
                                          "topic": lesson.get("konu", ""), "target": lesson.get("hedef", ""), "done": False})
                    if not tasks:
                        st.warning("Programdan görev çıkarılamadı.")
                    else:
                        write_user_json(user_id, "study_tasks", tasks)
                        st.success(f"{len(tasks)} görev oluşturuldu.")
                        st.rerun()
                except Exception as exc:
                    st.error(f"Program görevlere dönüştürülemedi: {exc}")
        else:
            st.info("Önce Program sekmesinden bir program kaydedin.")

        tasks = read_user_json(user_id, "study_tasks", [])
        st.markdown("### Haftalık görev takvimi")
        week_start = date.today() - timedelta(days=date.today().weekday())
        calendar_cols = st.columns(7)
        weekdays_tr = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]
        for day_index, calendar_col in enumerate(calendar_cols):
            calendar_date = week_start + timedelta(days=day_index)
            day_tasks = [task for task in tasks if task.get("date") == calendar_date.isoformat()]
            done_for_day = sum(bool(task.get("done")) for task in day_tasks)
            title_lines = "".join(f"<li>{html.escape(task.get('subject', 'Ders'))}: {html.escape(task.get('topic') or task.get('target') or 'Çalışma')}</li>" for task in day_tasks[:2])
            if len(day_tasks) > 2:
                title_lines += f"<li>+{len(day_tasks) - 2} görev</li>"
            if not title_lines:
                title_lines = "<li class='calendar-quiet'>Boş</li>"
            today_class = " is-today" if calendar_date == date.today() else ""
            calendar_col.markdown(f"<div class='calendar-day{today_class}'><small>{weekdays_tr[day_index]}</small><strong>{calendar_date.day:02d}</strong><span>{done_for_day}/{len(day_tasks)} tamam</span><ul>{title_lines}</ul></div>", unsafe_allow_html=True)
        if tasks:
            completed = sum(bool(task.get("done")) for task in tasks)
            st.progress(completed / max(1, len(tasks)), text=f"Tamamlanan görevler: {completed}/{len(tasks)}")
            overdue_tasks = sorted([task for task in tasks if not task.get("done") and task.get("date", "") < date.today().isoformat()], key=lambda item: item.get("date", ""))
            if overdue_tasks:
                st.warning(f"{len(overdue_tasks)} tamamlanmamış görev geçmiş tarihte kaldı.")
                if st.button("🗓️ Gecikenleri hafifçe plana dağıt", key="reschedule_overdue"):
                    for index, task in enumerate(overdue_tasks):
                        task_day = date.today() + timedelta(days=index // 3)
                        task["date"] = task_day.isoformat()
                        task["day"] = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"][task_day.weekday()]
                    write_user_json(user_id, "study_tasks", tasks)
                    st.success("Geciken görevler günde en fazla üç görev olacak şekilde yeniden planlandı.")
                    st.rerun()
            today_tasks = [task for task in tasks if task.get("date") == date.today().isoformat()]
            st.markdown("**Bugünün görevleri**")
            for task in today_tasks:
                label = " · ".join(part for part in [task.get("subject", "Ders"), task.get("topic", ""), task.get("target", "")] if part)
                state = st.checkbox(label, value=bool(task.get("done")), key=f"task_{task['id']}")
                if state != bool(task.get("done")):
                    for item in tasks:
                        if item.get("id") == task["id"]:
                            item["done"] = state
                    write_user_json(user_id, "study_tasks", tasks)
                    if state:
                        award_xp(user_id, f"task:{task['id']}", 10, "Planlı görev")
                    st.rerun()
            with st.expander("Haftanın diğer görevleri"):
                for task in tasks:
                    if task.get("date") != date.today().isoformat():
                        label = " · ".join(part for part in [task.get("date", ""), task.get("subject", "Ders"),
                                                              task.get("topic", ""), task.get("target", "")] if part)
                        state = st.checkbox(label, value=bool(task.get("done")), key=f"task_{task['id']}")
                        if state != bool(task.get("done")):
                            for item in tasks:
                                if item.get("id") == task["id"]:
                                    item["done"] = state
                            write_user_json(user_id, "study_tasks", tasks)
                            if state:
                                award_xp(user_id, f"task:{task['id']}", 10, "Planlı görev")
                            st.rerun()

        st.divider()
        st.markdown("**Deneme sonuçları**")
        with st.form("exam_result_form"):
            exam_date = st.date_input("Deneme tarihi", value=date.today())
            exam_label = st.text_input("Deneme adı", placeholder="TYT denemesi")
            a, b, c, d = st.columns(4)
            net_turkish = a.number_input("Türkçe neti", min_value=0.0, max_value=40.0, step=0.25)
            net_math = b.number_input("Matematik neti", min_value=0.0, max_value=40.0, step=0.25)
            net_social = c.number_input("Sosyal neti", min_value=0.0, max_value=20.0, step=0.25)
            net_science = d.number_input("Fen neti", min_value=0.0, max_value=20.0, step=0.25)
            add_exam = st.form_submit_button("Denemeyi kaydet")
        if add_exam:
            results = read_user_json(user_id, "exam_results", [])
            results.append({"id": uuid.uuid4().hex[:10], "date": exam_date.isoformat(), "name": exam_label.strip() or "Deneme",
                            "Türkçe": net_turkish, "Matematik": net_math, "Sosyal": net_social, "Fen": net_science,
                            "Toplam": net_turkish + net_math + net_social + net_science})
            award_xp(user_id, f"exam:{results[-1]['id']}", 10, "Deneme analizi")
            write_user_json(user_id, "exam_results", results)
            st.success("Deneme sonucu kaydedildi.")
            st.rerun()
        results = read_user_json(user_id, "exam_results", [])
        if results:
            st.markdown("### Deneme konu karnesi")
            st.caption("Son 10 denemeden konu bazlı doğru/yanlış verisi toplanır. AI raporu yalnızca yeterli örnek olan konular için başarı oranı verir.")
            topic_results = read_user_json(user_id, "exam_topic_results", [])
            if isinstance(topic_results, list):
                with st.form("exam_topic_result_form", clear_on_submit=True):
                    topic_exam = st.selectbox("Hangi deneme?", results,
                                              format_func=lambda item: f"{item.get('date', '')} · {item.get('name', 'Deneme')}",
                                              key="topic_result_exam")
                    topic_entry_cols = st.columns(4)
                    topic_subject = topic_entry_cols[0].selectbox("Ders", ["Matematik", "Fizik", "Kimya", "Biyoloji", "Türkçe", "Tarih", "Coğrafya", "Felsefe", "Geometri"])
                    topic_entry = topic_entry_cols[1].text_input("Konu", placeholder="Dalgalar")
                    attempted = topic_entry_cols[2].number_input("Çözülen", min_value=1, max_value=100, value=10)
                    correct = topic_entry_cols[3].number_input("Doğru", min_value=0, max_value=100, value=5)
                    topic_saved = st.form_submit_button("Konu sonucunu ekle", use_container_width=True)
                if topic_saved:
                    if not topic_entry.strip():
                        st.warning("Konu adını gir.")
                    elif correct > attempted:
                        st.warning("Doğru sayısı çözülen soru sayısından büyük olamaz.")
                    else:
                        topic_results.append({"id": uuid.uuid4().hex[:10], "exam_id": topic_exam.get("id", topic_exam.get("date")),
                                              "exam_date": topic_exam.get("date", ""), "exam_name": topic_exam.get("name", "Deneme"),
                                              "subject": topic_subject, "topic": topic_entry.strip(),
                                              "attempted": int(attempted), "correct": int(correct)})
                        write_user_json(user_id, "exam_topic_results", topic_results)
                        st.success("Konu sonucu deneme karnesine eklendi.")
                        st.rerun()
                recent_exam_rows_for_topics = sorted(results, key=lambda item: item.get("date", ""), reverse=True)[:10]
                recent_exam_ids = {str(item.get("id", item.get("date", ""))) for item in recent_exam_rows_for_topics}
                recent_topic_results = [item for item in topic_results
                                        if str(item.get("exam_id", item.get("exam_date", ""))) in recent_exam_ids]
                if recent_topic_results:
                    topic_performance = {}
                    for item in recent_topic_results:
                        key = (item.get("subject", "Ders"), item.get("topic", "Konu"))
                        agg = topic_performance.setdefault(key, {"doğru": 0, "soru": 0})
                        agg["doğru"] += int(item.get("correct", 0))
                        agg["soru"] += int(item.get("attempted", 0))
                    perf_frame = pd.DataFrame([{"Ders": subject, "Konu": topic, "Doğru": vals["doğru"],
                                                "Soru": vals["soru"], "Başarı (%)": round(100 * vals["doğru"] / max(1, vals["soru"]))}
                                               for (subject, topic), vals in topic_performance.items()])
                    st.dataframe(perf_frame.sort_values(["Başarı (%)", "Soru"]), use_container_width=True, hide_index=True)
                    if st.button("✨ Haftalık nokta atışı teşhis oluştur", key="generate_exam_predictor", use_container_width=True):
                        recent_exam_rows = recent_exam_rows_for_topics
                        eligible = [row for row in perf_frame.to_dict("records") if row["Soru"] >= 5]
                        weak = sorted(eligible, key=lambda row: row["Başarı (%)"])[:5]
                        wrong_topics = [{"ders": item.get("subject"), "konu": item.get("topic"), "hata": item.get("error_kind"), "tekrar": item.get("review_count", 0)}
                                        for item in read_user_json(user_id, "wrong_questions", [])]
                        evidence = {"son_deneme_netleri": recent_exam_rows,
                                    "konu_bazli_yeterli_ornekli_basari": weak,
                                    "yanlis_defteri": wrong_topics,
                                    "kullanicinin_konu_oncelik_matrisi": read_user_json(user_id, "topic_map", [])}
                        try:
                            diagnosis = generate_text("Yalnızca aşağıdaki JSON verisine dayanarak Türkçe, kısa ve ölçülü bir haftalık YKS teşhis raporu hazırla. En fazla 3 konu öner; her öneride kanıt sayısını, başarı oranını ve 3 günlük uygulanabilir adımı yaz. Beşten az örneği olan konuda yüzde tahmini yapma; veri yoksa bunu açıkça söyle. Net veya soru dağılımı uydurma. Veri: " + json.dumps(evidence, ensure_ascii=False))
                            st.session_state.exam_predictor_report = diagnosis
                            save_memory(user_id, "deneme_teshisi", diagnosis, "Haftalık deneme teşhisi")
                        except Exception as exc:
                            st.error(f"Teşhis raporu üretilemedi: {exc}")
                    if st.session_state.get("exam_predictor_report"):
                        st.markdown(st.session_state.exam_predictor_report)
            try:
                import pandas as pd
                ordered_results = sorted(results, key=lambda item: item.get("date", ""))
                latest = ordered_results[-1]
                sections = [("Türkçe", 40), ("Matematik", 40), ("Sosyal", 20), ("Fen", 20)]
                weakest = min(sections, key=lambda item: float(latest.get(item[0], 0)) / item[1])
                st.markdown(f"<div class='soft-card' style='margin:.8rem 0 1rem;border-left:4px solid #df7952'><span class='section-kicker'>DENEME TEŞHİSİ</span><p style='margin-top:.35rem'>Son denemede en çok gelişim alanı <b>{weakest[0]}</b> görünüyor ({float(latest.get(weakest[0], 0)):.2f}/{weakest[1]} net). Bu hafta bu derse iki kısa tekrar oturumu ekle.</p></div>", unsafe_allow_html=True)
                latest_frame = pd.DataFrame([{"Ders": name, "Net": latest.get(name, 0), "Kalan net": maximum} for name, maximum in sections])
                st.bar_chart(latest_frame, x="Ders", y="Net", color="#d45a42", height=230)
                if len(ordered_results) > 1:
                    previous = ordered_results[-2]
                    delta = float(latest.get("Toplam", 0)) - float(previous.get("Toplam", 0))
                    st.metric("Son denemeden değişim", f"{'+' if delta >= 0 else ''}{delta:.2f} net", help=f"{previous.get('date')} → {latest.get('date')}")
                mistake_counts = {}
                for mistake in read_user_json(user_id, "wrong_questions", []):
                    mistake_counts[mistake.get("error_kind", "Diğer")] = mistake_counts.get(mistake.get("error_kind", "Diğer"), 0) + 1
                if mistake_counts:
                    common_error = max(mistake_counts, key=mistake_counts.get)
                    st.caption(f"Soru laboratuvarında en sık görülen hata: {common_error} ({mistake_counts[common_error]} kayıt).")
                frame = pd.DataFrame(ordered_results)
                st.line_chart(frame.set_index("date")[["Türkçe", "Matematik", "Sosyal", "Fen", "Toplam"]])
                st.dataframe(frame.iloc[::-1], use_container_width=True, hide_index=True)
                if st.button("Deneme kayıtlarını temizle", key="clear_exam_results"):
                    write_user_json(user_id, "exam_results", [])
                    st.rerun()
            except ImportError:
                st.dataframe(results, use_container_width=True)

    if active_view == "🔗 Kaynak Arşivi":
        st.subheader("Ders notu / kaynak bağlantısı")
        link = st.text_input("Web bağlantısı", placeholder="https://...")
        topic = st.text_input("Konu", placeholder="Örn: Fonksiyonlar")
        read_page = st.checkbox("Sayfa metnini okuyup hafızaya ekle", value=True)
        make_summary = st.checkbox("AI ile kısa özet de oluştur", value=True)
        pdf_file = st.file_uploader("PDF ders notu yükle (isteğe bağlı)", type=["pdf"], key="resource_pdf")
        if pdf_file and st.button("📑 PDF'i özetle ve hafızaya kaydet", key="summarize_pdf"):
            try:
                from pypdf import PdfReader
                pdf_reader = PdfReader(io.BytesIO(pdf_file.getvalue()))
                pdf_text = "\n".join((page.extract_text() or "") for page in pdf_reader.pages)[:12000]
                if not pdf_text.strip():
                    st.warning("PDF'de seçilebilir metin yok. Taranmış PDF için OCR gerekir.")
                else:
                    with st.spinner("PDF özetleniyor..."):
                        summary = summarize_resource(pdf_file.name, pdf_text) if make_summary else pdf_text
                    save_memory(user_id, "kaynak_pdf", f"Dosya: {pdf_file.name}\n\n{summary}", topic or pdf_file.name)
                    st.session_state.last_resource_summary = summary
                    st.success("PDF ve özeti hafızaya eklendi.")
            except ImportError:
                st.error("PDF okumak için pypdf yükleyin: pip install pypdf")
            except Exception as exc:
                st.error(f"PDF işlenemedi: {exc}")
        if st.session_state.get("last_resource_summary"):
            with st.expander("Son kaynak özeti"):
                st.markdown(st.session_state.last_resource_summary)
        if st.button("📥 Kaynağı hafızaya ekle", use_container_width=True):
            if not link.strip() or not topic.strip():
                st.warning("Bağlantı ve konu alanlarını doldurun.")
            elif read_page:
                with st.spinner("Sayfa okunuyor..."):
                    scraped, error = scrape_link(link)
                if error:
                    st.error(error)
                else:
                    content = scraped["content"]
                    if make_summary:
                        with st.spinner("Kaynak özetleniyor..."):
                            content = summarize_resource(scraped["title"], content)
                        st.session_state.last_resource_summary = content
                    save_memory(user_id, "kaynak_linki", f"URL: {link}\nBaşlık: {scraped['title']}\n\n{content}", topic)
                    st.success("Kaynak içeriği hafızaya eklendi.")
            else:
                save_memory(user_id, "kaynak_linki", link.strip(), topic)
                st.success("Kaynak bağlantısı hafızaya eklendi.")

    if active_view == "🗂️ Hafıza":
        st.subheader("Kayıtlı hafıza")
        records = load_memory(user_id)
        if not records:
            st.info("Henüz hafıza kaydı yok.")
        for index, record in enumerate(reversed(records[-30:])):
            with st.expander(f"{record.get('type', 'Kayıt')} · {record.get('title', 'Başlıksız')}"):
                st.caption(record.get("created_at", "Tarih yok"))
                st.write(record.get("content", ""))
                left, right = st.columns(2)
                if record.get("type") == "calisma_programi" and left.button("📊 Görsel oluştur", key=f"memory_img_{index}"):
                    show_program_image(record.get("content", ""), f"memory_{index}")
                if right.button("🗑️ Kaydı sil", key=f"delete_{index}"):
                    delete_memory_record(user_id, record.get("id", ""))
                    st.rerun()

    if active_view == "🤖 JARVIS Araçları":
        st.subheader("JARVIS notları ve hatırlatıcıları")
        note_text = st.text_area("Hızlı not", placeholder="Daha sonra tekrar edeceğim konu...", key="jarvis_note")
        if st.button("📝 Notu kaydet", key="save_jarvis_note"):
            if note_text.strip():
                notes = read_user_json(user_id, "notes", [])
                notes.append({"id": uuid.uuid4().hex[:12], "created_at": datetime.now().astimezone().isoformat(timespec="minutes"),
                              "text": note_text.strip()})
                write_user_json(user_id, "notes", notes)
                st.success("Not kaydedildi.")
                st.rerun()
            else:
                st.warning("Kaydetmek için not yazın.")

        saved_notes = read_user_json(user_id, "notes", [])
        search_note = st.text_input("Notlarda ara", key="search_jarvis_note").strip().casefold()
        visible_notes = [note for note in saved_notes if search_note in note.get("text", "").casefold()]
        for note in reversed(visible_notes[-20:]):
            col_note, col_delete_note = st.columns([5, 1])
            col_note.caption(note.get("created_at", ""))
            col_note.write(note.get("text", ""))
            if col_delete_note.button("Sil", key=f"del_note_{note.get('id')}"):
                write_user_json(user_id, "notes", [n for n in saved_notes if n.get("id") != note.get("id")])
                st.rerun()

        st.divider()
        st.markdown("**Hatırlatıcı ekle**")
        remind_date = st.date_input("Tarih", value=date.today(), key="jarvis_reminder_date")
        remind_time = st.time_input("Saat", value=(datetime.now() + timedelta(hours=1)).time().replace(second=0, microsecond=0), key="jarvis_reminder_time")
        remind_text = st.text_input("Neyi hatırlatayım?", key="jarvis_reminder_text")
        if st.button("⏰ Hatırlatıcı kur", key="add_jarvis_reminder"):
            due = datetime.combine(remind_date, remind_time).astimezone()
            if not remind_text.strip():
                st.warning("Hatırlatma metnini yazın.")
            elif due <= datetime.now().astimezone():
                st.warning("Hatırlatma zamanı gelecekte olmalı.")
            else:
                reminders = read_user_json(user_id, "reminders", [])
                reminders.append({"id": uuid.uuid4().hex[:12], "due_at": due.isoformat(), "text": remind_text.strip(), "done": False})
                write_user_json(user_id, "reminders", reminders)
                st.success("Hatırlatıcı kuruldu. Uygulama açıkken bu sekmeye tekrar geldiğinizde zamanı kontrol edilir.")
                st.rerun()

        render_reminders(user_id)

        st.divider()
        st.markdown("**Ders rehberleri**")
        st.write("Matematik: Rehber Matematik, Eyüp B, Bıyıklı Matematik · Fizik: VIP Fizik, Özcan Aykın, Fizikfinito · "
                 "Kimya: Kimya Adası, Görkem Şahin, Sinan İhtiyaroğlu · Biyoloji: Selin Hoca, Dr. Biyoloji · "
                 "Türkçe: Rüştü Hoca, Kadir Gümüş · Tarih: Ramazan Yetgin · Coğrafya: Bayram Meral, Coğrafyanın Kodları")

    if active_view == "💬 Koçla Sohbet":
        st.divider()
        st.header("💬 Koçunla konuş")
        chats = read_user_json(user_id, "chats", [])
        if not chats:
            chats = [{"id": uuid.uuid4().hex[:12], "title": "Yeni sohbet", "messages": []}]
            write_user_json(user_id, "chats", chats)
        chat_ids = [chat["id"] for chat in chats]
        if st.session_state.get("active_chat") not in chat_ids:
            st.session_state.active_chat = chat_ids[-1]
        chat_left, chat_mid, chat_right = st.columns([3, 1, 1])
        active_chat_id = chat_left.selectbox("Sohbet", chat_ids,
                                            index=chat_ids.index(st.session_state.active_chat),
                                            format_func=lambda item_id: next((c["title"] for c in chats if c["id"] == item_id), "Sohbet"),
                                            key="chat_selector")
        st.session_state.active_chat = active_chat_id
        active_chat = next(chat for chat in chats if chat["id"] == active_chat_id)
        chat_mid.button("➕ Yeni", key="new_chat", on_click=create_new_chat, args=(user_id,))
        if chat_right.button("🧹 Temizle", key="clear_chat"):
            active_chat["messages"] = []
            active_chat["title"] = "Yeni sohbet"
            write_user_json(user_id, "chats", chats)
            st.rerun()
        if active_chat["messages"]:
            st.download_button("Sohbeti JSON indir", json.dumps(active_chat, ensure_ascii=False, indent=2),
                               file_name="jarvis_sohbet.json", mime="application/json", key="export_chat")
        messages = active_chat["messages"]
        for message in messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        user_input = st.chat_input("Mesajını yaz ve Enter'a bas...")
        if user_input:
            messages.append({"role": "user", "content": user_input})
            if active_chat["title"] == "Yeni sohbet":
                active_chat["title"] = user_input[:36] + ("…" if len(user_input) > 36 else "")
            write_user_json(user_id, "chats", chats)
            with st.chat_message("user"):
                st.markdown(user_input)
            with st.chat_message("assistant"):
                try:
                    normalized = user_input.casefold().strip()
                    if normalized.startswith("hesapla "):
                        answer = safe_calculate(user_input[8:].strip())
                    elif normalized.startswith("not al "):
                        notes = read_user_json(user_id, "notes", [])
                        notes.append({"id": uuid.uuid4().hex[:12], "created_at": datetime.now().astimezone().isoformat(timespec="minutes"),
                                      "text": user_input[7:].strip()})
                        write_user_json(user_id, "notes", notes)
                        answer = "Notunu kaydettim."
                    elif any(word in normalized for word in ("hocalar", "ders kadrosu", "hangi hoca")):
                        answer = "Matematik: Rehber Matematik, Eyüp B, Bıyıklı Matematik; Fizik: VIP Fizik, Özcan Aykın, Fizikfinito; " \
                                 "Kimya: Kimya Adası, Görkem Şahin, Sinan İhtiyaroğlu; Biyoloji: Selin Hoca, Dr. Biyoloji; " \
                                 "Türkçe: Rüştü Hoca, Kadir Gümüş; Tarih: Ramazan Yetgin; Coğrafya: Bayram Meral, Coğrafyanın Kodları."
                    else:
                        facts = read_user_json(user_id, "facts", [])
                        if re.search(r"benim adım|hedefim|favorim|seviyorum", normalized):
                            facts.append(user_input)
                            write_user_json(user_id, "facts", facts[-30:])
                        prior = "\n".join(f"{m['role']}: {m['content']}" for m in messages[-9:-1])
                        prompt = ("Sen JARVIS adlı, YKS öğrencisine kısa, somut ve motive edici öneriler veren kişisel koçsun. "
                                  "Kullanıcıya samimi ve net Türkçe ile, gerekirse 'efendim' diye hitap et. "
                                  "Belirsiz bilgiyi kesinmiş gibi sunma; uygulanabilir öneriler ver. "
                                  "Ders rehberleri: Matematik Rehber Matematik, Eyüp B, Bıyıklı Matematik; Fizik VIP Fizik, Özcan Aykın, Fizikfinito; "
                                  "Kimya Kimya Adası, Görkem Şahin, Sinan İhtiyaroğlu; Biyoloji Selin Hoca, Dr. Biyoloji; "
                                  "Türkçe Rüştü Hoca, Kadir Gümüş; Tarih Ramazan Yetgin; Coğrafya Bayram Meral, Coğrafyanın Kodları.\n"
                                  f"Öğrenci bilgileri: {'; '.join(facts[-10:])}\n"
                                  f"YKS hafızası:\n{memory_to_text(load_memory(user_id))}\n"
                                  f"Önceki konuşma:\n{prior}\n\nKullanıcının mesajı: {user_input}")
                        with st.spinner("JARVIS düşünüyor..."):
                            answer = generate_text(prompt)
                except Exception as exc:
                    answer = f"Yanıt oluşturulamadı: {exc}"
                st.markdown(answer)
            messages.append({"role": "assistant", "content": answer})
            write_user_json(user_id, "chats", chats)

if __name__ == "__main__":
    main()
