#!/usr/bin/env python3
"""
blog/ klasöründeki HTML dosyalarını tarar:
- index.html: sadece son 6 blog kartı gösterir  (id="blog" section içindeki grid)
- blog.html:  tüm blogları ekler               (id="blog-grid" div içine)
"""
import os, re

BLOG_DIR   = "blog"
INDEX_FILE = "index.html"
BLOG_PAGE  = "blog.html"
SKIP_FILES = {"blog-sablon.html"}
INDEX_LIMIT = 6

# ── Meta okuma ────────────────────────────────────────────────────────────────

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

# ── Kart HTML üretimi ─────────────────────────────────────────────────────────

def kart_olustur(slug, meta, data_attr=True):
    data = f' data-kategori="{meta["kategori"]}"' if data_attr else ''
    return (
        f'\n                <div class="bg-white blog-card shadow-lg border-t-4 border-ates-navy p-8"{data}>\n'
        f'                    <span class="text-ates-gold text-[10px] font-bold uppercase tracking-widest">{meta["kategori"]}</span>\n'
        f'                    <h3 class="text-xl font-bold mt-2 mb-4 text-ates-navy leading-tight">{meta["baslik"]}</h3>\n'
        f'                    <p class="text-gray-500 text-sm mb-6 line-clamp-3 italic">{meta["ozet"]}</p>\n'
        f'                    <a href="/blog/{slug}" class="text-ates-navy font-bold text-xs uppercase border-b border-ates-gold">Devamı →</a>\n'
        f'                </div>'
    )

# ── index.html güncelle ───────────────────────────────────────────────────────

def _index_grid_sinirlar(ic):
    """
    index.html'deki blog grid'inin açılış '>' ve kapanış '</div>' pozisyonlarını döndür.
    Güvenli yöntem: grid class'ını bul, açılış '>'den itibaren depth say.
    """
    blog_sec = ic.find('id="blog"')
    if blog_sec == -1:
        return -1, -1
    grid_attr = ic.find('class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3', blog_sec)
    if grid_attr == -1:
        return -1, -1
    acilis = ic.find('>', grid_attr)
    if acilis == -1:
        return -1, -1

    # Depth counting: açılış '>'DEN SONRA başla (div içeriğinden)
    depth = 1  # Grid div'inin kendisi zaten açık
    i = acilis + 1
    while i < len(ic):
        o = ic.find('<div', i)
        c = ic.find('</div>', i)
        if o != -1 and (c == -1 or o < c):
            depth += 1
            i = o + 4
        else:
            if c == -1:
                break
            depth -= 1
            if depth == 0:
                return acilis, c
            i = c + 6
    return acilis, -1

def index_guncelle(tum_bloglar):
    if not os.path.exists(INDEX_FILE):
        print(f"⚠️  {INDEX_FILE} bulunamadı.")
        return
    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        ic = f.read()

    acilis, kapan = _index_grid_sinirlar(ic)
    if acilis == -1 or kapan == -1:
        print("⚠️  index.html'de blog grid bulunamadı!")
        return

    grid_ic = ic[acilis + 1 : kapan]
    mevcut_sluglar = re.findall(r'href="/blog/([^"]+)"', grid_ic)

    yeni = [(s, m) for s, m in tum_bloglar if s not in mevcut_sluglar]
    for slug, meta in reversed(yeni):
        grid_ic = kart_olustur(slug, meta, data_attr=False) + "\n" + grid_ic

    # INDEX_LIMIT'e indir
    tum_sluglar = re.findall(r'href="/blog/([^"]+)"', grid_ic)
    if len(tum_sluglar) > INDEX_LIMIT:
        kaldir = tum_sluglar[INDEX_LIMIT:]
        for slug in kaldir:
            pattern = (
                r'\s*<div class="bg-white blog-card[^>]*>\s*(?:.*?)'
                rf'href="/blog/{re.escape(slug)}"(?:.*?)</div>'
            )
            grid_ic = re.sub(pattern, '', grid_ic, count=1, flags=re.DOTALL)

    yeni_ic = ic[:acilis + 1] + grid_ic + ic[kapan:]
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        f.write(yeni_ic)
    kalan = re.findall(r'href="/blog/([^"]+)"', grid_ic)
    print(f"✅ index.html güncellendi — {len(kalan)} kart gösteriliyor.")

# ── blog.html güncelle ────────────────────────────────────────────────────────

def blog_sayfasi_guncelle(tum_bloglar):
    if not os.path.exists(BLOG_PAGE):
        print(f"⚠️  {BLOG_PAGE} bulunamadı, atlandı.")
        return
    with open(BLOG_PAGE, "r", encoding="utf-8") as f:
        ic = f.read()

    grid_id_pos = ic.find('id="blog-grid"')
    if grid_id_pos == -1:
        print('⚠️  blog.html\'de id="blog-grid" bulunamadı!')
        return
    acilis = ic.find('>', grid_id_pos)
    if acilis == -1:
        return

    mevcut = set(re.findall(r'href="/blog/([^"]+)"', ic))
    eklenen = 0

    for slug, meta in reversed(tum_bloglar):
        if slug in mevcut:
            continue
        yeni_kart = kart_olustur(slug, meta, data_attr=True)
        ic = ic[:acilis + 1] + yeni_kart + "\n" + ic[acilis + 1:]
        acilis = ic.find('>', ic.find('id="blog-grid"'))
        mevcut.add(slug)
        eklenen += 1
        print(f"  ✅ blog.html'e eklendi: {meta['baslik'][:55]}")

        if f"filtrele('{meta['kategori']}')" not in ic:
            filtre_pos = ic.find('id="filtreler"')
            if filtre_pos != -1:
                filtre_acilis = ic.find('>', filtre_pos)
                kisa = meta['kategori'].replace(' Hukuku','').replace(' Kararları','')
                buton = (
                    f'\n                <button onclick="filtrele(\'{meta["kategori"]}\')" '
                    f'class="filtre-btn px-4 py-2 text-xs font-bold uppercase tracking-wider '
                    f'border-2 border-gray-300 text-gray-600 rounded hover:border-ates-navy '
                    f'hover:text-ates-navy transition">{kisa}</button>'
                )
                ic = ic[:filtre_acilis + 1] + buton + ic[filtre_acilis + 1:]
                print(f"  ✅ Filtre butonu eklendi: {meta['kategori']}")

    if eklenen > 0:
        with open(BLOG_PAGE, "w", encoding="utf-8") as f:
            f.write(ic)
        print(f"✅ blog.html güncellendi — {eklenen} yeni kart.")
    else:
        print("✅ blog.html zaten güncel.")

# ── Ana akış ─────────────────────────────────────────────────────────────────

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
