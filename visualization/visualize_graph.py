from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from neo4j import GraphDatabase
from pyvis.network import Network

# I've set the output path to a dedicated 'output' folder to keep the 
# repository root clean for other users.
OUTPUT_PATH = Path("output") / "enron_knowledge_graph.html"


class GraphVisualizer:
    def __init__(self, uri: str, auth: tuple[str, str]) -> None:
        # Initialize the Neo4j driver.
        self.driver = GraphDatabase.driver(uri, auth=auth)

    def shutdown(self) -> None:
        # Always close the driver connection to prevent memory leaks.
        self.driver.close()

    def fetch_graph_records(self, limit: int = 100) -> List[Dict[str, Any]]:
        # This Cypher query fetches nodes and their relationships.
        # I used coalesce here to ensure the visualizer always has a label 
        # to display, prioritizing the name over the raw text or file path.
        query = """
        MATCH (a)-[r]->(b)
        RETURN
            elementId(a) AS source_id,
            labels(a) AS source_labels,
            coalesce(a.name, a.file, a.text, 'Unknown') AS source_label,
            type(r) AS rel_type,
            elementId(b) AS target_id,
            labels(b) AS target_labels,
            coalesce(b.name, b.file, b.text, 'Unknown') AS target_label
        LIMIT $limit
        """
        with self.driver.session() as session:
            return [dict(r) for r in session.run(query, limit=limit)]

    def export_html(self, output_path: Path, limit: int = 100) -> None:
        """
        Generate a standalone HTML file containing the interactive network.
        """
        records = self.fetch_graph_records(limit=limit)

        # I chose Pyvis for the export because it creates a fully interactive 
        # HTML file that doesn't require a backend server to view.
        net = Network(height="750px", width="100%", bgcolor="#111111", font_color="white", directed=True)
        added_nodes = set()

        for record in records:
            source_id = str(record["source_id"])
            target_id = str(record["target_id"])
            source_label = str(record["source_label"])
            target_label = str(record["target_label"])
            rel_type = str(record["rel_type"])
            source_labels = record.get("source_labels") or []
            target_labels = record.get("target_labels") or []

            # I'm using a color-coding system here to help you distinguish 
            # between Entities (blue) and Claims (green) at a glance.
            if source_id not in added_nodes:
                net.add_node(
                    source_id,
                    label=source_label[:40], # Truncate labels so the graph stays readable.
                    title=f"Labels: {source_labels}<br>Value: {source_label}",
                    color="#00d4ff" if "Entity" in source_labels else "#88ffaa" if "Claim" in source_labels else "#bbbbbb",
                )
                added_nodes.add(source_id)

            if target_id not in added_nodes:
                net.add_node(
                    target_id,
                    label=target_label[:40],
                    title=f"Labels: {target_labels}<br>Value: {target_label}",
                    color="#00d4ff" if "Entity" in target_labels else "#88ffaa" if "Claim" in target_labels else "#bbbbbb",
                )
                added_nodes.add(target_id)

            net.add_edge(source_id, target_id, label=rel_type)

        # Create the directory if it doesn't exist before saving.
        output_path.parent.mkdir(parents=True, exist_ok=True)
        net.save_graph(str(output_path))


def build_visualizer_from_env() -> GraphVisualizer:
    # You'll need to make sure your .env file is active so these pull correctly.
    uri = os.getenv("NEO4J_URI")
    username = os.getenv("NEO4J_USERNAME")
    password = os.getenv("NEO4J_PASSWORD")

    if not uri or not username or not password:
        raise ValueError(
            "Missing Neo4j credentials. Set NEO4J_URI, NEO4J_USERNAME, and NEO4J_PASSWORD."
        )

    return GraphVisualizer(uri, (username, password))


if __name__ == "__main__":
    # This block allows you to run the script standalone to generate a snapshot.
    visualizer: Optional[GraphVisualizer] = None
    try:
        visualizer = build_visualizer_from_env()
        visualizer.export_html(OUTPUT_PATH, limit=100)
        print(f"Saved graph HTML to: {OUTPUT_PATH}")
    finally:
        if visualizer:
            visualizer.shutdown()