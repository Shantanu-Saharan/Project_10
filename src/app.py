import streamlit as st
from pyvis.network import Network
from neo4j import GraphDatabase
import streamlit.components.v1 as components

# --- CONFIG ---
URI = "neo4j+s://4266d4ef.databases.neo4j.io"
AUTH = ("4266d4ef", "S9cieujK6_0eSAO97NdfWi0kIxAn6_FSoqO-Q2kntA8")


class GraphVizApp:
    def __init__(self, uri, auth):
        # Setting up the Neo4j driver
        self.driver = GraphDatabase.driver(uri, auth=auth)

    def get_graph_data(self, entity_filter=""):
        # Returning only plain values instead of Neo4j objects
        query = """
        MATCH (e:Entity)-[r]->(c)
        WHERE toLower(e.name) CONTAINS toLower($filter)
        RETURN
            elementId(e) AS source_id,
            e.name AS source_name,
            type(r) AS rel_type,
            elementId(c) AS target_id,
            labels(c) AS target_labels,
            c.text AS claim_text,
            c.name AS target_name,
            c.quote AS quote,
            c.source AS source,
            c.created_at AS created_at
        LIMIT 50
        """
        with self.driver.session() as session:
            return [dict(record) for record in session.run(query, filter=entity_filter)]


# --- UI LAYOUT ---
st.set_page_config(layout="wide", page_title="Enron Memory Explorer")
st.title("Enron Memory Graph Explorer")

# Sidebar
st.sidebar.header("Filters & Search")
search_term = st.sidebar.text_input("Search Entity (e.g., Sanders)", "")
show_claims = st.sidebar.checkbox("Show Claim Nodes", value=True)

# Get graph data
viz_manager = GraphVizApp(URI, AUTH)
records = viz_manager.get_graph_data(search_term)

# Build network
net = Network(height="600px", width="100%", bgcolor="#222222", font_color="white", directed=True)

for record in records:
    source_id = str(record["source_id"])
    target_id = str(record["target_id"])
    source_name = str(record["source_name"]) if record["source_name"] else "Unknown Entity"
    rel_type = str(record["rel_type"]) if record["rel_type"] else "RELATED_TO"
    target_labels = record["target_labels"] or []

    # Add source entity node
    net.add_node(
        source_id,
        label=source_name,
        color="#00d4ff",
        title=f"Entity: {source_name}"
    )

    # Add target node
    if "Claim" in target_labels:
        if show_claims:
            claim_text = str(record["claim_text"]) if record["claim_text"] else "No text"
            short_label = claim_text[:30] + ".." if len(claim_text) > 30 else claim_text

            net.add_node(
                target_id,
                label=short_label,
                color="#ffcc00",
                title=f"Claim: {claim_text}"
            )

            net.add_edge(source_id, target_id, label=rel_type)
    else:
        target_name = str(record["target_name"]) if record["target_name"] else "Unknown"

        net.add_node(
            target_id,
            label=target_name,
            color="#999999",
            title=f"Node: {target_name}"
        )

        net.add_edge(source_id, target_id, label=rel_type)

# Save graph to html and show it
path = "graph.html"
net.save_graph(path)

with open(path, "r", encoding="utf-8") as f:
    components.html(f.read(), height=650, scrolling=True)

# EVIDENCE PANEL
st.markdown("---")
st.subheader("📄 Evidence Panel")

if records:
    shown = False
    for record in records:
        if "Claim" in (record["target_labels"] or []):
            shown = True
            claim_text = str(record["claim_text"]) if record["claim_text"] else "No claim text"
            quote = str(record["quote"]) if record["quote"] else "No evidence available"
            source = str(record["source"]) if record["source"] else "Unknown source"
            created_at = str(record["created_at"]) if record["created_at"] else "Unknown date"

            with st.expander(f"Claim: {claim_text[:100]}..."):
                st.write(f"**Evidence Quote:** *\"{quote}\"*")
                st.caption(f"**Source File:** {source}")
                st.caption(f"**Created At:** {created_at}")

    if not shown:
        st.info("No claim nodes found for this filter.")
else:
    st.info("No records found. Adjust your filters to explore the graph.")
