"""YKS Koçu - Streamlit Uygulaması

Kurulum: pip install streamlit google-generativeai requests beautifulsoup4 matplotlib pillow
API Anahtarı: .streamlit/secrets.toml içine GEMINI_API_KEY = "..."
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
from datetime import datetime, date
from pathlib import Path

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


# Sayfa Yapılandırması
st.set_page_config(
    page_title="YKS Koçu Pro",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Koyu/Açık Tema Uyumlu & Modern CSS
st.markdown("""
<style>
/* Tam Genişlik Düzenlemesi */
.main .block-container {
    max-width: 100% !important;
    padding: 1.5rem 2.5rem !important;
}

/* Şeffaf ve Modern Kart Yapısı (Tema ile Uyumlu) */
div[data-testid="stMetric"] {
    background-color: rgba(255, 255, 255, 0.05) !important;
    border: 1px solid rgba(128, 128, 128, 0.2) !important;
    border-radius: 12px !important;
    padding: 16px !important;
    backdrop-filter: blur(10px);
}

/* Metrik Metinlerinin Temaya Göre Belirginleşmesi */
div[data-testid="stMetricLabel"] p {
    font-weight: 600 !important;
    opacity: 0.9 !important;
}

div[data-testid="stMetricValue"] div {
    font-size: 1.8rem !important;
    font-weight: 700 !important;
}

/* Buton Tasarımı */
.stButton button, .stDownloadButton button {
    border-radius: 8px !important;
    font-weight: 600 !important;
    background: #2563eb !important;
    color: white !important;
    border: none !important;
    padding: 0.5rem 1.25rem !important;
    transition: background 0.2s ease !important;
}

.stButton button:hover {
    background: #1d4ed8 !important;
}

/* Tab Tasarımı */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    border-bottom: 2px solid rgba(128, 128, 128, 0.2);
}

.stTabs [data-baseweb="tab"] {
    border-radius: 8px 8px 0 0;
    font-weight: 600;
    padding: 10px 16px;
}

/* Chat Mesaj Kutuları */
[data-testid="stChatMessage"] {
    border-radius: 12px;
    border: 1px solid rgba(128, 128, 128, 0.15);
    margin-bottom: 10px;
}
</style>
""", unsafe_allow_html=True)

MEMORY_DIR = Path(__file__).resolve().parent / "yks_hafiza_kayitlari"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)
MAX_MEMORY_CHARS = 4000


# Helper Fonksiyonlar
def configure_gemini() -> bool:
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
    if plt is None:
        return None
    days = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.axis("off")
    table_data = [[day, "\n".join(schedule_data.get(day, ["Dinlenme"]))] for day in days]
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


# --- YAN MENÜ (SIDEBAR) ---
st.sidebar.title("🎓 YKS Koçu Pro")
user_key = st.sidebar.text_input("Öğrenci Adı / ID:", value="öğrenci1")

# YKS Geri Sayım Widget'ı
st.sidebar.markdown("---")
st.sidebar.subheader("⏳ YKS Geri Sayım")
yks_date = date(2027, 6, 20)
kalan_gun = (yks_date - date.today()).days
if kalan_gun > 0:
    st.sidebar.metric("YKS 2027'ye Kalan Gün", f"{kalan_gun} Gün")
else:
    st.sidebar.success("Sınav günü geldi! Başarılar!")

st.sidebar.markdown("---")
st.sidebar.info("💡 **İpucu:** Yapay zeka koçunuzdan günlük soru çözümü ve konu anlatımı stratejisi isteyebilirsiniz.")


# --- ANA SAYFA METRİKLERİ ---
col_m1, col_m2, col_m3 = st.columns(3)
col_m1.metric("📌 Aktif Öğrenci", user_key.capitalize())
col_m2.metric("💬 Sohbet Geçmişi", f"{len(st.session_state.get('messages', []))} Mesaj")
col_m3.metric("🎯 Hedef", "YKS Derece")

st.markdown("---")

# Tab Yapısı
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "💬 Yapay Zeka Koç", 
    "📅 Çalışma Programı", 
    "📊 Net Takip Grafiği", 
    "⏱️ Pomodoro Zamanlayıcı",
    "✅ Konu Takip Listesi"
])


# --- TAB 1: YAPAY ZEKA KOÇ ---
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
                "Sen uzman bir YKS rehberlik koçusun. "
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
            st.warning("Lütfen `.streamlit/secrets.toml` dosyasına `GEMINI_API_KEY` ekleyin.")


# --- TAB 2: ÇALIŞMA PROGRAMI ---
with tab2:
    st.header("Haftalık Çalışma Programı Hazırlayıcı")
    c1, c2 = st.columns(2)
    with c1:
        alani = st.selectbox("Alanınız:", ["Sayısal", "Eşit Ağırlık", "Sözel", "Dil"])
        gunluk_saat = st.slider("Günde Kaç Saat Çalışabilirsiniz?", 1, 12, 5)
    with c2:
        hedef = st.text_input("Öncelikli Hedef / Eksik Konular:", "Matematik LTI, Fizik Dalgalar")

    if st.button("Program Oluştur ✨"):
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
                            st.image(img_buf, caption="Haftalık Görsel Programınız")
                            st.download_button("Programı İndir (PNG)", data=img_buf, file_name="yks_program.png", mime="image/png")
                    else:
                        st.write(res.text)
                except Exception as e:
                    st.error(f"Hata oluştu: {e}")


# --- TAB 3: NET TAKİP GRAFİĞİ ---
with tab3:
    st.header("📈 Deneme Net Takibi")
    
    if "net_data" not in st.session_state:
        st.session_state.net_data = [{"Deneme": "Deneme 1", "TYT": 65, "AYT": 35}]

    with st.form("net_form"):
        f_col1, f_col2, f_col3 = st.columns(3)
        d_name = f_col1.text_input("Deneme Adı/Tarih", value=f"Deneme {len(st.session_state.net_data)+1}")
        tyt_net = f_col2.number_input("TYT Neti", 0.0, 120.0, 70.0)
        ayt_net = f_col3.number_input("AYT Neti", 0.0, 80.0, 40.0)
        submit_net = st.form_submit_button("Neti Kaydet")

        if submit_net:
            st.session_state.net_data.append({"Deneme": d_name, "TYT": tyt_net, "AYT": ayt_net})
            st.success("Netiniz kaydedildi!")

    if plt and st.session_state.net_data:
        denemeler = [d["Deneme"] for d in st.session_state.net_data]
        tyt_list = [d["TYT"] for d in st.session_state.net_data]
        ayt_list = [d["AYT"] for d in st.session_state.net_data]

        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(denemeler, tyt_list, marker='o', label='TYT Net', color='#2563eb', linewidth=2)
        ax.plot(denemeler, ayt_list, marker='s', label='AYT Net', color='#dc2626', linewidth=2)
        ax.set_ylabel("Net Sayısı")
        ax.set_title("Net Gelişim Grafiği")
        ax.legend()
        ax.grid(True, linestyle='--', alpha=0.5)
        st.pyplot(fig)


# --- TAB 4: POMODORO ZAMANLAYICI ---
with tab4:
    st.header("⏱️ Pomodoro Odaklanma Sayacı")
    p_col1, p_col2 = st.columns([1, 2])
    with p_col1:
        sure = st.number_input("Çalışma Süresi (Dakika):", value=25, min_value=1, max_value=60)
        if st.button("Sayacı Başlat"):
            st.info(f"{sure} dakikalık odaklanma süresi başladı! Dersinize odaklanın.")
    with p_col2:
        st.markdown("""
        **Pomodoro Tekniği Nasıl Uygulanır?**
        1. 25 dakika kesintisiz derse odaklanın.
        2. 5 dakika kısa mola verin.
        3. 4 periyot tamamladıktan sonra 20-30 dakikalık uzun mola verin.
        """)


# --- TAB 5: KONU TAKİP LİSTESİ ---
with tab5:
    st.header("✅ YKS Temel Konu Takibi")
    k_col1, k_col2 = st.columns(2)
    
    with k_col1:
        st.subheader("TYT Matematik")
        st.checkbox("Temel Kavramlar & Sayılar", value=True)
        st.checkbox("Rasyonel Sayılar")
        st.checkbox("Denklemler ve Eşitsizlikler")
        st.checkbox("Problemler")
        st.checkbox("Fonksiyonlar")

    with k_col2:
        st.subheader("TYT Türkçe")
        st.checkbox("Sözcükte ve Cümlede Anlam", value=True)
        st.checkbox("Paragraf Yapısı ve Yorumu")
        st.checkbox("Yazım Kuralları & Noktalama")
        st.checkbox("Dil Bilgisi (Dilbilgisi Karma)")
