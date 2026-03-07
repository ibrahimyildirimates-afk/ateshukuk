#!/usr/bin/env python3
"""
Blog klasöründeki tüm HTML dosyalarını tarar,
index.html'de kartı olmayanları otomatik ekler.
"""

import os
import re

BLOG_DIR = "blog"
INDEX_FILE = "index.html"
SKIP_FILES = {"blog-sablon.html"}

def blog_meta_oku(dosya_yolu: str) -> dict | None:
    """Blog HTML dosyasından başlık, özet ve kategori çeker."""
    try:
        with open(dosya_yolu, "r", encoding="utf-8") as f:
            icerik = f.read()

        # Başlık
        title = re.search(r"<title>(.*?)\s*\|", icerik)
        baslik = title.group(1).strip() if title else None

        # Meta description = özet
        desc = re.search(r'<meta name="description" content="([^"]+)"', icerik)
        ozet = desc.group(1).strip() if desc else ""

        # Kategori (article:section veya ilk kategori span'ı)
        kat = re.search(r'<meta property="article:section" content="([^"]+)"', icerik)
        if not kat:
            kat = re.search(r'<span class="text-ates-gold[^"]*"[^>]*>([^<]+)</span>', icerik)
        kategori = kat.group(1).strip() if kat else "Hukuki Blog"

        if not baslik:
            return None

        return {"baslik": baslik, "ozet": ozet[:160], "kategori": kategori}
    except Exception as e:
        print(f"  ⚠️  {dosya_yolu} okunamadı: {e}")
        return None


def index_guncelle(yeni_bloglar: list):
    """Eksik blog kartlarını index.html'e ekler."""
    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        icerik = f.read()

    eklenen = 0
    for slug, meta in yeni_bloglar:
        kart = f"""                <div class="bg-white blog-card shadow-lg border-t-4 border-ates-navy p-8">
                    <span class="text-ates-gold text-[10px] font-bold uppercase tracking-widest">{meta['kategori']}</span>
                    <h4 class="text-xl font-bold mt-2 mb-4 text-ates-navy leading-tight">{meta['baslik']}</h4>
                    <p class="text-gray-500 text-sm mb-6 line-clamp-3 italic">{meta['ozet']}</p>
                    <a href="/blog/{slug}" class="text-ates-navy font-bold text-xs uppercase border-b border-ates-gold">Devamı →</a>
                </div>"""

        # id="blog" section'ına ekle
        blog_start = icerik.find('id="blog"')
        if blog_start == -1:
            print("❌ id='blog' bulunamadı!")
            return

        section_end = icerik.find('</section>', blog_start)
        onceki = icerik[:section_end]
        son_div = onceki.rfind('</div>')

        icerik = icerik[:son_div] + kart + "\n            " + icerik[son_div:]
        eklenen += 1
        print(f"  ✅ Kart eklendi: {meta['baslik'][:60]}")

    if eklenen > 0:
        with open(INDEX_FILE, "w", encoding="utf-8") as f:
            f.write(icerik)
        print(f"\n✅ index.html güncellendi — {eklenen} yeni kart eklendi.")
    else:
        print("✅ index.html zaten güncel, değişiklik yok.")


def main():
    if not os.path.exists(BLOG_DIR):
        print("❌ blog/ klasörü bulunamadı.")
        return

    if not os.path.exists(INDEX_FILE):
        print("❌ index.html bulunamadı.")
        return

    # index.html'deki mevcut blog linklerini al
    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        index_icerik = f.read()

    mevcut_linkler = set(re.findall(r'href="/blog/([^"]+)"', index_icerik))
    print(f"📋 index.html'de mevcut {len(mevcut_linkler)} blog kartı var.")

    # blog/ klasöründeki tüm dosyaları tara
    blog_dosyalari = [
        f for f in os.listdir(BLOG_DIR)
        if f.endswith(".html") and f not in SKIP_FILES
    ]
    print(f"📂 blog/ klasöründe {len(blog_dosyalari)} HTML dosyası var.")

    # Eksik olanları bul
    eksik = []
    for dosya in sorted(blog_dosyalari):
        if dosya not in mevcut_linkler:
            meta = blog_meta_oku(os.path.join(BLOG_DIR, dosya))
            if meta:
                print(f"  ➕ Eksik: {dosya}")
                eksik.append((dosya, meta))

    if not eksik:
        print("\n✅ Tüm bloglar zaten index.html'de mevcut.")
        return

    print(f"\n🔄 {len(eksik)} eksik blog kartı eklenecek...")
    index_guncelle(eksik)


if __name__ == "__main__":
    main()
