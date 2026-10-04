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
import os
import re
import socket
import sqlite3
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
:root { --ink:#172554; --brand:#334e8c; --soft:#f3f6fb; --line:#dbe3ef; }
.main { color:var(--ink); font-family:'Segoe UI',Roboto,sans-serif; }
h1,h2,h3 { color:var(--brand); font-weight:650; }
.stButton button,.stDownloadButton button { border-radius:10px; font-weight:600; transition:.18s ease; }
.stButton button { background:var(--brand); color:white; border:0; }
.stButton button:hover { background:#253b70; color:white; transform:translateY(-1px); }
.stTextInput input,.stTextArea textarea { border-radius:9px; border-color:var(--line); }
[data-testid="stSidebar"] { background:#f7f9fc; }
[data-testid="stMetric"] { background:white; border:1px solid var(--line); border-radius:12px; padding:12px; }
.stTabs [data-baseweb="tab-list"] { gap:8px; }
.stTabs [data-baseweb="tab"] { border-radius:8px 8px 0 0; }
[data-testid="stChatMessage"] { border-radius:12px; }
@media(max-width:650px) { .stTabs [data-baseweb="tab"] { padding:6px 9px; } }
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
    if not re.fullmatch(r"[A-Za-z0-9_.-]{3,32}", username):
        return None, "Kullanıcı adı 3–32 karakter olmalı; İngilizce harf, rakam, nokta, tire veya alt çizgi kullanın."
    if len(password) < 10:
        return None, "Parola en az 10 karakter olmalı."
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


def main():
    st.title("📘 Kagan'in Yapay Zekâ YKS Koçu")
    st.caption("JARVIS · YKS koçu · çalışma takipçisi")
    if "user_id" not in st.session_state:
        st.session_state.user_id = None

    if st.session_state.user_id is None:
        login_tab, register_tab = st.tabs(["Giriş", "Hesap oluştur"])
        with login_tab:
            with st.form("login_form"):
                username = st.text_input("Kullanıcı adı")
                password = st.text_input("Parola", type="password")
                login = st.form_submit_button("Giriş yap", use_container_width=True)
            if login:
                user_id = authenticate(username, password)
                if user_id is None:
                    st.error("Kullanıcı adı veya parola hatalı.")
                else:
                    st.session_state.user_id = user_id
                    st.session_state.username = username.strip()
                    st.rerun()
        with register_tab:
            with st.form("register_form"):
                new_username = st.text_input("Kullanıcı adı", key="register_username")
                new_password = st.text_input("Parola (en az 10 karakter)", type="password", key="register_password")
                confirm_password = st.text_input("Parolayı tekrar yazın", type="password")
                register = st.form_submit_button("Hesap oluştur", use_container_width=True)
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
        st.caption("Hesap parolaları SQLite veritabanında PBKDF2 ile özetlenerek saklanır.")
        st.stop()

    user_id = st.session_state.user_id
    api_ready = configure_gemini()
    with st.sidebar:
        st.header(f"👤 {st.session_state.get('username', 'Kullanıcı')}")
        st.button("Çıkış yap", use_container_width=True, on_click=logout_user)
        st.download_button("⬇️ Hesap verilerimi yedekle", data=account_backup(user_id),
                           file_name=f"yks_kocu_yedek_{st.session_state.get('username', 'hesap')}.json",
                           mime="application/json", use_container_width=True)
        st.divider()
        st.header("🧠 Durum")
        st.success("Gemini API hazır") if api_ready else st.error("GEMINI_API_KEY bulunamadı")

    if not api_ready:
        st.warning("Gemini API hazır değil. Kayıtlı veriler, notlar ve hesap makinesi kullanılabilir; AI özellikleri API anahtarı gerektirir.")

    records = load_memory(user_id)
    with st.sidebar:
        st.metric("📂 Hafıza kaydı", len(records))
        if records:
            with st.expander("Son kayıtlar"):
                for item in records[-6:]:
                    st.write(f"• {item.get('type')} — {item.get('title')}")

    q_tab, p_tab, progress_tab, r_tab, m_tab, j_tab = st.tabs(
        ["📝 Soru Analizi", "📅 Program", "📈 İlerleme", "🔗 Kaynak", "🗂️ Hafıza", "🤖 JARVIS Araçları"]
    )
    with q_tab:
        st.subheader("Hatalı soru fotoğrafı")
        uploaded = st.file_uploader("Sorunun fotoğrafını yükleyin", type=["png", "jpg", "jpeg"], key="question_image")
        if uploaded:
            st.image(uploaded, caption="Yüklenen soru", use_container_width=True)
        if st.button("🔍 Soruyu analiz et ve hafızaya al", use_container_width=True):
            if not uploaded:
                st.warning("Önce bir soru fotoğrafı yükleyin.")
            else:
                try:
                    with st.spinner("Sorunuz inceleniyor..."):
                        analysis = analyze_image(uploaded)
                    st.session_state.last_analysis = analysis
                    save_memory(user_id, "soru_analizi", analysis, uploaded.name)
                except Exception as exc:
                    st.error(f"Soru analiz edilemedi: {exc}")
        if st.session_state.get("last_analysis"):
            st.markdown(st.session_state.last_analysis)

    with p_tab:
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
                        prompt = ("Öğrencinin durumu:\n" + status + "\n\nHafıza:\n" + memory_to_text(records) +
                                  "\n\nUygulanabilir 7 günlük YKS çalışma programı hazırla. Her gün ders, süre, konu ve ölçülebilir mini hedef olsun. "
                                  "Dengeli mola ve tekrar zamanları ekle; gerçekçi olmayan yoğunluk önermem.")
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

    with progress_tab:
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
        if tasks:
            completed = sum(bool(task.get("done")) for task in tasks)
            st.progress(completed / max(1, len(tasks)), text=f"Tamamlanan görevler: {completed}/{len(tasks)}")
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
                frame = pd.DataFrame(results).sort_values("date")
                st.line_chart(frame.set_index("date")[["Türkçe", "Matematik", "Sosyal", "Fen", "Toplam"]])
                st.dataframe(frame.iloc[::-1], use_container_width=True, hide_index=True)
                if st.button("Deneme kayıtlarını temizle", key="clear_exam_results"):
                    write_user_json(user_id, "exam_results", [])
                    st.rerun()
            except ImportError:
                st.dataframe(results, use_container_width=True)

    with r_tab:
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

    with m_tab:
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

    with j_tab:
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
        st.write("Matematik: Rehber Matematik / Mert Hoca · Fizik: VIP Fizik · Kimya: Görkem Şahin · "
                 "Biyoloji: Dr. Biyoloji · Türkçe: Rüştü Hoca · Tarih: Benim Hocam · Coğrafya: Coğrafyanın Kodları")

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
                    answer = "Matematik: Rehber Matematik / Mert Hoca; Fizik: VIP Fizik; Kimya: Görkem Şahin; " \
                             "Biyoloji: Dr. Biyoloji; Türkçe: Rüştü Hoca; Tarih: Benim Hocam; Coğrafya: Coğrafyanın Kodları."
                else:
                    facts = read_user_json(user_id, "facts", [])
                    if re.search(r"benim adım|hedefim|favorim|seviyorum", normalized):
                        facts.append(user_input)
                        write_user_json(user_id, "facts", facts[-30:])
                    prior = "\n".join(f"{m['role']}: {m['content']}" for m in messages[-9:-1])
                    prompt = ("Sen JARVIS adlı, YKS öğrencisine kısa, somut ve motive edici öneriler veren kişisel koçsun. "
                              "Kullanıcıya samimi ve net Türkçe ile, gerekirse 'efendim' diye hitap et. "
                              "Belirsiz bilgiyi kesinmiş gibi sunma; uygulanabilir öneriler ver. "
                              "Ders rehberleri: Matematik Rehber Matematik/Mert Hoca, Fizik VIP Fizik, Kimya Görkem Şahin, "
                              "Biyoloji Dr. Biyoloji, Türkçe Rüştü Hoca, Tarih Benim Hocam, Coğrafya Coğrafyanın Kodları.\n"
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
