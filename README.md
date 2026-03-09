# Enron Memory Graph RAG Explorer
An intelligent memory graph that transforms unstructured email communication into a grounded knowledge base, leveraging Neo4j and Streamlit.

### Design & Methodology
1. **Ontology & Data Model**
Our Bipartite Graph Structure:
- **Nodes**: Entities (People/Organizations) & Claims (Assertions/Statements extracted from text).
- **Edges**: Relationship types include MENTIONS, HAS_CLAIM, WORKS_FOR.

**Grounding**:
Each Claim node has a quote property & a source_file property. This way, our AI cannot fabricate without a receipt.

2. **Extraction & Canonicalization (Dedup)**
**Extraction Contract**: JSON Schema enforcement for LLM extraction. Each claim must be atomic & contain a direct quote.

**Deduplication Strategy**:
- **Entity Resolution**: MERGE operation in Cypher for case-insensitive entity resolution (e.g., 'Sanders' & 'sanders' become one node).
- **Relationship Logic**: Relationships contain timestamps for 'last_seen' to account for changing information.
