#!/usr/bin/env python3
"""
Ateş Hukuk Bürosu — Otomatik Blog Üretici (Google Gemini Sürümü)
Gemini API ile tam HTML formatında blog üretir ve:
  1. blog/ klasörüne yeni blog .html dosyası kaydeder
  2. index.html'deki blog kartları listesini günceller
"""

import google.generativeai as genai
import datetime
import json
import os
import re
import random
import sys

# ── Gemini API Kurulumu ──────────────────────────────────────────────────────
# API Anahtarınızı ortam değişkenlerinden alıyoruz
API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    print("⚠️ HATA: GEMINI_API_KEY ortam değişkeni bulunamadı!")
    sys.exit(1)

genai.configure(api_key=API_KEY)

# ── Konu havuzu ──────────────────────────────────────────────────────────────
KONULAR = [
    {"konu": "İş sözleşmesi fesih türleri ve işçi tazminat hakları", "kategori": "İş Hukuku"},
    {"konu": "Boşanmada mal paylaşımı: edinilmiş mallara katılma rejimi", "kategori": "Aile Hukuku"},
    {"konu": "Kira tespit ve tahliye davalarında kiracı hakları", "kategori": "Gayrimenkul Hukuku"},
    {"konu": "Trafik kazalarında tazminat: sigorta ve kusur oranı", "kategori": "Tazminat Hukuku"},
    {"konu": "Miras hukuku: saklı pay ve tenkis davası", "kategori": "Miras Hukuku"},
    {"konu": "Ceza muhakemesinde tutukluluk ve tahliye prosedürü", "kategori": "Ceza Hukuku"},
    {"konu": "Kentsel dönüşümde kat mülkiyeti ve müteahhit sorumlulukları", "kategori": "Gayrimenkul Hukuku"},
    {"konu": "İş kazası tazminatı: işverenin hukuki sorumluluğu", "kategori": "İş Hukuku"},
    {"konu": "Nafaka davası: tedbir, iştirak ve yoksulluk nafakası", "kategori": "Aile Hukuku"},
    {"konu": "Dolandırıcılık suçu: unsurları ve güncel Yargıtay kararları", "kategori": "Ceza Hukuku"},
    {"konu": "Anonim şirket genel kurul kararlarının iptali davası", "kategori": "Ticaret Hukuku"},
    {"konu": "KVKK kapsamında kişisel veri ihlali ve tazminat hakkı", "kategori": "Bilişim Hukuku"},
    {"konu": "Mobbing (işyeri psikolojik tacizi) ve hukuki yollar", "kategori": "İş Hukuku"},
    {"konu": "Velayetin değiştirilmesi davası: Yargıtay kriterleri", "kategori": "Aile Hukuku"},
    {"konu": "İcra hukuku: borcun durdurulması ve itiraz süreçleri", "kategori": "İcra Hukuku"},
]

# ── Yardımcı fonksiyonlar ─────────────────────────────────────────────────────

def slugify(text: str) -> str:
    tr_map = str.maketrans("çğışöüÇĞİŞÖÜ", "cgisoucgisou")
    text = text.translate(tr_map).lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"\s+", "-", text.strip())
    return text[:70]

def turkce_tarih(d: datetime.date) -> str:
    aylar = ["Ocak","Şubat","Mart","Nisan","Mayıs","Haziran",
             "Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık"]
    return f"{d.day} {aylar[d.month-1]} {d.year}"

def okuma_suresi(html: str) -> int:
    temiz = re.sub(r"<[^>]+>", " ", html)
    kelimeler = len(temiz.split())
    return max(3, round(kelimeler / 200))


# ── Mevcut blogları listele ──────────────────────────────────────────────────

def mevcut_blog_konulari() -> list:
    """blog/ klasöründeki mevcut HTML dosyalarının başlıklarını okur."""
    konular = []
    if not os.path.exists("blog"):
        return konular
    for dosya in os.listdir("blog"):
        if dosya.endswith(".html") and dosya != "blog-sablon.html":
            yol = os.path.join("blog", dosya)
            try:
                with open(yol, "r", encoding="utf-8") as f:
                    icerik = f.read()
                title_match = re.search(r"<title>(.*?)</title>", icerik)
                if title_match:
                    baslik = title_match.group(1).replace(" | Ateş Hukuk Bürosu İstanbul & İzmir", "").strip()
                    konular.append(baslik.lower())
            except:
                pass
    return konular

# ── Web search ile güncel konu bul ───────────────────────────────────────────

def guncel_konu_bul() -> dict:
    """Mevcut bloglarla çakışmayan rastgele konu seçer. %20 ihtimalle Yargıtay modu."""
    mevcut = mevcut_blog_konulari()
    print(f"📂 Mevcut blog sayısı: {len(mevcut)}")

    # %20 ihtimalle Yargıtay içtihadı
    if random.random() < 0.20:
        print("⚖️  Yargıtay içtihadı modu seçildi!")
        return {"konu": "YARGITAY_ICTIHAT", "kategori": "Yargıtay Kararları"}

    # Mevcut bloglarla çakışmayan konu bul
    deneme = 0
    while deneme < 10:
        secim = random.choice(KONULAR)
        konu_lower = secim["konu"].lower()
        cakisma = False
        for mevcut_konu in mevcut:
            ortak = set(konu_lower.split()) & set(mevcut_konu.split())
            if len(ortak) >= 3:
                cakisma = True
                break
        if not cakisma:
            print(f"📝 Seçilen konu: {secim['konu']}")
            return secim
        deneme += 1

    # Tüm konular işlendiyse rastgele seç
    return random.choice(KONULAR)


# ── Gemini API çağrısı ────────────────────────────────────────────────────────

def blog_uret(konu: str, kategori: str) -> dict:
    sistem = """Sen Türk hukuku alanında 20 yıllık deneyime sahip, aynı zamanda SEO uzmanı bir hukuk yazarısın.
Ateş Hukuk Bürosu (İstanbul Kartal, Kuruluş 1969) adına yazıyorsun.

TEMEL KURALLAR:
- Yanıtını YALNIZCA geçerli JSON olarak ver. Hiçbir ek açıklama, markdown bloğu veya backtick ekleme.
- JSON şeması (tüm alanlar zorunlu):
{
  "baslik": "55-60 karakter, anahtar kelime içeren SEO başlığı",
  "ozet": "150-160 karakter, merak uyandıran SEO meta açıklaması",
  "keywords": "8-10 adet virgülle ayrılmış long-tail anahtar kelime",
  "bolumler": [
    { "id": "bolum-slug", "baslik": "Bölüm Başlığı", "icerik": "<p>...</p> formatında zengin HTML içerik" }
  ],
  "sss": [
    { "soru": "...", "cevap": "..." }
  ],
  "cta_metin": "Bu konuda hukuki destek için özelleştirilmiş 1 cümle"
}

İÇERİK KALİTE KURALLARI:
- 1200-1800 kelime arasında kapsamlı Türkçe yazı (minimum 3000 karakter)
- En az 6 bölüm: çarpıcı giriş, 4 ana bölüm, güçlü sonuç
- SSS: 5-6 gerçekçi soru-cevap (vatandaşların gerçekten sorduğu sorular)
- Her bölüm 2-3 paragraf içermeli
- Somut örnekler ve senaryolar kullan ("Örneğin, bir işçi...")
- Okuyucuya doğrudan hitap et ("Eğer bu durumla karşılaştıysanız...")

HUKUK DOĞRULUĞU KURALLARI (ÇOK ÖNEMLİ):
- Türk mevzuatına dayandır: TMK, TCK, İş Kanunu (4857), HMK, CMK, TBK, TTK vb. ilgili kanun maddesini belirt
- Yargıtay kararlarına atıf yaparken "Yargıtay [Daire] kararları doğrultusunda" veya "yerleşik Yargıtay içtihadına göre" ifadelerini kullan
- Hukuki terimleri ilk kullanımda parantez içinde açıkla: "zamanaşımı (hak düşürücü süre)"
- Güncel mevzuat değişikliklerini belirt (varsa)

YASAL UYARI (her yazıya eklenecek — bunu bolumler içinde son bölüm olarak ekle):
{ "id": "yasal-uyari", "baslik": "Önemli Yasal Uyarı", "icerik": "<div class=\"info-box\"><p>⚖️ <strong>Bu makale yalnızca genel bilgilendirme amaçlıdır ve hukuki tavsiye niteliği taşımaz.</strong> Türk hukuku sık değişen bir alandır; yazıdaki bilgiler yayın tarihi itibarıyla geçerlidir. Somut hukuki sorunlarınızda hak kaybına uğramamak için mutlaka alanında uzman bir avukattan profesyonel destek alınız. Ateş Hukuk Bürosu olarak İstanbul ve İzmir ofislerimizden size yardımcı olmaktan memnuniyet duyarız.</p></div>" }

HTML KULLANIMI:
- <strong> ile önemli terimleri vurgula
- <ul><li> ile madde listelerini göster  
- blockquote ile önemli hukuki ilkeleri vurgula
- <div class="info-box"> ile dikkat çekilecek uyarıları göster
- <div class="yargitay-card"><div class="karar-no">İlgili Mevzuat</div><p>...</p></div> ile kanun maddelerini göster
"""

    # Model ismini en kararlı ve hızlı olan flash modeline çektik
    model = genai.GenerativeModel(
        model_name='gemini-1.5-flash', 
        system_instruction=sistem,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json", 
            temperature=0.7,
        )
    )

    prompt = f"Konu: {konu}\nKategori: {kategori}"

    try:
        response = model.generate_content(
            prompt, 
            request_options={"timeout": 180} 
        )
        raw = response.text.strip()
        return json.loads(raw)
    
    except json.JSONDecodeError:
        print("⚠️  JSON formatı geçerli değil, düzeltiliyor...")
        # JSON'u düzeltme isteği için de flash modeli
        fix_model = genai.GenerativeModel(
            model_name='gemini-1.5-flash',
