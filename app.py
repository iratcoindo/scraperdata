import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

# ========================
# INPUT ISU
# ========================
import streamlit as st

isu = st.text_input("Masukkan isu")

# ========================
# SEARCH DETIK
# ========================
search_url = f"https://www.detik.com/search/searchall?query={isu}"

headers = {
    "User-Agent": "Mozilla/5.0"
}

r = requests.get(search_url, headers=headers)

if r.status_code != 200:
    print("Gagal mengambil halaman pencarian")
    exit()

soup = BeautifulSoup(r.text, "html.parser")

# ========================
# AMBIL LINK BERITA
# ========================
links = []

for a in soup.select("article a"):
    href = a.get("href")

    if href and "detik.com" in href:
        if href not in links:
            links.append(href)

print(f"Ditemukan {len(links)} artikel")

# ========================
# SCRAPE ARTIKEL
# ========================
hasil = []

for url in links[:20]:

    try:
        r = requests.get(url, headers=headers, timeout=15)

        soup = BeautifulSoup(r.text, "html.parser")

        judul = soup.find("h1")

        if judul:
            judul = judul.get_text(strip=True)
        else:
            judul = ""

        tanggal = soup.find("div", class_="detail__date")

        if tanggal:
            tanggal = tanggal.get_text(strip=True)
        else:
            tanggal = ""

        paragraf = soup.select(".detail__body-text p")

        isi = " ".join(
            p.get_text(" ", strip=True)
            for p in paragraf
        )

        hasil.append({
            "isu": isu,
            "judul": judul,
            "tanggal": tanggal,
            "url": url,
            "isi": isi
        })

        print("OK:", judul)

        time.sleep(1)

    except Exception as e:
        print("Error:", url)

# ========================
# SAVE CSV
# ========================
df = pd.DataFrame(hasil)

nama_file = f"detik_{isu.replace(' ','_')}.csv"

df.to_csv(
    nama_file,
    index=False,
    encoding="utf-8-sig"
)

print(f"Selesai. Data tersimpan di {nama_file}")
