#!/usr/bin/env python3
"""
blog/ klasöründeki tüm HTML dosyalarını tarar,
index.html'de kartı olmayanları otomatik ekler.
"""
import os, re

BLOG_DIR = "blog"
INDEX_FILE = "index.html"
SKIP_FILES = {"blog-sablon.html"}

def blog_meta_oku(dosya_yolu):
    try:
        with open(dosya_yolu, "r", encoding="utf-8") as f:
            ic = f.read()
        title = re.search(r"<title>(.*?)(?:\s*\||\s*-)", ic)
        baslik = title.group(1).strip() if title else None
        desc = re.search(r'<meta name="description" content="([^"]+)"', ic)
        ozet = desc.group(1).strip()[:160] if desc else ""
        kat = re.search(r'<meta property="article:section" content="([^"]+)"', ic)
        if not kat:
            kat = re.search(r'<span class="text-ates-gold[^>]*>([^<]+)</span>', ic)
        kategori = kat.group(1).strip() if kat else "Hukuki Blog"
        return {"baslik": baslik, "ozet": ozet, "kategori": kategori} if baslik else None
    except Exception as e:
        print(f"  ⚠️  {dosya_yolu}: {e}")
        return None

def son_kart_sonu(icerik):
    """Son blog kartının kapanış </div>'inden sonraki pozisyonu döner."""
    kartlar = list(re.finditer(r'<div class="bg-white blog-card', icerik))
    if not kartlar:
        return -1
    son_kart_start = kartlar[-1].start()
    return icerik.find('</div>', son_kart_start) + 6

def main():
    if not os.path.exists(BLOG_DIR) or not os.path.exists(INDEX_FILE):
        print("❌ blog/ veya index.html bulunamadı.")
        return

    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        icerik = f.read()

    mevcut = set(re.findall(r'href="/blog/([^"]+)"', icerik))
    print(f"📋 index.html'de {len(mevcut)} kart mevcut.")

    dosyalar = sorted([f for f in os.listdir(BLOG_DIR)
                       if f.endswith(".html") and f not in SKIP_FILES])
    print(f"📂 blog/ klasöründe {len(dosyalar)} dosya var.")

    eklenen = 0
    for dosya in dosyalar:
        if dosya in mevcut:
            continue
        meta = blog_meta_oku(os.path.join(BLOG_DIR, dosya))
        if not meta:
            print(f"  ⚠️  {dosya} atlandı.")
            continue

        kart = f"""
                <div class="bg-white blog-card shadow-lg border-t-4 border-ates-navy p-8">
                    <span class="text-ates-gold text-[10px] font-bold uppercase tracking-widest">{meta['kategori']}</span>
                    <h4 class="text-xl font-bold mt-2 mb-4 text-ates-navy leading-tight">{meta['baslik']}</h4>
                    <p class="text-gray-500 text-sm mb-6 line-clamp-3 italic">{meta['ozet']}</p>
                    <a href="/blog/{dosya}" class="text-ates-navy font-bold text-xs uppercase border-b border-ates-gold">Devamı →</a>
                </div>"""

        insert = son_kart_sonu(icerik)
        if insert == -1:
            print("❌ Blog kartı bulunamadı!")
            return
        icerik = icerik[:insert] + kart + icerik[insert:]
        eklenen += 1
        print(f"  ✅ Eklendi: {meta['baslik'][:60]}")

    if eklenen > 0:
        with open(INDEX_FILE, "w", encoding="utf-8") as f:
            f.write(icerik)
        print(f"\n✅ {eklenen} yeni kart eklendi.")
    else:
        print("\n✅ Tüm bloglar zaten index'te.")

if __name__ == "__main__":
    main()
