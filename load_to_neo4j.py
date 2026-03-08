# I'm getting unauthorization error again and again. 
# Things I have tried to clear the error already - URI and Auth double checked, 
# I think I should see if the URI/Auth credentials are not changed after I downloaded them 

import os
import json
from neo4j import GraphDatabase

# Credentials - need to verify these in the Aura console if it keeps failing
URI = "neo4j+s://31903a0a.databases.neo4j.io"
AUTH = ("neo4j", "TpY6hVOY8sB6Lei6rrQm1dZbVpldKuf7X1PfgS5o-gc")

class EnronGraphManager:
    def __init__(self, uri, auth):
        # Setting up the driver connection here
        self.driver = GraphDatabase.driver(uri, auth=auth)

    def shutdown(self):
        # Closing the connection
        self.driver.close()

    def process_json_data(self, file_path):
        # Checking if the json file is actually there before starting
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return

        with open(file_path, 'r') as f:
            data = json.load(f)

        with self.driver.session() as session:
            for entry in data:
                # I have to add relationship links
                for r in entry.get('relationships', []):
                    f_name = entry.get('metadata', {}).get('file')
                    session.execute_write(self._add_relation, r, f_name)
                
                # I have to add specific claims and evidences
                for c in entry.get('claims', []):
                    session.execute_write(self._add_claim, c)

    @staticmethod
    def _add_relation(tx, rel, source_file):
        # MERGE helps to avoid creating the same person twice
        cypher = """
        MERGE (n1:Entity {name: $sub})
        MERGE (n2:Entity {name: $obj})
        MERGE (n1)-[r:RELATION {type: $rel_type}]->(n2)
        SET r.source = $src
        """
        tx.run(cypher, sub=rel['source_entity'], obj=rel['target_entity'], 
               rel_type=rel['relation_type'], src=source_file)

    @staticmethod
    def _add_claim(tx, claim):
        # Creating claim nodes and linking them to entities
        cypher = """
        MERGE (e:Entity {name: $subject})
        CREATE (c:Claim {
            text: $fact,
            quote: $evidence,
            file: $source_file
        })
        CREATE (e)-[:HAS_CLAIM]->(c)
        """
        tx.run(cypher, subject=claim['subject'], fact=claim['fact'], 
               evidence=claim['evidence_quote'], source_file=claim['source_file'])

if __name__ == "__main__":
    # Pointing to the file created in Task 3
    path_to_data = os.path.join("data", "extracted_memories.json")
    
    manager = None
    try:
        print("Connecting to Neo4j instance...")
        manager = EnronGraphManager(URI, AUTH)
        
        print(f"Loading data from: {path_to_data}")
        manager.process_json_data(path_to_data)
        
        print("Upload complete.")
        
    except Exception as error:
        # If this still shows 'Unauthorized', I need to reset the Aura password
        print(f"Upload failed: {error}")
    finally:
        # Making sure the driver closes no matter what happens
        if manager:
            manager.shutdown()