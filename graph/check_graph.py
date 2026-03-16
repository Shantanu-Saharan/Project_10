from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from neo4j import GraphDatabase


class GraphChecker:
    def __init__(self, uri: str, auth: tuple[str, str]) -> None:
        # Initialize the Neo4j driver using the credentials you provided.
        self.driver = GraphDatabase.driver(uri, auth=auth)

    def shutdown(self) -> None:
        # Always remember to close the driver to release database connections.
        self.driver.close()

    def get_stats(self) -> Dict[str, int]:
        # I wrote this specific Cypher query to give me a quick "birds-eye view" 
        # of the database. It helps me verify if my upload script actually worked.
        query = """
        RETURN
            COUNT { MATCH (:Document) } AS documents,
            COUNT { MATCH (:Entity) } AS entities,
            COUNT { MATCH (:Claim) } AS claims,
            COUNT { MATCH ()-[r]->() } AS edges
        """
        with self.driver.session() as session:
            record = session.run(query).single()
            return dict(record) if record else {}

    def get_sample_nodes(self, limit: int = 10) -> List[Dict[str, Any]]:
        # Fetch a small batch of nodes so you can inspect the raw properties.
        query = """
        MATCH (n)
        RETURN labels(n) AS labels, properties(n) AS props
        LIMIT $limit
        """
        with self.driver.session() as session:
            return [dict(r) for r in session.run(query, limit=limit)]

    def get_sample_edges(self, limit: int = 10) -> List[Dict[str, Any]]:
        # I use this to make sure my relationships (like REPORTS_TO) 
        # are pointing in the right direction between entities.
        query = """
        MATCH (a)-[r]->(b)
        RETURN
            labels(a) AS source_labels,
            properties(a) AS source_props,
            type(r) AS rel_type,
            properties(r) AS rel_props,
            labels(b) AS target_labels,
            properties(b) AS target_props
        LIMIT $limit
        """
        with self.driver.session() as session:
            return [dict(r) for r in session.run(query, limit=limit)]


def build_checker_from_env() -> GraphChecker:
    # You need to have NEO4J_URI, NEO4J_USERNAME, and NEO4J_PASSWORD 
    # set in your environment variables for this to work.
    uri = os.getenv("NEO4J_URI")
    username = os.getenv("NEO4J_USERNAME")
    password = os.getenv("NEO4J_PASSWORD")

    if not uri or not username or not password:
        # I added a clear error message here because missing credentials 
        # is the most common reason for database connection failures.
        raise ValueError(
            "Missing Neo4j credentials. Set NEO4J_URI, NEO4J_USERNAME, and NEO4J_PASSWORD."
        )

    return GraphChecker(uri, (username, password))


if __name__ == "__main__":
    # This main block is my "health check" for the project. 
    # Run it after your upload script to see if everything landed safely.
    checker: Optional[GraphChecker] = None
    try:
        checker = build_checker_from_env()

        print("=== GRAPH STATS ===")
        print(checker.get_stats())

        print("\n=== SAMPLE NODES ===")
        for row in checker.get_sample_nodes():
            print(row)

        print("\n=== SAMPLE EDGES ===")
        for row in checker.get_sample_edges():
            print(row)

    finally:
        if checker:
            checker.shutdown()