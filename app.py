import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

st.set_page_config(
    page_title="Detik News Scraper",
    page_icon="📰",
    layout="wide"
)

st.title("📰 Detik News Scraper")
st.write("Masukkan kata kunci isu dan klik tombol Scrape")

isu = st.text_input(
    "Kata kunci isu",
    placeholder="Contoh: badak jawa"
)

jumlah_artikel = st.slider(
    "Jumlah artikel maksimum",
    min_value=5,
    max_value=50,
    value=20
)

if st.button("Scrape Berita"):

    if not isu:
        st.warning("Masukkan kata kunci terlebih dahulu")
        st.stop()

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/137.0.0.0 Safari/537.36"
        )
    }

    search_url = f"https://www.detik.com/search/searchall?query={isu}"

    st.info(f"Mencari berita: {isu}")

    try:

        response = requests.get(
            search_url,
            headers=headers,
            timeout=20
        )

        st.write("Status pencarian:", response.status_code)

        if response.status_code != 200:
            st.error("Gagal mengakses halaman pencarian")
            st.stop()

        soup = BeautifulSoup(response.text, "html.parser")

        links = []

        for a in soup.find_all("a", href=True):

            href = a["href"]

            if (
                "detik.com" in href
                and "/d-" in href
                and href not in links
            ):
                links.append(href)

        st.success(f"Ditemukan {len(links)} link")

        if len(links) == 0:

            st.error(
                "Tidak ditemukan artikel. "
                "Kemungkinan struktur website berubah "
                "atau request diblokir."
            )

            st.code(response.text[:2000])

            st.stop()

        hasil = []

        progress = st.progress(0)

        for i, url in enumerate(links[:jumlah_artikel]):

            try:

                article = requests.get(
                    url,
                    headers=headers,
                    timeout=20
                )

                article_soup = BeautifulSoup(
                    article.text,
                    "html.parser"
                )

                judul = ""

                h1 = article_soup.find("h1")

                if h1:
                    judul = h1.get_text(strip=True)

                tanggal = ""

                date_div = article_soup.find(
                    "div",
                    class_="detail__date"
                )

                if date_div:
                    tanggal = date_div.get_text(strip=True)

                paragraf = article_soup.select(
                    ".detail__body-text p"
                )

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

                progress.progress(
                    (i + 1) / min(jumlah_artikel, len(links))
                )

                time.sleep(1)

            except Exception as e:

                st.warning(
                    f"Gagal mengambil artikel: {url}"
                )

        if len(hasil) == 0:

            st.error(
                "Tidak ada artikel yang berhasil diambil"
            )

            st.stop()

        df = pd.DataFrame(hasil)

        st.success(
            f"Berhasil mengambil {len(df)} artikel"
        )

        st.dataframe(df)

        csv = df.to_csv(
            index=False,
            encoding="utf-8-sig"
        ).encode("utf-8-sig")

        st.download_button(
            label="⬇ Download CSV",
            data=csv,
            file_name=f"detik_{isu.replace(' ','_')}.csv",
            mime="text/csv"
        )

    except Exception as e:

        st.error(str(e))
