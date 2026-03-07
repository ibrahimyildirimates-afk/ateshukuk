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
- <blockquote> ile önemli hukuki ilkeleri vurgula
- <div class="info-box"> ile dikkat çekilecek uyarıları göster
- <div class="yargitay-card"><div class="karar-no">İlgili Mevzuat</div><p>...</p></div> ile kanun maddelerini göster
"""

    model = genai.GenerativeModel(
        model_name='gemini-1.5-pro', # Kapsamlı metinler için en iyi model
        system_instruction=sistem,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json", # Kesin JSON formatlaması
            temperature=0.7,
        )
    )

    prompt = f"Konu: {konu}\nKategori: {kategori}"

    try:
        response = model.generate_content(
            prompt, 
            request_options={"timeout": 180} # 3 dakikalık zaman aşımı süresi
        )
        raw = response.text.strip()
        return json.loads(raw)
    
    except json.JSONDecodeError:
        print("⚠️  JSON formatı geçerli değil, düzeltiliyor...")
        # JSON'u düzeltme isteği
        fix_model = genai.GenerativeModel(
            model_name='gemini-1.5-pro',
            generation_config=genai.GenerationConfig(response_mime_type="application/json")
        )
        fix_resp = fix_model.generate_content(
            f"Bu JSON bozuk, TAM ve GEÇERLİ JSON olarak düzelt, sadece JSON dön:\n{response.text[:8000]}"
        )
        return json.loads(fix_resp.text.strip())


def yargitay_ictihat_uret() -> dict:
    """Gemini ile güncel Yargıtay içtihadı araştırır ve özel format üretir."""
    sistem = """Sen Türk hukuku uzmanısın. Güncel Yargıtay kararlarını araştırıp analiz ediyorsun.
Yanıtını YALNIZCA geçerli JSON olarak ver:
{
  "baslik": "Yargıtay Kararı: [konu] - [yıl]",
  "ozet": "150-160 karakter SEO özeti",
  "keywords": "8-10 anahtar kelime",
  "bolumler": [
    {"id": "karar-ozeti", "baslik": "Kararın Özeti", "icerik": "HTML"},
    {"id": "konu-hukuku", "baslik": "İlgili Hukuki Düzenleme", "icerik": "HTML"},
    {"id": "kararın-onemi", "baslik": "Kararın Önemi ve Etkisi", "icerik": "HTML"},
    {"id": "pratik-sonuclar", "baslik": "Vatandaşlar İçin Pratik Sonuçlar", "icerik": "HTML"},
    {"id": "benzer-kararlar", "baslik": "Benzer Yargıtay Kararları", "icerik": "HTML"},
    {"id": "sss-kararlar", "baslik": "Sık Sorulan Sorular", "icerik": "HTML"},
    {"id": "yasal-uyari", "baslik": "Önemli Yasal Uyarı", "icerik": "<div class=\"info-box\"><p>⚖️ <strong>Bu makale yalnızca bilgilendirme amaçlıdır.</strong> Hukuki tavsiye niteliği taşımaz. Somut durumunuz için uzman avukat desteği alınız.</p></div>"}
  ],
  "sss": [
    {"soru": "...", "cevap": "..."}
  ],
  "cta_metin": "Bu Yargıtay kararı hakkında hukuki danışmanlık alın."
}
Her bölüm en az 4 paragraf, toplam 1800-2500 kelime olsun. Gerçek veya gerçekçi Yargıtay kararı kullan."""

    model = genai.GenerativeModel(
        model_name='gemini-1.5-pro',
        system_instruction=sistem,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            temperature=0.7,
        )
    )

    prompt = "Türkiye Yargıtay 2025-2026 önemli emsal kararlar - vatandaşları en çok etkileyen güncel bir kararı detaylı incele ve JSON formatında üret"

    try:
        response = model.generate_content(
            prompt,
            request_options={"timeout": 180}
        )
        return json.loads(response.text.strip())
    except Exception as e:
        print(f"⚠️ Yargıtay içtihat üretiminde hata: {e}")
        # Hata anında rastgele standart bir konu üretmeye geri dönmesi için
        return blog_uret(random.choice(KONULAR)["konu"], random.choice(KONULAR)["kategori"])


# ── HTML dosyası oluştur ──────────────────────────────────────────────────────

def html_olustur(data: dict, kategori: str, slug: str, tarih: datetime.date) -> str:
    bolumler_html = ""
    for b in data["bolumler"]:
        bolumler_html += f'\n                        <h2 id="{b["id"]}">{b["baslik"]}</h2>\n'
        bolumler_html += f'                        {b["icerik"]}\n'

    toc_links = ""
    mobil_toc = ""
    for b in data["bolumler"]:
        toc_links += f'                                <a href="#{b["id"]}">{b["baslik"]}</a>\n'
        mobil_toc += f'                            <a href="#{b["id"]}" class="block text-sm text-gray-600 hover:text-ates-gold py-1">{b["baslik"]}</a>\n'

    sss_html = ""
    sss_schema = []
    for s in data["sss"]:
        sss_html += f"""
                            <div class="faq-item">
                                <div class="faq-question" onclick="toggleFaq(this)">
                                    <span>{s["soru"]}</span>
                                    <span class="faq-icon text-ates-gold text-xl">+</span>
                                </div>
                                <div class="faq-answer">{s["cevap"]}</div>
                            </div>"""
        sss_schema.append({
            "@type": "Question",
            "name": s["soru"],
            "acceptedAnswer": {"@type": "Answer", "text": s["cevap"]}
        })

    iso_tarih = tarih.strftime("%Y-%m-%dT09:00:00+03:00")
    tr_tarih = turkce_tarih(tarih)
    url = f"https://www.ateshukukburosu.com/blog/{slug}.html"

    article_body_for_timing = bolumler_html + sss_html
    sure = okuma_suresi(article_body_for_timing)

    schema_faq = json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": sss_schema}, ensure_ascii=False, indent=2)
    schema_article = json.dumps({
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": data["baslik"],
        "description": data["ozet"],
        "datePublished": iso_tarih,
        "dateModified": iso_tarih,
        "author": {"@type": "Organization", "name": "Ateş Hukuk Bürosu", "url": "https://www.ateshukukburosu.com"},
        "publisher": {"@type": "Organization", "name": "Ateş Hukuk Bürosu", "logo": {"@type": "ImageObject", "url": "https://www.ateshukukburosu.com/assets/logo.png"}},
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
        "articleSection": kategori,
        "inLanguage": "tr-TR"
    }, ensure_ascii=False, indent=2)

    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{data["baslik"]} | Ateş Hukuk Bürosu İstanbul & İzmir</title>
    <meta name="description" content="{data["ozet"]}">
    <meta name="keywords" content="{data["keywords"]}">
    <meta name="author" content="Ateş Hukuk Bürosu">
    <meta name="robots" content="index, follow">
    <link rel="canonical" href="{url}">
    <meta property="og:type" content="article">
    <meta property="og:url" content="{url}">
    <meta property="og:title" content="{data["baslik"]} | Ateş Hukuk Bürosu">
    <meta property="og:description" content="{data["ozet"]}">
    <meta property="og:image" content="https://www.ateshukukburosu.com/assets/og-image.jpg">
    <meta property="og:locale" content="tr_TR">
    <meta property="og:site_name" content="Ateş Hukuk Bürosu">
    <meta property="article:published_time" content="{iso_tarih}">
    <meta property="article:author" content="Ateş Hukuk Bürosu">
    <meta property="article:section" content="{kategori}">
    <script type="application/ld+json">{schema_article}</script>
    <script type="application/ld+json">{schema_faq}</script>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;600&family=Playfair+Display:wght@500;700&display=swap" rel="stylesheet">
    <script>
        tailwind.config = {{
            theme: {{
                extend: {{
                    colors: {{ 'ates-navy': '#001f3f', 'ates-gold': '#C5A065' }},
                    fontFamily: {{ 'heading': ['Playfair Display', 'serif'], 'body': ['Montserrat', 'sans-serif'] }}
                }}
            }}
        }}
    </script>
    <style>
        body {{ font-family: 'Montserrat', sans-serif; scroll-behavior: smooth; }}
        h1, h2, h3, h4 {{ font-family: 'Playfair Display', serif; }}
        .article-body h2 {{ font-size: 1.45rem; font-weight: 700; color: #001f3f; margin: 2.5rem 0 1rem; padding-bottom: 0.5rem; border-bottom: 2px solid #f3f4f6; }}
        .article-body h3 {{ font-size: 1.1rem; font-weight: 600; color: #001f3f; margin: 1.75rem 0 0.75rem; }}
        .article-body p {{ color: #374151; line-height: 1.95; margin-bottom: 1.25rem; font-size: 0.97rem; }}
        .article-body ul {{ list-style: none; padding-left: 0; margin-bottom: 1.25rem; }}
        .article-body ul li {{ position: relative; padding-left: 1.5rem; margin-bottom: 0.6rem; color: #374151; line-height: 1.8; font-size: 0.97rem; }}
        .article-body ul li::before {{ content: ''; position: absolute; left: 0; top: 0.65rem; width: 8px; height: 8px; border-radius: 50%; background-color: #C5A065; }}
        .article-body blockquote {{ border-left: 4px solid #C5A065; background: #fafafa; padding: 1.25rem 1.5rem; margin: 1.75rem 0; font-style: italic; color: #4b5563; font-size: 0.95rem; line-height: 1.85; }}
        .article-body .info-box {{ background: #fff7ed; border: 1px solid #fed7aa; border-left: 4px solid #C5A065; padding: 1.25rem 1.5rem; margin: 1.5rem 0; border-radius: 0 4px 4px 0; font-size: 0.93rem; color: #374151; line-height: 1.8; }}
        .article-body .yargitay-card {{ background: #f8f9fa; border: 1px solid #e5e7eb; border-left: 4px solid #001f3f; padding: 1.25rem 1.5rem; margin: 1.25rem 0; border-radius: 0 4px 4px 0; }}
        .article-body .yargitay-card .karar-no {{ font-size: 0.75rem; font-weight: 700; color: #C5A065; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.5rem; }}
        .article-body .yargitay-card p {{ font-size: 0.88rem; color: #4b5563; margin-bottom: 0; }}
        .faq-item {{ border-bottom: 1px solid #e5e7eb; }}
        .faq-question {{ cursor: pointer; padding: 1rem 0; display: flex; justify-content: space-between; align-items: center; font-weight: 600; font-size: 0.95rem; color: #001f3f; }}
        .faq-answer {{ padding-bottom: 1rem; font-size: 0.9rem; color: #374151; line-height: 1.8; display: none; }}
        .faq-answer.open {{ display: block; }}
        #toc a {{ color: #374151; font-size: 0.82rem; text-decoration: none; transition: color 0.2s; display: block; padding: 0.2rem 0; }}
        #toc a:hover, #toc a.toc-active {{ color: #C5A065; font-weight: 600; }}
    </style>
</head>
<body class="bg-gray-50 text-ates-navy">

    <header class="bg-ates-navy text-white py-4 sticky top-0 z-50 shadow-2xl border-b border-ates-gold/30">
        <div class="container mx-auto px-6 flex items-center justify-between">
            <a href="/" class="flex flex-col border-l-4 border-ates-gold pl-4">
                <span class="text-2xl font-bold tracking-tighter leading-none uppercase">Ateş Hukuk</span>
                <span class="text-[10px] tracking-[0.3em] text-ates-gold uppercase mt-1 font-bold">Bürosu • Kuruluş: 1969</span>
            </a>
            <nav class="hidden lg:flex space-x-8 text-xs font-semibold uppercase tracking-widest">
                <a href="/" class="hover:text-ates-gold transition">Ana Sayfa</a>
                <a href="/#hakkimizda" class="hover:text-ates-gold transition">Biz Kimiz</a>
                <a href="/#hizmetlerimiz" class="hover:text-ates-gold transition">Hizmetlerimiz</a>
                <a href="/#blog" class="hover:text-ates-gold transition">Hukuki Blog</a>
                <a href="/#ekibimiz" class="hover:text-ates-gold transition">Ekibimiz</a>
                <a href="/#iletisim" class="bg-ates-gold text-white px-6 py-2 rounded hover:bg-white hover:text-ates-navy transition shadow-lg">İletişim</a>
            </nav>
            <button id="menu-btn" class="lg:hidden flex flex-col gap-1.5 p-2 focus:outline-none" aria-label="Menüyü Aç">
                <span class="block w-6 h-0.5 bg-white transition-all duration-300" id="bar1"></span>
                <span class="block w-6 h-0.5 bg-white transition-all duration-300" id="bar2"></span>
                <span class="block w-6 h-0.5 bg-white transition-all duration-300" id="bar3"></span>
            </button>
        </div>
        <div id="mobile-menu" class="hidden lg:hidden bg-ates-navy border-t border-ates-gold/30 px-6 pb-6 pt-4">
            <nav class="flex flex-col space-y-4 text-xs font-semibold uppercase tracking-widest">
                <a href="/" class="hover:text-ates-gold transition mobile-link">Ana Sayfa</a>
                <a href="/#hakkimizda" class="hover:text-ates-gold transition mobile-link">Biz Kimiz</a>
                <a href="/#hizmetlerimiz" class="hover:text-ates-gold transition mobile-link">Hizmetlerimiz</a>
                <a href="/#blog" class="hover:text-ates-gold transition mobile-link">Hukuki Blog</a>
                <a href="/#ekibimiz" class="hover:text-ates-gold transition mobile-link">Ekibimiz</a>
                <a href="/#iletisim" class="bg-ates-gold text-white px-6 py-3 text-center rounded hover:bg-white hover:text-ates-navy transition mobile-link">İletişim</a>
            </nav>
        </div>
    </header>
    <script>
        const menuBtn = document.getElementById('menu-btn');
        const mobileMenu = document.getElementById('mobile-menu');
        const bar1 = document.getElementById('bar1'), bar2 = document.getElementById('bar2'), bar3 = document.getElementById('bar3');
        menuBtn.addEventListener('click', () => {{
            mobileMenu.classList.toggle('hidden');
            bar1.classList.toggle('rotate-45'); bar1.classList.toggle('translate-y-2');
            bar2.classList.toggle('opacity-0');
            bar3.classList.toggle('-rotate-45'); bar3.classList.toggle('-translate-y-2');
        }});
        document.querySelectorAll('.mobile-link').forEach(l => l.addEventListener('click', () => {{
            mobileMenu.classList.add('hidden');
            bar1.classList.remove('rotate-45','translate-y-2');
            bar2.classList.remove('opacity-0');
            bar3.classList.remove('-rotate-45','-translate-y-2');
        }}));
    </script>

    <div class="bg-white border-b border-gray-100 py-3">
        <div class="container mx-auto px-6 text-xs text-gray-400 uppercase tracking-widest">
            <a href="/" class="hover:text-ates-gold transition">Ana Sayfa</a>
            <span class="mx-2">›</span>
            <a href="/#blog" class="hover:text-ates-gold transition">Blog</a>
            <span class="mx-2">›</span>
            <span class="text-ates-navy">{data["baslik"][:50]}</span>
        </div>
    </div>

    <main class="py-20">
        <div class="container mx-auto px-6 max-w-5xl">
            <div class="flex flex-col lg:flex-row gap-12">
                <div class="lg:w-2/3">
                    <div class="mb-8">
                        <span class="text-ates-gold text-[10px] font-bold uppercase tracking-widest">{kategori}</span>
                        <h1 class="text-3xl md:text-4xl font-bold text-ates-navy mt-3 mb-5 leading-tight">{data["baslik"]}</h1>
                        <div class="flex flex-wrap items-center gap-6 text-xs text-gray-400 uppercase tracking-widest border-b border-gray-100 pb-6">
                            <span>📅 {tr_tarih}</span>
                            <span>✍️ Ateş Hukuk Bürosu</span>
                            <span>⏱ {sure} dk okuma</span>
                        </div>
                    </div>

                    <div class="lg:hidden bg-gray-50 border border-gray-200 border-l-4 border-l-ates-gold p-6 my-8 rounded-r">
                        <p class="text-sm font-bold uppercase tracking-widest text-ates-navy mb-4">Makale İçeriği</p>
                        <nav class="space-y-1">
{mobil_toc}                        </nav>
                    </div>

                    <article class="article-body">
{bolumler_html}
                        <h2 id="sss">Sık Sorulan Sorular</h2>
                        <div class="space-y-0 border-t border-gray-200 mt-4">
{sss_html}
                        </div>

                        <p class="text-xs text-gray-400 italic mt-8">Yasal Uyarı: Bu yazı yalnızca bilgilendirme amaçlıdır ve hukuki tavsiye niteliği taşımaz. Karşılaştığınız hukuki sorunlarda hak kaybı yaşamamak için mutlaka uzman bir avukattan profesyonel destek alınız.</p>
                    </article>

                    <div class="bg-ates-navy text-white p-10 mt-16 border-l-8 border-ates-gold">
                        <h3 class="text-2xl font-bold mb-4 font-heading">Hukuki Danışmanlık Alın</h3>
                        <p class="text-gray-300 mb-6 text-sm leading-relaxed">{data["cta_metin"]}</p>
                        <a href="tel:+905326021201" class="inline-block bg-ates-gold text-white px-8 py-3 font-bold uppercase tracking-widest text-sm hover:bg-white hover:text-ates-navy transition">
                            📞 0532 602 12 01
                        </a>
                    </div>

                    <div class="mt-12 pt-8 border-t border-gray-200">
                        <a href="/#blog" class="text-ates-navy font-bold text-xs uppercase tracking-widest border-b border-ates-gold hover:text-ates-gold transition">
                            ← Tüm Blog Yazıları
                        </a>
                    </div>
                </div>

                <aside class="hidden lg:block lg:w-1/3">
                    <div class="sticky top-24">
                        <div class="bg-white border border-gray-200 border-t-4 border-t-ates-navy p-6 shadow-md">
                            <h2 class="text-xs font-bold uppercase tracking-widest text-ates-navy mb-5">Makale İçeriği</h2>
                            <nav id="toc" class="space-y-1">
{toc_links}                            </nav>
                        </div>
                        <div class="bg-ates-navy text-white p-6 mt-6 border-b-4 border-ates-gold shadow-md">
                            <p class="text-ates-gold text-[10px] font-bold uppercase tracking-widest mb-3">Ücretsiz Ön Görüşme</p>
                            <p class="text-sm text-gray-300 mb-4 leading-relaxed">{kategori} alanında uzman görüşü alın.</p>
                            <a href="tel:+905326021201" class="block text-center bg-ates-gold text-white py-3 font-bold text-sm uppercase tracking-wider hover:bg-white hover:text-ates-navy transition">
                                📞 0532 602 12 01
                            </a>
                        </div>
                    </div>
                </aside>
            </div>
        </div>
    </main>

    <script>
        function toggleFaq(el) {{
            const answer = el.nextElementSibling;
            const icon = el.querySelector('.faq-icon');
            answer.classList.toggle('open');
            icon.textContent = answer.classList.contains('open') ? '−' : '+';
        }}
        const sections = document.querySelectorAll('h2[id]');
        const tocLinks = document.querySelectorAll('#toc a');
        const observer = new IntersectionObserver((entries) => {{
            entries.forEach(entry => {{
                if (entry.isIntersecting) {{
                    tocLinks.forEach(l => l.classList.remove('toc-active'));
                    const active = document.querySelector(`#toc a[href="#${{entry.target.id}}"]`);
                    if (active) active.classList.add('toc-active');
                }}
            }});
        }}, {{ rootMargin: '-20% 0px -70% 0px' }});
        sections.forEach(s => observer.observe(s));
    </script>

    <footer class="bg-ates-navy text-white pt-20 pb-10 border-t border-gray-800">
        <div class="container mx-auto px-6 grid md:grid-cols-3 gap-16 text-sm pb-16 border-b border-gray-800">
            <div>
                <h4 class="text-3xl font-bold mb-6 tracking-tighter font-heading uppercase">ATEŞ HUKUK</h4>
                <p class="text-gray-400 leading-relaxed italic text-lg">"1969'dan bugüne, hak ve adaletin izinde yarım asrı geride bıraktık."</p>
            </div>
            <div>
                <h4 class="text-ates-gold font-bold mb-6 uppercase tracking-widest font-heading">İletişim</h4>
                <p>Kartal / İstanbul</p>
                <a href="tel:+905326021201" class="text-xl font-bold mt-4 block text-white hover:text-ates-gold transition">0532 602 12 01</a>
            </div>
            <div>
                <h4 class="text-ates-gold font-bold mb-6 uppercase tracking-widest font-heading">Hızlı Linkler</h4>
                <ul class="space-y-3 uppercase text-[10px] tracking-[0.2em]" style="list-style:none;padding:0">
                    <li><a href="/#hakkimizda" class="hover:text-ates-gold transition">Kurumsal</a></li>
                    <li><a href="/#hizmetlerimiz" class="hover:text-ates-gold transition">Faaliyet Alanları</a></li>
                    <li><a href="/#blog" class="hover:text-ates-gold transition">Hukuki Blog</a></li>
                    <li><a href="/#ekibimiz" class="hover:text-ates-gold transition">Kadromuz</a></li>
                </ul>
            </div>
        </div>
        <div class="text-center mt-10 text-[10px] text-gray-600 uppercase tracking-[0.5em]">
            © {tarih.year} ATEŞ HUKUK BÜROSU | KURULUŞ: 1969
        </div>
    </footer>

</body>
</html>"""

# ── index.html blog kartı ekle ────────────────────────────────────────────────

def index_guncelle(index_yolu: str, data: dict, kategori: str, slug: str):
    with open(index_yolu, "r", encoding="utf-8") as f:
        icerik = f.read()

    # Özeti kısalt
    ozet = data["ozet"][:160] + ("…" if len(data["ozet"]) > 160 else "")

    yeni_kart = f"""                <div class="bg-white blog-card shadow-lg border-t-4 border-ates-navy p-8">
                    <span class="text-ates-gold text-[10px] font-bold uppercase tracking-widest">{kategori}</span>
                    <h4 class="text-xl font-bold mt-2 mb-4 text-ates-navy leading-tight">{data["baslik"]}</h4>
                    <p class="text-gray-500 text-sm mb-6 line-clamp-3 italic">{ozet}</p>
                    <a href="/blog/{slug}.html" class="text-ates-navy font-bold text-xs uppercase border-b border-ates-gold">Devamı →</a>
                </div>"""

    # Sadece blog section içindeki grid'e ekle
    # Blog section'ının benzersiz kapanış işaretçisi
    isaretci = '            </div>\n        </div>\n    </section>\n\n    '
    if isaretci in icerik:
        yeni_icerik = icerik.replace(isaretci, yeni_kart + "\n" + isaretci, 1)
        with open(index_yolu, "w", encoding="utf-8") as f:
            f.write(yeni_icerik)
        print(f"✅ index.html güncellendi — yeni kart blog section'a eklendi.")
    else:
        print("⚠️  index.html'de blog section işaretçisi bulunamadı, kart eklenemedi.")

# ── Ana akış ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Web'den güncel konu bul
    secim = guncel_konu_bul()
    konu = secim["konu"]
    kategori = secim["kategori"]
    print(f"📝 Konu: {konu} ({kategori})")

    # Yargıtay içtihat modu
    if konu == "YARGITAY_ICTIHAT":
        print("⚖️  Yargıtay içtihadı araştırılıyor...")
        data = yargitay_ictihat_uret()
        kategori = "Yargıtay Kararları"
    else:
        # Normal blog üret
        print("⏳ Gemini API'ye bağlanılıyor...")
        data = blog_uret(konu, kategori)

    print(f"✅ Başlık: {data['baslik']}")

    # 3000 karakter kontrolü
    toplam_icerik = " ".join(b.get("icerik","") for b in data.get("bolumler",[]))
    temiz = re.sub(r"<[^>]+>", " ", toplam_icerik)
    karakter = len(temiz.strip())
    print(f"📊 İçerik uzunluğu: {karakter} karakter")
    if karakter < 3000:
        print("⚠️  İçerik 3000 karakterin altında, yeniden üretiliyor...")
        data = blog_uret(konu + " (kapsamlı ve detaylı, en az 3000 karakter)", kategori)

    # Dosya adı
    tarih = datetime.date.today()
    slug = slugify(data["baslik"])
    dosya_adi = f"{slug}.html"

    # blog/ klasörüne kaydet
    os.makedirs("blog", exist_ok=True)
    yol = os.path.join("blog", dosya_adi)
    html = html_olustur(data, kategori, slug, tarih)
    with open(yol, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ Blog dosyası: {yol}")

    # index.html güncelle
    index_yolu = "index.html"
    if os.path.exists(index_yolu):
        index_guncelle(index_yolu, data, kategori, slug)
    else:
        print(f"⚠️  index.html bulunamadı ({index_yolu}), kart eklenemedi.")

    print(f"\n🎉 Tamamlandı! → blog/{dosya_adi}")
