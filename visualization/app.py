from __future__ import annotations

import os
import tempfile
from typing import Any, Dict, List

import streamlit as st
import streamlit.components.v1 as components
from neo4j import GraphDatabase
from pyvis.network import Network


class GraphVizApp:
    def __init__(self, uri: str, auth: tuple[str, str]) -> None:
        # Initialize the connection to Neo4j for the Streamlit frontend.
        self.driver = GraphDatabase.driver(uri, auth=auth)

    def shutdown(self) -> None:
        # Close the driver connection when the app session ends.
        self.driver.close()

    def get_graph_data(self, entity_filter: str = "", limit: int = 50) -> List[Dict[str, Any]]:
        # This Cypher query is the heart of the visualization.
        # I designed it to filter across entities, names, and claim text 
        # so you get a broad search result from a single input box.
        query = """
        MATCH (e:Entity)-[r]->(target)
        WHERE $filter = ""
           OR toLower(e.name) CONTAINS toLower($filter)
           OR (target.name IS NOT NULL AND toLower(target.name) CONTAINS toLower($filter))
           OR (target.text IS NOT NULL AND toLower(target.text) CONTAINS toLower($filter))
        RETURN
            elementId(e) AS source_id,
            e.name AS source_name,
            e.label AS source_label,
            type(r) AS rel_type,
            elementId(target) AS target_id,
            labels(target) AS target_labels,
            target.name AS target_name,
            target.text AS claim_text,
            target.quote AS quote,
            target.file AS source_file,
            target.event_time AS event_time,
            target.confidence AS confidence
        LIMIT $limit
        """
        with self.driver.session() as session:
            return [dict(record) for record in session.run(query, filter=entity_filter, limit=limit)]

    def get_graph_stats(self) -> Dict[str, int]:
        # Fetch real-time counts to display in the sidebar metrics.
        query = """
        RETURN
            COUNT { MATCH (:Document) } AS documents,
            COUNT { MATCH (:Entity) } AS entities,
            COUNT { MATCH (:Claim) } AS claims,
            COUNT { MATCH ()-[r]->() } AS edges
        """
        with self.driver.session() as session:
            record = session.run(query).single()
            return dict(record) if record else {"documents": 0, "entities": 0, "claims": 0, "edges": 0}


def build_app_from_env() -> GraphVizApp:
    # You must set your environment variables for the app to connect to the database.
    uri = os.getenv("NEO4J_URI")
    username = os.getenv("NEO4J_USERNAME")
    password = os.getenv("NEO4J_PASSWORD")

    if not uri or not username or not password:
        raise ValueError(
            "Missing Neo4j credentials. Set NEO4J_URI, NEO4J_USERNAME, and NEO4J_PASSWORD."
        )

    return GraphVizApp(uri, (username, password))


def build_network(records: List[Dict[str, Any]], show_claims: bool = True) -> Network:
    # I'm using Pyvis here to create an interactive HTML-based graph.
    # I chose a dark theme (#111111) to make the node colors pop.
    net = Network(
        height="650px",
        width="100%",
        bgcolor="#111111",
        font_color="white",
        directed=True,
    )

    added_nodes = set()

    for record in records:
        source_id = str(record["source_id"])
        target_id = str(record["target_id"])
        source_name = str(record["source_name"] or "Unknown Entity")
        source_label = str(record["source_label"] or "ENTITY")
        rel_type = str(record["rel_type"] or "RELATED_TO")
        target_labels = record.get("target_labels") or []

        # Add the source entity node.
        if source_id not in added_nodes:
            net.add_node(
                source_id,
                label=source_name,
                color="#00d4ff",
                title=f"Entity: {source_name}<br>Type: {source_label}",
            )
            added_nodes.add(source_id)

        # Handle nodes labeled as 'Claim' differently by changing their color to yellow.
        if "Claim" in target_labels:
            if not show_claims:
                continue

            claim_text = str(record.get("claim_text") or "No claim text")
            short_label = claim_text[:40] + "..." if len(claim_text) > 40 else claim_text
            quote = str(record.get("quote") or "")
            source_file = str(record.get("source_file") or "Unknown source")
            confidence = record.get("confidence")
            event_time = record.get("event_time")

            if target_id not in added_nodes:
                # I built these tooltips so you can see the evidence without 
                # leaving the graph view.
                tooltip = f"Claim: {claim_text}<br>Source: {source_file}"
                if quote:
                    tooltip += f"<br>Quote: {quote}"
                if confidence is not None:
                    tooltip += f"<br>Confidence: {confidence}"
                if event_time:
                    tooltip += f"<br>Event Time: {event_time}"

                net.add_node(
                    target_id,
                    label=short_label,
                    color="#ffcc00",
                    title=tooltip,
                )
                added_nodes.add(target_id)

            net.add_edge(source_id, target_id, label=rel_type)

        else:
            # Handle regular entity-to-entity connections.
            target_name = str(record.get("target_name") or "Unknown")
            target_type = ",".join(target_labels) if target_labels else "NODE"

            if target_id not in added_nodes:
                net.add_node(
                    target_id,
                    label=target_name,
                    color="#999999",
                    title=f"Node: {target_name}<br>Labels: {target_type}",
                )
                added_nodes.add(target_id)

            net.add_edge(source_id, target_id, label=rel_type)

    # I fine-tuned the physics engine here so the graph spreads out 
    # nicely instead of clumping together in a ball.
    net.set_options("""
    const options = {
      "nodes": {
        "shape": "dot",
        "size": 18,
        "font": {"size": 14}
      },
      "edges": {
        "arrows": {"to": {"enabled": true}},
        "font": {"size": 12},
        "smooth": false
      },
      "physics": {
        "enabled": true,
        "barnesHut": {
          "gravitationalConstant": -3000,
          "springLength": 140
        }
      }
    }
    """)
    return net


def render_network(net: Network) -> None:
    # Save the graph to a temporary HTML file so Streamlit can render it in an iframe.
    with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp_file:
        net.save_graph(tmp_file.name)
        html_path = tmp_file.name

    with open(html_path, "r", encoding="utf-8") as f:
        components.html(f.read(), height=700, scrolling=True)


def render_evidence_panel(records: List[Dict[str, Any]]) -> None:
    # I added this panel below the graph to show the detailed text for 
    # every claim currently visible in the search results.
    st.markdown("---")
    st.subheader("Evidence Panel")

    claim_records = [r for r in records if "Claim" in (r.get("target_labels") or [])]

    if not claim_records:
        st.info("No claim nodes found for this filter.")
        return

    for record in claim_records:
        claim_text = str(record.get("claim_text") or "No claim text")
        quote = str(record.get("quote") or "No evidence available")
        source_file = str(record.get("source_file") or "Unknown source")
        confidence = record.get("confidence")
        event_time = record.get("event_time")

        title = claim_text[:100] + ("..." if len(claim_text) > 100 else "")
        # Use expanders to keep the UI clean when dealing with many results.
        with st.expander(f"Claim: {title}"):
            st.write(f"**Evidence Quote:** \"{quote}\"")
            st.write(f"**Source File:** {source_file}")
            if confidence is not None:
                st.write(f"**Confidence:** {confidence}")
            if event_time:
                st.write(f"**Event Time:** {event_time}")


def main() -> None:
    # Set up the main Streamlit page layout.
    st.set_page_config(layout="wide", page_title="Enron Memory Explorer")
    st.title("Enron Memory Graph Explorer")
    st.caption("Explore extracted entities, claims, relationships, and grounded evidence.")

    try:
        app = build_app_from_env()
    except Exception as e:
        st.error(str(e))
        st.stop()

    try:
        # Display graph statistics and filters in the sidebar.
        stats = app.get_graph_stats()

        st.sidebar.header("Filters & Search")
        search_term = st.sidebar.text_input("Search entity or claim", "")
        show_claims = st.sidebar.checkbox("Show claim nodes", value=True)
        max_records = st.sidebar.slider("Max graph records", min_value=10, max_value=100, value=50, step=10)

        st.sidebar.markdown("---")
        st.sidebar.metric("Documents", stats["documents"])
        st.sidebar.metric("Entities", stats["entities"])
        st.sidebar.metric("Claims", stats["claims"])
        st.sidebar.metric("Edges", stats["edges"])

        # Fetch data based on your sidebar inputs.
        records = app.get_graph_data(search_term, limit=max_records)

        if not records:
            st.info("No records found. Adjust your search or load more data into the graph.")
            return

        # Execute the build and render pipeline.
        net = build_network(records, show_claims=show_claims)
        render_network(net)
        render_evidence_panel(records)

    finally:
        # Ensure the driver is always shut down when the app finishes.
        app.shutdown()


if __name__ == "__main__":
    main()