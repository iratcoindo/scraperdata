import streamlit as st
import requests
import pandas as pd

# ==========================
# CONFIG
# ==========================

st.set_page_config(
    page_title="Literature Review Assistant",
    page_icon="📚",
    layout="wide"
)

st.title("📚 OpenAlex Literature Review Assistant")

st.write(
    "Cari artikel ilmiah open-access dan buat ringkasan literatur otomatis."
)

# ==========================
# INPUT
# ==========================

keyword = st.text_input(
    "Keyword",
    placeholder="contoh: wildlife conservation fibroblast"
)

jumlah = st.slider(
    "Jumlah artikel",
    10,
    100,
    30
)

# ==========================
# FUNCTION
# ==========================

def reconstruct_abstract(inv_index):

    if not inv_index:
        return ""

    words = []

    for word, positions in inv_index.items():

        for pos in positions:
            words.append((pos, word))

    words.sort()

    return " ".join(
        word for pos, word in words
    )


def create_summary(text, max_words=500):

    if not text:
        return "Tidak ada abstrak yang tersedia."

    words = text.split()

    if len(words) <= max_words:
        return text

    return " ".join(words[:max_words]) + " ..."


# ==========================
# SEARCH
# ==========================

if st.button("🔍 Search Literature"):

    if not keyword:

        st.warning(
            "Masukkan keyword terlebih dahulu."
        )

        st.stop()

    url = (
        "https://api.openalex.org/works"
        f"?search={keyword}"
        f"&per-page={jumlah}"
    )

    with st.spinner("Mengambil data dari OpenAlex..."):

        r = requests.get(
            url,
            timeout=30
        )

    if r.status_code != 200:

        st.error(
            f"Gagal mengambil data. Status code: {r.status_code}"
        )

        st.stop()

    results = r.json()["results"]

    data = []

    all_abstracts = []

    for paper in results:

        try:

            journal = ""

            if paper.get("primary_location"):

                source = paper["primary_location"].get(
                    "source"
                )

                if source:
                    journal = source.get(
                        "display_name",
                        ""
                    )

            abstract = reconstruct_abstract(
                paper.get(
                    "abstract_inverted_index"
                )
            )

            doi = paper.get(
                "doi",
                ""
            )

            citations = paper.get(
                "cited_by_count",
                0
            )

            year = paper.get(
                "publication_year",
                ""
            )

            title = paper.get(
                "title",
                ""
            )

            open_access = paper.get(
                "open_access",
                {}
            ).get(
                "is_oa",
                False
            )

            data.append({

                "Title": title,

                "Year": year,

                "Journal": journal,

                "Citations": citations,

                "DOI": doi,

                "Open Access": open_access,

                "Abstract": abstract

            })

            if abstract:
                all_abstracts.append(
                    abstract
                )

        except Exception:
            pass

    df = pd.DataFrame(data)

    # ==========================
    # HASIL
    # ==========================

    st.success(
        f"Ditemukan {len(df)} artikel."
    )

    st.dataframe(
        df,
        use_container_width=True
    )

    # ==========================
    # SUMMARY
    # ==========================

    st.subheader(
        "📖 Literature Summary (~500 words)"
    )

    combined_text = " ".join(
        all_abstracts
    )

    summary = create_summary(
        combined_text,
        max_words=500
    )

    st.text_area(
        "Summary",
        summary,
        height=400
    )

    # ==========================
    # DOWNLOAD CSV
    # ==========================

    csv = df.to_csv(
        index=False
    ).encode(
        "utf-8-sig"
    )

    st.download_button(
        label="⬇ Download CSV",
        data=csv,
        file_name=(
            f"{keyword.replace(' ','_')}_literature.csv"
        ),
        mime="text/csv"
    )
