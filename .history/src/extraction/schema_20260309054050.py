# I based this schema on the 'MemoryGraphDesign' specs for Layer10.
# The 'GroundedClaim' class is the most important part because it 
# connects the facts directly back to the email 'receipts'.

from pydantic import BaseModel, Field
from typing import List, Optional

class Entity(BaseModel):
    # This normalized name is key for deduplication later in Neo4j
    name: str = Field(..., description="e.g. 'Vince Kaminski'")
    label: str = Field(..., description="PERSON, PROJECT, ORG, or DATE")
    
class Relationship(BaseModel):
    # Basic triple for the graph edges
    source_entity: str
    target_entity: str
    relation_type: str = Field(..., description="WORKS_ON, REPORTS_TO, etc.")

class GroundedClaim(BaseModel):
    # This is where the 'Grounding' happens
    subject: str
    fact: str
    evidence_quote: str = Field(..., description="The exact quote from the email")
    # Using timestamp to track how facts evolve over time
    timestamp: str 
    source_file: str = Field(..., description="The file path from the Enron CSV")
    confidence: float # LLM's confidence score for observability

class ExtractionOutput(BaseModel):
    # The final container for the LLM response
    entities: List[Entity]
    relationships: List[Relationship]
    claims: List[GroundedClaim]