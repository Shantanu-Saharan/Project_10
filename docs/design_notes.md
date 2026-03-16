# Design Notes

## Overview

This project implements a grounded long-term memory system over a subset of the Enron email dataset. The pipeline extracts structured knowledge from raw emails, deduplicates the extracted memory items, loads them into a Neo4j graph, retrieves grounded context packs, and exposes the graph through an interactive visualization.

## Corpus

The corpus used is a subset of the Enron Email Dataset. This dataset was chosen because it contains real organizational communication with people, teams, dates, requests, and decisions. It is a good proxy for Layer10’s target environment of email, chat, and work artifacts.

## Ontology / Schema

The extraction schema contains three main object types:

- **Entity**

  - `name`
  - `label`

- **Relationship**

  - `source_entity`
  - `target_entity`
  - `relation_type`
  - `evidence_quote` (optional)

- **GroundedClaim**
  - `subject`
  - `fact`
  - `evidence_quote`
  - `source_file`
  - `timestamp` (optional)
  - `confidence` (optional)

This keeps the ontology small, coherent, and extensible.

## Grounding

Every extracted claim is grounded by:

- source file id
- exact evidence quote
- optional timestamp
- confidence score

This ensures each memory item can be traced back to a concrete artifact.

## Extraction Contract

The extraction layer uses a free hosted model through Groq with schema-constrained outputs enforced through `instructor` and `pydantic`.

Key features:

- schema validation
- retry support
- token-saving truncation
- progressive checkpointing
- skip/resume support for already processed emails

## Deduplication Strategy

The deduplication layer performs:

- duplicate record removal by `email_id`
- entity deduplication by normalized `(name, label)`
- relationship deduplication by normalized `(source, target, type)`
- claim deduplication by normalized `(subject, fact, evidence, source)`

This is a lightweight but practical first-pass deduplication design.

## Memory Graph Design

The graph uses Neo4j with the following node types:

- `Document`
- `Entity`
- `Claim`

Relationships:

- `MENTIONS`
- `HAS_CLAIM`
- `SUPPORTS`
- `RELATION`

This design keeps the graph queryable and grounded while remaining simple enough for a take-home project.

## Time Semantics

Claims store `event_time` where available. In this prototype, validity time and historical revision tracking are not fully modeled in code, but the graph schema can be extended with:

- supersession edges
- active/inactive claim states
- validity windows

## Retrieval Design

Retrieval is graph-based rather than vector-based.

Steps:

1. map query to candidate entities through case-insensitive matching
2. retrieve related claims and relations
3. rank claims by confidence
4. format output with grounded source citations

This produces a context pack that is directly auditable.

## Visualization

The visualization layer uses Streamlit and Pyvis to provide:

- graph exploration
- search/filter support
- evidence panel
- graph stats

This allows a user to inspect entities, claims, relationships, and supporting evidence.

## Adapting to Layer10

To adapt this system to Layer10’s target environment:

### Email + Slack + Jira/Linear fusion

The ontology would be extended with:

- ticket / issue nodes
- channel / thread nodes
- project / component nodes
- cross-artifact references

### Long-term memory

Not all extracted context should become durable memory. Durable memory should require:

- repeated support
- high confidence
- recency and relevance checks
- optional human review

### Grounding and safety

All retrieval must preserve:

- provenance
- source citations
- permission-aware access
- deletion and redaction propagation

### Permissions

In production, every retrieved memory item should be filtered by access to the underlying source system.

### Operational considerations

A production system would require:

- incremental ingestion
- redaction-aware deletes
- regression evaluation
- monitoring for extraction drift
- cost-aware batching and model selection

## Limitations

Current limitations include:

- small processed sample size
- limited entity canonicalization
- no full historical revision tracking
- no merge reversibility UI
- no permission enforcement in code

## Conclusion

This project demonstrates the core Layer10 memory architecture:

- grounded extraction
- deduplication
- graph-based storage
- grounded retrieval
- explorable visualization
