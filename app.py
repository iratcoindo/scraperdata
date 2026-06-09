
import streamlit as st
import requests
import pandas as pd
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go

from pyvis.network import Network
from wordcloud import WordCloud
from community import community_louvain

from collections import Counter
from itertools import combinations
import tempfile
import re

st.set_page_config(
    page_title="OpenAlex SLR Dashboard",
    layout="wide"
)

st.title("OpenAlex SLR Dashboard")

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
    "Articles",
    20,
    300,
    100
)

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

query = " ".join(
    [
        keyword1,
        keyword2,
        keyword3
    ]
)

if st.button("Search"):

    url = (
        "https://api.openalex.org/works"
        f"?search={query}"
        f"&per-page={n_articles}"
    )

    r = requests.get(url)

    results = r.json()["results"]

records = []

for paper in results:

    year = paper.get(
        "publication_year"
    )

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

st.dataframe(df)

csv = df.to_csv(
    index=False
).encode(
    "utf-8-sig"
)

st.download_button(
    "Download CSV",
    csv,
    "literature.csv"
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
    title="Publication Trend"
)

st.plotly_chart(fig)

top_journal = (
    df["Journal"]
    .value_counts()
    .head(15)
)

st.bar_chart(
    top_journal
)

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
    "been","using","into"
}

keywords = [
    w for w in words
    if len(w) > 3
    and w not in stopwords
]

freq = Counter(
    keywords
)

wc = WordCloud(
    width=1200,
    height=600
).generate(
    " ".join(keywords)
)

fig, ax = plt.subplots(
    figsize=(12,10)
)

nx.draw_networkx_nodes(
    G_filtered,
    pos,
    node_size=sizes,
    node_color=colors,
    cmap=plt.cm.Set3
)

nx.draw_networkx_edges(
    G_filtered,
    pos,
    alpha=0.3
)

nx.draw_networkx_labels(
    G_filtered,
    pos,
    labels=labels,
    font_size=10
)

ax.axis("off")

st.pyplot(fig)

top_words = [
    w
    for w,c
    in freq.most_common(50)
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

        if G.has_edge(a,b):

            G[a][b][
                "weight"
            ] += 1

        else:

            G.add_edge(
                a,
                b,
                weight>=5
            )

partition = community_louvain.best_partition(
    G
)

community_df = pd.DataFrame({
    "Keyword":
    list(
        partition.keys()
    ),
    "Community":
    list(
        partition.values()
    )
})

st.dataframe(
    community_df
)

centrality = nx.degree_centrality(
    G
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
    central_df.head(30)
)

net = Network(
    height="700px",
    width="100%"
)

for node in G.nodes():

    net.add_node(
        node,
        label=node,
        group=partition[node]
    )

for edge in G.edges():

    net.add_edge(
        edge[0],
        edge[1]
    )

tmp = tempfile.NamedTemporaryFile(
    delete=False,
    suffix=".html"
)

net.save_graph(
    tmp.name
)

html = open(
    tmp.name,
    encoding="utf-8"
).read()

st.components.v1.html(
    html,
    height=700
)

nodes = list(
    G.nodes()
)

node_index = {
    n:i
    for i,n
    in enumerate(nodes)
}

source = []
target = []
value = []

for u,v,d in G.edges(
    data=True
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
            label=nodes
        ),
        link=dict(
            source=source,
            target=target,
            value=value
        )
    )
)

st.plotly_chart(fig)

st.subheader(
    "Research Gap"
)

least_common = (
    freq.most_common()
    [-20:]
)

for word,count in least_common:

    st.write(
        f"- {word}"
    )
