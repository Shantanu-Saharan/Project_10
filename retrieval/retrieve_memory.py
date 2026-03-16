from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from neo4j import GraphDatabase


DEFAULT_LIMIT = 10


class MemoryRetriever:
    def __init__(self, uri: str, auth: tuple[str, str]) -> None:
        self.driver = GraphDatabase.driver(uri, auth=auth)

    def shutdown(self) -> None:
        self.driver.close()

    def get_context_pack(self, search_term: str, limit: int = DEFAULT_LIMIT) -> List[Dict[str, Any]]:
        """
        Retrieve grounded context for an entity-like search term.
        Returns a mixed context pack of claims and relations.
        """
        with self.driver.session() as session:
            claim_results = session.execute_read(self._fetch_claims, search_term, limit)
            relation_results = session.execute_read(self._fetch_relations, search_term, limit)

        combined = claim_results + relation_results

        seen = set()
        deduped = []
        for item in combined:
            key = (
                item.get("type"),
                item.get("entity"),
                item.get("fact"),
                item.get("source"),
            )
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)

        return deduped[:limit]

    @staticmethod
    def _fetch_claims(tx, search_term: str, limit: int) -> List[Dict[str, Any]]:
        query = """
        MATCH (e:Entity)-[:HAS_CLAIM]->(c:Claim)
        WHERE toLower(e.name) CONTAINS toLower($term)
        RETURN
            e.name AS entity,
            c.text AS fact,
            c.quote AS evidence,
            c.file AS source,
            c.confidence AS confidence,
            c.event_time AS event_time
        ORDER BY coalesce(c.confidence, 0.0) DESC
        LIMIT $limit
        """
        result = tx.run(query, term=search_term, limit=limit)
        return [
            {
                "type": "claim",
                "entity": record["entity"],
                "fact": record["fact"],
                "evidence": record["evidence"],
                "source": record["source"],
                "confidence": record["confidence"],
                "event_time": record["event_time"],
                "citation": f"[{record['source']}]",
            }
            for record in result
        ]

    @staticmethod
    def _fetch_relations(tx, search_term: str, limit: int) -> List[Dict[str, Any]]:
        query = """
        MATCH (e:Entity)-[r:RELATION]->(other:Entity)
        WHERE toLower(e.name) CONTAINS toLower($term)
        OR toLower(other.name) CONTAINS toLower($term)
        RETURN
            e.name AS entity,
            r.type AS rel_type,
            other.name AS other_entity,
            '' AS evidence,
            r.source_file AS source
        LIMIT $limit
        """
        result = tx.run(query, term=search_term, limit=limit)
        return [
            {
                "type": "relation",
                "entity": record["entity"],
                "fact": f"{record['entity']} -[{record['rel_type']}]-> {record['other_entity']}",
                "evidence": record["evidence"],
                "source": record["source"],
                "confidence": None,
                "event_time": None,
                "citation": f"[{record['source']}]",
            }
            for record in result
        ]


def build_retriever_from_env() -> MemoryRetriever:
    uri = os.getenv("NEO4J_URI")
    username = os.getenv("NEO4J_USERNAME")
    password = os.getenv("NEO4J_PASSWORD")

    if not uri or not username or not password:
        raise ValueError(
            "Missing Neo4j credentials. Set NEO4J_URI, NEO4J_USERNAME, and NEO4J_PASSWORD."
        )

    return MemoryRetriever(uri, (username, password))


def print_context_pack(search_query: str, context: List[Dict[str, Any]]) -> None:
    print(f"\n--- FETCHING GROUNDED CONTEXT FOR: {search_query} ---")

    if not context:
        print("No grounded memories found for this query.")
        return

    for i, item in enumerate(context, 1):
        print(f"\n{i}. TYPE: {item['type'].upper()}")
        print(f"   ENTITY: {item['entity']}")
        print(f"   FACT: {item['fact']}")
        if item.get("evidence"):
            print(f"   EVIDENCE: \"{item['evidence']}\"")
        print(f"   SOURCE: {item['citation']}")
        if item.get("confidence") is not None:
            print(f"   CONFIDENCE: {item['confidence']}")
        if item.get("event_time"):
            print(f"   EVENT TIME: {item['event_time']}")


if __name__ == "__main__":
    search_query = input("Enter a search term: ").strip()

    retriever: Optional[MemoryRetriever] = None
    try:
        retriever = build_retriever_from_env()
        context = retriever.get_context_pack(search_query)
        print_context_pack(search_query, context)
    finally:
        if retriever:
            retriever.shutdown()