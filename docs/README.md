# Project Priory — Architecture & Semantic Layer Documentation

Welcome to the technical documentation for **Project Priory (gw2-priory-def)**, the neuro-symbolic knowledge layer and personalized progression engine for *Guild Wars 2*.

This documentation suite provides a complete, no-assumed-knowledge technical breakdown of the entire system, with an exhaustive focus on the **three semantic data layers** (`ref`, `def`, and the **Triple Store Graph Engine**).

---

## 📚 Table of Contents

1. [🏛️ Architecture Overview](file:///Users/clementd/Documents/GitHub/gw2-priory-def/docs/architecture_overview.md)
   * High-level system topology.
   * The Neuro-Symbolic Sandwich design pattern.
   * Component responsibilities and system boundaries.

2. [🔍 Semantic Layers Deep Dive (`ref`, `def`, Triple Store)](file:///Users/clementd/Documents/GitHub/gw2-priory-def/docs/semantic_layers_deep_dive.md)
   * **Layer 1 (`ref`):** W3C SKOS Controlled Vocabularies (`gw2-priory-ref`).
   * **Layer 2 (`def`):** W3C OWL 2 DL Schemas, SHACL Shapes & Instance Graphs (`gw2-priory-def`).
   * **Layer 3 (Triple Store):** In-Memory RDF Store, SPARQL 1.1 Traversal, Dynamic Overlay & Delta Engine.
   * Full cross-layer Mermaid diagrams and triple relationship maps.

3. [⚡ End-to-End Data Flow & Reasoning Trace](file:///Users/clementd/Documents/GitHub/gw2-priory-def/docs/data_flow_and_reasoning.md)
   * Step-by-step execution walkthrough of a real prompt (`"2 Legendary Sigils, 90 mins"`).
   * Exact data payloads at every transition point (Prompt $\rightarrow$ Top LLM $\rightarrow$ SPARQL $\rightarrow$ ArenaNet API $\rightarrow$ Delta Engine $\rightarrow$ Solver $\rightarrow$ Bottom LLM $\rightarrow$ User).
   * Complete Mermaid sequence diagram.

4. [📖 Ontology & Vocabulary Reference Guide](file:///Users/clementd/Documents/GitHub/gw2-priory-def/docs/ontology_and_vocab_reference.md)
   * Formal catalog of all OWL Classes.
   * Formal catalog of all Object and Datatype Properties.
   * Reference tables of all SKOS Concept Schemes and URI namespaces.
   * SHACL integrity shapes reference.

5. [📊 Pipeline & Semantic Touchpoints Reference](file:///Users/clementd/Documents/GitHub/gw2-priory-def/docs/neuro_symbolic_architecture_and_pipeline.md)
   * Visual diagrams of the Neuro-Symbolic Sandwich pipeline.
   * End-to-end component sequence interaction graphs.
   * Detailed breakdown of the 3 Semantic Layer touchpoints (resolution, graph traversal, and factual serialization).
   * Granular 10-step component and data transformation matrix.
