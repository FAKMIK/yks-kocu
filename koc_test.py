"""YKS Koçu Pro - Kapsamlı YKS Hazırlık & Yapay Zeka Platformu

Kurulum: pip install streamlit google-generativeai requests beautifulsoup4 matplotlib pillow
API Anahtarı: .streamlit/secrets.toml içinde GEMINI_API_KEY = "..."
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


# --- Sayfa Yapılandırması ---
st.set_page_config(
    page_title="YKS Koçu Pro | Dijital Hazırlık Platformu",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Temaya Uyarlamalı Özel CSS ---
st.markdown("""
<style>
.main .block-container {
    max-width: 100% !important;
    padding: 1.5rem 2rem !important;
}

/* Şeffaf ve Temaya Duyarlı Kartlar */
div[data-testid="stMetric"] {
    background-color: rgba(255, 255, 255, 0.04) !important;
    border: 1px solid rgba(128, 128, 128, 0.2) !important;
    border-radius: 12px !important;
    padding: 14px !important;
    backdrop-filter: blur(10px);
}

div[data-testid="stMetricLabel"] p {
    font-weight: 600 !important;
    opacity: 0.9 !important;
}

div[data-testid="stMetricValue"] div {
    font-size: 1.7rem !important;
    font-weight: 700 !important;
}

/* Modern Butonlar */
.stButton button, .stDownloadButton button {
    border-radius: 8px !important;
    font-weight: 600 !important;
    background: linear-gradient(135deg, #2563eb, #1d4ed8) !important;
    color: white !important;
    border: none !important;
    padding: 0.5rem 1.2rem !important;
    transition: transform 0.2s ease, box-shadow 0.2s ease !important;
}

.stButton button:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
}

/* Tab Yapısı */
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


# --- Yardımcı Fonksiyonlar ---
def configure_gemini() -> bool:
    if genai is None:
        st.error("Gemini paketi yüklü değil. `pip install google-generativeai` komutunu çalıştırın.")
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
        st.warning(f"Hafıza yükleme hatası: {e}")
    return records


def save_memory_record(user_key: str, record: dict):
    path = get_memory_filepath(user_key)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def build_memory_context(user_key: str) -> str:
    records = load_memory(user_key)
    if not records:
        return ""
    context_str = "Kullanıcı Hafızası:\n"
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
    table_data = [[day, "\n".join(schedule_data.get(day, ["Serbest Çalışma / Mola"]))] for day in days]
    table = ax.table(cellText=table_data, colLabels=["Gün", "Çalışma Programı"], loc="center", cellLoc="left")
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
    st.sidebar.success("Sınav Günü Geldi! Başarılar!")

# Günlük Soru Sayacı Widget'ı
st.sidebar.markdown("---")
st.sidebar.subheader("📝 Günlük Soru Sayacı")
if "toplam_soru" not in st.session_state:
    st.session_state.toplam_soru = 0

eklenen_soru = st.sidebar.number_input("Çözülen Soru Ekleyin:", min_value=0, step=10, value=0)
if st.sidebar.button("Sayıyı Ekle"):
    st.session_state.toplam_soru += eklenen_soru
    st.sidebar.success(f"Toplam: {st.session_state.toplam_soru} soru kaydedildi!")

st.sidebar.metric("Bugün Çözülen Toplam Soru", f"{st.session_state.toplam_soru} Soru")

st.sidebar.markdown("---")
st.sidebar.info("💡 **İpucu:** Yapamadığınız soruların fotoğrafını 'Soru Çözücü' sekmesinden yükleyebilirsiniz.")


# --- ANA SAYFA ÜST METRİKLER ---
col_m1, col_m2, col_m3, col_m4 = st.columns(4)
col_m1.metric("📌 Öğrenci Profil", user_key.capitalize())
col_m2.metric("💬 Koçluk Mesajları", f"{len(st.session_state.get('messages', []))} Mesaj")
col_m3.metric("✏️ Çözülen Soru", f"{st.session_state.toplam_soru} Soru")
col_m4.metric("🎯 Hedef Derece", "Top 10K")

st.markdown("---")

# --- ANA TAB YAPISI (7 KAPSAMLI MODÜL) ---
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "💬 Yapay Zeka Koç", 
    "📸 Görsel Soru Çözücü",
    "📅 Çalışma Programı", 
    "🧮 YKS Puan Hesapla",
    "📊 Net Takip Grafiği", 
    "⏱️ Pomodoro Zamanlayıcı",
    "✅ Konu Takip Listesi"
])


# --- TAB 1: YAPAY ZEKA KOÇ ---
with tab1:
    st.header("YKS Koçunuz ile Sohbet Edin")
    st.caption("Eksik konularınız, ders calışma taktikleri ve motivasyon için sorularınızı sorun.")

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Merhaba! Ben YKS Rehber Koçunuz. Bugün hangi ders veya konu üzerinde strateji belirlemek istersin?"}
        ]

    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).write(msg["content"])

    prompt = st.chat_input("Mesajınızı veya sorunuzu yazın...")

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
                "Sen uzman bir YKS rehberlik koçusun. Öğrenciye motive edici, sistemli, net odaklı ve pedagojik tavsiyeler ver. "
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


# --- TAB 2: GÖRSEL SORU ÇÖZÜCÜ ---
with tab2:
    st.header("📸 Yapay Zeka ile Yapamadığın Soruyu Çözdür")
    st.write("Yapamadığınız matematik, fizik, kimya veya herhangi bir YKS sorusunun fotoğrafını yükleyin.")

    uploaded_file = st.file_uploader("Soru Görseli Yükleyin (JPG, PNG)", type=["jpg", "jpeg", "png"])
    user_question = st.text_input("Sorunuzla ilgili eklemek istediğiniz bir not var mı?", "Bu sorunun adım adım çözümünü ve cevabını açıklar mısın?")

    if uploaded_file and st.button("Soruyu Analiz Et & Çöz ✨"):
        if configure_gemini() and Image is not None:
            try:
                img = Image.open(uploaded_file)
                st.image(img, caption="Yüklenen Soru", width=400)

                model = get_model()
                with st.spinner("Soru inceleniyor ve çözüm adımları hazırlanıyor..."):
                    response = model.generate_content([user_question, img])
                    st.markdown("### 📝 Çözüm ve Açıklama:")
                    st.write(response.text)
            except Exception as e:
                st.error(f"Görsel işlenirken bir hata oluştu: {e}")
        elif Image is None:
            st.error("Görsel işleme kütüphanesi (Pillow) eksik. Lütfen `pip install pillow` kurun.")


# --- TAB 3: ÇALIŞMA PROGRAMI ---
with tab3:
    st.header("📅 Haftalık Çalışma Programı Oluşturucu")
    c1, c2 = st.columns(2)
    with c1:
        alani = st.selectbox("Alanınız:", ["Sayısal", "Eşit Ağırlık", "Sözel", "Dil"])
        gunluk_saat = st.slider("Günde Kaç Saat Çalışabilirsiniz?", 1, 12, 5)
    with c2:
        hedef = st.text_input("Öncelikli Hedef / Eksik Konular:", "Matematik LTI, Fizik Dalgalar, Paragraf")

    if st.button("Program Oluştur ✨"):
        if configure_gemini():
            model = get_model()
            prog_prompt = (
                f"Alan: {alani}, Günlük Çalışma Süresi: {gunluk_saat} saat. "
                f"Öncelikli konular: {hedef}. "
                "Pazartesi'den Pazar'a kadar olan günleri içeren JSON formatında bir program üret. "
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
                            st.download_button("Programı Görsel Olarak İndir (PNG)", data=img_buf, file_name="yks_program.png", mime="image/png")
                    else:
                        st.write(res.text)
                except Exception as e:
                    st.error(f"Hata oluştu: {e}")


# --- TAB 4: YKS PUAN HESAPLAYICI ---
with tab4:
    st.header("🧮 YKS Tahmini Puan Hesaplama")
    st.caption("Netlerinizi girerek yaklaşık ÖSYM puan türlerinizi hesaplayın.")

    st.subheader("1. TYT Netleri")
    col_t1, col_t2, col_t3, col_t4 = st.columns(4)
    tyt_mat_d = col_t1.number_input("TYT Mat Doğru", 0, 40, 25)
    tyt_mat_y = col_t1.number_input("TYT Mat Yanlış", 0, 40, 3)
    
    tyt_tr_d = col_t2.number_input("TYT Türkçe Doğru", 0, 40, 30)
    tyt_tr_y = col_t2.number_input("TYT Türkçe Yanlış", 0, 40, 5)

    tyt_fen_d = col_t3.number_input("TYT Fen Doğru", 0, 20, 12)
    tyt_fen_y = col_t3.number_input("TYT Fen Yanlış", 0, 20, 4)

    tyt_sos_d = col_t4.number_input("TYT Sosyal Doğru", 0, 20, 14)
    tyt_sos_y = col_t4.number_input("TYT Sosyal Yanlış", 0, 20, 3)

    tyt_net = (tyt_mat_d - tyt_mat_y*0.25) + (tyt_tr_d - tyt_tr_y*0.25) + (tyt_fen_d - tyt_fen_y*0.25) + (tyt_sos_d - tyt_sos_y*0.25)
    
    st.markdown("---")
    st.subheader("2. AYT Netleri")
    col_a1, col_a2, col_a3, col_a4 = st.columns(4)
    ayt_mat_d = col_a1.number_input("AYT Mat Doğru", 0, 40, 20)
    ayt_mat_y = col_a1.number_input("AYT Mat Yanlış", 0, 40, 4)

    ayt_fiz_d = col_a2.number_input("AYT Fizik Doğru", 0, 14, 8)
    ayt_fiz_y = col_a2.number_input("AYT Fizik Yanlış", 0, 14, 2)

    ayt_kim_d = col_a3.number_input("AYT Kimya Doğru", 0, 13, 7)
    ayt_kim_y = col_a3.number_input("AYT Kimya Yanlış", 0, 13, 2)

    ayt_biy_d = col_a4.number_input("AYT Biyoloji Doğru", 0, 13, 8)
    ayt_biy_y = col_a4.number_input("AYT Biyoloji Yanlış", 0, 13, 2)

    ayt_say_net = (ayt_mat_d - ayt_mat_y*0.25) + (ayt_fiz_d - ayt_fiz_y*0.25) + (ayt_kim_d - ayt_kim_y*0.25) + (ayt_biy_d - ayt_biy_y*0.25)

    # Tahmini Puan Hesaplama Formülü
    tyt_puan = 100 + (tyt_net * 3.3)
    say_puan = 100 + (tyt_net * 1.3) + (ayt_say_net * 3.0)

    st.markdown("---")
    res_col1, res_col2, res_col3 = st.columns(3)
    res_col1.metric("Toplam TYT Netiniz", f"{tyt_net:.2f} Net")
    res_col2.metric("Tahmini TYT Puanı", f"{tyt_puan:.1f}")
    res_col3.metric("Tahmini Sayısal Puanı", f"{say_puan:.1f}")


# --- TAB 5: NET TAKİP GRAFİĞİ ---
with tab5:
    st.header("📈 Deneme Net Takip Grafiği")
    
    if "net_data" not in st.session_state:
        st.session_state.net_data = [{"Deneme": "Deneme 1", "TYT": 65, "AYT": 35}]

    with st.form("net_form"):
        f_col1, f_col2, f_col3 = st.columns(3)
        d_name = f_col1.text_input("Deneme Adı / Tarihi", value=f"Deneme {len(st.session_state.net_data)+1}")
        tyt_n = f_col2.number_input("TYT Netiniz", 0.0, 120.0, 70.0)
        ayt_n = f_col3.number_input("AYT Netiniz", 0.0, 80.0, 40.0)
        submit_net = st.form_submit_button("Neti Grafiğe Kaydet")

        if submit_net:
            st.session_state.net_data.append({"Deneme": d_name, "TYT": tyt_n, "AYT": ayt_n})
            st.success("Netiniz grafik geçmişine eklendi!")

    if plt and st.session_state.net_data:
        denemeler = [d["Deneme"] for d in st.session_state.net_data]
        tyt_list = [d["TYT"] for d in st.session_state.net_data]
        ayt_list = [d["AYT"] for d in st.session_state.net_data]

        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(denemeler, tyt_list, marker='o', label='TYT Net', color='#2563eb', linewidth=2.5)
        ax.plot(denemeler, ayt_list, marker='s', label='AYT Net', color='#dc2626', linewidth=2.5)
        ax.set_ylabel("Net Sayısı")
        ax.set_title("Deneme Gelişim İstatistiği")
        ax.legend()
        ax.grid(True, linestyle='--', alpha=0.4)
        st.pyplot(fig)


# --- TAB 6: POMODORO ---
with tab6:
    st.header("⏱️ Odaklanma & Pomodoro Alanı")
    p_col1, p_col2 = st.columns([1, 2])
    with p_col1:
        sure = st.number_input("Çalışma Süresi (Dakika):", value=25, min_value=1, max_value=90)
        mola = st.number_input("Mola Süresi (Dakika):", value=5, min_value=1, max_value=30)
        if st.button("Pomodoro Oturumunu Başlat"):
            st.info(f"🎯 {sure} dakikalık odaklanma oturumu başladı. Telefonunuzu uzaklaştırın ve derse odaklanın!")
    with p_col2:
        st.markdown("""
        ### 💡 Verimli Çalışma Tavsiyeleri:
        * **25 Dk Çalışma + 5 Dk Mola:** Zihninizin odaklanma süresini zirvede tutar.
        * **Mola Sırasında:** Ekrandan uzaklaşın, gözlerinizi dinlendirin ve su için.
        * **Her 4 Pomodoro Sonrasında:** 20-30 dakikalık uzun mola verin.
        """)


# --- TAB 7: DETAYLI KONU TAKİP ---
with tab7:
    st.header("✅ YKS Kapsamlı Müfretad & Konu Takibi")
    
    kt1, kt2, kt3 = st.tabs(["Matematik & Geometri", "Fen Bilimleri", "Türkçe & Sosyal"])

    with kt1:
        c_m1, c_m2 = st.columns(2)
        with c_m1:
            st.subheader("TYT Matematik")
            st.checkbox("Temel Kavramlar & Sayı Basamakları", value=True)
            st.checkbox("Bölme & Bölünebilme, EBOB-EKOK")
            st.checkbox("Rasyonel & Mutlak Değerli İfadeler")
            st.checkbox("Oran-Orantı & Problemler (Tümü)")
            st.checkbox("Fonksiyonlar & Mantık")
        with c_m2:
            st.subheader("AYT Matematik")
            st.checkbox("Polinomlar & 2. Dereceden Denklemler")
            st.checkbox("Trigonometri")
            st.checkbox("Logaritma & Diziler")
            st.checkbox("Limit & Süreklilik")
            st.checkbox("Türev & İntegral")

    with kt2:
        c_f1, c_f2 = st.columns(2)
        with c_f1:
            st.subheader("Fizik")
            st.checkbox("Fizik Bilimine Giriş & Madde")
            st.checkbox("Kuvvet, Hareket & Enerji")
            st.checkbox("Elektrik & Optik")
            st.checkbox("Atışlar & Çembersel Hareket (AYT)")
        with c_f2:
            st.subheader("Kimya & Biyoloji")
            st.checkbox("Kimyasal Türler Arası Etkileşimler")
            st.checkbox("Mol Kavramı & Tepkimeler")
            st.checkbox("Hücre & Canlıların Sınıflandırılması")
            st.checkbox("Sistemler (Anatomi AYT)")

    with kt3:
        c_s1, c_s2 = st.columns(2)
        with c_s1:
            st.subheader("Türkçe")
            st.checkbox("Paragrafta Anlam & Yorum", value=True)
            st.checkbox("Yazım Kuralları & Noktalama")
            st.checkbox("Ses Bilgisi & Sözcük Türleri")
        with c_s2:
            st.subheader("Tarih & Coğrafya")
            st.checkbox("Tarih Bilimi & İlk Çağ Uygarlıkları")
            st.checkbox("Milli Mücadele Dönemi")
            st.checkbox("Harita Bilgisi & İklim Tipleri")
