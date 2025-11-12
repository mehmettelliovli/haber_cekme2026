import requests
import xml.etree.ElementTree as ET
import sqlite3
from datetime import datetime

# ===============================
# Veritabanı bağlantısı
# ===============================
conn = sqlite3.connect("haberler.db")
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS haberler (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    baslik TEXT UNIQUE,
    metin TEXT,
    kaynak TEXT,
    tarih TEXT
)
''')
conn.commit()

# ===============================
# Sabitler
# ===============================
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15"
    )
}

KAYNAKLAR = {
    "Sözcü": "https://www.sozcu.com.tr/rss/anasayfa.xml",
    "Ensonhaber": "https://www.ensonhaber.com/rss/ensonhaber.xml",
    "Habertürk - Manşet": "https://www.haberturk.com/rss/manset.xml"
}

# ===============================
# Yardımcı fonksiyonlar
# ===============================
def haberi_kaydet(baslik, metin, kaynak):
    """Duplicate kontrolü yaparak haberi kaydeder."""
    cursor.execute("SELECT id FROM haberler WHERE baslik = ?", (baslik,))
    if cursor.fetchone():
        print(f"[{kaynak}] 🔁 Zaten mevcut: {baslik}")
        return

    tarih = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO haberler (baslik, metin, kaynak, tarih) VALUES (?, ?, ?, ?)",
        (baslik, metin, kaynak, tarih),
    )
    conn.commit()
    print(f"[{kaynak}] ✅ Kaydedildi: {baslik}")


def rss_haberlerini_cek(rss_url, kaynak_adi):
    """RSS adresinden haberleri çeker ve kaydeder."""
    try:
        res = requests.get(rss_url, headers=HEADERS, timeout=10)
        if res.status_code != 200:
            print(f"[{kaynak_adi}] RSS alınamadı (status: {res.status_code})")
            return

        if not res.text.strip():
            print(f"[{kaynak_adi}] RSS boş dönüyor.")
            return

        root = ET.fromstring(res.content)
        for item in root.findall(".//item"):
            baslik = item.find("title").text.strip() if item.find("title") is not None else "Başlık yok"
            aciklama = item.find("description").text.strip() if item.find("description") is not None else ""
            link = item.find("link").text.strip() if item.find("link") is not None else ""
            metin = f"{aciklama}\nKaynak linki: {link}"

            haberi_kaydet(baslik, metin, kaynak_adi)

    except Exception as e:
        print(f"[{kaynak_adi}] ⚠️ RSS hata: {e}")


# ===============================
# Çalıştırma
# ===============================
if __name__ == "__main__":
    print("📰 RSS üzerinden haberler çekiliyor...\n")

    for kaynak, rss in KAYNAKLAR.items():
        rss_haberlerini_cek(rss, kaynak)

    conn.close()
    print("\n✅ Tüm RSS haberleri başarıyla kaydedildi.")
