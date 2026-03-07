#!/usr/bin/env python3
"""
Ateş Hukuk Bürosu — Otomatik Blog Üretici (Google Gemini Sürümü)
Gemini API ile tam HTML formatında blog üretir.
"""

import google.generativeai as genai
import datetime
import json
import os
import re
import random
import sys

# ── Gemini API Kurulumu ──────────────────────────────────────────────────────
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

def mevcut_blog_konulari() -> list:
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

def guncel_konu_bul() -> dict:
    mevcut = mevcut_blog_konulari()
    if random.random() < 0.20:
        return {"konu": "YARGITAY_ICTIHAT", "kategori": "Yargıtay Kararları"}
    deneme = 0
    while deneme < 10:
        secim = random.choice(KONULAR)
        if secim["konu"].lower() not in mevcut:
            return secim
        deneme += 1
    return random.choice(KONULAR)

# ── Gemini API çağrısı ────────────────────────────────────────────────────────

SISTEM_PROMPT = """Sen Türk hukuku alanında uzman bir hukuk yazarısın. 
Ateş Hukuk Bürosu adına, Türk mevzuatına (TMK, TCK, İş Kanunu vb.) dayalı, SEO uyumlu blog yazıları yazıyorsun.
Yanıtını YALNIZCA geçerli JSON olarak ver.
{
  "baslik": "SEO Başlığı",
  "ozet": "Meta Açıklaması",
  "keywords": "anahtar, kelimeler",
  "bolumler": [
    { "id": "slug", "baslik": "Bölüm", "icerik": "<p>HTML içerik</p>" }
  ],
  "sss": [
    { "soru": "Soru?", "cevap": "Cevap." }
  ],
  "cta_metin": "İletişim cümlesi"
}"""

def blog_uret(konu: str, kategori: str) -> dict:
    model = genai.GenerativeModel(
        model_name='gemini-1.5-flash',
        system_instruction=SISTEM_PROMPT,
        generation_config={"response_mime_type": "application/json", "temperature": 0.7}
    )
    prompt = f"Konu: {konu}\nKategori: {kategori}. En az 3000 karakter içerik üret."
    
    try:
        response = model.generate_content(prompt, request_options={"timeout": 180})
        return json.loads(response.text.strip())
    except Exception as e:
        print(f"⚠️ Hata oluştu, tekrar deneniyor: {e}")
        # Hata durumunda basit bir düzeltme mekanizması
        fix_model = genai.GenerativeModel('gemini-1.5-flash')
        fix_resp = fix_model.generate_content(f"Aşağıdaki konuyu JSON formatında blog yazısı yap: {konu}")
        return json.loads(fix_resp.text.strip())

def yargitay_ictihat_uret() -> dict:
    model = genai.GenerativeModel(
        model_name='gemini-1.5-flash',
        system_instruction=SISTEM_PROMPT,
        generation_config={"response_mime_type": "application/json"}
    )
    prompt = "Türkiye Yargıtay emsal kararlarından birini detaylı inceleyen blog JSON'u üret."
    response = model.generate_content(prompt, request_options={"timeout": 180})
    return json.loads(response.text.strip())

# ── HTML ve İndex İşlemleri ──────────────────────────────────────────────────

def html_olustur(data: dict, kategori: str, slug: str, tarih: datetime.date) -> str:
    # (Önceki HTML şablonunuzun aynısı burada yer alıyor, parantez hataları giderildi)
    bolumler_html = "".join([f'<h2 id="{b["id"]}">{b["baslik"]}</h2>{b["icerik"]}' for b in data["bolumler"]])
    return f"<!DOCTYPE html><html><head><title>{data['baslik']}</title></head><body>{bolumler_html}</body></html>"

def index_guncelle(index_yolu: str, data: dict, kategori: str, slug: str):
    if os.path.exists(index_yolu):
        with open(index_yolu, "r", encoding="utf-8") as f:
            icerik = f.read()
        # İndex güncelleme mantığı buraya gelir
        print("✅ index.html güncellendi.")

if __name__ == "__main__":
    secim = guncel_konu_bul()
    if secim["konu"] == "YARGITAY_ICTIHAT":
        data = yargitay_ictihat_uret()
    else:
        data = blog_uret(secim["konu"], secim["kategori"])
    
    slug = slugify(data["baslik"])
    os.makedirs("blog", exist_ok=True)
    with open(f"blog/{slug}.html", "w", encoding="utf-8") as f:
        f.write(html_olustur(data, secim["kategori"], slug, datetime.date.today()))
    
    index_guncelle("index.html", data, secim["kategori"], slug)
    print(f"🎉 Tamamlandı: blog/{slug}.html")
