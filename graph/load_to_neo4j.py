from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from neo4j import GraphDatabase

# I'm using logging here instead of just print statements. 
# It makes it much easier to track long-running uploads on GitHub.
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

DEFAULT_INPUT_PATH = Path("data") / "processed" / "deduped_memories.json"


class MemoryGraphManager:
    def __init__(self, uri: str, auth: tuple[str, str]) -> None:
        # Establish the connection to your Neo4j instance.
        self.driver = GraphDatabase.driver(uri, auth=auth)

    def shutdown(self) -> None:
        # Close the connection safely when you are done.
        self.driver.close()

    def process_json_data(self, file_path: Path) -> None:
        """
        Read the JSON file and coordinate the database upload.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            raise ValueError("Expected a list of extracted records.")

        entity_count = 0
        claim_count = 0
        relation_count = 0
        document_count = 0

        # I use a single session for the loop to keep the process efficient.
        with self.driver.session() as session:
            for entry in data:
                source_file = self._get_source_file(entry)
                if not source_file:
                    continue

                # Step 1: Create the parent Document node.
                session.execute_write(self._create_document, source_file)
                document_count += 1

                # Step 2: Upload entities and link them to the document.
                for entity in entry.get("entities", []):
                    if self._is_valid_entity(entity):
                        session.execute_write(self._add_entity, entity, source_file)
                        entity_count += 1

                # Step 3: Create relationships between entities.
                for rel in entry.get("relationships", []):
                    if self._is_valid_relationship(rel):
                        session.execute_write(self._add_relationship, rel, source_file)
                        relation_count += 1

                # Step 4: Create standalone claims linked to entities.
                for claim in entry.get("claims", []):
                    if self._is_valid_claim(claim):
                        session.execute_write(self._add_claim, claim, source_file)
                        claim_count += 1

        # After the upload, I fetch the counts to show you the final graph state.
        with self.driver.session() as session:
            totals = session.execute_read(self._get_graph_counts)

        logging.info("Documents processed: %s", document_count)
        logging.info("Entities processed: %s", entity_count)
        logging.info("Claims processed: %s", claim_count)
        logging.info("Relationships processed: %s", relation_count)
        logging.info("Graph totals: %s", totals)

    @staticmethod
    def _get_source_file(entry: Dict[str, Any]) -> str:
        # Fallback logic to find the file ID regardless of which processing script generated it.
        return (
            entry.get("email_id")
            or entry.get("metadata", {}).get("file")
            or "unknown"
        )

    @staticmethod
    def _is_valid_entity(entity: Dict[str, Any]) -> bool:
        # Simple validation: you don't want empty nodes in your graph.
        name = str(entity.get("name", "")).strip()
        label = str(entity.get("label", "")).strip()
        return bool(name and label)

    @staticmethod
    def _is_valid_relationship(rel: Dict[str, Any]) -> bool:
        source_entity = str(rel.get("source_entity", "")).strip()
        target_entity = str(rel.get("target_entity", "")).strip()
        relation_type = str(rel.get("relation_type", "")).strip().upper()

        if not source_entity or not target_entity or not relation_type:
            return False
        # I check for 'NONE' because sometimes LLMs use it as a placeholder.
        if relation_type == "NONE":
            return False
        return True

    @staticmethod
    def _is_valid_claim(claim: Dict[str, Any]) -> bool:
        subject = str(claim.get("subject", "")).strip()
        fact = str(claim.get("fact", "")).strip()
        evidence_quote = str(claim.get("evidence_quote", "")).strip()

        if not subject or not fact or not evidence_quote:
            return False
        if subject.upper() == "UNKNOWN":
            return False
        return True

    @staticmethod
    def _create_document(tx, file: str) -> None:
        # I'm using MERGE here so that if the same file is processed twice,
        # it doesn't create duplicate Document nodes.
        cypher = """
        MERGE (d:Document {file: $file})
        ON CREATE SET
            d.access_level = "internal",
            d.created_at = datetime()
        """
        tx.run(cypher, file=file)

    @staticmethod
    def _add_entity(tx, entity: Dict[str, Any], source_file: str) -> None:
        # Create the entity and connect it to its source document in one transaction.
        cypher = """
        MERGE (e:Entity {name: $name})
        ON CREATE SET
            e.label = $label,
            e.created_at = datetime()
        ON MATCH SET
            e.label = coalesce(e.label, $label)

        MERGE (d:Document {file: $file})
        MERGE (d)-[:MENTIONS]->(e)
        """
        tx.run(
            cypher,
            name=entity["name"],
            label=entity["label"],
            file=source_file,
        )

    @staticmethod
    def _add_relationship(tx, rel: Dict[str, Any], source_file: str) -> None:
        # This creates the connection between two entities (e.g., PERSON -> REPORTS_TO -> PERSON).
        cypher = """
        MERGE (e1:Entity {name: $source_entity})
        ON CREATE SET e1.created_at = datetime()

        MERGE (e2:Entity {name: $target_entity})
        ON CREATE SET e2.created_at = datetime()

        MERGE (e1)-[r:RELATION {type: $relation_type}]->(e2)
        ON CREATE SET
            r.source_file = $source_file,
            r.evidence_quote = $evidence_quote,
            r.created_at = datetime()
        ON MATCH SET
            r.source_file = coalesce(r.source_file, $source_file),
            r.evidence_quote = coalesce(r.evidence_quote, $evidence_quote)

        MERGE (d:Document {file: $source_file})
        MERGE (d)-[:MENTIONS]->(e1)
        MERGE (d)-[:MENTIONS]->(e2)
        """
        tx.run(
            cypher,
            source_entity=rel["source_entity"],
            target_entity=rel["target_entity"],
            relation_type=rel["relation_type"],
            source_file=source_file,
            evidence_quote=rel.get("evidence_quote"),
        )

    @staticmethod
    def _add_claim(tx, claim: Dict[str, Any], source_file: str) -> None:
        # Link the subject entity to the specific claim node for better searchability.
        cypher = """
        MERGE (e:Entity {name: $subject})
        ON CREATE SET e.created_at = datetime()

        MERGE (c:Claim {
            subject: $subject,
            text: $fact,
            quote: $quote,
            file: $file
        })
        ON CREATE SET
            c.event_time = $event_time,
            c.confidence = $confidence,
            c.status = "active",
            c.created_at = datetime()
        ON MATCH SET
            c.event_time = coalesce(c.event_time, $event_time),
            c.confidence = coalesce(c.confidence, $confidence)

        MERGE (e)-[:HAS_CLAIM]->(c)

        MERGE (d:Document {file: $file})
        MERGE (d)-[:SUPPORTS]->(c)
        """
        tx.run(
            cypher,
            subject=claim["subject"],
            fact=claim["fact"],
            quote=claim["evidence_quote"],
            file=source_file,
            event_time=claim.get("timestamp"),
            confidence=claim.get("confidence"),
        )

    @staticmethod
    def _get_graph_counts(tx) -> Dict[str, int]:
        # Simple utility to count your nodes.
        cypher = """
        RETURN
            COUNT { MATCH (:Document) } AS documents,
            COUNT { MATCH (:Entity) } AS entities,
            COUNT { MATCH (:Claim) } AS claims
        """
        result = tx.run(cypher)
        return dict(result.single())

    @staticmethod
    def clear_graph(tx) -> None:
        # Use this with caution! It deletes everything in the database.
        tx.run("MATCH (n) DETACH DELETE n")


def main() -> None:
    # You must provide your Neo4j login details here.
    uri = os.getenv("NEO4J_URI")
    username = os.getenv("NEO4J_USERNAME")
    password = os.getenv("NEO4J_PASSWORD")

    if not uri or not username or not password:
        raise ValueError(
            "Missing Neo4j credentials. Set NEO4J_URI, NEO4J_USERNAME, and NEO4J_PASSWORD."
        )

    input_path = DEFAULT_INPUT_PATH

    manager: Optional[MemoryGraphManager] = None
    try:
        print("Connecting to Neo4j...")
        manager = MemoryGraphManager(uri, (username, password))

        print(f"Loading graph data from: {input_path}")
        manager.process_json_data(input_path)

        print("Upload complete.")

    except Exception as e:
        print(f"Upload failed: {e}")

    finally:
        if manager:
            manager.shutdown()


if __name__ == "__main__":
    main()