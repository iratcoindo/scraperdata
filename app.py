import streamlit as st
import requests
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import plotly.express as px
import numpy as np

from wordcloud import WordCloud
from community import community_louvain

from collections import Counter
from itertools import combinations
import re

# ==========================
# CONFIG
# ==========================

st.set_page_config(
    page_title="OpenAlex SLR Dashboard",
    layout="wide"
)

st.title("📚 OpenAlex SLR Dashboard")

# ==========================
# INPUT
# ==========================

keyword1 = st.text_input("Keyword 1")
keyword2 = st.text_input("Keyword 2")
keyword3 = st.text_input("Keyword 3")

start_year = st.number_input(
    "Start Year",
    1900,
    2100,
    2015
)

end_year = st.number_input(
    "End Year",
    1900,
    2100,
    2026
)

n_articles = st.slider(
    "Number of Articles",
    20,
    300,
    100
)

# ==========================
# FUNCTION
# ==========================

def reconstruct_abstract(inv):

    if not inv:
        return ""

    words = []

    for word, pos_list in inv.items():

        for pos in pos_list:

            words.append((pos, word))

    words.sort()

    return " ".join(
        word for pos, word in words
    )

# ==========================
# SEARCH
# ==========================

if st.button("Search"):

    query = " ".join(
        [
            keyword1,
            keyword2,
            keyword3
        ]
    )

    with st.spinner("Searching OpenAlex..."):

        url = (
            "https://api.openalex.org/works"
            f"?search={query}"
            f"&per-page={n_articles}"
        )

        r = requests.get(
            url,
            timeout=30
        )

        results = r.json()["results"]

    # ==========================
    # BUILD DATAFRAME
    # ==========================

    records = []

    for paper in results:

        year = paper.get(
            "publication_year"
        )

        if not year:
            continue

        if (
            year < start_year
            or
            year > end_year
        ):
            continue

        abstract = reconstruct_abstract(
            paper.get(
                "abstract_inverted_index"
            )
        )

        title = paper.get(
            "title",
            ""
        )

        citations = paper.get(
            "cited_by_count",
            0
        )

        journal = ""

        if paper.get(
            "primary_location"
        ):

            source = paper[
                "primary_location"
            ].get(
                "source"
            )

            if source:

                journal = source.get(
                    "display_name",
                    ""
                )

        records.append({

            "Title": title,

            "Year": year,

            "Journal": journal,

            "Citations": citations,

            "Abstract": abstract

        })

    df = pd.DataFrame(records)

    if len(df) == 0:

        st.warning(
            "No articles found."
        )

        st.stop()

    # ==========================
    # TABLE
    # ==========================

    st.subheader(
        "Literature Table"
    )

    st.dataframe(
        df,
        use_container_width=True
    )

    # ==========================
    # DOWNLOAD
    # ==========================

    csv = df.to_csv(
        index=False
    ).encode(
        "utf-8-sig"
    )

    st.download_button(
        "⬇ Download CSV",
        csv,
        "literature.csv",
        "text/csv"
    )

    # ==========================
    # PUBLICATION TREND
    # ==========================

    st.subheader(
        "Publication Trend"
    )

    trend = (
        df.groupby("Year")
        .size()
        .reset_index(
            name="Count"
        )
    )

    fig = px.line(
        trend,
        x="Year",
        y="Count",
        markers=True
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # ==========================
    # TOP JOURNALS
    # ==========================

    st.subheader(
        "Top Journals"
    )

    journal_df = (
        df["Journal"]
        .value_counts()
        .head(15)
    )

    st.bar_chart(
        journal_df
    )

    # ==========================
    # KEYWORD EXTRACTION
    # ==========================

    text = " ".join(
        (
            df["Title"]
            .fillna("")
            + " "
            + df["Abstract"]
            .fillna("")
        )
    )

    words = re.findall(
        r"[A-Za-z]+",
        text.lower()
    )

    stopwords = {

        "the","and","for",
        "with","from","that",
        "this","were","have",
        "been","using","into",
        "their","they","these",
        "study","studies"

    }

    keywords = [

        w
        for w in words

        if len(w) > 3
        and w not in stopwords

    ]

    freq = Counter(
        keywords
    )

    # ==========================
    # WORD CLOUD
    # ==========================

    st.subheader(
        "Word Cloud"
    )

    wc = WordCloud(
        width=1200,
        height=600,
        background_color="white"
    ).generate(
        " ".join(keywords)
    )

    fig, ax = plt.subplots(
        figsize=(12,6)
    )

    ax.imshow(wc)

    ax.axis("off")

    st.pyplot(fig)

    # ==========================
    # NETWORK ANALYSIS
    # ==========================

    st.subheader(
        "Keyword Network"
    )

    top_words = [

        w

        for w,c

        in freq.most_common(30)

    ]

    G = nx.Graph()

    for abstract in df["Abstract"]:

        abs_words = re.findall(
            r"[A-Za-z]+",
            str(abstract).lower()
        )

        abs_words = [

            w

            for w in abs_words

            if w in top_words

        ]

        for a,b in combinations(
            set(abs_words),
            2
        ):

            if G.has_edge(
                a,
                b
            ):

                G[a][b][
                    "weight"
                ] += 1

            else:

                G.add_edge(
                    a,
                    b,
                    weight=1
                )

    # FILTER EDGE
    all_edges = []

    for u,v,d in G.edges(data=True):
    
        all_edges.append(
            (u,v,d["weight"])
        )
    
    all_edges = sorted(
        all_edges,
        key=lambda x:x[2],
        reverse=True
    )
    
    top_edges = all_edges[:80]

    G_filtered = nx.Graph()

    for u,v,w in top_edges:
    
        G_filtered.add_edge(
            u,
            v,
            weight=w
        )

    # COMMUNITY

    if len(
        G_filtered.nodes()
    ) > 0:

        partition = community_louvain.best_partition(
            G_filtered
        )
        
        colors = [
        
            partition[n]
        
            for n in G_filtered.nodes()
        
        ]
        pos = nx.spring_layout(
            G_filtered,
            seed=42
        )

        fig, ax = plt.subplots(
            figsize=(12,10)
        )

        nx.draw_networkx_nodes(
            G_filtered,
            pos,
            node_color=colors,
            cmap=plt.cm.Set3,
            node_size=500
        )

        edge_widths = [

            np.sqrt(
                G_filtered[u][v]["weight"]
            ) * 1.5
        
            for u,v in G_filtered.edges()
        
        ]
        
        nx.draw_networkx_edges(
            G_filtered,
            pos,
            width=edge_widths,
            alpha=0.4
        )

        nx.draw_networkx_labels(
            G_filtered,
            pos,
            font_size=8
        )

        ax.axis("off")

        st.pyplot(fig)

        # ==========================
        # CENTRALITY
        # ==========================

        st.subheader(
            "Centrality Ranking"
        )

        centrality = nx.eigenvector_centrality(
            G_filtered,
            max_iter=1000
        )

        cvals = np.array(
            list(centrality.values())
        )
        
        cmin = cvals.min()
        cmax = cvals.max()
        
        node_sizes = []
        
        for n in G_filtered.nodes():
        
            size = 200 + (
                (centrality[n] - cmin)
                /
                (cmax - cmin + 1e-9)
            ) * 5000
        
            node_sizes.append(size)
        nx.draw_networkx_nodes(
            G_filtered,
            pos,
            node_size=node_sizes,
            node_color=colors,
            cmap=plt.cm.Set3,
            alpha=0.9
        )

        central_df = pd.DataFrame({

            "Keyword":
            list(
                centrality.keys()
            ),

            "Centrality":
            list(
                centrality.values()
            )

        })

        central_df = (
            central_df
            .sort_values(
                "Centrality",
                ascending=False
            )
        )

        st.dataframe(
            central_df.head(20)
        )

    # ==========================
    # RESEARCH GAP
    # ==========================

    st.subheader(
        "Potential Research Gaps"
    )

    for word,count in freq.most_common()[-20:]:

        st.write(
            f"• {word}"
        )
