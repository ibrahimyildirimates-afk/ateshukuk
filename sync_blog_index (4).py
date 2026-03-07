#!/usr/bin/env python3
"""
blog/ klasöründeki tüm HTML dosyalarını tarar,
index.html'de kartı olmayanları grid içine ekler.
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

def grid_sonu_bul(icerik, grid_start):
    """Grid div'inin kapanış pozisyonunu bulur."""
    pos = grid_start
    depth = 0
    while pos < len(icerik):
        o = icerik.find('<div', pos)
        c = icerik.find('</div>', pos)
        if o != -1 and (c == -1 or o < c):
            depth += 1
            pos = o + 4
        else:
            depth -= 1
            if depth == 0:
                return c  # </div> başlangıcı
            pos = c + 6
    return -1

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

    # Grid'i bul
    blog_start = icerik.find('id="blog"')
    grid_start = icerik.find('<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8', blog_start)
    if grid_start == -1:
        print("❌ Blog grid bulunamadı!")
        return

    eklenen = 0
    for dosya in dosyalar:
        if dosya in mevcut:
            continue
        meta = blog_meta_oku(os.path.join(BLOG_DIR, dosya))
        if not meta:
            continue

        kart = f"""
                <div class="bg-white blog-card shadow-lg border-t-4 border-ates-navy p-8">
                    <span class="text-ates-gold text-[10px] font-bold uppercase tracking-widest">{meta['kategori']}</span>
                    <h4 class="text-xl font-bold mt-2 mb-4 text-ates-navy leading-tight">{meta['baslik']}</h4>
                    <p class="text-gray-500 text-sm mb-6 line-clamp-3 italic">{meta['ozet']}</p>
                    <a href="/blog/{dosya}" class="text-ates-navy font-bold text-xs uppercase border-b border-ates-gold">Devamı →</a>
                </div>"""

        # Her seferinde grid sonunu yeniden hesapla
        grid_start = icerik.find('<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8',
                                  icerik.find('id="blog"'))
        grid_end = grid_sonu_bul(icerik, grid_start)
        if grid_end == -1:
            print("❌ Grid kapanışı bulunamadı!")
            return

        icerik = icerik[:grid_end] + kart + "\n            " + icerik[grid_end:]
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
