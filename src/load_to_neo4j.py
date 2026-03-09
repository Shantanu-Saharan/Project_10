# I'm getting unauthorization error again and again. 
# Things I have tried to clear the error already - URI and Auth double checked, 
# I think I should see if the URI/Auth credentials are not changed after I downloaded them 

# I have changed the URI na Auth to a new one and now the loading works fine.

import os
import json
import logging
from datetime import datetime
from neo4j import GraphDatabase

URI = "neo4j+s://4266d4ef.databases.neo4j.io"
AUTH = ("4266d4ef", "S9cieujK6_0eSAO97NdfWi0kIxAn6_FSoqO-Q2kntA8")

logging.basicConfig(level=logging.INFO)

class MemoryGraphManager:

    def __init__(self, uri, auth):
        self.driver = GraphDatabase.driver(uri, auth=auth)

    def shutdown(self):
        self.driver.close()

    def process_json_data(self, file_path):

        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return

        with open(file_path, "r") as f:
            data = json.load(f)

        entity_count = 0
        claim_count = 0
        relation_count = 0

        with self.driver.session() as session:

            for entry in data:

                source_file = entry.get("metadata", {}).get("file", "unknown")

                # Create document node
                session.execute_write(self._create_document, source_file)

                # Relationships
                for r in entry.get("relationships", []):
                    session.execute_write(self._add_relation, r, source_file)
                    relation_count += 1
                    entity_count += 2

                # Claims
                for c in entry.get("claims", []):
                    session.execute_write(self._add_claim, c, source_file)
                    claim_count += 1
                    entity_count += 1
        with self.driver.session() as session:
            total_entities = session.execute_read(self._count_entities)

        logging.info(f"Entities in graph: {total_entities}")
        logging.info(f"Claims processed: {claim_count}")
        logging.info(f"Relations processed: {relation_count}")

    @staticmethod
    def _create_document(tx, file):

        cypher = """
        MERGE (d:Document {file:$file})
        ON CREATE SET
            d.access_level = "internal",
            d.created_at = datetime()
        """

        tx.run(cypher, file=file)

    @staticmethod
    def _count_entities(tx):
        result = tx.run("MATCH (e:Entity) RETURN count(e) AS total")
        return result.single()["total"]

    @staticmethod
    def _count_entities(tx):
        result = tx.run("MATCH (e:Entity) RETURN count(e) AS total")
        return result.single()["total"]

    @staticmethod
    def _add_relation(tx, rel, source_file):

        cypher = """
        MERGE (e1:Entity {name:$sub})
        MERGE (e2:Entity {name:$obj})

        MERGE (e1)-[r:RELATION {type:$type}]->(e2)
        ON CREATE SET r.source=$src
        """

        tx.run(
            cypher,
            sub=rel["source_entity"],
            obj=rel["target_entity"],
            type=rel["relation_type"],
            src=source_file,
        )

    @staticmethod
    def _add_claim(tx, claim, source_file):

        cypher = """
        MERGE (e:Entity {name:$subject})

        CREATE (c:Claim {
            text:$fact,
            quote:$quote,
            file:$file,
            event_time:$event_time,
            created_at:datetime(),
            status:"active"
        })

        MERGE (e)-[:HAS_CLAIM]->(c)

        MERGE (d:Document {file:$file})
        MERGE (d)-[:SUPPORTS]->(c)
        """

        tx.run(
            cypher,
            subject=claim["subject"],
            fact=claim["fact"],
            quote=claim["evidence_quote"],
            file=source_file,
            event_time=datetime.now().isoformat(),
        )


if __name__ == "__main__":

    path_to_data = os.path.join("data", "extracted_memories.json")

    manager = None

    try:
        print("Connecting to Neo4j...")
        manager = MemoryGraphManager(URI, AUTH)

        print("Uploading memory graph...")
        manager.process_json_data(path_to_data)

        print("Upload complete.")

    except Exception as e:
        print(f"Upload failed: {e}")

    finally:
        if manager:
            manager.shutdown()
