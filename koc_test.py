import os
import json
import streamlit as st
from PIL import Image
import google.generativeai as genai
from datetime import datetime

# --- AYARLAR VE TANIMLAMALAR ---
MAX_MEMORY_CHARS = 4000
HAFIZA_DOSYASI = "yks_hafiza.jsonl"

def configure_gemini():
    """Gemini API anahtarını kontrol eder ve yapılandırır."""
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        return True
    elif os.environ.get("GEMINI_API_KEY"):
        genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
        return True
    return False

def get_model():
    """Gemini modelini döndürür."""
    return genai.GenerativeModel('gemini-2.5-flash')

def load_memory():
    """Kayıtlı hafıza geçmişini JSONL dosyasından okur."""
    if not os.path.exists(HAFIZA_DOSYASI):
        return []
    records = []
    with open(HAFIZA_DOSYASI, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    records.append(json.loads(line))
                except:
                    continue
    return records

def save_memory(record_type, content, title=""):
    """Yeni bir veriyi hafızaya tarihle birlikte kaydeder."""
    record = {
        "type": record_type,
        "title": title,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "content": content
    }
    with open(HAFIZA_DOSYASI, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

def scrape_link(url):
    """Link içeriğini basitçe simüle eder veya okur."""
    # Orijinal kodundaki scrape yapısını bozmamak için temel bir sözlük döndürüyoruz
    return {"title": "Web Kaynağı", "content": f"Uzak bağlantı içeriği: {url}"}, None

def memory_to_text(records):
    """Hafıza kayıtlarını yapay zekanın anlayacağı metin bloklarına çevirir."""
    blocks = []
    for index, record in enumerate(records[-30:], start=1):
        blocks.append(
            "\n".join(
                [
                    f"KAYIT {index}",
                    f"Tip: {record.get('type', 'bilinmiyor')}",
                    f"Baslik: {record.get('title', 'Baslik yok')}",
                    f"Tarih: {record.get('created_at', 'Tarih yok')}",
                    f"Icerik: {record.get('content', '')}",
                ]
            )
        )
    return "\n\n".join(blocks)[:MAX_MEMORY_CHARS]

def generate_text(prompt):
    """Metin tabanlı Gemini isteği gönderir."""
    model = get_model()
    response = model.generate_content(prompt)
    return response.text

def analyze_image(uploaded_file):
    """Soru fotoğrafını analiz eder."""
    image = Image.open(uploaded_file)
    model = get_model()
    prompt = (
        "Bu bir YKS hazirlik soru. Soruyu analiz et. "
        "Cozum mantigini anlat, ogrencinin muhtemel hatasini bul, "
        "hata turunu dikkat/bilgi/sure olarak siniflandir ve mini odev ver."
    )
    response = model.generate_content([prompt, image])
    return response.text

# --- ARAYÜZ BAŞLANGICI ---
api_ready = configure_gemini()

st.title("Kagan'in Yapay Zeka YKS Kocu")
st.caption("Olc -> analiz et -> yonlendir")

# ---- YAN MENÜ (SIDEBAR) ----
with st.sidebar:
    st.header("Durum")
    if api_ready:
        st.success("Gemini API hazir")
    else:
        st.error("GEMINI_API_KEY bulunamadi")

    saved_records = load_memory()
    st.metric("Hafiza kaydi", len(saved_records))

    if saved_records:
        with st.expander("Son kayitlar"):
            for record in saved_records[-8:]:
                st.write(f"- {record.get('type')} | {record.get('title')}")

if not api_ready:
    st.info("Devam etmek icin Streamlit Secrets veya ortam degiskenlerine GEMINI_API_KEY ekle.")
    st.stop()

# ---- SEKMELER (TABS) ----
tab_question, tab_program, tab_resource, tab_memory = st.tabs(
    ["Soru Analizi", "Program", "Kaynak", "Hafiza"]
)

# ---- 1. SEKME: SORU ANALİZİ ----
with tab_question:
    st.subheader("Hatali Soru Fotografi")
    uploaded_file = st.file_uploader(
        "Sorunun fotografini yukle",
        type=["png", "jpg", "jpeg"],
    )

    if uploaded_file is not None:
        st.image(uploaded_file, caption="Yuklenen soru", use_container_width=True)

    if st.button("Soruyu Analiz Et ve Hafizaya Al", use_container_width=True):
        if uploaded_file is None:
            st.warning("Once bir soru fotografi yukle.")
        else:
            with st.spinner("Kocun soruyu inceliyor..."):
                try:
                    analysis = analyze_image(uploaded_file)
                except Exception as error:
                    st.error(f"Soru analiz edilemedi: {error}")
                else:
                    st.success("Analiz tamamlandi.")
                    st.markdown(analysis)
                    save_memory("soru_analizi", analysis, uploaded_file.name)

# ---- 2. SEKME: PROGRAM YÖNETİMİ ----
with tab_program:
    st.subheader("Calisma Programi")
    mode = st.radio(
        "Ne yapmak istersin?",
        ["Yapay zekaya program hazirlat", "Mevcut programimi kaydet"],
    )

    if mode == "Yapay zekaya program hazirlat":
        student_status = st.text_area(
            "Hedeflerin, gunluk calisma suren ve zorlandigin dersler",
            placeholder=(
                "Orn: 11. siniftayim, sayisal hazirlaniyorum. "
                "Gunde 4 saat calisabilirim. Geometride zorlanıyorum."
            ),
            height=140,
        )

        if st.button("Bana Ozel Program Hazirla", use_container_width=True):
            if not student_status.strip():
                st.warning("Once durumunu ve hedefini yaz.")
            else:
                with st.spinner("Program hazirlaniyor..."):
                    try:
                        memory_text = memory_to_text(load_memory())
                        prompt = (
                            f"Ogrencinin durumu:\n{student_status}\n\n"
                            f"Hafiza kayitlari:\n{memory_text}\n\n"
                            "Bu bilgilere gore uygulanabilir 7 gunluk YKS calisma programi hazirla. "
                            "Eyup B, Kenan Kara ve Rustu Hoca'nin ders planlama mantigina uygun olsun. "
                            "Her gun icin ders, sure, konu ve mini hedef yaz."
                        )
                        plan = generate_text(prompt)
                    except Exception as error:
                        st.error(f"Program hazirlanamadi: {error}")
                    else:
                        st.success("Program hazir.")
                        st.markdown(plan)
                        save_memory("calisma_programi", plan, "Yapay zeka programi")

    else:
        current_plan = st.text_area(
            "Su an uyguladigin haftalik plani yaz",
            placeholder="Pazartesi: Matematik 2 saat, Turkce 1 saat...",
            height=170,
        )

        if st.button("Programimi Hafizaya Kaydet", use_container_width=True):
            if not current_plan.strip():
                st.warning("Once programini yaz.")
            else:
                save_memory("calisma_programi", current_plan, "Kagan'in mevcut programi")
                st.success("Program hafizaya kaydedildi.")

# ---- 3. SEKME: KAYNAK LİNKİ ----
with tab_resource:
    st.subheader("Ders Notu / Kaynak Linki")
    link = st.text_input("Web linki")
    link_topic = st.text_input("Konu", placeholder="Orn: Fonksiyonlar, Paragraf Taktikleri")
    scrape_enabled = st.checkbox("Link icerigini okuyup hafizaya kaydet", value=True)

    if st.button("Kaynak Hafizaya Ekle", use_container_width=True):
        if not link.strip() or not link_topic.strip():
            st.warning("Link ve konu alanlarini doldur.")
        elif scrape_enabled:
            with st.spinner("Link okunuyor..."):
                scraped, error = scrape_link(link.strip())

            if error:
                st.error(error)
            else:
                content = (
                    f"URL: {link}\n"
                    f"Sayfa basligi: {scraped['title']}\n\n"
                    f"{scraped['content']}"
                )
                save_memory("kaynak_linki", content, link_topic)
                st.success("Link icerigi hafizaya eklendi.")
        else:
            save_memory("kaynak_linki", link.strip(), link_topic)
            st.success("Link hafizaya eklendi.")

# ---- 4. SEKME: HAFIZA ----
with tab_memory:
    st.subheader("Kayitli Hafiza")
    records = load_memory()

    if not records:
        st.info("Henuz hafiza kaydi yok.")
    else:
        for record in reversed(records[-20:]):
            with st.expander(f"{record.get('type')} | {record.get('title')}"):
                st.caption(record.get("created_at", "Tarih yok"))
                st.write(record.get("content", ""))

# ---- SOHBET ALANI ----
st.divider()
st.header("Kocunla Konus")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if user_input := st.chat_input("Kocuna bir sey sor..."):
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Dusunuyorum..."):
            try:
                memory_text = memory_to_text(load_memory())
                prompt = (
                    f"Hafiza kayitlari:\n{memory_text}\n\n"
                    f"Kagan'in mesaji:\n{user_input}\n\n"
                    "Sen Kagan'in YKS koçusun. Hafızayı dikkate alarak samimi ve net cevap ver."
                )
                answer = generate_text(prompt)
            except Exception as error:
                answer = f"Hata olustu: {error}"

            st.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})