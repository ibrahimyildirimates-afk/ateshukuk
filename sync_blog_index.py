#!/usr/bin/env python3
"""
blog/ klasöründeki HTML dosyalarını tarar:
- index.html: sadece son 6 blog kartı gösterir
- blog.html: tüm blogları ekler (kategori filtreli)
"""
import os, re

BLOG_DIR = "blog"
INDEX_FILE = "index.html"
BLOG_PAGE = "blog.html"
SKIP_FILES = {"blog-sablon.html"}
INDEX_LIMIT = 6  # anasayfada gösterilecek max kart

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

def insert_point_bul(icerik):
    """Grid div kapanışını depth sayarak bulur, oraya ekle."""
    blog_start = icerik.find('id="blog"')
    grid_start = icerik.find('class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3', blog_start)
    if grid_start == -1:
        return -1
    # <div'in başına git
    div_start = icerik.rfind('<div', 0, grid_start)
    pos, depth = div_start, 0
    while pos < len(icerik):
        o = icerik.find('<div', pos)
        c = icerik.find('</div>', pos)
        if o != -1 and (c == -1 or o < c):
            depth += 1; pos = o + 4
        else:
            depth -= 1
            if depth == 0:
                return c  # grid kapanışının başı
            pos = c + 6
    return -1

def kart_olustur(slug, meta, data_attr=True):
    data = f' data-kategori="{meta["kategori"]}"' if data_attr else ''
    return f"""
                <div class="bg-white blog-card shadow-lg border-t-4 border-ates-navy p-8"{data}>
                    <span class="text-ates-gold text-[10px] font-bold uppercase tracking-widest">{meta['kategori']}</span>
                    <h3 class="text-xl font-bold mt-2 mb-4 text-ates-navy leading-tight">{meta['baslik']}</h3>
                    <p class="text-gray-500 text-sm mb-6 line-clamp-3 italic">{meta['ozet']}</p>
                    <a href="/blog/{slug}" class="text-ates-navy font-bold text-xs uppercase border-b border-ates-gold">Devamı →</a>
                </div>"""

def index_guncelle(tum_bloglar):
    """index.html'de son 6 kartı göster, eskilerini kaldır."""
    if not os.path.exists(INDEX_FILE):
        return
    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        ic = f.read()

    mevcut = re.findall(r'href="/blog/([^"]+)"', ic)
    
    # Yeni blogları ekle
    yeni = [(s, m) for s, m in tum_bloglar if s not in mevcut]
    for slug, meta in yeni:
        insert = insert_point_bul(ic)
        ic = ic[:insert] + kart_olustur(slug, meta, data_attr=False) + "\n                " + ic[insert:]

    # Toplam kart sayısını INDEX_LIMIT'e indir (en eskiyi kaldır)
    mevcut_guncel = re.findall(r'href="/blog/([^"]+)"', ic)
    if len(mevcut_guncel) > INDEX_LIMIT:
        fazla = mevcut_guncel[:len(mevcut_guncel) - INDEX_LIMIT]
        for slug in fazla:
            slug_pos = ic.find(f'href="/blog/{slug}"')
            if slug_pos == -1: continue
            kart_start = ic.rfind('<div class="bg-white blog-card', 0, slug_pos)
            pos, depth = kart_start, 0
            while pos < len(ic):
                o, c = ic.find('<div', pos), ic.find('</div>', pos)
                if o != -1 and (c == -1 or o < c):
                    depth += 1; pos = o + 4
                else:
                    depth -= 1
                    if depth == 0:
                        ic = ic[:kart_start] + ic[c + 6:]
                        break
                    pos = c + 6

    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        f.write(ic)
    
    kalan = re.findall(r'href="/blog/([^"]+)"', ic)
    print(f"✅ index.html güncellendi — {len(kalan)} kart gösteriliyor.")

def blog_sayfasi_guncelle(tum_bloglar):
    """blog.html'e eksik kartları ekle."""
    if not os.path.exists(BLOG_PAGE):
        print(f"⚠️  {BLOG_PAGE} bulunamadı, atlandı.")
        return
    with open(BLOG_PAGE, "r", encoding="utf-8") as f:
        ic = f.read()

    mevcut = set(re.findall(r'href="/blog/([^"]+)"', ic))
    eklenen = 0
    for slug, meta in tum_bloglar:
        if slug in mevcut:
            continue
        insert = insert_point_bul(ic)
        ic = ic[:insert] + kart_olustur(slug, meta, data_attr=True) + "\n                " + ic[insert:]
        eklenen += 1
        print(f"  ✅ blog.html'e eklendi: {meta['baslik'][:55]}")

    if eklenen > 0:
        with open(BLOG_PAGE, "w", encoding="utf-8") as f:
            f.write(ic)
        print(f"✅ blog.html güncellendi — {eklenen} yeni kart.")
    else:
        print("✅ blog.html zaten güncel.")

def main():
    if not os.path.exists(BLOG_DIR):
        print("❌ blog/ klasörü bulunamadı.")
        return

    dosyalar = sorted([f for f in os.listdir(BLOG_DIR)
                       if f.endswith(".html") and f not in SKIP_FILES])
    print(f"📂 {len(dosyalar)} blog dosyası bulundu.")

    tum_bloglar = []
    for dosya in dosyalar:
        meta = blog_meta_oku(os.path.join(BLOG_DIR, dosya))
        if meta:
            tum_bloglar.append((dosya, meta))

    index_guncelle(tum_bloglar)
    blog_sayfasi_guncelle(tum_bloglar)

if __name__ == "__main__":
    main()
