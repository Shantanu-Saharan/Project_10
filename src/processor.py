import pandas as pd
import instructor
from groq import Groq
from src.extraction.schema import ExtractionOutput
import os
import json

class EnronProcessor:
    def __init__(self, api_key):
        # We use instructor to wrap the LLM and enforce our schema
        self.client = instructor.from_groq(
            Groq(api_key=api_key), 
            model="llama-3.3-70b-versatile"
        )

    def process_row(self, row):
        """Processes a single email row from the dataframe."""
        email_content = row['message']
        source_id = row['file']
        
        # This is the "System" part: Structured prompt + Schema validation
        try:
            extraction = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a Knowledge Graph extractor. Extract entities, relationships, and grounded claims."
                    },
                    {
                        "role": "user", 
                        "content": f"Source File: {source_id}\n\nEmail Content:\n{email_content}"
                    }
                ],
                response_model=ExtractionOutput,
                max_retries=2
            )
            return extraction
        except Exception as e:
            print(f"❌ Error in {source_id}: {e}")
            return None