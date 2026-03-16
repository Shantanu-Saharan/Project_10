from __future__ import annotations

from typing import Any, Dict, Optional

import instructor
from groq import Groq

from .schema import ExtractionOutput

# I set these defaults to keep the processing fast and the costs low.
# Llama-3.1-8b is great for simple extraction tasks.
DEFAULT_MODEL = "llama-3.1-8b-instant"
DEFAULT_MAX_RETRIES = 1
DEFAULT_MAX_CHARS = 1000


def clean_output(extraction: ExtractionOutput) -> ExtractionOutput:
    """
    Remove weak, duplicate, or incomplete entries after schema parsing succeeds.
    """
    # I added this post-processing step because even good LLMs sometimes 
    # return empty quotes or repetitive data.

    # Filter out claims that don't have a supporting quote.
    extraction.claims = [
        c for c in extraction.claims
        if c.evidence_quote and str(c.evidence_quote).strip()
    ]

    # Keep only relationships that have all required parts.
    extraction.relationships = [
        r for r in extraction.relationships
        if r.source_entity and r.target_entity and r.relation_type
    ]

    # Deduplicate entities by name and label.
    seen_entities = set()
    unique_entities = []
    for e in extraction.entities:
        key = (str(e.name).strip().lower(), str(e.label).strip().upper())
        if key not in seen_entities:
            seen_entities.add(key)
            unique_entities.append(e)

    extraction.entities = unique_entities
    return extraction


class EnronProcessor:
    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        max_retries: int = DEFAULT_MAX_RETRIES,
        max_chars: int = DEFAULT_MAX_CHARS,
    ) -> None:
        self.model = model
        self.max_retries = max_retries
        self.max_chars = max_chars

        # I'm using the 'instructor' library here to wrap the Groq client.
        # It forces the LLM to follow our Pydantic schema perfectly.
        self.client = instructor.from_groq(
            Groq(api_key=api_key),
            model=self.model,
        )

    def _truncate_text(self, text: str) -> str:
        # Truncate text to stay within the character limit defined in the constructor.
        if not text:
            return ""

        text = str(text).strip()
        if len(text) <= self.max_chars:
            return text

        return text[: self.max_chars] + "\n\n[TRUNCATED_FOR_TOKEN_SAVING]"

    def _build_messages(self, source_id: str, email_text: str) -> list[Dict[str, str]]:
        # This system prompt contains the strict rules for the investigator.
        # I used very direct language here to minimize 'chatty' responses from the AI.
        system_prompt = (
            "You are a strict information extraction system for organizational emails.\n"
            "Return ONLY schema-compatible structured data.\n\n"
            "Rules:\n"
            "1. Use only these top-level fields: entities, relationships, claims.\n"
            "2. Do not add any other top-level fields.\n"
            "3. Do not repeat top-level keys.\n"
            "4. Do not use null for claim evidence_quote.\n"
            "5. If a claim lacks direct quote support, omit that claim.\n"
            "6. Relationship evidence_quote may be omitted if not available.\n"
            "7. Prefer fewer high-confidence items.\n"
            "8. Use exact short quotes copied from the email.\n"
            "9. Do not include passwords, credentials, or sensitive secrets as claims.\n"
            "10. If little useful information exists, return empty lists.\n"
        )

        user_prompt = (
            f"Source File: {source_id}\n\n"
            "Extract grounded entities, relationships, and claims from this email.\n"
            "Only include information explicitly supported by the text.\n\n"
            "Output format rules:\n"
            "- entities: list of {name, label}\n"
            "- relationships: list of {source_entity, target_entity, relation_type, evidence_quote}\n"
            "- claims: list of {subject, fact, evidence_quote, source_file, timestamp, confidence}\n"
            "- claims must always include a non-empty evidence_quote\n"
            "- relationships may omit evidence_quote if unavailable\n"
            "- do not output markdown\n"
            "- do not output explanatory text\n\n"
            f"Email Content:\n{email_text}"
        )

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def process_email(self, source_id: str, email_text: str) -> Optional[ExtractionOutput]:
        """
        Send email text to the LLM and return the structured extraction results.
        """
        cleaned_text = self._truncate_text(email_text)

        try:
            # Use the instructor client to generate a response that matches ExtractionOutput.
            extraction = self.client.chat.completions.create(
                messages=self._build_messages(source_id=source_id, email_text=cleaned_text),
                response_model=ExtractionOutput,
                max_retries=self.max_retries,
            )

            # Apply my manual cleaning logic to filter out low-quality data.
            extraction = clean_output(extraction)
            return extraction

        except Exception as e:
            # You should see an error message in the console if the API call fails.
            print(f"❌ Error in {source_id}: {e}")
            return None

    def process_row(self, row: Dict[str, Any]) -> Optional[ExtractionOutput]:
        """
        Helper method to process a single row from a CSV or DataFrame.
        """
        source_id = str(row.get("file", "unknown_source"))

        # I am checking multiple possible column names to make this compatible
        # with different versions of the Enron dataset.
        email_text = (
            row.get("body_only")
            or row.get("message")
            or row.get("text")
            or ""
        )

        return self.process_email(source_id=source_id, email_text=str(email_text))