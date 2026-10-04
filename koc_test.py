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
st.set_page_config(page_title="YKS Koçu", page_icon="📚", layout="wide")

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


def render_dashboard(user_id: int, username: str) -> None:
    tasks = read_user_json(user_id, "study_tasks", [])
    focus_logs = read_user_json(user_id, "study_sessions", [])
    exam_results = read_user_json(user_id, "exam_results", [])
    records = load_memory(user_id)
    today = date.today()
    today_name = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"][today.weekday()]
    safe_name = html.escape(username, quote=True)
    today_minutes = sum(int(item.get("minutes", 0)) for item in focus_logs if item.get("date") == today.isoformat())
    today_focus_label = f"{today_minutes // 60} sa {today_minutes % 60:02d} dk" if today_minutes >= 60 else f"{today_minutes} dk"
    task_count = len(tasks)
    done_count = sum(bool(item.get("done")) for item in tasks)
    completion = round(100 * done_count / task_count) if task_count else 0
    latest_exam = max(exam_results, key=lambda item: item.get("date", ""), default=None)
    latest_net = f"{latest_exam.get('Toplam', 0):g}" if latest_exam else "—"
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
    review_items = read_user_json(user_id, "wrong_questions", [])
    review_due = sum(not item.get("mastered") and item.get("next_review", "") <= today.isoformat() for item in review_items)
    unfinished_today = [item for item in tasks if item.get("date") == today.isoformat() and not item.get("done")]
    if review_due:
        insight = f"Tekrar zamanı gelen {review_due} yanlış sorunu çözerek bilgini pekiştir."
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
        <div class="hero-eyebrow">JARVIS · KİŞİSEL YKS STÜDYOSU</div>
        <h1>Selam {safe_name}.<br>Bugün hedeflerine bir adım daha.</h1>
        <p>Planını sade tut, ilerlemeni gör ve sıradaki doğru işe odaklan. Küçük ama düzenli adımlar büyük fark yaratır.</p>
        <span class="hero-pill">✦ &nbsp; {today_name}, {today:%d.%m.%Y} &nbsp;·&nbsp; Bugünün çalışma alanı</span>
      </div>
      <svg class="hero-art" viewBox="0 0 300 220" role="img" aria-label="Çalışma hedefi ve ilerleme çizimi">
        <defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#8ef0d0"/><stop offset="1" stop-color="#ffce73"/></linearGradient></defs>
        <circle cx="167" cy="108" r="86" fill="#ffffff0d" stroke="#ffffff25"/>
        <circle cx="167" cy="108" r="66" fill="#ffffff0a" stroke="#ffffff20"/>
        <rect x="105" y="56" width="120" height="108" rx="18" fill="#f7f9ff"/>
        <path d="M128 84h65M128 99h45" stroke="#cbd5e7" stroke-width="7" stroke-linecap="round"/>
        <path d="M128 127l16 14 34-37" fill="none" stroke="url(#g)" stroke-width="9" stroke-linecap="round" stroke-linejoin="round"/>
        <circle cx="229" cy="54" r="14" fill="#ffce73"/><path d="M229 46v16M221 54h16" stroke="#20365d" stroke-width="3" stroke-linecap="round"/>
        <circle cx="90" cy="160" r="8" fill="#79e0bd"/><circle cx="243" cy="148" r="6" fill="#b8c7ff"/>
      </svg>
    </section>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-kicker">Bugün ve bu hafta</div>', unsafe_allow_html=True)
    st.markdown(f"<div class='soft-card' style='margin-bottom:1rem;border-left:4px solid #e16a48'><span class='section-kicker'>JARVIS İÇGÖRÜSÜ</span><p style='margin-top:.4rem'>{html.escape(insight)}</p></div>", unsafe_allow_html=True)
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Bugünkü odak", today_focus_label, help="Kaydettiğin çalışma oturumlarının toplamı")
    k2.metric("Plan ilerlemesi", f"%{completion}", help=f"{done_count}/{task_count} görev tamamlandı")
    k3.metric("Son deneme neti", latest_net, help=latest_exam.get("name", "Deneme") if latest_exam else "Henüz deneme sonucu eklenmedi")
    k4.metric("Kaynak arşivin", str(resource_count), help="PDF ve bağlantı kaynakları")
    streak_col, badge_col = st.columns([1, 3])
    streak_col.metric("🔥 Çalışma serisi", f"{study_streak} gün")
    badge_col.markdown(f"<div class='soft-card' style='padding:.85rem 1rem'><span class='section-kicker'>GELİŞİM ROZETİ</span><p style='margin-top:.3rem'>🏅 {streak_badge} · Her gün kısa bir oturum bile serini sürdürür.</p></div>", unsafe_allow_html=True)

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
                st.markdown(f"<div class='soft-card' style='margin-bottom:9px;padding:12px 15px'><b style='color:{'#1f9b75' if item.get('done') else '#3858d6'}'>{state}</b> &nbsp; {html.escape(label)}</div>", unsafe_allow_html=True)
                if not item.get("done"):
                    task_actions = st.columns(2)
                    if task_actions[0].button("✓ Tamamlandı", key=f"dash_done_{item.get('id', task_index)}", use_container_width=True):
                        item["done"] = True
                        write_user_json(user_id, "study_tasks", tasks)
                        st.rerun()
                    if task_actions[1].button("Yarına taşı", key=f"dash_defer_{item.get('id', task_index)}", use_container_width=True):
                        item["date"] = (today + timedelta(days=1)).isoformat()
                        write_user_json(user_id, "study_tasks", tasks)
                        st.rerun()
        else:
            st.markdown("<div class='empty-state'>Bugün için planlanmış görev yok. Programını ekleyip görev listesine dönüştürebilirsin.</div>", unsafe_allow_html=True)
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
        state.focus_timer_deadline = None
        state.focus_timer_paused = False
        state.focus_timer_done = True
        st.rerun()


def render_login() -> None:
    theme_picker_columns = st.columns([1, 1, 1])
    theme_mode = theme_picker_columns[1].selectbox("Tema", ["Açık", "Koyu"], key="theme_mode", label_visibility="collapsed")
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
    st.markdown('<div class="auth-brand"><span>J</span> JARVIS · YKS STUDIO</div>', unsafe_allow_html=True)
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
        st.markdown('<div class="side-brand"><span class="side-mark">J</span><span>JARVIS <small style="display:block;color:#91a3bf;font-weight:500;letter-spacing:.12em">YKS STUDIO</small></span></div>', unsafe_allow_html=True)
        st.header(f"👤 {st.session_state.get('username', 'Kullanıcı')}")
        st.button("Çıkış yap", use_container_width=True, on_click=logout_user)
        st.download_button("⬇️ Hesap verilerimi yedekle", data=account_backup(user_id),
                           file_name=f"yks_kocu_yedek_{st.session_state.get('username', 'hesap')}.json",
                           mime="application/json", use_container_width=True)
        theme_mode = st.selectbox("🎨 Tema", ["Açık", "Koyu"], key="theme_mode")
        st.divider()

    if theme_mode == "Koyu":
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
    st.markdown("""<style>
    [data-testid="stAppViewContainer"] .main { position:relative; }
    [data-testid="stMainBlockContainer"] { position:relative; }
    .hero-art { filter:drop-shadow(0 0 18px #ffb74942); }
    [data-testid="stAppViewContainer"]::before { content:"";position:fixed;z-index:0;pointer-events:none;right:-105px;top:115px;width:240px;height:240px;border-radius:50%;opacity:.16;background:radial-gradient(circle,#fff7dc 0 5%,#ffc45b 6% 9%,#e34636 10% 13%,transparent 14% 28%,#e3463655 29% 30%,transparent 31%);box-shadow:0 0 60px #f15b3340; }
    @media(max-width:760px) { [data-testid="stAppViewContainer"]::before { width:130px;height:130px;right:-65px;top:80px;opacity:.11; } }
    </style>""", unsafe_allow_html=True)
    st.title("YKS ÇALIŞMA STÜDYOSU")
    st.caption("Kişisel çalışma alanın · planla, uygula, ilerle")

    if not api_ready:
        st.warning("Gemini API hazır değil. Kayıtlı veriler, notlar ve hesap makinesi kullanılabilir; AI özellikleri API anahtarı gerektirir.")

    records = load_memory(user_id)
    with st.sidebar:
        st.markdown("<div class='side-nav-label'>ÇALIŞMA ALANI</div>", unsafe_allow_html=True)
        active_view = st.radio("Bölümler", ["⌂ Genel Bakış", "📝 Soru Analizi", "📅 Program", "📈 İlerleme",
                                             "🎯 Odak Modu", "🎬 TYT Video Kampları", "🔗 Kaynak Arşivi", "🗂️ Hafıza", "🤖 JARVIS Araçları", "💬 Koçla Sohbet"],
                               label_visibility="collapsed", key="active_view")
        st.divider()
        st.markdown("<div class='side-nav-label'>DURUM</div>", unsafe_allow_html=True)
        st.success("Gemini API hazır") if api_ready else st.error("GEMINI_API_KEY bulunamadı")
        st.metric("📂 Hafıza kaydı", len(records))
        if records:
            with st.expander("Son kayıtlar"):
                for item in records[-6:]:
                    st.write(f"• {item.get('type', 'kayıt')} — {item.get('title', 'Başlıksız kayıt')}")

    if active_view == "⌂ Genel Bakış":
        render_dashboard(user_id, st.session_state.get("username", "Öğrenci"))
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
                                     "review_count": 0, "mastered": False, "analysis": analysis})
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
                st.caption(f"Hata türü: {mistake.get('error_kind', 'Belirtilmedi')} · Tekrar: {mistake.get('review_count', 0)}")
                with st.expander("Çözüm analizini aç"):
                    st.markdown(mistake.get("analysis", ""))
                review_actions = st.columns(2)
                if review_actions[0].button("Tekrar ettim", key=f"review_done_{mistake['id']}", use_container_width=True):
                    intervals = [1, 3, 7, 14, 30]
                    mistake["review_count"] = int(mistake.get("review_count", 0)) + 1
                    interval = intervals[min(mistake["review_count"] - 1, len(intervals) - 1)]
                    mistake["next_review"] = (date.today() + timedelta(days=interval)).isoformat()
                    write_user_json(user_id, "wrong_questions", mistakes)
                    st.rerun()
                if review_actions[1].button("Artık biliyorum", key=f"review_mastered_{mistake['id']}", use_container_width=True):
                    mistake["mastered"] = True
                    write_user_json(user_id, "wrong_questions", mistakes)
                    st.rerun()

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

    if active_view == "📈 İlerleme":
        st.subheader("Çalışma ve deneme takibi")
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
            results.append({"date": exam_date.isoformat(), "name": exam_label.strip() or "Deneme",
                            "Türkçe": net_turkish, "Matematik": net_math, "Sosyal": net_social, "Fen": net_science,
                            "Toplam": net_turkish + net_math + net_social + net_science})
            write_user_json(user_id, "exam_results", results)
            st.success("Deneme sonucu kaydedildi.")
            st.rerun()
        results = read_user_json(user_id, "exam_results", [])
        if results:
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
