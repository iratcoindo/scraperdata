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
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.decomposition import TruncatedSVD
import plotly.graph_objects as go

# ==========================
# CONFIG
# ==========================

st.set_page_config(
    page_title="OpenAlex SLR Dashboard",
    layout="wide"
)

st.title("📚 DRAMAGA SLR Dashboard")

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
    
                G[a][b]["weight"] += 1
    
            else:
    
                G.add_edge(
                    a,
                    b,
                    weight=1
                )
    
    # ==========================
    # FILTER STRONGEST EDGES
    # ==========================
    
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
    
    top_edges = all_edges[:40]
    
    G_filtered = nx.Graph()
    
    for u,v,w in top_edges:
    
        G_filtered.add_edge(
            u,
            v,
            weight=w
        )
    
    if len(G_filtered.nodes()) > 0:
    
        # ==========================
        # COMMUNITY
        # ==========================
    
        partition = community_louvain.best_partition(
            G_filtered
        )
    
        colors = [
    
            partition[n]
    
            for n in G_filtered.nodes()
    
        ]
    
        # ==========================
        # CENTRALITY
        # ==========================
    
        centrality = nx.eigenvector_centrality(
            G_filtered,
            max_iter=1000
        )
    
        cvals = np.array(
            list(
                centrality.values()
            )
        )
    
        cmin = cvals.min()
    
        cmax = cvals.max()
    
        node_sizes = []
    
        for n in G_filtered.nodes():
    
            size = 100 + (
    
                (centrality[n]-cmin)
    
                /
    
                (cmax-cmin+1e-9)
    
            )**2 * 12000
    
            node_sizes.append(size)
    
        # ==========================
        # EDGE WIDTH
        # ==========================
    
        weights = np.array([
    
            d["weight"]
    
            for _,_,d
    
            in G_filtered.edges(data=True)
    
        ])
    
        wmin = weights.min()
    
        wmax = weights.max()
    
        edge_widths = []
    
        for u,v,d in G_filtered.edges(data=True):
    
            width = 0.5 + (
    
                (d["weight"]-wmin)
    
                /
    
                (wmax-wmin+1e-9)
    
            ) * 10
    
            edge_widths.append(width)
    
        # ==========================
        # LABELS
        # ==========================
    
        top_nodes = sorted(
    
            centrality,
    
            key=centrality.get,
    
            reverse=True
    
        )[:12]
    
        labels = {
    
            n:n
    
            for n in top_nodes
    
        }
    
        # ==========================
        # LAYOUT
        # ==========================
    
        pos = nx.spring_layout(
    
            G_filtered,
    
            seed=42,
    
            k=2.5,
    
            iterations=500
    
        )
    
        # ==========================
        # DRAW NETWORK
        # ==========================
    
        fig, ax = plt.subplots(
            figsize=(14,10)
        )
    
        nx.draw_networkx_edges(
            G_filtered,
            pos,
            width=edge_widths,
            edge_color="#6c757d",
            alpha=0.15
        )
    
        nx.draw_networkx_nodes(
            G_filtered,
            pos,
            node_size=node_sizes,
            node_color=colors,
            cmap=plt.cm.Set3,
            edgecolors="black",
            linewidths=0.5
    
        )
    
        nx.draw_networkx_labels(
    
            G_filtered,
    
            pos,
    
            labels=labels,
    
            font_size=10,
    
            font_weight="bold"
    
        )
    
        ax.axis("off")
    
        st.pyplot(fig)
    
        # ==========================
        # CENTRALITY TABLE
        # ==========================
    
        st.subheader(
            "Centrality Ranking"
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
    
        central_df = central_df.sort_values(
            "Centrality",
            ascending=False
        )
    
        st.dataframe(
            central_df.head(20)
        )

    # ==========================
    # NETWORK INTERPRETATION
    # ==========================
    
    st.subheader(
        "Network Analysis Interpretation"
    )
    
    top_keyword = central_df.iloc[0]["Keyword"]
    
    top_centrality = central_df.iloc[0]["Centrality"]
    
    n_nodes = G_filtered.number_of_nodes()
    
    n_edges = G_filtered.number_of_edges()
    
    n_clusters = len(
        set(partition.values())
    )
    
    cluster_sizes = {}
    
    for node, cluster in partition.items():
    
        cluster_sizes.setdefault(
            cluster,
            0
        )
    
        cluster_sizes[cluster] += 1
    
    largest_cluster = max(
        cluster_sizes,
        key=cluster_sizes.get
    )
    
    largest_cluster_size = cluster_sizes[
        largest_cluster
    ]
    
    top_keywords = (
        central_df
        .head(10)["Keyword"]
        .tolist()
    )
    
    interpretation = f"""
    The keyword co-occurrence network consisted of
    {n_nodes} nodes and {n_edges} edges,
    indicating the existence of multiple thematic
    relationships among the most frequently occurring
    terms extracted from the retrieved literature.
    
    Community detection analysis identified
    {n_clusters} major thematic clusters.
    The largest cluster contained
    {largest_cluster_size} keywords,
    suggesting a dominant research theme within the field.
    
    The most influential keyword based on eigenvector
    centrality was '{top_keyword}'
    (centrality = {top_centrality:.3f}).
    This finding indicates that the keyword occupies
    a strategic position in the network and is strongly
    connected to other highly influential concepts.
    
    Other highly central keywords included:
    
    {", ".join(top_keywords)}.
    
    The presence of these highly connected keywords
    suggests that current research is concentrated around
    a limited number of core concepts that form the
    intellectual structure of the field.
    
    The network topology demonstrates that certain
    keywords act as bridges connecting otherwise separate
    research themes. Such bridging concepts often represent
    multidisciplinary topics and may indicate areas where
    future innovation and collaboration are likely to emerge.
    
    The community structure further reveals thematic
    specialization among research groups.
    Clusters may represent distinct scientific topics,
    methodological approaches, biological processes,
    or application areas depending on the search query.
    
    The relatively strong connections among central nodes
    indicate a mature and interconnected research area,
    whereas peripheral nodes with lower centrality may
    represent emerging topics, niche applications,
    or underexplored research directions.
    
    From a bibliometric perspective, the network suggests
    that knowledge production is organized around several
    core concepts, while additional peripheral concepts
    provide opportunities for expansion and interdisciplinary
    integration.
    
    Potential future research directions can be inferred
    from low-frequency keywords and weakly connected nodes,
    which may represent gaps in the literature.
    These topics are currently less integrated into the
    mainstream research network and therefore offer
    opportunities for novel contributions.
    
    Overall, the keyword co-occurrence network reveals
    the conceptual structure of the literature,
    identifies dominant research themes,
    highlights influential concepts,
    and provides evidence-based insights regarding
    future research priorities.
    """
    
    st.text_area(
        "Interpretation",
        interpretation,
        height=500
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

    # ==========================
    # THEMATIC MAP
    # ==========================
    
    st.subheader("Thematic Map")
    
    theme_data = []
    
    for cluster_id in set(partition.values()):
    
        nodes = [
    
            n
    
            for n,c
    
            in partition.items()
    
            if c == cluster_id
    
        ]
    
        if len(nodes) < 2:
            continue
    
        subG = G_filtered.subgraph(nodes)
    
        density = nx.density(subG)
    
        centrality_mean = np.mean(
            [
                centrality[n]
                for n in nodes
            ]
        )
    
        theme_data.append({
    
            "Cluster": f"C{cluster_id}",
    
            "Density": density,
    
            "Centrality": centrality_mean,
    
            "Keywords": ", ".join(nodes[:5])
    
        })
    
    theme_df = pd.DataFrame(theme_data)
    
    fig = px.scatter(
    
        theme_df,
    
        x="Centrality",
    
        y="Density",
    
        size="Density",
    
        color="Cluster",
    
        hover_data=["Keywords"],
    
        title="Thematic Map"
    
    )
    
    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # ==========================
    # MCA
    # ==========================
    
    st.subheader(
        "Conceptual Structure Map (MCA)"
    )
    
    docs = (
        df["Title"]
        .fillna("")
        + " "
        + df["Abstract"]
        .fillna("")
    )
    
    vectorizer = CountVectorizer(
    
        stop_words="english",
    
        max_features=100
    
    )
    
    X = vectorizer.fit_transform(
        docs
    )
    
    svd = TruncatedSVD(
        n_components=2,
        random_state=42
    )
    
    coords = svd.fit_transform(
        X.T
    )
    
    terms = vectorizer.get_feature_names_out()
    
    mca_df = pd.DataFrame({
    
        "Keyword": terms,
    
        "Dim1": coords[:,0],
    
        "Dim2": coords[:,1]
    
    })
    
    fig = px.scatter(
    
        mca_df,
    
        x="Dim1",
    
        y="Dim2",
    
        text="Keyword",
    
        title="Conceptual Structure Map"
    
    )
    
    fig.update_traces(
        textposition="top center"
    )
    
    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # ==========================
    # SANKEY
    # ==========================
    
    st.subheader(
        "Keyword Relationship Sankey"
    )
    
    top20 = [
    
        w
    
        for w,c
    
        in freq.most_common(20)
    
    ]
    
    nodes = top20
    
    node_index = {
    
        n:i
    
        for i,n
    
        in enumerate(nodes)
    
    }
    
    source = []
    target = []
    value = []
    
    for u,v,d in G_filtered.edges(data=True):
    
        if (
    
            u in node_index
    
            and
    
            v in node_index
    
        ):
    
            source.append(
                node_index[u]
            )
    
            target.append(
                node_index[v]
            )
    
            value.append(
                d["weight"]
            )
    
    fig = go.Figure(
    
        go.Sankey(
    
            node=dict(
    
                label=nodes,
    
                pad=20,
    
                thickness=20
    
            ),
    
            link=dict(
    
                source=source,
    
                target=target,
    
                value=value
    
            )
    
        )
    
    )
    
    st.plotly_chart(
        fig,
        use_container_width=True
    )
