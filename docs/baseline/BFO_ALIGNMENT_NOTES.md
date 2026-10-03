# BFO Alignment Notes

## a. Recipe Alignment
**Quote:** 
```turtle
priory:Recipe a owl:Class ;
    rdfs:label "Recipe"@en ;
    rdfs:comment "A transformation process taking ingredient inputs to produce an item output."@en .
```
*(ontology/priory_core.ttl:196-198)*

**Concern:** The definition describes `Recipe` as a "process", which would imply it belongs under `BFO_0000015` (Process). However, ontologically, a recipe is an informational artifact (`IAO_0000030: Information Content Entity` or a Plan Specification) that *directs* a process. Confusing the specification with the execution of the process violates BFO realism.
**Confidence Level:** High

## b. ManifestedArtifact vs Item Placement
**Quote (ManifestedArtifact):**
```turtle
priory:ManifestedArtifact a owl:Class ;
    rdfs:subClassOf priory:Entity, bfo:BFO_0000004 ;
    rdfs:label "Manifested Combat Artifact"@en ;
```
*(ontology/priory_core.ttl:111-113)*

**Quote (Item):**
```turtle
priory:Item a owl:Class ;
    rdfs:subClassOf priory:Entity ;
    rdfs:label "Game Item"@en ;
```
*(ontology/priory_core.ttl:116-118)*

**Concern:** `ManifestedArtifact` subclasses `BFO_0000004` (Independent Continuant / Material Entity). However, `Item` sits completely detached from BFO. Is an "Item" an independent physical entity, or merely a `BFO_0000023` (Role) that an artifact plays while in an inventory container? BFO forbids multiple inheritance that crosses disjoint boundaries. The split here introduces potential inconsistency.
**Confidence Level:** Medium

## c. AcquisitionPath and IngredientRequirement
**Quote:**
```turtle
priory:IngredientRequirement a owl:Class ;
    rdfs:label "Ingredient Requirement"@en ;
    rdfs:comment "Reified N-ary relation specifying a required item or currency and its exact quantity."@en .
```
*(ontology/priory_core.ttl:210-212)*

**Quote:**
```turtle
priory:AcquisitionPath a owl:Class ;
    rdfs:label "Acquisition Pathway"@en ;
    skos:definition "A method by which a player can obtain an item or currency in Guild Wars 2."@en ;
```
*(ontology/priory_core.ttl:219-221)*

**Concern:** Both lack a BFO parent. `IngredientRequirement` is a reified relation; in BFO, relational qualities are generally modeled using `BFO_0000020` (Specifically Dependent Continuant) or as information components in IAO. `AcquisitionPath` reads like a Plan Specification (`IAO_0000104`) or a Disposition (`BFO_0000016`). Leaving them detached creates an ungrounded domain graph.
**Confidence Level:** High

## d. LedgerToken
**Quote:**
```turtle
priory:LedgerToken a owl:Class ;
    rdfs:subClassOf priory:Entity, iao:IAO_0000030 ;
    rdfs:label "Ledger Token / Accounting Entity"@en ;
    rdfs:comment "Informational bookkeeping tokens, currencies, and intermediate crafting components."@en .
```
*(ontology/priory_core.ttl:162-165)*

**Concern:** `LedgerToken` maps to `IAO_0000030` (Information Content Entity). This makes sense for abstract wallet currencies (account variables). But the ontology states containerized tokens (physical items in bags) are subclasses of `LedgerToken`. A physical token occupying a physical slot should likely be a Material Entity (`BFO_0000040`), not an information artifact.
**Confidence Level:** Medium
