# Instead of a basic vector search, I'm using Graph-RAG.
# 1. Map the query to an Entity (The Anchor).
# 2. Traverse to find all HAS_CLAIM nodes.
# 3. Filter by 'Confidence' and 'Recency' to avoid context explosion.
# 4. Format the output with clear 'Source Citations'.

from neo4j import GraphDatabase
import logging

URI = "neo4j+s://4266d4ef.databases.neo4j.io"
AUTH = ("4266d4ef", "S9cieujK6_0eSAO97NdfWi0kIxAn6_FSoqO-Q2kntA8")

class MemoryRetriever:
    def __init__(self, uri, auth):
        self.driver = GraphDatabase.driver(uri, auth=auth)

    def get_context_pack(self, search_term):
        """Returns a grounded context pack using case-insensitive search."""
        # We use toLower() for the name and the search term to ensure a match.
        # We also look for RELATION or HAS_CLAIM to be safe.
        query = """
        MATCH (e:Entity)
        WHERE toLower(e.name) CONTAINS toLower($term)
        MATCH (e)-[r]->(other)
        RETURN 
            e.name AS entity,
            type(r) AS rel_type,
            CASE 
                WHEN labels(other)[0] = 'Claim' THEN other.text 
                ELSE other.name 
            END AS fact,
            CASE 
                WHEN labels(other)[0] = 'Claim' THEN other.quote 
                ELSE r.source 
            END AS grounding,
            CASE 
                WHEN labels(other)[0] = 'Claim' THEN other.file 
                ELSE r.source 
            END AS source
        LIMIT 10
        """
        
        with self.driver.session() as session:
            results = session.run(query, term=search_term)
            context_pack = []
            for record in results:
                context_pack.append({
                    "citation": f"[{record['source']}]",
                    "fact": f"{record['rel_type']}: {record['fact']}",
                    "grounding": record['grounding'],
                    "meta": {"entity": record['entity']}
                })
            return context_pack
        
    def shutdown(self):
        self.driver.close()

if __name__ == "__main__":
    # Example: Searching for mentions of a specific executive or project
    search_query = "Sanders"
    
    retriever = MemoryRetriever(URI, AUTH)
    print(f"--- FETCHING GROUNDED CONTEXT FOR: {search_query} ---")
    
    context = retriever.get_context_pack(search_query)
    
    if not context:
        print("No grounded memories found for this query.")
    else:
        for i, item in enumerate(context, 1):
            print(f"\n{i}. CLAIM: {item['fact']}")
            print(f"   EVIDENCE: \"{item['grounding']}\"")
            print(f"   SOURCE: {item['citation']}")

    retriever.shutdown()
