# Project_10: Grounded Long-Term Memory with Enron Emails

## Overview

This project implements a **grounded long-term memory system** using a subset of the Enron Email Dataset.  
The system converts unstructured email communication into a structured **memory graph** consisting of entities, relationships, and grounded claims.

The pipeline performs:

1. Structured information extraction using an LLM
2. Deduplication and canonicalization of extracted knowledge
3. Construction of a memory graph in Neo4j
4. Grounded retrieval of information with evidence citations
5. Interactive graph exploration through a Streamlit visualization interface

The goal is to demonstrate how scattered organizational communication can be transformed into **queryable, grounded long-term memory**.

---

# Dataset

This project uses a subset of the **Enron Email Dataset**, a widely used public dataset containing real organizational email communication.

Dataset Source:

https://www.cs.cmu.edu/~enron/

The dataset contains email threads involving employees, discussions, decisions, and organizational interactions, which makes it suitable for constructing a memory graph.

The subset used in this project is stored in:

data/raw/enron_sample.csv

---

# Repository Structure

Project_10/
│
├── README.md
├── requirements.txt
│
├── data/
│ ├── raw/
│ │   └── enron_sample.csv
│ └── processed/
│     ├── extracted_memories.json
│     ├── deduped_memories.json
│     └── retrieval_examples.json
│
├── output/
│   └── screenshots/
│
├── extraction/
│ ├── schema.py
│ ├── processor.py
│ └── extraction_pipeline.py
│
├── deduplication/
│ └── deduplication.py
│
├── graph/
│ ├── load_to_neo4j.py
│ └── check_graph.py
│
├── retrieval/
│ └── retrieve_memory.py
│
├── visualization/
│ ├── visualize_graph.py
│ └── app.py
│
└── docs/
└── design_notes.md

---

# System Architecture

The system follows a multi-stage pipeline.

Raw Emails
│
▼
Structured Extraction (LLM)
│
▼
Deduplication & Canonicalization
│
▼
Memory Graph Construction (Neo4j)
│
▼
Graph-Based Retrieval
│
▼
Interactive Visualization

Each component of the pipeline is designed to maintain **grounding and traceability to original evidence sources**.

---

# Features

## Structured Extraction

Emails are processed using an LLM to extract structured information including:

- Entities (people, organizations, dates, projects)
- Relationships between entities
- Grounded claims with supporting evidence

Each claim includes:

- subject
- fact
- evidence quote
- source file
- timestamp
- confidence score

---

## Deduplication

The deduplication layer removes redundant knowledge by merging:

- duplicate entities
- duplicate relationships
- duplicate claims

This prevents the memory system from storing the same knowledge multiple times.

---

## Memory Graph

Extracted knowledge is stored in a **Neo4j graph database**.

Node types:

- `Document`
- `Entity`
- `Claim`

Relationship types:

- `MENTIONS`
- `HAS_CLAIM`
- `SUPPORTS`
- `RELATION`

This structure allows queries that traverse entities, claims, and supporting evidence.

---

## Graph-Based Retrieval

The retrieval module performs **Graph-RAG style retrieval**:

1. Map query to candidate entities
2. Traverse the graph for connected claims
3. Return grounded context with evidence

Example query:

Query: Enron

Result:
Phillip K Allen -[WORKS_AT]-> Enron
Source: allen-p/\_sent_mail/1000

Each retrieved item includes a **source citation** that allows the user to verify the claim.

---

## Visualization

The system includes an interactive **Streamlit application** that allows users to:

- explore the memory graph
- search entities
- inspect relationships
- view supporting evidence
- examine claim nodes

The visualization includes:

- graph explorer
- evidence panel
- filtering options
- graph statistics

---

# Installation

Create a Python environment and install dependencies.

pip install -r requirements.txt

---

# Environment Variables

Set the required environment variables before running Neo4j components.

export NEO4J_URI="neo4j+s://YOUR_DATABASE.databases.neo4j.io"
export NEO4J_USERNAME="neo4j"
export NEO4J_PASSWORD="YOUR_PASSWORD"

For extraction:

export GROQ_API_KEY="YOUR_GROQ_API_KEY"

---

# Running the Pipeline

## Step 1 — Extraction

Run the extraction pipeline to process emails.

python -m extraction.extraction_pipeline --limit 5 --api-key YOUR_GROQ_API_KEY

This produces:

data/processed/extracted_memories.json

---

## Step 2 — Deduplication

python -m deduplication.deduplication

Output:

data/processed/deduped_memories.json

---

## Step 3 — Load Memory Graph

python -m graph.load_to_neo4j

This loads the extracted knowledge into Neo4j.

---

## Step 4 — Check Graph

python -m graph.check_graph

This verifies the graph contents and prints statistics.

---

## Step 5 — Retrieval

Run the retrieval script.

python -m retrieval.retrieve_memory

Example:

Enter a search term: Enron

Phillip K Allen -[WORKS_AT]-> Enron
SOURCE: allen-p/\_sent_mail/1000

---

## Step 6 — Visualization

Launch the interactive UI.

streamlit run visualization/app.py

Then open:

http://localhost:8501

---

# Example Retrieval Output

Query: Enron

TYPE: RELATION
ENTITY: Phillip K Allen
FACT: Phillip K Allen -[WORKS_AT]-> Enron
SOURCE: [allen-p/_sent_mail/1000.]

---

# Design Notes

Detailed design decisions including ontology, extraction strategy, deduplication approach, and memory graph design are documented in:

docs/design_notes.md

---

# Limitations

Current limitations include:

- small subset of emails processed
- simple entity canonicalization
- no full historical claim revision tracking
- no permission enforcement layer

---

# Future Improvements

Potential extensions include:

- processing larger email corpora
- stronger entity canonicalization
- historical claim versioning
- ranking improvements in retrieval
- permission-aware retrieval
- incremental memory updates

---

# Conclusion

This project demonstrates a prototype **memory graph system for organizational knowledge**, combining:

- structured extraction
- deduplication
- graph storage
- grounded retrieval
- interactive visualization

The architecture is designed to be adaptable to target environments including **email, Slack and the issue tracking system**.
