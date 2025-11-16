import requests
import xml.etree.ElementTree as ET
import sqlite3
from datetime import datetime
from bs4 import BeautifulSoup

# ===============================
# VERİTABANI
# ===============================
conn = sqlite3.connect("haberler.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS haberler (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    baslik TEXT UNIQUE,
    metin TEXT,
    kategori TEXT,
    kaynak TEXT,
    link TEXT,
    tarih TEXT
)
""")
conn.commit()

# ===============================
# SABİTLER
# ===============================
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15"
}

KAYNAKLAR = {
    "Sözcü": "https://www.sozcu.com.tr/rss/anasayfa.xml",
    "Ensonhaber": "https://www.ensonhaber.com/rss/ensonhaber.xml",
    "Habertürk": "https://www.haberturk.com/rss/manset.xml",
}

# ===============================
# FİLTRELER (Telif + Çöp Temizleyici)
# ===============================
KARA_LISTE = [
    "telif", "copyright", "izin alınmadan", "üye ol", 
    "üyelik sözleşmesi", "rıza metni", "çerez politikası",
    "kişisel verileriniz", "şifre yenileme", "spam", "gelen kutunuzu",
    "tüm hakları saklıdır", "mega ajans", "reh. tic.", "kaynak gösterilerek",
    "sosyal hesap", "gizlilik", "çerez", "giriş yap"
]

def paragraf_temizle(paragraflar):
    """Paragrafları filtreleyip çöp ve telif metinlerini temizler."""
    temiz = []
    for p in paragraflar:
        t = p.get_text(" ", strip=True)

        # kara liste kontrol
        if any(k in t.lower() for k in KARA_LISTE):
            continue

        # çok kısa paragrafı alma
        if len(t) < 20:
            continue

        temiz.append(t)
    return temiz


# ===============================
# TAM METİN ÇEKME
# ===============================
def tam_metin_cek(link):
    try:
        res = requests.get(link, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")

        # Sözcü
        if "sozcu.com.tr" in link:
            article = soup.select("div.news-detail > p, div.news-detail__wrapper > p")
        
        # Ensonhaber
        elif "ensonhaber.com" in link:
            article = soup.select("div.news-text > p")

        # Habertürk
        elif "haberturk.com" in link:
            article = soup.select("div.article-body > p, div.ht__news-text > p")

        else:
            article = soup.find_all("p")

        temiz = paragraf_temizle(article)

        return "\n\n".join(temiz)

    except Exception as e:
        print(f"[METİN HATASI] {link} - {e}")
        return ""


# ===============================
# HABERTÜRK KATEGORİ ÇEKME – SAYFADAN
# ===============================
def haberturk_kategori_cek(link):
    try:
        res = requests.get(link, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")

        # Kategori breadcrumb
        kategori = soup.select_one("div.breadcrumb a, a.category")
        if kategori:
            return kategori.get_text(strip=True)

    except:
        pass

    return "Genel"


# ===============================
# HABER KAYDETME
# ===============================
def haberi_kaydet(baslik, metin, kategori, kaynak, link):
    cursor.execute("SELECT id FROM haberler WHERE baslik = ?", (baslik,))
    if cursor.fetchone():
        print(f"[{kaynak}] 🔁 Zaten mevcut: {baslik}")
        return

    tarih = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO haberler (baslik, metin, kategori, kaynak, link, tarih) VALUES (?, ?, ?, ?, ?, ?)",
        (baslik, metin, kategori, kaynak, link, tarih)
    )
    conn.commit()
    print(f"[{kaynak}] ✅ Kaydedildi: {baslik}")


# ===============================
# RSS ÇEKME
# ===============================
def rss_haberlerini_cek(rss_url, kaynak_adi):
    try:
        res = requests.get(rss_url, headers=HEADERS, timeout=10)

        root = ET.fromstring(res.content)
        
        for item in root.findall(".//item"):
            baslik = item.findtext("title", "").strip()
            aciklama = item.findtext("description", "").strip()
            kategori = item.findtext("category", "").strip()
            link = item.findtext("link", "").strip()

            # Habertürk’te kategori yok → sayfadan al
            if kaynak_adi == "Habertürk" and kategori == "":
                kategori = haberturk_kategori_cek(link)

            tam_metin = tam_metin_cek(link)

            # Eğer haber metni çok boşsa description kullan
            if len(tam_metin) < 50:
                tam_metin = aciklama

            haberi_kaydet(baslik, tam_metin, kategori or "Genel", kaynak_adi, link)

    except Exception as e:
        print(f"[{kaynak_adi}] RSS HATA: {e}")


# ===============================
# ÇALIŞTIRMA
# ===============================
if __name__ == "__main__":
    print("\n📰 Haberler çekiliyor...\n")

    for kaynak, rss in KAYNAKLAR.items():
        rss_haberlerini_cek(rss, kaynak)

    conn.close()
    print("\n✅ Tüm haberler başarıyla kaydedildi.")
