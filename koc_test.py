import streamlit as st
import time

# -----------------------------------------------------------------------------
# 1. SAYFA YAPILANDIRMASI
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="IVI · YKS Çalışma Stüdyosu",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# 2. IVI ÖZEL CSS & SİBER-KADIN YAPAY ZEKÂ TEMA TASARIMI
# -----------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;800&display=swap');

:root {
    --bg-dark: #090d16;
    --card-bg: rgba(15, 23, 42, 0.75);
    --brand-pink: #ec4899;
    --brand-purple: #8b5cf6;
    --brand-cyan: #06b6d4;
    --text-main: #f8fafc;
    --text-muted: #94a3b8;
    --line-border: rgba(255, 255, 255, 0.08);
}

html, body, [data-testid="stAppViewContainer"] {
    background-color: var(--bg-dark);
    font-family: 'Plus Jakarta Sans', sans-serif;
    color: var(--text-main);
}

/* Yan Menü (Sidebar) Cam Efekti */
[data-testid="stSidebar"] {
    background: var(--card-bg) !important;
    backdrop-filter: blur(20px);
    border-right: 1px solid var(--line-border);
}

.side-brand {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 0.5rem 0 1.5rem;
    font-weight: 800;
    font-size: 1.2rem;
    letter-spacing: 0.05em;
    color: #fff;
}

.side-mark {
    display: grid;
    place-items: center;
    width: 40px;
    height: 40px;
    border-radius: 12px;
    background: linear-gradient(135deg, var(--brand-pink), var(--brand-cyan));
    color: #fff;
    font-weight: 900;
    box-shadow: 0 0 18px rgba(236, 72, 153, 0.5);
}

/* Hero Kartı - IVI Bilgi Paneli */
.hero-card {
    position: relative;
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 2rem;
    min-height: 220px;
    padding: 2.2rem;
    margin-bottom: 2rem;
    border-radius: 24px;
    border: 1px solid var(--line-border);
    background: linear-gradient(120deg, #0f172a 0%, #1e1b4b 50%, #4c1d95 100%);
    box-shadow: 0 20px 50px rgba(139, 92, 246, 0.2);
}

.hero-card::before {
    content: '';
    position: absolute;
    width: 300px;
    height: 300px;
    border-radius: 50%;
    right: -40px;
    top: -80px;
    background: radial-gradient(circle, rgba(236, 72, 153, 0.25) 0%, rgba(6, 182, 212, 0) 70%);
    filter: blur(40px);
    animation: ivipulse 6s ease-in-out infinite alternate;
}

@keyframes ivipulse {
    0% { transform: scale(0.9); opacity: 0.5; }
    100% { transform: scale(1.2); opacity: 0.9; }
}

/* IVI Holografik AI Core (Çekirdek Animasyonu) */
.ivi-core-container {
    width: 160px;
    height: 160px;
    display: grid;
    place-items: center;
    position: relative;
}

.ivi-ring {
    position: absolute;
    border-radius: 50%;
    border: 2px solid transparent;
}

.ivi-ring.outer {
    inset: 0%;
    border-top-color: var(--brand-pink);
    border-bottom-color: var(--brand-cyan);
    animation: spin 8s linear infinite;
    box-shadow: 0 0 15px rgba(236, 72, 153, 0.3);
}

.ivi-ring.mid {
    inset: 18%;
    border-left-color: var(--brand-purple);
    border-right-color: #38bdf8;
    animation: spin 12s linear infinite reverse;
}

.ivi-ring.inner {
    inset: 35%;
    border: 2px dashed rgba(255, 255, 255, 0.6);
    animation: spin 18s linear infinite;
}

.ivi-nucleus {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: radial-gradient(circle at 35% 35%, #fff, var(--brand-pink) 50%, var(--brand-purple) 90%);
    box-shadow: 0 0 20px var(--brand-pink), 0 0 40px var(--brand-purple);
    animation: coreGlow 2.5s ease-in-out infinite alternate;
}

@keyframes spin { to { transform: rotate(360deg); } }
@keyframes coreGlow {
    0% { filter: brightness(0.9); transform: scale(0.92); }
    100% { filter: brightness(1.3); transform: scale(1.08); }
}

/* Canlı Ses Dalgalı Gösterge */
.sound-wave {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    height: 18px;
    margin-left: 10px;
}

.sound-wave span {
    width: 3px;
    height: 100%;
    background: linear-gradient(180deg, var(--brand-pink), var(--brand-cyan));
    border-radius: 3px;
    animation: wave 1.2s ease-in-out infinite;
}

.sound-wave span:nth-child(2) { animation-delay: 0.2s; }
.sound-wave span:nth-child(3) { animation-delay: 0.4s; }
.sound-wave span:nth-child(4) { animation-delay: 0.1s; }

@keyframes wave {
    0%, 100% { height: 4px; }
    50% { height: 18px; }
}

/* Butonlar & Input Stilleri */
.stButton button {
    background: linear-gradient(135deg, var(--brand-pink), var(--brand-purple)) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
    box-shadow: 0 4px 15px rgba(236, 72, 153, 0.3) !important;
    transition: all 0.25s ease !important;
}

.stButton button:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 22px rgba(236, 72, 153, 0.5) !important;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 3. KİŞİLİK VE SİSTEM PROMPTU (IVI PERSONA)
# -----------------------------------------------------------------------------
IVI_SYSTEM_PROMPT = (
    "Sen IVI'sin (Intelligent Virtual Instructor). YKS öğrencilerine özel rehberlik sunan, "
    "yüksek empatiye sahip, motive edici, yapıcı, zeki ve son derece modern bir kadın yapay zekâ asistanısın. "
    "Öğrenciye hitap ederken samimi, destekleyici fakat disiplini elden bırakmayan bir üslup benimse. "
    "Analitik ve pratik tavsiyeler ver."
)

# Oturum Durumu Başlatma
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Selam Kağan! Ben IVI. YKS hazırlık sürecinde çalışma temponu yükseltmek ve hedeflerine ulaşmanı sağlamak için buradayım. Bugün nasıl gidiyoruz?"
        }
    ]

# -----------------------------------------------------------------------------
# 4. YAN MENÜ (SIDEBAR)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("""
        <div class="side-brand">
            <div class="side-mark">IVI</div>
            <div>IVI Stüdyo v2.5</div>
        </div>
    """, unsafe_allow_html=True)
    
    st.subheader("⚙️ Asistan Modu")
    mode = st.selectbox(
        "Odak Modu Seçin:",
        ["YKS Koçluğu & Soru Analizi", "Soru Hazırlama & Test", "Hızlı Yanıt & Konu Özetleri"]
    )
    
    st.divider()
    
    st.markdown("### 📊 Durum Paneli")
    st.caption("• Sistem: **Çevrimiçi**")
    st.caption("• Modül: **Gemini / Custom IVI Engine**")
    st.caption("• Odaklanma Seviyesi: **%100**")
    
    if st.button("Sohbeti Temizle"):
        st.session_state.messages = [
            {"role": "assistant", "content": "Sohbet sıfırlandı. Yeniden başlamaya hazırım!"}
        ]
        st.rerun()

# -----------------------------------------------------------------------------
# 5. ANA EKRAN VE HERO KART
# -----------------------------------------------------------------------------
st.markdown(f"""
    <div class="hero-card">
        <div>
            <h1 style="margin:0; font-size: 2.2rem; font-weight:800; color:#fff;">
                IVI Çalışma Stüdyosu
                <div class="sound-wave">
                    <span></span><span></span><span></span><span></span>
                </div>
            </h1>
            <p style="margin-top:8px; color: var(--text-muted); font-size:1.05rem;">
                Aktivite: <b>{mode}</b> — Zekâ, strateji ve yüksek motivasyonla hedeflerine odaklan.
            </p>
        </div>
        <div class="ivi-core-container">
            <div class="ivi-ring outer"></div>
            <div class="ivi-ring mid"></div>
            <div class="ivi-ring inner"></div>
            <div class="ivi-nucleus"></div>
        </div>
    </div>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 6. SOHBET AKIŞI (CHAT INTERFACE)
# -----------------------------------------------------------------------------
for msg in st.session_state.messages:
    if msg["role"] == "user":
        with st.chat_message("user", avatar="🧑‍💻"):
            st.write(msg["content"])
    else:
        with st.chat_message("assistant", avatar="💎"):
            st.write(msg["content"])

# Kullanıcı Girdisi
if user_input := st.chat_input("IVI'ye bir soru sor veya çalışma planından bahset..."):
    # Kullanıcı mesajını ekle
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user", avatar="🧑‍💻"):
        st.write(user_input)

    # IVI Yanıtı Simülasyonu
    with st.chat_message("assistant", avatar="💎"):
        response_placeholder = st.empty()
        full_response = ""
        
        # Buraya kendi API çağrınızı (örn: google-generativeai / openai) IVI_SYSTEM_PROMPT ile bağlayabilirsiniz.
        # Örnek simüle edilmiş yanıt akışı:
        simulated_text = f"Anladım. '{user_input}' konusu üzerine YKS stratejimizi netleştirelim. Çalışma programına sadık kaldığın sürece başarı kaçınılmaz!"
        
        for chunk in simulated_text.split():
            full_response += chunk + " "
            time.sleep(0.05)
            response_placeholder.markdown(full_response + "▌")
            
        response_placeholder.markdown(full_response)
    
    st.session_state.messages.append({"role": "assistant", "content": full_response})
