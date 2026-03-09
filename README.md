Enron Memory Graph-RAG Explorer
An intelligent memory graph that transforms unstructured email communication into a grounded, queryable knowledge base using Neo4j and Streamlit.

Design & Methodology
1. Ontology & Data Model
The system uses a Bipartite Graph Structure:

Nodes: Categorized as Entity (People/Organizations) and Claim (Assertions/Statements extracted from text).

Edges: Relationship types include MENTIONS, HAS_CLAIM, and WORKS_FOR.

The "Grounding" Layer: Every Claim node stores a quote and source_file property, ensuring the AI can never hallucinate without a "receipt."

2. Extraction & Canonicalization (Dedup)
Extraction Contract: We use a JSON schema enforcement to ensure the LLM extracts atomic claims. Every claim must have a direct quote for provenance.

Deduplication Strategy:

Entity Resolution: We use case-insensitive MERGE operations in Cypher to collapse multiple mentions (e.g., "Sanders" vs "sanders") into a single unique node.

Relationship Logic: Relationships are updated with last_seen timestamps to handle evolving information.
