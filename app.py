import streamlit as st
import requests
import pandas as pd

st.set_page_config(
    page_title="Literature Search",
    page_icon="📚",
    layout="wide"
)

st.title("📚 Open Literature Search")

keyword = st.text_input(
    "Keyword",
    placeholder="contoh: wildlife conservation fibroblast"
)

jumlah = st.slider(
    "Jumlah artikel",
    10,
    200,
    50
)

if st.button("Search"):

    if not keyword:
        st.warning("Masukkan keyword")
        st.stop()

    url = (
        "https://api.openalex.org/works"
        f"?search={keyword}"
        f"&per-page={jumlah}"
    )

    with st.spinner("Mencari artikel..."):

        r = requests.get(url, timeout=30)

        if r.status_code != 200:
            st.error("Gagal mengambil data")
            st.stop()

        results = r.json()["results"]

    data = []

    for paper in results:

        try:

            journal = ""

            if paper.get("primary_location"):
                source = paper["primary_location"].get("source")

                if source:
                    journal = source.get("display_name", "")

            doi = paper.get("doi", "")

            open_access = paper.get(
                "open_access",
                {}
            ).get(
                "is_oa",
                False
            )

            data.append({
                "Title": paper.get("title"),
                "Year": paper.get("publication_year"),
                "Citations": paper.get("cited_by_count"),
                "Journal": journal,
                "DOI": doi,
                "Open Access": open_access
            })

        except:
            pass

    df = pd.DataFrame(data)

    st.success(
        f"Ditemukan {len(df)} artikel"
    )

    st.dataframe(
        df,
        use_container_width=True
    )

    csv = df.to_csv(
        index=False
    ).encode("utf-8-sig")

    st.download_button(
        "⬇ Download CSV",
        csv,
        "literature_search.csv",
        "text/csv"
    )
