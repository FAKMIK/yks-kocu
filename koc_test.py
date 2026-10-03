"""YKS Koçu - Streamlit uygulaması.

Kurulum: pip install streamlit google-generativeai requests beautifulsoup4
İsteğe bağlı görsel program çıktısı: pip install matplotlib pillow
API anahtarı: .streamlit/secrets.toml içine GEMINI_API_KEY = "..."
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import requests
import streamlit as st

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

try:
    import google.generativeai as genai
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

# CSS: Web sitesini tam genişlik yapacak şekilde güncellendi
st.markdown("""
<style>
:root { --ink:#172554; --brand:#334e8c; --soft:#f3f6fb; --line:#dbe3ef; }

/* Ekranın tüm genişliğini kullanmasını sağlayan CSS tanımları */
.main .block-container {
    max-width: 100% !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
    padding-top: 2rem !important;
}

.main { color:var(--ink); font-family:'Segoe UI',Roboto,sans-serif; }
h1,h2,h3 { color:var(--brand); font-weight:650; }
.stButton button,.stDownloadButton button { border-radius:10px; font-weight:600; transition:0.18s ease; }
.stButton button { background:var(--brand); color:white; border:0; }
.stButton button:hover { background:#253b70; color:white; transform:translateY(-1px); }
.stTextInput input,.stTextArea textarea { border-radius:9px; border-color:var(--line); }
[data-testid="stSidebar"] { background:#f7f9fc; }
[data-testid="stMetric"] { background:white; border:1px solid var(--line); border-radius:12px; padding:12px; }
.stTabs [data-baseweb="tab-list"] { gap:8px; }
.stTabs [data-baseweb="tab"] { border-radius:8px 8px 0 0; }
[data-testid="stChatMessage"] { border-radius:12px; }
@media(max-width:650px) { 
    .main .block-container { padding-left: 1rem !important; padding-right: 1rem !important; }
    .stTabs [data-baseweb="tab"] { padding:6px 9px; } 
}
</style>
""", unsafe_allow_html=True)

MEMORY_DIR = Path(__file__).resolve().parent / "yks_hafiza_kayitlari"
MAX_MEMORY_CHARS = 4000
MEMORY_DIR.mkdir(parents=True, exist_ok=True)


def configure_gemini() -> bool:
    """API anahtarını secrets veya ortam değişkeninden alıp Gemini'yi hazırlar."""
    if genai is None:
        st.error("Gemini paketi bulunamadı. `pip install google-generativeai` komutunu çalıştırın.")
        return False
    try:
        key = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
    except (FileNotFoundError, AttributeError):
        key = os.getenv("GEMINI_API_KEY")
    if not key:
        return False
    genai.configure(api_key=key)
    return True


def get_model():
    return genai.GenerativeModel("gemini-1.5-flash")


def get_memory_filepath(user_key: str) -> Path:
    digest = hashlib.sha256(user_key.strip().casefold().encode("utf-8")).hexdigest()[:20]
    return MEMORY_DIR / f"hafiza_{digest}.jsonl"


def load_memory(user_key: str) -> list[dict]:
    path = get_memory_filepath(user_key)
    records = []
    if not path.exists():
        return records
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    records.append(json.loads(line))
    except Exception as e:
        st.warning(f"Hafıza yüklenirken hata oluştu: {e}")
    return records


def save_memory_record(user_key: str, record: dict):
    path = get_memory_filepath(user_key)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def build_memory_context(user_key: str) -> str:
    records = load_memory(user_key)
    if not records:
        return ""
    context_str = "Kullanıcı Geçmişi ve Hafıza Kayıtları:\n"
    for rec in records:
        context_str += f"- [{rec.get('tarih', '')}] {rec.get('icerik', '')}\n"
    return context_str[:MAX_MEMORY_CHARS]


def web_search_duckduckgo(query: str, max_results: int = 3) -> list[dict]:
    """DuckDuckGo HTML üzerinden basit web araması yapmayı dener."""
    if BeautifulSoup is None:
        return []
    url = "https://html.duckduckgo.com/html/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        res = requests.post(url, data={"q": query}, headers=headers, timeout=8)
        soup = BeautifulSoup(res.text, "html.parser")
        results = []
        for a in soup.find_all("a", class_="result__url", limit=max_results):
            title_elem = a.find_parent("div", class_="result__body")
            if title_elem:
                title = title_elem.find("a", class_="result__a").text.strip()
                snippet = title_elem.find("a", class_="result__snippet").text.strip()
                results.append({"title": title, "snippet": snippet, "link": a["href"]})
        return results
    except Exception:
        return []


def generate_schedule_image(schedule_data: dict) -> io.BytesIO | None:
    """Haftalık çalışma programını matplotlib ile görselleştirir."""
    if plt is None:
        return None
    
    days = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.axis("off")
    
    table_data = []
    for day in days:
        tasks = schedule_data.get(day, ["Dinlenme / Serbest"])
        table_data.append([day, "\n".join(tasks)])
        
    table = ax.table(cellText=table_data, colLabels=["Gün", "Çalışma Planı"], loc="center", cellLoc="left")
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.2, 1.8)
    
    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    buf.seek(0)
    plt.close(fig)
    return buf


# --- Uygulama Arayüzü ---

st.sidebar.title("📚 YKS Koçu Paneli")
user_key = st.sidebar.text_input("Öğrenci Adı / ID:", value="öğrenci1")

tab1, tab2, tab3 = st.tabs(["💬 Yapay Zeka Koç", "📅 Ders Programı Hazırla", "📝 Notlarım & Hafıza"])

with tab1:
    st.header("YKS Koçunuz ile Sohbet Edin")
    st.caption("Netleriniz, çalışma stratejileriniz veya konu eksikleriniz hakkında soru sorun.")

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Merhaba! Ben YKS Rehber Koçunuz. Bugün hangi ders veya konu üzerinde çalışıyoruz?"}
        ]

    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).write(msg["content"])

    prompt = st.chat_input("Mesajınızı yazın...")

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").write(prompt)

        if configure_gemini():
            model = get_model()
            hafiza_ozeti = build_memory_context(user_key)

            search_context = ""
            if any(w in prompt.lower() for w in ["tarih", "baraj", "kılavuz", "ösym", "kaç gün", "müfredat"]):
                search_results = web_search_duckduckgo(f"YKS {prompt}")
                if search_results:
                    search_context = "\nWeb Arama Sonuçları:\n" + "\n".join([f"- {r['title']}: {r['snippet']}" for r in search_results])

            system_instruction = (
                "Sen uzman bir YKS (Yükseköğretim Kurumları Sınavı) rehberlik koçusun. "
                "Öğrenciye motive edici, sistemli ve net odaklı tavsiyeler ver. "
                f"\n\n{hafiza_ozeti}\n{search_context}"
            )

            with st.chat_message("assistant"):
                with st.spinner("Koçunuz yanıt hazırlıyor..."):
                    try:
                        response = model.generate_content(f"{system_instruction}\n\nÖğrenci: {prompt}")
                        answer = response.text
                        st.write(answer)
                        st.session_state.messages.append({"role": "assistant", "content": answer})

                        save_memory_record(user_key, {
                            "tarih": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "icerik": f"Soru: {prompt} | Yanıt Özet: {answer[:120]}..."
                        })
                    except Exception as err:
                        st.error(f"Bir hata oluştu: {err}")
        else:
            st.warning("Lütfen `.streamlit/secrets.toml` dosyasına veya ortam değişkenlerine `GEMINI_API_KEY` ekleyin.")

with tab2:
    st.header("Haftalık Çalışma Programı")
    st.write("Hedeflerinize göre otomatik çalışma programı oluşturun.")

    alani = st.selectbox("Alanınız:", ["Sayısal", "Eşit Ağırlık", "Sözel", "Dil"])
    gunluk_saat = st.slider("Günde Kaç Saat Çalışabilirsiniz?", 1, 12, 5)
    hedef = st.text_input("Öncelikli Hedef veya Eksik Konularınız:", "Matematik LTI, Fizik Dalgalar")

    if st.button("Program Oluştur"):
        if configure_gemini():
            model = get_model()
            prog_prompt = (
                f"Alan: {alani}, Günlük Çalışma Süresi: {gunluk_saat} saat. "
                f"Öncelikli konular: {hedef}. "
                "Lütfen Pazartesi'den Pazar'a kadar olan günleri içeren JSON formatında bir program üret. "
                "Format sadece şu şekilde olsun: {\"Pazartesi\": [\"...\"], \"Salı\": [\"...\"], ...}"
            )
            with st.spinner("Program hazırlanıyor..."):
                try:
                    res = model.generate_content(prog_prompt)
                    clean_json = re.search(r"\{.*\}", res.text, re.DOTALL)
                    if clean_json:
                        schedule_dict = json.loads(clean_json.group())
                        st.json(schedule_dict)

                        img_buf = generate_schedule_image(schedule_dict)
                        if img_buf:
                            st.image(img_buf, caption="Haftalık Program Görseliniz")
                            st.download_button("Program Görselini İndir (PNG)", data=img_buf, file_name="yks_program.png", mime="image/png")
                    else:
                        st.write(res.text)
                except Exception as e:
                    st.error(f"Program oluşturulurken hata: {e}")

with tab3:
    st.header("Öğrenci Hafızası & Geçmiş Notlar")
    records = load_memory(user_key)
    if records:
        for rec in reversed(records):
            st.info(f"**[{rec.get('tarih')}]**\n{rec.get('icerik')}")
    else:
        st.write("Henüz kaydedilmiş bir hafıza/not kaydı bulunmuyor.")
