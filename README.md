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

3. **Deduplication Strategy**:
- **Entity Resolution**: MERGE operation in Cypher for case-insensitive entity resolution (e.g., 'Sanders' & 'sanders' become one node).
- **Relationship Logic**: Relationships contain timestamps for 'last_seen' to account for changing information.


## How the prototype can adapt to target enviorements

How this architecture adapts to **Slack, Teams, Jira, and Linear**.

---

### **1. Unstructured + Structured Fusion**

In a corporate environment, I would evolve the ontology to include **Anchor Nodes** for structured systems.

**The Connection**

A Slack thread mentioning a bug would be linked via a **`REFERENCES` edge** to a **Jira Ticket Node**.

**The Benefit**

This allows users to ask:

> *"What was the sentiment behind the delay on ticket L10-402?"*

The system can answer by **traversing from the structured ticket to the unstructured chat messages**.

---

### **2. Long-term Memory & Drift**

**Durable vs. Ephemeral**

- **Durable memories:** Technical decisions and project milestones  
- **Ephemeral memories:** Water-cooler chat or “meeting soon” messages  

Ephemeral messages would be assigned a **Time-To-Live (TTL)**.

**Preventing Drift**

A **Conflict Resolution Layer** would be implemented.

If a newer email contradicts an older one, the graph creates a:
**`SUPERSEDES` relationship**

This preserves the **historical audit trail** instead of deleting data.  
It allows the AI system to **explain why a decision changed over time**, rather than losing earlier context.

---

## 🔐 Grounding, Safety, & Permissions

### **Hard Citations**

Every response must include **provenance**.

If a user asks about a project, the UI displays the exact:

- Slack deep-link
- Document URL
- Email source

These act as the **source of truth** for the answer.

---

### **Auth-Gated Retrieval**

To enforce access control, I would implement **Row-Level Security (RLS)** in the graph.

The Cypher query would be dynamically modified at runtime:

```cypher
WHERE node.access_level IN $user_permissions

