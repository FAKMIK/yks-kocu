import json
import os
import re
from datetime import datetime
from pathlib import Path
import streamlit as str_app # Streamlit kütüphanesi
from PIL import Image
import requests
from bs4 import BeautifulSoup
from google import genai
from google.genai import types

MODEL_NAME = "gemini-2.5-flash"
MEMORY_FILE = Path("yks_hafiza.jsonl")

# Sayfa Tasarımı ve Mobil Uyum Ayarları
str_app.set_page_config(page_title="Kagan'ın YKS Koçu", page_icon="🧠", layout="centered")

COACH_MEMORY = """
Sen YKS ogrencisi Kagan'in akilli egitim kocusun.
Sana gelen fotograf, link veya mesajlari incelerken su hocalardan destek al:
- Matematik: Eyüp B, Geometri: Kenan Kara, Türkçe: Rüştü Hoca.
Konuyu YKS mantigina gore anlat: tanim, kritik noktalar, tuzaklar ve taktikler ver.
"Hata DNA'si" fikrine uygunsa dikkat/bilgi/sure hatalarini ayir.
"""

def is_valid_url(url):
    return url.startswith(("http://", "https://"))

def scrape_link(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        paragraphs = [p.get_text(" ").strip() for p in soup.find_all(["h1", "h2", "h3", "p", "li"])]
        content = "\n".join(part for part in paragraphs if len(part) > 20)
        return {"url": url, "title": soup.title.get_text() if soup.title else "Baslik yok", "content": content[:5000]}
    except:
        return None

# --- TELEFON EKRANI (ARAYÜZ) TASARIMI ---
str_app.title("🧠 Kagan'ın Yapay Zeka YKS Koçu")
str_app.write("Telefonundan fotoğraf çek, link at veya koçunla konuş!")

# 1. BÖLÜM: Fotoğraf Yükleme Alanı (Telefonda kamerayı açar)
str_app.subheader("📸 Hatalı Soru Fotoğrafı Yükle")
uploaded_file = str_app.file_uploader("Sorunun fotoğrafını çek veya galeriye ekle", type=["png", "jpg", "jpeg"])

# 2. BÖLÜM: Link Ekleme Alanı
str_app.subheader("🔗 Ders Notu / Kaynak Linki Ekle")
input_url = str_app.text_input("YKS ders notu içeren bir web linki yapıştırın:")
input_topic = str_app.text_input("Bu linkin konusu nedir? (Örn: Paragraf Taktikleri):")

if str_app.button("Link İçeriğini Hafızaya Kaydet"):
    if is_valid_url(input_url) and input_topic:
        with str_app.spinner("Link internetten kazınıyor..."):
            scraped = scrape_link(input_url)
            if scraped:
                scraped["topic"] = input_topic
                scraped["saved_at"] = datetime.now().isoformat()
                with open(MEMORY_FILE, "a", encoding="utf-8") as f:
                    f.write(json.dumps(scraped, ensure_ascii=False) + "\n")
                str_app.success(f"✔ '{input_topic}' konusu başarıyla hafızaya kaydedildi!")
            else:
                str_app.error("Link içeriği çekilemedi.")
    else:
        str_app.warning("Lütfen geçerli bir URL ve konu adı girin.")

# 3. BÖLÜM: Koça Soru Sor ve Sentezle
str_app.subheader("💬 Koçuna Danış / Hafızayı Birleştir")
user_message = str_app.text_area("Koçuna ne sormak istersin?", placeholder="Örn: Bu soruda nerede hata yaptım? Veya: Kaydettiğim notları birleştir.")

if str_app.button("💥 Koçumu Çalıştır / Analiz Et"):
    if not os.environ.get("GEMINI_API_KEY"):
        str_app.error("HATA: GEMINI_API_KEY bulunamadı!")
    else:
        client = genai.Client()
        contents_list = [user_message]
        
        # Eğer fotoğraf yüklendiyse listeye ekle
        if uploaded_file is not None:
            img = Image.open(uploaded_file)
            contents_list.append(img)
            str_app.image(img, caption="Yüklenen Soru Fotoğrafı", use_container_width=True)
            
        # Hafıza dosyasını oku ve ekle
        if MEMORY_FILE.exists():
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                memory_text = "\n".join([json.loads(line).get("content", "") for line in f if line.strip()])
                contents_list.append(f"\nHafızadaki Geçmiş Kayıtlar:\n{memory_text[:4000]}")
                
        with str_app.spinner("Kagan Koç düşünüyor ve not hazırlıyor..."):
            try:
                response = client.models.generate_content(
                    model=MODEL_NAME,
                    contents=contents_list,
                    config=types.GenerateContentConfig(system_instruction=COACH_MEMORY, temperature=0.3)
                )
                str_app.markdown("### 📋 YAPAY ZEKA KOÇUNUN CEVABI")
                str_app.info(response.text)
            except Exception as e:
                str_app.error(f"Bir hata oluştu: {e}")