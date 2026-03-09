# I'm using the 'instructor' library here because it's way easier to 
# force the LLM to give me clean JSON than writing regex myself.
# I had to set max_retries to 2 because sometimes the Llama 70b 
# cuts off the JSON if the email is too long.

import pandas as pd
import instructor
from groq import Groq
from src.extraction.schema import ExtractionOutput
import os
import json

class EmailExtractor:
    def __init__(self, groq_key):
        # Setting up the client with the schema wrapper
        self.groq_client = instructor.from_groq(
            Groq(api_key=groq_key), 
            model="llama-3.3-70b-versatile"
        )

    def process_email(self, row):
        # I have pulled outthe columns here 
        email_body = row['message']
        file_id = row['file']
        
        # I have called the LLM with the predefined schema
        try:
            # Note: I'm keeping the system prompt simple so it doesn't get confused. Maybe later we can change it to a complex one
            extraction = self.groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "system", 
                        "content": "Extract entities, relationships, and grounded claims for a Knowledge Graph."
                    },
                    {
                        "role": "user", 
                        "content": f"Source: {file_id}\n\nText:\n{email_body}"
                    }
                ],
                response_model=ExtractionOutput,
                max_retries=2 # retry if the JSON is malformed
            )
            return extraction
        except Exception as err:
            print(f"Skipping {file_id} due to error: {err}")
            return None