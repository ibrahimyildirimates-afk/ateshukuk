#!/usr/bin/env python3
"""
blog/ klasöründeki tüm HTML dosyalarını tarar,
index.html'de kartı olmayanları otomatik ekler.
"""

import os
import re

BLOG_DIR = "blog"
INDEX_FILE = "index.html"
SKIP_FILES = {"blog-sablon.html"}

def blog_meta_oku(dosya_yolu: str) -> dict | None:
    try:
        with open(dosya_yolu, "r", encoding="utf-8") as f:
            icerik = f.read()

        # Başlık — <title> etiketinden al
        title = re.search(r"<title>(.*?)(?:\s*\||\s*-)", icerik)
        baslik = title.group(1).strip() if title else None

        # Meta description
        desc = re.search(r'<meta name="description" content="([^"]+)"', icerik)
        ozet = desc.group(1).strip()[:160] if desc else ""

        # Kategori
        kat = re.search(r'<meta property="article:section" content="([^"]+)"', icerik)
        if not kat:
            kat = re.search(r'<span class="text-ates-gold[^>]*>([^<]+)</span>', icerik)
        kategori = kat.group(1).strip() if kat else "Hukuki Blog"

        if not baslik:
            return None

        return {"baslik": baslik, "ozet": ozet, "kategori": kategori}
    except Exception as e:
        print(f"  ⚠️  {dosya_yolu} okunamadı: {e}")
        return None


def kart_ekle(icerik: str, slug: str, meta: dict) -> str:
    """Blog kartını index.html'deki blog section'ına ekler."""
    kart = f"""                <div class="bg-white blog-card shadow-lg border-t-4 border-ates-navy p-8">
                    <span class="text-ates-gold text-[10px] font-bold uppercase tracking-widest">{meta['kategori']}</span>
                    <h4 class="text-xl font-bold mt-2 mb-4 text-ates-navy leading-tight">{meta['baslik']}</h4>
                    <p class="text-gray-500 text-sm mb-6 line-clamp-3 italic">{meta['ozet']}</p>
                    <a href="/blog/{slug}" class="text-ates-navy font-bold text-xs uppercase border-b border-ates-gold">Devamı →</a>
                </div>"""

    # id="blog" section'ını bul
    blog_start = icerik.find('id="blog"')
    if blog_start == -1:
        print("  ❌ id='blog' bulunamadı!")
        return icerik

    # Bu section'ın kapanış </section> etiketini bul
    section_end = icerik.find('</section>', blog_start)
    if section_end == -1:
        print("  ❌ Blog section kapanışı bulunamadı!")
        return icerik

    # section_end'den önceki son </div>'i bul — burası grid kapanışı
    onceki = icerik[:section_end]
    son_div = onceki.rfind('</div>')

    return icerik[:son_div] + kart + "\n            " + icerik[son_div:]


def main():
    if not os.path.exists(BLOG_DIR):
        print("❌ blog/ klasörü bulunamadı.")
        return
    if not os.path.exists(INDEX_FILE):
        print("❌ index.html bulunamadı.")
        return

    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        icerik = f.read()

    # index.html'deki mevcut blog linklerini al
    mevcut = set(re.findall(r'href="/blog/([^"]+)"', icerik))
    print(f"📋 index.html'de {len(mevcut)} blog kartı mevcut.")

    # blog/ klasöründeki dosyaları tara
    blog_dosyalari = sorted([
        f for f in os.listdir(BLOG_DIR)
        if f.endswith(".html") and f not in SKIP_FILES
    ])
    print(f"📂 blog/ klasöründe {len(blog_dosyalari)} dosya var.")

    eklenen = 0
    for dosya in blog_dosyalari:
        if dosya in mevcut:
            continue  # Zaten var
        
        meta = blog_meta_oku(os.path.join(BLOG_DIR, dosya))
        if not meta:
            print(f"  ⚠️  {dosya} meta verisi okunamadı, atlandı.")
            continue

        icerik = kart_ekle(icerik, dosya, meta)
        eklenen += 1
        print(f"  ✅ Eklendi: {meta['baslik'][:60]}")

    if eklenen > 0:
        with open(INDEX_FILE, "w", encoding="utf-8") as f:
            f.write(icerik)
        print(f"\n✅ {eklenen} yeni kart eklendi.")
    else:
        print("\n✅ Tüm bloglar zaten index'te, değişiklik yok.")


if __name__ == "__main__":
    main()
