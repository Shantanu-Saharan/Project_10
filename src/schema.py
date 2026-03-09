from pydantic import BaseModel, Field
from typing import List, Optional
import datetime

class Entity(BaseModel):
    """A person, place, or thing. Crucial for Deduplication."""
    name: str = Field(..., description="Normalized name, e.g. 'Vince Kaminski'")
    label: str = Field(..., description="Category: PERSON, PROJECT, ORG, DATE")
    
class Relationship(BaseModel):
    """The connection between two entities. Crucial for the Graph."""
    source_entity: str
    target_entity: str
    relation_type: str = Field(..., description="e.g., WORKS_ON, REPORTS_TO, ATTENDED")

class GroundedClaim(BaseModel):
    """A single fact with a 'receipt'."""
    subject: str
    fact: str
    evidence_quote: str = Field(..., description="The exact text from the email.")
    timestamp: str = Field(..., description="Date of the email to handle evolution.")
    source_file: str = Field(..., description="The 'file' column from our CSV.")
    confidence: float

class ExtractionOutput(BaseModel):
    entities: List[Entity]
    relationships: List[Relationship]
    claims: List[GroundedClaim]