from neo4j import GraphDatabase

URI = "neo4j+s://4266d4ef.databases.neo4j.io"
AUTH = ("4266d4ef", "S9cieujK6_0eSAO97NdfWi0kIxAn6_FSoqO-Q2kntA8")

def check_entities():
    driver = GraphDatabase.driver(URI, auth=AUTH)
    with driver.session() as session:
        # This asks for a list of the first 10 names in our database
        result = session.run("MATCH (e:Entity) RETURN e.name LIMIT 10")
        names = [record["e.name"] for record in result]
        
        if not names:
            print("The graph is EMPTY. We need to re-run the upload script.")
        else:
            print(f"Entities found in graph: {names}")
    driver.close()

if __name__ == "__main__":
    check_entities()
