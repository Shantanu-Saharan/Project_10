from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class Entity(BaseModel):
    """Canonical entity mentioned in an email."""
    # I used ConfigDict(extra="ignore") across all these models. 
    # This is a safety choice: if the LLM adds extra keys we didn't ask for, 
    # Pydantic will just ignore them instead of crashing the whole pipeline.
    model_config = ConfigDict(extra="ignore")

    name: str = Field(..., description="Normalized entity name.")
    label: str = Field(
        ...,
        description="Entity type such as PERSON, ORG, PROJECT, TEAM, DATE, LOCATION, or TOPIC."
    )


class Relationship(BaseModel):
    """Directed relationship between two extracted entities."""
    model_config = ConfigDict(extra="ignore")

    # These fields help you map how people and organizations in Enron are connected.
    source_entity: str = Field(..., description="Source entity name.")
    target_entity: str = Field(..., description="Target entity name.")
    relation_type: str = Field(
        ...,
        description="Relationship type such as REPORTS_TO, WORKS_ON, MENTIONED_WITH, SCHEDULED_WITH."
    )
    # I made this optional because sometimes a relationship is obvious 
    # from context but doesn't have one specific 'smoking gun' sentence.
    evidence_quote: Optional[str] = Field(
        default=None,
        description="Optional exact quote supporting the relationship."
    )


class GroundedClaim(BaseModel):
    """A grounded claim supported by the email text."""
    model_config = ConfigDict(extra="ignore")

    # Claims are the most detailed part of the extraction. 
    # They turn email sentences into verifiable facts.
    subject: str = Field(..., description="Main subject of the claim.")
    fact: str = Field(..., description="Extracted fact stated in simple natural language.")
    evidence_quote: str = Field(..., description="Exact supporting quote from the email.")
    source_file: str = Field(..., description="Email source id from the dataset.")
    
    # You can use the timestamp and confidence to filter the data later in the graph.
    timestamp: Optional[str] = Field(
        default=None,
        description="Email timestamp if available, else null."
    )
    confidence: Optional[float] = Field(
        default=None,
        description="Optional confidence score between 0 and 1."
    )


class ExtractionOutput(BaseModel):
    """Top-level structured extraction result for one email."""
    model_config = ConfigDict(extra="ignore")

    # This is the main container that the 'instructor' library uses to 
    # organize the AI's response into lists of objects.
    entities: List[Entity] = Field(default_factory=list)
    relationships: List[Relationship] = Field(default_factory=list)
    claims: List[GroundedClaim] = Field(default_factory=list)