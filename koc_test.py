import os
import json
import io
import streamlit as st
from PIL import Image
import google.generativeai as genai
from datetime import datetime
import matplotlib.pyplot as plt

# --------------------- ÖZEL CSS (MODERN TASARIM) ---------------------
st.set_page_config(page_title="YKS Koçu", page_icon="📚", layout="wide")

st.markdown("""
<style>
    /* Genel yazı tipi ve renk */
    .main {
        font-family: 'Segoe UI', Roboto, sans-serif;
        color: #1E293B;
    }
    h1, h2, h3 {
        font-weight: 600;
        color: #2E4374;
    }
    /* Butonlar */
    .stButton button {
        background-color: #2E4374;
        color: white;
        border-radius: 8px;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: 500;
        transition: all 0.2s ease;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .stButton button:hover {
        background-color: #1F2F55;
        transform: scale(1.02);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    /* Text input ve text area */
    .stTextInput input, .stTextArea textarea {
        border-radius: 8px;
        border: 1px solid #CBD5E1;
        padding: 0.6rem;
        font-size: 0.95rem;
    }
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: #2E4374;
        box-shadow: 0 0 0 2px rgba(46, 67, 116, 0.2);
    }
    /* Expander */
    .streamlit-expanderHeader {
        background-color: #F4F6FB;
        border-radius: 8px;
        font-weight: 500;
        color: #2E4374;
    }
    .streamlit-expanderContent {
        background-color: white;
        border-radius: 0 0 8px 8px;
        border-left: 3px solid #2E4374;
        padding: 1rem;
    }
    /* Sidebar */
    .css-1d391kg {
        background-color: #F8FAFC;
        padding: 1.5rem 1rem;
    }
    /* Metric */
    .stMetric {
        background-color: white;
        border-radius: 12px;
        padding: 0.8rem;
        box-shadow: 0 2px 6px rgba(0,0,0,0.05);
    }
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 0.6rem 1.2rem;
        background-color: #F1F5F9;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background-color: #2E4374;
        color: white;
    }
    /* Chat */
    .stChatMessage {
        border-radius: 12px;
        padding: 0.8rem 1.2rem;
        margin: 0.5rem 0;
    }
    .stChatMessage[data-testid="user"] {
        background-color: #EFF6FF;
        border-left: 4px solid #2E4374;
    }
    .stChatMessage[data-testid="assistant"] {
        background-color: #F8FAFC;
        border-left: 4px solid #94A3B8;
    }
    /* Görseller */
    .stImage img {
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    }
    /* Download butonu */
    .stDownloadButton button {
        background-color: #22C55E;
        color: white;
        border-radius: 8px;
        border: none;
        padding: 0.5rem 1.2rem;
        font-weight: 500;
    }
    .stDownloadButton button:hover {
        background-color: #16A34A;
    }
    /* Mobil uyum */
    @media (max-width: 600px) {
        .stButton button {
            font-size: 0.9rem;
            padding: 0.4rem 0.8rem;
        }
        .stTabs [data-baseweb="tab"] {
            padding: 0.4rem 0.8rem;
            font-size: 0.85rem;
        }
    }
</style>
""", unsafe_allow_html=True)

# --------------------- AYARLAR VE TANIMLAMALAR ---------------------
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

def generate_structured_plan(plan_metni):
    """Serbest metin halindeki bir programı, görselleştirmeye uygun JSON'a çevirir."""
    model = get_model()
    json_prompt = (
        "Asagida bir YKS calisma programi metni var:\n\n"
        f"{plan_metni}\n\n"
        "Bu programi SADECE gecerli JSON olarak, aciklama, yorum veya markdown "
        "isaretleri (```) OLMADAN, tam olarak asagidaki semaya uygun sekilde ver:\n\n"
        '{"program": ['
        '{"gun": "Pazartesi", '
        '"dersler": [{"ders": "Matematik", "sure": "2 saat", "konu": "Fonksiyonlar", "hedef": "20 soru"}]}'
        "]}\n\n"
        "Her gun icin en az bir ders girisi olsun. Sadece JSON dondur, baska hicbir metin ekleme."
    )
    response = model.generate_content(json_prompt)
    text = response.text.strip()
    text = text.replace("```json", "").replace("```", "").strip()
    return json.loads(text)

def render_program_image(program_data):
    """Yapılandırılmış program verisinden bir haftalık program görseli (PNG) üretir."""
    days = program_data.get("program", [])
    if not days:
        raise ValueError("Program verisi boş.")

    rows = []
    for day in days:
        gun = day.get("gun", "")
        dersler = day.get("dersler", [])
        satirlar = []
        for d in dersler:
            parca = f"{d.get('ders', '')} ({d.get('sure', '')})"
            if d.get("konu"):
                parca += f" - {d.get('konu')}"
            if d.get("hedef"):
                parca += f"\n  Hedef: {d.get('hedef')}"
            satirlar.append(parca)
        rows.append([gun, "\n\n".join(satirlar) if satirlar else "-"])

    fig_height = max(4, len(rows) * 1.4)
    fig, ax = plt.subplots(figsize=(11, fig_height))
    ax.axis("off")

    table = ax.table(
        cellText=rows,
        colLabels=["Gün", "Program"],
        loc="center",
        cellLoc="left",
        colWidths=[0.18, 0.82],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1, 2.8)  # satır yüksekliği

    for (row_idx, col_idx), cell in table.get_celld().items():
        cell.set_text_props(wrap=True, ha="left", va="center")
        cell.PAD = 0.02
        if row_idx == 0:
            cell.set_facecolor("#2E4374")
            cell.set_text_props(color="white", weight="bold", ha="center")
        else:
            cell.set_facecolor("#F8FAFC" if row_idx % 2 == 0 else "#EEF2F6")
            cell.set_edgecolor("#CBD5E1")

    plt.title("Haftalık Çalışma Programı", fontsize=14, weight="bold", pad=16)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=180, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf

def gorsel_olustur_ve_goster(plan_metni, anahtar):
    """Metin programdan JSON üretip görseli ekrana basan ve indirme butonu koyan yardımcı fonksiyon."""
    with st.spinner("Program görselleştiriliyor..."):
        try:
            structured = generate_structured_plan(plan_metni)
            image_buf = render_program_image(structured)
        except Exception as error:
            st.error(f"Görsel oluşturulamadı: {error}")
            return
    st.image(image_buf, caption="Haftalık Program Görseli", use_container_width=True)
    st.download_button(
        "Görseli İndir (PNG)",
        data=image_buf,
        file_name="yks_programi.png",
        mime="image/png",
        use_container_width=True,
        key=f"indir_{anahtar}",
    )

# --------------------- ARAYÜZ BAŞLANGICI ---------------------
api_ready = configure_gemini()

st.title("📘 Kagan'in Yapay Zeka YKS Koçu")
st.caption("Analiz et → Yönlendir → Başarıya ulaş")

# ---- YAN MENÜ (SIDEBAR) ----
with st.sidebar:
    # İstersen buraya bir logo ekleyebilirsin:
    # st.image("logo.png", width=150)
    st.header("🧠 Durum")
    if api_ready:
        st.success("✅ Gemini API hazır")
    else:
        st.error("❌ GEMINI_API_KEY bulunamadı")

    saved_records = load_memory()
    st.metric("📂 Hafıza kaydı", len(saved_records))

    if saved_records:
        with st.expander("📋 Son kayıtlar"):
            for record in saved_records[-8:]:
                st.write(f"- {record.get('type')} | {record.get('title')}")

if not api_ready:
    st.info("Devam etmek için Streamlit Secrets veya ortam değişkenlerine GEMINI_API_KEY ekle.")
    st.stop()

# ---- SEKMELER (TABS) ----
tab_question, tab_program, tab_resource, tab_memory = st.tabs(
    ["📝 Soru Analizi", "📅 Program", "🔗 Kaynak", "🗂️ Hafıza"]
)

# ---- 1. SEKME: SORU ANALİZİ ----
with tab_question:
    st.subheader("❓ Hatalı Soru Fotoğrafı")
    uploaded_file = st.file_uploader(
        "Sorunun fotoğrafını yükle",
        type=["png", "jpg", "jpeg"],
    )

    if uploaded_file is not None:
        st.image(uploaded_file, caption="Yüklenen soru", use_container_width=True)

    if st.button("🔍 Soruyu Analiz Et ve Hafızaya Al", use_container_width=True):
        if uploaded_file is None:
            st.warning("Önce bir soru fotoğrafı yükle.")
        else:
            with st.spinner("Koçun soruyu inceliyor..."):
                try:
                    analysis = analyze_image(uploaded_file)
                except Exception as error:
                    st.error(f"Soru analiz edilemedi: {error}")
                else:
                    st.success("✅ Analiz tamamlandı.")
                    st.markdown(analysis)
                    save_memory("soru_analizi", analysis, uploaded_file.name)

# ---- 2. SEKME: PROGRAM YÖNETİMİ ----
with tab_program:
    st.subheader("📅 Çalışma Programı")
    col1, col2 = st.columns([3, 1])
    with col1:
        mode = st.radio(
            "Ne yapmak istersin?",
            ["🤖 Yapay zekaya program hazırlat", "✍️ Mevcut programımı kaydet"],
            horizontal=True
        )

    if mode == "🤖 Yapay zekaya program hazırlat":
        student_status = st.text_area(
            "Hedeflerin, günlük çalışma süren ve zorlandığın dersler",
            placeholder=(
                "Örn: 11. sınıftayım, sayısal hazırlanıyorum. "
                "Günde 4 saat çalışabilirim. Geometride zorlanıyorum."
            ),
            height=140,
        )

        if st.button("🚀 Bana Özel Program Hazırla", use_container_width=True):
            if not student_status.strip():
                st.warning("Önce durumunu ve hedefini yaz.")
            else:
                with st.spinner("Program hazırlanıyor..."):
                    try:
                        memory_text = memory_to_text(load_memory())
                        prompt = (
                            f"Öğrencinin durumu:\n{student_status}\n\n"
                            f"Hafıza kayıtları:\n{memory_text}\n\n"
                            "Bu bilgilere göre uygulanabilir 7 günlük YKS çalışma programı hazırla. "
                            "Eyüp B., Kenan Kara ve Rüştü Hoca'nın ders planlama mantığına uygun olsun. "
                            "Her gün için ders, süre, konu ve mini hedef yaz."
                        )
                        plan = generate_text(prompt)
                    except Exception as error:
                        st.error(f"Program hazırlanamadı: {error}")
                    else:
                        st.success("✅ Program hazır.")
                        st.markdown(plan)
                        save_memory("calisma_programi", plan, "Yapay zeka programı")
                        st.session_state["son_ai_programi"] = plan

        if st.session_state.get("son_ai_programi"):
            st.divider()
            if st.button("📊 Programın Görselini Oluştur", use_container_width=True, key="gorsel_ai"):
                gorsel_olustur_ve_goster(st.session_state["son_ai_programi"], "ai")

    else:
        current_plan = st.text_area(
            "Şu an uyguladığın haftalık planı yaz",
            placeholder="Pazartesi: Matematik 2 saat, Türkçe 1 saat...",
            height=170,
        )

        if st.button("💾 Programımı Hafızaya Kaydet", use_container_width=True):
            if not current_plan.strip():
                st.warning("Önce programını yaz.")
            else:
                save_memory("calisma_programi", current_plan, "Kagan'in mevcut programı")
                st.success("✅ Program hafızaya kaydedildi.")
                st.session_state["son_manuel_program"] = current_plan

        if st.session_state.get("son_manuel_program"):
            st.divider()
            if st.button("📊 Programın Görselini Oluştur", use_container_width=True, key="gorsel_manuel"):
                gorsel_olustur_ve_goster(st.session_state["son_manuel_program"], "manuel")

# ---- 3. SEKME: KAYNAK LİNKİ ----
with tab_resource:
    st.subheader("🔗 Ders Notu / Kaynak Linki")
    link = st.text_input("Web linki")
    link_topic = st.text_input("Konu", placeholder="Örn: Fonksiyonlar, Paragraf Taktikleri")
    scrape_enabled = st.checkbox("📄 Link içeriğini okuyup hafızaya kaydet", value=True)

    if st.button("📥 Kaynak Hafızaya Ekle", use_container_width=True):
        if not link.strip() or not link_topic.strip():
            st.warning("Link ve konu alanlarını doldur.")
        elif scrape_enabled:
            with st.spinner("Link okunuyor..."):
                scraped, error = scrape_link(link.strip())

            if error:
                st.error(error)
            else:
                content = (
                    f"URL: {link}\n"
                    f"Sayfa başlığı: {scraped['title']}\n\n"
                    f"{scraped['content']}"
                )
                save_memory("kaynak_linki", content, link_topic)
                st.success("✅ Link içeriği hafızaya eklendi.")
        else:
            save_memory("kaynak_linki", link.strip(), link_topic)
            st.success("✅ Link hafızaya eklendi.")

# ---- 4. SEKME: HAFIZA ----
with tab_memory:
    st.subheader("🗂️ Kayıtlı Hafıza")
    records = load_memory()

    if not records:
        st.info("Henüz hafıza kaydı yok.")
    else:
        for idx, record in enumerate(reversed(records[-20:])):
            with st.expander(f"{record.get('type')} | {record.get('title')}"):
                st.caption(record.get("created_at", "Tarih yok"))
                st.write(record.get("content", ""))
                if record.get("type") == "calisma_programi":
                    if st.button("📊 Bu Programın Görselini Oluştur", key=f"gorsel_hafiza_{idx}"):
                        gorsel_olustur_ve_goster(record.get("content", ""), f"hafiza_{idx}")

# ---- SOHBET ALANI ----
st.divider()
st.header("💬 Koçunla Konuş")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if user_input := st.chat_input("Koçuna bir şey sor..."):
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Düşünüyorum..."):
            try:
                memory_text = memory_to_text(load_memory())
                prompt = (
                    f"Hafıza kayıtları:\n{memory_text}\n\n"
                    f"Kagan'in mesajı:\n{user_input}\n\n"
                    "Sen Kagan'in YKS koçusun. Hafızayı dikkate alarak samimi ve net cevap ver."
                )
                answer = generate_text(prompt)
            except Exception as error:
                answer = f"Hata oluştu: {error}"

            st.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})